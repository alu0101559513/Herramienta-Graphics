from __future__ import annotations

from server.services.dataset.filtering import filter_normalized_dataset_by_algorithms
from server.services.gridfs import get_file, save_file
from server.services.run_analysis.analysis.modules import build_algorithm_run_key


def get_source_dataset_file_id(analysis) -> str | None:
    """
    Description:
        Resolve the base dataset file id used to create filtered datasets.

    Args:
        analysis:
            Analysis document.

    Returns:
        str | None:
            Normalized dataset file id when available, otherwise raw dataset file id.
    """

    return getattr(analysis, "normalized_dataset_file_id", None) or getattr(
        analysis,
        "raw_dataset_file_id",
        None,
    )


def clean_algorithms(selected_algorithms: list[str]) -> list[str]:
    """
    Description:
        Normalize selected algorithm names.

    Args:
        selected_algorithms (list[str]):
            Raw selected algorithm names.

    Returns:
        list[str]:
            Clean non-empty algorithm names.
    """

    return [
        value.strip()
        for value in selected_algorithms
        if isinstance(value, str) and value.strip()
    ]


async def reanalyze_with_selected_algorithms(
    analysis,
    selected_algorithms: list[str],
) -> str:
    """
    Description:
        Create or reuse a filtered dataset containing only selected algorithms.

    Args:
        analysis:
            Analysis document.

        selected_algorithms (list[str]):
            Algorithms to keep in the filtered dataset.

    Returns:
        str:
            Filtered dataset file id.
    """

    algorithms = clean_algorithms(selected_algorithms)

    if not algorithms:
        raise ValueError("At least one algorithm must be selected")

    source_dataset_file_id = get_source_dataset_file_id(analysis)

    if not source_dataset_file_id:
        raise ValueError("Dataset file not found")

    dataset_bytes = await get_file(source_dataset_file_id)

    if not dataset_bytes:
        raise ValueError("Dataset is empty")

    run_key = build_algorithm_run_key(
        selected_algorithms=algorithms,
        all_algorithms=list(getattr(analysis, "algorithms", []) or []),
    )

    filtered_files_by_run = dict(
        getattr(analysis, "filtered_dataset_file_ids", None) or {}
    )

    existing_file_id = filtered_files_by_run.get(run_key)

    if existing_file_id:
        analysis.selected_algorithms_last_run = algorithms
        analysis.current_run_key = run_key
        await analysis.save()
        return existing_file_id

    filtered_dataset_bytes = filter_normalized_dataset_by_algorithms(
        normalized_csv_bytes=dataset_bytes,
        selected_algorithms=algorithms,
    )

    filtered_dataset_file_id = await save_file(
        f"{analysis.id}_{run_key}_filtered_dataset.csv",
        filtered_dataset_bytes,
    )

    filtered_files_by_run[run_key] = filtered_dataset_file_id

    analysis.filtered_dataset_file_ids = filtered_files_by_run
    analysis.selected_algorithms_last_run = algorithms
    analysis.current_run_key = run_key

    await analysis.save()

    return filtered_dataset_file_id
