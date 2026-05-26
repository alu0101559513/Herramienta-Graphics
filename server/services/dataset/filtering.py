from __future__ import annotations

import csv
from io import StringIO

from server.services.dataset.constants import HEADER_ALIASES
from server.services.dataset.detection import build_header_lookup, find_column


def filter_normalized_dataset_by_algorithms(
    normalized_csv_bytes: bytes,
    selected_algorithms: list[str],
) -> bytes:
    """
    Description:
        Filter a normalized CSV dataset by selected algorithms.

    Args:
        normalized_csv_bytes (bytes): Normalized CSV content.
        selected_algorithms (list[str]): Algorithm names to keep.

    Returns:
        bytes: Filtered CSV content.
    """

    selected_set = {
        algorithm.strip() for algorithm in selected_algorithms if algorithm.strip()
    }

    if not selected_set:
        raise ValueError("At least one algorithm must be selected")

    try:
        text = normalized_csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Normalized dataset must be UTF-8 encoded") from error

    reader = csv.DictReader(StringIO(text))

    if not reader.fieldnames:
        raise ValueError("Normalized dataset has no header")

    lookup = build_header_lookup(reader.fieldnames)
    algorithm_column = find_column(lookup, HEADER_ALIASES["algorithm"])

    if not algorithm_column:
        raise ValueError("Normalized dataset does not contain an Algorithm column")

    filtered_rows = [
        row
        for row in reader
        if str(row.get(algorithm_column, "")).strip() in selected_set
    ]

    if not filtered_rows:
        raise ValueError("No rows remain after filtering by selected algorithms")

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames)

    writer.writeheader()
    writer.writerows(filtered_rows)

    return output.getvalue().encode("utf-8")
