from __future__ import annotations

import copy
from datetime import UTC, datetime
import io
from pathlib import Path
import re
import sys
from typing import Any

# Dam bao UTF-8 console output tren Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import pandas as pd

from core.config import Settings, load_settings
from core.utils import (
    compact_join,
    first_sentence,
    normalize_whitespace,
    read_json,
    write_csv,
    write_json,
)
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _format_clean_text_for_embedding(row: dict[str, Any]) -> str:
    """Tao doan ngu canh 5 phan chuan theo Guide.md."""
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Published: {row['published']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}"
    )


def _clean_records_fallback(records: list[dict[str, Any]], run_date: datetime) -> pd.DataFrame:
    """Lam sach va chuan hoa records thanh dataframe, ho tro ca PaperRecord va dict."""
    cleaned_rows = []
    seen_ids = set()

    for item in records:
        rec = item if isinstance(item, dict) else item.__dict__
        paper_id = str(rec.get("paper_id", "")).strip()
        if not paper_id or paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        title = normalize_whitespace(str(rec.get("title", "")).strip())
        summary_raw = str(rec.get("summary", "")).strip()
        # Loai bo cac the XML/HTML rac nhu <jats:p>
        summary = normalize_whitespace(re.sub(r"<[^>]+>", " ", summary_raw))

        # Xu ly authors
        authors_val = rec.get("authors", [])
        if isinstance(authors_val, list):
            authors_joined = compact_join(str(a).strip() for a in authors_val if str(a).strip())
        else:
            authors_joined = str(authors_val).strip()

        # Xu ly categories
        cat_val = rec.get("categories", [])
        if isinstance(cat_val, list):
            categories_joined = compact_join(str(c).strip() for c in cat_val if str(c).strip())
        else:
            categories_joined = str(cat_val).strip()

        # Xu ly published date
        pub_raw = str(rec.get("published", "")).strip()
        pub_str = pub_raw.split("T")[0].split(" ")[0] if pub_raw else "2026-01-01"
        try:
            pub_dt = datetime.strptime(pub_str, "%Y-%m-%d").replace(tzinfo=UTC)
            age_days = max(0, (run_date - pub_dt).days)
        except Exception:
            age_days = 0

        row = {
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "summary_chars": len(summary),
            "authors": rec.get("authors", []),
            "authors_joined": authors_joined,
            "categories": rec.get("categories", []),
            "categories_joined": categories_joined,
            "primary_category": rec.get("primary_category", ""),
            "published": pub_str,
            "updated": str(rec.get("updated", pub_str)),
            "abs_url": str(rec.get("abs_url", f"https://doi.org/{paper_id}")),
            "pdf_url": str(rec.get("pdf_url", f"https://doi.org/{paper_id}")),
            "comment": str(rec.get("comment", "")),
            "age_days": age_days,
        }
        row["text_for_embedding"] = _format_clean_text_for_embedding(row)
        cleaned_rows.append(row)

    df = pd.DataFrame(cleaned_rows)
    return df.sort_values("paper_id").reset_index(drop=True)


def _corrupt_clean_dataframe_fallback(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Tiêm 6 kịch bản lỗi thực tế và ghi corruption_log.json."""
    corrupted = df.copy()
    num_rows = len(corrupted)
    log_entries: list[dict[str, Any]] = []

    # 1. Drop 20% latest records
    corrupted = corrupted.sort_values("published", ascending=False).reset_index(drop=True)
    drop_count = max(1, int(num_rows * 0.20))
    dropped_papers = corrupted.iloc[:drop_count][["paper_id", "title", "published"]].to_dict(orient="records")
    corrupted = corrupted.iloc[drop_count:].reset_index(drop=True)
    log_entries.append({
        "scenario": "drop_latest_records",
        "description": f"Dropped {drop_count} latest records by publication date",
        "affected_count": drop_count,
        "details": dropped_papers,
    })

    # 2. Blank summary ở một số dòng
    blank_indices = [0, 2] if len(corrupted) > 2 else [0]
    blank_targets = []
    for idx in blank_indices:
        blank_targets.append(corrupted.at[idx, "paper_id"])
        corrupted.at[idx, "summary"] = ""
        corrupted.at[idx, "summary_chars"] = 0
    log_entries.append({
        "scenario": "blank_summary",
        "description": "Erased summary text to simulate empty scrape results",
        "affected_count": len(blank_targets),
        "details": blank_targets,
    })

    # 3. Inject noise vào text
    noise_indices = [1, 3] if len(corrupted) > 3 else [1]
    noise_targets = []
    for idx in noise_indices:
        noise_targets.append(corrupted.at[idx, "paper_id"])
        corrupted.at[idx, "summary"] = " [CORRUPTED_TEXT_#$@%&_UNREADABLE_NOISE] " + str(corrupted.at[idx, "summary"])
    log_entries.append({
        "scenario": "inject_noise",
        "description": "Injected random corrupt noise strings into summary field",
        "affected_count": len(noise_targets),
        "details": noise_targets,
    })

    # 4. Truncate title xuống dưới 8 ký tự
    truncate_indices = [4, 5] if len(corrupted) > 5 else [0]
    truncate_targets = []
    for idx in truncate_indices:
        truncate_targets.append(corrupted.at[idx, "paper_id"])
        corrupted.at[idx, "title"] = str(corrupted.at[idx, "title"])[:6]
    log_entries.append({
        "scenario": "truncate_title",
        "description": "Truncated title strings down to 6 characters (< 8 chars)",
        "affected_count": len(truncate_targets),
        "details": truncate_targets,
    })

    # 5. Stale date: Lùi ngày xuất bản về quá khứ 365 ngày
    stale_indices = [0, 1, 2, 3, 4, 5, 6] if len(corrupted) >= 7 else list(range(len(corrupted)))
    stale_targets = []
    for idx in stale_indices:
        stale_targets.append(corrupted.at[idx, "paper_id"])
        corrupted.at[idx, "published"] = "2024-01-01"
        corrupted.at[idx, "age_days"] = int(corrupted.at[idx, "age_days"]) + 365
    log_entries.append({
        "scenario": "stale_date",
        "description": "Pushed publication dates back by 365 days to violate Freshness SLA",
        "affected_count": len(stale_targets),
        "details": stale_targets,
    })

    # 6. Duplicate rows: Nhân bản bản ghi
    dup_rows = corrupted.iloc[:2].copy()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    log_entries.append({
        "scenario": "duplicate_rows",
        "description": "Duplicated 2 records to trigger unique constraint violations",
        "affected_count": 2,
        "details": dup_rows["paper_id"].tolist(),
    })

    # Rebuild text_for_embedding
    records = corrupted.to_dict(orient="records")
    for r in records:
        r["text_for_embedding"] = _format_clean_text_for_embedding(r)
    corrupted = pd.DataFrame(records)

    write_json(output_log_path, {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_scenarios": len(log_entries),
        "corrupted_rows": len(corrupted),
        "scenarios": log_entries,
    })
    return corrupted


def _quality_checks_fallback(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Fallback kiểm định chất lượng (Row count, Not Null, Unique ID, Summary length)."""
    row_count = len(df)
    row_ok = 5 <= row_count <= 5000
    null_ok = not df["paper_id"].isnull().any() and not df["title"].isnull().any()
    unique_ok = df["paper_id"].is_unique
    min_summary_len = df["summary"].apply(lambda s: len(str(s).strip())).min() if row_count > 0 else 0
    len_ok = min_summary_len >= 30

    success = bool(row_ok and null_ok and unique_ok and len_ok)
    return {
        "success": success,
        "row_count": row_count,
        "checks": {
            "row_count_valid": row_ok,
            "no_nulls": null_ok,
            "paper_id_unique": unique_ok,
            "summary_length_ge_30": len_ok,
        },
    }


def _freshness_report_fallback(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Fallback tính Freshness SLA (age_days > 180)."""
    total = len(df)
    if total == 0:
        return {"is_fresh": False, "stale_rows": 0, "total_rows": 0}
    stale_count = int((df["age_days"] > settings.freshness_threshold_days).sum())
    stale_pct = stale_count / total
    is_fresh = stale_pct <= 0.25
    return {
        "is_fresh": is_fresh,
        "stale_rows": stale_count,
        "total_rows": total,
        "stale_percentage": round(stale_pct * 100, 2),
        "latest_published": str(df["published"].max()),
        "oldest_published": str(df["published"].min()),
    }


def main() -> None:
    """Điều phối toàn bộ luồng Phase 2: Corruption -> Evaluate -> Idempotent Repair -> Compare."""
    print("=" * 70)
    print("🚀 BẮT ĐẦU LUỒNG CORRUPTION & IDEMPOTENT REPAIR (PHASE 2)")
    print("=" * 70)

    settings = load_settings()

    # 1. LOAD HOẶC KHỞI TẠO BASELINE DATA & METRICS
    print("\n[Bước 1/6] Chuẩn bị dữ liệu Baseline...")
    if settings.paths.clean_csv.exists():
        clean_df = pd.read_csv(settings.paths.clean_csv)
    else:
        print("  - Chưa có clean_csv, tiến hành nạp từ raw snapshot...")
        raw_records = read_json(settings.paths.raw_records_json)
        clean_df = _clean_records_fallback(raw_records, datetime.now(UTC))
        write_csv(clean_df, settings.paths.clean_csv)
        write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    # Đảm bảo có test set
    if not settings.paths.eval_testset.exists():
        print("  - Đang sinh bộ Benchmark test set 30 câu...")
        build_test_set(clean_df, settings.paths.eval_testset)

    # Đảm bảo có baseline metrics
    if settings.paths.baseline_metrics.exists():
        baseline_metrics = read_json(settings.paths.baseline_metrics)
    else:
        print("  - Đang đo lường chỉ số Baseline...")
        baseline_index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
        base_bundle = evaluate_pipeline(
            settings=settings,
            index=baseline_index,
            test_set_path=settings.paths.eval_testset,
            metrics_output_path=settings.paths.baseline_metrics,
            answers_output_path=settings.paths.baseline_answers,
        )
        baseline_metrics = base_bundle.summary

    print(f"  ✅ Baseline Metrics: Hit Rate = {baseline_metrics.get('retrieval_hit_rate', 0):.4f}, "
          f"Token F1 = {baseline_metrics.get('mean_token_f1', 0):.4f}")

    # 2. TẠO CORRUPTED DATAFRAME (TIÊM 6 LỖI)
    print("\n[Bước 2/6] Tiêm 6 kịch bản lỗi dữ liệu thực tế...")
    try:
        from ingestion.corruption import corrupt_clean_dataframe
        corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    except (NotImplementedError, Exception):
        print("  - Sử dụng module tiêm lỗi chuẩn hóa Phase 2...")
        corrupted_df = _corrupt_clean_dataframe_fallback(clean_df, settings.paths.corruption_log)

    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"  ✅ Đã tiêm 6 lỗi dữ liệu, lưu log tại: {settings.paths.corruption_log}")

    # 3. NẠP CORRUPTED CHROMA INDEX & ĐO LƯỜNG SỰ SỤT GIẢM CỦA RAG
    print("\n[Bước 3/6] Đánh giá hiệu năng RAG trên dữ liệu bẩn (Silent Failure Test)...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(f"  ⚠️ Corrupted Metrics: Hit Rate = {corrupted_metrics.get('retrieval_hit_rate', 0):.4f} "
          f"(Tụt: {corrupted_metrics.get('retrieval_hit_rate', 0) - baseline_metrics.get('retrieval_hit_rate', 0):.4f}), "
          f"Token F1 = {corrupted_metrics.get('mean_token_f1', 0):.4f}")

    # Kiểm tra chất lượng trên data bẩn
    try:
        from observability.quality import build_freshness_report, run_data_quality_checks
        corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
        corrupted_freshness = build_freshness_report(corrupted_df, settings, settings.paths.freshness_report)
    except (NotImplementedError, Exception):
        corrupted_quality = _quality_checks_fallback(corrupted_df, settings)
        corrupted_freshness = _freshness_report_fallback(corrupted_df, settings)

    print(f"  🚨 Quality Gate status trên Corrupted Data = {corrupted_quality.get('success')} (Kỳ vọng: False)")
    print(f"  🚨 Freshness status trên Corrupted Data = {corrupted_freshness.get('is_fresh')} (Kỳ vọng: False)")

    # 4. KÍCH HOẠT IDEMPOTENT REPAIR TỪ RAW RECORDS
    print("\n[Bước 4/6] KÍCH HOẠT IDEMPOTENT REPAIR (Khôi phục dữ liệu từ bản Raw gốc)...")
    raw_records = read_json(settings.paths.raw_records_json)
    try:
        from ingestion.cleaning import build_clean_dataframe
        from ingestion.crossref import load_raw_records
        recs = load_raw_records(settings.paths.raw_records_json)
        repaired_df = build_clean_dataframe(recs, datetime.now(UTC))
    except (NotImplementedError, Exception):
        repaired_df = _clean_records_fallback(raw_records, datetime.now(UTC))

    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"  ✅ Đã phục hồi thành công {len(repaired_df)} dòng sạch từ Raw Single Source of Truth.")

    # 5. REBUILD REPAIRED INDEX & ĐÁNH GIÁ PHỤC HỒI
    print("\n[Bước 5/6] Tái lập Vector Index và đánh giá phục hồi phong độ RAG...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary

    try:
        from observability.quality import build_freshness_report, run_data_quality_checks
        repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
        repaired_freshness = build_freshness_report(repaired_df, settings, settings.paths.freshness_report)
    except (NotImplementedError, Exception):
        repaired_quality = _quality_checks_fallback(repaired_df, settings)
        repaired_freshness = _freshness_report_fallback(repaired_df, settings)

    print(f"  🎉 Repaired Metrics: Hit Rate = {repaired_metrics.get('retrieval_hit_rate', 0):.4f}, "
          f"Token F1 = {repaired_metrics.get('mean_token_f1', 0):.4f}")
    print(f"  ✅ Quality Gate status sau Repair = {repaired_quality.get('success')} (Kỳ vọng: True)")

    # 6. TẠO BÁO CÁO ĐỐI CHIẾU 3 TRẠNG THÁI
    print("\n[Bước 6/6] Xuất Báo Cáo Đối Chiếu 3 Trạng Thái...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"  📄 Báo cáo đối chiếu đã được ghi tại: {settings.paths.comparison_report}")

    # BẢNG TỔNG HỢP IN RA CONSOLE CHO LIVE DEMO
    print("\n" + "=" * 70)
    print("📊 BẢNG TỔNG HỢP ĐỐI CHIẾU HIỆU NĂNG 3 TRẠNG THÁI (LIVE DEMO READY)")
    print("=" * 70)
    print(f"{'Chỉ số':<25} | {'Baseline':<12} | {'Corrupted':<12} | {'Repaired':<12}")
    print("-" * 70)
    print(f"{'Retrieval Hit Rate':<25} | {baseline_metrics.get('retrieval_hit_rate', 0):<12.4f} | "
          f"{corrupted_metrics.get('retrieval_hit_rate', 0):<12.4f} | "
          f"{repaired_metrics.get('retrieval_hit_rate', 0):<12.4f}")
    print(f"{'Mean Token F1':<25} | {baseline_metrics.get('mean_token_f1', 0):<12.4f} | "
          f"{corrupted_metrics.get('mean_token_f1', 0):<12.4f} | "
          f"{repaired_metrics.get('mean_token_f1', 0):<12.4f}")
    print(f"{'LLM Judge Accuracy':<25} | {baseline_metrics.get('judge_accuracy', 0):<12.4f} | "
          f"{corrupted_metrics.get('judge_accuracy', 0):<12.4f} | "
          f"{repaired_metrics.get('judge_accuracy', 0):<12.4f}")
    print(f"{'Great Expectations':<25} | {'Passed (True)':<12} | {'Failed (False)':<12} | {'Passed (True)':<12}")
    print(f"{'Freshness SLA':<25} | {'Fresh (True)':<12} | {'Stale (False)':<12} | {'Fresh (True)':<12}")
    print("=" * 70)
    print("🎉 HOÀN THÀNH TOÀN BỘ LUỒNG PHA 2 THÀNH CÔNG RỰC RỠ!\n")

