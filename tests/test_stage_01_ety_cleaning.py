"""Etapa 1: validación de estructura del reporte ETY, con datos inventados."""

from datetime import datetime

import pytest

from core.runner import StageError, run_stage
from stages import stage_01_ety_cleaning
from tests.helpers import make_xlsx

COLUMNS = list(stage_01_ety_cleaning.INPUTS["ety_report"]["columns"])

ROW = [
    "0010000001", "12345678", "PERSONA DE PRUEBA", datetime(2026, 9, 28, 2, 0), 1000000, 0, 0,
    5000, 0, 995000, "AP00000001", "Cuentas a Pagar", 1, "00000001", "Pago Estándar",
    "CE0000000001", "DS_PRUEBA", "20025", "23-26", "1002", "4147", "2", "100212", "0002",
]


def ety_file(header=COLUMNS, rows=(ROW,), sheet="sheet1", header_row=4, name="ety.xlsx"):
    return make_xlsx([list(header), *[list(r) for r in rows]], sheet=sheet, header_row=header_row, name=name)


def run(*files):
    return run_stage(stage_01_ety_cleaning, {"ety_report": list(files)})


def stage_error(*files) -> StageError:
    with pytest.raises(StageError) as error:
        run(*files)
    return error.value


def problems_for(*files) -> list[str]:
    return stage_error(*files).problems


def test_messages_speak_of_a_single_file():
    error = stage_error(ety_file(header_row=1))
    assert error.message == "La estructura del archivo no es la esperada."


def test_valid_report_is_processed():
    result = run(ety_file(rows=(ROW, ROW)))
    assert result.summary.rows_read == 2
    assert result.output_file_name.startswith("E01_ety_cleaning_procesado_")


def test_header_spaces_are_tolerated():
    header = [f" {c} " for c in COLUMNS]
    assert run(ety_file(header=header)).summary.rows_read == 1


def test_any_sheet_name_is_accepted():
    assert run(ety_file(sheet="Hoja1")).summary.rows_read == 1


def test_column_order_is_validated():
    header = list(COLUMNS)
    header[4], header[5] = header[5], header[4]  # VR. BRUTO <-> VR. RTEFTE
    problems = problems_for(ety_file(header=header))
    assert len(problems) == 1
    assert "EST-008" in problems[0] and "posición 5" in problems[0] and "'VR. BRUTO'" in problems[0]


def test_missing_column():
    header = [c for c in COLUMNS if c != "Importe"]
    row = [v for c, v in zip(COLUMNS, ROW) if c != "Importe"]
    problems = problems_for(ety_file(header=header, rows=(row,)))
    assert any("EST-003" in p and "'Importe'" in p for p in problems)


def test_extra_column():
    problems = problems_for(ety_file(header=[*COLUMNS, "Otra"], rows=([*ROW, "x"],)))
    assert any("EST-004" in p and "'Otra'" in p for p in problems)


def test_title_rows_removed():
    problems = problems_for(ety_file(header_row=1))
    assert len(problems) == 1 and "están en la fila 1" in problems[0]


def test_only_one_file_allowed():
    problems = problems_for(ety_file(name="a.xlsx"), ety_file(name="b.xlsx"))
    assert any("EST-007" in p and "un solo archivo" in p for p in problems)
