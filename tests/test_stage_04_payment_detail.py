"""Etapa 4: carga del archivo procesado en la Etapa 3 y archivo con el formato del Detalle de pago."""

from io import BytesIO

import pandas as pd

import pytest
from openpyxl import load_workbook

from core.audit import AuditLog
from core.runner import StageError, file_name_warnings, run_stage, validate_input
from core.stage import applied_rules, input_specs, stage_rules
from stages import STAGES, stage_03_ap_voucher_validation, stage_04_payment_detail
from stages.stage_04_payment_detail.config import (
    ACCOUNTING_FORMAT,
    COLUMN_MAPPING,
    DATE_FORMAT,
    FIXED_VALUES,
    FUNDING_SOURCES,
    SUBTRUST_NAMES,
    SUBTRUST_RELATIONS,
    SUBTRUST_RESOURCES,
    OUTPUT_LAYOUT,
)
from stages.stage_04_payment_detail.process import (
    add_prefix,
    as_number,
    assign_from_subtrust,
    assign_validity,
    contract_number,
)
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
        "EST-007", "EST-001", "EST-003", "EST-004", "EST-005", "EST-006", "EST-008", "TRA-401", "TRA-402", "TRA-405",
        "TRA-407", "TRA-408", "TRA-406", "TRA-403", "TRA-404", "TRA-409", "TRA-410",
    ]


def test_output_has_the_payment_detail_columns():
    result = run(stage_3_output())
    sheet = output_sheet(result)
    assert sheet.title == "Hoja1"
    assert [c.value for c in sheet[1]] == DETAIL_COLUMNS
    assert [a.rule for a in result.audit.transformations] == [
        "TRA-401", "TRA-402", "TRA-402", "TRA-402", "TRA-402", "TRA-402", "TRA-405",
        "TRA-407", "TRA-408", "TRA-406", "TRA-403", "TRA-404", "TRA-409", "TRA-410",
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
            if detail_column in ("IDENTIFICACION", "SUBFIDEICOMISO", "CUENTA"):
                expected = int(expected)   # Se escribe como número (ver test_identification_is_written_as_number)
            if detail_column == "COMPROBANTE":
                expected = f"656-{expected}"   # Con el prefijo (ver test_voucher_gets_the_656_prefix)
            assert cell.value == expected, (row, detail_column)
    # Las columnas sin correspondencia quedan vacías.
    filled = [
        *COLUMN_MAPPING.values(), *FIXED_VALUES, "VALIDACION", "CONTRATO", "VIGENCIA", "CONTRATO_2",
        *[relation["column"] for relation in SUBTRUST_RELATIONS],
    ]
    unmapped = [c for c in DETAIL_COLUMNS if c not in filled]
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
    assert COLUMN_MAPPING["Cuenta"] == "CUENTA"
    assert COLUMN_MAPPING["Programa"] == "PROGRAMA"


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


def test_account_is_number_and_program_keeps_its_zeros():
    sheet = output_sheet(run(stage_3_output()))
    assert sheet["S2"].value == 4147 and sheet["S2"].data_type == "n"
    assert sheet["AA2"].value == "0002"   # Con ceros a la izquierda: se copia como texto


def test_fixed_values_are_assigned_to_every_record():
    result = run(stage_3_output())
    sheet = output_sheet(result)
    for row in (2, 3):
        assert sheet[f"W{row}"].value == "FIDUPREVISORA"
        assert sheet[f"AB{row}"].value == 656 and sheet[f"AB{row}"].data_type == "n"
        assert sheet[f"AC{row}"].value == "1" and sheet[f"AC{row}"].number_format == "@"
        assert sheet[f"AE{row}"].value == 0 and sheet[f"AF{row}"].value == 0
    assert sheet["AE2"].number_format == ACCOUNTING_FORMAT
    lines = "\n".join(result.audit.step_lines())
    assert "FIDUCIARIA_QUE_EFECTUO_EL_PAGO = «FIDUPREVISORA», GL = 656, Q_PAGOS = «1»" in lines


def test_funding_source_comes_from_the_subtrust():
    result = run(stage_3_output())
    sheet = output_sheet(result)
    assert sheet["Q2"].value == 1002 and sheet["AG2"].value == "PGN"
    assert "FUENTE_DE_RECURSOS asignada en 2 de 2 registros" in "\n".join(result.audit.step_lines())


def test_funding_source_relation_has_44_subtrusts():
    assert len(FUNDING_SOURCES) == 44
    assert set(FUNDING_SOURCES.values()) == {"PGN", "OTROS"}
    assert FUNDING_SOURCES["2016"] == "OTROS" and FUNDING_SOURCES["2041"] == "PGN"


def test_subtrust_name_comes_from_the_subtrust():
    result = run(stage_3_output())
    sheet = output_sheet(result)
    assert sheet["Q2"].value == 1002
    assert sheet["R2"].value == "PROGRAMAS DE DESARROLLO CON ENFOQUE TERRITORIAL -PDET"
    assert "NOMBRE_SUBFIDEICOMISO_PAGO asignada en 2 de 2 registros" in "\n".join(result.audit.step_lines())


def test_subtrust_names_have_the_same_44_subtrusts_and_no_trailing_spaces():
    assert set(SUBTRUST_NAMES) == set(FUNDING_SOURCES)
    assert all(name == name.strip() for name in SUBTRUST_NAMES.values())
    assert SUBTRUST_NAMES["2024"] == "NIÑEZ Y ADOLESCENCIA ICBF"
    assert SUBTRUST_NAMES["1003"] == SUBTRUST_NAMES["2045"] == "SUSTITUCION"


def test_resources_come_from_the_subtrust():
    result = run(stage_3_output())
    sheet = output_sheet(result)
    assert sheet["Q2"].value == 1002 and sheet["Z2"].value == "PAC JULIO 2026"
    assert "RECURSOS asignada en 2 de 2 registros" in "\n".join(result.audit.step_lines())


def test_resources_relation_has_the_same_44_subtrusts():
    assert set(SUBTRUST_RESOURCES) == set(FUNDING_SOURCES)
    assert SUBTRUST_RESOURCES["2016"] == "CENIT"
    assert SUBTRUST_RESOURCES["2023"] == "VISIÓN AMAZONIA"
    assert SUBTRUST_RESOURCES["2054"] == "CONVENIO 764-26 MEN"


def test_unknown_or_empty_subtrust_leaves_funding_source_empty():
    audit = AuditLog(stage_rules(stage_04_payment_detail))
    audit.step("Asignando FUENTE_DE_RECURSOS")
    detail = pd.DataFrame({"SUBFIDEICOMISO": [2054, "2016", 9999, None], "FUENTE_DE_RECURSOS": None}, dtype=object)
    relation = next(r for r in SUBTRUST_RELATIONS if r["column"] == "FUENTE_DE_RECURSOS")
    assign_from_subtrust(detail, relation, audit)
    assert list(detail["FUENTE_DE_RECURSOS"]) == ["OTROS", "OTROS", None, None]
    lines = "\n".join(audit.step_lines())
    assert "✗ [TRA-406] 2 registros sin FUENTE_DE_RECURSOS" in lines
    assert "(9999, (vacío))" in lines


@pytest.mark.parametrize(
    ("concept", "expected"),
    [
        # Mismos resultados que la fórmula de CONTRATO en Excel.
        ("DS_656-135323-1100622249_303_CONTRATO_303-2026_HONORARIOS", "303"),
        ("DS_656-1_008_CONTRATO_008-2026_PAGO", "008"),
        ("ADR_PROY_PROD_PIDAR_841-2024PAGO_01 AL 31", None),            # Sin «CONTRATO»: #¡VALOR!
        ("656-1_REINTEGRO CONTRATOS_DEL MES", "CONTRATOS"),             # Alfabético
        ("656-1_ARL_MTRA_CONTRATO_-2023-PLANILLA", ""),                 # Vacío
        ("656-1_Contrato_45-2026_X", "Contrato"),                       # SUBSTITUTE distingue mayúsculas
        ("PAGO CONTRATO", None),                                        # Sin «_» después: #¡VALOR!
    ],
)
def test_contract_number_repeats_the_excel_formula(concept, expected):
    assert contract_number(concept) == expected


def test_validity_is_taken_only_when_the_contract_is_a_number():
    audit = AuditLog(stage_rules(stage_04_payment_detail))
    audit.step("Asignando VIGENCIA")
    concepts = [
        "DS_656-160432-830093042_2826_CONTRATO_2826-2025_2do-DESEMBOLSO",   # 2025
        "DS_656-165410-1015427627_218_CONTRATO_218-2026_HONORARIOS",        # 2026
        "DS_656-1_8_CONTRATO_8-2024_PAGO",                                  # 2024
        "DS_656-1_008_CONTRATO_008-2026_PAGO",                              # 2026 (con ceros)
        "ADR_PROY_PROD_PIDAR_841-2024PAGO_01 AL 31",                        # Sin CONTRATO
        "656-1_REINTEGRO CONTRATOS_DEL MES",                                # CONTRATO alfabético
        "DS_1_CONTRATO_77_SIN VIGENCIA",                                    # Número sin la expresión
        None,                                                               # CONCEPTO vacío
    ]
    detail = pd.DataFrame({"CONCEPTO": concepts, "VIGENCIA": None}, dtype=object)
    assign_validity(detail, audit)
    assert list(detail["VIGENCIA"]) == [2025, 2026, 2024, 2026, None, None, None, None]
    audit.finish_step()   # El resumen del paso se escribe al cerrarlo
    lines = "\n".join(audit.step_lines())
    assert "VIGENCIA asignada en 4 de 8 registros; vacía en 3 porque el CONTRATO" in lines
    assert "y en 1 porque CONCEPTO no tiene la expresión CONTRATO_<número>-<vigencia>" in lines


def test_validity_is_empty_without_contract_in_the_concept():
    sheet = output_sheet(run(stage_3_output()))
    assert sheet["V2"].value == "DS_PRUEBA" and sheet["P2"].value is None


def test_contract_2_is_the_payment_detail_formula():
    result = run(stage_3_output())
    sheet = output_sheet(result)
    # La misma fórmula del Detalle de pago (=+CONCATENATE(O2,"-",P2)), en cada fila.
    assert sheet["AD2"].value == '=+CONCATENATE(O2,"-",P2)'
    assert sheet["AD3"].value == '=+CONCATENATE(O3,"-",P3)'
    assert sheet["AD2"].number_format == "General"
    lines = "\n".join(result.audit.step_lines())
    assert lines.index("Asignando VIGENCIA") < lines.index("Calculando CONTRATO_2")


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
