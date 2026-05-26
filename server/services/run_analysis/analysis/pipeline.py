from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from server.services.dataset.parsing import parse_dataset
from server.services.graphics.evolution_plots import generate_evolution_plots
from server.services.graphics.notebook_report import build_analysis_notebook
from server.services.graphics.reports import reports_saes
from server.services.graphics.saes_graphics.exporter import export_saes_dataset
from server.services.graphics.saes_graphics.metrics_config import (
    generate_metrics_csv,
    resolve_metrics_direction,
)
from server.services.graphics.saes_graphics.plots import plot_cd_saes, plots_saes
from server.services.gridfs import get_file, save_file
from server.services.run_analysis.analysis.modules import (
    OUTPUT_CATEGORIES,
    SAES_MODULES,
    build_algorithm_run_key,
    get_instances,
    get_metrics,
    normalize_export_formats,
    normalize_modules,
    normalize_requested_plot_types,
    validate_requested_modules,
)
from server.services.run_analysis.analysis.options import (
    build_evolution_history_key,
    build_evolution_history_label,
    build_evolution_options_signature,
    get_evolution_options,
    normalize_evolution_options_for_signature,
)
from server.services.run_analysis.analysis.storage import (
    get_source_dataset_file_id,
    save_generated_files,
)


async def generate_saes_metrics_csv(
    *,
    analysis,
    metrics: list[str],
    run_key: str,
) -> tuple[bytes, str]:
    """
    Description:
        Generate the SAES metrics configuration CSV and persist it.

    Args:
        analysis:
            Analysis document.

        metrics (list[str]):
            Metric names detected in the analysis.

        run_key (str):
            Current run key.

    Returns:
        tuple[bytes, str]:
            Metrics CSV bytes and stored file id.
    """

    metrics_direction = resolve_metrics_direction(
        metrics=metrics,
        frontend_config=getattr(analysis, "metrics_direction", {}) or {},
    )

    metrics_csv = generate_metrics_csv(metrics_direction)
    metrics_csv_id = await save_file(
        f"{analysis.id}_metrics_{run_key}.csv",
        metrics_csv,
    )

    analysis.metrics_config_file_id = metrics_csv_id
    analysis.metrics_direction = metrics_direction
    await analysis.save()

    return metrics_csv, metrics_csv_id


async def run_saes_plots(
    *,
    analysis,
    saes_dataset: bytes,
    metrics_csv: bytes,
    metrics: list[str],
    instances: list[str],
    export_formats: list[str],
    run_key: str,
    selected_plot_types: list[str] | None,
) -> dict[str, Any]:
    """
    Description:
        Generate SAES plots for the requested metrics, instances and plot types.

    Args:
        analysis:
            Analysis document.

        saes_dataset (bytes):
            Dataset converted to SAES CSV format.

        metrics_csv (bytes):
            SAES metrics configuration CSV.

        metrics (list[str]):
            Metric names to plot.

        instances (list[str]):
            Instance names to plot.

        export_formats (list[str]):
            Export formats to generate.

        run_key (str):
            Current run key.

        selected_plot_types (list[str] | None):
            Requested SAES plot types.

    Returns:
        dict[str, Any]:
            Saved SAES plot ids and optional warnings.
    """

    plots: dict[str, str] = {}
    warnings: list[str] = []

    requested_plot_types = normalize_requested_plot_types(selected_plot_types)

    for metric in metrics:
        if "critical_distance" in requested_plot_types:
            try:
                output = plot_cd_saes(
                    saes_dataset,
                    metrics_csv,
                    metric,
                    export_formats=export_formats,
                )
                plots.update(
                    await save_generated_files(
                        analysis_id=str(analysis.id),
                        run_key=run_key,
                        files=output["files"],
                    )
                )
            except Exception as error:
                warnings.append(f"critical_distance/{metric}: {error}")

        instance_plot_types = sorted(requested_plot_types - {"critical_distance"})

        for instance in instances if instance_plot_types else []:
            try:
                output = plots_saes(
                    saes_dataset,
                    metrics_csv,
                    metric,
                    instance,
                    export_formats=export_formats,
                    selected_plot_types=instance_plot_types,
                )
                plots.update(
                    await save_generated_files(
                        analysis_id=str(analysis.id),
                        run_key=run_key,
                        files=output["files"],
                    )
                )
            except Exception as error:
                warnings.append(f"{instance}/{metric}: {error}")

    if not plots:
        raise ValueError(
            "SAES did not generate any plot files for the selected dataset. "
            "Check CSV consistency and ensure each selected metric/instance "
            "has valid data for all selected algorithms and runs."
        )

    result: dict[str, Any] = {
        "saes_plots": plots,
        "generated_plot_types": sorted(requested_plot_types),
    }

    if warnings:
        result["saes_plot_warnings"] = warnings

    return result


async def run_saes_reports(
    *,
    analysis,
    saes_dataset: bytes,
    metrics_csv: bytes,
    metrics: list[str],
    run_key: str,
) -> dict[str, Any]:
    """
    Description:
        Generate SAES statistical report files.

    Args:
        analysis:
            Analysis document.

        saes_dataset (bytes):
            Dataset converted to SAES CSV format.

        metrics_csv (bytes):
            SAES metrics configuration CSV.

        metrics (list[str]):
            Metric names to report.

        run_key (str):
            Current run key.

    Returns:
        dict[str, Any]:
            Saved SAES report ids and optional warnings.
    """

    output = reports_saes(saes_dataset, metrics_csv, metrics)

    report_files = await save_generated_files(
        analysis_id=str(analysis.id),
        run_key=run_key,
        files=output["files"],
    )

    if not report_files:
        raise ValueError(
            "SAES did not generate any report files for the selected dataset."
        )

    result: dict[str, Any] = {"saes_reports": report_files}
    warnings = output.get("warnings") or output.get("saes_report_warnings") or []

    if warnings:
        result["saes_report_warnings"] = warnings

    return result


async def run_notebook(
    *,
    analysis,
    saes_dataset: bytes,
    metrics_csv: bytes,
    run_key: str,
) -> dict[str, Any]:
    """
    Description:
        Generate and persist the analysis notebook.

    Args:
        analysis:
            Analysis document.

        saes_dataset (bytes):
            Dataset converted to SAES CSV format.

        metrics_csv (bytes):
            SAES metrics configuration CSV.

        run_key (str):
            Current run key.

    Returns:
        dict[str, Any]:
            Saved notebook file id keyed by notebook filename.
    """

    notebook_bytes = build_analysis_notebook(
        analysis=analysis,
        dataset_bytes=saes_dataset,
        metrics_bytes=metrics_csv,
    )

    notebook_filename = f"{analysis.name}_{run_key}_notebook.ipynb"
    notebook_file_id = await save_file(
        f"{analysis.id}_{run_key}_{notebook_filename}",
        notebook_bytes,
    )

    return {
        "notebooks": {
            notebook_filename: notebook_file_id,
        }
    }


def resolve_evolution_files(evolution_output: dict[str, Any]) -> dict[str, bytes]:
    """
    Description:
        Normalize evolution plot generator outputs into filename/bytes pairs.

        The evolution plot generator may return file bytes directly, bytearrays,
        paths as strings or Path objects. This function converts all supported
        variants into a single dictionary of bytes.

    Args:
        evolution_output (dict[str, Any]):
            Raw output returned by the evolution plot generator.

    Returns:
        dict[str, bytes]:
            Generated files keyed by filename.
    """

    raw_files = evolution_output.get("files") or {}

    if not isinstance(raw_files, dict):
        raise ValueError("Evolution plot output must contain a files dictionary")

    files: dict[str, bytes] = {}

    for filename, value in raw_files.items():
        match value:
            case bytes():
                files[str(filename)] = value

            case bytearray():
                files[str(filename)] = bytes(value)

            case str():
                path = Path(value)

                if path.is_file():
                    files[path.name] = path.read_bytes()

            case Path():
                if value.is_file():
                    files[value.name] = value.read_bytes()

    return files


async def run_evolution_plots(
    *,
    analysis,
    dataset: bytes,
    export_formats: list[str],
    run_key: str,
) -> dict[str, Any]:
    """
    Description:
        Generate, persist and version evolution convergence plots.

    Args:
        analysis:
            Analysis document.

        dataset (bytes):
            Source dataset bytes.

        export_formats (list[str]):
            Export formats to generate.

        run_key (str):
            Current run key.

    Returns:
        dict[str, Any]:
            Saved evolution plot ids, metadata, signature and plot history set.
    """

    options = get_evolution_options(analysis)
    rows, capabilities = parse_dataset(dataset)

    if not capabilities.get("evolution_plots", False):
        raise ValueError(
            "Evolution plots are not available for this dataset. "
            "The CSV must contain Algorithm, MetricValue/Fitness, "
            "and at least one X column such as Generation, Time, "
            "Evaluations or Iteration."
        )

    with tempfile.TemporaryDirectory(prefix="evolution-plots-") as output_dir:
        output = generate_evolution_plots(
            rows,
            output_dir=output_dir,
            export_formats=export_formats,
            selected_algorithms=options["selected_algorithms"],
            selected_metrics=options["selected_metrics"],
            selected_instances=options["selected_instances"],
            title=options["title"],
            x_columns=options["x_columns"],
            x_label=options["x_label"],
            y_label=options["y_label"],
            x_labels_by_column=options["x_labels_by_column"],
            y_labels_by_metric=options["y_labels_by_metric"],
            show_grid=options["show_grid"],
            show_min_max=options["show_min_max"],
            show_std=options["show_std"],
            show_average=options["show_average"],
            show_median=options["show_median"],
            group_by_instance=options["group_by_instance"],
            group_by_metric=options["group_by_metric"],
        )

    files = resolve_evolution_files(output)

    signature = build_evolution_options_signature(options)
    history_key = build_evolution_history_key(options)
    generated_at = datetime.now(timezone.utc).isoformat()

    evolution_files = await save_generated_files(
        analysis_id=str(analysis.id),
        run_key=run_key,
        namespace=f"evolution_{history_key}",
        files=files,
    )

    if not evolution_files:
        raise ValueError("Evolution plot generation did not produce any output files.")

    evolution_metadata = {
        **dict(output.get("metadata", {}) or {}),
        "x_label": options["x_label"],
        "y_label": options["y_label"],
        "x_labels_by_column": options["x_labels_by_column"],
        "y_labels_by_metric": options["y_labels_by_metric"],
        "title": options["title"],
        "show_grid": options["show_grid"],
        "show_min_max": options["show_min_max"],
        "show_std": options["show_std"],
        "show_average": options["show_average"],
        "show_median": options["show_median"],
        "group_by_instance": options["group_by_instance"],
        "group_by_metric": options["group_by_metric"],
    }

    plot_set = {
        "signature": signature,
        "history_key": history_key,
        "label": build_evolution_history_label(options),
        "created_at": generated_at,
        "updated_at": generated_at,
        "options": normalize_evolution_options_for_signature(options),
        "evolution_plots": evolution_files,
        "evolution_metadata": evolution_metadata,
    }

    result: dict[str, Any] = {
        "evolution_plots": evolution_files,
        "evolution_metadata": evolution_metadata,
        "evolution_options_signature": signature,
        "evolution_plot_sets": {
            history_key: plot_set,
        },
    }

    warnings = output.get("warnings") or output.get("evolution_plot_warnings") or []

    if warnings:
        result["evolution_plot_warnings"] = warnings

    return result


def merge_outputs(
    *,
    analysis,
    run_key: str,
    run_results: dict[str, Any],
) -> dict[str, Any]:
    """
    Description:
        Merge newly generated run outputs with existing analysis outputs.

        Evolution plot sets are merged instead of replaced so previous
        evolution histories remain available.

    Args:
        analysis:
            Analysis document.

        run_key (str):
            Current run key.

        run_results (dict[str, Any]):
            Outputs generated during the current pipeline execution.

    Returns:
        dict[str, Any]:
            Updated analysis outputs dictionary.
    """

    outputs = dict(analysis.outputs or {})
    analysis_runs = dict(outputs.get("analysis_runs") or {})

    previous_run_outputs = dict(analysis_runs.get(run_key) or {})

    previous_plot_sets = dict(previous_run_outputs.get("evolution_plot_sets") or {})
    new_plot_sets = run_results.get("evolution_plot_sets")

    if isinstance(new_plot_sets, dict):
        previous_plot_sets.update(new_plot_sets)
        run_results = {
            **run_results,
            "evolution_plot_sets": previous_plot_sets,
        }

    merged_run_outputs = {
        **previous_run_outputs,
        **run_results,
    }

    analysis_runs[run_key] = merged_run_outputs
    outputs["analysis_runs"] = analysis_runs

    for category in OUTPUT_CATEGORIES:
        if category in merged_run_outputs:
            outputs[category] = merged_run_outputs[category]

    return outputs


async def prepare_saes_context(
    *,
    analysis,
    dataset: bytes,
    run_key: str,
) -> tuple[bytes, bytes, str, list[str], list[str]]:
    """
    Description:
        Prepare all inputs required by SAES modules.

    Args:
        analysis:
            Analysis document.

        dataset (bytes):
            Source dataset bytes.

        run_key (str):
            Current run key.

    Returns:
        tuple[bytes, bytes, str, list[str], list[str]]:
            SAES dataset bytes, metrics CSV bytes, metrics config file id,
            metric names and instance names.
    """

    metrics = get_metrics(analysis)
    instances = get_instances(analysis)

    if not metrics:
        raise ValueError("Analysis has no detected metrics")

    if not instances:
        raise ValueError("Analysis has no detected instances")

    saes_dataset = export_saes_dataset(dataset)

    metrics_csv, metrics_csv_id = await generate_saes_metrics_csv(
        analysis=analysis,
        metrics=metrics,
        run_key=run_key,
    )

    return saes_dataset, metrics_csv, metrics_csv_id, metrics, instances


async def run_analysis_pipeline(
    analysis,
    modules: list[str],
    selected_algorithms: list[str] | None = None,
    selected_plot_types: list[str] | None = None,
) -> dict[str, Any]:
    """
    Description:
        Run the selected analysis modules and persist generated outputs.

    Args:
        analysis:
            Analysis document.

        modules (list[str]):
            Requested modules.

        selected_algorithms (list[str] | None):
            Optional selected algorithms. When provided, a filtered dataset is
            created or reused before generating outputs.

        selected_plot_types (list[str] | None):
            Optional selected SAES plot types.

    Returns:
        dict[str, Any]:
            Outputs stored for the current run key.
    """

    normalized_modules = normalize_modules(modules)
    validate_requested_modules(analysis, normalized_modules)

    run_algorithms = (
        [value.strip() for value in selected_algorithms if value.strip()]
        if selected_algorithms is not None
        else list(getattr(analysis, "algorithms", []) or [])
    )

    run_key = build_algorithm_run_key(
        selected_algorithms=run_algorithms,
        all_algorithms=list(getattr(analysis, "algorithms", []) or []),
    )

    source_dataset_file_id = await get_source_dataset_file_id(
        analysis=analysis,
        run_key=run_key,
        selected_algorithms=selected_algorithms,
        run_algorithms=run_algorithms,
    )

    if not source_dataset_file_id:
        raise ValueError("Dataset file not found")

    dataset = await get_file(source_dataset_file_id)

    if not dataset:
        raise ValueError("Dataset is empty")

    export_formats = normalize_export_formats(analysis)

    run_results: dict[str, Any] = {
        "selected_algorithms": run_algorithms,
        "modules": normalized_modules,
    }

    requests_saes = any(module in SAES_MODULES for module in normalized_modules)

    saes_dataset: bytes | None = None
    metrics_csv: bytes | None = None
    metrics: list[str] = []
    instances: list[str] = []

    if requests_saes:
        (
            saes_dataset,
            metrics_csv,
            metrics_csv_id,
            metrics,
            instances,
        ) = await prepare_saes_context(
            analysis=analysis,
            dataset=dataset,
            run_key=run_key,
        )
        run_results["metrics_config_file_id"] = metrics_csv_id

    if "saes_plots" in normalized_modules:
        if saes_dataset is None or metrics_csv is None:
            raise ValueError("SAES dataset or metrics configuration is missing")

        run_results.update(
            await run_saes_plots(
                analysis=analysis,
                saes_dataset=saes_dataset,
                metrics_csv=metrics_csv,
                metrics=metrics,
                instances=instances,
                export_formats=export_formats,
                run_key=run_key,
                selected_plot_types=selected_plot_types,
            )
        )

    if "saes_reports" in normalized_modules:
        if saes_dataset is None or metrics_csv is None:
            raise ValueError("SAES dataset or metrics configuration is missing")

        run_results.update(
            await run_saes_reports(
                analysis=analysis,
                saes_dataset=saes_dataset,
                metrics_csv=metrics_csv,
                metrics=metrics,
                run_key=run_key,
            )
        )

    if "notebooks" in normalized_modules:
        if saes_dataset is None or metrics_csv is None:
            raise ValueError("SAES dataset or metrics configuration is missing")

        run_results.update(
            await run_notebook(
                analysis=analysis,
                saes_dataset=saes_dataset,
                metrics_csv=metrics_csv,
                run_key=run_key,
            )
        )

    if "evolution_plots" in normalized_modules:
        run_results.update(
            await run_evolution_plots(
                analysis=analysis,
                dataset=dataset,
                export_formats=export_formats,
                run_key=run_key,
            )
        )

    analysis.outputs = merge_outputs(
        analysis=analysis,
        run_key=run_key,
        run_results=run_results,
    )
    analysis.enabled_modules = normalized_modules
    analysis.selected_algorithms_last_run = run_algorithms
    analysis.current_run_key = run_key

    if "evolution_metadata" in run_results:
        analysis.evolution_metadata = run_results["evolution_metadata"]

    await analysis.save()

    return dict(analysis.outputs["analysis_runs"][run_key])
