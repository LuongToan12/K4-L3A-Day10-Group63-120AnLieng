from __future__ import annotations

from pathlib import Path
from typing import Any
import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Runs data quality validation using Great Expectations 1.x ephemeral context.

    Checks:
    1. Table row count between 5 and 5000.
    2. paper_id, title, text_for_embedding must not be null.
    3. paper_id must be unique.
    4. summary length must be at least 30 characters.
    """
    context = gx.get_context(mode="ephemeral")
    source_name = f"papers_source_{report_name}"
    asset_name = f"papers_asset_{report_name}"
    batch_name = f"papers_batch_{report_name}"

    data_source = context.data_sources.add_pandas(name=source_name)
    data_asset = data_source.add_dataframe_asset(name=asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe(batch_name)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=f"papers_quality_suite_{report_name}")
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    validation_result = batch.validate(suite)

    expectations_summary: list[dict[str, Any]] = []
    for item in validation_result.results:
        expectations_summary.append(
            {
                "expectation_type": item.expectation_config.type,
                "kwargs": dict(item.expectation_config.kwargs) if item.expectation_config.kwargs else {},
                "success": bool(item.success),
                "result": dict(item.result) if item.result else {},
            }
        )

    out_file = Path(settings.paths.quality_dir) / f"{report_name}_quality_report.json"
    report_payload = {
        "report_name": report_name,
        "success": bool(validation_result.success),
        "total_expectations": len(suite.expectations),
        "successful_expectations": sum(1 for r in validation_result.results if r.success),
        "unsuccessful_expectations": sum(1 for r in validation_result.results if not r.success),
        "expectations": expectations_summary,
        "evaluated_at": now_utc().isoformat(),
    }

    write_json(out_file, report_payload)

    return {
        "success": bool(validation_result.success),
        "report_name": report_name,
        "total_expectations": len(suite.expectations),
        "successful_expectations": sum(1 for r in validation_result.results if r.success),
        "unsuccessful_expectations": sum(1 for r in validation_result.results if not r.success),
        "report_path": str(out_file),
        "expectations": expectations_summary,
    }


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | str) -> dict[str, Any]:
    """Generates Freshness SLA report based on age_days and publication date."""
    total_rows = len(df)
    if total_rows == 0:
        payload = {
            "total_rows": 0,
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": False,
            "latest_published": None,
            "oldest_published": None,
            "evaluated_at": now_utc().isoformat(),
        }
        write_json(Path(report_path), payload)
        return payload

    if "age_days" in df.columns:
        stale_mask = df["age_days"] > settings.freshness_threshold_days
    elif "published" in df.columns:
        parsed_dates = pd.to_datetime(df["published"], errors="coerce", utc=True)
        now = now_utc()
        age_series = (now - parsed_dates).dt.days
        stale_mask = age_series > settings.freshness_threshold_days
    else:
        stale_mask = pd.Series([False] * total_rows)

    stale_rows = int(stale_mask.sum())
    stale_ratio = float(stale_rows / total_rows)
    is_fresh = bool(stale_ratio <= 0.25)

    latest_published = str(df["published"].max()) if "published" in df.columns and not df["published"].dropna().empty else None
    oldest_published = str(df["published"].min()) if "published" in df.columns and not df["published"].dropna().empty else None

    payload = {
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": is_fresh,
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "evaluated_at": now_utc().isoformat(),
    }

    write_json(Path(report_path), payload)
    return payload
