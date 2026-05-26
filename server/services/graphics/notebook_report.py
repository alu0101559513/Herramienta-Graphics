from __future__ import annotations

import base64
from typing import Any, Final

import nbformat as nbf

REQUIRED_DATA_COLUMNS: Final = {
    "Algorithm",
    "Instance",
    "MetricName",
    "ExecutionId",
    "MetricValue",
}

REQUIRED_METRICS_COLUMNS: Final = {"MetricName", "Maximize"}


def _join_items(items: list[str] | None) -> str:
    return ", ".join(items) if items else "N/A"


def _format_metrics_direction(metrics_direction: dict[str, str] | None) -> str:
    if not metrics_direction:
        return "N/A"

    return ", ".join(
        f"{metric}: {direction}" for metric, direction in metrics_direction.items()
    )


def _to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def _build_intro_markdown(analysis: Any) -> str:
    return "\n".join(
        [
            f"# Benchmark Notebook: {analysis.name}",
            "",
            f"**Description:** {analysis.description or 'N/A'}",
            "",
            "## Analysis Overview",
            "",
            f"- **Algorithms:** {_join_items(analysis.algorithms)}",
            f"- **Problems:** {_join_items(analysis.problems)}",
            f"- **Metrics:** {_join_items(analysis.metrics)}",
            f"- **Modules:** {_join_items(getattr(analysis, 'enabled_modules', []))}",
            (
                "- **Metrics direction:** "
                f"{_format_metrics_direction(analysis.metrics_direction)}"
            ),
        ]
    )


def _build_install_code() -> str:
    return """
import importlib
import subprocess
import sys


def run_pip(*args: str) -> None:
    command = [sys.executable, "-m", "pip", *args]
    print("Running:", " ".join(command))
    subprocess.check_call(command)


run_pip(
    "install",
    "--upgrade",
    "--prefer-binary",
    "pip",
    "setuptools",
    "wheel",
)

SCIENTIFIC_PACKAGES = [
    "numpy==1.26.4",
    "scipy==1.14.1",
    "pandas==2.2.3",
    "matplotlib==3.9.2",
    "seaborn==0.13.2",
    "statsmodels==0.14.4",
    "scikit-posthocs==0.11.2",
    "ipython==8.29.0",
    "nbformat==5.10.4",
]

SAES_PACKAGES = [
    "SAES==1.5.0",
]

run_pip(
    "install",
    "--upgrade",
    "--prefer-binary",
    *SCIENTIFIC_PACKAGES,
)

run_pip(
    "install",
    "--upgrade",
    "--prefer-binary",
    "--no-deps",
    *SAES_PACKAGES,
)

importlib.invalidate_caches()

print("Dependencies are ready.")
""".strip()


def _build_setup_code(dataset_bytes: bytes, metrics_bytes: bytes) -> str:
    dataset_b64 = _to_b64(dataset_bytes)
    metrics_b64 = _to_b64(metrics_bytes)

    return f"""
import base64
import io
import tempfile
from pathlib import Path

import pandas as pd
from IPython.display import Image, Markdown, display

_dataset_b64 = {dataset_b64!r}
_metrics_b64 = {metrics_b64!r}

experimentData = pd.read_csv(io.BytesIO(base64.b64decode(_dataset_b64)))
metrics = pd.read_csv(io.BytesIO(base64.b64decode(_metrics_b64)))

required_data_cols = {REQUIRED_DATA_COLUMNS!r}
required_metrics_cols = {REQUIRED_METRICS_COLUMNS!r}

missing_data = required_data_cols - set(experimentData.columns)
missing_metrics = required_metrics_cols - set(metrics.columns)

if missing_data:
    raise ValueError(f"Invalid dataset CSV. Missing columns: {{sorted(missing_data)}}")

if missing_metrics:
    raise ValueError(
        f"Invalid metrics CSV. Missing columns: {{sorted(missing_metrics)}}"
    )

ANALYSIS_METRICS = list(metrics["MetricName"].dropna().astype(str).unique())
ANALYSIS_ALGORITHMS = list(experimentData["Algorithm"].dropna().astype(str).unique())
ANALYSIS_PROBLEMS = list(experimentData["Instance"].dropna().astype(str).unique())

display(Markdown("## SAES Inputs"))
display(Markdown("### experimentData"))
display(experimentData.head())

display(Markdown("### metrics"))
display(metrics)

print("Algorithms:", ANALYSIS_ALGORITHMS)
print("Problems:", ANALYSIS_PROBLEMS)
print("Metrics:", ANALYSIS_METRICS)

WORKDIR = Path(tempfile.mkdtemp(prefix="saes_notebook_"))
OUTPUT_DIR = WORKDIR / "outputs"
REPORTS_DIR = OUTPUT_DIR / "reports"
PLOTS_DIR = OUTPUT_DIR / "plots"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

print("Working directory:", WORKDIR)
print("Output directory:", OUTPUT_DIR)


def safe_name(value: str) -> str:
    return (
        str(value)
        .replace("/", "_")
        .replace("\\\\", "_")
        .replace(" ", "_")
        .replace(":", "_")
    )


def show_png(path: Path, title: str | None = None) -> None:
    if title:
        display(Markdown(title))

    if path.exists():
        display(Image(filename=str(path)))
    else:
        display(Markdown(f"**Expected image not found:** `{{str(path)}}`"))
""".strip()


def _build_imports_code() -> str:
    return """
import matplotlib

matplotlib.use("Agg")

from SAES.latex_generation.stats_table import (
    Friedman,
    MeanMedian,
    Wilcoxon,
    WilcoxonPivot,
)

try:
    from SAES.plots.boxplot import Boxplot
except Exception:
    Boxplot = None

try:
    from SAES.plots.cdplot import CDplot
except Exception:
    CDplot = None

try:
    from SAES.plots.violin import Violin
except Exception:
    Violin = None

try:
    from SAES.plots.histoplot import HistoPlot
except Exception:
    HistoPlot = None

print("Boxplot:", "OK" if Boxplot is not None else "NOT AVAILABLE")
print("CDplot:", "OK" if CDplot is not None else "NOT AVAILABLE")
print("Violin:", "OK" if Violin is not None else "NOT AVAILABLE")
print("HistoPlot:", "OK" if HistoPlot is not None else "NOT AVAILABLE")
""".strip()


def _build_reports_code() -> str:
    return r"""
display(Markdown("## SAES Statistical Reports"))

for metric_name in ANALYSIS_METRICS:
    display(Markdown(f"### Metric: `{metric_name}`"))

    report_builders = [
        ("friedman", "Median Table with Friedman Test", Friedman),
        ("median_iqr", "Median and Interquartile Range Table", MeanMedian),
        (
            "wilcoxon_pivot",
            "Median Table with Wilcoxon Pairwise Test (Pivot-Based)",
            WilcoxonPivot,
        ),
        ("wilcoxon_pairwise", "Pairwise Wilcoxon Test Table", Wilcoxon),
    ]

    for report_slug, report_label, report_class in report_builders:
        display(Markdown(f"#### {report_label}"))

        report = report_class(
            experimentData,
            metrics,
            metric_name,
            normal=False,
        )

        report_dir = REPORTS_DIR / metric_name / report_slug
        report_dir.mkdir(parents=True, exist_ok=True)

        try:
            report.save(str(report_dir))
        except Exception as exc:
            print(f"Error saving report {report_slug} for {metric_name}: {exc}")

        try:
            rendered = report.show()

            if rendered is not None:
                display(rendered)
            else:
                print(f"{report_slug}: show() returned no displayable content.")
        except Exception as exc:
            print(f"Error displaying report {report_slug} for {metric_name}: {exc}")
""".strip()


def _build_plots_code() -> str:
    return r"""
display(Markdown("## SAES Plots"))

if CDplot is not None:
    for metric_name in ANALYSIS_METRICS:
        metric_dir = PLOTS_DIR / metric_name
        metric_dir.mkdir(parents=True, exist_ok=True)

        try:
            cdplot = CDplot(experimentData, metrics, metric_name)
            cdplot.save(str(metric_dir))
            output_path = metric_dir / f"cdplot_{metric_name}.png"
            show_png(output_path, f"### Critical Distance - `{metric_name}`")
        except Exception as exc:
            print(f"CDplot error for {metric_name}: {exc}")
else:
    display(Markdown("CDplot not available in this SAES installation."))

if Boxplot is not None:
    for metric_name in ANALYSIS_METRICS:
        metric_dir = PLOTS_DIR / metric_name / "boxplot"
        metric_dir.mkdir(parents=True, exist_ok=True)

        boxplot = Boxplot(experimentData, metrics, metric_name)

        for instance_name in ANALYSIS_PROBLEMS:
            safe_instance = safe_name(instance_name)
            output_file = f"boxplot_{metric_name}_{safe_instance}.png"
            output_path = metric_dir / output_file

            try:
                boxplot.save_instance(
                    instance_name,
                    str(metric_dir),
                    file_name=output_file,
                )
                show_png(
                    output_path,
                    f"### Boxplot - `{metric_name}` / `{instance_name}`",
                )
            except Exception as exc:
                print(f"Boxplot error for {metric_name}/{instance_name}: {exc}")
else:
    display(Markdown("Boxplot not available in this SAES installation."))

if Violin is not None:
    for metric_name in ANALYSIS_METRICS:
        metric_dir = PLOTS_DIR / metric_name / "violin"
        metric_dir.mkdir(parents=True, exist_ok=True)

        violin = Violin(experimentData, metrics, metric_name)

        for instance_name in ANALYSIS_PROBLEMS:
            safe_instance = safe_name(instance_name)
            output_file = f"violin_{metric_name}_{safe_instance}.png"
            output_path = metric_dir / output_file

            try:
                violin.save_instance(
                    instance_name,
                    str(metric_dir),
                    file_name=output_file,
                )
                show_png(
                    output_path,
                    f"### Violin - `{metric_name}` / `{instance_name}`",
                )
            except Exception as exc:
                print(f"Violin error for {metric_name}/{instance_name}: {exc}")
else:
    display(Markdown("Violin not available in this SAES installation."))

if HistoPlot is not None:
    for metric_name in ANALYSIS_METRICS:
        metric_dir = PLOTS_DIR / metric_name / "histogram"
        metric_dir.mkdir(parents=True, exist_ok=True)

        histoplot = HistoPlot(experimentData, metrics, metric_name)

        for instance_name in ANALYSIS_PROBLEMS:
            safe_instance = safe_name(instance_name)
            output_file = f"histoplot_{metric_name}_{safe_instance}.png"
            output_path = metric_dir / output_file

            try:
                histoplot.save_instance(
                    instance_name,
                    str(metric_dir),
                    file_name=output_file,
                )
                show_png(
                    output_path,
                    f"### Histogram - `{metric_name}` / `{instance_name}`",
                )
            except Exception as exc:
                print(f"Histogram error for {metric_name}/{instance_name}: {exc}")
else:
    display(Markdown("HistoPlot not available in this SAES installation."))
""".strip()


def build_analysis_notebook(
    *,
    analysis: Any,
    dataset_bytes: bytes,
    metrics_bytes: bytes,
) -> bytes:
    notebook = nbf.v4.new_notebook()
    notebook["cells"] = [
        nbf.v4.new_markdown_cell(_build_intro_markdown(analysis)),
        nbf.v4.new_markdown_cell(
            "## Dependency Installation\n\n"
            "Run this cell first if the environment does not already include SAES "
            "and the compatible scientific Python dependencies."
        ),
        nbf.v4.new_code_cell(_build_install_code()),
        nbf.v4.new_code_cell(_build_setup_code(dataset_bytes, metrics_bytes)),
        nbf.v4.new_code_cell(_build_imports_code()),
        nbf.v4.new_markdown_cell(
            "## SAES Report Generation\n\n"
            "Run the following cell to generate and visualize the statistical tables."
        ),
        nbf.v4.new_code_cell(_build_reports_code()),
        nbf.v4.new_markdown_cell(
            "## SAES Plot Generation\n\n"
            "Run the following cell to generate and visualize the plots using SAES."
        ),
        nbf.v4.new_code_cell(_build_plots_code()),
    ]

    return nbf.writes(notebook).encode("utf-8")
