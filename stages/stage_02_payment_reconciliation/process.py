"""Lógica de la Etapa 2 - Conciliación de pagos.

La validación de estructura la hace el ejecutor antes de llamar a process(): el
reporte ETY procesado en la Etapa 1 y la hoja Pagos de cada informe de pago de
Tesorería (uno por fecha). Aquí van las reglas propias de la etapa, en el orden de
ESPECIFICACION.md. Las reglas de conciliación se agregan a medida que se especifiquen.
"""

from datetime import date
from typing import Any

import pandas as pd

from core.audit import AuditLog, is_empty
from core.cleaning import comparable_text, convert_columns, parse_date, parse_number
from core.runner import StageError
from core.settings import DATE_FORMAT_TEXT, INPUT_DATE, SOURCE_FILE, SOURCE_ROW
from stages.stage_02_payment_reconciliation.config import (
    BUSINESS_UNIT,
    BUSINESS_UNIT_COLUMN,
    ETY_GROSS_COLUMN,
    ETY_PAYMENT_DATE_COLUMN,
    EXECUTION_DATE_COLUMN,
    INPUTS,
    MAX_ROWS_IN_MESSAGE,
    PAYMENT_GROSS_COLUMN,
    PAYMENT_VOUCHER_COLUMN,
)

# Tipo de cada columna obligatoria del informe de pago, según config.INPUTS.
PAYMENT_COLUMN_TYPES = INPUTS["treasury_reports"]["columns"]


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    # Los informes de pago solo se depuran en memoria: no hacen parte del archivo de salida
    # y el archivo original nunca se modifica.
    reports = inputs["treasury_reports"]
    payments = analyze_payments(reports, audit)
    audit.step(COMPARE_STEP)
    ety_totals = ety_gross_by_day(inputs["ety_processed"])
    loaded = reports[[SOURCE_FILE, INPUT_DATE]].drop_duplicates()
    for name, day in loaded.itertuples(index=False):
        compare_with_ety(name, day, payments, ety_totals, audit)
    return inputs["ety_processed"]


# Paso del log de ejecución de la regla VAL-202.
COMPARE_STEP = f"Comparando el total de {PAYMENT_GROSS_COLUMN} con el de {ETY_GROSS_COLUMN} del reporte ETY"


def analyze_payments(payments: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Reglas de los informes de pago, en orden: LIM-201, VAL-201, TIP-003/005, DUP-201 y TRA-201.

    La usa process() con todos los informes y analyze_payment_report() con cada informe
    apenas se carga, para que Procesar aplique exactamente las mismas reglas. Devuelve
    los pagos depurados.
    """
    audit.step(f"Tomando de los informes de pago los registros con {BUSINESS_UNIT_COLUMN} {BUSINESS_UNIT}")
    payments = filter_business_unit(payments, audit)
    audit.step(f"Verificando que la {EXECUTION_DATE_COLUMN} corresponda a la fecha de cada informe")
    check_execution_dates(payments, audit)
    audit.step(f"Convirtiendo {PAYMENT_VOUCHER_COLUMN} a código e {PAYMENT_GROSS_COLUMN} a moneda")
    payments = convert_payment_columns(payments, audit)
    audit.step(f"Dejando un solo registro por {PAYMENT_VOUCHER_COLUMN} en cada informe de pago")
    payments = remove_repeated_vouchers(payments, audit)
    audit.step(f"Calculando el total de {PAYMENT_GROSS_COLUMN}")
    report_gross_totals(payments, audit)
    return payments


def analyze_payment_report(
    report: pd.DataFrame, ety: pd.DataFrame, day: date, audit: AuditLog
) -> tuple[list[str], bool]:
    """Analiza un informe de pago apenas se carga (INPUT_ANALYSIS en __init__.py).

    Aplica las mismas reglas que Procesar, incluida la comparación con el reporte ETY
    (VAL-202), y devuelve la información calculada que la interfaz muestra debajo del
    campo del informe y si los totales coinciden (la sección se pinta verde o roja).

    Si los totales no coinciden, lo importante es la diferencia: la primera línea la
    anuncia (la interfaz la resalta) y solo siguen los totales que la explican.
    """
    payments = analyze_payments(report, audit)
    audit.step(COMPARE_STEP)
    name = report[SOURCE_FILE].iloc[0] if len(report) else "Informe"
    report_total, ety_total, matches = compare_with_ety(name, day, payments, ety_gross_by_day(ety), audit)
    discarded = sum(1 for removal in audit.removals if removal.rule == "DUP-201")
    is_number = payments[PAYMENT_GROSS_COLUMN].map(_is_number).astype(bool)
    totals = [f"Total de {PAYMENT_GROSS_COLUMN} del informe: {money(report_total)} en {_records(is_number.sum())}"]
    if not is_number.all():
        totals.append(f"Sin {PAYMENT_GROSS_COLUMN} numérico (no se sumaron): {_records((~is_number).sum())}")
    totals.append(
        f"Total de {ETY_GROSS_COLUMN} del reporte ETY del {day.strftime(DATE_FORMAT_TEXT)}: {money(ety_total)}"
    )
    if not matches:
        difference = (
            f"El total de {PAYMENT_GROSS_COLUMN} no es igual al de {ETY_GROSS_COLUMN} del reporte ETY: "
            f"diferencia de {money(report_total - ety_total)}"
        )
        return [difference, *totals], False
    counts = [
        f"Registros con {BUSINESS_UNIT_COLUMN} {BUSINESS_UNIT}: {len(payments) + discarded} de {len(report)}",
        f"Registros descartados por {PAYMENT_VOUCHER_COLUMN} repetido: {discarded}",
    ]
    return [*counts, *totals, "Los totales son iguales"], True


def ety_gross_by_day(ety: pd.DataFrame) -> dict[date, float]:
    """Total de VR. BRUTO del reporte ETY por cada FECHA DE PAGO (solo el día, sin la hora).

    Las fechas vacías o no válidas y los valores que no son número no se suman: la
    Etapa 1 ya los reportó y no corresponden a ningún informe de pago.
    """
    totals: dict[date, float] = {}
    for when, value in zip(ety[ETY_PAYMENT_DATE_COLUMN], ety[ETY_GROSS_COLUMN]):
        day = execution_day(when)
        try:
            amount = parse_number(value)
        except ValueError:
            continue
        if day is not None and amount is not None:
            totals[day] = totals.get(day, 0.0) + amount
    return totals


def compare_with_ety(
    name: str, day: date, payments: pd.DataFrame, ety_totals: dict[date, float], audit: AuditLog
) -> tuple[float, float, bool]:
    """Compara el total de Impt Bruto de un informe con el de VR. BRUTO del ETY de su fecha. Regla VAL-202.

    Se compara al centavo, para que las diferencias de redondeo de Excel no cuenten.
    Si no son iguales se avisa en el log (✗), pero no se detiene: la diferencia puede
    deberse a pagos que el usuario debe revisar. Devuelve los dos totales y si son iguales.
    """
    rows = payments[(payments[SOURCE_FILE] == name) & (payments[INPUT_DATE] == day)]
    values = rows[PAYMENT_GROSS_COLUMN]
    report_total = float(values[values.map(_is_number).astype(bool)].sum())
    ety_total = ety_totals.get(day, 0.0)
    matches = round(report_total - ety_total, 2) == 0
    when = day.strftime(DATE_FORMAT_TEXT)
    if matches:
        audit.note(f"{name} ({when}): {money(report_total)}, igual al {ETY_GROSS_COLUMN} del reporte ETY")
    else:
        audit.note(
            f"[VAL-202] {name} ({when}): {PAYMENT_GROSS_COLUMN} {money(report_total)} y {ETY_GROSS_COLUMN} "
            f"del reporte ETY {money(ety_total)}; diferencia de {money(report_total - ety_total)}",
            ok=False,
        )
    return report_total, ety_total, matches


def filter_business_unit(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Deja solo los pagos de la unidad de negocio del FCP (UN AP656). Regla LIM-201.

    El informe de Tesorería trae los pagos de todas las unidades de negocio. Los
    demás registros no son del FCP: en el log solo se cuenta cuántos se tomaron de
    cada informe, porque listarlos uno a uno (cientos por informe) taparía lo importante.
    """
    target = comparable_text(BUSINESS_UNIT)
    keep = df[BUSINESS_UNIT_COLUMN].map(lambda value: comparable_text(value) == target).astype(bool)
    for name, in_file in keep.groupby(df[SOURCE_FILE], sort=False):
        audit.note(
            f"{name}: {in_file.sum()} de {len(in_file)} registros con {BUSINESS_UNIT_COLUMN} {BUSINESS_UNIT}"
        )
    return df[keep]


def check_execution_dates(df: pd.DataFrame, audit: AuditLog) -> None:
    """Verifica que la F Ejec de cada pago sea la fecha del campo donde se cargó su informe. Regla VAL-201.

    Una fecha distinta indica, casi siempre, que el informe se cargó en el campo de
    otra fecha. Por eso se detiene sin generar resultados, como un error de estructura,
    y se explica qué informe falla, con qué fechas y en qué filas.
    """
    problems = []
    for (name, day), rows in df.groupby([SOURCE_FILE, INPUT_DATE], sort=False):
        found = rows[EXECUTION_DATE_COLUMN].map(execution_day)
        is_wrong = found != day
        if not is_wrong.any():
            audit.note(f"{name}: {len(rows)} registros del {day.strftime(DATE_FORMAT_TEXT)}")
        else:
            problems.append(date_problem(name, day, rows[is_wrong], found[is_wrong], len(rows)))
    if problems:
        for problem in problems:
            audit.note(problem, ok=False)
        audit.finish_step()
        count = "1 informe" if len(problems) == 1 else f"{len(problems)} informes"
        message = (
            f"La {EXECUTION_DATE_COLUMN} de {count} de pago no coincide con la fecha del campo donde se cargó."
        )
        raise StageError(message, problems, audit.step_lines())


def convert_payment_columns(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Comprobante como código (TIP-003) e Impt Bruto como moneda (TIP-005).

    Así «00157395» y 157395 se reconocen como el mismo comprobante y el total se calcula
    sobre números. Un Impt Bruto que no es número queda como estaba y se reporta como Error.
    """
    columns = [PAYMENT_VOUCHER_COLUMN, PAYMENT_GROSS_COLUMN]
    return convert_columns(df, {c: PAYMENT_COLUMN_TYPES[c] for c in columns}, audit)


def remove_repeated_vouchers(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Deja un solo registro por Comprobante dentro de cada informe de pago. Regla DUP-201.

    Un comprobante repetido es el mismo pago (por ejemplo, partido en dos transferencias
    con el mismo Impt Bruto): sumarlo dos veces inflaría el total. Se conserva el primero
    y cada descartado queda en la hoja Acciones con la fila del que se conservó. Los
    registros sin comprobante no se comparan entre sí. Se hace en memoria: el informe
    original no se modifica.
    """
    key = [SOURCE_FILE, PAYMENT_VOUCHER_COLUMN]
    has_voucher = ~df[PAYMENT_VOUCHER_COLUMN].map(is_empty).astype(bool)
    repeated = df.duplicated(subset=key, keep="first") & has_voucher
    first_rows = df[has_voucher & ~repeated].set_index(key)[SOURCE_ROW]
    reasons = pd.Series(
        [
            f"{PAYMENT_VOUCHER_COLUMN} repetido en el informe; se conserva la fila {first_rows.get((file, voucher))}"
            for file, voucher in zip(df[SOURCE_FILE], df[PAYMENT_VOUCHER_COLUMN])
        ],
        index=df.index,
        dtype=object,
    )
    return audit.remove_rows(df, repeated, "DUP-201", reasons)


def report_gross_totals(df: pd.DataFrame, audit: AuditLog) -> None:
    """Informa el total de Impt Bruto de cada informe y de todos juntos. Regla TRA-201.

    Se calcula después de dejar un registro por comprobante. Los valores que no son
    número (ya reportados como Error al convertir) no se suman, y se avisa cuántos son.
    """
    is_number = df[PAYMENT_GROSS_COLUMN].map(_is_number).astype(bool)
    for (name, day), rows in df.groupby([SOURCE_FILE, INPUT_DATE], sort=False):
        numbers = is_number[rows.index]
        total = rows.loc[numbers, PAYMENT_GROSS_COLUMN].sum()
        audit.note(
            f"{name} ({day.strftime(DATE_FORMAT_TEXT)}): {money(total)} en {_records(numbers.sum())}"
        )
        if not numbers.all():
            skipped = (~numbers).sum()
            verb = "no se sumó" if skipped == 1 else "no se sumaron"
            audit.note(
                f"{name}: {verb} {_records(skipped)} sin {PAYMENT_GROSS_COLUMN} numérico (ver Acciones)",
                ok=False,
            )
    reports = df[SOURCE_FILE].nunique()
    if reports == 0:
        audit.note("No se cargaron informes de pago: no hay valores que sumar")
        return
    total = df.loc[is_number, PAYMENT_GROSS_COLUMN].sum()
    label = "del informe" if reports == 1 else f"de los {reports} informes"
    audit.note(f"Total {label}: {money(total)} en {_records(is_number.sum())}")


def money(value: float) -> str:
    """Valor en formato de moneda colombiano, para los mensajes: $ 1.234.567,89 o -$ 1.234,00."""
    sign = "-" if round(value, 2) < 0 else ""
    text = f"{abs(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{sign}$ {text}"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not is_empty(value)


def _records(count: int) -> str:
    return "1 registro" if count == 1 else f"{count} registros"


def execution_day(value: Any) -> date | None:
    """Día de ejecución de un pago, sin la hora. None si está vacío o no es una fecha."""
    try:
        parsed = parse_date(value)
    except ValueError:
        return None
    return parsed.date() if parsed else None


def date_problem(name: str, day: date, wrong: pd.DataFrame, found: pd.Series, total: int) -> str:
    """Mensaje para el usuario: qué fechas se encontraron en el informe y en qué filas."""
    details = []
    for value, rows in wrong.groupby(found.map(_date_text), sort=False):
        records = "1 registro" if len(rows) == 1 else f"{len(rows)} registros"
        details.append(f"{value} en {records} ({_rows_text(list(rows[SOURCE_ROW]))})")
    return (
        f"[VAL-201] «{name}» se cargó como informe del {day.strftime(DATE_FORMAT_TEXT)}, pero "
        f"{len(wrong)} de sus {total} registros con {BUSINESS_UNIT_COLUMN} {BUSINESS_UNIT} tienen otra "
        f"{EXECUTION_DATE_COLUMN}: {'; '.join(details)}. Verifique que cargó el informe en el campo de su fecha."
    )


def _date_text(value: date | None) -> str:
    return value.strftime(DATE_FORMAT_TEXT) if value else "vacía o no válida"


def _rows_text(rows: list[int]) -> str:
    """Filas de ejemplo para el mensaje; si son muchas, las demás solo se cuentan."""
    shown = ", ".join(str(row) for row in rows[:MAX_ROWS_IN_MESSAGE])
    hidden = len(rows) - MAX_ROWS_IN_MESSAGE
    label = "fila" if len(rows) == 1 else "filas"
    return f"{label} {shown}" + (f" y {hidden} más" if hidden > 0 else "")
