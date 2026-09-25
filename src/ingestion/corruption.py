from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import now_utc, write_json


def _format_text_for_embedding(row: pd.Series | dict[str, Any]) -> str:
    title = str(row.get("title") or "")
    authors = row.get("authors_joined")
    if not authors:
        authors_val = row.get("authors", [])
        authors = ", ".join(authors_val) if isinstance(authors_val, list) else str(authors_val or "")
    published = str(row.get("published") or "")
    categories = row.get("categories_joined")
    if not categories:
        cat_val = row.get("categories", [])
        categories = ", ".join(cat_val) if isinstance(cat_val, list) else str(cat_val or "")
    summary = str(row.get("summary") or "")

    return (
        f"Title: {title}\n"
        f"Authors: {authors}\n"
        f"Published: {published}\n"
        f"Categories: {categories}\n"
        f"Summary: {summary}"
    ).strip()


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulates 6 synthetic data corruption scenarios on cleaned dataframe:

    1. Drop latest records: Drops 20% of the newest papers.
    2. Blank summary: Clears summary in selected records.
    3. Inject noise: Injects meaningless corrupted noise into summary.
    4. Truncate title: Truncates title to < 8 characters.
    5. Stale date: Pushes published date 365 days back (violating Freshness SLA).
    6. Duplicate rows: Duplicates selected rows.
    """
    if df.empty:
        write_json(Path(output_log_path), {"error": "Empty dataframe provided"})
        return df

    corrupted = df.copy()
    initial_count = len(corrupted)
    log_scenarios: dict[str, Any] = {}

    # Scenario 1: Drop latest records (20% of newest)
    if "published" in corrupted.columns:
        corrupted = corrupted.sort_values(by="published", ascending=False).reset_index(drop=True)
    num_drop = max(1, int(len(corrupted) * 0.2))
    dropped_slice = corrupted.iloc[:num_drop]
    dropped_paper_ids = dropped_slice["paper_id"].tolist() if "paper_id" in dropped_slice.columns else []
    corrupted = corrupted.iloc[num_drop:].reset_index(drop=True)

    log_scenarios["drop_latest_records"] = {
        "dropped_count": num_drop,
        "dropped_paper_ids": dropped_paper_ids,
        "description": "Dropped 20% of the newest published records to simulate data staleness and ingestion loss.",
    }

    # Scenario 2: Blank summary (select 2 rows)
    blank_indices = [0, 1] if len(corrupted) > 2 else [0]
    blank_paper_ids: list[str] = []
    for idx in blank_indices:
        corrupted.at[idx, "summary"] = ""
        if "summary_chars" in corrupted.columns:
            corrupted.at[idx, "summary_chars"] = 0
        if "paper_id" in corrupted.columns:
            blank_paper_ids.append(str(corrupted.at[idx, "paper_id"]))

    log_scenarios["blank_summary"] = {
        "count": len(blank_indices),
        "affected_paper_ids": blank_paper_ids,
        "description": "Cleared summary field to empty string simulating empty ingestion.",
    }

    # Scenario 3: Inject noise (select next 2 rows)
    noise_indices = [2, 3] if len(corrupted) > 4 else [min(len(corrupted) - 1, 1)]
    noise_paper_ids: list[str] = []
    noise_prefix = "[CORRUPTED_NOISE %$#@! NULL_PTR_ERROR] "
    for idx in noise_indices:
        curr_summary = str(corrupted.at[idx, "summary"])
        corrupted.at[idx, "summary"] = noise_prefix + curr_summary
        if "summary_chars" in corrupted.columns:
            corrupted.at[idx, "summary_chars"] = len(corrupted.at[idx, "summary"])
        if "paper_id" in corrupted.columns:
            noise_paper_ids.append(str(corrupted.at[idx, "paper_id"]))

    log_scenarios["inject_noise"] = {
        "count": len(noise_indices),
        "affected_paper_ids": noise_paper_ids,
        "description": "Injected synthetic garbled tokens into summary to corrupt semantic embeddings.",
    }

    # Scenario 4: Truncate title (< 8 characters, select next 2 rows)
    trunc_indices = [4, 5] if len(corrupted) > 6 else [min(len(corrupted) - 1, 2)]
    trunc_paper_ids: list[str] = []
    for idx in trunc_indices:
        corrupted.at[idx, "title"] = "Corrupt"  # 7 characters (< 8)
        if "paper_id" in corrupted.columns:
            trunc_paper_ids.append(str(corrupted.at[idx, "paper_id"]))

    log_scenarios["truncate_title"] = {
        "count": len(trunc_indices),
        "affected_paper_ids": trunc_paper_ids,
        "description": "Truncated titles to < 8 characters ('Corrupt') to break title semantics.",
    }

    # Scenario 5: Stale date (shift date 365 days back on >= 30% of records to breach Freshness SLA)
    stale_count = max(3, int(len(corrupted) * 0.35))
    stale_indices = list(range(len(corrupted) - stale_count, len(corrupted)))
    stale_paper_ids: list[str] = []
    for idx in stale_indices:
        try:
            curr_date = pd.to_datetime(corrupted.at[idx, "published"])
            stale_date = curr_date - pd.Timedelta(days=365)
            corrupted.at[idx, "published"] = stale_date.strftime("%Y-%m-%d")
        except Exception:
            corrupted.at[idx, "published"] = "2023-01-01"

        if "age_days" in corrupted.columns:
            try:
                corrupted.at[idx, "age_days"] = int(corrupted.at[idx, "age_days"]) + 365
            except Exception:
                corrupted.at[idx, "age_days"] = 400
        if "paper_id" in corrupted.columns:
            stale_paper_ids.append(str(corrupted.at[idx, "paper_id"]))

    log_scenarios["stale_date"] = {
        "count": len(stale_indices),
        "affected_paper_ids": stale_paper_ids,
        "description": "Pushed published date 365 days back and inflated age_days to trigger Freshness SLA alert.",
    }

    # Scenario 6: Duplicate rows (duplicate 2 rows)
    dup_rows = corrupted.iloc[:2].copy()
    dup_paper_ids = dup_rows["paper_id"].tolist() if "paper_id" in dup_rows.columns else []
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)

    log_scenarios["duplicate_rows"] = {
        "count": len(dup_rows),
        "duplicated_paper_ids": dup_paper_ids,
        "description": "Duplicated rows to violate uniqueness expectations and pollute vector indexing.",
    }

    # Rebuild text_for_embedding for all rows
    corrupted["text_for_embedding"] = corrupted.apply(_format_text_for_embedding, axis=1)

    log_payload = {
        "timestamp": now_utc().isoformat(),
        "initial_row_count": initial_count,
        "final_corrupted_row_count": len(corrupted),
        "scenarios": log_scenarios,
    }

    write_json(Path(output_log_path), log_payload)

    return corrupted
