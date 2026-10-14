from datetime import datetime

import pandas as pd
import pytest

from core.audit import AuditLog
from core.cleaning import (
    clean_text,
    comparable_text,
    flag_repeated_values,
    sort_rows,
    convert_columns,
    normalize_code,
    parse_date,
    parse_number,
    remove_duplicates,
    remove_empty_rows,
    remove_extra_spaces,
    to_text,
)
from core.rules import COMMON_RULES
from core.settings import ERROR, SOURCE_FILE, SOURCE_ROW, WARNING


def make_df(rows: list[dict], file: str = "a.xlsx") -> pd.DataFrame:
    df = pd.DataFrame(rows, dtype=object)
    df[SOURCE_FILE] = file
    df[SOURCE_ROW] = range(2, len(df) + 2)
    return df


# --- clean_text ---------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("  Bogotá  ", "Bogotá"),
        ("Dos  espacios", "Dos espacios"),
        ("con\xa0nbsp", "con nbsp"),
        ("salto\nde\r\nlínea", "salto de línea"),
        ("invi​sible﻿", "invisible"),
        ("MAYÚSCULAS", "MAYÚSCULAS"),
        ("", ""),
        (None, None),
        (5, 5),
    ],
)
def test_clean_text(value, expected):
    assert clean_text(value) == expected


# --- parse_number -------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1.234.567,89", 1234567.89),
        ("1,234,567.89", 1234567.89),
        ("$ 1.000", 1000.0),
        ("$1,000.50", 1000.5),
        ("(500)", -500.0),
        ("-500", -500.0),
        ("500-", -500.0),
        ("-$ 1.500,25", -1500.25),
        ("45.000", 45000.0),
        ("1,5", 1.5),
        ("1234.5", 1234.5),
        ("0", 0.0),
        (1234, 1234.0),
        (12.5, 12.5),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_parse_number(value, expected):
    assert parse_number(value) == expected


@pytest.mark.parametrize("value", ["abc", "1.23.4", "12,34,5", "1.2.3,4", "--5", True])
def test_parse_number_invalid(value):
    with pytest.raises(ValueError):
        parse_number(value)


def test_zero_is_not_empty():
    assert parse_number("0") == 0.0
    assert parse_number("") is None


# --- parse_date ---------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("05/03/2024", datetime(2024, 3, 5)),  # Siempre día/mes
        ("5/3/2024", datetime(2024, 3, 5)),
        ("31/12/2024 14:30", datetime(2024, 12, 31, 14, 30)),
        ("2024-03-05", datetime(2024, 3, 5)),
        (datetime(2024, 3, 5), datetime(2024, 3, 5)),
        (45356, datetime(2024, 3, 5)),
        ("45356", datetime(2024, 3, 5)),
        ("", None),
        (None, None),
    ],
)
def test_parse_date(value, expected):
    assert parse_date(value) == expected


@pytest.mark.parametrize("value", ["31/02/2024", "05/03/24", "13/13/2024", "marzo", "0", "-5"])
def test_parse_date_invalid(value):
    with pytest.raises(ValueError):
        parse_date(value)


# --- normalize_code / to_text -------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [("007", "007"), ("7.0", "7"), (7, "7"), (7.0, "7"), (" A-01 ", "A-01"), ("", None), (None, None)],
)
def test_normalize_code(value, expected):
    assert normalize_code(value) == expected


def test_to_text_keeps_text_as_is():
    assert to_text("3.0") == "3.0"
    assert to_text(3.0) == "3"
    assert to_text(datetime(2024, 3, 5)) == "05/03/2024"


# --- Funciones de DataFrame -----------------------------------------------------


def test_remove_extra_spaces_logs_only_changed_cells():
    audit = AuditLog(COMMON_RULES)
    df = make_df([{"A": " x ", "B": "y"}, {"A": "   ", "B": None}])
    result = remove_extra_spaces(df, audit)
    assert list(result["A"]) == ["x", None]
    assert [(c.source_row, c.old_value, c.new_value) for c in audit.changes] == [(2, " x ", "x"), (3, "   ", None)]


def test_remove_empty_rows():
    audit = AuditLog(COMMON_RULES)
    df = make_df([{"A": "x"}, {"A": None}])
    result = remove_empty_rows(df, audit)
    assert len(result) == 1
    assert audit.removals[0].source_row == 3
    assert audit.removals[0].rule == "LIM-002"


def test_convert_columns_findings_and_changes():
    audit = AuditLog(COMMON_RULES)
    df = make_df(
        [
            {"Valor": "1.234,5", "Fecha": "05/03/2024", "Codigo": "007"},
            {"Valor": "1234", "Fecha": 45356, "Codigo": 7},
            {"Valor": "abc", "Fecha": "31/02/2024", "Codigo": None},
            {"Valor": "1,234", "Fecha": None, "Codigo": "8.0"},
        ]
    )
    result = convert_columns(df, {"Valor": "number", "Fecha": "date", "Codigo": "code"}, audit)

    assert list(result["Valor"]) == [1234.5, 1234.0, "abc", 1.234]  # Inválido se deja como estaba
    assert result.at[0, "Fecha"] == datetime(2024, 3, 5)
    assert list(result["Codigo"]) == ["007", "7", None, "8"]

    errors = [(f.source_row, f.column) for f in audit.findings if f.severity == ERROR]
    assert errors == [(4, "Valor"), (4, "Fecha")]
    warnings = [(f.source_row, f.column) for f in audit.findings if f.severity == WARNING]
    assert warnings == [(5, "Valor")]

    # Solo cambia lo que el usuario ve distinto: "1.234,5" y "1,234" sí; "1234" no.
    changed = {(c.source_row, c.column) for c in audit.changes}
    assert (2, "Valor") in changed and (5, "Valor") in changed
    assert (3, "Valor") not in changed
    assert (2, "Fecha") not in changed  # "05/03/2024" ya mostraba la misma fecha
    assert (3, "Fecha") in changed      # Serial de Excel -> fecha
    assert (5, "Codigo") in changed and (2, "Codigo") not in changed


def test_remove_duplicates_within_and_across_files():
    audit = AuditLog(COMMON_RULES)
    a = make_df([{"K": "1"}, {"K": "2"}, {"K": "1"}], file="a.xlsx")
    b = make_df([{"K": "2"}, {"K": "3"}], file="b.xlsx")
    df = pd.concat([a, b], ignore_index=True)
    result = remove_duplicates(df, ["K"], audit)

    assert list(result["K"]) == ["1", "2", "3"]
    removed = [(r.source_file, r.source_row, r.reason) for r in audit.removals]
    assert removed == [
        ("a.xlsx", 4, "Duplicado del registro en a.xlsx, fila 2"),
        ("b.xlsx", 2, "Duplicado del registro en a.xlsx, fila 3"),
    ]


def test_comparable_text():
    assert comparable_text(" Distribucion  CAJA ") == comparable_text("Distribución Caja")
    assert comparable_text("Cuentas a Pagar") != comparable_text("Distribución Caja")
    assert comparable_text(None) == ""


def test_flag_repeated_values_ignores_empties_and_compares_as_codes():
    rules = {**COMMON_RULES, "VAL-900": "prueba"}
    audit = AuditLog(rules)
    df = make_df([{"C": "001"}, {"C": " 001 "}, {"C": "002"}, {"C": None}, {"C": None}, {"C": "001"}])
    flag_repeated_values(df, "C", audit, "VAL-900", WARNING, "Revisar")
    assert [f.source_row for f in audit.findings] == [2, 3, 7]
    assert audit.findings[0].description == "C repetido en 3 registros"
    assert audit.findings[0].severity == WARNING


def test_sort_rows_is_stable_with_empties_last():
    rules = {**COMMON_RULES, "TRA-900": "prueba"}
    audit = AuditLog(rules)
    df = make_df([{"C": "002", "N": 1}, {"C": None, "N": 2}, {"C": "001", "N": 3}, {"C": "002", "N": 4}])
    result = sort_rows(df, "C", audit, "TRA-900")
    assert list(result["N"]) == [3, 1, 4, 2]
    assert audit.transformations[0].detail == "Registros ordenados por C (4 registros)"
