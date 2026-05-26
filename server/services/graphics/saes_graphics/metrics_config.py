from __future__ import annotations

import csv
import io
from typing import Final

VALID_DIRECTIONS: Final = {"maximize", "minimize"}

DEFAULT_METRIC_DIRECTIONS: Final = {
    "ERROR": "minimize",
    "FITNESS": "maximize",
    "ACCURACY": "maximize",
    "HV": "maximize",
    "EPSILON": "minimize",
    "IGD": "minimize",
}

METRICS_CSV_COLUMNS: Final = {"MetricName", "Maximize"}


def normalize_metric_name(metric: str) -> str:
    """
    Description:
        Normalize a metric name for case-insensitive matching.

    Args:
        metric (str): Metric name.

    Returns:
        str: Normalized metric name.
    """

    return metric.strip().upper()


def get_default_metrics_direction(metrics: list[str]) -> dict[str, str]:
    """
    Description:
        Resolve default optimization directions for metrics.

    Args:
        metrics (list[str]): Metric names.

    Returns:
        dict[str, str]: Direction by metric name.
    """

    return {
        metric: DEFAULT_METRIC_DIRECTIONS.get(
            normalize_metric_name(metric),
            "maximize",
        )
        for metric in metrics
        if isinstance(metric, str) and metric.strip()
    }


def build_expected_metrics_lookup(metrics: list[str]) -> dict[str, str]:
    """
    Description:
        Build a normalized metric lookup preserving original metric names.

    Args:
        metrics (list[str]): Expected metric names.

    Returns:
        dict[str, str]: Normalized metric name to original metric name.
    """

    return {
        normalize_metric_name(metric): metric
        for metric in metrics
        if isinstance(metric, str) and metric.strip()
    }


def parse_metrics_csv(
    csv_bytes: bytes,
    expected_metrics: list[str],
) -> dict[str, str]:
    """
    Description:
        Parse a metrics configuration CSV.

    Args:
        csv_bytes (bytes): Metrics CSV bytes.
        expected_metrics (list[str]): Metrics expected in the dataset.

    Returns:
        dict[str, str]: Direction by metric name.
    """

    try:
        content = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Invalid metrics CSV encoding") from error

    reader = csv.DictReader(io.StringIO(content))

    if not reader.fieldnames:
        raise ValueError("Metrics CSV is empty")

    fieldnames = {field.strip() for field in reader.fieldnames if field}

    if not METRICS_CSV_COLUMNS.issubset(fieldnames):
        raise ValueError("Metrics CSV must contain 'MetricName' and 'Maximize' columns")

    expected_lookup = build_expected_metrics_lookup(expected_metrics)
    resolved = get_default_metrics_direction(expected_metrics)

    for row_index, row in enumerate(reader, start=2):
        metric_name = (row.get("MetricName") or "").strip()
        maximize_value = (row.get("Maximize") or "").strip().lower()

        if not metric_name:
            raise ValueError(
                f"MetricName cannot be empty in metrics CSV at row {row_index}"
            )

        normalized_metric = normalize_metric_name(metric_name)

        if normalized_metric not in expected_lookup:
            raise ValueError(f"Unknown metric '{metric_name}' in metrics CSV")

        if maximize_value not in {"true", "false"}:
            raise ValueError(
                f"Invalid Maximize value for metric '{metric_name}'. Use True or False."
            )

        resolved[expected_lookup[normalized_metric]] = (
            "maximize" if maximize_value == "true" else "minimize"
        )

    return resolved


def resolve_metrics_direction(
    metrics: list[str],
    frontend_config: dict[str, str] | None = None,
    csv_bytes: bytes | None = None,
) -> dict[str, str]:
    """
    Description:
        Resolve metric directions from CSV, frontend config or defaults.

    Args:
        metrics (list[str]): Dataset metric names.
        frontend_config (dict[str, str] | None): Optional directions from frontend.
        csv_bytes (bytes | None): Optional metrics CSV bytes.

    Returns:
        dict[str, str]: Direction by metric name.
    """

    if csv_bytes is not None:
        return parse_metrics_csv(csv_bytes, metrics)

    expected_lookup = build_expected_metrics_lookup(metrics)
    resolved = get_default_metrics_direction(metrics)

    if not frontend_config:
        return resolved

    for input_metric, direction in frontend_config.items():
        normalized_metric = normalize_metric_name(input_metric)

        if normalized_metric not in expected_lookup:
            raise ValueError(f"Unknown metric '{input_metric}'")

        normalized_direction = direction.strip().lower()

        if normalized_direction not in VALID_DIRECTIONS:
            raise ValueError(
                f"Invalid direction for metric '{input_metric}'. "
                "Use 'maximize' or 'minimize'."
            )

        resolved[expected_lookup[normalized_metric]] = normalized_direction

    return resolved


def generate_metrics_csv(metrics_direction: dict[str, str]) -> bytes:
    """
    Description:
        Generate a SAES metrics configuration CSV.

    Args:
        metrics_direction (dict[str, str]): Direction by metric name.

    Returns:
        bytes: Metrics CSV bytes.
    """

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["MetricName", "Maximize"])

    for metric, direction in metrics_direction.items():
        normalized_direction = direction.strip().lower()

        if normalized_direction not in VALID_DIRECTIONS:
            raise ValueError(
                f"Invalid direction for metric '{metric}'. "
                "Use 'maximize' or 'minimize'."
            )

        writer.writerow([metric, str(normalized_direction == "maximize")])

    return output.getvalue().encode("utf-8")
