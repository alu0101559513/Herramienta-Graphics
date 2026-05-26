import base64

import nbformat as nbf

import server.services.graphics.notebook_report as notebook_service


class DummyAnalysis:
    name = "Main Analysis"
    description = "Description"
    status = "completed"
    algorithms = ["A1", "A2"]
    problems = ["P1"]
    metrics = ["Accuracy"]
    num_runs = 2
    enabled_modules = ["saes_plots"]
    metrics_direction = {"Accuracy": "maximize"}


def test_join_items():
    assert notebook_service._join_items(["A", "B"]) == "A, B"
    assert notebook_service._join_items([]) == "N/A"
    assert notebook_service._join_items(None) == "N/A"


def test_format_metrics_direction():
    assert (
        notebook_service._format_metrics_direction({"Accuracy": "maximize"})
        == "Accuracy: maximize"
    )
    assert notebook_service._format_metrics_direction({}) == "N/A"
    assert notebook_service._format_metrics_direction(None) == "N/A"


def test_to_b64():
    assert notebook_service._to_b64(b"abc") == base64.b64encode(b"abc").decode()


def test_build_intro_markdown():
    intro = notebook_service._build_intro_markdown(DummyAnalysis())

    assert "# Benchmark Notebook: Main Analysis" in intro
    assert "**Description:** Description" in intro
    assert "- **Algorithms:** A1, A2" in intro
    assert "- **Metrics direction:** Accuracy: maximize" in intro


def test_build_install_code_contains_dependencies():
    code = notebook_service._build_install_code()

    assert "SAES==1.5.0" in code
    assert "pip" in code
    assert "sys.executable" in code


def test_build_setup_code_embeds_dataset_and_metrics():
    code = notebook_service._build_setup_code(
        b"Algorithm,Instance\nA1,P1\n",
        b"MetricName,Maximize\nAccuracy,True\n",
    )

    assert "_dataset_b64" in code
    assert "_metrics_b64" in code
    assert "pd.read_csv" in code
    assert "required_data_cols" in code


def test_build_imports_code():
    code = notebook_service._build_imports_code()

    assert "from SAES.latex_generation.stats_table" in code
    assert "Boxplot" in code
    assert "CDplot" in code


def test_build_reports_code():
    code = notebook_service._build_reports_code()

    assert "SAES Statistical Reports" in code
    assert "Friedman" in code
    assert "Wilcoxon" in code


def test_build_plots_code():
    code = notebook_service._build_plots_code()

    assert "SAES Plots" in code
    assert "CDplot" in code
    assert "Boxplot" in code
    assert "Violin" in code
    assert "HistoPlot" in code


def test_build_analysis_notebook():
    notebook_bytes = notebook_service.build_analysis_notebook(
        analysis=DummyAnalysis(),
        dataset_bytes=b"Algorithm,Instance,MetricName,ExecutionId,MetricValue\nA1,P1,Accuracy,1,0.9\n",
        metrics_bytes=b"MetricName,Maximize\nAccuracy,True\n",
    )

    notebook = nbf.reads(notebook_bytes.decode("utf-8"), as_version=4)

    assert len(notebook.cells) == 9
    assert notebook.cells[0].cell_type == "markdown"
    assert "Benchmark Notebook: Main Analysis" in notebook.cells[0].source
    assert any(
        "SAES Inputs" in cell.source
        for cell in notebook.cells
        if cell.cell_type == "code"
    )
