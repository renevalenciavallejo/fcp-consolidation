from io import BytesIO

import pandas as pd
import pytest
from openpyxl import load_workbook

from core.writer import ExcelFormula, build_output


def test_formula_references_are_resolved_by_column_name():
    formula = ExcelFormula("={A}-{C}", "#,##0.00")
    df = pd.DataFrame({"A": [5.0, 7.0], "B": ["x", "y"], "C": [1.0, 2.0], "D": [formula, formula]}, dtype=object)
    sheet = load_workbook(BytesIO(build_output(df, []))).active
    assert sheet["D2"].value == "=A2-C2"
    assert sheet["D3"].value == "=A3-C3"
    assert sheet["D2"].number_format == "#,##0.00"


def test_formula_with_unknown_column_fails():
    df = pd.DataFrame({"A": [1.0], "D": [ExcelFormula("={Z}-{A}")]}, dtype=object)
    with pytest.raises(ValueError, match="'Z'"):
        build_output(df, [])
