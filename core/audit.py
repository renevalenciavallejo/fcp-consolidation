"""Registro de auditoría: todo cambio, hallazgo o eliminación pasa por aquí.

Si algo no quedó registrado en el AuditLog, no debió pasar.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from core.settings import DATE_FORMAT_TEXT, ERROR, INFO, INTERNAL_PREFIX, SOURCE_FILE, SOURCE_ROW, WARNING

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


@dataclass
class Action:
    """Cualquier registro del log (cambio, hallazgo, eliminación, columna o transformación),
    con el paso en el que ocurrió. En orden, permiten reconstruir todo lo que se hizo."""

    step: str
    item: Change | Finding | Removal | AddedColumn | Transformation


# Columnas de la tabla de acciones, en el orden en que las ve el usuario. Después
# vienen todas las columnas del registro. "Archivo" solo se muestra con varios archivos.
ACTION_COLUMNS = ["Paso", "Archivo", "Fila", "Acción", "Columna", "Detalle", "Qué hacer", "Regla"]


@dataclass
class Step:
    """Un paso del log de ejecución: qué se hizo y su resultado."""

    title: str
    details: list[str] = field(default_factory=list)


# Marcas de las líneas del log de ejecución.
STEP_MARK = "▸"
OK_MARK = "✓"
FAIL_MARK = "✗"
# Cantidad máxima de filas que se listan en el resultado de un paso.
MAX_ROWS_LISTED = 10


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

    def __init__(self, rules: dict[str, str], on_line: Callable[[str], None] | None = None):
        self.rules = rules
        self.changes: list[Change] = []
        self.findings: list[Finding] = []
        self.removals: list[Removal] = []
        self.added_columns: list[AddedColumn] = []
        self.transformations: list[Transformation] = []
        # Todos los registros anteriores en el orden en que ocurrieron.
        self.actions: list[Action] = []
        # Log de ejecución: pasos en el orden en que ocurrieron.
        self.steps: list[Step] = []
        # Recibe cada línea del log de ejecución apenas se produce (la interfaz la muestra en vivo).
        self.on_line = on_line
        # Con varios archivos de entrada, las filas del log de ejecución se indican con el
        # nombre del archivo; con uno solo sería repetitivo. Lo define el ejecutor.
        self.multiple_files = False
        # Registros tal como se leyeron de los archivos, por (archivo, fila). Los guarda el
        # ejecutor para que la tabla de acciones muestre el registro completo de cada acción.
        self.source_rows: dict[tuple[str, int], dict] = {}
        self._open_step: Step | None = None
        self._step_start: dict[str, int] = {}

    def _check_rule(self, rule: str) -> None:
        if rule not in self.rules:
            raise ValueError(f"La regla '{rule}' no está declarada en el catálogo de reglas.")

    def remember_source_rows(self, df: pd.DataFrame) -> None:
        """Guarda los registros tal como se leyeron, para mostrarlos en la tabla de acciones."""
        columns = data_columns(df)
        for index in df.index:
            key = (df.at[index, SOURCE_FILE], int(df.at[index, SOURCE_ROW]))
            self.source_rows[key] = {c: _clean(df.at[index, c]) for c in columns}

    def _record(self, item) -> None:
        """Guarda el registro en el orden en que ocurrió, junto con el paso en curso."""
        self.actions.append(Action(self._open_step.title if self._open_step else "", item))

    # --- Log de ejecución ---------------------------------------------------

    def step(self, title: str) -> None:
        """Empieza un paso del log de ejecución (y cierra el anterior, si lo hay).

        Lo que se registre hasta el siguiente paso se resume como resultado de este.
        """
        self.finish_step()
        self._open_step = Step(title)
        self.steps.append(self._open_step)
        self._step_start = self._counts()
        self._emit(f"{STEP_MARK} {title}")

    def note(self, text: str, ok: bool = True) -> None:
        """Agrega un resultado escrito a mano al paso actual (✓ si salió bien, ✗ si no)."""
        if self._open_step is None:
            raise ValueError("No hay un paso abierto: llame primero a step().")
        line = f"{OK_MARK if ok else FAIL_MARK} {text}"
        self._open_step.details.append(line)
        self._emit(f"   {line}")

    def finish_step(self) -> None:
        """Cierra el paso actual. Si no tuvo notas, se resume lo que se registró durante el paso."""
        if self._open_step is None:
            return
        if not self._open_step.details:
            self.note(self.step_summary())
        self._open_step = None

    def steps_df(self) -> pd.DataFrame:
        """Log de ejecución como tabla: una fila por cada resultado de cada paso."""
        rows = [
            {"Paso": step.title, "Resultado": detail}
            for step in self.steps
            for detail in step.details or [""]
        ]
        return pd.DataFrame(rows, columns=["Paso", "Resultado"])

    def step_lines(self) -> list[str]:
        """Log de ejecución como texto, una línea por paso y por resultado."""
        lines = []
        for step in self.steps:
            lines.append(f"{STEP_MARK} {step.title}")
            lines.extend(f"   {detail}" for detail in step.details)
        return lines

    def _emit(self, line: str) -> None:
        if self.on_line is not None:
            self.on_line(line)

    def _counts(self) -> dict[str, int]:
        return {
            "changes": len(self.changes),
            "findings": len(self.findings),
            "removals": len(self.removals),
            "added_columns": len(self.added_columns),
            "transformations": len(self.transformations),
        }

    def step_summary(self) -> str:
        """Texto con lo que se registró desde que empezó el paso actual.

        Es el resultado que se pone solo al cerrar un paso sin notas. Una etapa lo
        puede usar con note() cuando quiere agregar más detalle debajo.
        """
        start = self._step_start
        changes = self.changes[start["changes"]:]
        findings = self.findings[start["findings"]:]
        removals = self.removals[start["removals"]:]
        parts = []
        if removals:
            parts.append(f"{_plural(len(removals), 'fila eliminada', 'filas eliminadas')}: {_rows_text(removals, self.multiple_files)}")
        if changes:
            cells = len({(c.source_file, c.source_row, c.column) for c in changes})
            parts.append(_plural(cells, "celda modificada", "celdas modificadas"))
        if findings:
            counts = {severity: 0 for severity in SEVERITIES}
            for finding in findings:
                counts[finding.severity] += 1
            by_severity = [f"{count} {severity}" for severity, count in counts.items() if count]
            parts.append(f"{_plural(len(findings), 'hallazgo', 'hallazgos')} ({', '.join(by_severity)})")
        for added in self.added_columns[start["added_columns"]:]:
            parts.append(f"Columna «{added.column}» agregada en {_plural(added.rows, 'fila', 'filas')}")
        for item in self.transformations[start["transformations"]:]:
            parts.append(item.detail)
        return " · ".join(parts) if parts else "Sin cambios"

    # --- Registro de un elemento -------------------------------------------

    def change(self, source_file, source_row, column, old_value, new_value, rule) -> None:
        """Registra que una celda cambió de valor."""
        self._check_rule(rule)
        item = Change(source_file, int(source_row), column, _clean(old_value), _clean(new_value), rule)
        self.changes.append(item)
        self._record(item)

    def finding(
        self, source_file, source_row, column, severity, rule, description, value, suggested_action
    ) -> None:
        """Registra un hallazgo que el usuario debe revisar."""
        self._check_rule(rule)
        if severity not in SEVERITIES:
            raise ValueError(f"Severidad '{severity}' no válida. Use una de: {', '.join(SEVERITIES)}")
        item = Finding(
            source_file, int(source_row), column, severity, rule,
            description, _clean(value), suggested_action,
        )
        self.findings.append(item)
        self._record(item)

    def removal(self, source_file, source_row, rule, reason, row_data) -> None:
        """Registra que un registro completo se eliminó."""
        self._check_rule(rule)
        clean_data = {k: _clean(v) for k, v in row_data.items()}
        item = Removal(source_file, int(source_row), rule, reason, clean_data)
        self.removals.append(item)
        self._record(item)

    def column_added(self, column: str, rule: str, rows: int) -> None:
        """Registra que se agregó una columna calculada.

        Se registra una vez por columna (no celda por celda) y aparece en la hoja
        Resumen del log, con la regla y la cantidad de filas.
        """
        self._check_rule(rule)
        item = AddedColumn(column, rule, rows)
        self.added_columns.append(item)
        self._record(item)

    def transformation(self, rule: str, detail: str) -> None:
        """Registra una transformación que afecta toda la tabla y no celdas puntuales
        (por ejemplo, ordenar los registros). Aparece en la hoja Resumen del log."""
        self._check_rule(rule)
        item = Transformation(rule, detail)
        self.transformations.append(item)
        self._record(item)

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

    def actions_df(self) -> pd.DataFrame:
        """Todo lo que se hizo, en el orden en que ocurrió: una fila por acción.

        Une hallazgos, cambios, eliminaciones, columnas agregadas y transformaciones
        en una sola tabla, para que el usuario no tenga que cruzar varias hojas.
        """
        base = [c for c in ACTION_COLUMNS if c != "Archivo" or self.multiple_files]
        rows = []
        record_columns: list[str] = []
        for action in self.actions:
            row = _action_row(action)
            record = self._record_data(action.item)
            for column in record:
                if column not in record_columns and column not in ACTION_COLUMNS:
                    record_columns.append(column)
            rows.append({**record, **row})  # Si un nombre coincide, prima el de la acción
        return pd.DataFrame(rows, columns=base + record_columns)

    def _record_data(self, item) -> dict:
        """Registro completo de una acción: el eliminado tal como estaba al eliminarlo, o el
        registro original del archivo. Las acciones sobre toda la tabla no tienen registro."""
        if isinstance(item, Removal):
            return item.row_data
        if isinstance(item, (Change, Finding)):
            return self.source_rows.get((item.source_file, item.source_row), {})
        return {}

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


def _action_row(action: Action) -> dict:
    """Una acción como fila de la tabla de acciones, con textos para el usuario."""
    item = action.item
    row = {column: "" for column in ACTION_COLUMNS}
    row["Paso"] = action.step
    row["Regla"] = item.rule
    if isinstance(item, (Change, Finding, Removal)):
        row["Archivo"] = item.source_file
        row["Fila"] = item.source_row
    if isinstance(item, Change):
        row["Acción"] = "Valor modificado"
        row["Columna"] = item.column
        row["Detalle"] = f"{_show(item.old_value)} → {_show(item.new_value)}"
    elif isinstance(item, Finding):
        row["Acción"] = f"Hallazgo ({item.severity})"
        row["Columna"] = item.column
        row["Detalle"] = f"{item.description}. Valor: {_show(item.value)}"
        row["Qué hacer"] = item.suggested_action
    elif isinstance(item, Removal):
        row["Acción"] = "Fila eliminada"
        row["Detalle"] = item.reason
    elif isinstance(item, AddedColumn):
        row["Acción"] = "Columna agregada"
        row["Columna"] = item.column
        row["Detalle"] = f"Columna «{item.column}» agregada en {_plural(item.rows, 'fila', 'filas')}"
    else:
        row["Acción"] = "Transformación"
        row["Detalle"] = item.detail
    return row


def _show(value: Any) -> str:
    """Valor como texto para el usuario. Los textos van entre «» para distinguir
    «1234» (texto) de 1234 (número), que es justamente lo que cambia al convertir."""
    if is_empty(value):
        return "(vacío)"
    if isinstance(value, str):
        return f"«{value}»"
    if isinstance(value, datetime):
        return value.strftime(DATE_FORMAT_TEXT)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _plural(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _rows_text(removals: list[Removal], with_file: bool) -> str:
    """Filas eliminadas como texto («filas 1, 2 y 3»), agrupadas por archivo si `with_file`.

    Se listan como máximo MAX_ROWS_LISTED filas; el detalle completo está en Eliminados.
    """
    by_file: dict[str, list[int]] = {}
    for removal in removals:
        by_file.setdefault(removal.source_file, []).append(removal.source_row)
    texts = []
    for name, rows in by_file.items():
        listed = [str(r) for r in rows[:MAX_ROWS_LISTED]]
        if len(rows) > MAX_ROWS_LISTED:
            rows_text = f"{', '.join(listed)} y {len(rows) - MAX_ROWS_LISTED} más"
        elif len(listed) > 1:
            rows_text = f"{', '.join(listed[:-1])} y {listed[-1]}"
        else:
            rows_text = listed[0]
        prefix = f"{name}: " if with_file else ""
        texts.append(f"{prefix}{'fila' if len(rows) == 1 else 'filas'} {rows_text}")
    return "; ".join(texts)


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
