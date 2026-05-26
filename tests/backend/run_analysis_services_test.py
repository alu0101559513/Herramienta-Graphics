from pathlib import Path

import pytest

import server.services.run_analysis.analysis.modules as analysis_modules
import server.services.run_analysis.analysis.options as analysis_options
import server.services.run_analysis.analysis.pipeline as analysis_pipeline
import server.services.run_analysis.analysis.storage as analysis_storage
import server.services.run_analysis.reanalyze as reanalyze_service


class DummyAnalysis:
    def __init__(self, **kwargs):
        self.id = "analysis-id"
        self.name = "Analysis"
        self.description = "Description"
        self.normalized_dataset_file_id = "normalized-id"
        self.raw_dataset_file_id = "raw-id"
        self.filtered_dataset_file_ids = {}
        self.dataset_capabilities = {
            "saes_plots": True,
            "saes_reports": True,
            "notebooks": True,
            "evolution_plots": True,
        }
        self.algorithms = ["A1", "A2"]
        self.problems = ["P1"]
        self.metrics = ["Accuracy"]
        self.metrics_direction = {"Accuracy": "maximize"}
        self.plot_export_formats = ["png"]
        self.outputs = {}
        self.enabled_modules = []
        self.selected_algorithms_last_run = []
        self.current_run_key = "all"
        self.evolution_metadata = {}
        self.saved = False

        for key, value in kwargs.items():
            setattr(self, key, value)

    async def save(self):
        self.saved = True
        return self


def test_normalize_requested_plot_types():
    assert analysis_modules.normalize_requested_plot_types(None) == {
        "boxplot",
        "violin",
        "histogram",
        "critical_distance",
    }
    assert analysis_modules.normalize_requested_plot_types([" boxplot ", "", 1]) == {
        "boxplot"
    }


def test_get_modules_pending_reanalysis_without_outputs():
    assert analysis_modules.get_modules_pending_reanalysis(
        selected_modules=["saes_plots", "notebooks"],
        run_outputs=None,
        selected_plot_types=["boxplot"],
    ) == ["notebooks", "saes_plots"]


def test_get_modules_pending_reanalysis_detects_missing_plot_type():
    result = analysis_modules.get_modules_pending_reanalysis(
        selected_modules=["saes_plots"],
        run_outputs={
            "saes_plots": {"a.png": "id"},
            "generated_plot_types": ["boxplot"],
        },
        selected_plot_types=["boxplot", "violin"],
    )

    assert result == ["saes_plots"]


def test_get_modules_pending_reanalysis_no_pending():
    result = analysis_modules.get_modules_pending_reanalysis(
        selected_modules=["saes_plots"],
        run_outputs={
            "saes_plots": {"a.png": "id"},
            "generated_plot_types": ["boxplot"],
        },
        selected_plot_types=["boxplot"],
    )

    assert result == []


def test_build_algorithm_run_key():
    assert analysis_modules.build_algorithm_run_key(["A1", "A2"], ["A2", "A1"]) == "all"
    assert (
        analysis_modules.build_algorithm_run_key([" A 1 ", "B/2"], ["A 1", "B/2", "C"])
        == "a_1__b_2"
    )


def test_normalize_modules_success_and_errors():
    assert analysis_modules.normalize_modules(
        ["saes_notebook", "saes_plots", "saes_plots"]
    ) == [
        "notebooks",
        "saes_plots",
    ]

    with pytest.raises(ValueError, match="At least one module"):
        analysis_modules.normalize_modules([])

    with pytest.raises(ValueError, match="Invalid module"):
        analysis_modules.normalize_modules(["bad"])


def test_normalize_export_formats():
    analysis = DummyAnalysis(plot_export_formats=["PNG", "pdf", "svg", "png"])
    assert analysis_modules.normalize_export_formats(analysis) == ["png", "svg"]

    analysis = DummyAnalysis(plot_export_formats=["bad"])

    with pytest.raises(ValueError, match="Invalid export format"):
        analysis_modules.normalize_export_formats(analysis)


def test_validate_requested_modules():
    analysis_modules.validate_requested_modules(
        DummyAnalysis(),
        ["saes_plots", "evolution_plots"],
    )

    with pytest.raises(ValueError, match="SAES outputs"):
        analysis_modules.validate_requested_modules(
            DummyAnalysis(
                dataset_capabilities={
                    "saes_plots": False,
                    "evolution_plots": True,
                }
            ),
            ["saes_plots"],
        )

    with pytest.raises(ValueError, match="Evolution plots"):
        analysis_modules.validate_requested_modules(
            DummyAnalysis(
                dataset_capabilities={
                    "saes_plots": True,
                    "evolution_plots": False,
                }
            ),
            ["evolution_plots"],
        )


def test_get_metrics_and_instances():
    analysis = DummyAnalysis(metrics=[" Accuracy ", "", 1], problems=[" P1 ", None])

    assert analysis_modules.get_metrics(analysis) == ["Accuracy"]
    assert analysis_modules.get_instances(analysis) == ["P1"]


def test_resolve_metrics_direction():
    assert analysis_pipeline.resolve_metrics_direction(
        metrics=["Accuracy"],
        frontend_config={"accuracy": "minimize"},
    ) == {"Accuracy": "minimize"}

    assert analysis_pipeline.resolve_metrics_direction(
        metrics=[],
        frontend_config={},
    ) == {}

    with pytest.raises(ValueError, match="Invalid direction"):
        analysis_pipeline.resolve_metrics_direction(
            metrics=["Accuracy"],
            frontend_config={"Accuracy": "up"},
        )


def test_normalize_string_helpers_and_bool_option():
    assert analysis_options.normalize_string_list(" A ") == ["A"]
    assert analysis_options.normalize_string_list(["A", " A ", "", 1]) == ["A"]
    assert analysis_options.normalize_string_list(123) == []

    assert analysis_options.normalize_string_dict(
        {" A ": " One ", "": "x", "B": "", 1: "bad"}
    ) == {"A": "One"}

    assert analysis_options.get_bool_option({"x": "yes"}, "x", False) is True
    assert analysis_options.get_bool_option({"x": "off"}, "x", True) is False
    assert analysis_options.get_bool_option({"x": "bad"}, "x", True) is True


def test_get_evolution_options_defaults_and_legacy_axis():
    analysis = DummyAnalysis(
        outputs={
            "evolution_options": {
                "x_axis": "generation",
                "show_grid": "false",
            }
        }
    )

    options = analysis_options.get_evolution_options(analysis)

    assert options["x_columns"] == ["Generation"]
    assert options["y_label"] == "Fitness"
    assert options["show_grid"] is False


def test_evolution_signature_key_and_label_are_stable():
    options = {"selected_metrics": ["Accuracy"], "x_columns": ["Generation"]}
    signature = analysis_options.build_evolution_options_signature(options)

    assert "Accuracy" in signature
    assert len(analysis_options.build_evolution_history_key(options)) == 16
    assert "Evolución" in analysis_options.build_evolution_history_label(options)


@pytest.mark.asyncio
async def test_save_generated_files(monkeypatch):
    saved = []

    async def fake_save_file(filename, data):
        saved.append((filename, data))
        return f"id-{len(saved)}"

    monkeypatch.setattr(analysis_storage, "save_file", fake_save_file)

    result = await analysis_storage.save_generated_files(
        analysis_id="a1",
        run_key="all",
        namespace="plots",
        files={"plot.png": b"png"},
    )

    assert result == {"plot.png": "id-1"}
    assert saved[0][0] == "a1_all_plots_plot.png"


@pytest.mark.asyncio
async def test_generate_saes_metrics_csv(monkeypatch):
    async def fake_save_file(filename, data):
        return "metrics-id"

    monkeypatch.setattr(analysis_pipeline, "save_file", fake_save_file)

    analysis = DummyAnalysis(metrics_direction={"Accuracy": "maximize"})
    metrics_csv, metrics_id = await analysis_pipeline.generate_saes_metrics_csv(
        analysis=analysis,
        metrics=["Accuracy"],
        run_key="all",
    )

    assert metrics_id == "metrics-id"
    assert b"Accuracy,True" in metrics_csv
    assert analysis.metrics_config_file_id == "metrics-id"
    assert analysis.saved is True


def test_resolve_evolution_files():
    assert analysis_pipeline.resolve_evolution_files(
        {"files": {"plot.png": b"png"}}
    ) == {"plot.png": b"png"}

    assert analysis_pipeline.resolve_evolution_files(
        {"files": {"plot.png": bytearray(b"png")}}
    ) == {"plot.png": b"png"}

    assert analysis_pipeline.resolve_evolution_files({"files": []}) == {}


def test_resolve_evolution_files_from_path(tmp_path: Path):
    file_path = tmp_path / "plot.png"
    file_path.write_bytes(b"png")

    assert analysis_pipeline.resolve_evolution_files(
        {"files": {"ignored": str(file_path)}}
    ) == {"plot.png": b"png"}

    assert analysis_pipeline.resolve_evolution_files(
        {"files": {"ignored": file_path}}
    ) == {"plot.png": b"png"}


def test_merge_outputs_preserves_evolution_history():
    analysis = DummyAnalysis(
        outputs={
            "analysis_runs": {
                "all": {
                    "evolution_plot_sets": {
                        "old": {
                            "evolution_plots": {
                                "old.png": "old-id",
                            }
                        }
                    }
                }
            }
        }
    )

    merged = analysis_pipeline.merge_outputs(
        analysis=analysis,
        run_key="all",
        run_results={
            "evolution_plots": {"new.png": "new-id"},
            "evolution_plot_sets": {
                "new": {
                    "evolution_plots": {
                        "new.png": "new-id",
                    }
                }
            },
        },
    )

    assert "old" in merged["analysis_runs"]["all"]["evolution_plot_sets"]
    assert "new" in merged["analysis_runs"]["all"]["evolution_plot_sets"]
    assert merged["evolution_plots"] == {"new.png": "new-id"}


@pytest.mark.asyncio
async def test_get_source_dataset_file_id_reanalysis(monkeypatch):
    async def fake_reanalyze_with_selected_algorithms(analysis, selected_algorithms):
        return "filtered-id"

    monkeypatch.setattr(
        analysis_storage,
        "reanalyze_with_selected_algorithms",
        fake_reanalyze_with_selected_algorithms,
    )

    result = await analysis_storage.get_source_dataset_file_id(
        analysis=DummyAnalysis(),
        run_key="a1",
        selected_algorithms=["A1"],
        run_algorithms=["A1"],
    )

    assert result == "filtered-id"


@pytest.mark.asyncio
async def test_run_analysis_pipeline_saes_plots(monkeypatch):
    async def fake_get_file(file_id):
        return b"dataset"

    def fake_export_saes_dataset(dataset):
        return b"saes"

    async def fake_generate_saes_metrics_csv(analysis, metrics, run_key):
        return b"metrics", "metrics-id"

    async def fake_run_saes_plots(**kwargs):
        return {
            "saes_plots": {"plot.png": "plot-id"},
            "generated_plot_types": ["boxplot"],
        }

    monkeypatch.setattr(analysis_pipeline, "get_file", fake_get_file)
    monkeypatch.setattr(analysis_pipeline, "export_saes_dataset", fake_export_saes_dataset)
    monkeypatch.setattr(
        analysis_pipeline,
        "generate_saes_metrics_csv",
        fake_generate_saes_metrics_csv,
    )
    monkeypatch.setattr(analysis_pipeline, "run_saes_plots", fake_run_saes_plots)

    analysis = DummyAnalysis()
    result = await analysis_pipeline.run_analysis_pipeline(
        analysis,
        modules=["saes_plots"],
        selected_plot_types=["boxplot"],
    )

    assert result["saes_plots"] == {"plot.png": "plot-id"}
    assert analysis.current_run_key == "all"
    assert analysis.saved is True


@pytest.mark.asyncio
async def test_run_analysis_pipeline_errors(monkeypatch):
    with pytest.raises(ValueError, match="Dataset file not found"):
        await analysis_pipeline.run_analysis_pipeline(
            DummyAnalysis(normalized_dataset_file_id=None, raw_dataset_file_id=None),
            modules=["saes_plots"],
        )

    async def fake_get_file(file_id):
        return b""

    monkeypatch.setattr(analysis_pipeline, "get_file", fake_get_file)

    with pytest.raises(ValueError, match="Dataset is empty"):
        await analysis_pipeline.run_analysis_pipeline(
            DummyAnalysis(),
            modules=["saes_plots"],
        )


def test_reanalyze_build_algorithm_run_key_and_clean():
    assert reanalyze_service.clean_algorithms([" A1 ", "", 1]) == ["A1"]
    assert reanalyze_service.build_algorithm_run_key(["A1", "A2"], ["A2", "A1"]) == "all"
    assert reanalyze_service.build_algorithm_run_key(["A 1"], ["A 1", "A2"]) == "a_1"


def test_reanalyze_get_source_dataset_file_id():
    assert reanalyze_service.get_source_dataset_file_id(DummyAnalysis()) == "normalized-id"
    assert (
        reanalyze_service.get_source_dataset_file_id(
            DummyAnalysis(
                normalized_dataset_file_id=None,
                raw_dataset_file_id="raw-id",
            )
        )
        == "raw-id"
    )


@pytest.mark.asyncio
async def test_reanalyze_with_selected_algorithms_existing_file(monkeypatch):
    async def fake_get_file(file_id):
        assert file_id == "normalized-id"
        return b"Algorithm,MetricValue\nA1,1\n"

    monkeypatch.setattr(reanalyze_service, "get_file", fake_get_file)

    analysis = DummyAnalysis(filtered_dataset_file_ids={"a1": "existing-id"})

    result = await reanalyze_service.reanalyze_with_selected_algorithms(
        analysis,
        ["A1"],
    )

    assert result == "existing-id"
    assert analysis.current_run_key == "a1"
    assert analysis.selected_algorithms_last_run == ["A1"]
    assert analysis.saved is True


@pytest.mark.asyncio
async def test_reanalyze_with_selected_algorithms_creates_file(monkeypatch):
    async def fake_get_file(file_id):
        return b"Algorithm,Value\nA1,1\nA2,2\n"

    async def fake_save_file(filename, data):
        assert b"A1" in data
        return "new-filtered-id"

    monkeypatch.setattr(reanalyze_service, "get_file", fake_get_file)
    monkeypatch.setattr(reanalyze_service, "save_file", fake_save_file)

    analysis = DummyAnalysis(algorithms=["A1", "A2"])

    result = await reanalyze_service.reanalyze_with_selected_algorithms(
        analysis,
        ["A1"],
    )

    assert result == "new-filtered-id"
    assert analysis.filtered_dataset_file_ids["a1"] == "new-filtered-id"
    assert analysis.current_run_key == "a1"


@pytest.mark.asyncio
async def test_reanalyze_with_selected_algorithms_errors(monkeypatch):
    with pytest.raises(ValueError, match="At least one algorithm"):
        await reanalyze_service.reanalyze_with_selected_algorithms(
            DummyAnalysis(),
            [" "],
        )

    with pytest.raises(ValueError, match="Dataset file not found"):
        await reanalyze_service.reanalyze_with_selected_algorithms(
            DummyAnalysis(normalized_dataset_file_id=None, raw_dataset_file_id=None),
            ["A1"],
        )

    async def fake_get_file(file_id):
        return b""

    monkeypatch.setattr(reanalyze_service, "get_file", fake_get_file)

    with pytest.raises(ValueError, match="Dataset is empty"):
        await reanalyze_service.reanalyze_with_selected_algorithms(
            DummyAnalysis(),
            ["A1"],
        )
