import pandas as pd
import pytest

import server.services.graphics.evolution_plots as evo


ROWS = [
    {
        "algorithm": "A1",
        "instance": "P1",
        "metricname": "Accuracy",
        "executionid": 1,
        "generation": 1,
        "time": 10,
        "evolution_x": 100,
        "evolution_y": 0.5,
    },
    {
        "algorithm": "A1",
        "instance": "P1",
        "metricname": "Accuracy",
        "executionid": 1,
        "generation": 2,
        "time": 20,
        "evolution_x": 200,
        "evolution_y": 0.7,
    },
    {
        "algorithm": "A1",
        "instance": "P1",
        "metricname": "Accuracy",
        "executionid": 2,
        "generation": 1,
        "time": 10,
        "evolution_x": 100,
        "evolution_y": 0.4,
    },
    {
        "algorithm": "A1",
        "instance": "P1",
        "metricname": "Accuracy",
        "executionid": 2,
        "generation": 2,
        "time": 20,
        "evolution_x": 200,
        "evolution_y": 0.8,
    },
    {
        "algorithm": "A2",
        "instance": "P1",
        "metricname": "Accuracy",
        "executionid": 1,
        "generation": 1,
        "time": 10,
        "evolution_x": 100,
        "evolution_y": 0.3,
    },
    {
        "algorithm": "A2",
        "instance": "P1",
        "metricname": "Accuracy",
        "executionid": 1,
        "generation": 2,
        "time": 20,
        "evolution_x": 200,
        "evolution_y": 0.6,
    },
]


def test_normalize_column_key():
    assert evo.normalize_column_key(" Generación-X ") == "generacionx"
    assert evo.normalize_column_key("Function Evaluation") == "functionevaluation"


def test_slugify():
    assert evo.slugify(" A/B C:D ") == "a_b_c_d"
    assert evo.slugify("") == "unnamed"


def test_normalize_metric_name():
    assert evo.normalize_metric_name(" Accuracy ") == "Accuracy"
    assert evo.normalize_metric_name("") == "fitness"
    assert evo.normalize_metric_name(None) == "fitness"


def test_normalize_unique_strings():
    assert evo.normalize_unique_strings([" A ", "A", "", 1, "B"]) == ["A", "B"]
    assert evo.normalize_unique_strings(None) == []


@pytest.mark.parametrize(
    "metric,direction,expected",
    [
        ("Accuracy", None, "maximize"),
        ("Error", None, "minimize"),
        ("Any", "max", "maximize"),
        ("Any", "maximizar", "maximize"),
        ("Any", "min", "minimize"),
        ("Any", "minimizar", "minimize"),
        ("Reward", "bad", "maximize"),
    ],
)
def test_infer_direction(metric, direction, expected):
    assert evo.infer_direction(metric, direction) == expected


def test_resolve_metric_direction():
    assert evo.resolve_metric_direction("Accuracy", {"Accuracy": "minimize"}) == "minimize"
    assert evo.resolve_metric_direction("Accuracy", "maximize") == "maximize"


def test_resolve_export_formats():
    assert evo.resolve_export_formats(["PNG", "pdf", "svg", "bad", 1, "png"]) == ["png", "svg"]
    assert evo.resolve_export_formats(None) == ["png"]
    assert evo.resolve_export_formats(["pdf", "bad"]) == ["png"]


def test_resolve_row_x_value():
    row = {
        "generation": 2,
        "time": 5,
        "evolution_x": 10,
        "Custom": 99,
    }

    assert evo.resolve_row_x_value(row, "Custom") == 99
    assert evo.resolve_row_x_value(row, "Generation") == 2
    assert evo.resolve_row_x_value(row, "Time") == 5
    assert evo.resolve_row_x_value(row, "Evaluations") == 10
    assert evo.resolve_row_x_value(row, "Unknown") == 10


def test_resolve_run_value():
    assert evo.resolve_run_value({"evolution_run": " 3 "}) == "3"
    assert evo.resolve_run_value({"executionid": 2}) == "2"
    assert evo.resolve_run_value({}) == "single_run"


def test_detect_available_x_columns():
    assert evo.detect_available_x_columns([{"generation": 1, "evolution_x": 2}]) == ["Generation"]
    assert evo.detect_available_x_columns([{"time": 1, "evolution_x": 2}]) == ["Time"]
    assert evo.detect_available_x_columns([{"evolution_x": 2}]) == ["EvolutionX"]
    assert evo.detect_available_x_columns([{}]) == ["EvolutionX"]


def test_resolve_x_axis_alias():
    assert evo.resolve_x_axis_alias("generation") == "Generation"
    assert evo.resolve_x_axis_alias("tiempo") == "Time"
    assert evo.resolve_x_axis_alias("evaluations") == "EvolutionX"
    assert evo.resolve_x_axis_alias("missing") is None


def test_resolve_x_columns():
    assert evo.resolve_x_columns(ROWS, x_columns=[" Custom ", "Custom"]) == ["Custom"]
    assert evo.resolve_x_columns(ROWS, x_axis="time") == ["Time"]
    assert evo.resolve_x_columns(ROWS) == ["Generation", "Time"]


def test_resolve_labels_and_title():
    assert evo.resolve_x_label(
        x_column="Generation",
        x_label="X",
        x_labels_by_column={"Generation": "Generación"},
    ) == "Generación"

    assert evo.resolve_x_label(
        x_column="Generation",
        x_label="",
        x_labels_by_column={},
    ) == "Generation"

    assert evo.resolve_y_label(
        metric="Accuracy",
        y_label="Fitness",
        y_labels_by_metric={"Accuracy": "Precisión"},
    ) == "Precisión"

    assert evo.resolve_y_label(
        metric="Accuracy",
        y_label="Fitness",
        y_labels_by_metric={},
    ) == "Accuracy"

    assert evo.resolve_y_label(
        metric="Accuracy",
        y_label="Value",
        y_labels_by_metric={},
    ) == "Value"

    assert evo.resolve_plot_title(
        title="{metric}-{instance}-{x_column}",
        metric="Accuracy",
        instance="P1",
        x_column="Generation",
    ) == "Accuracy-P1-Generation"

    assert "Curva de Convergencia" in evo.resolve_plot_title(
        title=None,
        metric="Accuracy",
        instance="P1",
        x_column="Generation",
    )


def test_rows_to_evolution_dataframe_success():
    df = evo.rows_to_evolution_dataframe(ROWS, x_column="Generation")

    assert list(df.columns) == [
        "algorithm",
        "instance",
        "metric",
        "run",
        "x_column",
        "x",
        "value",
    ]
    assert len(df) == 6
    assert df.iloc[0]["algorithm"] == "A1"


def test_rows_to_evolution_dataframe_skips_invalid_rows():
    rows = [
        {"algorithm": "A1", "evolution_y": None, "generation": 1},
        {"algorithm": "A1", "evolution_y": "bad", "generation": 1},
        {"algorithm": "A1", "evolution_y": 1.0, "generation": None, "evolution_x": None},
        {"algorithm": "A1", "evolution_y": 2.0, "generation": 1},
    ]

    df = evo.rows_to_evolution_dataframe(rows, x_column="Generation")

    assert len(df) == 1
    assert df.iloc[0]["value"] == 2.0


def test_rows_to_evolution_dataframe_errors():
    with pytest.raises(ValueError, match="No evolution data"):
        evo.rows_to_evolution_dataframe(
            [{"algorithm": "A1", "evolution_y": None, "generation": 1}],
            x_column="Generation",
        )

    with pytest.raises(ValueError, match="valid algorithms"):
        evo.rows_to_evolution_dataframe(
            [{"algorithm": "", "evolution_y": 1.0, "generation": 1}],
            x_column="Generation",
        )


def test_apply_best_so_far_maximize_and_minimize():
    df = evo.rows_to_evolution_dataframe(ROWS[:2], x_column="Generation")

    max_df = evo.apply_best_so_far(df, "maximize")
    min_df = evo.apply_best_so_far(df, "minimize")

    assert list(max_df["best_so_far"]) == [0.5, 0.7]
    assert list(min_df["best_so_far"]) == [0.5, 0.5]


def test_summarize_convergence():
    df = evo.rows_to_evolution_dataframe(ROWS, x_column="Generation")
    best_df = evo.apply_best_so_far(df, "maximize")
    summary = evo.summarize_convergence(best_df)

    assert {"mean", "median", "std", "min", "max", "count"}.issubset(summary.columns)
    assert summary["count"].max() == 2
    assert summary["std"].isna().sum() == 0


def test_add_unique_legend():
    fig, ax = evo.plt.subplots()
    ax.plot([1, 2], [1, 2], label="A")
    ax.plot([1, 2], [2, 3], label="A")

    evo.add_unique_legend(ax)

    assert ax.get_legend() is not None
    evo.plt.close(fig)


def test_plot_algorithm_summary_all_options():
    summary = pd.DataFrame(
        {
            "algorithm": ["A1", "A1"],
            "instance": ["P1", "P1"],
            "metric": ["Accuracy", "Accuracy"],
            "x": [1.0, 2.0],
            "mean": [0.5, 0.7],
            "median": [0.45, 0.75],
            "std": [0.1, 0.2],
            "min": [0.4, 0.6],
            "max": [0.6, 0.9],
            "count": [2, 2],
        }
    )

    fig, ax = evo.plt.subplots()

    evo.plot_algorithm_summary(
        ax,
        summary,
        algorithm="A1",
        color="blue",
        show_min_max=True,
        show_std=True,
        show_average=True,
        show_median=True,
    )

    assert len(ax.lines) >= 4
    evo.plt.close(fig)


def test_plot_algorithm_summary_defaults_when_all_disabled():
    summary = pd.DataFrame(
        {
            "algorithm": ["A1"],
            "instance": ["P1"],
            "metric": ["Accuracy"],
            "x": [1.0],
            "mean": [0.5],
            "median": [0.5],
            "std": [0.0],
            "min": [0.5],
            "max": [0.5],
            "count": [1],
        }
    )

    fig, ax = evo.plt.subplots()

    evo.plot_algorithm_summary(
        ax,
        summary,
        algorithm="A1",
        color="blue",
        show_min_max=False,
        show_std=False,
        show_average=False,
        show_median=False,
    )

    assert len(ax.lines) == 1
    evo.plt.close(fig)


def test_configure_axes_grid_and_no_grid():
    fig, ax = evo.plt.subplots()

    evo.configure_axes(
        ax,
        title="{metric}",
        metric="Accuracy",
        instance="P1",
        x_column="Generation",
        x_label=None,
        y_label=None,
        x_labels_by_column=None,
        y_labels_by_metric=None,
        show_grid=True,
    )

    assert ax.get_title() == "Accuracy"
    assert ax.get_xlabel() == "Generation"
    assert ax.get_ylabel() == "Accuracy"

    evo.configure_axes(
        ax,
        title=None,
        metric="Accuracy",
        instance="P1",
        x_column="Generation",
        x_label=None,
        y_label=None,
        x_labels_by_column=None,
        y_labels_by_metric=None,
        show_grid=False,
    )

    evo.plt.close(fig)


def test_plot_convergence_summary():
    df = evo.rows_to_evolution_dataframe(ROWS, x_column="Generation")
    best_df = evo.apply_best_so_far(df, "maximize")
    summary = evo.summarize_convergence(best_df)

    fig = evo.plot_convergence_summary(
        summary,
        metric="Accuracy",
        instance="P1",
        x_column="Generation",
        show_grid=True,
    )

    assert fig.axes
    evo.plt.close(fig)


def test_save_figure(tmp_path):
    fig, ax = evo.plt.subplots()
    ax.plot([1, 2], [1, 2])

    result = evo.save_figure(
        fig,
        output_dir=tmp_path,
        output_stem="plot",
        export_formats=["png", "svg"],
    )

    assert "plot.png" in result
    assert "plot.svg" in result
    assert (tmp_path / "plot.png").exists()

    evo.plt.close(fig)


def test_apply_filters():
    df = evo.rows_to_evolution_dataframe(ROWS, x_column="Generation")

    filtered = evo.apply_filters(
        df,
        selected_algorithms=["A1"],
        selected_metrics=["Accuracy"],
        selected_instances=["P1"],
    )

    assert set(filtered["algorithm"]) == {"A1"}

    empty = evo.apply_filters(df, selected_algorithms=["Missing"])
    assert empty.empty


def test_generate_evolution_plots_for_x_column_success(tmp_path):
    files, names, metadata, warnings = evo.generate_evolution_plots_for_x_column(
        rows=ROWS,
        x_column="Generation",
        output_dir=tmp_path,
        export_formats=["png"],
        selected_algorithms=None,
        selected_metrics=None,
        selected_instances=None,
        direction={"Accuracy": "maximize"},
        title="{metric}-{instance}-{x_column}",
        x_label=None,
        y_label=None,
        x_labels_by_column=None,
        y_labels_by_metric=None,
        show_grid=True,
        show_min_max=True,
        show_std=True,
        show_average=True,
        show_median=True,
        group_by_instance=True,
        group_by_metric=True,
        output_suffix="test",
    )

    assert files
    assert names
    assert metadata["metrics"] == ["Accuracy"]
    assert metadata["algorithms"] == ["A1", "A2"]
    assert metadata["x_min"] == 1.0
    assert metadata["x_max"] == 2.0
    assert warnings == []


def test_generate_evolution_plots_for_x_column_filters_empty(tmp_path):
    files, names, metadata, warnings = evo.generate_evolution_plots_for_x_column(
        rows=ROWS,
        x_column="Generation",
        output_dir=tmp_path,
        export_formats=["png"],
        selected_algorithms=["Missing"],
        selected_metrics=None,
        selected_instances=None,
        direction=None,
        title=None,
        x_label=None,
        y_label=None,
        x_labels_by_column=None,
        y_labels_by_metric=None,
        show_grid=True,
        show_min_max=True,
        show_std=True,
        show_average=True,
        show_median=True,
        group_by_instance=True,
        group_by_metric=True,
    )

    assert files == {}
    assert names == []
    assert metadata == {}
    assert "No evolution rows remain" in warnings[0]


def test_generate_evolution_plots_for_x_column_group_by_metric_warning(tmp_path):
    rows = ROWS + [
        {
            "algorithm": "A1",
            "instance": "P1",
            "metricname": "Error",
            "executionid": 1,
            "generation": 1,
            "evolution_y": 10,
        },
        {
            "algorithm": "A1",
            "instance": "P1",
            "metricname": "Error",
            "executionid": 1,
            "generation": 2,
            "evolution_y": 8,
        },
    ]

    files, names, metadata, warnings = evo.generate_evolution_plots_for_x_column(
        rows=rows,
        x_column="Generation",
        output_dir=tmp_path,
        export_formats=["png"],
        selected_algorithms=None,
        selected_metrics=None,
        selected_instances=None,
        direction=None,
        title=None,
        x_label=None,
        y_label=None,
        x_labels_by_column=None,
        y_labels_by_metric=None,
        show_grid=False,
        show_min_max=False,
        show_std=False,
        show_average=False,
        show_median=False,
        group_by_instance=False,
        group_by_metric=False,
    )

    assert files
    assert any("group_by_metric=False" in warning for warning in warnings)
    assert len(metadata["metrics"]) == 1


def test_generate_evolution_plots_success(tmp_path):
    result = evo.generate_evolution_plots(
        ROWS,
        output_dir=tmp_path,
        export_formats=["png"],
        x_columns=["Generation"],
        direction={"Accuracy": "maximize"},
        selected_algorithms=["A1"],
        selected_metrics=["Accuracy"],
        selected_instances=["P1"],
        title="{metric}",
        x_label="X",
        y_label="Y",
        x_labels_by_column={"Generation": "Gen"},
        y_labels_by_metric={"Accuracy": "Acc"},
        output_suffix="run",
    )

    assert result["files"]
    assert result["generated_files"]
    assert result["metadata"]["x_columns"] == ["Generation"]
    assert result["metadata"]["metrics"] == ["Accuracy"]
    assert result["metadata"]["algorithms"] == ["A1"]
    assert result["metadata"]["x_label"] == "X"
    assert result["metadata"]["y_label"] == "Y"
    assert result["metadata"]["output_suffix"] == "run"


def test_generate_evolution_plots_single_run_warning(tmp_path):
    single_run_rows = [row for row in ROWS if row["executionid"] == 1]

    result = evo.generate_evolution_plots(
        single_run_rows,
        output_dir=tmp_path,
        export_formats=["png"],
        x_columns=["Generation"],
    )

    assert any("Only one run" in warning for warning in result["warnings"])


def test_generate_evolution_plots_raises_when_no_files(tmp_path):
    with pytest.raises(ValueError, match="did not produce"):
        evo.generate_evolution_plots(
            [{"algorithm": "A1", "evolution_y": None}],
            output_dir=tmp_path,
            x_columns=["Generation"],
        )