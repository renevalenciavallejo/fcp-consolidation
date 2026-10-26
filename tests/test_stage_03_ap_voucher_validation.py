"""Etapa 3: carga del archivo procesado en la Etapa 2 y del AP Voucher, con datos inventados."""

from io import BytesIO

import pytest
from openpyxl import load_workbook

from core.runner import StageError, file_name_warnings, run_stage
from core.stage import applied_rules, input_specs
from stages import STAGES, stage_02_payment_reconciliation, stage_03_ap_voucher_validation
from tests.helpers import make_xlsx
from tests.test_stage_01_ety_cleaning import OUTPUT_COLUMNS, ety_file
from tests.test_stage_02_payment_reconciliation import run as run_stage_2
from tests.test_stage_02_payment_reconciliation import stage_1_output


def stage_2_output():
    """Archivo procesado en la Etapa 2, tal como lo descarga el usuario."""
    result = run_stage_2(stage_1_output())
    file = BytesIO(result.output_bytes)
    file.name = result.output_file_name
    return file


def ap_voucher(name="AP_Voucher.xlsx"):
    """Archivo AP Voucher: su estructura todavía no está especificada."""
    return make_xlsx([["Voucher"], ["00153417"]], name=name)


def run(*files, voucher=None):
    vouchers = [ap_voucher()] if voucher is None else voucher
    return run_stage(stage_03_ap_voucher_validation, {"ety_processed": list(files), "ap_voucher": vouchers})


def test_stage_3_is_registered_after_stage_2():
    assert STAGES[1:3] == [stage_02_payment_reconciliation, stage_03_ap_voucher_validation]


def test_expected_columns_are_the_stage_2_output():
    assert list(stage_03_ap_voucher_validation.INPUTS["ety_processed"]["columns"]) == OUTPUT_COLUMNS


def test_stage_2_output_is_accepted():
    result = run(stage_2_output())
    assert result.summary.rows_output == 2
    assert result.output_file_name == "ETY_sept_E03_procesado.xlsx"
    sheet = load_workbook(BytesIO(result.output_bytes)).active
    assert sheet.title == "sheet1" and [c.value for c in sheet[1]] == OUTPUT_COLUMNS


def test_original_report_is_rejected():
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
        run(stage_2_output(), stage_2_output())
    assert any("EST-007" in p and "un solo archivo" in p for p in error.value.problems)


def test_ap_voucher_is_required():
    with pytest.raises(StageError) as error:
        run(stage_2_output(), voucher=[])
    assert any("AP Voucher" in p for p in error.value.problems)


def test_ap_voucher_must_be_xlsx():
    broken = BytesIO(b"no es un excel")
    broken.name = "AP_Voucher.xlsx"
    with pytest.raises(StageError) as error:
        run(stage_2_output(), voucher=[broken])
    assert any("EST-001" in p for p in error.value.problems)


def test_name_without_stage_2_mark_warns():
    spec = next(s for s in input_specs(stage_03_ap_voucher_validation) if s.key == "ety_processed")
    assert file_name_warnings(spec, [make_xlsx([["x"]], name="ETY_sept_E01_procesado.xlsx")])
    assert not file_name_warnings(spec, [make_xlsx([["x"]], name="ETY_sept_E02_procesado.xlsx")])


def test_applied_rules():
    codes = [code for code, _ in applied_rules(stage_03_ap_voucher_validation)]
    assert codes == ["EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008"]
