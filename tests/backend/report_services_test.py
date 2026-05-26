from pathlib import Path

import pytest

import server.services.graphics.reports as reports_service


DATASET = b"""Algorithm,Instance,MetricName,ExecutionId,MetricValue
A1,P1,Accuracy,1,0.9
A2,P1,Accuracy,1,0.8
"""

METRICS = b"""MetricName,Maximize
Accuracy,True
"""


SIMPLE_TEX = r"""
\begin{table}
\caption{Accuracy table}
\begin{tabular}{cc}
Algorithm & Score \\
A1 & \cellcolor{gray25} 0.9 \\
A2 & 0.8 \\
\end{tabular}
\end{table}
"""


class FakeReport:
    def __init__(self, data_df, metrics_df, metric, normal=False):
        self.metric = metric

    def compute_table(self):
        return None

    def save(self, output_path, file_name, sideways=False):
        Path(output_path, file_name).write_text(SIMPLE_TEX, encoding="utf-8")


class FailingReport:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("boom")


def patch_report_types(monkeypatch, fake_class=FakeReport):
    monkeypatch.setattr(
        reports_service,
        "REPORT_TYPES",
        {
            "median_iqr": {
                "class": fake_class,
                "label": "Median and Interquartile Range Table",
                "slug": "median_iqr",
            }
        },
    )


def test_unescape_latex():
    assert reports_service.unescape_latex(r"\textbf{Accuracy\_Score}") == "Accuracy_Score"
    assert reports_service.unescape_latex("$x^{2}$") == "x2"
    assert reports_service.unescape_latex(r"\num{1.23}") == "1.23"


def test_extract_cell_shade():
    value, shade = reports_service.extract_cell_shade(r"\cellcolor{gray25} 0.9")

    assert value == "0.9"
    assert shade == 25


def test_parse_cell():
    result = reports_service.parse_cell(r"\cellcolor{gray25} 0.9")

    assert result["value"] == "0.9"
    assert result["highlight"] is True
    assert result["shade"] == 25


def test_split_unescaped_ampersand():
    assert reports_service.split_unescaped_ampersand(r"A \& B & C") == [r"A \& B", "C"]


def test_clean_table_line():
    assert reports_service.clean_table_line(r"\hline") == ""
    assert reports_service.clean_table_line("% comment") == ""
    assert reports_service.clean_table_line(r"A & B \\") == r"A & B \\"


def test_extract_caption():
    assert reports_service.extract_caption(SIMPLE_TEX) == "Accuracy table"
    assert reports_service.extract_caption(r"\begin{tabular}{c} A \\ \end{tabular}") is None


def test_extract_tabular_body():
    body = reports_service.extract_tabular_body(SIMPLE_TEX)

    assert "Algorithm & Score" in body

    with pytest.raises(ValueError, match="tabular"):
        reports_service.extract_tabular_body("no table")


def test_parse_latex_table():
    result = reports_service.parse_latex_table(SIMPLE_TEX)

    assert result["caption"] == "Accuracy table"
    assert result["headers"] == ["Algorithm", "Score"]
    assert result["rows"][0][0]["value"] == "A1"
    assert result["rows"][0][1]["highlight"] is True


def test_parse_latex_table_no_rows():
    with pytest.raises(ValueError, match="No rows"):
        reports_service.parse_latex_table(r"\begin{tabular}{c}\hline\end{tabular}")


def test_build_preview_json_bytes(monkeypatch):
    patch_report_types(monkeypatch)

    result = reports_service.build_preview_json_bytes(
        tex_source=SIMPLE_TEX,
        report_key="median_iqr",
        metric="Accuracy",
    )

    assert b'"report_key": "median_iqr"' in result
    assert b'"metric": "Accuracy"' in result


def test_validate_inputs_success():
    import pandas as pd
    import io

    data_df = pd.read_csv(io.BytesIO(DATASET))
    metrics_df = pd.read_csv(io.BytesIO(METRICS))

    reports_service.validate_inputs(data_df, metrics_df)


def test_validate_inputs_errors():
    import pandas as pd

    with pytest.raises(ValueError, match="Dataset does not match"):
        reports_service.validate_inputs(pd.DataFrame({"A": [1]}), pd.DataFrame({"MetricName": ["A"], "Maximize": [True]}))

    with pytest.raises(ValueError, match="Metrics config does not match"):
        reports_service.validate_inputs(
            pd.DataFrame(
                {
                    "Algorithm": ["A1"],
                    "Instance": ["P1"],
                    "MetricName": ["Accuracy"],
                    "ExecutionId": [1],
                    "MetricValue": [0.9],
                }
            ),
            pd.DataFrame({"A": [1]}),
        )


def test_clean_metrics():
    assert reports_service.clean_metrics([" Accuracy ", "", 1]) == ["Accuracy"]

    with pytest.raises(ValueError, match="Metrics list cannot be empty"):
        reports_service.clean_metrics(["", 1])


def test_build_report_files_for_metric_success(monkeypatch, tmp_path):
    import pandas as pd
    import io

    patch_report_types(monkeypatch)

    data_df = pd.read_csv(io.BytesIO(DATASET))
    metrics_df = pd.read_csv(io.BytesIO(METRICS))

    result = reports_service.build_report_files_for_metric(
        data_df=data_df,
        metrics_df=metrics_df,
        metric="Accuracy",
        output_dir=tmp_path,
    )

    assert "median_iqr_Accuracy.tex" in result
    assert "median_iqr_Accuracy.preview.json" in result


def test_build_report_files_for_metric_skips_errors(monkeypatch, tmp_path):
    import pandas as pd
    import io

    patch_report_types(monkeypatch, fake_class=FailingReport)

    data_df = pd.read_csv(io.BytesIO(DATASET))
    metrics_df = pd.read_csv(io.BytesIO(METRICS))

    result = reports_service.build_report_files_for_metric(
        data_df=data_df,
        metrics_df=metrics_df,
        metric="Accuracy",
        output_dir=tmp_path,
    )

    assert result == {}


def test_reports_saes_success(monkeypatch):
    patch_report_types(monkeypatch)

    result = reports_service.reports_saes(
        DATASET,
        METRICS,
        metrics=["Accuracy"],
    )

    assert "files" in result
    assert "median_iqr_Accuracy.tex" in result["files"]
    assert "median_iqr_Accuracy.preview.json" in result["files"]


def test_reports_saes_errors(monkeypatch):
    with pytest.raises(ValueError, match="Dataset bytes are empty"):
        reports_service.reports_saes(b"", METRICS, ["Accuracy"])

    with pytest.raises(ValueError, match="Metrics bytes are empty"):
        reports_service.reports_saes(DATASET, b"", ["Accuracy"])

    patch_report_types(monkeypatch, fake_class=FailingReport)

    with pytest.raises(ValueError, match="SAES did not generate"):
        reports_service.reports_saes(DATASET, METRICS, ["Accuracy"])