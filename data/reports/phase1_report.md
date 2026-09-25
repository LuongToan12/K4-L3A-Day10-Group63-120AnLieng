# Báo Cáo Pha 1 — Baseline Data Pipeline & Observability

> **Ngày thực hiện:** N/A  
> **Nguồn dữ liệu:** Crossref Academic API / Local Snapshot (24 bản ghi)  
> **Trạng thái Quality Gate:** ✅ PASSED | **Trạng thái Freshness:** ✅ FRESH

---

## 1. Tổng Quan Nguồn Dữ Liệu & Pipeline Lineage

Hệ thống đã thu thập và bảo toàn nguyên vẹn 2 tầng dữ liệu thô (Raw Preservation) trước khi làm sạch:
- **Raw API Response:** `data/raw/crossref_response.json` (bảo toàn toàn bộ JSON gốc).
- **Raw Records Lineage:** `data/raw/crossref_records.json` (danh sách đối tượng `PaperRecord` chuẩn hóa).
- **Cleaned Dataset:** `data/clean/papers_clean.csv` (24 dòng sạch, đã khử trùng lặp theo `paper_id`, loại bỏ thẻ HTML/XML, tính toán `age_days` và định dạng `text_for_embedding`).

---

## 2. Kết Quả Kiểm Định Chất Lượng (Great Expectations 1.x)

Trạm kiểm dịch dữ liệu Ephemeral Context của **Great Expectations 1.x** đã thẩm định dữ liệu sạch trước khi cho phép nạp vào Vector Database:

| Tiêu chí kiểm định (Expectation) | Tham số cấu hình | Trạng thái | Đánh giá |
| :--- | :--- | :---: | :--- |
| `ExpectTableRowCountToBeBetween` | min=5, max=5000 | ✅ Pass | Số lượng bản ghi hợp lệ (24 dòng) |
| `ExpectColumnValuesToNotBeNull` | `paper_id`, `title`, `text_for_embedding` | ✅ Pass | Không có trường quan trọng nào bị rỗng |
| `ExpectColumnValuesToBeUnique` | `paper_id` | ✅ Pass | Mã định danh DOI là duy nhất 100% |
| `ExpectColumnValueLengthsToBeBetween` | `summary` min_length=30 | ✅ Pass | Tóm tắt có đủ độ dài ngữ nghĩa cho AI đọc |

**Kết luận Quality Gate:** Toàn bộ dữ liệu sạch đạt chuẩn, sẵn sàng đưa vào ChromaDB collection `papers-baseline`.

---

## 3. Báo Cáo Độ Tươi Mới (Freshness SLA Monitoring)

- **Bài báo mới nhất:** 2026-07-22
- **Bài báo cũ nhất:** 2026-03-28
- **Số bài báo cũ quá hạn (> 180 ngày):** 1 / 24 (4.2%)
- **Ngưỡng vi phạm SLA:** 25.0%
- **Đánh giá:** ✅ FRESH (Tỷ lệ bài cũ nằm trong giới hạn cho phép).

---

## 4. Đánh Giá Hiệu Năng RAG Baseline

Mô hình nhúng `sentence-transformers/all-MiniLM-L6-v2` kết hợp ChromaDB đã được kiểm thử qua bộ Benchmark 30 câu hỏi đa dạng:

| Chỉ số đo lường (Metric) | Điểm số Baseline | Ý nghĩa thực tế |
| :--- | :---: | :--- |
| **Retrieval Hit Rate** | **1.0000** | Tỷ lệ tìm thấy đúng bài báo mục tiêu trong Top-k kết quả |
| **Mean Token F1** | **1.0000** | Độ chính xác từ vựng giữa câu trả lời của AI và Ground Truth |
| **LLM Judge Accuracy** | **1.0000** | Tỷ lệ câu trả lời được giám khảo LLM chấm là chính xác |
| **Mean Judge Score (1-5★)** | **5.0000** | Điểm số chất lượng trung bình của câu trả lời |

---

## 5. Kết Luận Pha 1
Dữ liệu sạch đáp ứng trọn vẹn các tiêu chuẩn chất lượng. AI Agent hoạt động ổn định và đạt hiệu năng cơ sở chuẩn (Baseline) cao, làm thước đo tin cậy để đối chiếu với Pha 2 khi thử thách tiêm độc tố dữ liệu.
