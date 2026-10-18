"""Etapa 2: carga del archivo procesado en la Etapa 1, con datos inventados."""

from io import BytesIO

import pytest
from openpyxl import load_workbook

from core.runner import StageError, run_stage
from core.stage import applied_rules
from stages import STAGES, stage_01_ety_cleaning, stage_02_payment_reconciliation
from tests.helpers import make_xlsx
from tests.test_stage_01_ety_cleaning import OUTPUT_COLUMNS, ROW, distinct, ety_file


def stage_1_output(rows=distinct(ROW, ROW)):
    """Archivo procesado en la Etapa 1, tal como lo descarga el usuario."""
    result = run_stage(stage_01_ety_cleaning, {"ety_report": [ety_file(rows=rows, name="ETY_sept.xlsx")]})
    file = BytesIO(result.output_bytes)
    file.name = result.output_file_name
    return file


def run(*files):
    return run_stage(stage_02_payment_reconciliation, {"ety_processed": list(files)})


def test_stage_2_is_registered_after_stage_1():
    assert STAGES[:2] == [stage_01_ety_cleaning, stage_02_payment_reconciliation]


def test_expected_columns_are_the_stage_1_output():
    assert list(stage_02_payment_reconciliation.INPUTS["ety_processed"]["columns"]) == OUTPUT_COLUMNS


def test_stage_1_output_is_accepted():
    result = run(stage_1_output())
    assert result.summary.rows_read == 2 and result.summary.rows_output == 2
    assert result.output_file_name == "ETY_sept_E02_procesado.xlsx"
    sheet = load_workbook(BytesIO(result.output_bytes)).active
    assert sheet.title == "sheet1" and [c.value for c in sheet[1]] == OUTPUT_COLUMNS


def test_original_report_is_rejected():
    # El reporte sin procesar (títulos en las filas 1 a 3, sin Diferencia) no corresponde a esta etapa.
    with pytest.raises(StageError) as error:
        run(ety_file())
    assert any("EST-003" in p for p in error.value.problems)


def test_columns_out_of_order_are_rejected():
    columns = list(OUTPUT_COLUMNS)
    columns[0], columns[1] = columns[1], columns[0]
    with pytest.raises(StageError) as error:
        run(make_xlsx([columns, [None] * len(columns)], sheet="sheet1"))
    assert any("EST-008" in p for p in error.value.problems)


def test_only_one_file_allowed():
    with pytest.raises(StageError) as error:
        run(stage_1_output(), stage_1_output())
    assert any("EST-007" in p and "un solo archivo" in p for p in error.value.problems)


def test_applied_rules_are_structure_rules():
    codes = [code for code, _ in applied_rules(stage_02_payment_reconciliation)]
    assert codes == ["EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008"]
