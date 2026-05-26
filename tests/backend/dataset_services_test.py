import pytest

from server.services.dataset.detection import (
    build_header_lookup,
    detect_columns,
    detect_dataset_capabilities,
    detect_format,
    find_column,
    get_missing_fields,
    normalize_header,
)
from server.services.dataset.exceptions import DatasetFormatError, DatasetValidationError
from server.services.dataset.filtering import filter_normalized_dataset_by_algorithms
from server.services.dataset.metadata import extract_metadata, sorted_unique
from server.services.dataset.parsing import (
    build_base_row,
    get_optional_text,
    get_required_text,
    inspect_dataset,
    is_empty,
    normalize_dataset,
    parse_dataset,
    parse_float,
    parse_int,
    parse_optional_int,
    read_csv,
)
from server.services.dataset.validation import (
    require_int,
    require_number,
    require_string,
    validate_dataset,
    validate_runs,
)


SAES_CSV = b"""Algorithm,Instance,MetricName,ExecutionId,MetricValue
A1,P1,Accuracy,1,0.9
A1,P1,Accuracy,2,0.91
A2,P1,Accuracy,1,0.8
A2,P1,Accuracy,2,0.82
"""

EVOLUTION_CSV = b"""Algorithm,Fitness,Generation,ExecutionId
A1,0.1,1,1
A1,0.2,2,1
A2,0.3,1,1
A2,0.4,2,1
"""

BOTH_CSV = b"""Algorithm,Instance,MetricName,ExecutionId,MetricValue,Generation
A1,P1,Accuracy,1,0.8,1
A1,P1,Accuracy,1,0.9,2
A1,P1,Accuracy,2,0.7,1
A1,P1,Accuracy,2,0.95,2
A2,P1,Accuracy,1,0.6,1
A2,P1,Accuracy,1,0.7,2
A2,P1,Accuracy,2,0.5,1
A2,P1,Accuracy,2,0.75,2
"""


def test_normalize_header_removes_spaces_case_and_symbols():
    assert normalize_header(" Metric Value ") == "metricvalue"
    assert normalize_header("Execution-ID") == "executionid"


def test_build_header_lookup_and_find_column():
    lookup = build_header_lookup([" Algorithm ", "Metric Value"])
    assert lookup == {"algorithm": " Algorithm ", "metricvalue": "Metric Value"}
    assert find_column(lookup, ["MetricValue", "Fitness"]) == "Metric Value"
    assert find_column(lookup, ["Missing"]) is None


def test_detect_columns_finds_common_headers():
    detected = detect_columns(["Algorithm", "Instance", "MetricName", "ExecutionId", "MetricValue"])
    assert detected["algorithm"] == "Algorithm"
    assert detected["metricvalue"] == "MetricValue"


def test_get_missing_fields_returns_display_names():
    detected = {"algorithm": "Algorithm", "instance": None}
    assert get_missing_fields(detected, ("algorithm", "instance")) == ["Instance"]


def test_detect_dataset_capabilities_saes_only():
    result = detect_dataset_capabilities(
        ["Algorithm", "Instance", "MetricName", "ExecutionId", "MetricValue"]
    )
    assert result.capabilities["saes_plots"] is True
    assert result.capabilities["evolution_plots"] is False
    assert "Generation/Time/Evaluations" in result.missing_columns["evolution"]


def test_detect_dataset_capabilities_evolution_only_with_warning():
    result = detect_dataset_capabilities(["Algorithm", "Fitness", "Generation"])
    assert result.capabilities["saes_plots"] is False
    assert result.capabilities["evolution_plots"] is True
    assert result.warnings


def test_detect_dataset_capabilities_generation_and_time_warning():
    result = detect_dataset_capabilities(["Algorithm", "Fitness", "Generation", "Time"])
    assert result.capabilities["evolution_plots"] is True
    assert any("Generation and Time" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    "columns,expected",
    [
        (["Algorithm", "Instance", "MetricName", "ExecutionId", "MetricValue", "Generation"], "saes_with_evolution"),
        (["Algorithm", "Instance", "MetricName", "ExecutionId", "MetricValue"], "saes"),
        (["Algorithm", "Fitness", "Generation"], "evolution"),
    ],
)
def test_detect_format_success(columns, expected):
    assert detect_format(columns) == expected


def test_detect_format_error():
    with pytest.raises(DatasetFormatError):
        detect_format(["x", "y"])


def test_normalize_dataset_decodes_utf8_sig():
    assert normalize_dataset(b"\xef\xbb\xbfA,B\n1,2\n") == "A,B\n1,2\n"


def test_normalize_dataset_rejects_non_bytes():
    with pytest.raises(TypeError):
        normalize_dataset("bad")  # type: ignore[arg-type]


def test_read_csv_success():
    headers, rows = read_csv(SAES_CSV)
    assert headers[0] == "Algorithm"
    assert rows[0]["Algorithm"] == "A1"


def test_read_csv_rejects_invalid_utf8():
    with pytest.raises(DatasetFormatError, match="UTF-8"):
        read_csv(b"\xff\xfe\xfd")


def test_read_csv_rejects_no_header():
    with pytest.raises(DatasetFormatError, match="no header"):
        read_csv(b"")


@pytest.mark.parametrize("value", [None, "", "   "])
def test_is_empty(value):
    assert is_empty(value) is True


def test_parse_int_and_optional_int():
    assert parse_int("1.0", 2, "ExecutionId") == 1
    assert parse_optional_int("", 2, "ExecutionId") is None


def test_parse_int_errors():
    with pytest.raises(DatasetFormatError, match="Empty"):
        parse_int("", 2, "ExecutionId")
    with pytest.raises(DatasetFormatError, match="integer"):
        parse_int("abc", 2, "ExecutionId")


def test_parse_float_success_and_errors():
    assert parse_float("0.5", 2, "MetricValue") == 0.5

    with pytest.raises(DatasetFormatError, match="Empty"):
        parse_float("", 2, "MetricValue")

    with pytest.raises(DatasetFormatError, match="numeric"):
        parse_float("bad", 2, "MetricValue")

    with pytest.raises(DatasetFormatError, match="NaN"):
        parse_float("nan", 2, "MetricValue")


def test_get_required_and_optional_text():
    row = {"Algorithm": " A1 ", "Instance": ""}
    assert get_required_text(row, "Algorithm", 2, "Algorithm") == "A1"
    assert get_optional_text(row, "Instance") is None
    assert get_optional_text(row, None) is None

    with pytest.raises(DatasetFormatError, match="Missing Algorithm"):
        get_required_text(row, None, 2, "Algorithm")

    with pytest.raises(DatasetFormatError, match="Empty Algorithm"):
        get_required_text({"Algorithm": ""}, "Algorithm", 2, "Algorithm")


def test_build_base_row():
    columns = {
        "algorithm": "Algorithm",
        "instance": "Instance",
        "metricname": "MetricName",
        "executionid": "ExecutionId",
        "metricvalue": "MetricValue",
    }
    row = {
        "Algorithm": "A1",
        "Instance": "P1",
        "MetricName": "Accuracy",
        "ExecutionId": "1",
        "MetricValue": "0.9",
    }

    parsed = build_base_row(row, columns, {"saes_plots": True}, 2)
    assert parsed["algorithm"] == "A1"
    assert parsed["metricvalue"] == 0.9


def test_parse_dataset_saes_success():
    rows, capabilities = parse_dataset(SAES_CSV)
    assert len(rows) == 4
    assert capabilities["saes_plots"] is True
    assert capabilities["evolution_plots"] is False
    assert rows[0]["algorithm"] == "A1"


def test_parse_dataset_evolution_success():
    rows, capabilities = parse_dataset(EVOLUTION_CSV)
    assert capabilities["evolution_plots"] is True
    assert rows[0]["evolution_x"] == 1.0
    assert rows[0]["evolution_y"] == 0.1


def test_parse_dataset_both_success():
    rows, capabilities = parse_dataset(BOTH_CSV)
    assert capabilities["saes_plots"] is True
    assert capabilities["evolution_plots"] is True
    assert rows[0]["metricname"] == "Accuracy"
    assert rows[0]["evolution_x"] == 1.0


def test_parse_dataset_unsupported():
    with pytest.raises(DatasetFormatError, match="Unsupported dataset format"):
        parse_dataset(b"x,y\n1,2\n")


def test_inspect_dataset():
    result = inspect_dataset(BOTH_CSV)
    assert result["row_count"] == 8
    assert result["capabilities"]["saes_plots"] is True
    assert result["columns"][0] == "Algorithm"


def test_sorted_unique_filters_invalid_values():
    assert sorted_unique(["B", "A", "", None, "A", 1]) == ["A", "B"]


def test_extract_metadata_empty():
    result = extract_metadata([])
    assert result["algorithms"] == []
    assert result["runs"] == 0
    assert result["evolution"]["point_count"] == 0


def test_extract_metadata_populated():
    rows, _ = parse_dataset(BOTH_CSV)
    result = extract_metadata(rows)

    assert result["algorithms"] == ["A1", "A2"]
    assert result["problems"] == ["P1"]
    assert result["metrics"] == ["Accuracy"]
    assert result["runs"] == 2
    assert result["row_count"] == 8
    assert result["has_saes"] is True
    assert result["has_evolution"] is True
    assert result["evolution"]["x_min"] == 1.0
    assert result["evolution"]["x_max"] == 2.0


def test_filter_normalized_dataset_by_algorithms_success():
    result = filter_normalized_dataset_by_algorithms(SAES_CSV, ["A1"])
    text = result.decode()

    assert "A1" in text
    assert "A2" not in text


def test_filter_normalized_dataset_errors():
    with pytest.raises(ValueError, match="At least one algorithm"):
        filter_normalized_dataset_by_algorithms(SAES_CSV, [" "])

    with pytest.raises(ValueError, match="UTF-8"):
        filter_normalized_dataset_by_algorithms(b"\xff", ["A1"])

    with pytest.raises(ValueError, match="no header"):
        filter_normalized_dataset_by_algorithms(b"", ["A1"])

    with pytest.raises(ValueError, match="Algorithm"):
        filter_normalized_dataset_by_algorithms(b"X,Y\n1,2\n", ["A1"])

    with pytest.raises(ValueError, match="No rows remain"):
        filter_normalized_dataset_by_algorithms(SAES_CSV, ["Missing"])


def test_validate_dataset_success_saes_and_evolution():
    rows, _ = parse_dataset(BOTH_CSV)
    validate_dataset(rows)


def test_validate_dataset_empty():
    with pytest.raises(DatasetValidationError, match="empty"):
        validate_dataset([])


def test_validate_dataset_no_capabilities():
    with pytest.raises(DatasetValidationError, match="does not support"):
        validate_dataset([{"capabilities": {"saes_plots": False, "evolution_plots": False}, "algorithm": "A1"}])


def test_validate_algorithm_empty():
    with pytest.raises(DatasetValidationError, match="Algorithm cannot be empty"):
        validate_dataset([
            {
                "capabilities": {"saes_plots": False, "evolution_plots": True},
                "algorithm": "",
                "evolution_x": 1.0,
                "evolution_y": 2.0,
            }
        ])


def test_require_helpers():
    row = {"name": " x ", "n": 1, "v": 1.5}
    assert require_string(row, "name", "bad") == "x"
    assert require_int(row, "n", "bad") == 1
    assert require_number(row, "v", "bad") == 1.5

    with pytest.raises(DatasetValidationError, match="bad"):
        require_string({"name": ""}, "name", "bad")

    with pytest.raises(DatasetValidationError, match="bad"):
        require_int({"n": 1.2}, "n", "bad")

    with pytest.raises(DatasetValidationError, match="empty v"):
        require_number({"v": None}, "v", "bad")

    with pytest.raises(DatasetValidationError, match="bad"):
        require_number({"v": "x"}, "v", "bad")


def test_validate_saes_errors():
    base = {
        "capabilities": {"saes_plots": True, "evolution_plots": False},
        "algorithm": "A1",
        "instance": "P1",
        "metricname": "Accuracy",
        "executionid": 1,
        "metricvalue": 0.9,
    }

    with pytest.raises(DatasetValidationError, match="ExecutionId cannot be negative"):
        validate_dataset([{**base, "executionid": -1}])

    with pytest.raises(DatasetValidationError, match="NaN"):
        validate_dataset([{**base, "metricvalue": float("nan")}])


def test_validate_runs_errors():
    with pytest.raises(DatasetValidationError, match="At least 1 instance"):
        validate_runs({}, set())

    with pytest.raises(DatasetValidationError, match="no valid run"):
        validate_runs({}, {"P1"})

    with pytest.raises(DatasetValidationError, match="Unbalanced"):
        validate_runs({("A1", "P1", "M"): {1}, ("A2", "P1", "M"): {1, 2}}, {"P1"})

    with pytest.raises(DatasetValidationError, match="At least 2 runs"):
        validate_runs({("A1", "P1", "M"): {1}}, {"P1"})


def test_validate_evolution_requires_two_points_per_algorithm():
    rows = [
        {
            "capabilities": {"saes_plots": False, "evolution_plots": True},
            "algorithm": "A1",
            "evolution_x": 1.0,
            "evolution_y": 2.0,
        }
    ]

    with pytest.raises(DatasetValidationError, match="At least two evolution points"):
        validate_dataset(rows)