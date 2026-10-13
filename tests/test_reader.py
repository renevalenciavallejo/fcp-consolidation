from datetime import datetime

from core.reader import read_file
from core.settings import SOURCE_FILE, SOURCE_ROW
from core.stage import InputSpec
from tests.helpers import make_xlsx

SPEC = InputSpec(
    key="r", label="Reporte", multiple=False, required=True, sheet="Datos", header_row=1,
    columns={"Codigo": "code", "Valor": "number"},
)


def test_reads_native_values_and_source_rows():
    file = make_xlsx(
        [["Codigo", "Valor"], ["007", 1500], [None, None], ["8", datetime(2024, 1, 2)], [None, None]],
        name="area.xlsx",
    )
    result = read_file(file, SPEC)
    assert result.problems == []
    df = result.data
    assert list(df["Codigo"]) == ["007", None, "8"]  # La fila vacía final no se lee
    assert df.at[0, "Valor"] == 1500
    assert list(df[SOURCE_ROW]) == [2, 3, 4]
    assert set(df[SOURCE_FILE]) == {"area.xlsx"}


def test_source_row_with_header_not_in_first_row():
    spec = InputSpec(**{**SPEC.__dict__, "header_row": 3})
    file = make_xlsx([["Codigo", "Valor"], ["1", 1]], header_row=3)
    result = read_file(file, spec)
    assert list(result.data[SOURCE_ROW]) == [4]


def test_header_spaces_are_ignored():
    file = make_xlsx([[" Codigo ", "Valor\xa0"], ["1", 1]])
    assert read_file(file, SPEC).problems == []


def test_missing_sheet():
    file = make_xlsx([["Codigo", "Valor"]], sheet="Otra")
    problems = read_file(file, SPEC).problems
    assert len(problems) == 1 and "EST-002" in problems[0] and "Otra" in problems[0]


def test_missing_and_extra_columns():
    file = make_xlsx([["Codigo", "Extra"], ["1", "x"]])
    problems = read_file(file, SPEC).problems
    assert any("EST-003" in p and "'Valor'" in p for p in problems)
    assert any("EST-004" in p and "'Extra'" in p for p in problems)


def test_extra_columns_allowed_when_configured():
    spec = InputSpec(**{**SPEC.__dict__, "allow_extra_columns": True})
    file = make_xlsx([["Codigo", "Valor", "Extra"], ["1", 1, "x"]])
    result = read_file(file, spec)
    assert result.problems == []
    assert "Extra" in result.data.columns


def test_repeated_header_and_data_without_header():
    file = make_xlsx([["Codigo", "Valor", "Valor", None], ["1", 1, 2, "dato"]])
    problems = read_file(file, SPEC).problems
    assert any("EST-005" in p for p in problems)
    assert any("EST-006" in p and "columna D" in p for p in problems)


def test_not_an_excel_file():
    from io import BytesIO

    file = BytesIO(b"esto no es un excel")
    file.name = "malo.xlsx"
    problems = read_file(file, SPEC).problems
    assert "EST-001" in problems[0] and "malo.xlsx" in problems[0]


def test_headers_in_another_row_gives_clear_message():
    spec = InputSpec(**{**SPEC.__dict__, "header_row": 3})
    file = make_xlsx([["Codigo", "Valor"], ["1", 1]], header_row=1)  # Sin filas de título
    problems = read_file(file, spec).problems
    assert len(problems) == 1
    assert "están en la fila 1" in problems[0] and "en la fila 3" in problems[0]


def test_without_sheet_name_uses_first_sheet():
    spec = InputSpec(**{**SPEC.__dict__, "sheet": None})
    file = make_xlsx([["Codigo", "Valor"], ["1", 1]], sheet="Cualquiera", extra_sheets={"Otra": [["x"]]})
    result = read_file(file, spec)
    assert result.problems == [] and len(result.data) == 1


def test_column_order_only_checked_when_configured():
    file = make_xlsx([["Valor", "Codigo"], [1, "1"]])
    assert read_file(file, SPEC).problems == []
    spec = InputSpec(**{**SPEC.__dict__, "check_column_order": True})
    problems = read_file(make_xlsx([["Valor", "Codigo"], [1, "1"]]), spec).problems
    assert len(problems) == 1 and "EST-008" in problems[0]


def test_column_order_ignores_allowed_extra_columns():
    spec = InputSpec(**{**SPEC.__dict__, "check_column_order": True, "allow_extra_columns": True})
    file = make_xlsx([["Extra", "Codigo", "Otra", "Valor"], ["x", "1", "y", 1]])
    assert read_file(file, spec).problems == []
