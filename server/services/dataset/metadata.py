from __future__ import annotations

from typing import Any

from server.services.dataset.constants import CAPABILITIES_DEFAULT


def extract_metadata(rows: list[dict]) -> dict:
    """
    Description:
        Extract metadata from parsed dataset rows.

    Args:
        rows (list[dict]): Parsed dataset rows.

    Returns:
        dict: Dataset metadata summary.
    """

    if not rows:
        return {
            "algorithms": [],
            "problems": [],
            "metrics": [],
            "runs": 0,
            "capabilities": CAPABILITIES_DEFAULT,
            "evolution": {
                "runs": 0,
                "x_min": None,
                "x_max": None,
                "generation_min": None,
                "generation_max": None,
                "time_min": None,
                "time_max": None,
                "y_min": None,
                "y_max": None,
                "point_count": 0,
            },
        }

    capabilities = rows[0].get("capabilities") or CAPABILITIES_DEFAULT

    algorithms = sorted_unique(row.get("algorithm") for row in rows)
    problems = sorted_unique(row.get("instance") for row in rows)
    metrics = sorted_unique(row.get("metricname") for row in rows)

    runs = {row["executionid"] for row in rows if row.get("executionid") is not None}

    evolution_runs = {
        row["evolution_run"] for row in rows if row.get("evolution_run") is not None
    }

    evolution_x_values = [
        row["evolution_x"] for row in rows if row.get("evolution_x") is not None
    ]

    generation_values = [
        row["generation"] for row in rows if row.get("generation") is not None
    ]

    time_values = [row["time"] for row in rows if row.get("time") is not None]

    evolution_y_values = [
        row["evolution_y"] for row in rows if row.get("evolution_y") is not None
    ]

    return {
        "algorithms": algorithms,
        "problems": problems,
        "metrics": metrics,
        "runs": len(runs or evolution_runs),
        "row_count": len(rows),
        "algorithm_count": len(algorithms),
        "problem_count": len(problems),
        "metric_count": len(metrics),
        "capabilities": capabilities,
        "has_saes": bool(capabilities.get("saes_plots")),
        "has_evolution": bool(capabilities.get("evolution_plots")),
        "evolution": {
            "runs": len(evolution_runs),
            "x_min": min(evolution_x_values) if evolution_x_values else None,
            "x_max": max(evolution_x_values) if evolution_x_values else None,
            "generation_min": min(generation_values) if generation_values else None,
            "generation_max": max(generation_values) if generation_values else None,
            "time_min": min(time_values) if time_values else None,
            "time_max": max(time_values) if time_values else None,
            "y_min": min(evolution_y_values) if evolution_y_values else None,
            "y_max": max(evolution_y_values) if evolution_y_values else None,
            "point_count": len(evolution_x_values),
        },
    }


def sorted_unique(values: Any) -> list[str]:
    """
    Description:
        Return sorted unique non-empty string values.

    Args:
        values (Any): Iterable of values.

    Returns:
        list[str]: Sorted unique strings.
    """

    return sorted(
        {value for value in values if isinstance(value, str) and value.strip()}
    )
