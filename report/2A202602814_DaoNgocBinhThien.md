# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                 |
| ----------------- | ------------------------------------------------------------------------ |
| Họ và tên         | Đào Ngọc Bình Thiên                                                      |
| MSSV              | 2A2026021814                                                             |
| Khóa/Lớp          | AI-ENGINEER-K4                                                           |
| Tên nhóm          | Group 63 (120AnLieng)                                                    |
| Vai trò chính     | Thành viên 2: Data Observability & Corruption Specialist                 |
| Repository        | https://github.com/LuongToan12/K4-L3A-Day10-Group63-120AnLieng           |
| Ngày hoàn thành   | 2026-09-25                                                               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | --------------- | ---------- |
| Data Observability (GX 1.x) | `src/observability/quality.py` (`run_data_quality_checks`) | `df: pd.DataFrame`, `settings: Settings`, `report_name: str` | Báo cáo kiểm định JSON tại `data/quality/{report_name}_quality_report.json` và dict kết quả `{"success": bool, ...}` | Hoàn thành |
| Freshness SLA Monitoring | `src/observability/quality.py` (`build_freshness_report`) | `df: pd.DataFrame`, `settings: Settings`, `report_path: Path` | `data/quality/freshness_report.json` phản ánh tỷ lệ dữ liệu cũ quá hạn 180 ngày | Hoàn thành |
| Synthetic Data Corruption | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | Cleaned `df: pd.DataFrame`, `output_log_path: Path` | DataFrame bị tiêm 6 lỗi dữ liệu, cập nhật lại `text_for_embedding`, log `data/results/corruption_log.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Hỗ trợ tích hợp Baseline Pipeline | TV1 (`src/pipelines/phase1.py`) | Cung cấp hàm `run_data_quality_checks` và `build_freshness_report` để TV1 tích hợp vào Phase 1 chạy nghiệm thu. |
| Hỗ trợ tích hợp Corruption Flow & Repair | TV3 (`src/pipelines/corruption_flow.py`) | Cung cấp hàm `corrupt_clean_dataframe` và kiểm định chốt chất lượng trước và sau khi TV3 chạy Idempotent Repair. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Thiết lập Data Quality Gate GX 1.x | `src/observability/quality.py` | 4 Expectations chuẩn Ephemeral Context: table row count (5-5000), not null (`paper_id`, `title`, `text_for_embedding`), unique `paper_id`, summary length >= 30. | `python -c "from observability.quality import run_data_quality_checks; ..."` -> `success = True` trên clean data |
| Giám sát Freshness SLA | `src/observability/quality.py` | Phát hiện tỷ lệ bài báo có `age_days > 180`, gắn cờ `is_fresh = False` nếu tỷ lệ > 25%. | `data/quality/freshness_report.json` |
| Bộ tiêm 6 kịch bản lỗi | `src/ingestion/corruption.py` | Triển khai 6 kịch bản: drop latest 20%, blank summary, inject noise, truncate title (< 8 chars), stale date (+365 days), duplicate rows. | `data/results/corruption_log.json` ghi nhận đầy đủ 6 dạng lỗi |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Trong kiến trúc RAG ứng dụng, hiện tượng **Silent Failure** xảy ra khi dữ liệu đầu vào bị lỗi hoặc bị lỗi thời nhưng hệ thống không ném Exception, dẫn đến Agent sinh ra câu trả lời sai lệch (Hallucination). Module của tôi đóng vai trò "chốt kiểm dịch" chặn dữ liệu hỏng trước khi nạp vào ChromaDB và chủ động giả lập các sự cố dữ liệu thực tế để kiểm chứng khả năng phát hiện lỗi của hệ thống.

### Cách triển khai
1. **Great Expectations 1.x Ephemeral Context:**
   Sử dụng API chuẩn mới của Great Expectations 1.x:
   ```python
   context = gx.get_context(mode="ephemeral")
   data_source = context.data_sources.add_pandas(name=source_name)
   data_asset = data_source.add_dataframe_asset(name=asset_name)
   batch_def = data_asset.add_batch_definition_whole_dataframe(batch_name)
   batch = batch_def.get_batch(batch_parameters={"dataframe": df})
   ```
   Tạo `gx.ExpectationSuite` với 4 expectations cốt lõi và gọi `batch.validate(suite)`.

2. **Cơ chế Freshness SLA:**
   Đo lường độ tươi của kho tri thức dựa trên `age_days` so với ngưỡng quy định 180 ngày. Nếu tỷ lệ bài cũ vượt quá 25%, hệ thống cảnh báo dữ liệu cần được làm mới.

3. **6 Kịch bản Data Corruption:**
   - Cắt giảm 20% bài báo mới nhất để làm mất thông tin thời sự.
   - Xóa trắng tóm tắt (`summary = ""`).
   - Bơm chuỗi token nhiễu rác `[CORRUPTED_NOISE %$#@! NULL_PTR_ERROR]` vào tóm tắt.
   - Cắt ngắn tiêu đề thành 7 ký tự (`"Corrupt"`).
   - Lùi ngày xuất bản 365 ngày để kích hoạt vi phạm Freshness SLA.
   - Nhân bản dòng để vi phạm tính toàn vẹn (Uniqueness).
   - Tái tạo lại toàn bộ cột `text_for_embedding` trên dữ liệu đã biến đổi.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | `pd.DataFrame` chứa các trường chuẩn: `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`, `text_for_embedding` |
| Output | File JSON kiểm định chất lượng và độ tươi; DataFrame bị tiêm lỗi kèm file log `corruption_log.json` |
| Module phụ thuộc | Nhận DataFrame sạch từ `src/ingestion/cleaning.py` (TV1) |
| Module sử dụng output | `src/pipelines/phase1.py` (TV1), `src/pipelines/corruption_flow.py` (TV3), `src/observability/reporting.py` (TV3) |

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn chế độ hoạt động của Great Expectations 1.x (File-based Context hay Ephemeral Context trên RAM).
- **Các phương án đã cân nhắc:**
  1. Dùng `mode="file"` sinh thư mục cấu hình `great_expectations/` trên ổ đĩa.
  2. Dùng `mode="ephemeral"` tạo in-memory context trực tiếp trong bộ nhớ RAM.
- **Phương án đã chọn:** `mode="ephemeral"`.
- **Lý do:** Tránh việc sinh hàng chục file YAML/JSON cấu hình rác vào repository, thực thi kiểm định siêu tốc (dưới 1 giây), hoàn toàn tương thích với các môi trường CI/CD và ephemeral container.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'core'` khi chạy lệnh kiểm thử độc lập từ terminal.
- **Nguyên nhân gốc:** Thư mục `src/` chưa được liên kết vào `sys.path` của virtual environment `.venv`.
- **Cách xử lý:** Kích hoạt chế độ cài đặt editable package qua lệnh `.\.venv\Scripts\python.exe -m pip install -e .` (liên kết `pyproject.toml` vào site-packages).
- **Cách xác minh sau khi sửa:** Lệnh import `from core.config import load_settings` thực thi thành công không còn lỗi.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu thô từ Crossref REST API được tải về lưu nguyên bản vào `data/raw/` để bảo toàn Data Lineage. Sau đó, module cleaning làm sạch ký tự XML, tính `age_days`, ghép `text_for_embedding` rồi đi qua Great Expectations Quality Gate. Khi dữ liệu đạt chuẩn (Pass), mô hình MiniLM sẽ mã hóa văn bản thành vector 384 chiều và nạp vào ChromaDB collection.
2. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - Quality checks kiểm tra tính hợp lệ về cấu trúc, độ đầy đủ, tính duy nhất và độ dài tối thiểu của dữ liệu tại thời điểm nạp.
   - Freshness monitoring kiểm tra tính thời sự của kho dữ liệu theo thời gian (SLA 180 ngày), phát hiện khi dữ liệu trở nên lạc hậu so với thực tế.
3. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính khách quan và khoa học khi so sánh. Việc cố định 10 câu hỏi đánh giá giúp mọi sự thay đổi về Hit Rate và Token F1 chỉ phản ánh đúng chất lượng của dữ liệu, loại bỏ sai số do đề thi thay đổi.
4. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Thành công khi Quality Gate chuyển từ `Fail` sang `Pass` (`success=True`), Freshness SLA đạt chuẩn `is_fresh=True`, và các chỉ số `retrieval_hit_rate` và `mean_token_f1` trong `repaired_metrics.json` phục hồi tương đương với mức ban đầu trong `baseline_metrics.json`.

---

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.

**Họ và tên xác nhận:** Đào Ngọc Bình Thiên  
**Ngày xác nhận:** 2026-09-25
