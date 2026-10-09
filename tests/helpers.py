"""Utilidades para crear archivos de Excel de prueba en memoria."""

from io import BytesIO

from openpyxl import Workbook


def make_xlsx(
    rows: list[list],
    sheet: str = "Datos",
    header_row: int = 1,
    name: str = "prueba.xlsx",
    extra_sheets: dict[str, list[list]] | None = None,
) -> BytesIO:
    """Crea un .xlsx en memoria. `rows` incluye la fila de encabezados.

    Si header_row > 1, se agregan filas de título antes de los encabezados.
    """
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet
    for number in range(1, header_row):
        worksheet.append([f"Título {number}"])
    for row in rows:
        worksheet.append(row)
    for title, sheet_rows in (extra_sheets or {}).items():
        other = workbook.create_sheet(title)
        for row in sheet_rows:
            other.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    buffer.name = name
    return buffer
