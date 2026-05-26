from __future__ import annotations

import csv
import io
from typing import Any, Final

from server.services.dataset.constants import HEADER_ALIASES
from server.services.dataset.detection import build_header_lookup, find_column


class SaesExportError(Exception):
    """
    Description:
        Raised when a dataset cannot be exported to SAES CSV format.
    """

    pass


SAES_FIELDNAMES: Final = [
    "Algorithm",
    "Instance",
    "MetricName",
    "ExecutionId",
    "MetricValue",
]

SAES_COLUMN_ALIASES: Final = {
    "Algorithm": HEADER_ALIASES["algorithm"],
    "Instance": HEADER_ALIASES["instance"],
    "MetricName": HEADER_ALIASES["metricname"],
    "ExecutionId": HEADER_ALIASES["executionid"],
    "MetricValue": HEADER_ALIASES["metricvalue"],
}

EVOLUTION_X_ALIASES: Final = HEADER_ALIASES["evolution_x"]

SaesColumns = dict[str, str]
RawRow = dict[str, Any]
SaesRow = dict[str, Any]
GroupKey = tuple[str, str, str, int]
SelectedRow = tuple[float, int, SaesRow]


def read_csv(dataset_bytes: bytes) -> tuple[list[str], list[RawRow]]:
    """
    Description:
        Read dataset CSV bytes.

    Args:
        dataset_bytes (bytes): Dataset CSV content.

    Returns:
        tuple[list[str], list[RawRow]]: CSV headers and rows.
    """

    if not isinstance(dataset_bytes, bytes):
        raise TypeError("Dataset content must be bytes")

    try:
        text = dataset_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise SaesExportError("CSV must be UTF-8 encoded") from error

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise SaesExportError("CSV has no header")

    rows = list(reader)

    if not rows:
        raise SaesExportError("CSV has no rows")

    return reader.fieldnames, rows


def detect_saes_columns(columns: list[str]) -> SaesColumns:
    """
    Description:
        Detect required SAES columns using configured aliases.

    Args:
        columns (list[str]): CSV headers.

    Returns:
        SaesColumns: Detected SAES column mapping.
    """

    lookup = build_header_lookup(columns)
    detected: SaesColumns = {}

    for canonical_name, aliases in SAES_COLUMN_ALIASES.items():
        column = find_column(lookup, aliases)

        if not column:
            raise SaesExportError(
                "Dataset cannot be exported to SAES format. "
                f"Missing required column: {canonical_name}"
            )

        detected[canonical_name] = column

    return detected


def detect_evolution_x_column(columns: list[str]) -> str | None:
    """
    Description:
        Detect whether the dataset contains an evolution X axis column.

    Args:
        columns (list[str]): CSV headers.

    Returns:
        str | None: Detected evolution X column.
    """

    lookup = build_header_lookup(columns)
    return find_column(lookup, EVOLUTION_X_ALIASES)


def is_empty(value: Any) -> bool:
    """
    Description:
        Check whether a CSV value is empty.

    Args:
        value (Any): Raw value.

    Returns:
        bool: Whether the value is empty.
    """

    return value is None or str(value).strip() == ""


def parse_float(value: Any, column_name: str, row_index: int) -> float:
    """
    Description:
        Parse a required numeric value.

    Args:
        value (Any): Raw value.
        column_name (str): Column name.
        row_index (int): CSV row number.

    Returns:
        float: Parsed numeric value.
    """

    if is_empty(value):
        raise SaesExportError(f"Empty {column_name} at row {row_index}")

    try:
        return float(str(value).strip())
    except ValueError as error:
        raise SaesExportError(
            f"Invalid {column_name} at row {row_index}: must be numeric"
        ) from error


def parse_int(value: Any, column_name: str, row_index: int) -> int:
    """
    Description:
        Parse a required integer value.

    Args:
        value (Any): Raw value.
        column_name (str): Column name.
        row_index (int): CSV row number.

    Returns:
        int: Parsed integer value.
    """

    if is_empty(value):
        raise SaesExportError(f"Empty {column_name} at row {row_index}")

    try:
        numeric_value = float(str(value).strip())
    except ValueError as error:
        raise SaesExportError(
            f"Invalid {column_name} at row {row_index}: must be an integer"
        ) from error

    if not numeric_value.is_integer():
        raise SaesExportError(
            f"Invalid {column_name} at row {row_index}: must be an integer"
        )

    return int(numeric_value)


def clean_text(value: Any, column_name: str, row_index: int) -> str:
    """
    Description:
        Parse a required non-empty text value.

    Args:
        value (Any): Raw value.
        column_name (str): Column name.
        row_index (int): CSV row number.

    Returns:
        str: Clean text value.
    """

    cleaned = str(value or "").strip()

    if not cleaned:
        raise SaesExportError(f"Empty {column_name} at row {row_index}")

    return cleaned


def build_saes_row(
    raw_row: RawRow,
    columns: SaesColumns,
    row_index: int,
) -> SaesRow:
    """
    Description:
        Convert one raw CSV row into a SAES-compatible row.

    Args:
        raw_row (RawRow): Raw CSV row.
        columns (SaesColumns): Detected SAES columns.
        row_index (int): CSV row number.

    Returns:
        SaesRow: SAES row.
    """

    return {
        "Algorithm": clean_text(
            raw_row.get(columns["Algorithm"]),
            "Algorithm",
            row_index,
        ),
        "Instance": clean_text(
            raw_row.get(columns["Instance"]),
            "Instance",
            row_index,
        ),
        "MetricName": clean_text(
            raw_row.get(columns["MetricName"]),
            "MetricName",
            row_index,
        ),
        "ExecutionId": parse_int(
            raw_row.get(columns["ExecutionId"]),
            "ExecutionId",
            row_index,
        ),
        "MetricValue": parse_float(
            raw_row.get(columns["MetricValue"]),
            "MetricValue",
            row_index,
        ),
    }


def write_saes_rows(rows: list[SaesRow]) -> bytes:
    """
    Description:
        Write SAES rows into UTF-8 CSV bytes.

    Args:
        rows (list[SaesRow]): SAES rows.

    Returns:
        bytes: SAES CSV bytes.
    """

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=SAES_FIELDNAMES)

    writer.writeheader()
    writer.writerows(rows)

    return output.getvalue().encode("utf-8")


def export_classic_saes(
    raw_rows: list[RawRow],
    columns: SaesColumns,
) -> bytes:
    """
    Description:
        Export a classic SAES dataset without evolution reduction.

    Args:
        raw_rows (list[RawRow]): Raw CSV rows.
        columns (SaesColumns): Detected SAES columns.

    Returns:
        bytes: SAES CSV bytes.
    """

    rows = [
        build_saes_row(raw_row, columns, row_index)
        for row_index, raw_row in enumerate(raw_rows, start=2)
    ]

    return write_saes_rows(rows)


def build_group_key(saes_row: SaesRow) -> GroupKey:
    """
    Description:
        Build the grouping key used to identify one final evolution point.

    Args:
        saes_row (SaesRow): SAES row.

    Returns:
        GroupKey: Algorithm, instance, metric and execution id key.
    """

    return (
        saes_row["Algorithm"],
        saes_row["Instance"],
        saes_row["MetricName"],
        saes_row["ExecutionId"],
    )


def sort_saes_row(saes_row: SaesRow) -> GroupKey:
    """
    Description:
        Build the sort key for deterministic SAES output.

    Args:
        saes_row (SaesRow): SAES row.

    Returns:
        GroupKey: Sort key.
    """

    return (
        saes_row["Algorithm"],
        saes_row["Instance"],
        saes_row["MetricName"],
        saes_row["ExecutionId"],
    )


def export_final_points_as_saes(
    raw_rows: list[RawRow],
    columns: SaesColumns,
    x_column: str,
) -> bytes:
    """
    Description:
        Export only the final evolution point per algorithm, instance, metric and run.

    Args:
        raw_rows (list[RawRow]): Raw CSV rows.
        columns (SaesColumns): Detected SAES columns.
        x_column (str): Evolution X axis column.

    Returns:
        bytes: SAES CSV bytes.
    """

    selected_by_group: dict[GroupKey, SelectedRow] = {}

    for row_index, raw_row in enumerate(raw_rows, start=2):
        saes_row = build_saes_row(raw_row, columns, row_index)
        x_value = parse_float(raw_row.get(x_column), x_column, row_index)
        key = build_group_key(saes_row)

        previous = selected_by_group.get(key)

        if previous is None or (x_value, row_index) > (previous[0], previous[1]):
            selected_by_group[key] = (x_value, row_index, saes_row)

    if not selected_by_group:
        raise SaesExportError("No valid rows were found to export to SAES format")

    final_rows = sorted(
        (selected[2] for selected in selected_by_group.values()),
        key=sort_saes_row,
    )

    return write_saes_rows(final_rows)


def export_saes_dataset(dataset_bytes: bytes) -> bytes:
    """
    Description:
        Export a dataset to SAES CSV format.

    Args:
        dataset_bytes (bytes): Source dataset CSV bytes.

    Returns:
        bytes: SAES-compatible CSV bytes.
    """

    columns, raw_rows = read_csv(dataset_bytes)
    detected_columns = detect_saes_columns(columns)
    x_column = detect_evolution_x_column(columns)

    if x_column:
        return export_final_points_as_saes(
            raw_rows=raw_rows,
            columns=detected_columns,
            x_column=x_column,
        )

    return export_classic_saes(
        raw_rows=raw_rows,
        columns=detected_columns,
    )
