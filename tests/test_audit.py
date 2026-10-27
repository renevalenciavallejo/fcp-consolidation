import pandas as pd
import pytest

from core.audit import AuditLog
from core.rules import COMMON_RULES
from core.settings import ERROR, SOURCE_FILE, SOURCE_ROW, WARNING


def test_unknown_rule_is_rejected():
    audit = AuditLog(COMMON_RULES)
    with pytest.raises(ValueError):
        audit.change("a.xlsx", 2, "A", "x", "y", "XXX-999")


def test_unknown_severity_is_rejected():
    audit = AuditLog(COMMON_RULES)
    with pytest.raises(ValueError):
        audit.finding("a.xlsx", 2, "A", "Grave", "TIP-001", "d", "v", "a")


def test_counts_and_tables():
    audit = AuditLog(COMMON_RULES)
    audit.change("a.xlsx", 2, "A", " x", "x", "LIM-001")
    audit.finding("a.xlsx", 3, "B", ERROR, "TIP-001", "No es número", "abc", "Corregir")
    audit.removal("a.xlsx", 4, "LIM-002", "Fila sin datos", {"A": None, "B": float("nan")})

    assert audit.findings_by_severity()[ERROR] == 1
    assert audit.rule_counts() == {"LIM-001": 1, "LIM-002": 1, "TIP-001": 1}
    assert audit.changes_df().iloc[0]["Descripción de la regla"] == COMMON_RULES["LIM-001"]
    removals = audit.removals_df()
    assert list(removals.columns) == ["Archivo origen", "Fila origen", "Código de regla", "Motivo", "A", "B"]
    assert removals.iloc[0]["B"] is None  # NaN se normaliza a vacío


def test_change_column_detects_type_changes():
    audit = AuditLog(COMMON_RULES)
    df = pd.DataFrame({"A": ["1", "2"], SOURCE_FILE: "a.xlsx", SOURCE_ROW: [2, 3]}, dtype=object)
    audit.change_column(df, "A", pd.Series(["1", 2], dtype=object), "TIP-001")
    assert [c.source_row for c in audit.changes] == [3]


def test_remove_rows_with_reason_per_row():
    audit = AuditLog(COMMON_RULES)
    df = pd.DataFrame({"A": ["x", "y"], SOURCE_FILE: "a.xlsx", SOURCE_ROW: [2, 3]}, dtype=object)
    mask = pd.Series([True, False])
    result = audit.remove_rows(df, mask, "DUP-001", pd.Series(["motivo x", "motivo y"]))
    assert list(result["A"]) == ["y"]
    assert audit.removals[0].reason == "motivo x"
    assert audit.removals[0].row_data == {"A": "x"}  # Sin columnas internas


def test_step_result_summarizes_what_was_registered():
    lines = []
    audit = AuditLog(COMMON_RULES, on_line=lines.append)
    audit.step("Primer paso")
    audit.change("a.xlsx", 2, "A", " x", "x", "LIM-001")
    audit.change("a.xlsx", 2, "A", "x", "y", "LIM-001")  # Misma celda: cuenta una vez
    audit.finding("a.xlsx", 3, "B", ERROR, "TIP-001", "d", "v", "a")
    audit.finding("a.xlsx", 4, "B", WARNING, "TIP-001", "d", "v", "a")
    audit.removal("a.xlsx", 5, "LIM-002", "Fila sin datos", {})
    audit.step("Paso sin registros")
    audit.finish_step()
    assert lines == [
        "▸ Primer paso",
        "   ✓ 1 fila eliminada: fila 5 · 1 celda modificada · 2 hallazgos (1 Error, 1 Advertencia)",
        "▸ Paso sin registros",
        "   ✓ Sin cambios",
    ]
    assert audit.step_lines() == lines


def test_step_with_notes_is_not_summarized():
    audit = AuditLog(COMMON_RULES)
    audit.step("Validando")
    audit.note("Problema", ok=False)
    audit.removal("a.xlsx", 5, "LIM-002", "Fila sin datos", {})
    audit.finish_step()
    assert audit.steps[0].details == ["✗ Problema"]


def test_note_without_step_is_rejected():
    with pytest.raises(ValueError):
        AuditLog(COMMON_RULES).note("x")


def test_removed_rows_list_is_truncated_and_grouped_by_file():
    audit = AuditLog(COMMON_RULES)
    audit.multiple_files = True
    audit.step("Eliminando")
    for row in range(2, 15):
        audit.removal("a.xlsx", row, "LIM-002", "Fila sin datos", {})
    audit.removal("b.xlsx", 7, "LIM-002", "Fila sin datos", {})
    audit.finish_step()
    assert audit.steps[0].details == [
        "✓ 14 filas eliminadas: a.xlsx: filas 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 y 3 más; b.xlsx: fila 7"
    ]


def test_added_columns_and_transformations_in_step_result():
    audit = AuditLog({**COMMON_RULES, "TRA-901": "Prueba"})
    audit.step("Calculando")
    audit.column_added("Total", "TRA-901", 3)
    audit.transformation("TRA-901", "Registros ordenados por A (3 registros)")
    audit.finish_step()
    assert audit.steps[0].details == [
        "✓ Columna «Total» agregada en 3 filas · Registros ordenados por A (3 registros)"
    ]


def test_steps_df():
    audit = AuditLog(COMMON_RULES)
    audit.step("Uno")
    audit.note("a")
    audit.note("b", ok=False)
    audit.step("Dos")
    audit.finish_step()
    table = audit.steps_df()
    assert list(table.columns) == ["Paso", "Resultado"]
    assert table.values.tolist() == [["Uno", "✓ a"], ["Uno", "✗ b"], ["Dos", "✓ Sin cambios"]]


def test_actions_follow_the_order_in_which_they_happened():
    audit = AuditLog({**COMMON_RULES, "TRA-901": "Prueba"})
    audit.step("Limpiando")
    audit.removal("a.xlsx", 4, "LIM-002", "Fila sin datos", {"A": None})
    audit.change("a.xlsx", 2, "A", "1.234,5", 1234.5, "TIP-001")
    audit.step("Validando")
    audit.finding("a.xlsx", 3, "B", ERROR, "TIP-001", "No es número", "abc", "Corregir")
    audit.step("Calculando")
    audit.column_added("Total", "TRA-901", 2)
    audit.transformation("TRA-901", "Registros ordenados por A (2 registros)")
    table = audit.actions_df()
    # Con un solo archivo no se muestra la columna Archivo; al final van las columnas del registro.
    assert list(table.columns) == ["Paso", "Fila", "Acción", "Columna", "Detalle", "Qué hacer", "Regla", "A"]
    assert table[["Paso", "Acción", "Detalle"]].values.tolist() == [
        ["Limpiando", "Fila eliminada", "Fila sin datos"],
        ["Limpiando", "Valor modificado", "«1.234,5» → 1234.5"],
        ["Validando", "Hallazgo (Error)", "No es número. Valor: «abc»"],
        ["Calculando", "Columna agregada", "Columna «Total» agregada en 2 filas"],
        ["Calculando", "Transformación", "Registros ordenados por A (2 registros)"],
    ]
    assert table.iloc[2]["Qué hacer"] == "Corregir"
    assert table.iloc[0]["Fila"] == 4
    assert table.iloc[3]["Fila"] == ""  # Las acciones sobre toda la tabla no tienen fila


def test_actions_show_empty_and_date_values():
    from datetime import datetime

    audit = AuditLog(COMMON_RULES)
    audit.change("a.xlsx", 2, "A", "05/03/2024", datetime(2024, 3, 5), "TIP-002")
    audit.change("a.xlsx", 3, "A", "   ", None, "LIM-001")
    details = audit.actions_df()["Detalle"].tolist()
    assert details == ["«05/03/2024» → 05/03/2024", "«   » → (vacío)"]
    assert audit.actions_df()["Paso"].tolist() == ["", ""]  # Sin paso abierto


def test_actions_show_the_whole_record():
    audit = AuditLog(COMMON_RULES)
    df = pd.DataFrame(
        {"A": ["1.234,5", "x"], "B": ["uno", "dos"], SOURCE_FILE: "a.xlsx", SOURCE_ROW: [2, 3]}, dtype=object
    )
    audit.remember_source_rows(df)
    audit.change("a.xlsx", 2, "A", "1.234,5", 1234.5, "TIP-001")
    audit.removal("a.xlsx", 3, "LIM-002", "Motivo", {"A": "x", "B": "dos"})
    table = audit.actions_df()
    assert list(table.columns)[-2:] == ["A", "B"]
    # El registro original del archivo, tal como se leyó (el cambio se ve en Detalle).
    assert table.iloc[0][["A", "B"]].tolist() == ["1.234,5", "uno"]
    assert table.iloc[1][["A", "B"]].tolist() == ["x", "dos"]


def test_actions_show_file_only_with_several_files():
    audit = AuditLog(COMMON_RULES)
    audit.multiple_files = True
    audit.removal("a.xlsx", 3, "LIM-002", "Motivo", {})
    table = audit.actions_df()
    assert list(table.columns)[:3] == ["Paso", "Archivo", "Fila"]
    assert table.iloc[0]["Archivo"] == "a.xlsx"


def test_actions_show_the_record_as_it_was_read():
    df = pd.DataFrame({"Codigo": ["007", "8"], "Valor": [1, 2], SOURCE_FILE: ["a.xlsx"] * 2, SOURCE_ROW: [2, 3]})
    audit = AuditLog(COMMON_RULES)
    audit.remember_source_rows(df)
    df.loc[0, "Valor"] = 99   # La etapa cambia la tabla después de leerla
    audit.step("Paso")
    audit.finding("a.xlsx", 2, "Valor", WARNING, "LIM-001", "Revisar", 99, "")
    row = audit.actions_df().iloc[0]
    assert (row["Codigo"], row["Valor"]) == ("007", 1)
    assert audit.source_row("a.xlsx", 9) == {}
