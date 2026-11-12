"""Etapa 4: carga del archivo procesado en la Etapa 3 y archivo con el formato del Detalle de pago."""

from io import BytesIO

import pytest
from openpyxl import load_workbook

from core.runner import StageError, file_name_warnings, run_stage, validate_input
from core.stage import applied_rules, input_specs
from stages import STAGES, stage_03_ap_voucher_validation, stage_04_payment_detail
from stages.stage_04_payment_detail.config import ACCOUNTING_FORMAT, DATE_FORMAT, OUTPUT_LAYOUT
from tests.helpers import make_xlsx
from tests.test_stage_01_ety_cleaning import OUTPUT_COLUMNS, ety_file
from tests.test_stage_03_ap_voucher_validation import run as run_stage_3
from tests.test_stage_03_ap_voucher_validation import stage_2_output

# Las 34 columnas del Detalle de pago, en orden (DetallePagoEjemploFormato.xlsx).
DETAIL_COLUMNS = [
    "ITEM", "IDENTIFICACION", "TERCERO", "FECHA_DE_PAGO", "VR_BRUTO", "VR_RTEFTE", "VR_RETEIVA",
    "VR_RETEICA", "VR_TASAS", "VR_NETO", "VALIDACION", "ASIENTO", "COMPROBANTE", "NO_SEC_DOC",
    "CONTRATO", "VIGENCIA", "SUBFIDEICOMISO", "NOMBRE_SUBFIDEICOMISO_PAGO", "CUENTA", "TIPO_DE_PAGO",
    "NO_BENEFICIARIOS", "CONCEPTO", "FIDUCIARIA_QUE_EFECTUO_EL_PAGO", "INFORME_SEMANAL",
    "PERIODO_DE_COBRO", "RECURSOS", "PROGRAMA", "GL", "Q_PAGOS", "CONTRATO_2",
    "AMORTIZACION_ANTICIPO", "MULTA", "FUENTE_DE_RECURSOS", "RANGO",
]


def stage_3_output():
    """Archivo procesado en la Etapa 3, tal como lo descarga el usuario."""
    result = run_stage_3(stage_2_output())
    file = BytesIO(result.output_bytes)
    file.name = result.output_file_name
    return file


def run(*files):
    return run_stage(stage_04_payment_detail, {"ety_processed": list(files)})


def output_sheet(result):
    return load_workbook(BytesIO(result.output_bytes)).active


def test_stage_4_is_registered_after_stage_3():
    assert STAGES[2:4] == [stage_03_ap_voucher_validation, stage_04_payment_detail]


def test_expected_columns_are_the_stage_3_output():
    assert list(stage_04_payment_detail.INPUTS["ety_processed"]["columns"]) == OUTPUT_COLUMNS


def test_stage_3_output_is_accepted():
    result = run(stage_3_output())
    assert result.output_file_name == "ETY_sept_E04_procesado.xlsx"
    assert result.log_file_name == "ETY_sept_E04_log.xlsx"
    assert result.summary.rows_read == 2


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
        run(stage_3_output(), stage_3_output())
    assert any("EST-007" in p and "un solo archivo" in p for p in error.value.problems)


def test_name_without_stage_3_mark_warns():
    spec = input_specs(stage_04_payment_detail)[0]
    assert file_name_warnings(spec, [make_xlsx([["x"]], name="ETY_sept_E02_procesado.xlsx")])
    assert not file_name_warnings(spec, [make_xlsx([["x"]], name="ETY_sept_E03_procesado.xlsx")])


def test_ety_is_validated_on_upload():
    data = validate_input(stage_04_payment_detail, "ety_processed", [stage_3_output()])
    assert len(data) == 2
    with pytest.raises(StageError):
        validate_input(stage_04_payment_detail, "ety_processed", [ety_file()])


def test_applied_rules():
    codes = [code for code, _ in applied_rules(stage_04_payment_detail)]
    assert codes == ["EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008", "TRA-401"]


def test_output_has_the_payment_detail_columns_and_no_data():
    result = run(stage_3_output())
    sheet = output_sheet(result)
    assert sheet.title == "Hoja1"
    assert [c.value for c in sheet[1]] == DETAIL_COLUMNS
    assert sheet.max_row == 1
    assert result.summary.rows_output == 0
    assert [a.rule for a in result.audit.transformations] == ["TRA-401"]


def test_output_has_the_payment_detail_format():
    sheet = output_sheet(run(stage_3_output()))
    header = sheet["A1"]
    assert header.font.b and header.font.name == "Calibri" and header.font.color.rgb[-6:] == "FFFFFF"
    assert header.fill.start_color.rgb[-6:] == "2F75B5"
    assert header.alignment.horizontal == "center" and header.alignment.wrap_text
    assert header.border.bottom.style == "thin"
    # VIGENCIA y PROGRAMA tienen el encabezado verde.
    assert sheet["P1"].fill.start_color.rgb[-6:] == "00B050"
    assert sheet["AA1"].fill.start_color.rgb[-6:] == "00B050"
    assert sheet.row_dimensions[1].height == 58
    assert sheet.column_dimensions["C"].width == OUTPUT_LAYOUT["columns"]["TERCERO"]["width"]
    assert sheet.column_dimensions["V"].width == OUTPUT_LAYOUT["columns"]["CONCEPTO"]["width"]
    # Formatos de celda de la columna completa, para los datos que se agreguen.
    assert sheet.column_dimensions["D"].number_format == DATE_FORMAT
    assert sheet.column_dimensions["E"].number_format == ACCOUNTING_FORMAT
    assert sheet.column_dimensions["AC"].number_format == "@"
    assert sheet.column_dimensions["B"].alignment.horizontal == "center"
