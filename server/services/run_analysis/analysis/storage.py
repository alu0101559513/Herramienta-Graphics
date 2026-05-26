from __future__ import annotations

from server.services.gridfs import save_file
from server.services.run_analysis.reanalyze import (
    reanalyze_with_selected_algorithms,
)


async def get_source_dataset_file_id(
    *,
    analysis,
    run_key: str,
    selected_algorithms: list[str] | None,
    run_algorithms: list[str],
) -> str | None:
    """
    Description:
        Resolve the dataset file id used for an analysis run.

        When specific algorithms are selected, a filtered dataset is generated
        (or reused) containing only those algorithms.

        Otherwise, the function tries to reuse an already filtered dataset
        associated with the current run key. If none exists, it falls back
        to the normalized dataset and finally to the raw uploaded dataset.

    Args:
        analysis:
            Analysis document containing dataset file references.

        run_key (str):
            Unique identifier representing the selected algorithms for the run.

        selected_algorithms (list[str] | None):
            Explicitly selected algorithms requested by the user.

        run_algorithms (list[str]):
            Clean normalized algorithms used in the current run.

    Returns:
        str | None:
            GridFS file id of the dataset to use for the analysis pipeline.
    """

    if selected_algorithms is not None:
        return await reanalyze_with_selected_algorithms(
            analysis=analysis,
            selected_algorithms=run_algorithms,
        )

    filtered_ids = getattr(analysis, "filtered_dataset_file_ids", None) or {}

    return (
        filtered_ids.get(run_key)
        or getattr(analysis, "normalized_dataset_file_id", None)
        or getattr(analysis, "raw_dataset_file_id", None)
    )


async def save_generated_files(
    *,
    analysis_id: str,
    run_key: str,
    files: dict[str, bytes],
    namespace: str | None = None,
) -> dict[str, str]:
    """
    Description:
        Save generated analysis files into GridFS.

        Each file is stored using a deterministic filename composed of:
            - analysis id
            - run key
            - optional namespace
            - original filename

        The returned dictionary maps original filenames to their
        corresponding GridFS file ids.

    Args:
        analysis_id (str):
            Analysis identifier.

        run_key (str):
            Unique identifier for the current analysis run.

        files (dict[str, bytes]):
            Generated files indexed by filename.

        namespace (str | None):
            Optional namespace used to separate different output groups,
            such as evolution plot histories.

    Returns:
        dict[str, str]:
            Mapping between filenames and stored GridFS file ids.
    """

    saved_files: dict[str, str] = {}

    storage_run_key = f"{run_key}_{namespace}" if namespace else run_key

    for filename, file_bytes in files.items():
        file_id = await save_file(
            f"{analysis_id}_{storage_run_key}_{filename}",
            file_bytes,
        )

        saved_files[filename] = file_id

    return saved_files
