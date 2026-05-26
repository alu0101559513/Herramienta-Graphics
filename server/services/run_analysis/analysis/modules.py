from __future__ import annotations

from typing import Any, Final

SAES_MODULES: Final = {"saes_plots", "saes_reports", "notebooks"}
EVOLUTION_MODULES: Final = {"evolution_plots"}
ALL_ALLOWED_MODULES: Final = SAES_MODULES | EVOLUTION_MODULES

ALLOWED_EXPORT_FORMATS: Final = {"png", "eps", "svg", "jpg", "jpeg"}
DEFAULT_PLOT_TYPES: Final = {"boxplot", "violin", "histogram", "critical_distance"}

OUTPUT_CATEGORIES: Final = (
    "saes_plots",
    "saes_reports",
    "notebooks",
    "evolution_plots",
    "evolution_metadata",
    "evolution_plot_sets",
    "saes_plot_warnings",
    "saes_report_warnings",
    "evolution_plot_warnings",
    "generated_plot_types",
    "evolution_options",
    "evolution_options_signature",
)


def normalize_requested_plot_types(selected_plot_types: list[str] | None) -> set[str]:
    """
    Description:
        Normalize requested SAES plot types.

        When no plot types are provided, all default plot types are returned.
        Empty strings and non-string values are ignored.

    Args:
        selected_plot_types (list[str] | None):
            Plot types requested by the user or frontend.

    Returns:
        set[str]:
            Normalized plot type names.
    """

    requested = {
        value.strip()
        for value in (selected_plot_types or DEFAULT_PLOT_TYPES)
        if isinstance(value, str) and value.strip()
    }

    return requested or set(DEFAULT_PLOT_TYPES)


def get_modules_pending_reanalysis(
    *,
    selected_modules: list[str],
    run_outputs: dict[str, Any] | None,
    selected_plot_types: list[str] | None,
    evolution_signature: str | None = None,
) -> list[str]:
    """
    Description:
        Determine which selected modules still need to be generated.

    Args:
        selected_modules (list[str]): Requested modules.
        run_outputs (dict[str, Any] | None): Existing outputs for the run.
        selected_plot_types (list[str] | None): Requested SAES plot types.
        evolution_signature (str | None): Requested evolution options signature.

    Returns:
        list[str]: Pending modules to generate.
    """

    if not isinstance(run_outputs, dict):
        return sorted(set(selected_modules))

    requested_plot_types = normalize_requested_plot_types(selected_plot_types)

    generated_plot_types = {
        value.strip()
        for value in run_outputs.get("generated_plot_types", [])
        if isinstance(value, str) and value.strip()
    }

    pending_modules: list[str] = []

    for module in selected_modules:
        module_outputs = run_outputs.get(module)

        if module == "saes_plots":
            if not isinstance(module_outputs, dict) or not module_outputs:
                pending_modules.append(module)
                continue

            if not requested_plot_types.issubset(generated_plot_types):
                pending_modules.append(module)

            continue

        if module == "evolution_plots":
            if evolution_signature is None:
                if not isinstance(module_outputs, dict) or not module_outputs:
                    pending_modules.append(module)

                continue

            evolution_plot_sets = run_outputs.get("evolution_plot_sets")

            if not isinstance(evolution_plot_sets, dict):
                pending_modules.append(module)
                continue

            already_exists = any(
                plot_set.get("signature") == evolution_signature
                for plot_set in evolution_plot_sets.values()
                if isinstance(plot_set, dict)
            )

            if not already_exists:
                pending_modules.append(module)

            continue

        if not isinstance(module_outputs, dict) or not module_outputs:
            pending_modules.append(module)

    return sorted(set(pending_modules))


def build_algorithm_run_key(
    selected_algorithms: list[str],
    all_algorithms: list[str],
) -> str:
    """
    Description:
        Build a stable run key from selected algorithms.

        If no algorithm is selected, or if all algorithms are selected,
        the run key is "all". Otherwise, selected algorithm names are
        normalized and joined with double underscores.

    Args:
        selected_algorithms (list[str]):
            Algorithms selected for the run.

        all_algorithms (list[str]):
            All algorithms available in the analysis.

    Returns:
        str:
            Stable run key.
    """

    selected = sorted({value.strip() for value in selected_algorithms if value.strip()})
    all_values = sorted({value.strip() for value in all_algorithms if value.strip()})

    if not selected or selected == all_values:
        return "all"

    return "__".join(
        value.lower().replace(" ", "_").replace("/", "_").replace("\\", "_")
        for value in selected
    )


def normalize_modules(modules: list[str]) -> list[str]:
    """
    Description:
        Normalize and validate requested analysis modules.

        Legacy notebook module names are converted to "notebooks".
        Duplicate modules are removed while preserving order.

    Args:
        modules (list[str]):
            Requested module names.

    Returns:
        list[str]:
            Normalized unique module names.
    """

    if not modules:
        raise ValueError("At least one module must be selected")

    normalized_modules: list[str] = []

    for module in modules:
        normalized_module = str(module).strip()

        if normalized_module in {"saes_notebook", "saes_notebooks"}:
            normalized_module = "notebooks"

        if normalized_module not in ALL_ALLOWED_MODULES:
            raise ValueError(f"Invalid module '{normalized_module}'")

        if normalized_module not in normalized_modules:
            normalized_modules.append(normalized_module)

    return normalized_modules


def normalize_export_formats(analysis) -> list[str]:
    """
    Description:
        Normalize and validate export formats configured in an analysis.

        PDF is ignored because the current plot exporters do not support it.
        When no valid format remains, PNG is used as fallback.

    Args:
        analysis:
            Analysis document containing plot_export_formats.

    Returns:
        list[str]:
            Valid export formats.
    """

    raw_formats = getattr(analysis, "plot_export_formats", None) or ["png"]
    formats: list[str] = []

    for value in raw_formats:
        export_format = str(value).strip().lower()

        if not export_format or export_format == "pdf":
            continue

        if export_format not in ALLOWED_EXPORT_FORMATS:
            raise ValueError(
                f"Invalid export format '{export_format}'. "
                f"Allowed formats: {', '.join(sorted(ALLOWED_EXPORT_FORMATS))}."
            )

        if export_format not in formats:
            formats.append(export_format)

    return formats or ["png"]


def get_capabilities(analysis) -> dict[str, bool]:
    """
    Description:
        Read dataset capabilities from an analysis document.

    Args:
        analysis:
            Analysis document.

    Returns:
        dict[str, bool]:
            Dataset capabilities or an empty dictionary.
    """

    capabilities = getattr(analysis, "dataset_capabilities", None)
    return capabilities if isinstance(capabilities, dict) else {}


def validate_requested_modules(analysis, modules: list[str]) -> None:
    """
    Description:
        Validate that requested modules are available for the dataset.

        SAES modules require SAES-compatible columns.
        Evolution plots require evolution-compatible columns.

    Args:
        analysis:
            Analysis document.

        modules (list[str]):
            Requested module names.

    Returns:
        None
    """

    capabilities = get_capabilities(analysis)

    if any(module in SAES_MODULES for module in modules) and not capabilities.get(
        "saes_plots",
        False,
    ):
        raise ValueError(
            "SAES outputs are not available for this dataset. "
            "The CSV must contain Algorithm, Instance, MetricName, ExecutionId "
            "and MetricValue."
        )

    if "evolution_plots" in modules and not capabilities.get("evolution_plots", False):
        raise ValueError(
            "Evolution plots are not available for this dataset. "
            "The CSV must contain Algorithm, MetricValue/Fitness, "
            "and at least one X column such as Generation, Time, "
            "Evaluations or Iteration."
        )


def get_metrics(analysis) -> list[str]:
    """
    Description:
        Read valid metric names from an analysis document.

    Args:
        analysis:
            Analysis document.

    Returns:
        list[str]:
            Clean non-empty metric names.
    """

    return [
        metric.strip()
        for metric in getattr(analysis, "metrics", []) or []
        if isinstance(metric, str) and metric.strip()
    ]


def get_instances(analysis) -> list[str]:
    """
    Description:
        Read valid instance names from an analysis document.

    Args:
        analysis:
            Analysis document.

    Returns:
        list[str]:
            Clean non-empty instance names.
    """

    return [
        problem.strip()
        for problem in getattr(analysis, "problems", []) or []
        if isinstance(problem, str) and problem.strip()
    ]
