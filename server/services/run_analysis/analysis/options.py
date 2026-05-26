from __future__ import annotations

import hashlib
import json
from typing import Any


def normalize_string_list(value: Any) -> list[str]:
    """
    Description:
        Normalize a raw value into a unique list of non-empty strings.

        Accepted inputs:
            - None
            - str
            - list[str]
            - tuple[str, ...]
            - set[str]

        Non-string values inside iterables are ignored.

    Args:
        value (Any):
            Raw value to normalize.

    Returns:
        list[str]:
            Unique cleaned string values preserving input order when possible.
    """

    if value is None:
        return []

    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []

    if isinstance(value, (list, tuple, set)):
        result: list[str] = []

        for item in value:
            if not isinstance(item, str):
                continue

            cleaned = item.strip()

            if cleaned and cleaned not in result:
                result.append(cleaned)

        return result

    return []


def normalize_string_dict(value: Any) -> dict[str, str]:
    """
    Description:
        Normalize a raw value into a dictionary of non-empty string pairs.

        Non-dictionary values are ignored. Dictionary entries are kept only when
        both key and value are strings and both remain non-empty after stripping.

    Args:
        value (Any):
            Raw value to normalize.

    Returns:
        dict[str, str]:
            Clean string dictionary.
    """

    if not isinstance(value, dict):
        return {}

    result: dict[str, str] = {}

    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            continue

        cleaned_key = key.strip()
        cleaned_item = item.strip()

        if cleaned_key and cleaned_item:
            result[cleaned_key] = cleaned_item

    return result


def get_bool_option(options: dict[str, Any], key: str, default: bool) -> bool:
    """
    Description:
        Resolve a boolean option from a dictionary.

        The value may be a bool or a common boolean-like string.
        Unknown values fall back to the provided default.

    Args:
        options (dict[str, Any]):
            Options dictionary.

        key (str):
            Option key to read.

        default (bool):
            Default value used when the option is missing or invalid.

    Returns:
        bool:
            Resolved boolean value.
    """

    value = options.get(key, default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {"true", "1", "yes", "y", "on"}:
            return True

        if normalized in {"false", "0", "no", "n", "off"}:
            return False

    return default


def get_evolution_options(analysis) -> dict[str, Any]:
    """
    Description:
        Read and normalize evolution plot options stored in analysis outputs.

        This function also supports the legacy single-value x_axis option and
        converts it into the current x_columns list.

    Args:
        analysis:
            Analysis document containing outputs.evolution_options.

    Returns:
        dict[str, Any]:
            Normalized evolution plot options.
    """

    outputs = getattr(analysis, "outputs", None) or {}
    options = outputs.get("evolution_options") or {}

    if not isinstance(options, dict):
        options = {}

    x_columns = normalize_string_list(options.get("x_columns"))

    if not x_columns:
        legacy_x_axis = options.get("x_axis")

        if isinstance(legacy_x_axis, str) and legacy_x_axis.strip():
            x_axis = legacy_x_axis.strip().lower()

            if x_axis == "generation":
                x_columns = ["Generation"]
            elif x_axis == "time":
                x_columns = ["Time"]
            elif x_axis == "evolution_x":
                x_columns = ["EvolutionX"]

    return {
        "title": options.get("title"),
        "x_columns": x_columns,
        "x_label": options.get("x_label"),
        "y_label": options.get("y_label") or "Fitness",
        "x_labels_by_column": normalize_string_dict(options.get("x_labels_by_column")),
        "y_labels_by_metric": normalize_string_dict(options.get("y_labels_by_metric")),
        "selected_algorithms": normalize_string_list(
            options.get("selected_algorithms")
        ),
        "selected_metrics": normalize_string_list(options.get("selected_metrics")),
        "selected_instances": normalize_string_list(options.get("selected_instances")),
        "show_grid": get_bool_option(options, "show_grid", True),
        "show_min_max": get_bool_option(options, "show_min_max", True),
        "show_std": get_bool_option(options, "show_std", True),
        "show_average": get_bool_option(options, "show_average", True),
        "show_median": get_bool_option(options, "show_median", True),
        "group_by_instance": get_bool_option(options, "group_by_instance", True),
        "group_by_metric": get_bool_option(options, "group_by_metric", True),
    }


def normalize_evolution_options_for_signature(
    options: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Description:
        Normalize evolution options into a deterministic structure.

        The normalized structure is used to build a stable signature and history
        key. Lists are sorted and dictionaries are sorted by key so equivalent
        option sets always produce the same signature.

    Args:
        options (dict[str, Any] | None):
            Evolution plot options.

    Returns:
        dict[str, Any]:
            Deterministic normalized options.
    """

    source = options or {}

    return {
        "title": str(source.get("title") or "").strip() or None,
        "x_columns": sorted(normalize_string_list(source.get("x_columns"))),
        "x_label": str(source.get("x_label") or "").strip() or None,
        "y_label": str(source.get("y_label") or "").strip() or None,
        "x_labels_by_column": dict(
            sorted(normalize_string_dict(source.get("x_labels_by_column")).items())
        ),
        "y_labels_by_metric": dict(
            sorted(normalize_string_dict(source.get("y_labels_by_metric")).items())
        ),
        "selected_algorithms": sorted(
            normalize_string_list(source.get("selected_algorithms"))
        ),
        "selected_metrics": sorted(
            normalize_string_list(source.get("selected_metrics"))
        ),
        "selected_instances": sorted(
            normalize_string_list(source.get("selected_instances"))
        ),
        "show_grid": get_bool_option(source, "show_grid", True),
        "show_min_max": get_bool_option(source, "show_min_max", True),
        "show_std": get_bool_option(source, "show_std", True),
        "show_average": get_bool_option(source, "show_average", True),
        "show_median": get_bool_option(source, "show_median", True),
        "group_by_instance": get_bool_option(source, "group_by_instance", True),
        "group_by_metric": get_bool_option(source, "group_by_metric", True),
    }


def build_evolution_options_signature(options: dict[str, Any] | None) -> str:
    """
    Description:
        Build a stable JSON signature for evolution plot options.

    Args:
        options (dict[str, Any] | None):
            Evolution plot options.

    Returns:
        str:
            Deterministic JSON signature.
    """

    return json.dumps(
        normalize_evolution_options_for_signature(options),
        sort_keys=True,
        separators=(",", ":"),
    )


def build_evolution_history_key(options: dict[str, Any] | None) -> str:
    """
    Description:
        Build a compact deterministic history key from evolution options.

        The key is derived from the stable options signature and is used to
        identify a generated evolution plot set.

    Args:
        options (dict[str, Any] | None):
            Evolution plot options.

    Returns:
        str:
            First 16 hexadecimal characters of the SHA1 options hash.
    """

    signature = build_evolution_options_signature(options)
    return hashlib.sha1(signature.encode("utf-8")).hexdigest()[:16]


def build_evolution_history_label(options: dict[str, Any] | None) -> str:
    """
    Description:
        Build a human-readable label for an evolution plot history entry.

        The label includes enabled visual layers and optional filters such as
        selected metrics, selected instances and X columns.

    Args:
        options (dict[str, Any] | None):
            Evolution plot options.

    Returns:
        str:
            Human-readable plot set label.
    """

    normalized = normalize_evolution_options_for_signature(options)
    layers: list[str] = []

    if normalized.get("show_average"):
        layers.append("media")
    if normalized.get("show_median"):
        layers.append("mediana")
    if normalized.get("show_std"):
        layers.append("desviación")
    if normalized.get("show_min_max"):
        layers.append("min/max")

    parts = ["Evolución"]

    if layers:
        parts.append(" + ".join(layers))

    metrics = normalized.get("selected_metrics") or []
    instances = normalized.get("selected_instances") or []
    x_columns = normalized.get("x_columns") or []

    if metrics:
        parts.append(f"métricas: {', '.join(metrics)}")
    if instances:
        parts.append(f"instancias: {', '.join(instances)}")
    if x_columns:
        parts.append(f"X: {', '.join(x_columns)}")

    return " · ".join(parts)
