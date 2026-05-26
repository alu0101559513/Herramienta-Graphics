from pathlib import Path

import pytest

import server.services.graphics.saes_graphics.plots as plots_service


DATASET = b"""Algorithm,Instance,MetricName,ExecutionId,MetricValue
A1,P1,Accuracy,1,0.9
A2,P1,Accuracy,1,0.8
"""

METRICS = b"""MetricName,Maximize
Accuracy,True
"""


class FakeInstancePlot:
    def __init__(self, data_df, metrics_df, metric):
        self.metric = metric

    def save_instance(self, instance, output_path, file_name):
        Path(output_path, file_name).write_bytes(
            f"{self.__class__.__name__}:{instance}:{self.metric}".encode()
        )


class FakeCDPlot:
    def __init__(self, data_df, metrics_df, metric):
        self.metric = metric

    def save(self, output_path, file_name):
        Path(output_path, file_name).write_bytes(f"CD:{self.metric}".encode())


def patch_plot_classes(monkeypatch):
    monkeypatch.setattr(plots_service, "Boxplot", FakeInstancePlot)
    monkeypatch.setattr(plots_service, "Violin", FakeInstancePlot)
    monkeypatch.setattr(plots_service, "HistoPlot", FakeInstancePlot)
    monkeypatch.setattr(plots_service, "CDplot", FakeCDPlot)


def test_normalize_export_format_success():
    assert plots_service._normalize_export_format(" PNG ") == "png"


def test_normalize_export_format_error():
    with pytest.raises(ValueError, match="Unsupported export format"):
        plots_service._normalize_export_format("pdf")


def test_plots_saes_generates_selected_plot_files(monkeypatch):
    patch_plot_classes(monkeypatch)

    result = plots_service.plots_saes(
        DATASET,
        METRICS,
        metric="Accuracy",
        instance="P1",
        export_formats=["png", "svg"],
        selected_plot_types=["boxplot", "histogram"],
    )

    files = result["files"]

    assert "Accuracy_P1_boxplot.png" in files
    assert "Accuracy_P1_histogram.png" in files
    assert "Accuracy_P1_boxplot.svg" in files
    assert "Accuracy_P1_histogram.svg" in files
    assert "Accuracy_P1_violin.png" not in files


def test_plots_saes_default_plot_types(monkeypatch):
    patch_plot_classes(monkeypatch)

    result = plots_service.plots_saes(
        DATASET,
        METRICS,
        metric="Accuracy",
        instance="P1",
    )

    assert "Accuracy_P1_boxplot.png" in result["files"]
    assert "Accuracy_P1_violin.png" in result["files"]
    assert "Accuracy_P1_histogram.png" in result["files"]


@pytest.mark.parametrize(
    "dataset,metrics,metric,instance,error",
    [
        (b"", METRICS, "Accuracy", "P1", "Dataset bytes are empty"),
        (DATASET, b"", "Accuracy", "P1", "Metrics bytes are empty"),
        (DATASET, METRICS, "", "P1", "Metric cannot be empty"),
        (DATASET, METRICS, "Accuracy", "", "Instance cannot be empty"),
    ],
)
def test_plots_saes_input_errors(dataset, metrics, metric, instance, error):
    with pytest.raises(ValueError, match=error):
        plots_service.plots_saes(dataset, metrics, metric, instance)


def test_plots_saes_invalid_plot_type(monkeypatch):
    patch_plot_classes(monkeypatch)

    with pytest.raises(ValueError, match="Unsupported plot types"):
        plots_service.plots_saes(
            DATASET,
            METRICS,
            metric="Accuracy",
            instance="P1",
            selected_plot_types=["boxplot", "bad"],
        )


def test_plot_cd_saes_success(monkeypatch):
    patch_plot_classes(monkeypatch)

    result = plots_service.plot_cd_saes(
        DATASET,
        METRICS,
        metric="Accuracy",
        export_formats=["png", "eps"],
    )

    assert "Accuracy_critical_distance.png" in result["files"]
    assert "Accuracy_critical_distance.eps" in result["files"]


@pytest.mark.parametrize(
    "dataset,metrics,metric,error",
    [
        (b"", METRICS, "Accuracy", "Dataset bytes are empty"),
        (DATASET, b"", "Accuracy", "Metrics bytes are empty"),
        (DATASET, METRICS, "", "Metric cannot be empty"),
    ],
)
def test_plot_cd_saes_input_errors(dataset, metrics, metric, error):
    with pytest.raises(ValueError, match=error):
        plots_service.plot_cd_saes(dataset, metrics, metric)