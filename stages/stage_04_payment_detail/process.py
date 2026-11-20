"""Lógica de la Etapa 4 - Integración al Detalle de pago.

La validación de estructura del reporte ETY la hace el ejecutor antes de llamar a
process(). Aquí van las reglas propias de la etapa, en el orden de ESPECIFICACION.md.
"""

import re
from datetime import date

import pandas as pd

from core.audit import AuditLog, is_empty
from core.cleaning import clean_text, comparable_text, normalize_code, parse_number
from core.settings import SOURCE_FILE, SOURCE_ROW
from core.writer import ExcelFormula
from stages.stage_04_payment_detail.config import (
    BENEFICIARIES_COLUMN,
    BENEFICIARIES_PREFIX,
    BUDGET_CONTRACT_COLUMN,
    BUDGET_PENDING_COLUMN,
    BUDGET_SOURCE_COLUMN,
    BUDGET_SOURCES_COLUMN,
    BUDGET_EMPTY_SOURCE,
    MAX_CONTRACTS_IN_NOTE,
    MIN_BUDGET_RECORDS,
    SOURCE_COUNT,
    OPTIONAL_COLUMNS,
    SOURCES_SEPARATOR,
    COLUMN_MAPPING,
    CONTRACT_BY_CONCEPT,
    CONTRACT_COLUMN,
    CONTRACT_ERROR,
    CONCEPT_COLUMN,
    CONTRACT_PREFIX,
    CONTRACT_SEPARATORS,
    CONTRACT_WORD,
    CURRENT_PAC,
    VALIDITY_COLUMN,
    FIXED_VALUES,
    FORMULA_COLUMNS,
    FORMULA_COLUMNS_AFTER_VALIDITY,
    GENERATION_YEAR_COLUMN,
    INDIVIDUAL_BENEFICIARIES,
    INDIVIDUAL_PAYMENT,
    MASS_PAYMENT,
    MONTH_ABBREVIATION_LENGTH,
    MONTHS,
    PAYMENT_DATE_COLUMN,
    PAYMENT_TYPE_COLUMN,
    PERIOD_COLUMN,
    PERIOD_END_MARKER,
    PERIOD_MONTH_RANGE,
    PERIOD_SEPARATORS,
    PERIOD_SINGLE_MONTH,
    PERIOD_YEAR_PATTERN,
    PROGRAM_COLUMN,
    MAX_SUBTRUSTS_IN_NOTE,
    NUMBER_COLUMNS,
    OUTPUT_LAYOUT,
    SUBTRUST_COLUMN,
    SUBTRUST_RELATIONS,
    VALUE_PREFIXES,
    WEEKLY_REPORT_COLUMN,
)


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog, parameters: dict[str, str]) -> pd.DataFrame:
    """`parameters` trae los valores escritos por el usuario (PARAMETERS), como el PAC vigente."""
    ety = inputs["ety_processed"]
    audit.step("Generando el archivo con la estructura del Detalle de pago")
    detail = empty_payment_detail(ety, audit)
    audit.step("Copiando los datos del reporte ETY al Detalle de pago")
    detail = copy_ety_values(ety, detail, audit)
    audit.step("Asignando los valores fijos del Detalle de pago")
    assign_fixed_values(detail, audit)
    audit.step(f"Asignando {GENERATION_YEAR_COLUMN}")
    assign_generation_year(detail, date.today().year, audit)
    audit.step(f"Asignando {WEEKLY_REPORT_COLUMN}")
    assign_weekly_report(detail, parameters["weekly_report"], audit)
    audit.step(f"Asignando {PAYMENT_TYPE_COLUMN} y {BENEFICIARIES_COLUMN}")
    assign_payment_type(detail, audit)
    audit.step(f"Asignando {PERIOD_COLUMN} según {CONCEPT_COLUMN}")
    assign_billing_period(detail, audit)
    for relation in SUBTRUST_RELATIONS:
        audit.step(f"Asignando {relation['column']} según el {SUBTRUST_COLUMN}")
        assign_from_subtrust(detail, relation, audit, parameters["current_pac"])
    for formula in FORMULA_COLUMNS:
        audit.step(f"Calculando {formula['column']}")
        add_formula(detail, formula, audit)
    audit.step(f"Asignando {CONTRACT_COLUMN} según {CONCEPT_COLUMN} donde la fórmula da {CONTRACT_ERROR}")
    assign_contract_by_concept(detail, audit)
    audit.step(f"Asignando {VALIDITY_COLUMN}")
    assign_validity(detail, audit)
    for formula in FORMULA_COLUMNS_AFTER_VALIDITY:
        audit.step(f"Calculando {formula['column']}")
        add_formula(detail, formula, audit)
    audit.step("Buscando las fuentes de recursos en la Ejecución presupuestal")
    detail = add_budget_sources(detail, inputs["budget_execution"], audit)
    return detail


def empty_payment_detail(ety: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Tabla del Detalle de pago con sus columnas en orden, una fila por registro del ETY,
    todas vacías. Regla TRA-401.

    El formato (encabezados, anchos, formatos de celda) lo aplica el ejecutor con
    OUTPUT_LAYOUT. Cada fila conserva el archivo y la fila de origen del registro del
    ETY, para que los hallazgos se puedan ubicar en la salida.
    """
    # Las columnas opcionales (OPTIONAL_COLUMNS) se agregan después, solo si se cargó su entrada.
    columns = [column for column in OUTPUT_LAYOUT["columns"] if column not in OPTIONAL_COLUMNS]
    detail = pd.DataFrame(None, index=ety.index, columns=columns, dtype=object)
    detail[SOURCE_FILE] = ety[SOURCE_FILE]
    detail[SOURCE_ROW] = ety[SOURCE_ROW]
    audit.transformation("TRA-401", f"Archivo con las {len(columns)} columnas y el formato del Detalle de pago")
    return detail


def copy_ety_values(ety: pd.DataFrame, detail: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Copia los valores del ETY, fila por fila y sin cambios, a su columna del Detalle de pago. Regla TRA-402.

    Las fechas y los valores se copian tal como vienen del ETY (fecha y número); el
    formato con que se ven es el de la columna destino en el Detalle de pago.
    """
    for ety_column, detail_column in COLUMN_MAPPING.items():
        detail[detail_column] = ety[ety_column]
    pairs = ", ".join(f"{source} → {target}" for source, target in COLUMN_MAPPING.items())
    records = "1 registro" if len(ety) == 1 else f"{len(ety)} registros"
    audit.transformation("TRA-402", f"{records} del reporte ETY copiados: {pairs}")
    for column in NUMBER_COLUMNS:
        write_as_numbers(detail, column, audit)
    for column, prefix in VALUE_PREFIXES.items():
        add_prefix(detail, column, prefix, audit)
    return detail.reset_index(drop=True)


def add_prefix(detail: pd.DataFrame, column: str, prefix: str, audit: AuditLog) -> None:
    """Antepone el prefijo a cada valor no vacío de la columna (00153414 -> 656-00153414). Regla TRA-402.

    Las celdas vacías quedan vacías. Un valor que ya trae el prefijo no se repite.
    """
    def with_prefix(value: object) -> object:
        if is_empty(value):
            return value
        text = normalize_code(value)
        return text if text.startswith(prefix) else f"{prefix}{text}"

    detail[column] = detail[column].map(with_prefix)
    filled = int((~detail[column].map(is_empty)).sum())
    audit.transformation("TRA-402", f"{column}: prefijo «{prefix}» agregado a {filled} valores")


def assign_fixed_values(detail: pd.DataFrame, audit: AuditLog) -> None:
    """Asigna a todos los registros el valor fijo de cada columna de FIXED_VALUES. Regla TRA-405.

    Son los valores que tienen todos los registros del Detalle de pago (por ejemplo, la
    fiduciaria FIDUPREVISORA y el GL 656).
    """
    for column, value in FIXED_VALUES.items():
        detail[column] = [value] * len(detail)
    values = ", ".join(f"{column} = {_shown(value)}" for column, value in FIXED_VALUES.items())
    audit.transformation("TRA-405", f"Valores fijos en {len(detail)} registros: {values}")


def assign_from_subtrust(detail: pd.DataFrame, relation: dict, audit: AuditLog, current_pac: str) -> None:
    """Llena la columna con el valor que le corresponde al SUBFIDEICOMISO de cada registro,
    según su relación (SUBTRUST_RELATIONS). Reglas TRA-407 (NOMBRE_SUBFIDEICOMISO_PAGO),
    TRA-408 (RECURSOS) y TRA-406 (FUENTE_DE_RECURSOS).

    Si la relación tiene excepción por Programa (program_values) y el PROGRAMA del registro
    está en ella, prevalece el valor del Programa (RECURSOS y FUENTE_DE_RECURSOS).

    La marca CURRENT_PAC de las relaciones se reemplaza por `current_pac`, el PAC vigente que
    escribe el usuario al procesar, para no tener que cambiar el código cuando cambia el PAC.

    El Subfideicomiso se compara como código (1002 y «1002» son el mismo). Si no está en
    la relación o está vacío, la celda queda vacía y el log lo indica con ✗, para que el
    usuario la complete; no detiene el proceso.
    """
    column, rule, values = relation["column"], relation["rule"], relation["values"]
    program_values = relation.get("program_values", {})
    subtrusts = detail[SUBTRUST_COLUMN].map(normalize_code)
    programs = detail[PROGRAM_COLUMN].map(normalize_code)
    by_program = programs.map(lambda code: code in program_values)
    assigned = [
        program_values[program] if program in program_values else values.get(subtrust)
        for program, subtrust in zip(programs, subtrusts)
    ]
    assigned = [current_pac if value == CURRENT_PAC else value for value in assigned]
    # dtype=object: los vacíos quedan como None, sin que pandas los convierta en NaN.
    detail[column] = pd.Series(assigned, index=detail.index, dtype=object)
    missing = detail[column].map(is_empty)
    detail_text = f"{column} asignada en {int((~missing).sum())} de {len(detail)} registros"
    if program_values:
        detail_text += f" ({int(by_program.sum())} por la excepción de {PROGRAM_COLUMN})"
    audit.transformation(rule, detail_text)
    audit.note(audit.step_summary())
    if missing.any():
        unknown = ["(vacío)" if is_empty(code) else code for code in dict.fromkeys(subtrusts[missing])]
        shown = ", ".join(unknown[:MAX_SUBTRUSTS_IN_NOTE])
        if len(unknown) > MAX_SUBTRUSTS_IN_NOTE:
            shown += f" y {len(unknown) - MAX_SUBTRUSTS_IN_NOTE} más"
        audit.note(
            f"[{rule}] {int(missing.sum())} registros sin {column}: el {SUBTRUST_COLUMN} "
            f"no está en la relación o está vacío ({shown}). Complételos manualmente",
            ok=False,
        )


def assign_generation_year(detail: pd.DataFrame, year: int, audit: AuditLog) -> None:
    """RANGO: el año en que se genera el archivo, igual en todos los registros. Regla TRA-411.

    El año se recibe como parámetro (process() pasa el de la fecha actual) para que las
    pruebas no dependan del día en que se ejecutan.
    """
    detail[GENERATION_YEAR_COLUMN] = [year] * len(detail)
    audit.transformation("TRA-411", f"{GENERATION_YEAR_COLUMN} = {year} (año de generación) en {len(detail)} registros")


def assign_weekly_report(detail: pd.DataFrame, week: str, audit: AuditLog) -> None:
    """INFORME_SEMANAL: el número de la semana que escribe el usuario, igual en todos los
    registros. Regla TRA-415. Se escribe como texto para conservar los ceros a la izquierda
    (0010); el ejecutor ya verificó que no esté vacío."""
    detail[WEEKLY_REPORT_COLUMN] = [week] * len(detail)
    audit.transformation("TRA-415", f"{WEEKLY_REPORT_COLUMN} = {week} en {len(detail)} registros")


def assign_payment_type(detail: pd.DataFrame, audit: AuditLog) -> None:
    """TIPO_DE_PAGO y NO_BENEFICIARIOS según CONCEPTO. Regla TRA-412.

    Si CONCEPTO contiene BENEF_<número>_ (BENEF_14_), el pago es MASIVO y NO_BENEFICIARIOS
    es ese número (14). Si no la contiene, o el número es 1 (BENEF_1_: un solo
    beneficiario), INDIVIDUAL y 1.
    """
    pattern = re.compile(rf"{re.escape(BENEFICIARIES_PREFIX)}(\d+)_")
    types, beneficiaries = [], []
    for concept in detail[CONCEPT_COLUMN]:
        match = pattern.search("" if is_empty(concept) else str(concept))
        count = int(match.group(1)) if match else INDIVIDUAL_BENEFICIARIES
        types.append(INDIVIDUAL_PAYMENT if count == INDIVIDUAL_BENEFICIARIES else MASS_PAYMENT)
        beneficiaries.append(count)
    detail[PAYMENT_TYPE_COLUMN] = pd.Series(types, index=detail.index, dtype=object)
    detail[BENEFICIARIES_COLUMN] = pd.Series(beneficiaries, index=detail.index, dtype=object)
    mass = types.count(MASS_PAYMENT)
    audit.transformation(
        "TRA-412",
        f"{PAYMENT_TYPE_COLUMN}: {mass} {MASS_PAYMENT} ({BENEFICIARIES_PREFIX}<número>_ en {CONCEPT_COLUMN}, "
        f"con más de {INDIVIDUAL_BENEFICIARIES} beneficiario) y {len(types) - mass} {INDIVIDUAL_PAYMENT} "
        f"(con {INDIVIDUAL_BENEFICIARIES} en {BENEFICIARIES_COLUMN})",
    )


def assign_billing_period(detail: pd.DataFrame, audit: AuditLog) -> None:
    """PERIODO_DE_COBRO según los meses que menciona CONCEPTO. Regla TRA-414.

    Se escribe el texto calculado (no una fórmula de Excel). Si CONCEPTO no menciona ningún
    mes, o no trae año y FECHA_DE_PAGO está vacía, la celda queda vacía y el log lo indica
    con ✗, para que el usuario la complete.
    """
    values = []
    year_from_payment_date = 0
    for concept, payment_date in zip(detail[CONCEPT_COLUMN], detail[PAYMENT_DATE_COLUMN]):
        period, from_payment_date = billing_period(concept, payment_date)
        values.append(period)
        year_from_payment_date += from_payment_date
    detail[PERIOD_COLUMN] = pd.Series(values, index=detail.index, dtype=object)
    missing = detail[PERIOD_COLUMN].map(is_empty)
    detail_text = f"{PERIOD_COLUMN} asignado en {int((~missing).sum())} de {len(detail)} registros"
    if year_from_payment_date:
        detail_text += f" ({year_from_payment_date} con el año de {PAYMENT_DATE_COLUMN}, porque {CONCEPT_COLUMN} no lo trae)"
    audit.transformation("TRA-414", detail_text)
    audit.note(audit.step_summary())
    if missing.any():
        audit.note(
            f"[TRA-414] {int(missing.sum())} registros sin {PERIOD_COLUMN}: {CONCEPT_COLUMN} no menciona "
            f"ningún mes (o no trae año y {PAYMENT_DATE_COLUMN} está vacía). Complételos manualmente",
            ok=False,
        )


def billing_period(concept: object, payment_date: object) -> tuple[str | None, bool]:
    """Periodo de cobro de un CONCEPTO («Febrero de 2026» o «Febrero a Marzo de 2026»).

    Devuelve el periodo (None si no se encuentra ningún mes o ningún año) y si el año se
    tomó de FECHA_DE_PAGO.
    1. Toma CONCEPTO hasta «AUTORIZACION», sin mayúsculas ni tildes, y cambia los
       separadores (_ - * ' / . ,) por espacios.
    2. Busca cada mes por su nombre completo al inicio de una palabra (« febrero») o por su
       abreviatura suelta (« feb »). El mes inicial es el que aparece primero y el final, el
       que aparece último (cada mes se ubica por su primera aparición).
    3. El año es el primer número 20xx después del mes final; si no hay, el de FECHA_DE_PAGO.
    """
    text = comparable_text(concept)
    end = text.find(comparable_text(PERIOD_END_MARKER))
    if end >= 0:
        text = text[:end]
    for separator in PERIOD_SEPARATORS:
        text = text.replace(separator, " ")
    positions = {}
    for month in MONTHS:
        name = comparable_text(month)
        # Palabra completa: sin letras pegadas antes ni después (sí números, como en «julio2026»).
        words = f"{name}|{name[:MONTH_ABBREVIATION_LENGTH]}"
        match = re.search(rf"(?<![a-z])({words})(?![a-z])", text)
        if match:
            positions[month] = match.start()
    if not positions:
        return None, False
    start = min(positions, key=positions.get)
    last = max(positions, key=positions.get)
    year_match = re.search(PERIOD_YEAR_PATTERN, text[positions[last]:])
    from_payment_date = year_match is None
    if year_match:
        year = year_match.group()
    elif hasattr(payment_date, "year") and not is_empty(payment_date):
        year = str(payment_date.year)
    else:
        return None, False
    template = PERIOD_SINGLE_MONTH if start == last else PERIOD_MONTH_RANGE
    return template.format(start=start, end=last, year=year), from_payment_date


def _shown(value: object) -> str:
    """Valor para el log: los textos entre comillas («1») para distinguirlos de los números (1)."""
    return f"«{value}»" if isinstance(value, str) else str(value)


def add_formula(detail: pd.DataFrame, formula: dict, audit: AuditLog) -> None:
    """Escribe en cada fila la fórmula de Excel de la columna (FORMULA_COLUMNS y
    FORMULA_COLUMNS_AFTER_VALIDITY). Reglas TRA-403, TRA-404 y TRA-410.

    openpyxl no calcula fórmulas: el resultado aparece al abrir el archivo en Excel.
    - VALIDACION: la fórmula de Diferencia del ETY, porque su resultado no queda guardado
      en el archivo y no se puede copiar.
    - CONTRATO: la fórmula del Detalle de pago, que toma el número de contrato de CONCEPTO.
    - CONTRATO_2: la fórmula del Detalle de pago, que une CONTRATO y VIGENCIA.
    """
    column = formula["column"]
    detail[column] = [ExcelFormula(formula["formula"], formula["format"])] * len(detail)
    audit.transformation(formula["rule"], f"{column}: fórmula de Excel en {len(detail)} filas")


def assign_validity(detail: pd.DataFrame, audit: AuditLog) -> None:
    """VIGENCIA según el CONTRATO y el CONCEPTO de cada registro. Regla TRA-409.

    Si el CONTRATO es un número, la vigencia es el número que sigue a
    «CONTRATO_<número>-» en CONCEPTO (CONTRATO_1345-2025 -> 2025). Si el CONTRATO está
    vacío o no es un número, o CONCEPTO no tiene esa expresión, VIGENCIA queda vacía.
    """
    values = []
    not_number = not_found = 0
    for concept in detail[CONCEPT_COLUMN]:
        text = "" if is_empty(concept) else str(concept)
        contract = contract_number(text)
        if contract is None or not contract.isdigit():
            not_number += 1
            values.append(None)
            continue
        match = re.search(rf"{re.escape(CONTRACT_PREFIX)}{re.escape(contract)}-(\d+)", text)
        if match is None:
            not_found += 1
        values.append(int(match.group(1)) if match else None)
    detail[VALIDITY_COLUMN] = pd.Series(values, index=detail.index, dtype=object)
    assigned = len(detail) - not_number - not_found
    detail_text = (
        f"{VALIDITY_COLUMN} asignada en {assigned} de {len(detail)} registros; "
        f"vacía en {not_number} porque el {CONTRACT_WORD} está vacío o no es un número"
    )
    if not_found:
        detail_text += f" y en {not_found} porque {CONCEPT_COLUMN} no tiene la expresión {CONTRACT_PREFIX}<número>-<vigencia>"
    audit.transformation("TRA-409", detail_text)


def assign_contract_by_concept(detail: pd.DataFrame, audit: AuditLog) -> None:
    """CONTRATO según CONCEPTO en los registros donde su fórmula da #¡VALOR!. Regla TRA-413.

    Si CONCEPTO contiene uno de los términos de CONTRACT_BY_CONCEPT, el valor reemplaza la
    fórmula (cada cambio queda en Acciones). Si no, la fórmula se conserva y Excel sigue
    mostrando #¡VALOR!, para que el usuario lo ajuste; el log lo indica con ✗.
    """
    error_rows = assigned = 0
    for index, concept in detail[CONCEPT_COLUMN].items():
        text = "" if is_empty(concept) else str(concept)
        if contract_number(text) is not None:
            continue    # La fórmula encuentra el contrato: no es #¡VALOR!
        error_rows += 1
        value = contract_by_concept(text)
        if value is None:
            continue
        assigned += 1
        detail.at[index, CONTRACT_COLUMN] = value
        audit.change(
            detail.at[index, SOURCE_FILE], detail.at[index, SOURCE_ROW], CONTRACT_COLUMN,
            CONTRACT_ERROR, value, "TRA-413",
        )
    audit.note(
        f"{CONTRACT_COLUMN} da {CONTRACT_ERROR} en {error_rows} de {len(detail)} registros; "
        f"asignado según {CONCEPT_COLUMN} en {assigned}"
    )
    if error_rows > assigned:
        audit.note(
            f"[TRA-413] {error_rows - assigned} registros siguen con {CONTRACT_ERROR}: {CONCEPT_COLUMN} "
            f"no contiene ninguno de los términos. Ajústelos manualmente",
            ok=False,
        )


def contract_by_concept(concept: str) -> str | None:
    """Valor de CONTRATO para el término de CONTRACT_BY_CONCEPT que contiene CONCEPTO.

    Compara sin mayúsculas ni tildes (comparable_text), conservando «_» y espacios. Si
    contiene varios términos, gana el más largo; con el mismo largo, el primero de la lista.
    """
    text = comparable_text(concept)
    found = [term for term in CONTRACT_BY_CONCEPT if comparable_text(term) in text]
    if not found:
        return None
    longest = max(found, key=lambda term: len(comparable_text(term)))
    return CONTRACT_BY_CONCEPT[longest]


def contract_number(concept: str) -> str | None:
    """El resultado de la fórmula de CONTRATO del Detalle de pago para ese CONCEPTO.

    Repite los pasos de la fórmula de Excel (FORMULA_COLUMNS), porque la herramienta no
    calcula fórmulas y VIGENCIA depende del resultado:
    1. Busca «CONTRATO» sin distinguir mayúsculas (SEARCH); si no está, la fórmula da
       #¡VALOR! y aquí se devuelve None.
    2. Desde ahí, cambia espacios, «/» y «-» por «_» y quita «CONTRATO_» (SUBSTITUTE,
       que sí distingue mayúsculas).
    3. Toma el texto hasta el siguiente «_»; si no hay, la fórmula da #¡VALOR! (None).
    """
    start = concept.upper().find(CONTRACT_WORD.upper())
    if start < 0:
        return None
    text = concept
    for separator in CONTRACT_SEPARATORS:
        text = text.replace(separator, "_")
    text = text[start:].replace(CONTRACT_PREFIX, "")
    end = text.find("_")
    return text[:end] if end >= 0 else None


def write_as_numbers(detail: pd.DataFrame, column: str, audit: AuditLog) -> None:
    """Escribe como número los valores de la columna que el ETY trae como texto. Regla TRA-402.

    El valor que se ve no cambia (1085283965 sigue siendo 1085283965); solo deja de
    ser texto, para que Excel lo reconozca como número. Los valores con otros caracteres
    o con ceros a la izquierda se dejan como texto y se cuentan en el log.
    """
    numbers = detail[column].map(as_number)
    converted = numbers.map(lambda v: isinstance(v, int)) & detail[column].map(lambda v: isinstance(v, str))
    detail[column] = numbers
    kept = detail[column].map(lambda v: isinstance(v, str))
    audit.transformation(
        "TRA-402",
        f"{column}: {int(converted.sum())} valores escritos como número"
        + (f"; {int(kept.sum())} quedan como texto (tienen otros caracteres o ceros a la izquierda)" if kept.any() else ""),
    )


def as_number(value: object) -> object:
    """El texto como número entero si tiene solo dígitos y no empieza por cero; si no, el mismo valor."""
    if isinstance(value, str) and value.isdigit() and value.isascii() and not value.startswith("0"):
        return int(value)
    return value


def add_budget_sources(detail: pd.DataFrame, budget: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Columna con las fuentes de recursos de la Ejecución presupuestal. Regla VAL-401.

    La Ejecución presupuestal es opcional: si no se cargó (o no tiene registros), no se
    agrega la columna y el log lo indica. Si se cargó, por cada registro con CONTRATO
    numérico se buscan los registros de la Ejecución presupuestal del mismo contrato (el año
    no cuenta) con PENDIENTE POR PAGAR mayor que 0. Si hay más de uno, aunque sean de la
    misma fuente, la celda indica cuántos hay de cada fuente («PGN: 2, OTROS: 1»); con uno o
    ninguno queda vacía (solo se cuenta en el log).
    """
    if budget.empty:
        audit.note("No se cargó la Ejecución presupuestal: no se hace esta validación")
        return detail
    sources = pending_sources(budget)
    values, contracts = [], []
    without_contract = not_found = single = 0
    for concept in detail[CONCEPT_COLUMN]:
        contract = contract_number("" if is_empty(concept) else str(concept))
        if contract is None or not contract.isdigit():
            without_contract += 1
            values.append(None)
            continue
        counts = sources.get(_contract_key(contract), {})
        records = sum(counts.values())
        if records < MIN_BUDGET_RECORDS:
            not_found += records == 0
            single += records == 1
            values.append(None)
            continue
        contracts.append(_contract_key(contract))
        values.append(SOURCES_SEPARATOR.join(
            SOURCE_COUNT.format(source=source, count=count) for source, count in counts.items()
        ))
    detail[BUDGET_SOURCES_COLUMN] = pd.Series(values, index=detail.index, dtype=object)
    audit.column_added(BUDGET_SOURCES_COLUMN, "VAL-401", len(contracts))
    audit.note(
        f"{BUDGET_SOURCES_COLUMN} asignada en {len(contracts)} de {len(detail)} registros (contrato con "
        f"más de un registro con {BUDGET_PENDING_COLUMN} mayor que 0); vacía en {single} con un solo "
        f"registro, en {not_found} sin registros y en {without_contract} sin {CONTRACT_COLUMN} numérico"
    )
    if contracts:
        unique = list(dict.fromkeys(contracts))
        shown = ", ".join(unique[:MAX_CONTRACTS_IN_NOTE])
        if len(unique) > MAX_CONTRACTS_IN_NOTE:
            shown += f" y {len(unique) - MAX_CONTRACTS_IN_NOTE} más"
        audit.note(
            f"[VAL-401] {len(contracts)} registros cuyo contrato tiene más de un registro pendiente por "
            f"pagar en la Ejecución presupuestal ({len(unique)} contratos: {shown}). Revíselos",
            ok=False,
        )
    return detail


def pending_sources(budget: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Número de registros de la Ejecución presupuestal con PENDIENTE POR PAGAR mayor que 0,
    por contrato y fuente de recursos, en el orden en que aparecen. Regla VAL-401.

    El año del contrato no se tiene en cuenta. Un PENDIENTE POR PAGAR vacío o que no es un
    número no cuenta.
    """
    sources: dict[str, dict[str, int]] = {}
    for contract, pending, source in zip(
        budget[BUDGET_CONTRACT_COLUMN], budget[BUDGET_PENDING_COLUMN], budget[BUDGET_SOURCE_COLUMN],
    ):
        try:
            amount = parse_number(pending)
        except ValueError:
            continue
        if amount is None or amount <= 0 or is_empty(contract):
            continue
        counts = sources.setdefault(_contract_key(contract), {})
        text = BUDGET_EMPTY_SOURCE if is_empty(source) else clean_text(str(source)) or BUDGET_EMPTY_SOURCE
        counts[text] = counts.get(text, 0) + 1
    return sources


def _contract_key(value: object) -> str:
    """Contrato para comparar: como código, sin ceros a la izquierda si es un número
    (303, 303.0, «303» y «0303» son el mismo contrato) y sin mayúsculas si tiene letras."""
    text = normalize_code(value) or ""
    return str(int(text)) if text.isdigit() and text.isascii() else text.upper()
