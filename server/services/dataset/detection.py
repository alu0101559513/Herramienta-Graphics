from __future__ import annotations

from dataclasses import dataclass

from server.services.dataset.constants import (
    DISPLAY_NAMES,
    EVOLUTION_REQUIRED_FIELDS,
    HEADER_ALIASES,
    SAES_REQUIRED_FIELDS,
)
from server.services.dataset.exceptions import DatasetFormatError


@dataclass(frozen=True)
class DatasetDetectionResult:
    """
    Description:
        Result produced by dataset capability detection.

    Args:
        capabilities (dict[str, bool]): Available analysis outputs.
        detected_columns (dict[str, str | None]): Detected CSV columns by field.
        missing_columns (dict[str, list[str]]): Missing fields by dataset type.
        warnings (list[str]): Non-blocking detection warnings.
    """

    capabilities: dict[str, bool]
    detected_columns: dict[str, str | None]
    missing_columns: dict[str, list[str]]
    warnings: list[str]


def normalize_header(value: str) -> str:
    """
    Description:
        Normalize a CSV header so it can be compared with aliases.

    Args:
        value (str): Original header value.

    Returns:
        str: Normalized header.
    """

    return "".join(char for char in value.strip().lower() if char.isalnum())


def build_header_lookup(columns: list[str]) -> dict[str, str]:
    """
    Description:
        Build a normalized lookup for original CSV headers.

    Args:
        columns (list[str]): CSV header names.

    Returns:
        dict[str, str]: Mapping from normalized header to original header.
    """

    return {normalize_header(column): column for column in columns}


def find_column(
    lookup: dict[str, str],
    aliases: list[str],
) -> str | None:
    """
    Description:
        Find the first CSV column that matches any alias.

    Args:
        lookup (dict[str, str]): Normalized header lookup.
        aliases (list[str]): Accepted aliases for a field.

    Returns:
        str | None: Original CSV column name when found.
    """

    for alias in aliases:
        column = lookup.get(normalize_header(alias))

        if column:
            return column

    return None


def detect_columns(columns: list[str]) -> dict[str, str | None]:
    """
    Description:
        Detect all known canonical columns from CSV headers.

    Args:
        columns (list[str]): CSV header names.

    Returns:
        dict[str, str | None]: Detected original columns by canonical field.
    """

    lookup = build_header_lookup(columns)

    return {
        field: find_column(lookup, aliases) for field, aliases in HEADER_ALIASES.items()
    }


def get_missing_fields(
    detected_columns: dict[str, str | None],
    required_fields: tuple[str, ...],
) -> list[str]:
    """
    Description:
        Get display names for required fields that were not detected.

    Args:
        detected_columns (dict[str, str | None]): Detected columns.
        required_fields (tuple[str, ...]): Required canonical field names.

    Returns:
        list[str]: Missing field display names.
    """

    return [
        DISPLAY_NAMES.get(field, field)
        for field in required_fields
        if detected_columns.get(field) is None
    ]


def detect_dataset_capabilities(columns: list[str]) -> DatasetDetectionResult:
    """
    Description:
        Detect whether a dataset supports SAES outputs and/or evolution plots.

    Args:
        columns (list[str]): CSV header names.

    Returns:
        DatasetDetectionResult: Dataset detection result.
    """

    detected_columns = detect_columns(columns)

    saes_missing = get_missing_fields(detected_columns, SAES_REQUIRED_FIELDS)

    evolution_missing = get_missing_fields(
        detected_columns,
        EVOLUTION_REQUIRED_FIELDS,
    )

    has_evolution_axis = any(
        detected_columns.get(field) is not None
        for field in ("evolution_x", "generation", "time")
    )

    if not has_evolution_axis:
        evolution_missing.append("Generation/Time/Evaluations")

    can_saes = not saes_missing
    can_evolution = not evolution_missing

    warnings: list[str] = []

    if can_evolution and detected_columns.get("executionid") is None:
        warnings.append(
            "No run, seed or ExecutionId column detected. "
            "Evolution plots can be generated, "
            "but dispersion by independent executions will not be available."
        )

    if (
        can_evolution
        and detected_columns.get("generation")
        and detected_columns.get("time")
    ):
        warnings.append(
            "Generation and Time columns were detected. "
            "Evolution plots can use either axis depending on the selected x_axis."
        )

    return DatasetDetectionResult(
        capabilities={
            "saes_plots": can_saes,
            "saes_reports": can_saes,
            "notebooks": can_saes,
            "evolution_plots": can_evolution,
        },
        detected_columns=detected_columns,
        missing_columns={
            "saes": saes_missing,
            "evolution": evolution_missing,
        },
        warnings=warnings,
    )


def detect_format(columns: list[str]) -> str:
    """
    Description:
        Return a dataset format label from its detected capabilities.

    Args:
        columns (list[str]): CSV header names.

    Returns:
        str: One of 'saes_with_evolution', 'saes' or 'evolution'.
    """

    detection = detect_dataset_capabilities(columns)

    match (
        detection.capabilities["saes_plots"],
        detection.capabilities["evolution_plots"],
    ):
        case (True, True):
            return "saes_with_evolution"
        case (True, False):
            return "saes"
        case (False, True):
            return "evolution"
        case _:
            raise DatasetFormatError(
                "Unsupported dataset format. The CSV must contain either SAES columns "
                "(Algorithm, Instance, MetricName, ExecutionId, MetricValue), "
                "evolution columns (Algorithm, MetricValue/Fitness and "
                "Generation/Time/Evaluations), "
                "or both."
            )
