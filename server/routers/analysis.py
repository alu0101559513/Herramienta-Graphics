from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Annotated, Any

from beanie import PydanticObjectId
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response, StreamingResponse
from server.dependencies.auth import get_authenticated_user
from server.models.analysis import Analysis
from server.models.user import User
from server.schemas.analysis import AnalysisCreate, AnalysisReanalyzeRequest
from server.services.dataset.exceptions import (
    DatasetFormatError,
    DatasetValidationError,
)
from server.services.dataset.metadata import extract_metadata
from server.services.dataset.parsing import (
    inspect_dataset,
    normalize_dataset,
    parse_dataset,
)
from server.services.dataset.validation import validate_dataset
from server.services.graphics.saes_graphics.metrics_config import (
    get_default_metrics_direction,
    resolve_metrics_direction,
)
from server.services.gridfs import get_file, save_file
from server.services.run_analysis.analysis.modules import (
    build_algorithm_run_key,
    get_modules_pending_reanalysis,
)
from server.services.run_analysis.analysis.pipeline import run_analysis_pipeline

router = APIRouter(prefix="/analyses", tags=["analyses"])

ALLOWED_PLOT_EXPORT_FORMATS = {"png", "eps", "svg", "jpg", "jpeg"}
ALLOWED_MODULES = {"saes_plots", "saes_reports", "notebooks", "evolution_plots"}
SAES_MODULES = {"saes_plots", "saes_reports", "notebooks"}
EVOLUTION_MODULES = {"evolution_plots"}

ALLOWED_PLOT_TYPES = {
    "boxplot",
    "violin",
    "histogram",
    "critical_distance",
    "evolution",
}
SAES_PLOT_TYPES = {"boxplot", "violin", "histogram", "critical_distance"}

EVOLUTION_HISTORY_PREFIX = "evolution_history__"

INTERNAL_OUTPUT_KEYS = {
    "error",
    "analysis_runs",
    "evolution_metadata",
    "generated_plot_types",
    "evolution_options",
    "evolution_options_signature",
    "evolution_plot_sets",
    "selected_algorithms",
    "modules",
    "metrics_config_file_id",
    "saes_plot_warnings",
    "saes_report_warnings",
    "evolution_plot_warnings",
}

MEDIA_TYPES = {
    ".preview.json": "application/json",
    ".json": "application/json",
    ".ipynb": "application/x-ipynb+json",
    ".csv": "text/csv",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".eps": "application/postscript",
    ".txt": "text/plain; charset=utf-8",
    ".tex": "application/x-tex",
    ".zip": "application/zip",
}


def build_evolution_history_category(signature: str) -> str:
    """
    Description:
        Build the virtual output category used to expose an evolution plot set.

    Args:
        signature (str): Evolution plot set signature or history key.

    Returns:
        str: Virtual category name.
    """

    return f"{EVOLUTION_HISTORY_PREFIX}{signature}"


def get_evolution_history_signature(category: str) -> str | None:
    """
    Description:
        Extract an evolution history signature from a virtual category.

    Args:
        category (str): Requested output category.

    Returns:
        str | None: Signature when the category is an evolution history category.
    """

    if not category.startswith(EVOLUTION_HISTORY_PREFIX):
        return None

    signature = category[len(EVOLUTION_HISTORY_PREFIX) :].strip()
    return signature or None


def deduplicate_file_mapping(files: dict[str, Any]) -> dict[str, str]:
    """
    Description:
        Normalize and deduplicate a filename-to-file-id mapping.

        Duplicates with the same stored file id are ignored. When two different
        stored files share the same visible filename, a numeric suffix is added
        to keep both downloadable without overwriting one another in listings
        or ZIP archives.

    Args:
        files (dict[str, Any]): Raw file mapping.

    Returns:
        dict[str, str]: Deduplicated file mapping.
    """

    deduplicated: dict[str, str] = {}
    seen_file_ids: set[str] = set()

    for raw_filename, raw_file_id in files.items():
        if not raw_filename or not raw_file_id:
            continue

        filename = str(raw_filename)
        file_id = str(raw_file_id)

        if file_id in seen_file_ids:
            continue

        seen_file_ids.add(file_id)

        if filename not in deduplicated:
            deduplicated[filename] = file_id
            continue

        stem, dot, suffix = filename.rpartition(".")
        base_name = stem if dot else filename
        extension = f".{suffix}" if dot else ""
        counter = 2
        candidate = f"{base_name}__{counter}{extension}"

        while candidate in deduplicated:
            counter += 1
            candidate = f"{base_name}__{counter}{extension}"

        deduplicated[candidate] = file_id

    return deduplicated


def merge_evolution_plot_files(run_outputs: dict[str, Any]) -> dict[str, str]:
    """
    Description:
        Merge current and historical evolution plot files into one category.

        The frontend should only see the `evolution_plots` category. Historical
        plot sets remain stored internally, but their files are merged here so
        downloads include every generated evolution graph without exposing
        separate `evolution_history__...` categories.

    Args:
        run_outputs (dict[str, Any]): Outputs for a specific analysis run.

    Returns:
        dict[str, str]: Merged evolution plot files.
    """

    merged: dict[str, str] = {}
    seen_file_ids: set[str] = set()

    def add_file(raw_filename: Any, raw_file_id: Any) -> None:
        if not raw_filename or not raw_file_id:
            return

        filename = str(raw_filename)
        file_id = str(raw_file_id)

        if file_id in seen_file_ids:
            return

        seen_file_ids.add(file_id)

        if filename not in merged:
            merged[filename] = file_id
            return

        stem, dot, suffix = filename.rpartition(".")
        base_name = stem if dot else filename
        extension = f".{suffix}" if dot else ""
        counter = 2
        candidate = f"{base_name}__{counter}{extension}"

        while candidate in merged:
            counter += 1
            candidate = f"{base_name}__{counter}{extension}"

        merged[candidate] = file_id

    def add_mapping(value: Any) -> None:
        if not isinstance(value, dict):
            return

        for filename, file_id in value.items():
            add_file(filename, file_id)

    add_mapping(run_outputs.get("evolution_plots"))

    evolution_plot_sets = run_outputs.get("evolution_plot_sets")

    if isinstance(evolution_plot_sets, dict):
        for plot_set in evolution_plot_sets.values():
            if isinstance(plot_set, dict):
                add_mapping(plot_set.get("evolution_plots"))

    return merged


def get_category_files(
    run_outputs: dict[str, Any],
    category: str,
) -> dict[str, str] | None:
    """
    Description:
        Resolve the files stored under an output category.

        `evolution_plots` is treated as a consolidated category that includes
        current and historical evolution files. Legacy `evolution_history__...`
        categories are still resolved for compatibility, but they are no longer
        exposed by file listings.

    Args:
        run_outputs (dict[str, Any]): Outputs for a specific analysis run.
        category (str): Requested category name.

    Returns:
        dict[str, str] | None: File names mapped to file ids, if found.
    """

    if category == "evolution_plots":
        evolution_files = merge_evolution_plot_files(run_outputs)
        return evolution_files or None

    history_signature = get_evolution_history_signature(category)

    if history_signature:
        plot_sets = run_outputs.get("evolution_plot_sets")

        if not isinstance(plot_sets, dict):
            return None

        plot_set = plot_sets.get(history_signature)

        if not isinstance(plot_set, dict):
            return None

        evolution_files = plot_set.get("evolution_plots")
        return (
            deduplicate_file_mapping(evolution_files)
            if isinstance(evolution_files, dict)
            else None
        )

    category_data = run_outputs.get(category)

    if not isinstance(category_data, dict):
        return None

    return deduplicate_file_mapping(category_data) or None


def serialize_outputs(outputs: dict[str, Any]) -> dict[str, list[str]]:
    """
    Description:
        Convert internal analysis outputs into a frontend-friendly file listing.

        Internal keys are hidden. Evolution plot history files are merged into
        the single `evolution_plots` category to avoid duplicated categories and
        repeated downloads.

    Args:
        outputs (dict[str, Any]): Raw run outputs.

    Returns:
        dict[str, list[str]]: Visible categories mapped to filenames.
    """

    files: dict[str, list[str]] = {}

    visible_outputs = {
        key: value
        for key, value in outputs.items()
        if key not in INTERNAL_OUTPUT_KEYS
        and not key.startswith(EVOLUTION_HISTORY_PREFIX)
    }

    for key, value in visible_outputs.items():
        if key == "evolution_plots":
            continue

        if isinstance(value, dict):
            category_files = deduplicate_file_mapping(value)

            if category_files:
                files[key] = list(category_files.keys())

        elif isinstance(value, list):
            files[key] = list(dict.fromkeys(str(item) for item in value if item))

        elif value is not None:
            files[key] = [key]

    evolution_files = merge_evolution_plot_files(outputs)

    if evolution_files:
        files["evolution_plots"] = list(evolution_files.keys())

    return files


def get_media_type(filename: str) -> str:
    """
    Description:
        Resolve the HTTP media type for a generated file.

    Args:
        filename (str): File name.

    Returns:
        str: Matching media type or application/octet-stream.
    """

    lower = filename.lower()

    for extension, media_type in MEDIA_TYPES.items():
        if lower.endswith(extension):
            return media_type

    return "application/octet-stream"


def normalize_module_name(module: str) -> str:
    """
    Description:
        Normalize legacy module aliases.

    Args:
        module (str): Raw module name.

    Returns:
        str: Normalized module name.
    """

    normalized = module.strip()

    if normalized in {"saes_notebook", "saes_notebooks"}:
        return "notebooks"

    return normalized


def normalize_modules_list(modules: list[str]) -> list[str]:
    """
    Description:
        Validate, normalize and deduplicate module names.

    Args:
        modules (list[str]): Requested modules.

    Returns:
        list[str]: Valid unique module names.
    """

    if not modules:
        raise HTTPException(400, "Modules must not be empty")

    cleaned_modules: list[str] = []

    for module in modules:
        if not isinstance(module, str):
            raise HTTPException(400, "Modules must be a list of strings")

        normalized_module = normalize_module_name(module)

        if not normalized_module:
            raise HTTPException(400, "Modules must not contain empty values")

        if normalized_module not in ALLOWED_MODULES:
            raise HTTPException(400, f"Invalid module '{normalized_module}'")

        if normalized_module not in cleaned_modules:
            cleaned_modules.append(normalized_module)

    return cleaned_modules


def parse_modules_input(modules: str) -> list[str]:
    """
    Description:
        Parse modules from form input.

        The input may be a JSON array, a JSON string, or a plain module name.

    Args:
        modules (str): Raw modules form value.

    Returns:
        list[str]: Normalized module list.
    """

    try:
        parsed_modules: Any = json.loads(modules)
    except json.JSONDecodeError:
        parsed_modules = modules

    if isinstance(parsed_modules, str):
        parsed_modules = [parsed_modules]

    if not isinstance(parsed_modules, list) or not all(
        isinstance(module, str) for module in parsed_modules
    ):
        raise HTTPException(400, "Modules must be a string or a JSON array of strings")

    return normalize_modules_list(parsed_modules)


def get_capabilities(analysis: Analysis) -> dict[str, bool]:
    """
    Description:
        Read dataset capabilities from an analysis.

    Args:
        analysis (Analysis): Analysis document.

    Returns:
        dict[str, bool]: Capability flags.
    """

    return dict(
        analysis.dataset_capabilities
        or {
            "saes_plots": False,
            "saes_reports": False,
            "notebooks": False,
            "evolution_plots": False,
        }
    )


def validate_modules_against_capabilities(
    analysis: Analysis,
    modules: list[str],
) -> None:
    """
    Description:
        Validate that requested modules are compatible with dataset capabilities.

    Args:
        analysis (Analysis): Analysis document.
        modules (list[str]): Requested modules.

    Returns:
        None.
    """

    capabilities = get_capabilities(analysis)
    requests_saes = any(module in SAES_MODULES for module in modules)
    requests_evolution = any(module in EVOLUTION_MODULES for module in modules)

    if requests_saes and not capabilities.get("saes_plots", False):
        raise HTTPException(
            400,
            "SAES outputs are not available for this dataset. The CSV must "
            "contain Algorithm, Instance, MetricName, ExecutionId and MetricValue.",
        )

    if requests_evolution and not capabilities.get("evolution_plots", False):
        raise HTTPException(
            400,
            "Evolution plots are not available for this dataset. The CSV must "
            "contain Algorithm, MetricValue/Fitness, and at least one X column "
            "such as Generation, Time, Evaluations or Iteration.",
        )


def build_default_modules_from_capabilities(capabilities: dict[str, bool]) -> list[str]:
    """
    Description:
        Build the default module list from detected dataset capabilities.

    Args:
        capabilities (dict[str, bool]): Dataset capability flags.

    Returns:
        list[str]: Default modules available for the dataset.
    """

    modules: list[str] = []

    if capabilities.get("saes_plots"):
        modules.append("saes_plots")

    if capabilities.get("saes_reports"):
        modules.append("saes_reports")

    if capabilities.get("notebooks"):
        modules.append("notebooks")

    if capabilities.get("evolution_plots"):
        modules.append("evolution_plots")

    return modules


def get_reanalysis_modules(
    analysis: Analysis,
    modules: list[str] | None = None,
) -> list[str]:
    """
    Description:
        Resolve which modules should be used for reanalysis.

        Explicit modules have priority. If not provided, previously enabled
        modules are reused. If none exist, defaults are built from capabilities.

    Args:
        analysis (Analysis): Analysis document.
        modules (list[str] | None): Optional requested modules.

    Returns:
        list[str]: Modules selected for reanalysis.
    """

    if modules is not None:
        selected_modules = normalize_modules_list(modules)
    elif analysis.enabled_modules:
        selected_modules = normalize_modules_list(list(analysis.enabled_modules))
    else:
        selected_modules = build_default_modules_from_capabilities(
            get_capabilities(analysis)
        )

    validate_modules_against_capabilities(analysis, selected_modules)
    return selected_modules


def normalize_plot_types_list(plot_types: list[str] | None) -> list[str]:
    """
    Description:
        Validate and normalize requested plot types.

    Args:
        plot_types (list[str] | None): Requested plot types.

    Returns:
        list[str]: Sorted unique plot types.
    """

    if plot_types is None:
        return sorted(ALLOWED_PLOT_TYPES)

    cleaned_plot_types: list[str] = []

    for plot_type in plot_types:
        if not isinstance(plot_type, str):
            raise HTTPException(400, "Plot types must be a list of strings")

        normalized_plot_type = plot_type.strip().lower()

        if not normalized_plot_type:
            raise HTTPException(400, "Plot types must not contain empty values")

        if normalized_plot_type not in ALLOWED_PLOT_TYPES:
            raise HTTPException(400, f"Invalid plot type '{normalized_plot_type}'")

        if normalized_plot_type not in cleaned_plot_types:
            cleaned_plot_types.append(normalized_plot_type)

    return sorted(cleaned_plot_types)


def get_saes_plot_types(plot_types: list[str]) -> list[str]:
    """
    Description:
        Extract SAES plot types from a mixed plot type list.

    Args:
        plot_types (list[str]): Normalized plot types.

    Returns:
        list[str]: SAES plot types only.
    """

    return [plot_type for plot_type in plot_types if plot_type in SAES_PLOT_TYPES]


def parse_metrics_direction_input(
    metrics_direction: str | None,
) -> dict[str, str] | None:
    """
    Description:
        Parse metric optimization directions from form input.

    Args:
        metrics_direction (str | None): JSON object as string.

    Returns:
        dict[str, str] | None: Normalized metric directions.
    """

    if metrics_direction is None or not metrics_direction.strip():
        return None

    try:
        parsed_metrics_direction = json.loads(metrics_direction)
    except json.JSONDecodeError as error:
        raise HTTPException(400, "Invalid metrics_direction format") from error

    if not isinstance(parsed_metrics_direction, dict):
        raise HTTPException(400, "metrics_direction must be a JSON object")

    normalized_metrics_direction: dict[str, str] = {}

    for metric, direction in parsed_metrics_direction.items():
        if not isinstance(metric, str) or not isinstance(direction, str):
            raise HTTPException(
                400,
                "metrics_direction must be a JSON object of string keys and values",
            )

        normalized_direction = direction.strip().lower()

        if normalized_direction not in {"maximize", "minimize"}:
            raise HTTPException(
                400,
                f"Invalid direction for metric '{metric}'. "
                "Use 'maximize' or 'minimize'.",
            )

        normalized_metrics_direction[metric.strip()] = normalized_direction

    return normalized_metrics_direction


def parse_plot_export_formats_input(plot_export_formats: str | None) -> list[str]:
    """
    Description:
        Parse plot export formats from form input.

        The input may be a JSON array or a comma-separated string.

    Args:
        plot_export_formats (str | None): Raw export formats value.

    Returns:
        list[str]: Normalized export formats.
    """

    if plot_export_formats is None or not plot_export_formats.strip():
        return ["png"]

    raw_value = plot_export_formats.strip()

    try:
        parsed_value: Any = json.loads(raw_value)
    except json.JSONDecodeError:
        parsed_value = raw_value

    if isinstance(parsed_value, str):
        values = [part.strip() for part in parsed_value.split(",") if part.strip()]
    elif isinstance(parsed_value, list):
        values = [str(part).strip() for part in parsed_value if str(part).strip()]
    else:
        raise HTTPException(
            400,
            "plot_export_formats must be a JSON array or a comma-separated string",
        )

    normalized_formats: list[str] = []

    for export_format in values:
        normalized_format = export_format.lower()

        if normalized_format not in ALLOWED_PLOT_EXPORT_FORMATS:
            allowed = ", ".join(sorted(ALLOWED_PLOT_EXPORT_FORMATS))
            raise HTTPException(
                400,
                f"Invalid plot export format '{export_format}'. Use one of: {allowed}.",
            )

        if normalized_format not in normalized_formats:
            normalized_formats.append(normalized_format)

    return normalized_formats or ["png"]


def parse_bool_form_value(value: str | None, default: bool) -> bool:
    """
    Description:
        Parse a boolean value from form input.

    Args:
        value (str | None): Raw form value.
        default (bool): Default value when input is empty.

    Returns:
        bool: Parsed boolean value.
    """

    if value is None or not str(value).strip():
        return default

    normalized = str(value).strip().lower()

    if normalized in {"true", "1", "yes", "y", "on"}:
        return True

    if normalized in {"false", "0", "no", "n", "off"}:
        return False

    raise HTTPException(400, f"Invalid boolean value '{value}'")


def parse_string_list_form_value(value: str | None, field_name: str) -> list[str]:
    """
    Description:
        Parse a string list from form input.

        The input may be a JSON array or a plain string.

    Args:
        value (str | None): Raw form value.
        field_name (str): Field name for validation messages.

    Returns:
        list[str]: Clean unique string list.
    """

    if value is None or not str(value).strip():
        return []

    raw_value = str(value).strip()

    try:
        parsed_value: Any = json.loads(raw_value)
    except json.JSONDecodeError:
        parsed_value = raw_value

    if isinstance(parsed_value, str):
        cleaned = parsed_value.strip()
        return [cleaned] if cleaned else []

    if not isinstance(parsed_value, list):
        raise HTTPException(400, f"{field_name} must be a JSON array of strings")

    result: list[str] = []

    for item in parsed_value:
        if not isinstance(item, str):
            raise HTTPException(400, f"{field_name} must contain only strings")

        cleaned = item.strip()

        if cleaned and cleaned not in result:
            result.append(cleaned)

    return result


def parse_string_dict_form_value(value: str | None, field_name: str) -> dict[str, str]:
    """
    Description:
        Parse a string dictionary from form input.

    Args:
        value (str | None): Raw form value.
        field_name (str): Field name for validation messages.

    Returns:
        dict[str, str]: Clean string dictionary.
    """

    if value is None or not str(value).strip():
        return {}

    raw_value = str(value).strip()

    try:
        parsed_value: Any = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise HTTPException(
            400,
            f"{field_name} must be a JSON object of strings",
        ) from error

    if not isinstance(parsed_value, dict):
        raise HTTPException(400, f"{field_name} must be a JSON object of strings")

    result: dict[str, str] = {}

    for key, item in parsed_value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise HTTPException(
                400,
                f"{field_name} must contain only string keys and values",
            )

        cleaned_key = key.strip()
        cleaned_item = item.strip()

        if cleaned_key and cleaned_item:
            result[cleaned_key] = cleaned_item

    return result


def parse_evolution_x_columns(value: str | None) -> list[str]:
    """
    Description:
        Parse evolution X columns from form input.

    Args:
        value (str | None): Raw form value.

    Returns:
        list[str]: Clean X column names.
    """

    return parse_string_list_form_value(value, "evolution_x_columns")


def clean_list(values: list[str] | None) -> list[str]:
    """
    Description:
        Normalize a list of strings.

    Args:
        values (list[str] | None): Raw values.

    Returns:
        list[str]: Clean unique string list.
    """

    result: list[str] = []

    for value in values or []:
        if not isinstance(value, str):
            continue

        cleaned = value.strip()

        if cleaned and cleaned not in result:
            result.append(cleaned)

    return result


def clean_string_dict(value: dict[str, str] | None) -> dict[str, str]:
    """
    Description:
        Normalize a dictionary of string pairs.

    Args:
        value (dict[str, str] | None): Raw dictionary.

    Returns:
        dict[str, str]: Clean string dictionary.
    """

    result: dict[str, str] = {}

    for key, item in (value or {}).items():
        if not isinstance(key, str) or not isinstance(item, str):
            continue

        cleaned_key = key.strip()
        cleaned_item = item.strip()

        if cleaned_key and cleaned_item:
            result[cleaned_key] = cleaned_item

    return result


def clean_optional_string(value: str | None) -> str | None:
    """
    Description:
        Normalize an optional string.

    Args:
        value (str | None): Raw value.

    Returns:
        str | None: Clean string or None.
    """

    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None


def build_evolution_options_from_payload(
    payload: AnalysisReanalyzeRequest,
) -> dict[str, Any]:
    """
    Description:
        Build evolution plot options from a reanalysis payload.

    Args:
        payload (AnalysisReanalyzeRequest): Reanalysis request payload.

    Returns:
        dict[str, Any]: Evolution options dictionary.
    """

    return {
        "title": clean_optional_string(payload.evolution_title),
        "x_columns": clean_list(payload.evolution_x_columns),
        "x_label": clean_optional_string(payload.evolution_x_label),
        "y_label": clean_optional_string(payload.evolution_y_label),
        "x_labels_by_column": clean_string_dict(payload.evolution_x_labels_by_column),
        "y_labels_by_metric": clean_string_dict(payload.evolution_y_labels_by_metric),
        "selected_algorithms": clean_list(payload.evolution_selected_algorithms),
        "selected_metrics": clean_list(payload.evolution_selected_metrics),
        "selected_instances": clean_list(payload.evolution_selected_instances),
        "show_grid": payload.evolution_show_grid,
        "show_min_max": payload.evolution_show_min_max,
        "show_std": payload.evolution_show_std,
        "show_average": payload.evolution_show_average,
        "show_median": payload.evolution_show_median,
        "group_by_instance": payload.evolution_group_by_instance,
        "group_by_metric": payload.evolution_group_by_metric,
    }


def compact_evolution_options(options: dict[str, Any] | None) -> dict[str, Any]:
    """
    Description:
        Remove empty values from evolution options.

    Args:
        options (dict[str, Any] | None): Raw evolution options.

    Returns:
        dict[str, Any]: Compacted evolution options.
    """

    compacted: dict[str, Any] = {}

    for key, value in (options or {}).items():
        if value is None:
            continue

        if isinstance(value, list):
            cleaned = clean_list(value)

            if cleaned:
                compacted[key] = cleaned

            continue

        if isinstance(value, dict):
            cleaned_dict = clean_string_dict(value)

            if cleaned_dict:
                compacted[key] = cleaned_dict

            continue

        if isinstance(value, str):
            cleaned = value.strip()

            if cleaned:
                compacted[key] = cleaned

            continue

        compacted[key] = value

    return compacted


def normalize_statistics_options(options: dict[str, Any]) -> dict[str, Any]:
    """
    Description:
        Convert legacy statistics list into explicit evolution display flags.

    Args:
        options (dict[str, Any]): Evolution options.

    Returns:
        dict[str, Any]: Evolution options with normalized statistic flags.
    """

    compacted = dict(options)
    stats = compacted.get("statistics")

    if not isinstance(stats, list):
        return compacted

    stats_list = [
        str(value).strip().lower()
        for value in stats
        if isinstance(value, str) and value.strip()
    ]

    compacted["show_std"] = "std" in stats_list
    compacted["show_median"] = "median" in stats_list
    compacted["show_average"] = "mean" in stats_list
    compacted["show_min_max"] = "min_max" in stats_list
    compacted.pop("statistics", None)

    return compacted


def normalize_evolution_options_for_signature(
    options: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Description:
        Normalize evolution options into a deterministic signature structure.

    Args:
        options (dict[str, Any] | None): Evolution options.

    Returns:
        dict[str, Any]: Deterministic normalized options.
    """

    compacted = normalize_statistics_options(compact_evolution_options(options))

    return {
        "title": compacted.get("title"),
        "x_columns": sorted(clean_list(compacted.get("x_columns"))),
        "x_label": compacted.get("x_label"),
        "y_label": compacted.get("y_label"),
        "x_labels_by_column": dict(
            sorted(clean_string_dict(compacted.get("x_labels_by_column")).items())
        ),
        "y_labels_by_metric": dict(
            sorted(clean_string_dict(compacted.get("y_labels_by_metric")).items())
        ),
        "selected_algorithms": sorted(clean_list(compacted.get("selected_algorithms"))),
        "selected_metrics": sorted(clean_list(compacted.get("selected_metrics"))),
        "selected_instances": sorted(clean_list(compacted.get("selected_instances"))),
        "show_grid": bool(compacted.get("show_grid", True)),
        "show_min_max": bool(compacted.get("show_min_max", True)),
        "show_std": bool(compacted.get("show_std", True)),
        "show_average": bool(compacted.get("show_average", True)),
        "show_median": bool(compacted.get("show_median", True)),
        "group_by_instance": bool(compacted.get("group_by_instance", True)),
        "group_by_metric": bool(compacted.get("group_by_metric", True)),
    }


def build_evolution_options_signature(options: dict[str, Any] | None) -> str:
    """
    Description:
        Build a stable JSON signature for evolution options.

    Args:
        options (dict[str, Any] | None): Evolution options.

    Returns:
        str: Deterministic JSON signature.
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

    Args:
        options (dict[str, Any] | None): Evolution options.

    Returns:
        str: First 16 characters of the SHA1 options signature.
    """

    signature = build_evolution_options_signature(options)
    return hashlib.sha1(signature.encode("utf-8")).hexdigest()[:16]


def build_evolution_history_label(options: dict[str, Any] | None) -> str:
    """
    Description:
        Build a readable label for an evolution plot history entry.

    Args:
        options (dict[str, Any] | None): Evolution options.

    Returns:
        str: Human-readable history label.
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


def run_has_matching_evolution_options(
    run_outputs: dict[str, Any] | None,
    evolution_options: dict[str, Any] | None,
) -> bool:
    """
    Description:
        Check if a run already contains evolution plots for the requested options.

    Args:
        run_outputs (dict[str, Any] | None): Existing run outputs.
        evolution_options (dict[str, Any] | None): Requested evolution options.

    Returns:
        bool: True when existing evolution outputs match the requested options.
    """

    if not isinstance(run_outputs, dict):
        return False

    evolution_files = run_outputs.get("evolution_plots")

    if not isinstance(evolution_files, dict) or not evolution_files:
        return False

    expected_signature = build_evolution_options_signature(evolution_options)
    stored_signature = run_outputs.get("evolution_options_signature")

    if stored_signature == expected_signature:
        return True

    stored_options = run_outputs.get("evolution_options")

    if isinstance(stored_options, dict):
        return build_evolution_options_signature(stored_options) == expected_signature

    return False


def persist_evolution_options_for_run(
    *,
    analysis: Analysis,
    run_key: str,
    evolution_options: dict[str, Any] | None,
) -> None:
    """
    Description:
        Persist evolution options and history metadata for a run.

        This does not save the analysis document by itself. The caller is
        responsible for calling analysis.save().

    Args:
        analysis (Analysis): Analysis document.
        run_key (str): Current run key.
        evolution_options (dict[str, Any] | None): Evolution options.

    Returns:
        None.
    """

    compacted_options = normalize_statistics_options(
        compact_evolution_options(evolution_options)
    )

    if not compacted_options:
        return

    signature = build_evolution_options_signature(compacted_options)
    history_key = build_evolution_history_key(compacted_options)

    outputs = dict(analysis.outputs or {})
    analysis_runs = dict(outputs.get("analysis_runs") or {})
    run_outputs = dict(analysis_runs.get(run_key) or {})

    run_outputs["evolution_options"] = compacted_options
    run_outputs["evolution_options_signature"] = signature

    plot_sets = dict(run_outputs.get("evolution_plot_sets") or {})
    plot_set = dict(plot_sets.get(history_key) or {})

    if isinstance(run_outputs.get("evolution_plots"), dict):
        plot_set["evolution_plots"] = run_outputs["evolution_plots"]

    if isinstance(run_outputs.get("evolution_metadata"), dict):
        plot_set["evolution_metadata"] = run_outputs["evolution_metadata"]

    plot_set["signature"] = signature
    plot_set["history_key"] = history_key
    plot_set["label"] = build_evolution_history_label(compacted_options)
    plot_set["created_at"] = (
        plot_set.get("created_at") or datetime.now(timezone.utc).isoformat()
    )
    plot_set["updated_at"] = datetime.now(timezone.utc).isoformat()
    plot_set["options"] = compacted_options

    if (
        isinstance(plot_set.get("evolution_plots"), dict)
        and plot_set["evolution_plots"]
    ):
        plot_sets[history_key] = plot_set
        run_outputs["evolution_plot_sets"] = plot_sets

    analysis_runs[run_key] = run_outputs
    outputs["analysis_runs"] = analysis_runs
    outputs["evolution_options"] = compacted_options
    outputs["evolution_options_signature"] = signature
    outputs["evolution_plot_sets"] = run_outputs.get("evolution_plot_sets", {})

    analysis.outputs = outputs


def sanitize_zip_name(value: str) -> str:
    """
    Description:
        Sanitize a value for use as a ZIP filename component.

    Args:
        value (str): Raw name.

    Returns:
        str: Sanitized name.
    """

    return value.replace("/", "_").replace("\\", "_").replace(" ", "_").strip("_")


def get_requested_run_key(
    analysis: Analysis,
    run_key: str | None = None,
    selected_algorithms: list[str] | None = None,
) -> str:
    """
    Description:
        Resolve which run key should be used to read outputs.

    Args:
        analysis (Analysis): Analysis document.
        run_key (str | None): Explicit run key.
        selected_algorithms (list[str] | None): Optional selected algorithms.

    Returns:
        str: Resolved run key.
    """

    if run_key and run_key.strip():
        return run_key.strip()

    if selected_algorithms is not None:
        return build_algorithm_run_key(
            selected_algorithms=selected_algorithms,
            all_algorithms=list(analysis.algorithms or []),
        )

    return analysis.current_run_key or "all"


def get_run_outputs(
    analysis: Analysis,
    run_key: str | None = None,
    selected_algorithms: list[str] | None = None,
) -> dict[str, Any]:
    """
    Description:
        Read outputs for a specific run.

        If the requested run is not present in analysis_runs, this function
        falls back to legacy top-level output fields.

    Args:
        analysis (Analysis): Analysis document.
        run_key (str | None): Optional run key.
        selected_algorithms (list[str] | None): Optional selected algorithms.

    Returns:
        dict[str, Any]: Run outputs.
    """

    outputs = dict(analysis.outputs or {})

    resolved_run_key = get_requested_run_key(
        analysis=analysis,
        run_key=run_key,
        selected_algorithms=selected_algorithms,
    )

    analysis_runs = dict(outputs.get("analysis_runs") or {})
    run_outputs = analysis_runs.get(resolved_run_key)

    if isinstance(run_outputs, dict):
        return run_outputs

    fallback_outputs: dict[str, Any] = {}

    for category in (
        "saes_plots",
        "saes_reports",
        "notebooks",
        "evolution_plots",
        "evolution_metadata",
        "saes_plot_warnings",
        "evolution_plot_warnings",
        "generated_plot_types",
        "evolution_options",
        "evolution_options_signature",
        "evolution_plot_sets",
    ):
        value = outputs.get(category)

        if isinstance(value, (dict, list, str)):
            fallback_outputs[category] = value

    return fallback_outputs


async def execute_analysis_modules(
    analysis: Analysis,
    modules: str,
    metrics_direction: str | None = None,
    metrics_file: UploadFile | None = None,
    plot_export_formats: str | None = None,
    selected_algorithms: list[str] | None = None,
    evolution_title: str | None = None,
    evolution_x_columns: str | None = None,
    evolution_x_label: str | None = None,
    evolution_y_label: str | None = None,
    evolution_x_labels_by_column: str | None = None,
    evolution_y_labels_by_metric: str | None = None,
    evolution_selected_algorithms: str | None = None,
    evolution_selected_metrics: str | None = None,
    evolution_selected_instances: str | None = None,
    evolution_show_grid: str | None = None,
    evolution_show_min_max: str | None = None,
    evolution_show_std: str | None = None,
    evolution_show_average: str | None = None,
    evolution_show_median: str | None = None,
    evolution_group_by_instance: str | None = None,
    evolution_group_by_metric: str | None = None,
) -> dict[str, Any]:
    """
    Description:
        Execute selected analysis modules from multipart form input.

    Args:
        analysis (Analysis): Analysis document.
        modules (str): Modules form field.
        metrics_direction (str | None): Optional metrics direction JSON.
        metrics_file (UploadFile | None): Optional metrics CSV upload.
        plot_export_formats (str | None): Optional export formats.
        selected_algorithms (list[str] | None): Optional algorithm filter.
        evolution_title (str | None): Optional evolution title.
        evolution_x_columns (str | None): Optional evolution X columns.
        evolution_x_label (str | None): Optional X label.
        evolution_y_label (str | None): Optional Y label.
        evolution_x_labels_by_column (str | None): Optional X labels map.
        evolution_y_labels_by_metric (str | None): Optional Y labels map.
        evolution_selected_algorithms (str | None): Optional evolution algorithms.
        evolution_selected_metrics (str | None): Optional evolution metrics.
        evolution_selected_instances (str | None): Optional evolution instances.
        evolution_show_grid (str | None): Optional grid toggle.
        evolution_show_min_max (str | None): Optional min/max toggle.
        evolution_show_std (str | None): Optional std toggle.
        evolution_show_average (str | None): Optional average toggle.
        evolution_show_median (str | None): Optional median toggle.
        evolution_group_by_instance (str | None): Optional instance grouping toggle.
        evolution_group_by_metric (str | None): Optional metric grouping toggle.

    Returns:
        dict[str, Any]: Execution response.
    """

    if not analysis.normalized_dataset_file_id and not analysis.raw_dataset_file_id:
        raise HTTPException(400, "Dataset not uploaded")

    parsed_modules = parse_modules_input(modules)
    validate_modules_against_capabilities(analysis, parsed_modules)

    parsed_metrics_direction = parse_metrics_direction_input(metrics_direction)
    parsed_plot_export_formats = parse_plot_export_formats_input(plot_export_formats)

    metrics_file_bytes = None

    if metrics_file is not None:
        if not metrics_file.filename or not metrics_file.filename.endswith(".csv"):
            raise HTTPException(400, "Only CSV files are allowed for metrics file")

        metrics_file_bytes = await metrics_file.read()

    requested_modules = set(parsed_modules)
    requests_saes = any(module in SAES_MODULES for module in requested_modules)

    if requests_saes:
        try:
            analysis.metrics_direction = resolve_metrics_direction(
                metrics=analysis.metrics,
                frontend_config=parsed_metrics_direction,
                csv_bytes=metrics_file_bytes,
            )
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
    elif parsed_metrics_direction:
        analysis.metrics_direction = parsed_metrics_direction

    evolution_options = compact_evolution_options(
        {
            "title": evolution_title,
            "x_columns": parse_evolution_x_columns(evolution_x_columns),
            "x_label": evolution_x_label,
            "y_label": evolution_y_label,
            "x_labels_by_column": parse_string_dict_form_value(
                evolution_x_labels_by_column,
                "evolution_x_labels_by_column",
            ),
            "y_labels_by_metric": parse_string_dict_form_value(
                evolution_y_labels_by_metric,
                "evolution_y_labels_by_metric",
            ),
            "selected_algorithms": parse_string_list_form_value(
                evolution_selected_algorithms,
                "evolution_selected_algorithms",
            ),
            "selected_metrics": parse_string_list_form_value(
                evolution_selected_metrics,
                "evolution_selected_metrics",
            ),
            "selected_instances": parse_string_list_form_value(
                evolution_selected_instances,
                "evolution_selected_instances",
            ),
            "show_grid": parse_bool_form_value(evolution_show_grid, True),
            "show_min_max": parse_bool_form_value(evolution_show_min_max, True),
            "show_std": parse_bool_form_value(evolution_show_std, True),
            "show_average": parse_bool_form_value(evolution_show_average, True),
            "show_median": parse_bool_form_value(evolution_show_median, True),
            "group_by_instance": parse_bool_form_value(
                evolution_group_by_instance,
                True,
            ),
            "group_by_metric": parse_bool_form_value(
                evolution_group_by_metric,
                True,
            ),
        }
    )

    outputs = dict(analysis.outputs or {})
    outputs["evolution_options"] = evolution_options

    analysis.outputs = outputs
    analysis.plot_export_formats = parsed_plot_export_formats
    analysis.enabled_modules = sorted(
        list(set(analysis.enabled_modules or []) | requested_modules)
    )
    analysis.status = "running"
    analysis.updated_at = datetime.now(timezone.utc)

    await analysis.save()

    try:
        await run_analysis_pipeline(
            analysis=analysis,
            modules=sorted(requested_modules),
            selected_algorithms=selected_algorithms,
        )

        if "evolution_plots" in requested_modules:
            persist_evolution_options_for_run(
                analysis=analysis,
                run_key=analysis.current_run_key or "all",
                evolution_options=evolution_options,
            )

        analysis.status = "completed"

    except Exception as error:
        outputs = dict(analysis.outputs or {})
        outputs["error"] = str(error)
        analysis.outputs = outputs
        analysis.status = "failed"

    analysis.updated_at = datetime.now(timezone.utc)
    await analysis.save()

    run_outputs = get_run_outputs(analysis)

    return {
        "analysis_id": str(analysis.id),
        "modules": analysis.enabled_modules,
        "status": analysis.status,
        "metrics_direction": analysis.metrics_direction,
        "plot_export_formats": analysis.plot_export_formats,
        "selected_algorithms_last_run": analysis.selected_algorithms_last_run,
        "current_run_key": analysis.current_run_key,
        "dataset_capabilities": analysis.dataset_capabilities,
        "outputs": serialize_outputs(run_outputs),
        "error": (analysis.outputs or {}).get("error"),
    }


async def execute_reanalysis(
    analysis: Analysis,
    selected_algorithms: list[str],
    modules: list[str] | None = None,
    selected_plot_types: list[str] | None = None,
    evolution_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Description:
        Execute a reanalysis for an existing analysis.

    Args:
        analysis (Analysis): Analysis document.
        selected_algorithms (list[str]): Selected algorithms.
        modules (list[str] | None): Modules to execute.
        selected_plot_types (list[str] | None): Selected plot types.
        evolution_options (dict[str, Any] | None): Evolution plot configuration.

    Returns:
        dict[str, Any]: Reanalysis result and generated outputs.

    Raises:
        HTTPException: Raised when the dataset or algorithms are invalid.
    """
    cleaned_algorithms = [
        value.strip()
        for value in selected_algorithms
        if isinstance(value, str) and value.strip()
    ]

    if not cleaned_algorithms:
        raise HTTPException(400, "At least one algorithm must be selected")

    if not analysis.normalized_dataset_file_id and not analysis.raw_dataset_file_id:
        raise HTTPException(400, "Dataset not uploaded")

    selected_modules = get_reanalysis_modules(analysis, modules)
    normalized_plot_types = normalize_plot_types_list(selected_plot_types)
    saes_plot_types = get_saes_plot_types(normalized_plot_types)

    compacted_evolution_options = normalize_statistics_options(
        compact_evolution_options(evolution_options)
    )

    evolution_signature = build_evolution_options_signature(compacted_evolution_options)

    run_key = build_algorithm_run_key(
        selected_algorithms=cleaned_algorithms,
        all_algorithms=list(analysis.algorithms or []),
    )

    outputs = dict(analysis.outputs or {})

    if compacted_evolution_options:
        outputs["evolution_options"] = compacted_evolution_options
        analysis.outputs = outputs

    analysis_runs = dict(outputs.get("analysis_runs") or {})
    run_outputs = analysis_runs.get(run_key)

    modules_to_run = get_modules_pending_reanalysis(
        selected_modules=selected_modules,
        run_outputs=run_outputs if isinstance(run_outputs, dict) else None,
        selected_plot_types=saes_plot_types,
        evolution_signature=evolution_signature,
    )

    modules_to_run = sorted(set(modules_to_run))

    analysis.enabled_modules = sorted(
        list(set(analysis.enabled_modules or []) | set(selected_modules))
    )
    analysis.selected_algorithms_last_run = cleaned_algorithms
    analysis.current_run_key = run_key

    if not modules_to_run:
        if compacted_evolution_options:
            persist_evolution_options_for_run(
                analysis=analysis,
                run_key=run_key,
                evolution_options=compacted_evolution_options,
            )

        analysis.status = "completed"
        analysis.updated_at = datetime.now(timezone.utc)

        await analysis.save()

        return {
            "analysis_id": str(analysis.id),
            "modules": analysis.enabled_modules,
            "status": analysis.status,
            "metrics_direction": analysis.metrics_direction,
            "plot_export_formats": analysis.plot_export_formats,
            "selected_algorithms_last_run": analysis.selected_algorithms_last_run,
            "selected_plot_types_last_run": normalized_plot_types,
            "current_run_key": analysis.current_run_key,
            "outputs": serialize_outputs(get_run_outputs(analysis, run_key=run_key)),
            "error": None,
        }

    analysis.status = "running"
    analysis.updated_at = datetime.now(timezone.utc)

    await analysis.save()

    try:
        await run_analysis_pipeline(
            analysis=analysis,
            modules=modules_to_run,
            selected_algorithms=cleaned_algorithms,
            selected_plot_types=saes_plot_types,
        )

        if "evolution_plots" in modules_to_run and compacted_evolution_options:
            persist_evolution_options_for_run(
                analysis=analysis,
                run_key=run_key,
                evolution_options=compacted_evolution_options,
            )

        analysis.status = "completed"

    except Exception as error:
        outputs = dict(analysis.outputs or {})
        outputs["error"] = str(error)
        analysis.outputs = outputs
        analysis.status = "failed"

    analysis.updated_at = datetime.now(timezone.utc)

    await analysis.save()

    return {
        "analysis_id": str(analysis.id),
        "modules": analysis.enabled_modules,
        "status": analysis.status,
        "metrics_direction": analysis.metrics_direction,
        "plot_export_formats": analysis.plot_export_formats,
        "selected_algorithms_last_run": analysis.selected_algorithms_last_run,
        "selected_plot_types_last_run": normalized_plot_types,
        "current_run_key": analysis.current_run_key,
        "outputs": serialize_outputs(get_run_outputs(analysis, run_key=run_key)),
        "error": (analysis.outputs or {}).get("error"),
    }


async def get_user_analysis(
    analysis_id: PydanticObjectId,
    user_id: PydanticObjectId,
) -> Analysis:
    """
    Description:
        Fetch an analysis and ensure it belongs to the authenticated user.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        user_id (PydanticObjectId): Current user identifier.

    Returns:
        Analysis: Matching analysis document.
    """

    analysis = await Analysis.get(analysis_id)

    if not analysis or analysis.user_id != user_id:
        raise HTTPException(404, "Analysis not found")

    return analysis


@router.post("/")
async def create_analysis(
    data: AnalysisCreate,
    user: Annotated[User, Depends(get_authenticated_user)],
):
    """
    Description:
        Create a new analysis for the authenticated user.

    Args:
        data (AnalysisCreate): Analysis creation payload.
        user (User): Currently authenticated user.

    Returns:
        Analysis: Persisted analysis document.
    """

    analysis = Analysis(
        user_id=user.id,
        name=data.name,
        description=data.description,
        plot_export_formats=["png"],
        dataset_capabilities={
            "saes_plots": False,
            "saes_reports": False,
            "notebooks": False,
            "evolution_plots": False,
        },
    )

    await analysis.insert()
    return analysis


@router.get("/")
async def list_analyses(user: Annotated[User, Depends(get_authenticated_user)]):
    """
    Description:
        List all analyses owned by the authenticated user.

    Args:
        user (User): Currently authenticated user.

    Returns:
        list[Analysis]: Analyses linked to the user.
    """

    return await Analysis.find(Analysis.user_id == user.id).to_list()


@router.get("/{analysis_id}")
async def get_analysis(
    analysis_id: PydanticObjectId,
    user: Annotated[User, Depends(get_authenticated_user)],
):
    """
    Description:
        Fetch a single analysis owned by the authenticated user.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        user (User): Currently authenticated user.

    Returns:
        Analysis: Matching analysis document.
    """

    return await get_user_analysis(analysis_id, user.id)


@router.patch("/{analysis_id}")
async def update_analysis(
    analysis_id: PydanticObjectId,
    data: AnalysisCreate,
    user: Annotated[User, Depends(get_authenticated_user)],
):
    """
    Description:
        Update an analysis name and description.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        data (AnalysisCreate): Updated analysis payload.
        user (User): Currently authenticated user.

    Returns:
        Analysis: Updated analysis document.
    """

    analysis = await get_user_analysis(analysis_id, user.id)
    analysis.name = data.name
    analysis.description = data.description
    analysis.updated_at = datetime.now(timezone.utc)

    await analysis.save()
    return analysis


@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: PydanticObjectId,
    user: Annotated[User, Depends(get_authenticated_user)],
):
    """
    Description:
        Delete an analysis owned by the authenticated user.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        user (User): Currently authenticated user.

    Returns:
        dict[str, str]: Confirmation message.
    """

    analysis = await get_user_analysis(analysis_id, user.id)

    await analysis.delete()
    return {"message": "Analysis deleted"}


@router.post("/{analysis_id}/inspect-dataset")
async def inspect_uploaded_dataset(
    analysis_id: PydanticObjectId,
    file: Annotated[UploadFile, File(...)],
    user: Annotated[User, Depends(get_authenticated_user)],
):
    """
    Description:
        Inspect an uploaded CSV without persisting it.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        file (UploadFile): Uploaded CSV file.
        user (User): Currently authenticated user.

    Returns:
        dict[str, Any]: Dataset inspection result.
    """

    await get_user_analysis(analysis_id, user.id)

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are allowed")

    content = await file.read()

    try:
        return inspect_dataset(content)
    except DatasetFormatError as error:
        raise HTTPException(400, str(error)) from error
    except Exception as error:
        raise HTTPException(400, f"Invalid CSV format: {error}") from error


@router.post("/{analysis_id}/upload-dataset")
async def upload_dataset(
    analysis_id: PydanticObjectId,
    file: Annotated[UploadFile, File(...)],
    user: Annotated[User, Depends(get_authenticated_user)],
):
    """
    Description:
        Upload, validate, normalize and store a dataset for an analysis.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        file (UploadFile): Uploaded CSV file.
        user (User): Currently authenticated user.

    Returns:
        dict[str, Any]: Upload summary and detected metadata.
    """

    analysis = await get_user_analysis(analysis_id, user.id)

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are allowed")

    content = await file.read()

    try:
        rows, capabilities = parse_dataset(content)
        validate_dataset(rows)
    except DatasetFormatError as error:
        raise HTTPException(400, str(error)) from error
    except DatasetValidationError as error:
        raise HTTPException(400, str(error)) from error
    except Exception as error:
        raise HTTPException(400, f"Invalid CSV format: {error}") from error

    metadata = extract_metadata(rows)
    normalized_csv = normalize_dataset(content)

    raw_file_id = await save_file(file.filename, content)
    normalized_file_id = await save_file(
        f"normalized_{file.filename}",
        normalized_csv.encode("utf-8"),
    )

    analysis.raw_dataset_file_id = raw_file_id
    analysis.raw_dataset_filename = file.filename
    analysis.normalized_dataset_file_id = normalized_file_id
    analysis.filtered_dataset_file_ids = {}
    analysis.dataset_capabilities = {
        "saes_plots": bool(capabilities.get("saes_plots")),
        "saes_reports": bool(capabilities.get("saes_reports")),
        "notebooks": bool(capabilities.get("notebooks")),
        "evolution_plots": bool(capabilities.get("evolution_plots")),
    }
    analysis.algorithms = metadata["algorithms"]
    analysis.problems = metadata["problems"]
    analysis.metrics = metadata["metrics"]
    analysis.metrics_direction = (
        get_default_metrics_direction(metadata["metrics"])
        if analysis.dataset_capabilities.get("saes_plots") and metadata["metrics"]
        else {}
    )
    analysis.metrics_config_file_id = None
    analysis.plot_export_formats = ["png"]
    analysis.outputs = {}
    analysis.enabled_modules = []
    analysis.num_runs = metadata["runs"]
    analysis.evolution_metadata = metadata.get("evolution", {})
    analysis.selected_algorithms_last_run = []
    analysis.current_run_key = "all"
    analysis.status = "dataset_uploaded"
    analysis.updated_at = datetime.now(timezone.utc)

    await analysis.save()

    return {
        "message": "Dataset uploaded",
        "analysis_id": str(analysis.id),
        "raw_dataset_filename": analysis.raw_dataset_filename,
        "dataset_capabilities": analysis.dataset_capabilities,
        "metadata": {
            "algorithms": analysis.algorithms,
            "problems": analysis.problems,
            "metrics": analysis.metrics,
            "runs": analysis.num_runs,
            "evolution": analysis.evolution_metadata,
        },
        "default_modules": build_default_modules_from_capabilities(
            analysis.dataset_capabilities
        ),
    }


async def _execute_analysis_from_form(
    analysis_id: PydanticObjectId,
    user: User,
    modules: str,
    metrics_direction: str | None,
    metrics_file: UploadFile | None,
    plot_export_formats: str | None,
    evolution_title: str | None,
    evolution_x_columns: str | None,
    evolution_x_label: str | None,
    evolution_y_label: str | None,
    evolution_x_labels_by_column: str | None,
    evolution_y_labels_by_metric: str | None,
    evolution_selected_algorithms: str | None,
    evolution_selected_metrics: str | None,
    evolution_selected_instances: str | None,
    evolution_show_grid: str | None,
    evolution_show_min_max: str | None,
    evolution_show_std: str | None,
    evolution_show_average: str | None,
    evolution_show_median: str | None,
    evolution_group_by_instance: str | None,
    evolution_group_by_metric: str | None,
):
    """
    Description:
        Shared implementation for POST/PATCH analyze endpoints.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        user (User): Currently authenticated user.
        modules (str): Modules form value.
        metrics_direction (str | None): Optional metrics direction value.
        metrics_file (UploadFile | None): Optional metrics CSV.
        plot_export_formats (str | None): Optional export formats value.
        evolution_title (str | None): Optional evolution title.
        evolution_x_columns (str | None): Optional X columns.
        evolution_x_label (str | None): Optional X label.
        evolution_y_label (str | None): Optional Y label.
        evolution_x_labels_by_column (str | None): Optional X labels dictionary.
        evolution_y_labels_by_metric (str | None): Optional Y labels dictionary.
        evolution_selected_algorithms (str | None): Optional selected algorithms.
        evolution_selected_metrics (str | None): Optional selected metrics.
        evolution_selected_instances (str | None): Optional selected instances.
        evolution_show_grid (str | None): Optional grid toggle.
        evolution_show_min_max (str | None): Optional min/max toggle.
        evolution_show_std (str | None): Optional standard deviation toggle.
        evolution_show_average (str | None): Optional average toggle.
        evolution_show_median (str | None): Optional median toggle.
        evolution_group_by_instance (str | None): Optional grouping toggle.
        evolution_group_by_metric (str | None): Optional grouping toggle.

    Returns:
        dict[str, Any]: Analysis execution response.
    """

    analysis = await get_user_analysis(analysis_id, user.id)

    return await execute_analysis_modules(
        analysis=analysis,
        modules=modules,
        metrics_direction=metrics_direction,
        metrics_file=metrics_file,
        plot_export_formats=plot_export_formats,
        evolution_title=evolution_title,
        evolution_x_columns=evolution_x_columns,
        evolution_x_label=evolution_x_label,
        evolution_y_label=evolution_y_label,
        evolution_x_labels_by_column=evolution_x_labels_by_column,
        evolution_y_labels_by_metric=evolution_y_labels_by_metric,
        evolution_selected_algorithms=evolution_selected_algorithms,
        evolution_selected_metrics=evolution_selected_metrics,
        evolution_selected_instances=evolution_selected_instances,
        evolution_show_grid=evolution_show_grid,
        evolution_show_min_max=evolution_show_min_max,
        evolution_show_std=evolution_show_std,
        evolution_show_average=evolution_show_average,
        evolution_show_median=evolution_show_median,
        evolution_group_by_instance=evolution_group_by_instance,
        evolution_group_by_metric=evolution_group_by_metric,
    )


@router.post("/{analysis_id}/analyze")
async def analyze_analysis(
    analysis_id: PydanticObjectId,
    modules: Annotated[str, Form(...)],
    user: Annotated[User, Depends(get_authenticated_user)],
    metrics_direction: Annotated[str | None, Form()] = None,
    metrics_file: Annotated[UploadFile | None, File()] = None,
    plot_export_formats: Annotated[str | None, Form()] = None,
    evolution_title: Annotated[str | None, Form()] = None,
    evolution_x_columns: Annotated[str | None, Form()] = None,
    evolution_x_label: Annotated[str | None, Form()] = None,
    evolution_y_label: Annotated[str | None, Form()] = None,
    evolution_x_labels_by_column: Annotated[str | None, Form()] = None,
    evolution_y_labels_by_metric: Annotated[str | None, Form()] = None,
    evolution_selected_algorithms: Annotated[str | None, Form()] = None,
    evolution_selected_metrics: Annotated[str | None, Form()] = None,
    evolution_selected_instances: Annotated[str | None, Form()] = None,
    evolution_show_grid: Annotated[str | None, Form()] = None,
    evolution_show_min_max: Annotated[str | None, Form()] = None,
    evolution_show_std: Annotated[str | None, Form()] = None,
    evolution_show_average: Annotated[str | None, Form()] = None,
    evolution_show_median: Annotated[str | None, Form()] = None,
    evolution_group_by_instance: Annotated[str | None, Form()] = None,
    evolution_group_by_metric: Annotated[str | None, Form()] = None,
):
    """
    Description:
        Execute the selected analysis modules for the current analysis.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        modules (str): Modules form value.
        user (User): Currently authenticated user.
        metrics_direction (str | None): Optional metrics direction.
        metrics_file (UploadFile | None): Optional metrics CSV file.
        plot_export_formats (str | None): Optional export formats.
        evolution_title (str | None): Optional evolution title.
        evolution_x_columns (str | None): Optional X columns.
        evolution_x_label (str | None): Optional X-axis label.
        evolution_y_label (str | None): Optional Y-axis label.
        evolution_x_labels_by_column (str | None): Optional X labels dictionary.
        evolution_y_labels_by_metric (str | None): Optional Y labels dictionary.
        evolution_selected_algorithms (str | None): Optional algorithms.
        evolution_selected_metrics (str | None): Optional metrics.
        evolution_selected_instances (str | None): Optional instances.
        evolution_show_grid (str | None): Optional grid toggle.
        evolution_show_min_max (str | None): Optional min/max toggle.
        evolution_show_std (str | None): Optional standard deviation toggle.
        evolution_show_average (str | None): Optional average toggle.
        evolution_show_median (str | None): Optional median toggle.
        evolution_group_by_instance (str | None): Optional instance grouping toggle.
        evolution_group_by_metric (str | None): Optional metric grouping toggle.

    Returns:
        dict[str, Any]: Analysis execution response.
    """

    return await _execute_analysis_from_form(
        analysis_id,
        user,
        modules,
        metrics_direction,
        metrics_file,
        plot_export_formats,
        evolution_title,
        evolution_x_columns,
        evolution_x_label,
        evolution_y_label,
        evolution_x_labels_by_column,
        evolution_y_labels_by_metric,
        evolution_selected_algorithms,
        evolution_selected_metrics,
        evolution_selected_instances,
        evolution_show_grid,
        evolution_show_min_max,
        evolution_show_std,
        evolution_show_average,
        evolution_show_median,
        evolution_group_by_instance,
        evolution_group_by_metric,
    )


@router.patch("/{analysis_id}/analyze")
async def update_analysis_execution(
    analysis_id: PydanticObjectId,
    modules: Annotated[str, Form(...)],
    user: Annotated[User, Depends(get_authenticated_user)],
    metrics_direction: Annotated[str | None, Form()] = None,
    metrics_file: Annotated[UploadFile | None, File()] = None,
    plot_export_formats: Annotated[str | None, Form()] = None,
    evolution_title: Annotated[str | None, Form()] = None,
    evolution_x_columns: Annotated[str | None, Form()] = None,
    evolution_x_label: Annotated[str | None, Form()] = None,
    evolution_y_label: Annotated[str | None, Form()] = None,
    evolution_x_labels_by_column: Annotated[str | None, Form()] = None,
    evolution_y_labels_by_metric: Annotated[str | None, Form()] = None,
    evolution_selected_algorithms: Annotated[str | None, Form()] = None,
    evolution_selected_metrics: Annotated[str | None, Form()] = None,
    evolution_selected_instances: Annotated[str | None, Form()] = None,
    evolution_show_grid: Annotated[str | None, Form()] = None,
    evolution_show_min_max: Annotated[str | None, Form()] = None,
    evolution_show_std: Annotated[str | None, Form()] = None,
    evolution_show_average: Annotated[str | None, Form()] = None,
    evolution_show_median: Annotated[str | None, Form()] = None,
    evolution_group_by_instance: Annotated[str | None, Form()] = None,
    evolution_group_by_metric: Annotated[str | None, Form()] = None,
):
    """
    Description:
        Re-run the analysis pipeline with updated execution parameters.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        modules (str): Modules form value.
        user (User): Currently authenticated user.
        metrics_direction (str | None): Optional metrics direction.
        metrics_file (UploadFile | None): Optional metrics CSV file.
        plot_export_formats (str | None): Optional export formats.
        evolution_title (str | None): Optional evolution title.
        evolution_x_columns (str | None): Optional X columns.
        evolution_x_label (str | None): Optional X-axis label.
        evolution_y_label (str | None): Optional Y-axis label.
        evolution_x_labels_by_column (str | None): Optional X labels dictionary.
        evolution_y_labels_by_metric (str | None): Optional Y labels dictionary.
        evolution_selected_algorithms (str | None): Optional algorithms.
        evolution_selected_metrics (str | None): Optional metrics.
        evolution_selected_instances (str | None): Optional instances.
        evolution_show_grid (str | None): Optional grid toggle.
        evolution_show_min_max (str | None): Optional min/max toggle.
        evolution_show_std (str | None): Optional standard deviation toggle.
        evolution_show_average (str | None): Optional average toggle.
        evolution_show_median (str | None): Optional median toggle.
        evolution_group_by_instance (str | None): Optional instance grouping toggle.
        evolution_group_by_metric (str | None): Optional metric grouping toggle.

    Returns:
        dict[str, Any]: Updated analysis execution response.
    """

    return await _execute_analysis_from_form(
        analysis_id,
        user,
        modules,
        metrics_direction,
        metrics_file,
        plot_export_formats,
        evolution_title,
        evolution_x_columns,
        evolution_x_label,
        evolution_y_label,
        evolution_x_labels_by_column,
        evolution_y_labels_by_metric,
        evolution_selected_algorithms,
        evolution_selected_metrics,
        evolution_selected_instances,
        evolution_show_grid,
        evolution_show_min_max,
        evolution_show_std,
        evolution_show_average,
        evolution_show_median,
        evolution_group_by_instance,
        evolution_group_by_metric,
    )


@router.post("/{analysis_id}/reanalyze")
@router.patch("/{analysis_id}/reanalyze")
async def update_reanalysis(
    analysis_id: PydanticObjectId,
    payload: Annotated[AnalysisReanalyzeRequest, Body(...)],
    user: Annotated[User, Depends(get_authenticated_user)],
):
    """
    Description:
        Reanalyze an existing analysis.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        payload (AnalysisReanalyzeRequest): Reanalysis configuration.
        user (User): Currently authenticated user.

    Returns:
        dict[str, Any]: Reanalysis result and generated outputs.
    """
    analysis = await get_user_analysis(analysis_id, user.id)

    return await execute_reanalysis(
        analysis=analysis,
        selected_algorithms=payload.selected_algorithms,
        modules=payload.modules,
        selected_plot_types=payload.selected_plot_types,
        evolution_options=build_evolution_options_from_payload(payload),
    )


@router.get("/{analysis_id}/runs")
async def list_analysis_runs(
    analysis_id: PydanticObjectId,
    user: Annotated[User, Depends(get_authenticated_user)],
):
    """
    Description:
        List execution runs stored for an analysis.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        user (User): Currently authenticated user.

    Returns:
        dict[str, Any]: Run metadata grouped by run key.
    """

    analysis = await get_user_analysis(analysis_id, user.id)
    analysis_runs = dict((analysis.outputs or {}).get("analysis_runs") or {})

    return {
        run_key: {
            "selected_algorithms": run_outputs.get("selected_algorithms", []),
            "modules": run_outputs.get("modules", []),
            "categories": serialize_outputs(run_outputs),
        }
        for run_key, run_outputs in analysis_runs.items()
        if isinstance(run_outputs, dict)
    }


@router.get("/{analysis_id}/files")
async def list_files(
    analysis_id: PydanticObjectId,
    user: Annotated[User, Depends(get_authenticated_user)],
    run_key: Annotated[str | None, Query()] = None,
):
    """
    Description:
        List generated files for a given analysis run.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        user (User): Currently authenticated user.
        run_key (str | None): Optional run key.

    Returns:
        dict[str, list[str]]: Files grouped by category.
    """

    analysis = await get_user_analysis(analysis_id, user.id)

    return serialize_outputs(get_run_outputs(analysis, run_key=run_key))


@router.get("/{analysis_id}/files/{category}/zip")
async def download_analysis_category_zip(
    analysis_id: PydanticObjectId,
    category: str,
    user: Annotated[User, Depends(get_authenticated_user)],
    run_key: Annotated[str | None, Query()] = None,
):
    """
    Description:
        Download every file in a category as a ZIP archive.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        category (str): Output category.
        user (User): Currently authenticated user.
        run_key (str | None): Optional run key.

    Returns:
        StreamingResponse: ZIP archive response.
    """

    analysis = await get_user_analysis(analysis_id, user.id)
    run_outputs = get_run_outputs(analysis, run_key=run_key)
    category_files = get_category_files(run_outputs, category)

    if not category_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No files found for this category",
        )

    zip_buffer = io.BytesIO()
    added_files = 0

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        items = category_files.items() if isinstance(category_files, dict) else []

        for filename, file_id in items:
            if not file_id:
                continue

            try:
                file_bytes = await get_file(file_id)
                safe_filename = sanitize_zip_name(filename) or f"file_{added_files + 1}"
                zip_file.writestr(safe_filename, file_bytes)
                added_files += 1
            except Exception:
                continue

    if added_files == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No downloadable files found for this category",
        )

    zip_buffer.seek(0)

    safe_analysis_name = sanitize_zip_name(analysis.name or "analysis")
    safe_category = sanitize_zip_name(category)
    safe_run_key = sanitize_zip_name(run_key or analysis.current_run_key or "all")
    zip_name = f"{safe_analysis_name}_{safe_run_key}_{safe_category}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


@router.get("/{analysis_id}/files/{category}/{filename:path}")
async def download_file(
    analysis_id: PydanticObjectId,
    category: str,
    filename: str,
    user: Annotated[User, Depends(get_authenticated_user)],
    download: bool = True,
    run_key: Annotated[str | None, Query()] = None,
):
    """
    Description:
        Download or stream a single generated file.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        category (str): Output category.
        filename (str): File name.
        user (User): Currently authenticated user.
        download (bool): Whether to force attachment download.
        run_key (str | None): Optional run key.

    Returns:
        Response: File response.
    """

    analysis = await get_user_analysis(analysis_id, user.id)
    run_outputs = get_run_outputs(analysis, run_key=run_key)
    category_data = get_category_files(run_outputs, category)

    if not isinstance(category_data, dict):
        raise HTTPException(404, "Category not found")

    if filename not in category_data:
        raise HTTPException(404, f"File not found: {filename}")

    file_id = category_data[filename]
    file_data = await get_file(file_id)

    if file_data is None:
        raise HTTPException(404, f"Stored file not found: {filename}")

    disposition = "attachment" if download else "inline"

    return Response(
        content=file_data,
        media_type=get_media_type(filename),
        headers={
            "Content-Disposition": (
                f'{disposition}; filename="{filename.split("/")[-1]}"'
            ),
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/{analysis_id}/dataset/raw")
async def download_raw_dataset(
    analysis_id: PydanticObjectId,
    user: Annotated[User, Depends(get_authenticated_user)],
):
    """
    Description:
        Download the original raw dataset.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        user (User): Currently authenticated user.

    Returns:
        Response: Raw dataset CSV response.
    """

    analysis = await get_user_analysis(analysis_id, user.id)

    if not analysis.raw_dataset_file_id:
        raise HTTPException(404, "Raw dataset file not found")

    file_data = await get_file(analysis.raw_dataset_file_id)

    return Response(
        content=file_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=raw_dataset.csv"},
    )


@router.get("/{analysis_id}/dataset/normalized")
async def download_normalized_dataset(
    analysis_id: PydanticObjectId,
    user: Annotated[User, Depends(get_authenticated_user)],
):
    """
    Description:
        Download the normalized dataset.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        user (User): Currently authenticated user.

    Returns:
        Response: Normalized dataset CSV response.
    """

    analysis = await get_user_analysis(analysis_id, user.id)

    if not analysis.normalized_dataset_file_id:
        raise HTTPException(404, "Normalized dataset file not found")

    file_data = await get_file(analysis.normalized_dataset_file_id)

    return Response(
        content=file_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=normalized_dataset.csv"},
    )


@router.get("/{analysis_id}/dataset/filtered")
async def download_filtered_dataset(
    analysis_id: PydanticObjectId,
    user: Annotated[User, Depends(get_authenticated_user)],
    run_key: Annotated[str | None, Query()] = None,
):
    """
    Description:
        Download the filtered dataset for a specific run.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        user (User): Currently authenticated user.
        run_key (str | None): Optional run key.

    Returns:
        Response: Filtered dataset CSV response.
    """

    analysis = await get_user_analysis(analysis_id, user.id)
    resolved_run_key = run_key or analysis.current_run_key or "all"
    file_id = (analysis.filtered_dataset_file_ids or {}).get(resolved_run_key)

    if not file_id:
        raise HTTPException(404, "Filtered dataset file not found")

    file_data = await get_file(file_id)

    return Response(
        content=file_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="filtered_dataset_{resolved_run_key}.csv"'
            )
        },
    )


@router.get("/{analysis_id}/metrics")
async def download_metrics(
    analysis_id: PydanticObjectId,
    user: Annotated[User, Depends(get_authenticated_user)],
):
    """
    Description:
        Download the metrics configuration CSV.

    Args:
        analysis_id (PydanticObjectId): Analysis identifier.
        user (User): Currently authenticated user.

    Returns:
        Response: Metrics CSV response.
    """

    analysis = await get_user_analysis(analysis_id, user.id)

    if not analysis.metrics_config_file_id:
        raise HTTPException(404, "Metrics file not found")

    file_data = await get_file(analysis.metrics_config_file_id)

    return Response(
        content=file_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=metrics.csv"},
    )
