from typing import Any

from pydantic import BaseModel, Field, field_validator


class AnalysisCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class AnalysisUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class DatasetCapabilities(BaseModel):
    saes_plots: bool = False
    saes_reports: bool = False
    notebooks: bool = False
    evolution_plots: bool = False


class DatasetInspectionResponse(BaseModel):
    capabilities: DatasetCapabilities
    columns: list[str] = Field(default_factory=list)
    row_count: int = 0


class EvolutionPlotSetResponse(BaseModel):
    signature: str
    label: str | None = None
    created_at: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    evolution_plots: dict[str, str] = Field(default_factory=dict)
    evolution_metadata: dict[str, Any] = Field(default_factory=dict)
    evolution_plot_warnings: list[str] = Field(default_factory=list)


class AnalysisRunOutputsResponse(BaseModel):
    selected_algorithms: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    categories: dict[str, list[str]] = Field(default_factory=dict)
    evolution_plot_sets: dict[str, EvolutionPlotSetResponse] = Field(
        default_factory=dict
    )


class AnalysisResponse(BaseModel):
    id: str
    user_id: str

    name: str
    description: str | None = None

    raw_dataset_file_id: str | None = None
    raw_dataset_filename: str | None = None
    normalized_dataset_file_id: str | None = None
    filtered_dataset_file_ids: dict[str, str] = Field(default_factory=dict)

    metrics_config_file_id: str | None = None
    metrics_direction: dict[str, str] = Field(default_factory=dict)

    dataset_capabilities: dict[str, bool] = Field(default_factory=dict)

    algorithms: list[str] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)

    num_runs: int | None = None
    evolution_metadata: dict[str, Any] = Field(default_factory=dict)

    selected_algorithms_last_run: list[str] = Field(default_factory=list)
    current_run_key: str = "all"

    enabled_modules: list[str] = Field(default_factory=list)
    outputs: dict[str, Any] = Field(default_factory=dict)

    plot_export_formats: list[str] = Field(default_factory=lambda: ["png"])

    status: str

    created_at: str
    updated_at: str


class AnalysisReanalyzeRequest(BaseModel):
    selected_algorithms: list[str] = Field(default_factory=list)
    modules: list[str] | None = None

    selected_plot_types: list[str] | None = None

    evolution_title: str | None = None
    evolution_x_columns: list[str] | None = None

    evolution_x_label: str | None = None
    evolution_y_label: str | None = None

    evolution_x_labels_by_column: dict[str, str] | None = None
    evolution_y_labels_by_metric: dict[str, str] | None = None

    evolution_selected_algorithms: list[str] | None = None
    evolution_selected_metrics: list[str] | None = None
    evolution_selected_instances: list[str] | None = None

    evolution_show_grid: bool | None = None
    evolution_show_min_max: bool | None = None
    evolution_show_std: bool | None = None
    evolution_show_average: bool | None = None
    evolution_show_median: bool | None = None

    evolution_group_by_instance: bool | None = None
    evolution_group_by_metric: bool | None = None

    @field_validator(
        "selected_algorithms",
        "modules",
        "selected_plot_types",
        "evolution_x_columns",
        "evolution_selected_algorithms",
        "evolution_selected_metrics",
        "evolution_selected_instances",
    )
    @classmethod
    def normalize_string_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None

        cleaned: list[str] = []

        for item in value:
            if not isinstance(item, str):
                continue

            normalized = item.strip()

            if normalized and normalized not in cleaned:
                cleaned.append(normalized)

        return cleaned

    @field_validator(
        "evolution_x_labels_by_column",
        "evolution_y_labels_by_metric",
    )
    @classmethod
    def normalize_string_dicts(
        cls, value: dict[str, str] | None
    ) -> dict[str, str] | None:
        if value is None:
            return None

        cleaned: dict[str, str] = {}

        for key, item in value.items():
            if not isinstance(key, str) or not isinstance(item, str):
                continue

            clean_key = key.strip()
            clean_value = item.strip()

            if clean_key and clean_value:
                cleaned[clean_key] = clean_value

        return cleaned
