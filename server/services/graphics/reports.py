from __future__ import annotations

import io
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Final

import pandas as pd
from SAES.latex_generation.stats_table import (
    Friedman,
    MeanMedian,
    Wilcoxon,
    WilcoxonPivot,
)

LATEX_SPECIALS: Final = {
    r"\&": "&",
    r"\%": "%",
    r"\_": "_",
    r"\#": "#",
    r"\$": "$",
    r"\{": "{",
    r"\}": "}",
    r"\textbackslash{}": "\\",
    r"\textasciitilde{}": "~",
    r"\textasciicircum{}": "^",
}

REQUIRED_DATA_COLUMNS: Final = {
    "Algorithm",
    "Instance",
    "MetricName",
    "ExecutionId",
    "MetricValue",
}

REQUIRED_METRICS_COLUMNS: Final = {
    "MetricName",
    "Maximize",
}

EMPTY_CELL: Final = {"value": "", "highlight": False, "shade": None}

REPORT_TYPES: Final[dict[str, dict[str, Any]]] = {
    "median_iqr": {
        "class": MeanMedian,
        "label": "Median and Interquartile Range Table",
        "slug": "median_iqr",
    },
    "friedman_base": {
        "class": Friedman,
        "label": "Median Table with Friedman Test",
        "slug": "friedman_base",
    },
    "wilcoxon_pivot": {
        "class": WilcoxonPivot,
        "label": "Median Table with Wilcoxon Pairwise Test (Pivot-Based)",
        "slug": "wilcoxon_pivot",
    },
    "wilcoxon_pairwise": {
        "class": Wilcoxon,
        "label": "Pairwise Wilcoxon Test Table",
        "slug": "wilcoxon_pairwise",
    },
}

CELL_SHADE_PATTERNS: Final = [
    r"\\cellcolor\s*\{\s*gray(\d+)\s*\}",
    r"\\cellcolor\s*gray(\d+)",
    r"\\cellcolorgray(\d+)",
    r"\\colorcell\s*\{\s*gray(\d+)\s*\}",
    r"\\colorcell\s*gray(\d+)",
    r"\\colorcellgray(\d+)",
]

LATEX_REPLACEMENTS: Final = [
    (r"\\SI\{([^}]*)\}\{[^}]*\}", r"\1"),
    (r"\\num\{([^}]*)\}", r"\1"),
    (r"\\textbf\{(.*?)\}", r"\1"),
    (r"\\mathbf\{(.*?)\}", r"\1"),
    (r"\\emph\{(.*?)\}", r"\1"),
    (r"\\mathrm\{(.*?)\}", r"\1"),
    (r"\\operatorname\{(.*?)\}", r"\1"),
    (r"([^\s{}_]+)\s*_\{\s*([^}]*)\s*\}", r"\1 (\2)"),
    (r"\^\{([^}]*)\}", r"\1"),
    (r"\^([^\s{}]+)", r"\1"),
]

IGNORED_TABLE_PREFIXES: Final = (
    r"\begin{scriptsize}",
    r"\end{scriptsize}",
    r"\centering",
    r"\small",
    r"\footnotesize",
    r"\scriptsize",
    r"\tiny",
    r"\resizebox",
    r"\vspace",
)

IGNORED_TABLE_TOKENS: Final = {
    r"\hline",
    r"\toprule",
    r"\midrule",
    r"\bottomrule",
}

TABULAR_PATTERNS: Final = [
    r"\\begin\{tabular\*?\}\{.*?\}(.*?)\\end\{tabular\*?\}",
    r"\\begin\{tabularx\}\{.*?\}\{.*?\}(.*?)\\end\{tabularx\}",
]


def unescape_latex(text: str) -> str:
    """
    Description:
        Convert a LaTeX cell value into readable plain text.

    Args:
        text (str): LaTeX text.

    Returns:
        str: Clean plain text.
    """

    value = text.strip()

    for source, target in LATEX_SPECIALS.items():
        value = value.replace(source, target)

    if value.startswith("$") and value.endswith("$"):
        value = value[1:-1].strip()

    for pattern, replacement in LATEX_REPLACEMENTS:
        value = re.sub(pattern, replacement, value)

    value = value.replace("{", "").replace("}", "")
    value = value.replace("~", " ")

    return re.sub(r"\s+", " ", value).strip()


def extract_cell_shade(raw: str) -> tuple[str, int | None]:
    """
    Description:
        Extract gray highlight information from a LaTeX table cell.

    Args:
        raw (str): Raw LaTeX cell content.

    Returns:
        tuple[str, int | None]: Cell content without highlight command and shade value.
    """

    value = raw
    shade: int | None = None

    for pattern in CELL_SHADE_PATTERNS:
        match = re.search(pattern, value)

        if not match:
            continue

        try:
            shade = int(match.group(1))
        except ValueError:
            shade = None

        value = re.sub(pattern, "", value).strip()
        break

    return value, shade


def parse_cell(cell: str) -> dict[str, Any]:
    """
    Description:
        Parse a LaTeX table cell into preview metadata.

    Args:
        cell (str): Raw LaTeX cell.

    Returns:
        dict[str, Any]: Parsed cell with value, highlight and shade.
    """

    raw, shade = extract_cell_shade(cell.strip())

    return {
        "value": unescape_latex(raw),
        "highlight": shade is not None,
        "shade": shade,
    }


def split_unescaped_ampersand(row: str) -> list[str]:
    """
    Description:
        Split a LaTeX row by unescaped ampersands.

    Args:
        row (str): Raw LaTeX table row.

    Returns:
        list[str]: Split cell contents.
    """

    parts: list[str] = []
    current: list[str] = []
    escaped = False

    for char in row:
        if escaped:
            current.append(char)
            escaped = False
            continue

        if char == "\\":
            current.append(char)
            escaped = True
            continue

        if char == "&":
            parts.append("".join(current).strip())
            current = []
            continue

        current.append(char)

    parts.append("".join(current).strip())
    return parts


def clean_table_line(line: str) -> str:
    """
    Description:
        Remove LaTeX table formatting lines that are not data rows.

    Args:
        line (str): Raw LaTeX line.

    Returns:
        str: Cleaned line or empty string when ignored.
    """

    value = line.strip()

    if not value or value.startswith("%"):
        return ""

    if value.startswith(IGNORED_TABLE_PREFIXES):
        return ""

    if value in IGNORED_TABLE_TOKENS:
        return ""

    for token in IGNORED_TABLE_TOKENS:
        value = value.replace(token, "").strip()

    return value


def extract_caption(tex_source: str) -> str | None:
    """
    Description:
        Extract a LaTeX table caption when available.

    Args:
        tex_source (str): LaTeX source.

    Returns:
        str | None: Caption text.
    """

    caption_match = re.search(r"\\caption\{(.*?)\}", tex_source, flags=re.DOTALL)
    return unescape_latex(caption_match.group(1)) if caption_match else None


def extract_tabular_body(tex_source: str) -> str:
    """
    Description:
        Extract the body from a LaTeX tabular or tabularx environment.

    Args:
        tex_source (str): LaTeX source.

    Returns:
        str: Tabular body.
    """

    for pattern in TABULAR_PATTERNS:
        match = re.search(pattern, tex_source, flags=re.DOTALL)

        if match:
            return match.group(1)

    raise ValueError("Could not find tabular environment in LaTeX source")


def normalize_table_row(
    row: list[dict[str, Any]],
    max_len: int,
) -> list[dict[str, Any]]:
    """
    Description:
        Pad or trim a parsed table row to match the expected row length.

    Args:
        row (list[dict[str, Any]]): Parsed row.
        max_len (int): Expected row length.

    Returns:
        list[dict[str, Any]]: Normalized parsed row.
    """

    missing = max_len - len(row)

    if missing > 0:
        row = row + [EMPTY_CELL.copy() for _ in range(missing)]

    return row[:max_len]


def parse_latex_rows(tabular_body: str) -> list[list[dict[str, Any]]]:
    """
    Description:
        Parse rows from a LaTeX tabular body.

    Args:
        tabular_body (str): LaTeX tabular body.

    Returns:
        list[list[dict[str, Any]]]: Parsed rows.
    """

    rows: list[list[dict[str, Any]]] = []
    buffer = ""

    for raw_line in tabular_body.splitlines():
        clean_line = clean_table_line(raw_line)

        if not clean_line:
            continue

        buffer = f"{buffer} {clean_line}".strip() if buffer else clean_line

        if r"\\" not in clean_line:
            continue

        chunks = re.split(r"\\\\", buffer)

        for chunk in chunks[:-1]:
            row = chunk.strip()

            if not row:
                continue

            cells = [parse_cell(cell) for cell in split_unescaped_ampersand(row)]

            if any((cell.get("value") or "") for cell in cells):
                rows.append(cells)

        buffer = chunks[-1].strip()

    if buffer:
        cells = [parse_cell(cell) for cell in split_unescaped_ampersand(buffer)]

        if any((cell.get("value") or "") for cell in cells):
            rows.append(cells)

    return rows


def parse_latex_table(tex_source: str) -> dict[str, Any]:
    """
    Description:
        Parse a LaTeX table into a JSON-serializable preview structure.

    Args:
        tex_source (str): LaTeX source.

    Returns:
        dict[str, Any]: Parsed preview table.
    """

    caption = extract_caption(tex_source)
    tabular_body = extract_tabular_body(tex_source)
    rows = parse_latex_rows(tabular_body)

    if not rows:
        raise ValueError("No rows could be parsed from LaTeX table")

    headers_raw = rows[0]
    data_rows_raw = rows[1:]
    max_len = max(len(row) for row in rows)

    headers = [
        cell.get("value", "") for cell in normalize_table_row(headers_raw, max_len)
    ]
    data_rows = [normalize_table_row(row, max_len) for row in data_rows_raw]

    return {
        "caption": caption,
        "headers": headers,
        "rows": data_rows,
        "raw_tex": tex_source,
    }


def build_preview_json_bytes(
    tex_source: str,
    report_key: str,
    metric: str,
) -> bytes:
    """
    Description:
        Build preview JSON bytes from a SAES LaTeX report.

    Args:
        tex_source (str): LaTeX source.
        report_key (str): Report type key.
        metric (str): Metric name.

    Returns:
        bytes: UTF-8 encoded preview JSON.
    """

    preview = parse_latex_table(tex_source)
    preview["report_key"] = report_key
    preview["report_label"] = REPORT_TYPES[report_key]["label"]
    preview["metric"] = metric

    return json.dumps(preview, ensure_ascii=False, indent=2).encode("utf-8")


def validate_inputs(data_df: pd.DataFrame, metrics_df: pd.DataFrame) -> None:
    """
    Description:
        Validate that dataset and metrics DataFrames match SAES format.

    Args:
        data_df (pd.DataFrame): SAES dataset DataFrame.
        metrics_df (pd.DataFrame): SAES metrics DataFrame.

    Returns:
        None
    """

    missing_data_cols = REQUIRED_DATA_COLUMNS - set(data_df.columns)

    if missing_data_cols:
        raise ValueError(
            "Dataset does not match SAES format. Missing columns: "
            f"{sorted(missing_data_cols)}"
        )

    missing_metrics_cols = REQUIRED_METRICS_COLUMNS - set(metrics_df.columns)

    if missing_metrics_cols:
        raise ValueError(
            "Metrics config does not match SAES format. Missing columns: "
            f"{sorted(missing_metrics_cols)}"
        )


def clean_metrics(metrics: list[str]) -> list[str]:
    """
    Description:
        Normalize and validate the requested metrics list.

    Args:
        metrics (list[str]): Requested metrics.

    Returns:
        list[str]: Clean non-empty metrics.
    """

    cleaned = [
        metric.strip()
        for metric in metrics
        if isinstance(metric, str) and metric.strip()
    ]

    if not cleaned:
        raise ValueError("Metrics list cannot be empty")

    return cleaned


def build_report_files_for_metric(
    *,
    data_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    metric: str,
    output_dir: Path,
) -> dict[str, bytes]:
    """
    Description:
        Generate all configured SAES report files for one metric.

    Args:
        data_df (pd.DataFrame): SAES dataset DataFrame.
        metrics_df (pd.DataFrame): SAES metrics DataFrame.
        metric (str): Metric name.
        output_dir (Path): Temporary output directory.

    Returns:
        dict[str, bytes]: Generated report files keyed by filename.
    """

    files: dict[str, bytes] = {}

    for report_key, report_info in REPORT_TYPES.items():
        report_class = report_info["class"]
        slug = report_info["slug"]

        base_name = f"{slug}_{metric}"
        tex_filename = f"{base_name}.tex"
        preview_filename = f"{base_name}.preview.json"
        tex_path = output_dir / tex_filename

        try:
            report = report_class(
                data_df,
                metrics_df,
                metric,
                normal=False,
            )

            report.compute_table()
            report.save(
                output_path=str(output_dir),
                file_name=tex_filename,
                sideways=False,
            )

            if not tex_path.exists():
                continue

            tex_bytes = tex_path.read_bytes()
            tex_source = tex_bytes.decode("utf-8", errors="replace")

            files[tex_filename] = tex_bytes
            files[preview_filename] = build_preview_json_bytes(
                tex_source=tex_source,
                report_key=report_key,
                metric=metric,
            )

        except Exception:
            continue

    return files


def reports_saes(
    dataset_bytes: bytes,
    metrics_bytes: bytes,
    metrics: list[str],
) -> dict[str, Any]:
    """
    Description:
        Generate SAES statistical reports and JSON previews.

    Args:
        dataset_bytes (bytes): SAES dataset CSV bytes.
        metrics_bytes (bytes): SAES metrics CSV bytes.
        metrics (list[str]): Metrics to generate reports for.

    Returns:
        dict[str, Any]: Generated files and optional warnings.
    """

    if not dataset_bytes:
        raise ValueError("Dataset bytes are empty")

    if not metrics_bytes:
        raise ValueError("Metrics bytes are empty")

    data_df = pd.read_csv(io.BytesIO(dataset_bytes))
    metrics_df = pd.read_csv(io.BytesIO(metrics_bytes))

    validate_inputs(data_df, metrics_df)

    results: dict[str, bytes] = {}
    warnings: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)

        for metric in clean_metrics(metrics):
            metric_files = build_report_files_for_metric(
                data_df=data_df,
                metrics_df=metrics_df,
                metric=metric,
                output_dir=output_dir,
            )

            if not metric_files:
                warnings.append(f"No reports were generated for metric '{metric}'.")

            results.update(metric_files)

    if not results:
        raise ValueError("SAES did not generate any report files.")

    response: dict[str, Any] = {"files": results}

    if warnings:
        response["warnings"] = warnings
        response["saes_report_warnings"] = warnings

    return response
