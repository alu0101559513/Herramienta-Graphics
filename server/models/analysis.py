from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from beanie import Document, Indexed, PydanticObjectId, Replace, before_event
from pydantic import Field


class Analysis(Document):
    """
    Description:
        Analysis document persisted in MongoDB.

        Stores dataset references, detected metadata, available capabilities,
        generated output references and execution state.

    Args:
        None.

    Returns:
        Analysis:
            Beanie document instance.
    """

    user_id: Annotated[PydanticObjectId, Indexed()]

    name: str
    description: str | None = None

    raw_dataset_file_id: str | None = None
    raw_dataset_filename: str | None = None
    normalized_dataset_file_id: str | None = None
    filtered_dataset_file_ids: dict[str, str] = Field(default_factory=dict)

    metrics_config_file_id: str | None = None
    metrics_direction: dict[str, str] = Field(default_factory=dict)

    dataset_capabilities: dict[str, bool] = Field(
        default_factory=lambda: {
            "saes_plots": False,
            "saes_reports": False,
            "notebooks": False,
            "evolution_plots": False,
        }
    )

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

    status: str = "created"

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        """
        Description:
            Beanie configuration for the analysis collection.

        Args:
            None.

        Returns:
            Settings:
                Embedded Beanie settings class.
        """

        name = "analyses"

    @before_event(Replace)
    def update_timestamp(self) -> None:
        """
        Description:
            Refresh the `updated_at` timestamp before replacing the document.

        Args:
            self (Analysis):
                Current analysis document.

        Returns:
            None:
                Mutates the current instance timestamp.
        """

        self.updated_at = datetime.now(timezone.utc)
