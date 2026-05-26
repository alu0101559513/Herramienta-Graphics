from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

ALLOWED_EXPORT_FORMATS: Final = {"png", "svg", "eps", "jpg", "jpeg"}

GENERATION_ALIASES: Final = {
    "generation",
    "generations",
    "generacion",
    "generaciones",
    "iteration",
    "iterations",
    "iteracion",
    "iteraciones",
}

TIME_ALIASES: Final = {
    "time",
    "times",
    "tiempo",
}

EVOLUTION_X_ALIASES: Final = {
    "evaluation",
    "evaluations",
    "evaluacion",
    "evaluaciones",
    "eval",
    "evals",
    "functionevaluation",
    "functionevaluations",
    "function_evaluation",
    "function_evaluations",
}

RUN_COLUMNS: Final = ("evolution_run", "executionid", "run", "seed")
SORT_COLUMNS: Final = ["algorithm", "instance", "metric", "run", "x"]
GROUP_COLUMNS: Final = ["algorithm", "instance", "metric", "run"]
SUMMARY_GROUP_COLUMNS: Final = ["algorithm", "instance", "metric", "x"]


@dataclass(frozen=True)
class EvolutionPlotConfig:
    """
    Description:
        Configuration used to generate evolution convergence plots.

    Args:
        output_dir (str | Path): Directory where plot files are written.
        export_formats (Iterable[str] | None): Requested export formats.
        selected_algorithms (list[str] | None): Algorithms to include.
        selected_metrics (list[str] | None): Metrics to include.
        selected_instances (list[str] | None): Instances to include.
        x_columns (Iterable[str] | None): X columns to plot.
        x_axis (str | None): X axis alias requested by the user.
        direction (str | Mapping[str, str] | None): Optimization direction.
        title (str | None): Plot title template.
        x_label (str | None): X axis label.
        y_label (str | None): Y axis label.
        x_labels_by_column (Mapping[str, str] | None): Labels by X column.
        y_labels_by_metric (Mapping[str, str] | None): Labels by metric.
        show_grid (bool): Whether to show grid lines.
        show_min_max (bool): Whether to show min/max bands.
        show_std (bool): Whether to show standard deviation bands.
        show_average (bool): Whether to show average line.
        show_median (bool): Whether to show median line.
        group_by_instance (bool): Whether to generate one plot per instance.
        group_by_metric (bool): Whether to generate one plot per metric.
        output_suffix (str | None): Optional suffix for output filenames.
    """

    output_dir: str | Path
    export_formats: Iterable[str] | None = None
    selected_algorithms: list[str] | None = None
    selected_metrics: list[str] | None = None
    selected_instances: list[str] | None = None
    x_columns: Iterable[str] | None = None
    x_axis: str | None = None
    direction: str | Mapping[str, str] | None = None
    title: str | None = None
    x_label: str | None = None
    y_label: str | None = None
    x_labels_by_column: Mapping[str, str] | None = None
    y_labels_by_metric: Mapping[str, str] | None = None
    show_grid: bool = True
    show_min_max: bool = True
    show_std: bool = True
    show_average: bool = True
    show_median: bool = True
    group_by_instance: bool = True
    group_by_metric: bool = True
    output_suffix: str | None = None


def normalize_column_key(value: str) -> str:
    """
    Description:
        Normalize a column name for alias matching.

    Args:
        value (str): Column name or alias.

    Returns:
        str: Lowercase normalized key without accents or separators.
    """

    normalized = unicodedata.normalize("NFD", str(value or "").strip().lower())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^a-z0-9]", "", normalized)


NORMALIZED_GENERATION_ALIASES: Final = {
    normalize_column_key(value) for value in GENERATION_ALIASES
}
NORMALIZED_TIME_ALIASES: Final = {normalize_column_key(value) for value in TIME_ALIASES}
NORMALIZED_EVOLUTION_X_ALIASES: Final = {
    normalize_column_key(value) for value in EVOLUTION_X_ALIASES
}


def slugify(value: str) -> str:
    """
    Description:
        Convert a value into a safe filename fragment.

    Args:
        value (str): Value to slugify.

    Returns:
        str: Safe slug value.
    """

    value = str(value or "").strip().lower()
    value = re.sub(r"[^\w\s-]", "_", value)
    value = re.sub(r"[\s/\\]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "unnamed"


def normalize_metric_name(value: str | None) -> str:
    """
    Description:
        Normalize a metric name and provide a default when empty.

    Args:
        value (str | None): Metric name.

    Returns:
        str: Normalized metric name.
    """

    cleaned = str(value or "").strip()
    return cleaned or "fitness"


def normalize_unique_strings(values: Iterable[str] | None) -> list[str]:
    """
    Description:
        Normalize a list of strings, removing empty values and duplicates.

    Args:
        values (Iterable[str] | None): Values to normalize.

    Returns:
        list[str]: Unique non-empty strings preserving input order.
    """

    if not values:
        return []

    return list(
        dict.fromkeys(
            str(value).strip()
            for value in values
            if isinstance(value, str) and str(value).strip()
        )
    )


def infer_direction(metric_name: str, direction: str | None = None) -> str:
    """
    Description:
        Infer whether a metric should be maximized or minimized.

    Args:
        metric_name (str): Metric name.
        direction (str | None): Explicit direction value.

    Returns:
        str: Either 'maximize' or 'minimize'.
    """

    if direction:
        cleaned = direction.lower().strip()

        if cleaned in {"maximize", "max", "maximizar"}:
            return "maximize"

        if cleaned in {"minimize", "min", "minimizar"}:
            return "minimize"

    metric_lower = metric_name.lower()

    if any(
        token in metric_lower
        for token in ("accuracy", "score", "reward", "hypervolume", "hv", "nhv")
    ):
        return "maximize"

    return "minimize"


def resolve_metric_direction(
    metric: str,
    direction: str | Mapping[str, str] | None = None,
) -> str:
    """
    Description:
        Resolve the optimization direction for a metric.

    Args:
        metric (str): Metric name.
        direction (str | Mapping[str, str] | None): Direction or direction mapping.

    Returns:
        str: Either 'maximize' or 'minimize'.
    """

    if isinstance(direction, Mapping):
        return infer_direction(metric, direction.get(metric))

    return infer_direction(metric, direction)


def resolve_export_formats(export_formats: Iterable[str] | None) -> list[str]:
    """
    Description:
        Resolve valid export formats, ignoring unsupported values and PDF.

    Args:
        export_formats (Iterable[str] | None): Requested export formats.

    Returns:
        list[str]: Valid export formats.
    """

    resolved: list[str] = []

    for value in export_formats or ["png"]:
        if not isinstance(value, str):
            continue

        cleaned = value.lower().strip()

        if (
            cleaned != "pdf"
            and cleaned in ALLOWED_EXPORT_FORMATS
            and cleaned not in resolved
        ):
            resolved.append(cleaned)

    return resolved or ["png"]


def resolve_row_x_value(row: dict[str, Any], x_column: str) -> Any | None:
    """
    Description:
        Resolve the X value for a row based on the requested X column.

    Args:
        row (dict[str, Any]): Evolution row.
        x_column (str): Requested X column.

    Returns:
        Any | None: Resolved X value.
    """

    if x_column in row and row.get(x_column) is not None:
        return row.get(x_column)

    normalized = normalize_column_key(x_column)

    if normalized in NORMALIZED_GENERATION_ALIASES:
        return (
            row.get("generation")
            if row.get("generation") is not None
            else row.get("evolution_x")
        )

    if normalized in NORMALIZED_TIME_ALIASES:
        return (
            row.get("time") if row.get("time") is not None else row.get("evolution_x")
        )

    if normalized in NORMALIZED_EVOLUTION_X_ALIASES:
        return row.get("evolution_x")

    return row.get("evolution_x")


def resolve_run_value(row: dict[str, Any]) -> str:
    """
    Description:
        Resolve the run identifier for an evolution row.

    Args:
        row (dict[str, Any]): Evolution row.

    Returns:
        str: Run identifier.
    """

    for column in RUN_COLUMNS:
        value = row.get(column)

        if value is not None and str(value).strip():
            return str(value).strip()

    return "single_run"


def detect_available_x_columns(rows: list[dict[str, Any]]) -> list[str]:
    """
    Description:
        Detect available X columns from evolution rows.

    Args:
        rows (list[dict[str, Any]]): Evolution rows.

    Returns:
        list[str]: Available X column labels.
    """

    candidates = [
        ("Generation", "generation"),
        ("Time", "time"),
        ("EvolutionX", "evolution_x"),
    ]

    detected = [
        label
        for label, key in candidates
        if any(row.get(key) is not None for row in rows)
    ]

    if "EvolutionX" in detected and len(detected) > 1:
        detected.remove("EvolutionX")

    return detected or ["EvolutionX"]


def resolve_x_axis_alias(x_axis: str) -> str | None:
    """
    Description:
        Resolve a user-provided X axis alias to a supported X column label.

    Args:
        x_axis (str): X axis alias.

    Returns:
        str | None: Resolved X column label.
    """

    normalized = normalize_column_key(x_axis)

    if normalized in NORMALIZED_GENERATION_ALIASES:
        return "Generation"

    if normalized in NORMALIZED_TIME_ALIASES:
        return "Time"

    if normalized in NORMALIZED_EVOLUTION_X_ALIASES:
        return "EvolutionX"

    return None


def resolve_x_columns(
    rows: list[dict[str, Any]],
    x_columns: Iterable[str] | None = None,
    x_axis: str | None = None,
) -> list[str]:
    """
    Description:
        Resolve the X columns that should be plotted.

    Args:
        rows (list[dict[str, Any]]): Evolution rows.
        x_columns (Iterable[str] | None): Explicit X columns.
        x_axis (str | None): X axis alias.

    Returns:
        list[str]: Resolved X columns.
    """

    resolved = normalize_unique_strings(x_columns)

    if resolved:
        return resolved

    if x_axis:
        resolved_axis = resolve_x_axis_alias(x_axis)

        if resolved_axis:
            return [resolved_axis]

    return detect_available_x_columns(rows)


def resolve_x_label(
    *,
    x_column: str,
    x_label: str | None,
    x_labels_by_column: Mapping[str, str] | None = None,
) -> str:
    """
    Description:
        Resolve the X axis label.

    Args:
        x_column (str): X column name.
        x_label (str | None): Default X label.
        x_labels_by_column (Mapping[str, str] | None): X labels by column.

    Returns:
        str: Resolved X axis label.
    """

    label_by_column = str((x_labels_by_column or {}).get(x_column, "")).strip()

    if label_by_column:
        return label_by_column

    cleaned = str(x_label or "").strip()
    return cleaned or x_column


def resolve_y_label(
    *,
    metric: str,
    y_label: str | None,
    y_labels_by_metric: Mapping[str, str] | None = None,
) -> str:
    """
    Description:
        Resolve the Y axis label.

    Args:
        metric (str): Metric name.
        y_label (str | None): Default Y label.
        y_labels_by_metric (Mapping[str, str] | None): Y labels by metric.

    Returns:
        str: Resolved Y axis label.
    """

    metric_label = str((y_labels_by_metric or {}).get(metric, "")).strip()

    if metric_label:
        return metric_label

    cleaned = str(y_label or "").strip()

    if cleaned and cleaned.lower() != "fitness":
        return cleaned

    return metric


def resolve_plot_title(
    *,
    title: str | None,
    metric: str,
    instance: str | None,
    x_column: str,
) -> str:
    """
    Description:
        Resolve a convergence plot title.

    Args:
        title (str | None): Optional title template.
        metric (str): Metric name.
        instance (str | None): Instance name.
        x_column (str): X column name.

    Returns:
        str: Resolved plot title.
    """

    resolved_instance = instance or "all_instances"
    cleaned = str(title or "").strip()

    if cleaned:
        return (
            cleaned.replace("{metric}", metric)
            .replace("{instance}", resolved_instance)
            .replace("{x_column}", x_column)
        )

    base = f"Curva de Convergencia - {metric} - {x_column}"

    if resolved_instance != "all_instances":
        base += f" - {resolved_instance}"

    return base


def rows_to_evolution_dataframe(
    rows: list[dict[str, Any]],
    *,
    x_column: str,
) -> pd.DataFrame:
    """
    Description:
        Convert evolution rows into a normalized pandas DataFrame.

    Args:
        rows (list[dict[str, Any]]): Evolution rows.
        x_column (str): X column to resolve.

    Returns:
        pd.DataFrame: Normalized evolution DataFrame.
    """

    records = []

    for row in rows:
        y_value = row.get("evolution_y")

        if y_value is None:
            continue

        x_value = resolve_row_x_value(row, x_column)

        if x_value is None:
            continue

        try:
            records.append(
                {
                    "algorithm": str(row.get("algorithm", "")).strip(),
                    "instance": str(row.get("instance") or "all_instances").strip(),
                    "metric": normalize_metric_name(row.get("metricname")),
                    "run": resolve_run_value(row),
                    "x_column": x_column,
                    "x": float(x_value),
                    "value": float(y_value),
                }
            )
        except (TypeError, ValueError):
            continue

    df = pd.DataFrame.from_records(records)

    if df.empty:
        msg = (
            f"No evolution data available to generate convergence plots "
            f"for X column '{x_column}'"
        )
        raise ValueError(msg)

    df = df[df["algorithm"] != ""]

    if df.empty:
        raise ValueError("Evolution data does not contain valid algorithms")

    return df.sort_values(SORT_COLUMNS)


def apply_best_so_far(df: pd.DataFrame, direction: str) -> pd.DataFrame:
    """
    Description:
        Compute the best-so-far value per algorithm, instance, metric and run.

    Args:
        df (pd.DataFrame): Evolution DataFrame.
        direction (str): Optimization direction.

    Returns:
        pd.DataFrame: DataFrame with best_so_far column.
    """

    working = df.sort_values(SORT_COLUMNS).copy()
    grouped = working.groupby(GROUP_COLUMNS)["value"]

    working["best_so_far"] = (
        grouped.cummax() if direction == "maximize" else grouped.cummin()
    )

    return working


def summarize_convergence(df: pd.DataFrame) -> pd.DataFrame:
    """
    Description:
        Summarize convergence values by algorithm, instance, metric and X value.

    Args:
        df (pd.DataFrame): Evolution DataFrame with best_so_far values.

    Returns:
        pd.DataFrame: Summary DataFrame.
    """

    summary = (
        df.groupby(SUMMARY_GROUP_COLUMNS, sort=False)["best_so_far"]
        .agg(
            mean="mean",
            median="median",
            std="std",
            min="min",
            max="max",
            count="count",
        )
        .reset_index()
    )

    summary["std"] = summary["std"].fillna(0.0)
    summary["count"] = summary["count"].astype(int)

    return summary.sort_values(["algorithm", "instance", "metric", "x"])


def add_unique_legend(ax: plt.Axes) -> None:
    """
    Description:
        Add a legend to a matplotlib axis without duplicate labels.

    Args:
        ax (plt.Axes): Matplotlib axis.

    Returns:
        None
    """

    handles, labels = ax.get_legend_handles_labels()
    unique = {}

    for handle, label in zip(handles, labels, strict=False):
        unique.setdefault(label, handle)

    if unique:
        ax.legend(
            unique.values(),
            unique.keys(),
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=True,
        )


def plot_algorithm_summary(
    ax: plt.Axes,
    algorithm_df: pd.DataFrame,
    *,
    algorithm: str,
    color: Any,
    show_min_max: bool,
    show_std: bool,
    show_average: bool,
    show_median: bool,
) -> None:
    """
    Description:
        Plot convergence summary lines and dispersion bands for one algorithm.

    Args:
        ax (plt.Axes): Matplotlib axis.
        algorithm_df (pd.DataFrame): Summary DataFrame for one algorithm.
        algorithm (str): Algorithm name.
        color (Any): Matplotlib color value.
        show_min_max (bool): Whether to show min/max bands.
        show_std (bool): Whether to show standard deviation bands.
        show_average (bool): Whether to show average line.
        show_median (bool): Whether to show median line.

    Returns:
        None
    """

    x = algorithm_df["x"].to_numpy(dtype=float)
    mean = algorithm_df["mean"].to_numpy(dtype=float)
    median = algorithm_df["median"].to_numpy(dtype=float)
    std = algorithm_df["std"].to_numpy(dtype=float)
    min_values = algorithm_df["min"].to_numpy(dtype=float)
    max_values = algorithm_df["max"].to_numpy(dtype=float)
    has_dispersion = algorithm_df["count"].max() > 1
    markevery = max(1, len(x) // 12)

    if show_min_max and has_dispersion:
        ax.fill_between(
            x,
            min_values,
            max_values,
            color=color,
            alpha=0.10,
            linewidth=0,
            label=f"{algorithm} Min/Max",
            zorder=1,
        )
        ax.plot(
            x,
            min_values,
            color=color,
            linewidth=1.2,
            linestyle=":",
            alpha=0.75,
            label=f"{algorithm} Min",
            zorder=2,
        )
        ax.plot(
            x,
            max_values,
            color=color,
            linewidth=1.2,
            linestyle=":",
            alpha=0.75,
            label=f"{algorithm} Max",
            zorder=2,
        )

    if show_std and has_dispersion:
        ax.fill_between(
            x,
            mean - std,
            mean + std,
            color=color,
            alpha=0.18,
            linewidth=0,
            label=f"{algorithm} ± Desv. Est.",
            zorder=3,
        )

    if show_average:
        ax.plot(
            x,
            mean,
            color=color,
            linewidth=3.2,
            linestyle="-",
            marker="o",
            markersize=4.8,
            markerfacecolor=color,
            markeredgecolor="white",
            markeredgewidth=0.9,
            markevery=markevery,
            label=f"{algorithm} Media",
            zorder=7,
        )

    if show_median:
        ax.plot(
            x,
            median,
            color=color,
            linewidth=2.4,
            linestyle="--",
            marker="s",
            markersize=4.2,
            markerfacecolor="white",
            markeredgecolor=color,
            markeredgewidth=1.2,
            markevery=markevery,
            label=f"{algorithm} Mediana",
            zorder=8,
        )

    if not any((show_average, show_median, show_min_max, show_std)):
        ax.plot(
            x,
            mean,
            color=color,
            linewidth=3.2,
            linestyle="-",
            marker="o",
            markersize=4.8,
            markerfacecolor=color,
            markeredgecolor="white",
            markeredgewidth=0.9,
            markevery=markevery,
            label=f"{algorithm} Media",
            zorder=7,
        )


def configure_axes(
    ax: plt.Axes,
    *,
    title: str | None,
    metric: str,
    instance: str | None,
    x_column: str,
    x_label: str | None,
    y_label: str | None,
    x_labels_by_column: Mapping[str, str] | None,
    y_labels_by_metric: Mapping[str, str] | None,
    show_grid: bool,
) -> None:
    """
    Description:
        Configure title, labels, margins and grid for a convergence plot.

    Args:
        ax (plt.Axes): Matplotlib axis.
        title (str | None): Plot title template.
        metric (str): Metric name.
        instance (str | None): Instance name.
        x_column (str): X column name.
        x_label (str | None): X axis label.
        y_label (str | None): Y axis label.
        x_labels_by_column (Mapping[str, str] | None): X labels by column.
        y_labels_by_metric (Mapping[str, str] | None): Y labels by metric.
        show_grid (bool): Whether to show grid lines.

    Returns:
        None
    """

    ax.set_title(
        resolve_plot_title(
            title=title,
            metric=metric,
            instance=instance,
            x_column=x_column,
        ),
        fontsize=15,
        fontweight="bold",
    )
    ax.set_xlabel(
        resolve_x_label(
            x_column=x_column,
            x_label=x_label,
            x_labels_by_column=x_labels_by_column,
        )
    )
    ax.set_ylabel(
        resolve_y_label(
            metric=metric,
            y_label=y_label,
            y_labels_by_metric=y_labels_by_metric,
        )
    )
    ax.set_axisbelow(True)
    ax.margins(x=0.015, y=0.06)

    if not show_grid:
        ax.grid(False)
        return

    ax.minorticks_on()
    ax.grid(True, which="major", axis="both", linestyle="-", linewidth=0.65, alpha=0.30)
    ax.grid(True, which="minor", axis="both", linestyle=":", linewidth=0.45, alpha=0.18)


def plot_convergence_summary(
    summary: pd.DataFrame,
    *,
    metric: str,
    instance: str | None,
    x_column: str,
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    x_labels_by_column: Mapping[str, str] | None = None,
    y_labels_by_metric: Mapping[str, str] | None = None,
    show_grid: bool = True,
    show_min_max: bool = True,
    show_std: bool = True,
    show_average: bool = True,
    show_median: bool = True,
) -> plt.Figure:
    """
    Description:
        Build a convergence summary figure for a metric and instance.

    Args:
        summary (pd.DataFrame): Summary DataFrame.
        metric (str): Metric to plot.
        instance (str | None): Instance to plot.
        x_column (str): X column name.
        title (str | None): Plot title template.
        x_label (str | None): X axis label.
        y_label (str | None): Y axis label.
        x_labels_by_column (Mapping[str, str] | None): X labels by column.
        y_labels_by_metric (Mapping[str, str] | None): Y labels by metric.
        show_grid (bool): Whether to show grid lines.
        show_min_max (bool): Whether to show min/max bands.
        show_std (bool): Whether to show standard deviation bands.
        show_average (bool): Whether to show average line.
        show_median (bool): Whether to show median line.

    Returns:
        plt.Figure: Generated matplotlib figure.
    """

    fig, ax = plt.subplots(figsize=(14, 7), constrained_layout=True)

    filtered = summary[summary["metric"] == metric]

    if instance and instance != "all_instances":
        filtered = filtered[filtered["instance"] == instance]

    color_pool = list(plt.cm.tab10.colors) + list(plt.cm.tab20.colors)

    for index, algorithm in enumerate(sorted(filtered["algorithm"].unique())):
        algorithm_df = filtered[filtered["algorithm"] == algorithm].sort_values("x")

        if algorithm_df.empty:
            continue

        plot_algorithm_summary(
            ax,
            algorithm_df,
            algorithm=algorithm,
            color=color_pool[index % len(color_pool)],
            show_min_max=show_min_max,
            show_std=show_std,
            show_average=show_average,
            show_median=show_median,
        )

    configure_axes(
        ax,
        title=title,
        metric=metric,
        instance=instance,
        x_column=x_column,
        x_label=x_label,
        y_label=y_label,
        x_labels_by_column=x_labels_by_column,
        y_labels_by_metric=y_labels_by_metric,
        show_grid=show_grid,
    )

    add_unique_legend(ax)

    return fig


def save_figure(
    fig: plt.Figure,
    output_dir: str | Path,
    output_stem: str,
    export_formats: Iterable[str] | None = None,
) -> dict[str, bytes]:
    """
    Description:
        Save a matplotlib figure in the requested export formats.

    Args:
        fig (plt.Figure): Matplotlib figure.
        output_dir (str | Path): Output directory.
        output_stem (str): Output filename without extension.
        export_formats (Iterable[str] | None): Requested export formats.

    Returns:
        dict[str, bytes]: Generated files keyed by filename.
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generated = {}

    for export_format in resolve_export_formats(export_formats):
        file_path = output_path / f"{output_stem}.{export_format}"
        save_kwargs = {"bbox_inches": "tight"}

        if export_format in {"png", "jpg", "jpeg"}:
            save_kwargs["dpi"] = 240

        fig.savefig(file_path, **save_kwargs)
        generated[file_path.name] = file_path.read_bytes()

    return generated


def apply_filters(
    df: pd.DataFrame,
    *,
    selected_algorithms: list[str] | None = None,
    selected_metrics: list[str] | None = None,
    selected_instances: list[str] | None = None,
) -> pd.DataFrame:
    """
    Description:
        Apply algorithm, metric and instance filters to an evolution DataFrame.

    Args:
        df (pd.DataFrame): Evolution DataFrame.
        selected_algorithms (list[str] | None): Selected algorithms.
        selected_metrics (list[str] | None): Selected metrics.
        selected_instances (list[str] | None): Selected instances.

    Returns:
        pd.DataFrame: Filtered DataFrame.
    """

    filtered = df

    if selected_algorithms:
        filtered = filtered[filtered["algorithm"].isin(selected_algorithms)]

    if selected_metrics:
        filtered = filtered[filtered["metric"].isin(selected_metrics)]

    if selected_instances:
        filtered = filtered[filtered["instance"].isin(selected_instances)]

    return filtered


def generate_evolution_plots_for_x_column(
    *,
    rows: list[dict[str, Any]],
    x_column: str,
    output_dir: str | Path,
    export_formats: Iterable[str] | None,
    selected_algorithms: list[str] | None,
    selected_metrics: list[str] | None,
    selected_instances: list[str] | None,
    direction: str | Mapping[str, str] | None,
    title: str | None,
    x_label: str | None,
    y_label: str | None,
    x_labels_by_column: Mapping[str, str] | None,
    y_labels_by_metric: Mapping[str, str] | None,
    show_grid: bool,
    show_min_max: bool,
    show_std: bool,
    show_average: bool,
    show_median: bool,
    group_by_instance: bool,
    group_by_metric: bool,
    output_suffix: str | None = None,
) -> tuple[dict[str, bytes], list[str], dict[str, Any], list[str]]:
    """
    Description:
        Generate evolution plots for a single X column.

    Args:
        rows (list[dict[str, Any]]): Evolution rows.
        x_column (str): X column to plot.
        output_dir (str | Path): Output directory.
        export_formats (Iterable[str] | None): Requested export formats.
        selected_algorithms (list[str] | None): Algorithms to include.
        selected_metrics (list[str] | None): Metrics to include.
        selected_instances (list[str] | None): Instances to include.
        direction (str | Mapping[str, str] | None): Optimization direction.
        title (str | None): Plot title template.
        x_label (str | None): X axis label.
        y_label (str | None): Y axis label.
        x_labels_by_column (Mapping[str, str] | None): X labels by column.
        y_labels_by_metric (Mapping[str, str] | None): Y labels by metric.
        show_grid (bool): Whether to show grid lines.
        show_min_max (bool): Whether to show min/max bands.
        show_std (bool): Whether to show standard deviation bands.
        show_average (bool): Whether to show average line.
        show_median (bool): Whether to show median line.
        group_by_instance (bool): Whether to generate one plot per instance.
        group_by_metric (bool): Whether to generate one plot per metric.
        output_suffix (str | None): Optional output filename suffix.

    Returns:
        tuple[dict[str, bytes], list[str], dict[str, Any], list[str]]:
            Generated files, filenames, metadata and warnings.
    """

    warnings = []
    df = rows_to_evolution_dataframe(rows, x_column=x_column)
    df = apply_filters(
        df,
        selected_algorithms=selected_algorithms,
        selected_metrics=selected_metrics,
        selected_instances=selected_instances,
    )

    if df.empty:
        msg = (
            f"No evolution rows remain after applying filters for X column '{x_column}'"
        )
        return ({}, [], {}, [msg])

    metrics = sorted(df["metric"].unique())
    metrics_to_plot = metrics if group_by_metric else metrics[:1]

    if not group_by_metric and len(metrics) > 1:
        msg = (
            "group_by_metric=False is not recommended for evolution plots "
            "with different metric scales. Only the first metric was plotted."
        )
        warnings.append(msg)

    generated_files = {}
    generated_file_names = []
    safe_suffix = slugify(output_suffix or "") if output_suffix else ""

    for metric in metrics_to_plot:
        metric_df = df[df["metric"] == metric].copy()

        if not group_by_instance:
            metric_df["instance"] = "all_instances"

        best_df = apply_best_so_far(
            metric_df,
            resolve_metric_direction(metric, direction),
        )
        summary = summarize_convergence(best_df)
        instances = (
            sorted(summary["instance"].unique())
            if group_by_instance
            else ["all_instances"]
        )

        for instance in instances:
            instance_summary = (
                summary[summary["instance"] == instance]
                if instance != "all_instances"
                else summary
            )

            if instance_summary.empty:
                continue

            fig = plot_convergence_summary(
                summary,
                metric=metric,
                instance=instance,
                x_column=x_column,
                title=title,
                x_label=x_label,
                y_label=y_label,
                x_labels_by_column=x_labels_by_column,
                y_labels_by_metric=y_labels_by_metric,
                show_grid=show_grid,
                show_min_max=show_min_max,
                show_std=show_std,
                show_average=show_average,
                show_median=show_median,
            )

            output_stem = (
                f"convergence_{slugify(metric)}_{slugify(instance)}_{slugify(x_column)}"
            )

            if safe_suffix:
                output_stem = f"{output_stem}_{safe_suffix}"

            files = save_figure(
                fig=fig,
                output_dir=output_dir,
                output_stem=output_stem,
                export_formats=export_formats,
            )

            plt.close(fig)

            generated_files.update(files)
            generated_file_names.extend(files.keys())

    run_count = df.groupby(["algorithm", "instance", "metric"])["run"].nunique().max()
    run_count = int(run_count) if pd.notna(run_count) else 0

    metadata = {
        "metrics": metrics_to_plot,
        "algorithms": sorted(df["algorithm"].unique()),
        "instances": sorted(df["instance"].unique()),
        "run_count": run_count,
        "x_min": float(df["x"].min()),
        "x_max": float(df["x"].max()),
    }

    return generated_files, generated_file_names, metadata, warnings


class EvolutionPlotGenerator:
    """
    Description:
        Orchestrates evolution convergence plot generation across X columns.

    Args:
        rows (list[dict[str, Any]]): Evolution rows.
        config (EvolutionPlotConfig): Plot generation configuration.
    """

    def __init__(
        self,
        rows: list[dict[str, Any]],
        config: EvolutionPlotConfig,
    ) -> None:
        self.rows = rows
        self.config = config

        self.generated_files: dict[str, bytes] = {}
        self.generated_file_names: list[str] = []
        self.warnings: list[str] = []
        self.metadata_by_x_column: dict[str, dict[str, Any]] = {}

        self.all_metrics: set[str] = set()
        self.all_algorithms: set[str] = set()
        self.all_instances: set[str] = set()
        self.max_run_count = 0

    def generate(self) -> dict[str, Any]:
        """
        Description:
            Generate all requested evolution plots.

        Returns:
            dict[str, Any]: Generated files, filenames, warnings and metadata.
        """

        resolved_x_columns = resolve_x_columns(
            self.rows,
            x_columns=self.config.x_columns,
            x_axis=self.config.x_axis,
        )

        for x_column in resolved_x_columns:
            self._generate_for_x_column(x_column)

        if not self.generated_files:
            msg = (
                "Evolution plot generation did not produce any output files. "
                "Check selected X columns and dataset content."
            )
            raise ValueError(msg)

        if self.max_run_count <= 1:
            msg = (
                "Only one run was detected per algorithm/instance/metric. "
                "Standard deviation and min/max bands will not represent "
                "dispersion across independent executions."
            )
            self.warnings.append(msg)

        return {
            "files": self.generated_files,
            "generated_files": self.generated_file_names,
            "warnings": list(dict.fromkeys(self.warnings)),
            "metadata": self._build_response_metadata(resolved_x_columns),
        }

    def _generate_for_x_column(self, x_column: str) -> None:
        """
        Description:
            Generate plots and collect metadata for a single X column.

        Args:
            x_column (str): X column to process.

        Returns:
            None
        """

        try:
            files, file_names, metadata, warnings = (
                generate_evolution_plots_for_x_column(
                    rows=self.rows,
                    x_column=x_column,
                    output_dir=self.config.output_dir,
                    export_formats=self.config.export_formats,
                    selected_algorithms=self.config.selected_algorithms,
                    selected_metrics=self.config.selected_metrics,
                    selected_instances=self.config.selected_instances,
                    direction=self.config.direction,
                    title=self.config.title,
                    x_label=self.config.x_label,
                    y_label=self.config.y_label,
                    x_labels_by_column=self.config.x_labels_by_column,
                    y_labels_by_metric=self.config.y_labels_by_metric,
                    show_grid=self.config.show_grid,
                    show_min_max=self.config.show_min_max,
                    show_std=self.config.show_std,
                    show_average=self.config.show_average,
                    show_median=self.config.show_median,
                    group_by_instance=self.config.group_by_instance,
                    group_by_metric=self.config.group_by_metric,
                    output_suffix=self.config.output_suffix,
                )
            )
        except ValueError as error:
            self.warnings.append(str(error))
            return

        self.warnings.extend(warnings)

        if not files:
            return

        self.generated_files.update(files)
        self.generated_file_names.extend(file_names)
        self.metadata_by_x_column[x_column] = metadata

        self.all_metrics.update(metadata.get("metrics", []))
        self.all_algorithms.update(metadata.get("algorithms", []))
        self.all_instances.update(metadata.get("instances", []))
        self.max_run_count = max(
            self.max_run_count,
            int(metadata.get("run_count") or 0),
        )

    def _build_response_metadata(self, resolved_x_columns: list[str]) -> dict[str, Any]:
        """
        Description:
            Build response metadata from generated plot information.

        Args:
            resolved_x_columns (list[str]): Resolved X columns.

        Returns:
            dict[str, Any]: Response metadata.
        """

        return {
            "x_columns": resolved_x_columns,
            "metrics": sorted(self.all_metrics),
            "algorithms": sorted(self.all_algorithms),
            "instances": sorted(self.all_instances),
            "run_count": self.max_run_count,
            "by_x_column": self.metadata_by_x_column,
            "x_label": self.config.x_label,
            "y_label": self.config.y_label,
            "x_labels_by_column": dict(self.config.x_labels_by_column or {}),
            "y_labels_by_metric": dict(self.config.y_labels_by_metric or {}),
            "show_grid": self.config.show_grid,
            "show_min_max": self.config.show_min_max,
            "show_std": self.config.show_std,
            "show_average": self.config.show_average,
            "show_median": self.config.show_median,
            "group_by_instance": self.config.group_by_instance,
            "group_by_metric": self.config.group_by_metric,
            "title": self.config.title,
            "output_suffix": self.config.output_suffix,
        }


def generate_evolution_plots(
    rows: list[dict[str, Any]],
    *,
    output_dir: str | Path,
    export_formats: Iterable[str] | None = None,
    selected_algorithms: list[str] | None = None,
    selected_metrics: list[str] | None = None,
    selected_instances: list[str] | None = None,
    x_columns: Iterable[str] | None = None,
    x_axis: str | None = None,
    direction: str | Mapping[str, str] | None = None,
    title: str | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    x_labels_by_column: Mapping[str, str] | None = None,
    y_labels_by_metric: Mapping[str, str] | None = None,
    show_grid: bool = True,
    show_min_max: bool = True,
    show_std: bool = True,
    show_average: bool = True,
    show_median: bool = True,
    group_by_instance: bool = True,
    group_by_metric: bool = True,
    output_suffix: str | None = None,
) -> dict[str, Any]:
    """
    Description:
        Generate evolution convergence plots.

    Args:
        rows (list[dict[str, Any]]): Evolution rows.
        output_dir (str | Path): Directory where plot files are written.
        export_formats (Iterable[str] | None): Requested export formats.
        selected_algorithms (list[str] | None): Algorithms to include.
        selected_metrics (list[str] | None): Metrics to include.
        selected_instances (list[str] | None): Instances to include.
        x_columns (Iterable[str] | None): X columns to plot.
        x_axis (str | None): X axis alias requested by the user.
        direction (str | Mapping[str, str] | None): Optimization direction.
        title (str | None): Plot title template.
        x_label (str | None): X axis label.
        y_label (str | None): Y axis label.
        x_labels_by_column (Mapping[str, str] | None): Labels by X column.
        y_labels_by_metric (Mapping[str, str] | None): Labels by metric.
        show_grid (bool): Whether to show grid lines.
        show_min_max (bool): Whether to show min/max bands.
        show_std (bool): Whether to show standard deviation bands.
        show_average (bool): Whether to show average line.
        show_median (bool): Whether to show median line.
        group_by_instance (bool): Whether to generate one plot per instance.
        group_by_metric (bool): Whether to generate one plot per metric.
        output_suffix (str | None): Optional suffix for output filenames.

    Returns:
        dict[str, Any]: Generated files, filenames, warnings and metadata.
    """

    config = EvolutionPlotConfig(
        output_dir=output_dir,
        export_formats=export_formats,
        selected_algorithms=selected_algorithms,
        selected_metrics=selected_metrics,
        selected_instances=selected_instances,
        x_columns=x_columns,
        x_axis=x_axis,
        direction=direction,
        title=title,
        x_label=x_label,
        y_label=y_label,
        x_labels_by_column=x_labels_by_column,
        y_labels_by_metric=y_labels_by_metric,
        show_grid=show_grid,
        show_min_max=show_min_max,
        show_std=show_std,
        show_average=show_average,
        show_median=show_median,
        group_by_instance=group_by_instance,
        group_by_metric=group_by_metric,
        output_suffix=output_suffix,
    )

    return EvolutionPlotGenerator(rows=rows, config=config).generate()
