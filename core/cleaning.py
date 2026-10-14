"""Funciones reutilizables de limpieza y conversión de datos.

Hay dos tipos de funciones:
- De valor (clean_text, parse_number, parse_date, normalize_code): reciben un
  valor y devuelven el valor limpio o convertido. No saben nada del log.
- De DataFrame (remove_extra_spaces, remove_empty_rows, convert_columns,
  remove_duplicates): aplican las anteriores a columnas completas y registran
  cada cambio, hallazgo o eliminación en el AuditLog.
"""

import re
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from core.audit import AuditLog, data_columns, is_empty
from core.settings import DATE_FORMAT_TEXT, ERROR, SOURCE_FILE, SOURCE_ROW, WARNING

# Caracteres invisibles que llegan al copiar desde otros sistemas y no se ven en Excel.
INVISIBLE_CHARS = re.compile("[​‌‍⁠﻿­]")

# Espacios "raros" que deben tratarse como un espacio normal.
SPACE_CHARS = re.compile(r"[\s   ]+")

# Número con puntos de miles: 1.234 / 12.345.678
DOT_THOUSANDS = re.compile(r"\d{1,3}(\.\d{3})+")

# Número con comas de miles: 1,234 / 12,345,678
COMMA_THOUSANDS = re.compile(r"\d{1,3}(,\d{3})+")

# Fecha en texto dd/mm/aaaa, con hora opcional.
DATE_TEXT = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?")

# Fecha en texto aaaa-mm-dd (formato ISO, no es ambiguo).
DATE_ISO = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")

# Día 0 de las fechas seriales de Excel.
EXCEL_EPOCH = datetime(1899, 12, 30)

# Rango de seriales de Excel aceptados: 01/01/1900 a 31/12/9999.
EXCEL_SERIAL_MIN = 1
EXCEL_SERIAL_MAX = 2958465

# Acción sugerida para los valores que no se pudieron convertir.
FIX_AT_SOURCE = "Corregir el valor en el archivo de origen y volver a procesar"


# --- Funciones de valor -----------------------------------------------------


def clean_text(value: Any) -> Any:
    """Quita espacios sobrantes, saltos de línea y caracteres invisibles de un texto.

    No cambia tildes ni mayúsculas. Los valores que no son texto se devuelven igual.
    """
    if not isinstance(value, str):
        return value
    text = INVISIBLE_CHARS.sub("", value)
    return SPACE_CHARS.sub(" ", text).strip()


def parse_number(value: Any) -> float | None:
    """Convierte un valor a número. Devuelve None si está vacío.

    Acepta formato colombiano (1.234.567,89), estadounidense (1,234,567.89),
    símbolo $ y negativos con signo o entre paréntesis. Cuando hay un solo
    separador se asume el uso colombiano: la coma es decimal ("1,5" = 1.5) y un
    punto seguido de exactamente tres dígitos es de miles ("45.000" = 45000).

    Lanza ValueError si el valor no se puede interpretar como número; nunca
    devuelve cero en lugar de un valor inválido.
    """
    if is_empty(value):
        return None
    if isinstance(value, bool):
        raise ValueError("Es un valor verdadero/falso, no un número")
    if isinstance(value, (int, float)):
        return float(value)

    text = clean_text(str(value)).replace("$", "").replace(" ", "")
    if text == "":
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    if text.startswith("-"):
        negative = not negative
        text = text[1:]
    elif text.endswith("-"):
        negative = not negative
        text = text[:-1]

    integer_part, decimal_part = _split_number(text)
    if not integer_part.isdigit() or (decimal_part and not decimal_part.isdigit()):
        raise ValueError("No es un número válido")
    number = float(f"{integer_part}.{decimal_part or 0}")
    return -number if negative else number


def _split_number(text: str) -> tuple[str, str]:
    """Separa la parte entera y la decimal según los separadores que tenga el texto."""
    if "," in text and "." in text:
        # El último separador que aparece es el decimal.
        if text.rfind(",") > text.rfind("."):
            thousands, decimal = ".", ","
        else:
            thousands, decimal = ",", "."
        integer_part, _, decimal_part = text.rpartition(decimal)
        pattern = DOT_THOUSANDS if thousands == "." else COMMA_THOUSANDS
        if thousands in integer_part and not pattern.fullmatch(integer_part):
            raise ValueError("Los separadores de miles no están bien ubicados")
        return integer_part.replace(thousands, ""), decimal_part

    if "," in text:
        if text.count(",") > 1:
            if not COMMA_THOUSANDS.fullmatch(text):
                raise ValueError("Los separadores de miles no están bien ubicados")
            return text.replace(",", ""), ""
        integer_part, _, decimal_part = text.partition(",")
        return integer_part, decimal_part

    if "." in text:
        if DOT_THOUSANDS.fullmatch(text):
            return text.replace(".", ""), ""
        if text.count(".") > 1:
            raise ValueError("Los separadores de miles no están bien ubicados")
        integer_part, _, decimal_part = text.partition(".")
        return integer_part, decimal_part

    return text, ""


def is_ambiguous_number(value: Any) -> bool:
    """True si el texto puede leerse como miles en un formato y decimal en otro.

    Ejemplo: "1,234" es 1,234 (decimal) en formato colombiano y 1234 en formato
    estadounidense. Se convierte con la regla colombiana pero conviene revisarlo.
    """
    if not isinstance(value, str):
        return False
    text = clean_text(value).replace("$", "").replace(" ", "").strip("()-")
    return bool(re.fullmatch(r"\d{1,3},\d{3}", text))


def parse_date(value: Any) -> datetime | None:
    """Convierte un valor a fecha. Devuelve None si está vacío.

    Acepta fechas nativas de Excel, número serial de Excel, texto dd/mm/aaaa
    (siempre día/mes, nunca mes/día) y texto aaaa-mm-dd.
    Lanza ValueError si la fecha es inválida o ambigua (por ejemplo, año de dos dígitos).
    """
    if is_empty(value):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, bool):
        raise ValueError("Es un valor verdadero/falso, no una fecha")
    if isinstance(value, (int, float)):
        return _from_excel_serial(value)

    text = clean_text(str(value))
    if text == "":
        return None

    match = DATE_TEXT.fullmatch(text)
    if match:
        day, month, year, hour, minute, second = match.groups()
        if len(year) != 4:
            raise ValueError("El año debe tener cuatro dígitos (dd/mm/aaaa)")
        try:
            return datetime(
                int(year), int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0)
            )
        except ValueError:
            raise ValueError("La fecha no existe en el calendario") from None

    match = DATE_ISO.fullmatch(text)
    if match:
        year, month, day = match.groups()
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            raise ValueError("La fecha no existe en el calendario") from None

    if re.fullmatch(r"\d+(\.\d+)?", text):
        return _from_excel_serial(float(text))

    raise ValueError("No es una fecha válida (se espera dd/mm/aaaa)")


def _from_excel_serial(serial: float) -> datetime:
    """Convierte un número serial de Excel (días desde 1900) a fecha."""
    if not EXCEL_SERIAL_MIN <= serial <= EXCEL_SERIAL_MAX:
        raise ValueError("El número no corresponde a una fecha de Excel")
    result = EXCEL_EPOCH + timedelta(days=serial)
    # Se redondea al segundo para evitar residuos de la parte decimal.
    return result.replace(microsecond=0)


def normalize_code(value: Any) -> str | None:
    """Convierte un código a texto conservando los ceros a la izquierda.

    Quita el ".0" que aparece cuando Excel guardó el código como número.
    """
    if is_empty(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = clean_text(str(value))
    if text == "":
        return None
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".")[0]
    return text


def to_text(value: Any) -> str | None:
    """Convierte a texto los valores que Excel guardó como número o fecha.

    Los textos se devuelven sin cambios (la limpieza de espacios es otra regla).
    """
    if is_empty(value):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, datetime):
        return value.strftime(DATE_FORMAT_TEXT)
    return str(value)


# --- Funciones de DataFrame -------------------------------------------------


def remove_extra_spaces(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Aplica clean_text a todas las columnas y deja vacías las celdas que solo tenían espacios.

    Los reportes de las áreas suelen traer espacios invisibles que impiden
    detectar duplicados y cruzar códigos correctamente. Regla LIM-001.
    """
    df = df.copy()
    for column in data_columns(df):
        new_values = pd.Series(
            [_empty_to_none(clean_text(v)) for v in df[column]], index=df.index, dtype=object
        )
        audit.change_column(df, column, new_values, "LIM-001")
        df[column] = new_values
    return df


def _empty_to_none(value: Any) -> Any:
    return None if value == "" else value


def remove_empty_rows(df: pd.DataFrame, audit: AuditLog) -> pd.DataFrame:
    """Elimina las filas en las que todas las columnas están vacías. Regla LIM-002.

    Conviene ejecutarla después de remove_extra_spaces, para que las celdas con
    solo espacios ya cuenten como vacías.
    """
    columns = data_columns(df)
    empty = df[columns].map(is_empty).all(axis=1)
    return audit.remove_rows(df, empty, "LIM-002", "Fila sin datos")


def convert_columns(df: pd.DataFrame, column_types: dict[str, str], audit: AuditLog) -> pd.DataFrame:
    """Convierte cada columna al tipo indicado ("text", "code", "number", "currency", "date").

    "currency" se convierte igual que "number"; la diferencia es el formato de
    moneda en el archivo de salida.

    Las columnas "text" solo pasan a texto los valores que Excel guardó como
    número (por ejemplo 5 -> "5"); su contenido no se modifica.

    Los valores que no se pueden convertir se dejan como estaban y se registran
    como hallazgo de severidad Error, para que el usuario los vea resaltados.
    Solo se registra un cambio cuando el valor visible cambia (por ejemplo,
    "1.234,5" -> 1234.5), no cuando solo cambia el tipo ("1234" -> 1234).
    """
    df = df.copy()
    converters = {
        "number": (parse_number, "TIP-001", _same_number),
        "currency": (parse_number, "TIP-005", _same_number),
        "date": (parse_date, "TIP-002", _same_date),
        "code": (normalize_code, "TIP-003", _same_code),
        "text": (to_text, "TIP-004", _same_code),
    }
    for column, column_type in column_types.items():
        if column_type not in converters or column not in df.columns:
            continue
        converter, rule, is_same = converters[column_type]
        new_values = []
        changed = []
        for index, old in df[column].items():
            try:
                new = converter(old)
            except ValueError as error:
                audit.finding(
                    df.at[index, SOURCE_FILE], df.at[index, SOURCE_ROW], column, ERROR, rule,
                    str(error), old, FIX_AT_SOURCE,
                )
                new = old
            else:
                if column_type in ("number", "currency") and is_ambiguous_number(old):
                    audit.finding(
                        df.at[index, SOURCE_FILE], df.at[index, SOURCE_ROW], column, WARNING, rule,
                        f"Valor ambiguo: se interpretó la coma como decimal ({new})",
                        old, "Verificar si la coma era separador de miles",
                    )
            new_values.append(new)
            changed.append(not is_same(old, new))
        new_series = pd.Series(new_values, index=df.index, dtype=object)
        audit.change_column(df, column, new_series, rule, pd.Series(changed, index=df.index))
        df[column] = new_series
    return df


def _same_number(old: Any, new: Any) -> bool:
    """True si el texto original ya era un número simple con el mismo valor."""
    if is_empty(old) or is_empty(new):
        return is_empty(old) and is_empty(new)
    if isinstance(new, str):
        return True  # No se convirtió: no hay cambio
    if isinstance(old, (int, float)) and not isinstance(old, bool):
        return float(old) == new
    try:
        return float(str(old)) == new
    except ValueError:
        return False


def _same_date(old: Any, new: Any) -> bool:
    """True si el texto original ya mostraba la misma fecha en formato dd/mm/aaaa."""
    if is_empty(old) or is_empty(new):
        return is_empty(old) and is_empty(new)
    if isinstance(new, str):
        return True
    if isinstance(old, (datetime, date)):
        return True
    return str(old) in (new.strftime(DATE_FORMAT_TEXT), new.strftime(f"{DATE_FORMAT_TEXT} %H:%M:%S"))


def _same_code(old: Any, new: Any) -> bool:
    if is_empty(old) or is_empty(new):
        return is_empty(old) and is_empty(new)
    return str(old) == new


def remove_duplicates(df: pd.DataFrame, key: list[str], audit: AuditLog) -> pd.DataFrame:
    """Elimina los registros repetidos según las columnas de `key`. Regla DUP-001.

    Busca duplicados dentro de cada archivo y entre archivos. Se conserva la
    primera aparición y el motivo de cada eliminado indica cuál es el original.
    """
    duplicated = df.duplicated(subset=key, keep="first")
    if not duplicated.any():
        return df
    first_index = df.groupby(key, dropna=False, sort=False).ngroup()
    originals = df[~duplicated].assign(_group=first_index[~duplicated]).set_index("_group")
    reasons = pd.Series(
        [
            f"Duplicado del registro en {originals.at[g, SOURCE_FILE]}, fila {originals.at[g, SOURCE_ROW]}"
            for g in first_index
        ],
        index=df.index,
    )
    return audit.remove_rows(df, duplicated, "DUP-001", reasons)
