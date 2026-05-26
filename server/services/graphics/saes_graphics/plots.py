from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Any, Final

import pandas as pd
from SAES.plots.boxplot import Boxplot
from SAES.plots.cdplot import CDplot
from SAES.plots.histoplot import HistoPlot
from SAES.plots.violin import Violin

ALLOWED_EXPORT_FORMATS: Final = {"png", "eps", "svg", "jpg", "jpeg"}
ALLOWED_PLOT_TYPES: Final = {"boxplot", "violin", "histogram", "critical_distance"}
DEFAULT_EXPORT_FORMATS: Final = ["png"]
DEFAULT_INSTANCE_PLOT_TYPES: Final = ["boxplot", "violin", "histogram"]


def _normalize_export_format(export_format: str) -> str:
    """
    Description:
        Normalize and validate a plot export format.

    Args:
        export_format (str): Requested export format.

    Returns:
        str: Lowercase export format accepted by the renderer.
    """

    normalized_format = export_format.strip().lower()

    if normalized_format not in ALLOWED_EXPORT_FORMATS:
        raise ValueError(
            f"Unsupported export format: {export_format}. "
            f"Allowed formats: {', '.join(sorted(ALLOWED_EXPORT_FORMATS))}"
        )

    return normalized_format


def _normalize_export_formats(export_formats: list[str] | None) -> list[str]:
    """
    Description:
        Normalize and validate all requested plot export formats.

    Args:
        export_formats (list[str] | None): Requested export formats.

    Returns:
        list[str]: Normalized export formats.
    """

    return [
        _normalize_export_format(export_format)
        for export_format in (export_formats or DEFAULT_EXPORT_FORMATS)
    ]


def _read_saes_inputs(
    dataset_bytes: bytes,
    metrics_bytes: bytes,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Description:
        Read SAES dataset and metrics CSV bytes into pandas DataFrames.

    Args:
        dataset_bytes (bytes): Dataset contents in CSV form.
        metrics_bytes (bytes): Metrics configuration CSV contents.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Dataset and metrics DataFrames.
    """

    data_df = pd.read_csv(io.BytesIO(dataset_bytes))
    metrics_df = pd.read_csv(io.BytesIO(metrics_bytes))

    return data_df, metrics_df


def _validate_common_inputs(
    dataset_bytes: bytes,
    metrics_bytes: bytes,
    metric: str,
) -> None:
    """
    Description:
        Validate common inputs required by SAES plot generation.

    Args:
        dataset_bytes (bytes): Dataset contents in CSV form.
        metrics_bytes (bytes): Metrics configuration CSV contents.
        metric (str): Metric to plot.

    Returns:
        None
    """

    if not dataset_bytes:
        raise ValueError("Dataset bytes are empty")

    if not metrics_bytes:
        raise ValueError("Metrics bytes are empty")

    if not metric or not metric.strip():
        raise ValueError("Metric cannot be empty")


def _read_existing_files(tmp_path: Path, file_names: list[str]) -> dict[str, bytes]:
    """
    Description:
        Read generated files from a temporary directory when they exist.

    Args:
        tmp_path (Path): Temporary directory path.
        file_names (list[str]): Expected generated file names.

    Returns:
        dict[str, bytes]: Existing generated files keyed by filename.
    """

    results: dict[str, bytes] = {}

    for file_name in file_names:
        file_path = tmp_path / file_name

        if file_path.exists():
            results[file_name] = file_path.read_bytes()

    return results


def plots_saes(
    dataset_bytes: bytes,
    metrics_bytes: bytes,
    metric: str,
    instance: str,
    export_formats: list[str] | None = None,
    selected_plot_types: list[str] | None = None,
) -> dict[str, Any]:
    """
    Description:
        Generate SAES plots for a metric/instance pair.

    Args:
        dataset_bytes (bytes): Dataset contents in CSV form.
        metrics_bytes (bytes): Metrics configuration CSV contents.
        metric (str): Metric to plot.
        instance (str): Instance to plot.
        export_formats (list[str] | None): Requested export formats.
        selected_plot_types (list[str] | None): Plot types to generate.

    Returns:
        dict[str, Any]: Generated plot files keyed by filename.
    """

    _validate_common_inputs(dataset_bytes, metrics_bytes, metric)

    if not instance or not instance.strip():
        raise ValueError("Instance cannot be empty")

    normalized_formats = _normalize_export_formats(export_formats)
    requested_plot_types = set(selected_plot_types or DEFAULT_INSTANCE_PLOT_TYPES)

    invalid_plot_types = requested_plot_types - ALLOWED_PLOT_TYPES
    if invalid_plot_types:
        raise ValueError(
            f"Unsupported plot types: {', '.join(sorted(invalid_plot_types))}"
        )

    data_df, metrics_df = _read_saes_inputs(dataset_bytes, metrics_bytes)

    results: dict[str, bytes] = {}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        boxplot = (
            Boxplot(data_df, metrics_df, metric)
            if "boxplot" in requested_plot_types
            else None
        )
        violin = (
            Violin(data_df, metrics_df, metric)
            if "violin" in requested_plot_types
            else None
        )
        histoplot = (
            HistoPlot(data_df, metrics_df, metric)
            if "histogram" in requested_plot_types
            else None
        )

        for normalized_format in normalized_formats:
            boxplot_name = f"{metric}_{instance}_boxplot.{normalized_format}"
            violin_name = f"{metric}_{instance}_violin.{normalized_format}"
            histoplot_name = f"{metric}_{instance}_histogram.{normalized_format}"

            if boxplot is not None:
                boxplot.save_instance(
                    instance=instance,
                    output_path=str(tmp_path),
                    file_name=boxplot_name,
                )

            if violin is not None:
                violin.save_instance(
                    instance=instance,
                    output_path=str(tmp_path),
                    file_name=violin_name,
                )

            if histoplot is not None:
                histoplot.save_instance(
                    instance=instance,
                    output_path=str(tmp_path),
                    file_name=histoplot_name,
                )

            results.update(
                _read_existing_files(
                    tmp_path,
                    [boxplot_name, violin_name, histoplot_name],
                )
            )

    return {"files": results}


def plot_cd_saes(
    dataset_bytes: bytes,
    metrics_bytes: bytes,
    metric: str,
    export_formats: list[str] | None = None,
) -> dict[str, Any]:
    """
    Description:
        Generate the critical-distance plot for a metric.

    Args:
        dataset_bytes (bytes): Dataset contents in CSV form.
        metrics_bytes (bytes): Metrics configuration CSV contents.
        metric (str): Metric to plot.
        export_formats (list[str] | None): Requested export formats.

    Returns:
        dict[str, Any]: Generated plot files keyed by filename.
    """

    _validate_common_inputs(dataset_bytes, metrics_bytes, metric)

    normalized_formats = _normalize_export_formats(export_formats)
    data_df, metrics_df = _read_saes_inputs(dataset_bytes, metrics_bytes)

    results: dict[str, bytes] = {}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cdplot = CDplot(data_df, metrics_df, metric)

        for normalized_format in normalized_formats:
            cdplot_name = f"{metric}_critical_distance.{normalized_format}"

            cdplot.save(
                output_path=str(tmp_path),
                file_name=cdplot_name,
            )

            results.update(_read_existing_files(tmp_path, [cdplot_name]))

    return {"files": results}
