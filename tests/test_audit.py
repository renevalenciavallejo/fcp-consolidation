import pandas as pd
import pytest

from core.audit import AuditLog
from core.rules import COMMON_RULES
from core.settings import ERROR, SOURCE_FILE, SOURCE_ROW


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
