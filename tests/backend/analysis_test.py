import io
import json
import zipfile

import pytest
from fastapi import HTTPException

import server.routers.analysis as analysis_routes
from tests.backend.conftest import TestAnalysis
from server.services.dataset.exceptions import DatasetFormatError, DatasetValidationError


def test_get_category_files_regular_category():
    run_outputs = {"saes_plots": {"plot.png": "file-id"}}
    assert analysis_routes.get_category_files(run_outputs, "saes_plots") == {"plot.png": "file-id"}

def test_get_category_files_regular_category_not_dict():
    run_outputs = {"saes_plots": ["plot.png"]}
    assert analysis_routes.get_category_files(run_outputs, "saes_plots") is None

def test_serialize_outputs_ignores_internal_keys_and_serializes_supported_values():
    outputs = {
        "saes_plots": {"a.png": "file-1", "b.png": "file-2"},
        "notebooks": {"main.ipynb": "file-3"},
        "plain_list": ["one.txt", "two.txt"],
        "single": "file-4",
        "none": None,
        "error": "failed",
        "analysis_runs": {"all": {}},
        "evolution_metadata": {"x": 1},
        "generated_plot_types": ["boxplot"],
        "evolution_options": {"show_grid": True},
        "evolution_options_signature": "sig",
        "selected_algorithms": ["A1"],
        "modules": ["saes_plots"],
        "metrics_config_file_id": "metrics-id",
        "saes_plot_warnings": ["warning"],
        "evolution_plot_warnings": ["warning"],
    }

    assert analysis_routes.serialize_outputs(outputs) == {
        "saes_plots": ["a.png", "b.png"],
        "notebooks": ["main.ipynb"],
        "plain_list": ["one.txt", "two.txt"],
        "single": ["single"],
    }
def test_serialize_outputs_merges_evolution_history_into_evolution_plots():
    outputs = {
        "evolution_plot_sets": {
            "abc123": {
                "evolution_plots": {
                    "mean.png": "file-1",
                    "std.png": "file-2",
                }
            },
            "empty": {"evolution_plots": {}},
            "invalid": [],
            123: {"evolution_plots": {"bad.png": "file"}},
        }
    }

    assert analysis_routes.serialize_outputs(outputs) == {
        "evolution_plots": ["mean.png", "std.png", "bad.png"]
    }
@pytest.mark.parametrize(
    "filename,expected",
    [
        ("data.preview.json", "application/json"),
        ("DATA.PREVIEW.JSON", "application/json"),
        ("data.json", "application/json"),
        ("notebook.ipynb", "application/x-ipynb+json"),
        ("data.csv", "text/csv"),
        ("plot.png", "image/png"),
        ("photo.jpg", "image/jpeg"),
        ("photo.jpeg", "image/jpeg"),
        ("image.webp", "image/webp"),
        ("vector.svg", "image/svg+xml"),
        ("figure.eps", "application/postscript"),
        ("notes.txt", "text/plain; charset=utf-8"),
        ("table.tex", "application/x-tex"),
        ("files.zip", "application/zip"),
        ("unknown.bin", "application/octet-stream"),
    ],
)
def test_get_media_type(filename, expected):
    assert analysis_routes.get_media_type(filename) == expected

@pytest.mark.parametrize(
    "value,expected",
    [
        ("saes_notebook", "notebooks"),
        ("saes_notebooks", "notebooks"),
        (" saes_plots ", "saes_plots"),
    ],
)
def test_normalize_module_name(value, expected):
    assert analysis_routes.normalize_module_name(value) == expected

def test_parse_modules_input_from_json_array():
    assert analysis_routes.parse_modules_input('["saes_plots", "notebooks"]') == [
        "saes_plots",
        "notebooks",
    ]

def test_parse_modules_input_from_plain_string():
    assert analysis_routes.parse_modules_input("saes_notebook") == ["notebooks"]

@pytest.mark.parametrize(
    "value,detail",
    [
        ('{"bad": true}', "Modules must be a string or a JSON array of strings"),
        ("[]", "Modules must not be empty"),
        ('[""]', "Modules must not contain empty values"),
        ('["bad_module"]', "Invalid module 'bad_module'"),
        ('[123]', "Modules must be a string or a JSON array of strings"),
    ],
)
def test_parse_modules_input_errors(value, detail):
    with pytest.raises(HTTPException) as exc:
        analysis_routes.parse_modules_input(value)
    assert exc.value.status_code == 400
    assert exc.value.detail == detail

def test_normalize_modules_list_rejects_non_string_direct_call():
    with pytest.raises(HTTPException) as exc:
        analysis_routes.normalize_modules_list(["saes_plots", 1])  # type: ignore[list-item]
    assert exc.value.status_code == 400
    assert exc.value.detail == "Modules must be a list of strings"

def test_get_capabilities_returns_existing(test_analysis):
    assert analysis_routes.get_capabilities(test_analysis) == test_analysis.dataset_capabilities

def test_get_capabilities_returns_defaults_when_missing(authenticated_test_user):
    analysis = TestAnalysis(user_id=authenticated_test_user.id)
    analysis.dataset_capabilities = None
    assert analysis_routes.get_capabilities(analysis) == {
        "saes_plots": False,
        "saes_reports": False,
        "notebooks": False,
        "evolution_plots": False,
    }

def test_validate_modules_against_capabilities_accepts_enabled_modules(test_analysis):
    analysis_routes.validate_modules_against_capabilities(
        test_analysis,
        ["saes_plots", "evolution_plots"],
    )

def test_validate_modules_against_capabilities_rejects_saes(authenticated_test_user):
    analysis = TestAnalysis(
        user_id=authenticated_test_user.id,
        dataset_capabilities={
            "saes_plots": False,
            "saes_reports": False,
            "notebooks": False,
            "evolution_plots": True,
        },
    )
    with pytest.raises(HTTPException) as exc:
        analysis_routes.validate_modules_against_capabilities(analysis, ["saes_plots"])
    assert exc.value.status_code == 400
    assert "SAES outputs are not available" in exc.value.detail

def test_validate_modules_against_capabilities_rejects_evolution(authenticated_test_user):
    analysis = TestAnalysis(
        user_id=authenticated_test_user.id,
        dataset_capabilities={
            "saes_plots": True,
            "saes_reports": True,
            "notebooks": True,
            "evolution_plots": False,
        },
    )
    with pytest.raises(HTTPException) as exc:
        analysis_routes.validate_modules_against_capabilities(analysis, ["evolution_plots"])
    assert exc.value.status_code == 400
    assert "Evolution plots are not available" in exc.value.detail

def test_get_reanalysis_modules_from_payload(test_analysis):
    assert analysis_routes.get_reanalysis_modules(test_analysis, ["saes_plots"]) == [
        "saes_plots"
    ]

def test_get_reanalysis_modules_from_enabled_modules(test_analysis):
    test_analysis.enabled_modules = ["notebooks"]
    assert analysis_routes.get_reanalysis_modules(test_analysis) == ["notebooks"]

def test_get_reanalysis_modules_from_capabilities(test_analysis):
    test_analysis.enabled_modules = []
    assert analysis_routes.get_reanalysis_modules(test_analysis) == [
        "saes_plots",
        "saes_reports",
        "notebooks",
        "evolution_plots",
    ]

def test_normalize_plot_types_default_includes_evolution():
    assert analysis_routes.normalize_plot_types_list(None) == [
        "boxplot",
        "critical_distance",
        "evolution",
        "histogram",
        "violin",
    ]

def test_normalize_plot_types_removes_duplicates_and_sorts():
    assert analysis_routes.normalize_plot_types_list(["violin", "boxplot", "violin"]) == [
        "boxplot",
        "violin",
    ]

@pytest.mark.parametrize(
    "value,detail",
    [
        ([123], "Plot types must be a list of strings"),
        ([""], "Plot types must not contain empty values"),
        (["wrong"], "Invalid plot type 'wrong'"),
    ],
)
def test_normalize_plot_types_errors(value, detail):
    with pytest.raises(HTTPException) as exc:
        analysis_routes.normalize_plot_types_list(value)
    assert exc.value.status_code == 400
    assert exc.value.detail == detail

def test_get_saes_plot_types_filters_evolution():
    assert analysis_routes.get_saes_plot_types(["boxplot", "evolution", "histogram"]) == [
        "boxplot",
        "histogram",
    ]

def test_parse_metrics_direction_input_none():
    assert analysis_routes.parse_metrics_direction_input(None) is None
    assert analysis_routes.parse_metrics_direction_input("   ") is None

def test_parse_metrics_direction_input_success():
    assert analysis_routes.parse_metrics_direction_input(
        '{"Accuracy": "MAXIMIZE", "Time": " minimize "}'
    ) == {"Accuracy": "maximize", "Time": "minimize"}

@pytest.mark.parametrize(
    "value,detail",
    [
        ("{bad json", "Invalid metrics_direction format"),
        ('["Accuracy"]', "metrics_direction must be a JSON object"),
        ('{"Accuracy": 123}', "metrics_direction must be a JSON object of string keys and values"),
        ('{"Accuracy": "up"}', "Invalid direction for metric 'Accuracy'. Use 'maximize' or 'minimize'."),
    ],
)
def test_parse_metrics_direction_input_errors(value, detail):
    with pytest.raises(HTTPException) as exc:
        analysis_routes.parse_metrics_direction_input(value)
    assert exc.value.status_code == 400
    assert exc.value.detail == detail

@pytest.mark.parametrize(
    "value,expected",
    [
        (None, ["png"]),
        ("", ["png"]),
        ("png,svg,png", ["png", "svg"]),
        ('["jpg", "eps"]', ["jpg", "eps"]),
        ("jpeg", ["jpeg"]),
    ],
)
def test_parse_plot_export_formats_input_success(value, expected):
    assert analysis_routes.parse_plot_export_formats_input(value) == expected

@pytest.mark.parametrize(
    "value,detail",
    [
        ('{"format": "png"}', "plot_export_formats must be a JSON array or a comma-separated string"),
        ("gif", "Invalid plot export format 'gif'. Use one of: eps, jpeg, jpg, png, svg."),
    ],
)
def test_parse_plot_export_formats_input_errors(value, detail):
    with pytest.raises(HTTPException) as exc:
        analysis_routes.parse_plot_export_formats_input(value)
    assert exc.value.status_code == 400
    assert exc.value.detail == detail

@pytest.mark.parametrize(
    "value,default,expected",
    [
        (None, True, True),
        ("", False, False),
        ("true", False, True),
        ("1", False, True),
        ("yes", False, True),
        ("y", False, True),
        ("on", False, True),
        ("false", True, False),
        ("0", True, False),
        ("no", True, False),
        ("n", True, False),
        ("off", True, False),
    ],
)
def test_parse_bool_form_value(value, default, expected):
    assert analysis_routes.parse_bool_form_value(value, default) is expected

def test_parse_bool_form_value_invalid():
    with pytest.raises(HTTPException) as exc:
        analysis_routes.parse_bool_form_value("maybe", True)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid boolean value 'maybe'"

@pytest.mark.parametrize(
    "value,expected",
    [
        (None, []),
        ("", []),
        ("Generation", ["Generation"]),
        ('["Generation", "Time", "Generation"]', ["Generation", "Time"]),
        ('["", "Time"]', ["Time"]),
    ],
)
def test_parse_string_list_form_value_success(value, expected):
    assert analysis_routes.parse_string_list_form_value(value, "field") == expected

@pytest.mark.parametrize(
    "value,detail",
    [
        ('{"x": "Generation"}', "field must be a JSON array of strings"),
        ('["Generation", 1]', "field must contain only strings"),
    ],
)
def test_parse_string_list_form_value_errors(value, detail):
    with pytest.raises(HTTPException) as exc:
        analysis_routes.parse_string_list_form_value(value, "field")
    assert exc.value.status_code == 400
    assert exc.value.detail == detail

@pytest.mark.parametrize(
    "value,expected",
    [
        (None, {}),
        ("", {}),
        ('{"Generation": "Evaluaciones", "": "x", "Metric": ""}', {"Generation": "Evaluaciones"}),
    ],
)
def test_parse_string_dict_form_value_success(value, expected):
    assert analysis_routes.parse_string_dict_form_value(value, "field") == expected

@pytest.mark.parametrize(
    "value,detail",
    [
        ("bad", "field must be a JSON object of strings"),
        ('["x"]', "field must be a JSON object of strings"),
        ('{"x": 1}', "field must contain only string keys and values"),
    ],
)
def test_parse_string_dict_form_value_errors(value, detail):
    with pytest.raises(HTTPException) as exc:
        analysis_routes.parse_string_dict_form_value(value, "field")
    assert exc.value.status_code == 400
    assert exc.value.detail == detail

def test_parse_evolution_x_columns_delegates_list_parser():
    assert analysis_routes.parse_evolution_x_columns('["Generation"]') == ["Generation"]

def test_clean_list_removes_invalid_empty_and_duplicates():
    assert analysis_routes.clean_list([" A ", "", "A", "B", 1]) == ["A", "B"]  # type: ignore[list-item]

def test_clean_string_dict_removes_invalid_empty_and_strips():
    assert analysis_routes.clean_string_dict({" A ": " One ", "": "x", "B": "", 1: "bad"}) == {"A": "One"}  # type: ignore[dict-item]

def test_clean_optional_string():
    assert analysis_routes.clean_optional_string(None) is None
    assert analysis_routes.clean_optional_string("  ") is None
    assert analysis_routes.clean_optional_string(" x ") == "x"
def test_compact_evolution_options_removes_empty_values():
    result = analysis_routes.compact_evolution_options(
        {
            "title": " Curve ",
            "x_columns": ["Generation", "", "Generation"],
            "x_labels_by_column": {"Generation": " Eval ", "": "bad"},
            "empty_list": [],
            "empty_dict": {},
            "empty_string": "   ",
            "statistics": ["std", "median", "mean", "min_max"],
            "show_grid": False,
        }
    )

    assert result["title"] == "Curve"
    assert result["x_columns"] == ["Generation"]
    assert result["x_labels_by_column"] == {"Generation": "Eval"}
    assert result["statistics"] == ["std", "median", "mean", "min_max"]
    assert result["show_grid"] is False
    assert "empty_list" not in result
    assert "empty_dict" not in result
    assert "empty_string" not in result

def test_normalize_evolution_options_for_signature_is_stable():
    first = analysis_routes.normalize_evolution_options_for_signature(
        {
            "x_columns": ["Time", "Generation"],
            "selected_algorithms": ["B", "A"],
            "x_labels_by_column": {"b": "B", "a": "A"},
            "show_grid": False,
        }
    )
    second = analysis_routes.normalize_evolution_options_for_signature(
        {
            "x_columns": ["Generation", "Time"],
            "selected_algorithms": ["A", "B"],
            "x_labels_by_column": {"a": "A", "b": "B"},
            "show_grid": False,
        }
    )
    assert first == second
    assert first["show_grid"] is False
    assert first["show_std"] is True

def test_build_evolution_options_signature_and_key_are_stable():
    options = {"x_columns": ["Generation"], "selected_metrics": ["Accuracy"]}
    signature = analysis_routes.build_evolution_options_signature(options)
    assert json.loads(signature)["x_columns"] == ["Generation"]
    assert analysis_routes.build_evolution_history_key(options) == analysis_routes.build_evolution_history_key(options)
    assert len(analysis_routes.build_evolution_history_key(options)) == 16

def test_build_evolution_history_label():
    label = analysis_routes.build_evolution_history_label(
        {
            "show_average": True,
            "show_median": True,
            "show_std": False,
            "show_min_max": True,
            "selected_metrics": ["Accuracy"],
            "selected_instances": ["P1"],
            "x_columns": ["Generation"],
        }
    )
    assert "Evolución" in label
    assert "media" in label
    assert "mediana" in label
    assert "min/max" in label
    assert "métricas: Accuracy" in label
    assert "instancias: P1" in label
    assert "X: Generation" in label

def test_run_has_matching_evolution_options():
    options = {"x_columns": ["Generation"], "show_grid": True}
    signature = analysis_routes.build_evolution_options_signature(options)
    assert analysis_routes.run_has_matching_evolution_options(
        {"evolution_plots": {"plot.png": "id"}, "evolution_options_signature": signature},
        options,
    ) is True
    assert analysis_routes.run_has_matching_evolution_options(
        {"evolution_plots": {"plot.png": "id"}, "evolution_options": options},
        options,
    ) is True
    assert analysis_routes.run_has_matching_evolution_options({}, options) is False
    assert analysis_routes.run_has_matching_evolution_options({"evolution_plots": {}}, options) is False

def test_persist_evolution_options_for_run(test_analysis):
    options = {"x_columns": ["Generation"], "show_average": True}
    test_analysis.outputs = {
        "analysis_runs": {
            "all": {
                "evolution_plots": {"plot.png": "plot-id"},
                "evolution_metadata": {"runs": 10},
            }
        }
    }

    analysis_routes.persist_evolution_options_for_run(
        analysis=test_analysis,
        run_key="all",
        evolution_options=options,
    )

    run_outputs = test_analysis.outputs["analysis_runs"]["all"]
    assert "evolution_options" in run_outputs
    assert "evolution_options_signature" in run_outputs
    assert "evolution_plot_sets" in run_outputs
    assert test_analysis.outputs["evolution_plot_sets"] == run_outputs["evolution_plot_sets"]

def test_persist_evolution_options_for_run_empty_options_noop(test_analysis):
    test_analysis.outputs = {}
    analysis_routes.persist_evolution_options_for_run(
        analysis=test_analysis,
        run_key="all",
        evolution_options={},
    )
    assert test_analysis.outputs == {}

def test_sanitize_zip_name():
    assert analysis_routes.sanitize_zip_name(" my/file name\\test ") == "my_file_name_test"

def test_get_requested_run_key_explicit(test_analysis):
    assert analysis_routes.get_requested_run_key(test_analysis, run_key=" custom ") == "custom"

def test_get_requested_run_key_selected_algorithms(monkeypatch, test_analysis):
    monkeypatch.setattr(
        analysis_routes,
        "build_algorithm_run_key",
        lambda selected_algorithms, all_algorithms: "A1",
    )
    assert analysis_routes.get_requested_run_key(test_analysis, selected_algorithms=["A1"]) == "A1"

def test_get_requested_run_key_fallback(test_analysis):
    test_analysis.current_run_key = None
    assert analysis_routes.get_requested_run_key(test_analysis) == "all"

def test_get_run_outputs_uses_analysis_runs(test_analysis):
    assert analysis_routes.get_run_outputs(test_analysis, run_key="all") == {
        "selected_algorithms": ["A1", "A2"],
        "modules": ["saes_plots"],
        "saes_plots": {"plot.png": "plot-file-id"},
    }

def test_get_run_outputs_fallback_categories(test_analysis):
    result = analysis_routes.get_run_outputs(test_analysis, run_key="missing")
    assert result["saes_plots"] == {"plot.png": "plot-file-id"}
    assert result["saes_reports"] == {"report.tex": "report-file-id"}
    assert result["notebooks"] == {"analysis.ipynb": "notebook-file-id"}

def test_build_default_modules_from_capabilities():
    assert analysis_routes.build_default_modules_from_capabilities(
        {
            "saes_plots": True,
            "saes_reports": False,
            "notebooks": True,
            "evolution_plots": True,
        }
    ) == ["saes_plots", "notebooks", "evolution_plots"]

def test_create_analysis(client, authenticated_test_user):
    response = client.post("/analyses/", json={"name": "New Analysis", "description": "Description"})
    assert response.status_code == 200, response.json()
    assert len(TestAnalysis.analyses) == 1
    data = response.json()
    assert data["name"] == "New Analysis"
    assert data["description"] == "Description"
    assert data["plot_export_formats"] == ["png"]

def test_list_analyses(client, authenticated_test_user, test_analysis):
    response = client.get("/analyses/")
    assert response.status_code == 200, response.json()
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Main Analysis"

def test_get_analysis_success(client, authenticated_test_user, test_analysis):
    response = client.get(f"/analyses/{test_analysis.id}")
    assert response.status_code == 200, response.json()
    assert response.json()["name"] == "Main Analysis"

def test_get_analysis_not_found(client, authenticated_test_user):
    response = client.get("/analyses/000000000000000000009999")
    assert response.status_code == 404, response.json()
    assert response.json()["detail"] == "Analysis not found"

def test_update_analysis_success(client, authenticated_test_user, test_analysis):
    response = client.patch(
        f"/analyses/{test_analysis.id}",
        json={"name": "Updated", "description": "Updated description"},
    )
    assert response.status_code == 200, response.json()
    assert response.json()["name"] == "Updated"
    assert test_analysis.description == "Updated description"
    assert test_analysis.saved is True

def test_delete_analysis_success(client, authenticated_test_user, test_analysis):
    response = client.delete(f"/analyses/{test_analysis.id}")
    assert response.status_code == 200, response.json()
    assert response.json() == {"message": "Analysis deleted"}
    assert test_analysis.deleted is True
    assert TestAnalysis.analyses == []

def test_inspect_uploaded_dataset_success(client, authenticated_test_user, test_analysis, monkeypatch):
    monkeypatch.setattr(analysis_routes, "inspect_dataset", lambda content: {"columns": ["Algorithm", "MetricValue"]})
    response = client.post(
        f"/analyses/{test_analysis.id}/inspect-dataset",
        files={"file": ("dataset.csv", b"Algorithm,MetricValue\nA1,1\n", "text/csv")},
    )
    assert response.status_code == 200, response.json()
    assert response.json() == {"columns": ["Algorithm", "MetricValue"]}

def test_inspect_uploaded_dataset_rejects_non_csv(client, authenticated_test_user, test_analysis):
    response = client.post(
        f"/analyses/{test_analysis.id}/inspect-dataset",
        files={"file": ("dataset.txt", b"content", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only CSV files are allowed"

def test_inspect_uploaded_dataset_format_error(client, authenticated_test_user, test_analysis, monkeypatch):
    def raise_format_error(content):
        raise DatasetFormatError("bad csv")

    monkeypatch.setattr(analysis_routes, "inspect_dataset", raise_format_error)
    response = client.post(
        f"/analyses/{test_analysis.id}/inspect-dataset",
        files={"file": ("dataset.csv", b"bad", "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "bad csv"

def test_inspect_uploaded_dataset_generic_error(client, authenticated_test_user, test_analysis, monkeypatch):
    def raise_error(content):
        raise RuntimeError("boom")

    monkeypatch.setattr(analysis_routes, "inspect_dataset", raise_error)
    response = client.post(
        f"/analyses/{test_analysis.id}/inspect-dataset",
        files={"file": ("dataset.csv", b"bad", "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid CSV format: boom"

def test_upload_dataset_success(client, authenticated_test_user, test_analysis, monkeypatch):
    saved_files = []

    def test_parse_dataset(content):
        return (
            [
                {
                    "Algorithm": "A1",
                    "Instance": "P1",
                    "MetricName": "Accuracy",
                    "ExecutionId": "1",
                    "MetricValue": "0.9",
                }
            ],
            {
                "saes_plots": True,
                "saes_reports": True,
                "notebooks": True,
                "evolution_plots": False,
            },
        )

    def test_extract_metadata(rows):
        return {
            "algorithms": ["A1"],
            "problems": ["P1"],
            "metrics": ["Accuracy"],
            "runs": 1,
            "evolution": {},
        }

    async def test_save_file(filename, content):
        saved_files.append((filename, content))
        return f"file-id-{len(saved_files)}"

    monkeypatch.setattr(analysis_routes, "parse_dataset", test_parse_dataset)
    monkeypatch.setattr(analysis_routes, "validate_dataset", lambda rows: None)
    monkeypatch.setattr(analysis_routes, "extract_metadata", test_extract_metadata)
    monkeypatch.setattr(analysis_routes, "normalize_dataset", lambda content: "normalized,csv\n")
    monkeypatch.setattr(analysis_routes, "save_file", test_save_file)
    monkeypatch.setattr(analysis_routes, "get_default_metrics_direction", lambda metrics: {"Accuracy": "maximize"})

    response = client.post(
        f"/analyses/{test_analysis.id}/upload-dataset",
        files={"file": ("dataset.csv", b"Algorithm,MetricValue\nA1,0.9\n", "text/csv")},
    )

    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["message"] == "Dataset uploaded"
    assert data["dataset_capabilities"]["saes_plots"] is True
    assert data["metadata"]["algorithms"] == ["A1"]
    assert data["default_modules"] == ["saes_plots", "saes_reports", "notebooks"]
    assert test_analysis.raw_dataset_file_id == "file-id-1"
    assert test_analysis.normalized_dataset_file_id == "file-id-2"
    assert test_analysis.metrics_direction == {"Accuracy": "maximize"}
    assert test_analysis.status == "dataset_uploaded"
    assert test_analysis.saved is True

@pytest.mark.parametrize(
    "filename,expected_detail",
    [("dataset.txt", "Only CSV files are allowed")],
)
def test_upload_dataset_rejects_non_csv(client, authenticated_test_user, test_analysis, filename, expected_detail):
    response = client.post(
        f"/analyses/{test_analysis.id}/upload-dataset",
        files={"file": (filename, b"content", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == expected_detail

def test_upload_dataset_format_error(client, authenticated_test_user, test_analysis, monkeypatch):
    def raise_format_error(content):
        raise DatasetFormatError("format error")

    monkeypatch.setattr(analysis_routes, "parse_dataset", raise_format_error)
    response = client.post(
        f"/analyses/{test_analysis.id}/upload-dataset",
        files={"file": ("dataset.csv", b"bad", "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "format error"

def test_upload_dataset_validation_error(client, authenticated_test_user, test_analysis, monkeypatch):
    monkeypatch.setattr(analysis_routes, "parse_dataset", lambda content: ([{"bad": "row"}], {"saes_plots": False}))

    def raise_validation_error(rows):
        raise DatasetValidationError("validation error")

    monkeypatch.setattr(analysis_routes, "validate_dataset", raise_validation_error)
    response = client.post(
        f"/analyses/{test_analysis.id}/upload-dataset",
        files={"file": ("dataset.csv", b"bad", "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "validation error"

def test_upload_dataset_generic_error(client, authenticated_test_user, test_analysis, monkeypatch):
    def raise_error(content):
        raise RuntimeError("boom")

    monkeypatch.setattr(analysis_routes, "parse_dataset", raise_error)
    response = client.post(
        f"/analyses/{test_analysis.id}/upload-dataset",
        files={"file": ("dataset.csv", b"bad", "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid CSV format: boom"

def test_analyze_success(client, authenticated_test_user, test_analysis, monkeypatch):
    async def test_run_analysis_pipeline(analysis, modules, selected_algorithms=None, selected_plot_types=None):
        analysis.outputs = {
            **(analysis.outputs or {}),
            "analysis_runs": {
                "all": {
                    "selected_algorithms": selected_algorithms or [],
                    "modules": modules,
                    "saes_plots": {"plot.png": "plot-file-id"},
                }
            },
        }

    monkeypatch.setattr(analysis_routes, "run_analysis_pipeline", test_run_analysis_pipeline)
    monkeypatch.setattr(analysis_routes, "resolve_metrics_direction", lambda metrics, frontend_config, csv_bytes: {"Accuracy": "maximize"})

    response = client.post(
        f"/analyses/{test_analysis.id}/analyze",
        data={
            "modules": '["saes_plots"]',
            "metrics_direction": '{"Accuracy": "maximize"}',
            "plot_export_formats": "png,svg",
            "evolution_x_columns": '["Generation"]',
            "evolution_show_grid": "true",
            "evolution_show_min_max": "false",
            "evolution_show_std": "true",
            "evolution_group_by_instance": "yes",
            "evolution_group_by_metric": "no",
        },
    )

    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["status"] == "completed"
    assert data["modules"] == ["saes_plots"]
    assert data["metrics_direction"] == {"Accuracy": "maximize"}
    assert data["plot_export_formats"] == ["png", "svg"]
    assert data["outputs"]["saes_plots"] == ["plot.png"]

def test_analyze_with_metrics_file_success(client, authenticated_test_user, test_analysis, monkeypatch):
    captured = {}

    async def test_run_analysis_pipeline(analysis, modules, selected_algorithms=None, selected_plot_types=None):
        analysis.outputs = {"saes_reports": {"report.tex": "report-id"}}

    def test_resolve_metrics_direction(metrics, frontend_config, csv_bytes):
        captured["csv_bytes"] = csv_bytes
        return {"Accuracy": "maximize"}

    monkeypatch.setattr(analysis_routes, "run_analysis_pipeline", test_run_analysis_pipeline)
    monkeypatch.setattr(analysis_routes, "resolve_metrics_direction", test_resolve_metrics_direction)

    response = client.post(
        f"/analyses/{test_analysis.id}/analyze",
        data={"modules": "saes_reports"},
        files={"metrics_file": ("metrics.csv", b"Metric,Direction\nAccuracy,maximize\n", "text/csv")},
    )

    assert response.status_code == 200, response.json()
    assert captured["csv_bytes"] == b"Metric,Direction\nAccuracy,maximize\n"

def test_analyze_rejects_invalid_metrics_file(client, authenticated_test_user, test_analysis):
    response = client.post(
        f"/analyses/{test_analysis.id}/analyze",
        data={"modules": "saes_plots"},
        files={"metrics_file": ("metrics.txt", b"bad", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only CSV files are allowed for metrics file"

def test_analyze_returns_failed_when_pipeline_fails(client, authenticated_test_user, test_analysis, monkeypatch):
    async def failing_pipeline(*args, **kwargs):
        raise RuntimeError("pipeline failed")

    monkeypatch.setattr(analysis_routes, "run_analysis_pipeline", failing_pipeline)
    monkeypatch.setattr(analysis_routes, "resolve_metrics_direction", lambda metrics, frontend_config, csv_bytes: {"Accuracy": "maximize"})
    response = client.post(f"/analyses/{test_analysis.id}/analyze", data={"modules": "saes_plots"})
    assert response.status_code == 200, response.json()
    assert response.json()["status"] == "failed"
    assert response.json()["error"] == "pipeline failed"

def test_analyze_rejects_missing_dataset(client, authenticated_test_user):
    analysis = TestAnalysis(user_id=authenticated_test_user.id, raw_dataset_file_id=None, normalized_dataset_file_id=None)
    TestAnalysis.analyses.append(analysis)
    response = client.post(f"/analyses/{analysis.id}/analyze", data={"modules": "saes_plots"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Dataset not uploaded"

def test_patch_analyze_success(client, authenticated_test_user, test_analysis, monkeypatch):
    async def test_run_analysis_pipeline(analysis, modules, selected_algorithms=None, selected_plot_types=None):
        analysis.outputs = {"notebooks": {"analysis.ipynb": "notebook-id"}}

    monkeypatch.setattr(analysis_routes, "run_analysis_pipeline", test_run_analysis_pipeline)
    response = client.patch(f"/analyses/{test_analysis.id}/analyze", data={"modules": "notebooks", "plot_export_formats": "png"})
    assert response.status_code == 200, response.json()
    assert response.json()["status"] == "completed"
    assert response.json()["outputs"] == {"notebooks": ["analysis.ipynb"]}

def test_reanalyze_success(client, authenticated_test_user, test_analysis, monkeypatch):
    async def test_run_analysis_pipeline(analysis, modules, selected_algorithms=None, selected_plot_types=None):
        analysis.outputs = {
            "analysis_runs": {
                "A1": {
                    "selected_algorithms": ["A1"],
                    "modules": modules,
                    "saes_plots": {"boxplot.png": "boxplot-id"},
                }
            }
        }

    monkeypatch.setattr(analysis_routes, "run_analysis_pipeline", test_run_analysis_pipeline)
    monkeypatch.setattr(analysis_routes, "build_algorithm_run_key", lambda selected_algorithms, all_algorithms: "A1")
    response = client.post(
        f"/analyses/{test_analysis.id}/reanalyze",
        json={"selected_algorithms": [" A1 "], "modules": ["saes_plots"], "selected_plot_types": ["boxplot"]},
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["status"] == "completed"
    assert data["selected_algorithms_last_run"] == ["A1"]
    assert data["selected_plot_types_last_run"] == ["boxplot"]
    assert data["current_run_key"] == "A1"

def test_reanalyze_with_evolution_options_persists_history(client, authenticated_test_user, test_analysis, monkeypatch):
    async def test_run_analysis_pipeline(analysis, modules, selected_algorithms=None, selected_plot_types=None):
        analysis.outputs = {
            "analysis_runs": {
                "A1": {
                    "selected_algorithms": ["A1"],
                    "modules": modules,
                    "evolution_plots": {"evolution.png": "evolution-id"},
                    "evolution_metadata": {"runs": 1},
                }
            }
        }

    monkeypatch.setattr(analysis_routes, "run_analysis_pipeline", test_run_analysis_pipeline)
    monkeypatch.setattr(analysis_routes, "build_algorithm_run_key", lambda selected_algorithms, all_algorithms: "A1")

    response = client.post(
        f"/analyses/{test_analysis.id}/reanalyze",
        json={
            "selected_algorithms": ["A1"],
            "modules": ["evolution_plots"],
            "selected_plot_types": ["evolution"],
            "evolution_x_columns": ["Generation"],
            "evolution_show_average": True,
        },
    )
    assert response.status_code == 200, response.json()
    assert "evolution_plots" in response.json()["outputs"]

def test_patch_reanalyze_success(client, authenticated_test_user, test_analysis, monkeypatch):
    async def test_run_analysis_pipeline(analysis, modules, selected_algorithms=None, selected_plot_types=None):
        analysis.outputs = {
            "analysis_runs": {
                "A2": {
                    "selected_algorithms": ["A2"],
                    "modules": modules,
                    "notebooks": {"analysis.ipynb": "notebook-id"},
                }
            }
        }

    monkeypatch.setattr(analysis_routes, "run_analysis_pipeline", test_run_analysis_pipeline)
    monkeypatch.setattr(analysis_routes, "build_algorithm_run_key", lambda selected_algorithms, all_algorithms: "A2")
    response = client.patch(
        f"/analyses/{test_analysis.id}/reanalyze",
        json={"selected_algorithms": ["A2"], "modules": ["notebooks"], "selected_plot_types": ["histogram"]},
    )
    assert response.status_code == 200, response.json()
    assert response.json()["current_run_key"] == "A2"

def test_reanalyze_rejects_empty_algorithms(client, authenticated_test_user, test_analysis):
    response = client.post(
        f"/analyses/{test_analysis.id}/reanalyze",
        json={"selected_algorithms": [" ", ""], "modules": ["saes_plots"], "selected_plot_types": ["boxplot"]},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "At least one algorithm must be selected"
def test_reanalyze_runs_when_requested_outputs_are_not_detected(
    client,
    authenticated_test_user,
    test_analysis,
    monkeypatch,
):
    called = {"pipeline": False}

    async def test_run_analysis_pipeline(*args, **kwargs):
        called["pipeline"] = True

    test_analysis.outputs = {
        "analysis_runs": {
            "A1": {
                "selected_algorithms": ["A1"],
                "modules": ["saes_plots"],
                "saes_plots": {
                    "plot.png": "plot-id",
                    "generated_plot_types": ["boxplot"],
                },
            }
        }
    }

    monkeypatch.setattr(
        analysis_routes,
        "run_analysis_pipeline",
        test_run_analysis_pipeline,
    )
    monkeypatch.setattr(
        analysis_routes,
        "build_algorithm_run_key",
        lambda selected_algorithms, all_algorithms: "A1",
    )

    response = client.post(
        f"/analyses/{test_analysis.id}/reanalyze",
        json={
            "selected_algorithms": ["A1"],
            "modules": ["saes_plots"],
            "selected_plot_types": ["boxplot"],
        },
    )

    assert response.status_code == 200, response.json()
    assert response.json()["status"] == "completed"
    assert called["pipeline"] is True
def test_reanalyze_returns_failed_when_pipeline_fails(client, authenticated_test_user, test_analysis, monkeypatch):
    async def failing_pipeline(*args, **kwargs):
        raise RuntimeError("reanalyze failed")

    monkeypatch.setattr(analysis_routes, "run_analysis_pipeline", failing_pipeline)
    monkeypatch.setattr(analysis_routes, "build_algorithm_run_key", lambda selected_algorithms, all_algorithms: "A1")
    response = client.post(
        f"/analyses/{test_analysis.id}/reanalyze",
        json={"selected_algorithms": ["A1"], "modules": ["saes_plots"], "selected_plot_types": ["boxplot"]},
    )
    assert response.status_code == 200, response.json()
    assert response.json()["status"] == "failed"
    assert response.json()["error"] == "reanalyze failed"

def test_list_analysis_runs(client, authenticated_test_user, test_analysis):
    response = client.get(f"/analyses/{test_analysis.id}/runs")
    assert response.status_code == 200, response.json()
    data = response.json()
    assert "all" in data
    assert data["all"]["selected_algorithms"] == ["A1", "A2"]
    assert data["all"]["modules"] == ["saes_plots"]
    assert data["all"]["categories"] == {"saes_plots": ["plot.png"]}

def test_list_files(client, authenticated_test_user, test_analysis):
    response = client.get(f"/analyses/{test_analysis.id}/files")
    assert response.status_code == 200, response.json()
    assert response.json() == {"saes_plots": ["plot.png"]}

def test_list_files_with_missing_run_key_fallback(client, authenticated_test_user, test_analysis):
    response = client.get(f"/analyses/{test_analysis.id}/files", params={"run_key": "missing"})
    assert response.status_code == 200, response.json()
    assert response.json()["saes_reports"] == ["report.tex"]

def test_download_analysis_category_zip_success(
    client,
    authenticated_test_user,
    test_analysis,
    monkeypatch,
):
    test_analysis.outputs = {
        "analysis_runs": {
            "all": {
                "saes_plots": {
                    "plot.png": "plot-file-id",
                }
            }
        }
    }
    test_analysis.current_run_key = "all"

    async def test_get_file(file_id):
        return f"content-{file_id}".encode()

    monkeypatch.setattr(analysis_routes, "get_file", test_get_file)

    response = client.get(
        f"/analyses/{test_analysis.id}/files/saes_plots/zip",
        params={"run_key": "all"},
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    assert "attachment;" in response.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        assert zip_file.namelist() == ["plot.png"]
        assert zip_file.read("plot.png") == b"content-plot-file-id"
def test_download_analysis_category_zip_evolution_history_success(client, authenticated_test_user, test_analysis, monkeypatch):
    test_analysis.outputs = {
        "analysis_runs": {
            "all": {
                "evolution_plot_sets": {
                    "abc123": {
                        "evolution_plots": {"evolution.png": "evolution-file-id"}
                    }
                }
            }
        }
    }

    async def test_get_file(file_id):
        return f"content-{file_id}".encode()

    monkeypatch.setattr(analysis_routes, "get_file", test_get_file)
    response = client.get(f"/analyses/{test_analysis.id}/files/evolution_history__abc123/zip")
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        assert zip_file.namelist() == ["evolution.png"]
        assert zip_file.read("evolution.png") == b"content-evolution-file-id"

def test_download_analysis_category_zip_not_found(client, authenticated_test_user, test_analysis):
    response = client.get(f"/analyses/{test_analysis.id}/files/missing/zip")
    assert response.status_code == 404
    assert response.json()["detail"] == "No files found for this category"
def test_download_analysis_category_zip_no_downloadable_files(
    client,
    authenticated_test_user,
    test_analysis,
    monkeypatch,
):
    test_analysis.outputs = {
        "analysis_runs": {
            "all": {
                "saes_plots": {
                    "plot.png": "plot-id",
                }
            }
        }
    }
    test_analysis.current_run_key = "all"

    async def test_get_file(file_id):
        return None

    monkeypatch.setattr(analysis_routes, "get_file", test_get_file)

    response = client.get(
        f"/analyses/{test_analysis.id}/files/saes_plots/zip",
        params={"run_key": "all"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No downloadable files found for this category"
def test_download_analysis_category_zip_skips_get_file_errors(client, authenticated_test_user, test_analysis, monkeypatch):
    test_analysis.outputs = {"saes_plots": {"plot.png": "plot-id"}}

    async def test_get_file(file_id):
        raise RuntimeError("storage down")

    monkeypatch.setattr(analysis_routes, "get_file", test_get_file)
    response = client.get(f"/analyses/{test_analysis.id}/files/saes_plots/zip")
    assert response.status_code == 404
    assert response.json()["detail"] == "No downloadable files found for this category"

def test_download_file_success(client, authenticated_test_user, test_analysis, monkeypatch):
    async def test_get_file(file_id):
        assert file_id == "plot-file-id"
        return b"png-bytes"

    monkeypatch.setattr(analysis_routes, "get_file", test_get_file)
    response = client.get(
        f"/analyses/{test_analysis.id}/files/saes_plots/plot.png",
        params={"download": "false"},
    )
    assert response.status_code == 200, response.text
    assert response.content == b"png-bytes"
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-disposition"] == 'inline; filename="plot.png"'
    assert response.headers["cache-control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["expires"] == "0"

def test_download_file_category_not_found(client, authenticated_test_user, test_analysis):
    response = client.get(f"/analyses/{test_analysis.id}/files/missing/plot.png")
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"

def test_download_file_filename_not_found(client, authenticated_test_user, test_analysis):
    response = client.get(f"/analyses/{test_analysis.id}/files/saes_plots/missing.png")
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found: missing.png"

def test_download_file_stored_file_not_found(client, authenticated_test_user, test_analysis, monkeypatch):
    async def test_get_file(file_id):
        return None

    monkeypatch.setattr(analysis_routes, "get_file", test_get_file)
    response = client.get(f"/analyses/{test_analysis.id}/files/saes_plots/plot.png")
    assert response.status_code == 404
    assert response.json()["detail"] == "Stored file not found: plot.png"

def test_download_raw_dataset_success(client, authenticated_test_user, test_analysis, monkeypatch):
    async def test_get_file(file_id):
        assert file_id == "raw-file-id"
        return b"raw,csv\n"

    monkeypatch.setattr(analysis_routes, "get_file", test_get_file)
    response = client.get(f"/analyses/{test_analysis.id}/dataset/raw")
    assert response.status_code == 200, response.text
    assert response.content == b"raw,csv\n"
    assert response.headers["content-type"].startswith("text/csv")

def test_download_raw_dataset_not_found(client, authenticated_test_user, test_analysis):
    test_analysis.raw_dataset_file_id = None
    response = client.get(f"/analyses/{test_analysis.id}/dataset/raw")
    assert response.status_code == 404
    assert response.json()["detail"] == "Raw dataset file not found"

def test_download_normalized_dataset_success(client, authenticated_test_user, test_analysis, monkeypatch):
    async def test_get_file(file_id):
        assert file_id == "normalized-file-id"
        return b"normalized,csv\n"

    monkeypatch.setattr(analysis_routes, "get_file", test_get_file)
    response = client.get(f"/analyses/{test_analysis.id}/dataset/normalized")
    assert response.status_code == 200, response.text
    assert response.content == b"normalized,csv\n"
    assert response.headers["content-type"].startswith("text/csv")

def test_download_normalized_dataset_not_found(client, authenticated_test_user, test_analysis):
    test_analysis.normalized_dataset_file_id = None
    response = client.get(f"/analyses/{test_analysis.id}/dataset/normalized")
    assert response.status_code == 404
    assert response.json()["detail"] == "Normalized dataset file not found"

def test_download_filtered_dataset_success(client, authenticated_test_user, test_analysis, monkeypatch):
    async def test_get_file(file_id):
        assert file_id == "filtered-file-id"
        return b"filtered,csv\n"

    monkeypatch.setattr(analysis_routes, "get_file", test_get_file)
    response = client.get(f"/analyses/{test_analysis.id}/dataset/filtered")
    assert response.status_code == 200, response.text
    assert response.content == b"filtered,csv\n"
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="filtered_dataset_all.csv"' in response.headers["content-disposition"]

def test_download_filtered_dataset_with_run_key(client, authenticated_test_user, test_analysis, monkeypatch):
    test_analysis.filtered_dataset_file_ids = {"A1": "filtered-a1-id"}

    async def test_get_file(file_id):
        assert file_id == "filtered-a1-id"
        return b"filtered-a1,csv\n"

    monkeypatch.setattr(analysis_routes, "get_file", test_get_file)
    response = client.get(f"/analyses/{test_analysis.id}/dataset/filtered", params={"run_key": "A1"})
    assert response.status_code == 200, response.text
    assert 'filename="filtered_dataset_A1.csv"' in response.headers["content-disposition"]

def test_download_filtered_dataset_not_found(client, authenticated_test_user, test_analysis):
    test_analysis.filtered_dataset_file_ids = {}
    response = client.get(f"/analyses/{test_analysis.id}/dataset/filtered")
    assert response.status_code == 404
    assert response.json()["detail"] == "Filtered dataset file not found"

def test_download_metrics_success(client, authenticated_test_user, test_analysis, monkeypatch):
    async def test_get_file(file_id):
        assert file_id == "metrics-file-id"
        return b"Metric,Direction\nAccuracy,maximize\n"

    monkeypatch.setattr(analysis_routes, "get_file", test_get_file)
    response = client.get(f"/analyses/{test_analysis.id}/metrics")
    assert response.status_code == 200, response.text
    assert response.content == b"Metric,Direction\nAccuracy,maximize\n"
    assert response.headers["content-type"].startswith("text/csv")

def test_download_metrics_not_found(client, authenticated_test_user, test_analysis):
    test_analysis.metrics_config_file_id = None
    response = client.get(f"/analyses/{test_analysis.id}/metrics")
    assert response.status_code == 404
    assert response.json()["detail"] == "Metrics file not found"