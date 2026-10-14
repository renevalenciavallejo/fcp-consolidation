"""Registro de auditoría: todo cambio, hallazgo o eliminación pasa por aquí.

Si algo no quedó registrado en el AuditLog, no debió pasar.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from core.settings import ERROR, INFO, INTERNAL_PREFIX, SOURCE_FILE, SOURCE_ROW, WARNING

SEVERITIES = (ERROR, WARNING, INFO)


@dataclass
class Change:
    source_file: str
    source_row: int
    column: str
    old_value: Any
    new_value: Any
    rule: str


@dataclass
class Finding:
    source_file: str
    source_row: int
    column: str
    severity: str
    rule: str
    description: str
    value: Any
    suggested_action: str


@dataclass
class Removal:
    source_file: str
    source_row: int
    rule: str
    reason: str
    row_data: dict


@dataclass
class AddedColumn:
    column: str
    rule: str
    rows: int


@dataclass
class Transformation:
    rule: str
    detail: str


def is_empty(value: Any) -> bool:
    """True si el valor está vacío (None, NaN o NaT). Un cero NO es vacío."""
    return value is None or (not isinstance(value, (list, dict)) and bool(pd.isna(value)))


def data_columns(df: pd.DataFrame) -> list[str]:
    """Columnas del DataFrame sin las columnas internas (_source_file, _source_row)."""
    return [c for c in df.columns if not str(c).startswith(INTERNAL_PREFIX)]


class AuditLog:
    """Acumula los cambios, hallazgos y eliminaciones de un procesamiento.

    Recibe el catálogo de reglas permitidas para que un código mal escrito se
    detecte de inmediato y no aparezca en el log una regla sin descripción.
    """

    def __init__(self, rules: dict[str, str]):
        self.rules = rules
        self.changes: list[Change] = []
        self.findings: list[Finding] = []
        self.removals: list[Removal] = []
        self.added_columns: list[AddedColumn] = []
        self.transformations: list[Transformation] = []

    def _check_rule(self, rule: str) -> None:
        if rule not in self.rules:
            raise ValueError(f"La regla '{rule}' no está declarada en el catálogo de reglas.")

    # --- Registro de un elemento -------------------------------------------

    def change(self, source_file, source_row, column, old_value, new_value, rule) -> None:
        """Registra que una celda cambió de valor."""
        self._check_rule(rule)
        self.changes.append(
            Change(source_file, int(source_row), column, _clean(old_value), _clean(new_value), rule)
        )

    def finding(
        self, source_file, source_row, column, severity, rule, description, value, suggested_action
    ) -> None:
        """Registra un hallazgo que el usuario debe revisar."""
        self._check_rule(rule)
        if severity not in SEVERITIES:
            raise ValueError(f"Severidad '{severity}' no válida. Use una de: {', '.join(SEVERITIES)}")
        self.findings.append(
            Finding(
                source_file, int(source_row), column, severity, rule,
                description, _clean(value), suggested_action,
            )
        )

    def removal(self, source_file, source_row, rule, reason, row_data) -> None:
        """Registra que un registro completo se eliminó."""
        self._check_rule(rule)
        clean_data = {k: _clean(v) for k, v in row_data.items()}
        self.removals.append(Removal(source_file, int(source_row), rule, reason, clean_data))

    def column_added(self, column: str, rule: str, rows: int) -> None:
        """Registra que se agregó una columna calculada.

        Se registra una vez por columna (no celda por celda) y aparece en la hoja
        Resumen del log, con la regla y la cantidad de filas.
        """
        self._check_rule(rule)
        self.added_columns.append(AddedColumn(column, rule, rows))

    def transformation(self, rule: str, detail: str) -> None:
        """Registra una transformación que afecta toda la tabla y no celdas puntuales
        (por ejemplo, ordenar los registros). Aparece en la hoja Resumen del log."""
        self._check_rule(rule)
        self.transformations.append(Transformation(rule, detail))

    # --- Registro en bloque -------------------------------------------------

    def change_column(
        self,
        df: pd.DataFrame,
        column: str,
        new_values: pd.Series,
        rule: str,
        changed: pd.Series | None = None,
    ) -> None:
        """Registra los cambios de una columna completa, solo en las celdas que cambian.

        `changed` es una máscara opcional que indica qué filas cambiaron; si no se
        da, se compara el valor anterior con el nuevo. Sirve cuando el valor cambia
        de tipo pero no de contenido (por ejemplo, "1234" -> 1234.0).
        """
        old_values = df[column]
        if changed is None:
            changed = pd.Series(
                [not _same(o, n) for o, n in zip(old_values, new_values)], index=df.index
            )
        for index in df.index[changed.to_numpy(dtype=bool)]:
            self.change(
                df.at[index, SOURCE_FILE], df.at[index, SOURCE_ROW], column,
                old_values.at[index], new_values.at[index], rule,
            )

    def finding_column(
        self,
        df: pd.DataFrame,
        mask: pd.Series,
        column: str,
        severity: str,
        rule: str,
        description: str,
        suggested_action: str,
    ) -> None:
        """Registra el mismo hallazgo para todas las filas marcadas en `mask`."""
        for index in df.index[mask.to_numpy(dtype=bool)]:
            self.finding(
                df.at[index, SOURCE_FILE], df.at[index, SOURCE_ROW], column, severity,
                rule, description, df.at[index, column], suggested_action,
            )

    def remove_rows(
        self, df: pd.DataFrame, mask: pd.Series, rule: str, reason: str | pd.Series
    ) -> pd.DataFrame:
        """Registra y quita las filas marcadas en `mask`. Devuelve el DataFrame sin ellas.

        `reason` puede ser un texto igual para todas las filas o una Series con un
        motivo por fila (por ejemplo, de qué registro es duplicado).
        """
        columns = data_columns(df)
        for index in df.index[mask.to_numpy(dtype=bool)]:
            row_reason = reason.at[index] if isinstance(reason, pd.Series) else reason
            row_data = {c: df.at[index, c] for c in columns}
            self.removal(df.at[index, SOURCE_FILE], df.at[index, SOURCE_ROW], rule, row_reason, row_data)
        return df[~mask.to_numpy(dtype=bool)]

    # --- Consulta -----------------------------------------------------------

    def findings_by_severity(self) -> dict[str, int]:
        """Cantidad de hallazgos por severidad (incluye las severidades sin hallazgos)."""
        counts = {severity: 0 for severity in SEVERITIES}
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts

    def rule_counts(self) -> dict[str, int]:
        """Cuántas veces se aplicó cada regla (cambios + hallazgos + eliminaciones + filas calculadas)."""
        counts: dict[str, int] = {}
        for item in [*self.changes, *self.findings, *self.removals]:
            counts[item.rule] = counts.get(item.rule, 0) + 1
        for added in self.added_columns:
            counts[added.rule] = counts.get(added.rule, 0) + added.rows
        for item in self.transformations:
            counts[item.rule] = counts.get(item.rule, 0) + 1
        return dict(sorted(counts.items()))

    def findings_df(self) -> pd.DataFrame:
        """Hallazgos como tabla, con los encabezados que ve el usuario."""
        return pd.DataFrame(
            [
                {
                    "Archivo origen": f.source_file,
                    "Fila origen": f.source_row,
                    "Columna": f.column,
                    "Severidad": f.severity,
                    "Código de regla": f.rule,
                    "Descripción": f.description,
                    "Valor encontrado": f.value,
                    "Acción sugerida": f.suggested_action,
                }
                for f in self.findings
            ],
            columns=[
                "Archivo origen", "Fila origen", "Columna", "Severidad", "Código de regla",
                "Descripción", "Valor encontrado", "Acción sugerida",
            ],
        )

    def changes_df(self) -> pd.DataFrame:
        """Cambios como tabla, con los encabezados que ve el usuario."""
        return pd.DataFrame(
            [
                {
                    "Archivo origen": c.source_file,
                    "Fila origen": c.source_row,
                    "Columna": c.column,
                    "Valor anterior": c.old_value,
                    "Valor nuevo": c.new_value,
                    "Código de regla": c.rule,
                    "Descripción de la regla": self.rules[c.rule],
                }
                for c in self.changes
            ],
            columns=[
                "Archivo origen", "Fila origen", "Columna", "Valor anterior", "Valor nuevo",
                "Código de regla", "Descripción de la regla",
            ],
        )

    def removals_df(self) -> pd.DataFrame:
        """Eliminados como tabla: datos de origen y motivo, seguidos del registro completo."""
        base = ["Archivo origen", "Fila origen", "Código de regla", "Motivo"]
        record_columns: list[str] = []
        for r in self.removals:
            for column in r.row_data:
                if column not in record_columns and column not in base:
                    record_columns.append(column)
        rows = [
            {
                "Archivo origen": r.source_file,
                "Fila origen": r.source_row,
                "Código de regla": r.rule,
                "Motivo": r.reason,
                **r.row_data,
            }
            for r in self.removals
        ]
        return pd.DataFrame(rows, columns=base + record_columns)


def _clean(value: Any) -> Any:
    """Normaliza vacíos a None para que el log no muestre 'nan' o 'NaT'."""
    if is_empty(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


def _same(old: Any, new: Any) -> bool:
    """True si dos valores son iguales, considerando iguales dos vacíos."""
    if is_empty(old) and is_empty(new):
        return True
    if is_empty(old) or is_empty(new):
        return False
    # "1" y 1 no son lo mismo: un cambio de tipo también es un cambio.
    same_type = isinstance(old, type(new)) or isinstance(new, type(old))
    return same_type and old == new
