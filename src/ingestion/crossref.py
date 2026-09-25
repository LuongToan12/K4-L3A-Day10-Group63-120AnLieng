from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []
    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue
        titles = item.get("title", [])
        title = normalize_whitespace(titles[0]) if titles else ""
        if not title:
            continue

        abstract = item.get("abstract", "")
        summary = normalize_whitespace(re.sub(r"<[^>]+>", "", abstract))

        authors: list[str] = []
        for a in item.get("author", []):
            given = a.get("given", "").strip()
            family = a.get("family", "").strip()
            full_name = f"{given} {family}".strip() if given or family else a.get("name", "").strip()
            if full_name:
                authors.append(full_name)

        categories = [normalize_whitespace(c) for c in item.get("subject", []) if c]
        primary_category = categories[0] if categories else "General"

        date_parts = item.get("published", {}).get("date-parts", [[]])[0]
        if len(date_parts) >= 3:
            published = f"{date_parts[0]:04d}-{date_parts[1]:02d}-{date_parts[2]:02d}"
        elif len(date_parts) == 2:
            published = f"{date_parts[0]:04d}-{date_parts[1]:02d}-01"
        elif len(date_parts) == 1:
            published = f"{date_parts[0]:04d}-01-01"
        else:
            created_dt = item.get("created", {}).get("date-time", "")
            published = created_dt[:10] if created_dt else "2026-01-01"

        updated = published
        url = item.get("URL", f"https://doi.org/{doi}")

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=url,
                comment=f"Crossref record {doi}",
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records."""
    payload = None
    if settings.refresh_source:
        try:
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {"User-Agent": "VinUni-AI-Day10/1.0 (mailto:student@vinuni.edu.vn)"}
            resp = requests.get(
                "https://api.crossref.org/works",
                params=params,
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 200:
                payload = resp.json()
                write_json(settings.paths.raw_api_response, payload)
        except Exception:
            payload = None

    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        elif settings.paths.raw_records_json.exists():
            return load_raw_records(settings.paths.raw_records_json)
        else:
            raise FileNotFoundError(
                f"No source records or snapshot found at {settings.paths.raw_api_response}"
            )

    records = parse_crossref_payload(payload)
    records_dict = [
        {
            "paper_id": r.paper_id,
            "title": r.title,
            "summary": r.summary,
            "authors": r.authors,
            "categories": r.categories,
            "primary_category": r.primary_category,
            "published": r.published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
        }
        for r in records
    ]
    write_json(settings.paths.raw_records_json, records_dict)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    raw_list = read_json(path)
    return [PaperRecord(**item) for item in raw_list]
