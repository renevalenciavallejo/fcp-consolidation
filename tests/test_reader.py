from datetime import datetime
from io import BytesIO

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


def test_repeated_extra_column_is_allowed_when_extra_columns_are():
    # Un encabezado repetido se tolera solo si es una columna que la etapa no usa.
    spec = InputSpec(**{**SPEC.__dict__, "allow_extra_columns": True})
    result = read_file(make_xlsx([["Codigo", "Cuenta", "Valor", "Cuenta"], ["1", "A", 1, "B"]]), spec)
    assert result.problems == []
    assert result.data.at[0, "Cuenta"] == "A"  # Se conserva la primera
    repeated = read_file(make_xlsx([["Codigo", "Valor", "Valor"], ["1", 1, 2]]), spec).problems
    assert any("EST-005" in p for p in repeated)


def test_not_an_excel_file():

    file = BytesIO(b"esto no es un excel")
    file.name = "malo.xlsx"
    result = read_file(file, SPEC)
    assert "EST-001" in result.problems[0] and "malo.xlsx" in result.problems[0]
    assert result.opened is False


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


# --- Lectura rápida (python-calamine) -----------------------------------------

FAST_SPEC = InputSpec(**{**SPEC.__dict__, "header_row": 3, "allow_extra_columns": True, "fast_read": True})


def fast_file():
    """Columna A vacía, dos filas de título, celdas vacías y una columna adicional."""
    return make_xlsx(
        [[None, "Codigo", "Valor", "Otra"], [None, "007", 1500, None], [None, None, None, "x"], [None, "8", 2.5, None]],
        header_row=3,
    )


def test_fast_read_gives_the_same_values_and_rows():
    normal = read_file(fast_file(), InputSpec(**{**FAST_SPEC.__dict__, "fast_read": False}))
    fast = read_file(fast_file(), FAST_SPEC)
    assert fast.problems == []
    assert list(fast.data[SOURCE_ROW]) == [4, 5, 6]   # Filas reales, aunque la columna A esté vacía
    assert list(fast.data["Codigo"]) == ["007", None, "8"]
    assert list(fast.data["Otra"]) == [None, "x", None]   # Las celdas vacías quedan vacías, no ""
    assert list(fast.data["Valor"].fillna(0)) == list(normal.data["Valor"].fillna(0))
    assert fast.title_rows == normal.title_rows


def test_fast_read_has_no_style():
    assert read_file(fast_file(), FAST_SPEC).style is None


def test_fast_read_reports_structure_problems():
    file = make_xlsx([["Codigo"], ["1"]], header_row=3)
    assert any("EST-003" in p and "Valor" in p for p in read_file(file, FAST_SPEC).problems)


def test_fast_read_rejects_a_file_that_is_not_excel():
    broken = BytesIO(b"no es un excel")
    broken.name = "malo.xlsx"
    result = read_file(broken, FAST_SPEC)
    assert not result.opened and "EST-001" in result.problems[0]
