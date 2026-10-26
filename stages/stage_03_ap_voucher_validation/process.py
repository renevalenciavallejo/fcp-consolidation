"""Lógica de la Etapa 3 - Cruce con el AP Voucher.

La validación de estructura la hace el ejecutor antes de llamar a process(): el
reporte ETY procesado en la Etapa 2 y el archivo AP Voucher. Aquí van las reglas
propias de la etapa, en el orden de ESPECIFICACION.md.
"""

from dataclasses import dataclass

import pandas as pd

from core.audit import AuditLog
from core.cleaning import comparable_text, normalize_code
from core.settings import SOURCE_FILE, SOURCE_ROW, WARNING
from stages.stage_03_ap_voucher_validation.config import (
    AP_VOUCHER_CHECKS,
    AP_VOUCHER_COLUMN,
    ETY_VOUCHER_COLUMN,
    MAX_ROWS_IN_DETAIL,
    MAX_VOUCHERS_IN_NOTE,
)


@dataclass
class CheckResult:
    """Resultado de una búsqueda en el AP Voucher (por ejemplo, la de comprobantes cerrados)."""

    check: dict               # La búsqueda, tal como está en AP_VOUCHER_CHECKS
    selected: int             # Registros del AP Voucher con el valor buscado
    distinct: int             # Comprobantes distintos entre esos registros
    found: pd.DataFrame       # Registros del ETY cuyo comprobante está entre ellos


def process(inputs: dict[str, pd.DataFrame], audit: AuditLog) -> pd.DataFrame:
    # El AP Voucher solo se consulta en memoria: el reporte ETY sale sin cambios y los
    # comprobantes encontrados quedan como hallazgos para la revisión manual.
    ety = inputs["ety_processed"]
    check_ap_voucher(ety, inputs["ap_voucher"], audit)
    return ety


def result_notice(audit: AuditLog) -> list[str]:
    """Notificación con los resultados del procesamiento (RESULT_NOTICE en __init__.py).

    Por cada búsqueda, los registros del ETY encontrados y el color con que se resaltan
    en el archivo de salida, como sublista (las líneas con dos espacios van dentro de la
    anterior). Si son muchos, se listan los primeros y los demás se cuentan (todos están
    en Acciones).
    """
    lines = []
    for check in AP_VOUCHER_CHECKS:
        found = [f for f in audit.findings if f.rule == check["rule"]]
        title = (
            f"{check['state'].capitalize()}s en el AP Voucher ({check['column']} «{check['value']}»), "
            f"resaltados en {check['color']}"
        )
        if not found:
            lines.append(f"{title}: ninguno")
            continue
        lines.append(f"{title}: {_vouchers(len(found))}")
        for finding in found[:MAX_VOUCHERS_IN_NOTE]:
            lines.append(f"  {normalize_code(finding.value)} (fila {finding.source_row} del reporte ETY)")
        hidden = len(found) - MAX_VOUCHERS_IN_NOTE
        if hidden > 0:
            lines.append(f"  y {hidden} más (ver «Acciones realizadas»)")
    return lines


def check_ap_voucher(ety: pd.DataFrame, ap_voucher: pd.DataFrame, audit: AuditLog) -> list[CheckResult]:
    """Hace cada búsqueda de AP_VOUCHER_CHECKS, en orden, cada una en su paso del log."""
    results = []
    for check in AP_VOUCHER_CHECKS:
        audit.step(f"Buscando comprobantes del reporte ETY con {check['column']} «{check['value']}» en el AP Voucher")
        results.append(flag_vouchers_in_ap_voucher(ety, ap_voucher, check, audit))
    return results


def ap_voucher_rows(ap_voucher: pd.DataFrame, column: str, value: str) -> dict[str, list[int]]:
    """Comprobantes únicos del AP Voucher con ese valor en la columna, y sus filas en el archivo.

    El valor se compara sin distinguir mayúsculas, tildes ni espacios sobrantes, y el
    comprobante como código, para que «00132345» y « 00132345 » sean el mismo.
    """
    selected = ap_voucher[ap_voucher[column].map(comparable_text) == comparable_text(value)]
    rows: dict[str, list[int]] = {}
    for voucher, row in zip(selected[AP_VOUCHER_COLUMN].map(normalize_code), selected[SOURCE_ROW]):
        if voucher is not None:
            rows.setdefault(voucher, []).append(int(row))
    return rows


def flag_vouchers_in_ap_voucher(
    ety: pd.DataFrame, ap_voucher: pd.DataFrame, check: dict, audit: AuditLog
) -> CheckResult:
    """Señala los registros del ETY cuyo comprobante tiene ese estado en el AP Voucher. Reglas VAL-301 y VAL-302.

    Cada registro encontrado queda como Advertencia en su Comprobante (se resalta en la
    salida con el color de la regla y aparece en Acciones), sin detener el proceso: el
    usuario hace la verificación manual.
    """
    rows = ap_voucher_rows(ap_voucher, check["column"], check["value"])
    selected = sum(len(r) for r in rows.values())
    audit.note(
        f"AP Voucher: {_records(selected)} con {check['column']} «{check['value']}» "
        f"({_vouchers(len(rows))} {_distinct(len(rows))})"
    )
    vouchers = ety[ETY_VOUCHER_COLUMN].map(normalize_code)
    found = ety[vouchers.isin(list(rows))]
    result = CheckResult(check, selected, len(rows), found)
    state = check["state"]
    if found.empty:
        audit.note(f"Ningún comprobante del reporte ETY está {state} en el AP Voucher")
        return result

    unique = list(dict.fromkeys(vouchers[found.index]))
    verb = "está" if len(unique) == 1 else "están"
    audit.note(
        f"[{check['rule']}] {_vouchers(len(unique))} del reporte ETY {verb} {_state(state, len(unique))} "
        f"en el AP Voucher: {_list_text(unique)}",
        ok=False,
    )
    ap_name = ap_voucher[SOURCE_FILE].iloc[0]
    for index, row in found.iterrows():
        audit.finding(
            row[SOURCE_FILE], row[SOURCE_ROW], ETY_VOUCHER_COLUMN, WARNING, check["rule"],
            f"El comprobante está con {check['column']} «{check['value']}» en el AP Voucher "
            f"(«{ap_name}», {_rows_text(rows[vouchers[index]])})",
            row[ETY_VOUCHER_COLUMN],
            f"Verifique el comprobante {state} en el AP Voucher",
        )
    return result


def _list_text(vouchers: list[str]) -> str:
    """Comprobantes separados por comas; si son muchos, se listan los primeros y los demás se cuentan."""
    shown = ", ".join(vouchers[:MAX_VOUCHERS_IN_NOTE])
    hidden = len(vouchers) - MAX_VOUCHERS_IN_NOTE
    return f"{shown} y {hidden} más (ver «Acciones realizadas»)" if hidden > 0 else shown


def _rows_text(rows: list[int]) -> str:
    shown = ", ".join(str(r) for r in rows[:MAX_ROWS_IN_DETAIL])
    hidden = len(rows) - MAX_ROWS_IN_DETAIL
    label = "fila" if len(rows) == 1 else "filas"
    return f"{label} {shown} y {hidden} más" if hidden > 0 else f"{label} {shown}"


def _state(state: str, count: int) -> str:
    """«cerrado» o «cerrados», según la cantidad."""
    return state if count == 1 else f"{state}s"


def _records(count: int) -> str:
    return f"{count} registro" if count == 1 else f"{count} registros"


def _vouchers(count: int) -> str:
    return f"{count} comprobante" if count == 1 else f"{count} comprobantes"


def _distinct(count: int) -> str:
    return "distinto" if count == 1 else "distintos"
