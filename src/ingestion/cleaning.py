from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime | date) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    if not records:
        return pd.DataFrame()

    ref_date = run_date.date() if isinstance(run_date, datetime) else run_date

    cleaned_rows: list[dict[str, Any]] = []
    for r in records:
        paper_id = normalize_whitespace(r.paper_id)
        title = normalize_whitespace(r.title)
        summary = normalize_whitespace(r.summary)
        authors = [normalize_whitespace(a) for a in r.authors if normalize_whitespace(a)]
        categories = [normalize_whitespace(c) for c in r.categories if normalize_whitespace(c)]
        primary_category = normalize_whitespace(r.primary_category) or (categories[0] if categories else "General")

        published_str = normalize_whitespace(r.published)
        try:
            pub_date = datetime.strptime(published_str[:10], "%Y-%m-%d").date()
        except Exception:
            pub_date = ref_date

        updated_str = normalize_whitespace(r.updated) or published_str
        age_days = max(0, (ref_date - pub_date).days)

        authors_joined = compact_join(authors, sep=", ")
        categories_joined = compact_join(categories, sep=", ")
        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published_str}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published_str,
                "updated": updated_str,
                "abs_url": normalize_whitespace(r.abs_url),
                "pdf_url": normalize_whitespace(r.pdf_url),
                "comment": normalize_whitespace(r.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(cleaned_rows)

    # Filter out empty or null paper_id or title
    df = df[df["paper_id"].astype(bool) & df["title"].astype(bool)]

    # Deduplicate by paper_id, keeping the first occurrence
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Sort deterministically
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    return df
