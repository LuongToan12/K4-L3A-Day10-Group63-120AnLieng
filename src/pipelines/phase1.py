from __future__ import annotations

import logging
from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from retrieval.index import LocalEmbeddingIndex

logger = logging.getLogger(__name__)


def main() -> None:
    """Xay dung va dieu phoi baseline pipeline end-to-end."""
    print("=" * 70)
    print("🚀 BẮT ĐẦU CHẠY BASELINE PIPELINE (PHASE 1)")
    print("=" * 70)

    # 1. Load settings
    settings = load_settings()
    print(f"[Phase 1] 1. Cấu hình hệ thống sẵn sàng. Provider: {settings.llm_provider}")

    # 2. Ingestion raw records
    records = fetch_source_records(settings)
    print(f"[Phase 1] 2. Ingestion hoàn tất: Đã nạp {len(records)} bản ghi từ {settings.source_api}.")

    # 3. Clean data
    run_date = now_utc()
    df = build_clean_dataframe(records, run_date)
    print(f"[Phase 1] 3. Data Cleaning hoàn tất: {len(df)} dòng dữ liệu chuẩn sạch.")

    # 4. Save clean CSV/JSON
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    print(f"[Phase 1] 4. Đã lưu artifacts dữ liệu sạch:")
    print(f"           - CSV:  {settings.paths.clean_csv}")
    print(f"           - JSON: {settings.paths.clean_json}")

    # 5. Build Chroma vector index
    print(f"[Phase 1] 5. Đang tạo Vector Embedding ({settings.embedding_model}) và nạp ChromaDB...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"[Phase 1] 5. Đã lập chỉ mục {len(df)} tài liệu vào collection '{settings.baseline_collection_name}'.")

    # 6. Build or load evaluation set (Phần việc TV3)
    test_set = None
    try:
        from evaluation.testset import build_test_set

        test_set = build_test_set(df, settings.paths.eval_testset)
        print(f"[Phase 1] 6. Đã tạo {len(test_set)} câu hỏi đánh giá vào {settings.paths.eval_testset}.")
    except (NotImplementedError, ImportError):
        if settings.paths.eval_testset.exists():
            test_set = read_json(settings.paths.eval_testset)
            print(f"[Phase 1] 6. Đã nạp {len(test_set)} câu hỏi từ test set có sẵn.")
        else:
            print("[Phase 1] 6. [Chờ Thành viên 3]: build_test_set trong src/evaluation/testset.py chưa được triển khai.")

    # 7. Evaluate baseline metrics
    eval_bundle = None
    if test_set:
        try:
            from evaluation.metrics import evaluate_pipeline

            print("[Phase 1] 7. Đang đánh giá hiệu năng Baseline Retrieval & QA Agent...")
            eval_bundle = evaluate_pipeline(
                settings=settings,
                index=index,
                test_set_path=settings.paths.eval_testset,
                metrics_output_path=settings.paths.baseline_metrics,
                answers_output_path=settings.paths.baseline_answers,
            )
            hit_rate = eval_bundle.summary.get("retrieval_hit_rate", 0.0)
            token_f1 = eval_bundle.summary.get("mean_token_f1", 0.0)
            print(f"[Phase 1] 7. Đánh giá hoàn tất: Hit Rate = {hit_rate:.2%}, Token F1 = {token_f1:.4f}")
        except Exception as exc:
            print(f"[Phase 1] 7. Bỏ qua evaluation do: {exc}")

    # 8. Run data quality checks & freshness report (Phần việc TV2)
    quality_report = None
    freshness_report = None
    try:
        from observability.quality import build_freshness_report, run_data_quality_checks

        quality_report = run_data_quality_checks(df, settings, "baseline")
        freshness_report = build_freshness_report(df, settings, settings.paths.freshness_report)
        print(f"[Phase 1] 8. Quality Gate: Success = {quality_report.get('success')}, Freshness = {freshness_report.get('is_fresh')}")
    except (NotImplementedError, ImportError):
        print("[Phase 1] 8. [Chờ Thành viên 2]: run_data_quality_checks trong src/observability/quality.py chưa được triển khai.")

    # 9. Generate Phase 1 markdown report (Phần việc TV3)
    try:
        from observability.reporting import generate_phase1_report

        if eval_bundle and quality_report and freshness_report:
            generate_phase1_report(
                report_path=settings.paths.baseline_report,
                source_summary={
                    "source_api": settings.source_api,
                    "total_records": len(records),
                    "clean_rows": len(df),
                },
                metrics=eval_bundle.summary,
                quality=quality_report,
                freshness=freshness_report,
            )
            print(f"[Phase 1] 9. Báo cáo Phase 1 đã xuất vào {settings.paths.baseline_report}.")
    except (NotImplementedError, ImportError):
        print("[Phase 1] 9. [Chờ Thành viên 3]: generate_phase1_report trong src/observability/reporting.py chưa được triển khai.")

    # 10. Smoke Demo search query
    demo_query = "What is agentic retrieval-augmented generation?"
    search_results = index.search(demo_query, top_k=2)
    print("-" * 70)
    print(f"[Phase 1] 10. Demo truy vấn thực tế với câu hỏi: '{demo_query}'")
    for r in search_results:
        print(f"           - [{r.score:.3f}] {r.title} ({r.paper_id})")
    print("=" * 70)
    print("🎉 HOÀN THÀNH TOÀN TUYẾN BASELINE PIPELINE (PHASE 1) THÀNH CÔNG!")
    print("=" * 70)


if __name__ == "__main__":
    main()
