from __future__ import annotations

import csv
import math
from dataclasses import asdict
from io import StringIO
from typing import Any

from server.services.dataset.detection import detect_dataset_capabilities
from server.services.dataset.exceptions import DatasetFormatError


def normalize_dataset(data: bytes) -> str:
    """
    Description:
        Decode dataset bytes using UTF-8 with BOM support.

    Args:
        data (bytes): Dataset content.

    Returns:
        str: Decoded CSV text.
    """

    if not isinstance(data, bytes):
        raise TypeError("Dataset content must be bytes")

    return data.decode("utf-8-sig")


def read_csv(data: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Description:
        Read CSV bytes into fieldnames and dictionary rows.

    Args:
        data (bytes): CSV content.

    Returns:
        tuple[list[str], list[dict[str, Any]]]: CSV headers and rows.
    """

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DatasetFormatError("CSV must be UTF-8 encoded") from error

    reader = csv.DictReader(StringIO(text))

    if not reader.fieldnames:
        raise DatasetFormatError("CSV has no header")

    return reader.fieldnames, list(reader)


def is_empty(value: Any) -> bool:
    """
    Description:
        Check whether a raw CSV value is empty.

    Args:
        value (Any): Raw value.

    Returns:
        bool: Whether the value is empty.
    """

    return value is None or str(value).strip() == ""


def parse_int(value: Any, row_index: int, column_name: str) -> int:
    """
    Description:
        Parse a required integer value from a CSV cell.

    Args:
        value (Any): Raw CSV value.
        row_index (int): CSV row number.
        column_name (str): Column name.

    Returns:
        int: Parsed integer.
    """

    if is_empty(value):
        raise DatasetFormatError(f"Empty {column_name} at row {row_index}")

    try:
        return int(float(str(value).strip()))
    except ValueError as error:
        raise DatasetFormatError(
            f"Invalid {column_name} at row {row_index}: must be an integer"
        ) from error


def parse_float(value: Any, row_index: int, column_name: str) -> float:
    """
    Description:
        Parse a required numeric value from a CSV cell.

    Args:
        value (Any): Raw CSV value.
        row_index (int): CSV row number.
        column_name (str): Column name.

    Returns:
        float: Parsed numeric value.
    """

    if is_empty(value):
        raise DatasetFormatError(f"Empty {column_name} at row {row_index}")

    try:
        parsed = float(str(value).strip())
    except ValueError as error:
        raise DatasetFormatError(
            f"Invalid {column_name} at row {row_index}: must be numeric"
        ) from error

    if math.isnan(parsed):
        raise DatasetFormatError(
            f"Invalid {column_name} at row {row_index}: NaN is not allowed"
        )

    return parsed


def parse_optional_int(value: Any, row_index: int, column_name: str) -> int | None:
    """
    Description:
        Parse an optional integer value from a CSV cell.

    Args:
        value (Any): Raw CSV value.
        row_index (int): CSV row number.
        column_name (str): Column name.

    Returns:
        int | None: Parsed integer or None.
    """

    return None if is_empty(value) else parse_int(value, row_index, column_name)


def get_required_text(
    raw_row: dict[str, Any],
    column_name: str | None,
    row_index: int,
    label: str,
) -> str:
    """
    Description:
        Extract a required text value from a CSV row.

    Args:
        raw_row (dict[str, Any]): Raw CSV row.
        column_name (str | None): Column name.
        row_index (int): CSV row number.
        label (str): Display label.

    Returns:
        str: Clean text value.
    """

    if not column_name:
        raise DatasetFormatError(f"Missing {label} column at row {row_index}")

    value = str(raw_row.get(column_name, "")).strip()

    if not value:
        raise DatasetFormatError(f"Empty {label} at row {row_index}")

    return value


def get_optional_text(raw_row: dict[str, Any], column_name: str | None) -> str | None:
    """
    Description:
        Extract an optional text value from a CSV row.

    Args:
        raw_row (dict[str, Any]): Raw CSV row.
        column_name (str | None): Column name.

    Returns:
        str | None: Clean text or None.
    """

    if not column_name:
        return None

    value = str(raw_row.get(column_name, "")).strip()
    return value or None


def build_base_row(
    raw_row: dict[str, Any],
    columns: dict[str, str | None],
    capabilities: dict[str, bool],
    row_index: int,
) -> dict[str, Any]:
    """
    Description:
        Build the common normalized row structure.

    Args:
        raw_row (dict[str, Any]): Raw CSV row.
        columns (dict[str, str | None]): Detected columns.
        capabilities (dict[str, bool]): Detected capabilities.
        row_index (int): CSV row number.

    Returns:
        dict[str, Any]: Normalized base row.
    """

    executionid_column = columns.get("executionid")
    metricvalue_column = columns.get("metricvalue")

    return {
        "capabilities": capabilities,
        "algorithm": get_required_text(
            raw_row,
            columns.get("algorithm"),
            row_index,
            "Algorithm",
        ),
        "instance": get_optional_text(raw_row, columns.get("instance")),
        "metricname": get_optional_text(raw_row, columns.get("metricname")),
        "executionid": (
            parse_optional_int(
                raw_row.get(executionid_column),
                row_index,
                executionid_column,
            )
            if executionid_column
            else None
        ),
        "metricvalue": (
            parse_float(
                raw_row.get(metricvalue_column),
                row_index,
                metricvalue_column,
            )
            if metricvalue_column
            else None
        ),
        "evolution_x": None,
        "evolution_y": None,
        "evolution_run": None,
    }


def apply_saes_fields(
    parsed_row: dict[str, Any],
    raw_row: dict[str, Any],
    columns: dict[str, str | None],
    row_index: int,
) -> None:
    """
    Description:
        Fill required SAES fields in a normalized row.

    Args:
        parsed_row (dict[str, Any]): Normalized row to update.
        raw_row (dict[str, Any]): Raw CSV row.
        columns (dict[str, str | None]): Detected columns.
        row_index (int): CSV row number.

    Returns:
        None
    """

    parsed_row["instance"] = get_required_text(
        raw_row,
        columns.get("instance"),
        row_index,
        "Instance",
    )
    parsed_row["metricname"] = get_required_text(
        raw_row,
        columns.get("metricname"),
        row_index,
        "MetricName",
    )
    parsed_row["executionid"] = parse_int(
        raw_row.get(columns["executionid"]),
        row_index,
        "ExecutionId",
    )
    parsed_row["metricvalue"] = parse_float(
        raw_row.get(columns["metricvalue"]),
        row_index,
        "MetricValue",
    )


def apply_evolution_fields(
    parsed_row: dict[str, Any],
    raw_row: dict[str, Any],
    columns: dict[str, str | None],
    row_index: int,
) -> None:
    """
    Description:
        Fill required evolution fields in a normalized row.

    Args:
        parsed_row (dict[str, Any]): Normalized row to update.
        raw_row (dict[str, Any]): Raw CSV row.
        columns (dict[str, str | None]): Detected columns.
        row_index (int): CSV row number.

    Returns:
        None
    """

    x_column = columns.get("evolution_x")
    y_column = columns.get("metricvalue")
    run_column = columns.get("executionid")

    if not x_column or not y_column:
        raise DatasetFormatError("Internal evolution detection error")

    parsed_row["evolution_x"] = parse_float(
        raw_row.get(x_column),
        row_index,
        x_column,
    )
    parsed_row["evolution_y"] = parse_float(
        raw_row.get(y_column),
        row_index,
        y_column,
    )
    parsed_row["evolution_run"] = (
        parse_optional_int(raw_row.get(run_column), row_index, run_column)
        if run_column
        else None
    )


def parse_dataset(data: bytes) -> tuple[list[dict], dict[str, bool]]:
    """
    Description:
        Parse a CSV dataset into normalized rows and capabilities.

    Args:
        data (bytes): CSV dataset content.

    Returns:
        tuple[list[dict], dict[str, bool]]: Parsed rows and capabilities.
    """

    original_headers, raw_rows = read_csv(data)
    detection = detect_dataset_capabilities(original_headers)

    if (
        not detection.capabilities["saes_plots"]
        and not detection.capabilities["evolution_plots"]
    ):
        raise DatasetFormatError(
            "Unsupported dataset format. Missing SAES columns: "
            f"{', '.join(detection.missing_columns['saes'])}. "
            "Missing evolution columns: "
            f"{', '.join(detection.missing_columns['evolution'])}."
        )

    rows: list[dict] = []

    for row_index, raw_row in enumerate(raw_rows, start=2):
        parsed_row = build_base_row(
            raw_row=raw_row,
            columns=detection.detected_columns,
            capabilities=detection.capabilities,
            row_index=row_index,
        )

        if detection.capabilities["saes_plots"]:
            apply_saes_fields(
                parsed_row=parsed_row,
                raw_row=raw_row,
                columns=detection.detected_columns,
                row_index=row_index,
            )

        if detection.capabilities["evolution_plots"]:
            apply_evolution_fields(
                parsed_row=parsed_row,
                raw_row=raw_row,
                columns=detection.detected_columns,
                row_index=row_index,
            )

        rows.append(parsed_row)

    return rows, detection.capabilities


def inspect_dataset(data: bytes) -> dict:
    """
    Description:
        Inspect dataset columns, row count and detected capabilities.

    Args:
        data (bytes): CSV dataset content.

    Returns:
        dict: Inspection result.
    """

    original_headers, raw_rows = read_csv(data)
    detection = detect_dataset_capabilities(original_headers)

    return {
        **asdict(detection),
        "columns": original_headers,
        "row_count": len(raw_rows),
    }
