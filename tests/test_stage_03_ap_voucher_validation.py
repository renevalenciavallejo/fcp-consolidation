"""Etapa 3: carga del archivo procesado en la Etapa 2 y del AP Voucher, con datos inventados."""

from io import BytesIO

import pytest
from openpyxl import load_workbook

from core.audit import AuditLog
from core.runner import StageError, file_name_warnings, run_stage, validate_input
from core.stage import stage_rules
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


# Encabezados del AP Voucher (algunas columnas, con «Nombre» repetido como en el real).
AP_HEADER = ["Descripción", "Comprobante", "Nombre", "Estado Cierre", "Nombre", "Acción"]


def ap_row(voucher, closing="Abierto", action="Programación Pago"):
    return ["FCP", voucher, "PERSONA", closing, "PERSONA", action]


def ap_voucher(rows=(ap_row("00153417"),), name="AP_Voucher.xlsx"):
    """Archivo AP Voucher: 19 filas de título y los encabezados en la fila 20."""
    return make_xlsx([AP_HEADER, *[list(r) for r in rows]], header_row=20, name=name)


# Comprobantes del archivo procesado en la Etapa 2 (filas 2 y 3).
ETY_VOUCHERS = ["00000101", "00000102"]


def fill(sheet, row):
    """Color de la celda Comprobante de una fila del archivo de salida."""
    column = OUTPUT_COLUMNS.index("Comprobante") + 1
    return sheet.cell(row=row, column=column).fill.start_color.rgb[-6:]


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
    assert codes == [
        "EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008",
        "LIM-003", "VAL-301", "VAL-302",
    ]


def test_ap_voucher_needs_its_columns_in_row_20():
    wrong = make_xlsx([["Comprobante", "Estado Cierre"], ["00000101", "Cerrado"]], header_row=20)
    with pytest.raises(StageError) as error:
        run(stage_2_output(), voucher=[wrong])
    assert any("EST-003" in p and "Acción" in p for p in error.value.problems)


def test_no_closed_or_cancelled_vouchers():
    result = run(stage_2_output())
    assert not result.audit.findings
    lines = "\n".join(result.audit.step_lines())
    assert "Ningún comprobante del reporte ETY está cerrado" in lines
    assert "Ningún comprobante del reporte ETY está cancelado" in lines


def test_closed_vouchers_are_flagged_once_per_ety_record():
    # El comprobante cerrado aparece dos veces en el AP Voucher y con espacios: cuenta una vez.
    rows = [ap_row("00000101", "Cerrado"), ap_row(" 00000101 ", "CERRADO"), ap_row("00000102")]
    result = run(stage_2_output(), voucher=[ap_voucher(rows)])
    findings = result.audit.findings
    assert [(f.rule, f.severity, f.source_row, f.value) for f in findings] == [
        ("VAL-301", "Advertencia", 2, "00000101")
    ]
    assert "filas 21, 22" in findings[0].description
    lines = "\n".join(result.audit.step_lines())
    assert "AP Voucher: 2 registros con Estado Cierre «Cerrado» (1 comprobante distinto)" in lines
    assert "✗ [VAL-301] 1 comprobante del reporte ETY está cerrado en el AP Voucher: 00000101" in lines
    assert result.summary.rows_output == 2   # El reporte ETY no cambia


def test_cancelled_vouchers_are_flagged():
    rows = [ap_row("00000102", action="Cancelado"), ap_row("00000101", action="Cancelado")]
    result = run(stage_2_output(), voucher=[ap_voucher(rows)])
    assert [(f.rule, f.source_row) for f in result.audit.findings] == [("VAL-302", 2), ("VAL-302", 3)]
    assert "2 comprobantes del reporte ETY están cancelados en el AP Voucher" in "\n".join(result.audit.step_lines())


def test_closed_and_cancelled_have_their_own_colors():
    rows = [ap_row("00000101", "Cerrado"), ap_row("00000102", action="Cancelado")]
    result = run(stage_2_output(), voucher=[ap_voucher(rows)])
    sheet = load_workbook(BytesIO(result.output_bytes)).active
    fills = stage_03_ap_voucher_validation.RULE_FILLS
    assert fill(sheet, 2) == fills["VAL-301"]
    assert fill(sheet, 3) == fills["VAL-302"]


def test_ap_voucher_title_rows_are_logged():
    result = run(stage_2_output())
    titles = [a for a in result.audit.removals if a.rule == "LIM-003"]
    assert len(titles) == 19


def test_ety_is_validated_on_upload():
    audit = AuditLog(stage_rules(stage_03_ap_voucher_validation))
    data = validate_input(stage_03_ap_voucher_validation, "ety_processed", [stage_2_output()], audit)
    assert list(data["Comprobante"]) == ETY_VOUCHERS
    assert "✓ 25 columnas en el orden esperado, 2 registros" in "\n".join(audit.step_lines())


def test_wrong_ety_is_rejected_on_upload():
    with pytest.raises(StageError) as error:
        validate_input(stage_03_ap_voucher_validation, "ety_processed", [ety_file()])
    assert any("EST-003" in p for p in error.value.problems)
    assert any("Validando la estructura" in line for line in error.value.steps)



def test_ap_voucher_structure_is_validated_on_upload():
    data = validate_input(stage_03_ap_voucher_validation, "ap_voucher", [ap_voucher([ap_row("00000101", "Cerrado")])])
    assert list(data["Estado Cierre"]) == ["Cerrado"]
    with pytest.raises(StageError) as error:
        validate_input(stage_03_ap_voucher_validation, "ap_voucher", [make_xlsx([["Comprobante"], ["00000101"]])])
    assert any("EST-003" in p for p in error.value.problems)


def test_notice_without_matches_names_the_colors():
    assert run(stage_2_output()).notice == [
        "Cerrados en el AP Voucher (Estado Cierre «Cerrado»), resaltados en naranja claro: ninguno",
        "Cancelados en el AP Voucher (Acción «Cancelado»), resaltados en gris claro: ninguno",
    ]


def test_notice_lists_closed_and_cancelled_vouchers():
    rows = [ap_row("00000101", "Cerrado"), ap_row("00000102", action="Cancelado"), ap_row("00000101", action="Cancelado")]
    assert run(stage_2_output(), voucher=[ap_voucher(rows)]).notice == [
        "Cerrados en el AP Voucher (Estado Cierre «Cerrado»), resaltados en naranja claro: 1 comprobante",
        "  00000101 (fila 2 del reporte ETY)",
        "Cancelados en el AP Voucher (Acción «Cancelado»), resaltados en gris claro: 2 comprobantes",
        "  00000101 (fila 2 del reporte ETY)",
        "  00000102 (fila 3 del reporte ETY)",
    ]
