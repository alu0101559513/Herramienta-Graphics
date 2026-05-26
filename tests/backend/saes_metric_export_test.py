import csv
import io

import pytest

from server.services.graphics.saes_graphics.exporter import (
    SaesExportError,
    build_saes_row,
    clean_text,
    detect_evolution_x_column,
    detect_saes_columns,
    export_saes_dataset,
    parse_float,
    parse_int,
    read_csv,
)
from server.services.graphics.saes_graphics.metrics_config import (
    build_expected_metrics_lookup,
    generate_metrics_csv,
    get_default_metrics_direction,
    normalize_metric_name,
    parse_metrics_csv,
    resolve_metrics_direction,
)


CLASSIC_CSV = b"""Algorithm,Instance,MetricName,ExecutionId,MetricValue
A1,P1,Accuracy,1,0.8
A1,P1,Accuracy,2,0.9
"""

EVOLUTION_CSV = b"""Algorithm,Instance,MetricName,ExecutionId,MetricValue,Generation
A1,P1,Accuracy,1,0.7,1
A1,P1,Accuracy,1,0.9,2
A1,P1,Accuracy,2,0.6,1
A1,P1,Accuracy,2,0.95,2
"""


def decode_csv(data: bytes):
    return list(csv.DictReader(io.StringIO(data.decode())))


def test_normalize_metric_name():
    assert normalize_metric_name(" accuracy ") == "ACCURACY"


def test_get_default_metrics_direction():
    assert get_default_metrics_direction(["Accuracy", "Error", "Custom", "", 1]) == {
        "Accuracy": "maximize",
        "Error": "minimize",
        "Custom": "maximize",
    }


def test_build_expected_metrics_lookup():
    assert build_expected_metrics_lookup([" Accuracy ", "Error"]) == {
        "ACCURACY": " Accuracy ",
        "ERROR": "Error",
    }


def test_parse_metrics_csv_success():
    csv_bytes = b"MetricName,Maximize\nAccuracy,false\nError,true\n"
    result = parse_metrics_csv(csv_bytes, ["Accuracy", "Error"])

    assert result == {"Accuracy": "minimize", "Error": "maximize"}


def test_parse_metrics_csv_errors():
    with pytest.raises(ValueError, match="encoding"):
        parse_metrics_csv(b"\xff", ["Accuracy"])

    with pytest.raises(ValueError, match="empty"):
        parse_metrics_csv(b"", ["Accuracy"])

    with pytest.raises(ValueError, match="MetricName"):
        parse_metrics_csv(b"Metric,Direction\nAccuracy,maximize\n", ["Accuracy"])

    with pytest.raises(ValueError, match="MetricName cannot be empty"):
        parse_metrics_csv(b"MetricName,Maximize\n,true\n", ["Accuracy"])

    with pytest.raises(ValueError, match="Unknown metric"):
        parse_metrics_csv(b"MetricName,Maximize\nOther,true\n", ["Accuracy"])

    with pytest.raises(ValueError, match="Invalid Maximize"):
        parse_metrics_csv(b"MetricName,Maximize\nAccuracy,yes\n", ["Accuracy"])


def test_resolve_metrics_direction_defaults_frontend_and_csv():
    assert resolve_metrics_direction(["Accuracy"]) == {"Accuracy": "maximize"}

    assert resolve_metrics_direction(
        ["Accuracy"],
        frontend_config={"accuracy": "minimize"},
    ) == {"Accuracy": "minimize"}

    assert resolve_metrics_direction(
        ["Accuracy"],
        csv_bytes=b"MetricName,Maximize\nAccuracy,false\n",
    ) == {"Accuracy": "minimize"}


def test_resolve_metrics_direction_errors():
    with pytest.raises(ValueError, match="Unknown metric"):
        resolve_metrics_direction(["Accuracy"], frontend_config={"Other": "maximize"})

    with pytest.raises(ValueError, match="Invalid direction"):
        resolve_metrics_direction(["Accuracy"], frontend_config={"Accuracy": "up"})


def test_generate_metrics_csv_success():
    result = generate_metrics_csv({"Accuracy": "maximize", "Error": "minimize"})
    assert b"MetricName,Maximize" in result
    assert b"Accuracy,True" in result
    assert b"Error,False" in result


def test_generate_metrics_csv_invalid_direction():
    with pytest.raises(ValueError, match="Invalid direction"):
        generate_metrics_csv({"Accuracy": "up"})


def test_exporter_read_csv_success():
    headers, rows = read_csv(CLASSIC_CSV)
    assert headers == ["Algorithm", "Instance", "MetricName", "ExecutionId", "MetricValue"]
    assert rows[0]["Algorithm"] == "A1"


def test_exporter_read_csv_errors():
    with pytest.raises(TypeError):
        read_csv("bad")  # type: ignore[arg-type]

    with pytest.raises(SaesExportError, match="UTF-8"):
        read_csv(b"\xff")

    with pytest.raises(SaesExportError, match="no header"):
        read_csv(b"")

    with pytest.raises(SaesExportError, match="no rows"):
        read_csv(b"Algorithm,Instance\n")


def test_detect_saes_columns_success_and_error():
    detected = detect_saes_columns(["Algorithm", "Instance", "MetricName", "ExecutionId", "MetricValue"])
    assert detected["Algorithm"] == "Algorithm"

    with pytest.raises(SaesExportError, match="Missing required column"):
        detect_saes_columns(["Algorithm"])


def test_detect_evolution_x_column():
    assert detect_evolution_x_column(["Algorithm", "Generation"]) == "Generation"
    assert detect_evolution_x_column(["Algorithm"]) is None


def test_exporter_parse_float_and_int():
    assert parse_float("1.5", "MetricValue", 2) == 1.5
    assert parse_int("2.0", "ExecutionId", 2) == 2

    with pytest.raises(SaesExportError, match="Empty"):
        parse_float("", "MetricValue", 2)

    with pytest.raises(SaesExportError, match="numeric"):
        parse_float("bad", "MetricValue", 2)

    with pytest.raises(SaesExportError, match="integer"):
        parse_int("bad", "ExecutionId", 2)


def test_clean_text():
    assert clean_text(" A1 ", "Algorithm", 2) == "A1"

    with pytest.raises(SaesExportError, match="Empty Algorithm"):
        clean_text("", "Algorithm", 2)


def test_build_saes_row():
    columns = {
        "Algorithm": "Algorithm",
        "Instance": "Instance",
        "MetricName": "MetricName",
        "ExecutionId": "ExecutionId",
        "MetricValue": "MetricValue",
    }
    raw = {
        "Algorithm": "A1",
        "Instance": "P1",
        "MetricName": "Accuracy",
        "ExecutionId": "1",
        "MetricValue": "0.9",
    }

    assert build_saes_row(raw, columns, 2) == {
        "Algorithm": "A1",
        "Instance": "P1",
        "MetricName": "Accuracy",
        "ExecutionId": 1,
        "MetricValue": 0.9,
    }


def test_export_saes_dataset_classic():
    rows = decode_csv(export_saes_dataset(CLASSIC_CSV))
    assert len(rows) == 2
    assert rows[0]["Algorithm"] == "A1"


def test_export_saes_dataset_evolution_takes_final_points():
    rows = decode_csv(export_saes_dataset(EVOLUTION_CSV))
    assert len(rows) == 2
    assert rows[0]["MetricValue"] == "0.9"
    assert rows[1]["MetricValue"] == "0.95"