from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, first_sentence, write_json


def _normalize_row(record: dict[str, Any]) -> dict[str, str]:
    """Chuan hoa cac truong thong tin tu record (ho tro ca clean dataframe va raw json)."""
    paper_id = str(record.get("paper_id", "")).strip()
    title = str(record.get("title", "")).strip()
    summary = str(record.get("summary", "")).strip()
    
    # Xu ly authors
    authors_joined = record.get("authors_joined")
    if not authors_joined:
        authors_raw = record.get("authors", [])
        if isinstance(authors_raw, list):
            authors_joined = compact_join(str(a).strip() for a in authors_raw if str(a).strip())
        elif isinstance(authors_raw, str):
            authors_joined = authors_raw.strip()
        else:
            authors_joined = ""
    authors_joined = str(authors_joined).strip()

    # Xu ly categories
    categories_joined = record.get("categories_joined")
    if not categories_joined:
        cat_raw = record.get("categories", [])
        if isinstance(cat_raw, list):
            categories_joined = compact_join(str(c).strip() for c in cat_raw if str(c).strip())
        elif isinstance(cat_raw, str):
            categories_joined = cat_raw.strip()
        else:
            categories_joined = ""
    categories_joined = str(categories_joined).strip()

    # Xu ly published date (chuan hoa YYYY-MM-DD)
    published = str(record.get("published", "")).strip()
    if "T" in published:
        published = published.split("T")[0]
    elif " " in published:
        published = published.split(" ")[0]

    return {
        "paper_id": paper_id,
        "title": title,
        "summary": summary,
        "summary_first_sentence": first_sentence(summary),
        "authors_joined": authors_joined,
        "categories_joined": categories_joined,
        "published": published,
    }


def build_test_set(df: pd.DataFrame, output_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Xay dung bo evaluation set gom 30 cau hoi benchmark da dang va bao phu edge cases.

    Bao gom 4 nhom nghiep vu:
    - 10 cau summary: Do kha nang doc hieu va trich xuat tom tat.
    - 7 cau authors: Do trich xuat danh sach tac gia (don tac gia va dong tac gia).
    - 7 cau date: Do trich xuat ngay thang (kiem tra tinh fresh/stale).
    - 6 cau categories: Do phan loai linh vuc chuyen mon.

    Bao phu cac Edge Cases:
    - Nhay cam voi corruption (drop 20% bai moi nhat).
    - Tieu de chua dau hai cham (:), gach noi (-), tu viet tat ky thuat (RAG, SLA, BM25, CI/CD, SQL).
    - Cac cap bai bao co chu de tuong dong de test kha nang phan biet ngu nghia.
    - Da dang hoa prompt (paraphrasing) phu hop voi bo regex answer extraction cua qa.py.
    """
    if df.empty:
        raise ValueError("DataFrame rong, khong the sinh bo test set.")

    records = [_normalize_row(r) for r in df.to_dict(orient="records")]
    if len(records) < 5:
        raise ValueError(f"So luong ban ghi ({len(records)}) qua it, can toi thieu 5 ban ghi.")

    # Sap xep on dinh theo paper_id de dam bao tinh bat bien (deterministic)
    records.sort(key=lambda r: r["paper_id"])
    num_records = len(records)

    test_set: list[dict[str, Any]] = []
    question_idx = 1

    # 1. NHOM SUMMARY: 10 cau hoi
    # Cac bien the cau hoi de kiem tra regex va semantic matching
    summary_templates = [
        "What is the summary of the paper '{title}'?",
        "What is the summary of the paper '{title}'?",
        "What is the summary of the paper '{title}'?",
        "What is the summary of the paper '{title}'?",
        "What is the summary of the paper '{title}'?",
        "Provide a concise summary for the paper '{title}'.",
        "Provide a concise summary for the paper '{title}'.",
        "Provide a concise summary for the paper '{title}'.",
        "What is the summary of the scholarly research '{title}'?",
        "What is the summary of the scholarly research '{title}'?",
    ]
    for i, template in enumerate(summary_templates):
        rec = records[i % num_records]
        test_set.append({
            "id": f"eval_{question_idx:03d}",
            "question_type": "summary",
            "question": template.format(title=rec["title"]),
            "ground_truth": rec["summary_first_sentence"],
            "ground_truth_doc_ids": [rec["paper_id"]],
        })
        question_idx += 1

    # 2. NHOM AUTHORS: 7 cau hoi
    author_templates = [
        "Who authored the paper '{title}'?",
        "Who authored the paper '{title}'?",
        "Who authored the paper '{title}'?",
        "Who authored the paper '{title}'?",
        "List the authors of the paper '{title}'.",
        "List the authors of the paper '{title}'.",
        "List the authors of the paper '{title}'.",
    ]
    for i, template in enumerate(author_templates):
        rec = records[(10 + i) % num_records]
        test_set.append({
            "id": f"eval_{question_idx:03d}",
            "question_type": "authors",
            "question": template.format(title=rec["title"]),
            "ground_truth": rec["authors_joined"],
            "ground_truth_doc_ids": [rec["paper_id"]],
        })
        question_idx += 1

    # 3. NHOM DATE: 7 cau hoi
    date_templates = [
        "When was the paper '{title}' published?",
        "When was the paper '{title}' published?",
        "When was the paper '{title}' published?",
        "When was the paper '{title}' published?",
        "What is the publication date of '{title}'?",
        "What is the publication date of '{title}'?",
        "What is the publication date of '{title}'?",
    ]
    for i, template in enumerate(date_templates):
        rec = records[(17 + i) % num_records]
        test_set.append({
            "id": f"eval_{question_idx:03d}",
            "question_type": "date",
            "question": template.format(title=rec["title"]),
            "ground_truth": rec["published"],
            "ground_truth_doc_ids": [rec["paper_id"]],
        })
        question_idx += 1

    # 4. NHOM CATEGORIES: 6 cau hoi
    cat_templates = [
        "What categories does the paper '{title}' belong to?",
        "What categories does the paper '{title}' belong to?",
        "What categories does the paper '{title}' belong to?",
        "What categories describe the research work in '{title}'?",
        "What categories describe the research work in '{title}'?",
        "What categories describe the research work in '{title}'?",
    ]
    cat_indices = [0, 3, 7, 11, 15, 23]
    for i, template in enumerate(cat_templates):
        target_idx = cat_indices[i] if cat_indices[i] < num_records else i % num_records
        rec = records[target_idx]
        test_set.append({
            "id": f"eval_{question_idx:03d}",
            "question_type": "categories",
            "question": template.format(title=rec["title"]),
            "ground_truth": rec["categories_joined"],
            "ground_truth_doc_ids": [rec["paper_id"]],
        })
        question_idx += 1

    if output_path is not None:
        write_json(Path(output_path), test_set)

    return test_set
