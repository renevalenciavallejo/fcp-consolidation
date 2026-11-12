"""Etapa 4: carga del archivo procesado en la Etapa 3 y archivo con el formato del Detalle de pago."""

from io import BytesIO

import pandas as pd

import pytest
from openpyxl import load_workbook

from core.audit import AuditLog
from core.runner import StageError, file_name_warnings, run_stage, validate_input
from core.stage import applied_rules, input_specs, stage_rules
from stages import STAGES, stage_03_ap_voucher_validation, stage_04_payment_detail
from stages.stage_04_payment_detail.config import ACCOUNTING_FORMAT, COLUMN_MAPPING, DATE_FORMAT, OUTPUT_LAYOUT
from stages.stage_04_payment_detail.process import add_prefix, as_number
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
    assert codes == [
        "EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008", "TRA-401", "TRA-402", "TRA-403",
        "TRA-404",
    ]


def test_output_has_the_payment_detail_columns():
    result = run(stage_3_output())
    sheet = output_sheet(result)
    assert sheet.title == "Hoja1"
    assert [c.value for c in sheet[1]] == DETAIL_COLUMNS
    assert [a.rule for a in result.audit.transformations] == [
        "TRA-401", "TRA-402", "TRA-402", "TRA-402", "TRA-402", "TRA-403", "TRA-404",
    ]


def test_ety_values_are_copied_row_by_row_without_changes():
    ety = validate_input(stage_04_payment_detail, "ety_processed", [stage_3_output()])
    result = run(stage_3_output())
    sheet = output_sheet(result)
    assert result.summary.rows_output == len(ety) == 2
    assert sheet.max_row == 3
    for position, (_, record) in enumerate(ety.iterrows()):
        row = position + 2
        for ety_column, detail_column in COLUMN_MAPPING.items():
            cell = sheet.cell(row, DETAIL_COLUMNS.index(detail_column) + 1)
            expected = record[ety_column]
            if detail_column in ("IDENTIFICACION", "SUBFIDEICOMISO"):
                expected = int(expected)   # Se escribe como número (ver test_identification_is_written_as_number)
            if detail_column == "COMPROBANTE":
                expected = f"656-{expected}"   # Con el prefijo (ver test_voucher_gets_the_656_prefix)
            assert cell.value == expected, (row, detail_column)
    # Las columnas sin correspondencia quedan vacías.
    unmapped = [c for c in DETAIL_COLUMNS if c not in [*COLUMN_MAPPING.values(), "VALIDACION", "CONTRATO"]]
    assert all(sheet.cell(2, DETAIL_COLUMNS.index(c) + 1).value is None for c in unmapped)
    assert "2 registros del reporte ETY copiados" in "\n".join(result.audit.step_lines())


def test_identification_is_written_as_number():
    result = run(stage_3_output())
    sheet = output_sheet(result)
    assert sheet["B2"].value == 12345678 and sheet["B2"].data_type == "n"
    assert "IDENTIFICACION: 2 valores escritos como número" in "\n".join(result.audit.step_lines())


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1085283965", 1085283965), ("0012345", "0012345"), ("900123456-1", "900123456-1"), (None, None), (77178085, 77178085)],
)
def test_only_plain_digits_become_numbers(value, expected):
    assert as_number(value) == expected


def test_new_columns_are_mapped():
    assert COLUMN_MAPPING["Asiento"] == "ASIENTO"
    assert COLUMN_MAPPING["Comprobante"] == "COMPROBANTE"
    assert COLUMN_MAPPING["Nº Sec Doc"] == "NO_SEC_DOC"
    assert COLUMN_MAPPING["Más Info"] == "CONCEPTO"
    assert COLUMN_MAPPING["Subfideicomiso"] == "SUBFIDEICOMISO"


def test_voucher_gets_the_656_prefix():
    result = run(stage_3_output())
    sheet = output_sheet(result)
    assert [sheet["M2"].value, sheet["M3"].value] == ["656-00000101", "656-00000102"]
    assert "COMPROBANTE: prefijo «656-» agregado a 2 valores" in "\n".join(result.audit.step_lines())


@pytest.mark.parametrize(("value", "expected"), [("00153414", "656-00153414"), ("656-00153414", "656-00153414"), (None, None)])
def test_prefix_is_added_once_and_empty_stays_empty(value, expected):
    detail = pd.DataFrame({"COMPROBANTE": [value]}, dtype=object)
    add_prefix(detail, "COMPROBANTE", "656-", AuditLog(stage_rules(stage_04_payment_detail)))
    assert detail["COMPROBANTE"][0] == expected


def test_validation_is_the_difference_formula_of_each_row():
    sheet = output_sheet(run(stage_3_output()))
    assert sheet["K2"].value == "=E2-F2-G2-H2-I2-J2"
    assert sheet["K3"].value == "=E3-F3-G3-H3-I3-J3"
    assert sheet["K2"].number_format == ACCOUNTING_FORMAT


def test_subtrust_is_written_as_number():
    result = run(stage_3_output())
    sheet = output_sheet(result)
    assert sheet["Q2"].value == 1002 and sheet["Q2"].data_type == "n"
    assert "SUBFIDEICOMISO: 2 valores escritos como número" in "\n".join(result.audit.step_lines())


def test_contract_is_the_payment_detail_formula_over_concept():
    sheet = output_sheet(run(stage_3_output()))
    assert sheet["V2"].value == "DS_PRUEBA"
    formula = sheet["O2"].value
    # La misma fórmula del Detalle de pago, sobre CONCEPTO (columna V) de la misma fila.
    assert formula.startswith('=MID(SUBSTITUTE(MID(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(V2," ","_")')
    assert 'SEARCH("CONTRATO",V2,1),LEN(V2))' in formula
    assert "{" not in formula and "V3" not in formula
    assert "V3" in sheet["O3"].value
    assert sheet["O2"].number_format == "General"


def test_copied_values_take_the_payment_detail_cell_formats():
    sheet = output_sheet(run(stage_3_output()))
    assert sheet["D2"].number_format == DATE_FORMAT
    assert all(sheet[f"{letter}2"].number_format == ACCOUNTING_FORMAT for letter in "EFGHIJ")
    assert sheet["B2"].alignment.horizontal == "center"
    assert sheet["C2"].border.left.style == "thin"
    assert sheet["Q2"].border.left.style == "thin"   # También las columnas vacías


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
