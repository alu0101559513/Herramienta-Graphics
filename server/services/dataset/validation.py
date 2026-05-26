from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from server.services.dataset.constants import CAPABILITIES_DEFAULT
from server.services.dataset.exceptions import DatasetValidationError


def validate_dataset(rows: list[dict]) -> None:
    """
    Description:
        Validate a parsed dataset according to its capabilities.

    Args:
        rows (list[dict]): Parsed dataset rows.

    Returns:
        None
    """

    if not rows:
        raise DatasetValidationError("Dataset is empty")

    capabilities = rows[0].get("capabilities") or CAPABILITIES_DEFAULT

    if not capabilities.get("saes_plots") and not capabilities.get("evolution_plots"):
        raise DatasetValidationError("Dataset does not support any analysis output")

    validate_algorithm_values(rows)

    if capabilities.get("saes_plots"):
        validate_saes_rows(rows)

    if capabilities.get("evolution_plots"):
        validate_evolution_rows(rows)


def validate_algorithm_values(rows: list[dict]) -> None:
    """
    Description:
        Validate that every row has a non-empty algorithm.

    Args:
        rows (list[dict]): Parsed dataset rows.

    Returns:
        None
    """

    for row in rows:
        algorithm = row.get("algorithm")

        if not isinstance(algorithm, str) or not algorithm.strip():
            raise DatasetValidationError("Algorithm cannot be empty")


def validate_saes_rows(rows: list[dict]) -> None:
    """
    Description:
        Validate SAES rows for statistical analysis.

    Args:
        rows (list[dict]): Parsed dataset rows.

    Returns:
        None
    """

    problems: set[str] = set()
    run_counts: dict[tuple[str, str, str], set[int]] = defaultdict(set)

    for row in rows:
        algorithm = require_string(row, "algorithm", "Algorithm cannot be empty")
        instance = require_string(row, "instance", "Instance cannot be empty")
        metricname = require_string(row, "metricname", "MetricName cannot be empty")
        executionid = require_int(row, "executionid", "ExecutionId must be an integer")
        metricvalue = require_number(row, "metricvalue", "MetricValue must be numeric")

        if executionid < 0:
            raise DatasetValidationError("ExecutionId cannot be negative")

        if isinstance(metricvalue, float) and math.isnan(metricvalue):
            raise DatasetValidationError("Dataset contains NaN values")

        problems.add(instance)
        run_counts[(algorithm, instance, metricname)].add(executionid)

    validate_runs(run_counts, problems)


def validate_evolution_rows(rows: list[dict]) -> None:
    """
    Description:
        Validate evolution rows for convergence plots.

    Args:
        rows (list[dict]): Parsed dataset rows.

    Returns:
        None
    """

    algorithm_points: dict[str, set[float]] = defaultdict(set)

    for row in rows:
        algorithm = require_string(row, "algorithm", "Algorithm cannot be empty")

        x_value = require_number(
            row,
            "evolution_x",
            "Evolution X value must be numeric",
        )

        y_value = require_number(
            row,
            "evolution_y",
            "Evolution Y value must be numeric",
        )

        if isinstance(x_value, float) and math.isnan(x_value):
            raise DatasetValidationError("Evolution dataset contains NaN X values")

        if isinstance(y_value, float) and math.isnan(y_value):
            raise DatasetValidationError("Evolution dataset contains NaN Y values")

        algorithm_points[algorithm].add(float(x_value))

    if not algorithm_points:
        raise DatasetValidationError("At least one algorithm is required")

    if any(len(points) < 2 for points in algorithm_points.values()):
        raise DatasetValidationError(
            "At least two evolution points are required per algorithm"
        )


def require_string(row: dict[str, Any], key: str, message: str) -> str:
    """
    Description:
        Require a non-empty string field from a parsed row.

    Args:
        row (dict[str, Any]): Parsed row.
        key (str): Field key.
        message (str): Error message.

    Returns:
        str: Clean string value.
    """

    value = row.get(key)

    if not isinstance(value, str) or not value.strip():
        raise DatasetValidationError(message)

    return value.strip()


def require_int(row: dict[str, Any], key: str, message: str) -> int:
    """
    Description:
        Require an integer field from a parsed row.

    Args:
        row (dict[str, Any]): Parsed row.
        key (str): Field key.
        message (str): Error message.

    Returns:
        int: Integer value.
    """

    value = row.get(key)

    if not isinstance(value, int):
        raise DatasetValidationError(message)

    return value


def require_number(row: dict[str, Any], key: str, message: str) -> int | float:
    """
    Description:
        Require a numeric field from a parsed row.

    Args:
        row (dict[str, Any]): Parsed row.
        key (str): Field key.
        message (str): Error message.

    Returns:
        int | float: Numeric value.
    """

    value = row.get(key)

    if value is None:
        raise DatasetValidationError(f"Dataset contains empty {key} values")

    if not isinstance(value, (int, float)):
        raise DatasetValidationError(message)

    return value


def validate_runs(
    run_counts: dict[tuple[str, str, str], set[int]],
    problems: set[str],
) -> None:
    """
    Description:
        Validate run balance across algorithm, instance and metric groups.

    Args:
        run_counts (dict[tuple[str, str, str], set[int]]): Run IDs by group.
        problems (set[str]): Detected instances.

    Returns:
        None
    """

    if not problems:
        raise DatasetValidationError("At least 1 instance is required")

    if not run_counts:
        raise DatasetValidationError("Dataset contains no valid run information")

    run_sizes = {len(execution_ids) for execution_ids in run_counts.values()}

    if len(run_sizes) != 1:
        raise DatasetValidationError(
            "Unbalanced dataset: different number of runs per algorithm/instance/metric"
        )

    if next(iter(run_sizes)) < 2:
        raise DatasetValidationError(
            "At least 2 runs are required for statistical analysis"
        )
