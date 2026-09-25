# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                        |
| ----------------- | --------------------------------------------------------------- |
| Họ và tên        | Lương Khánh Toàn                                                |
| MSSV              | [Điền MSSV]                                                     |
| Khóa/Lớp          | K4-L3A                                                          |
| Tên nhóm          | Group63-120AnLieng                                              |
| Vai trò chính     | Pipeline Lead & Data Ingestion                                  |
| Repository        | https://github.com/LuongToan12/K4-L3A-Day10-Group63-120AnLieng  |
| Ngày hoàn thành  | 2026-09-25                                                      |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Raw Ingestion & Lineage** | `src/ingestion/crossref.py`<br>- `parse_crossref_payload`<br>- `fetch_source_records`<br>- `load_raw_records` | Settings cấu hình API Crossref / snapshot local | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` | Hoàn thành |
| **Data Cleaning & Modeling** | `src/ingestion/cleaning.py`<br>- `build_clean_dataframe` | List `PaperRecord`, `run_date` | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` (24 dòng sạch) | Hoàn thành |
| **Baseline Orchestration** | `src/pipelines/phase1.py`<br>`script/run_phase1.py` | Pipeline configurations & modules | Điều phối Phase 1, tạo Chroma collection `papers-baseline` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Lập kế hoạch dự án 3 người** | Toàn đội (TV2, TV3) | Tài liệu [`docs/PROJECT_PLAN_3_MEMBERS.md`](../docs/PROJECT_PLAN_3_MEMBERS.md) phân công chi tiết theo 7 Checkpoints |
| **Quản trị Repository & Branch** | Quản lý Git | Khởi tạo branch `LuongToan12`, chuẩn bị môi trường và cấu hình `.env` |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Thu thập và bảo tồn dữ liệu gốc | `src/ingestion/crossref.py` | 24 bản ghi bài báo khoa học chuẩn | `python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"` |
| Làm sạch và chuẩn hóa embedding text | `src/ingestion/cleaning.py` | `papers_clean.csv` (24 dòng, đầy đủ `text_for_embedding`) | `python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"` |
| Điều phối Baseline Phase 1 | `src/pipelines/phase1.py`<br>`script/run_phase1.py` | ChromaDB collection `papers-baseline`, semantic search demo | `python script/run_phase1.py` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Mất nguồn gốc dữ liệu (Data Lineage loss):** Nếu trực tiếp biến đổi dữ liệu nhận từ API mà không lưu trữ raw snapshot, khi pipeline biến đổi bị lỗi sẽ không có cách nào khôi phục hoặc so sánh đối chiếu.
2. **Nhiễu văn bản và định dạng không chuẩn:** Metadata từ Crossref chứa các thẻ HTML/JATS XML thừa (`<jats:p>`), khoảng trắng bất thường, định dạng ngày tháng không đồng nhất.
3. **Ghost vectors & dữ liệu trùng lặp:** Dữ liệu trùng lặp DOI gây loãng không gian vector, làm sai lệch kết quả xếp hạng của RAG.

### Cách triển khai
1. **Hai tầng lưu trữ thô (Dual Raw Artifacts):**
   - Lưu trữ toàn bộ payload HTTP gốc nhận từ API vào `data/raw/crossref_response.json`.
   - Parse và lưu danh sách đối tượng `PaperRecord` chuẩn hóa vào `data/raw/crossref_records.json`.
   - Trang bị cơ chế fallback offline: Khi không có kết nối internet hoặc API trả về mã lỗi `429 Too Many Requests`, tự động nạp từ file snapshot local mà không gây dừng pipeline.
2. **Quy trình làm sạch 5 bước (`build_clean_dataframe`):**
   - Loại bỏ toàn bộ thẻ JATS XML bằng regex và chuẩn hóa khoảng trắng thừa.
   - Tính toán độ tuổi bài báo theo ngày: `age_days = max(0, (ref_date - pub_date).days)`.
   - Ghép nối cấu trúc 5 phần vào cột `text_for_embedding` (Title, Authors, Published, Categories, Summary).
   - Khử trùng lặp theo khóa duy nhất `paper_id` (`drop_duplicates(subset=['paper_id'], keep='first')`).
   - Sắp xếp dữ liệu xác định (deterministic sorting) theo ngày xuất bản và ID bài báo.
3. **Pipeline Orchestrator (`phase1.py`):**
   - Kết nối toàn bộ các mắt xích theo kiến trúc Module hóa rõ ràng.
   - Thiết kế dạng loose coupling (ghép nối lỏng): Nhận diện và gọi các module kiểm tra chất lượng (TV2) và đánh giá (TV3) khi hoàn thành mà không gây crash pipeline nếu các module đó đang trong quá trình phát triển.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Settings hệ thống, `data/raw/crossref_response.json` hoặc Crossref REST API |
| **Output** | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`, ChromaDB collection `papers-baseline` |
| **Data Contract** | Mỗi dòng dữ liệu sạch đảm bảo đủ 16 cột: `paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, `comment`, `authors_joined`, `categories_joined`, `summary_chars`, `age_days`, `text_for_embedding`. `paper_id` và `title` không được rỗng. |

### Xử lý lỗi ngoại lệ (Failure Handling)
- **API lỗi / mất mạng:** Bắt `requests.RequestException` và tự động fallback về `read_json(raw_api_response)` hoặc `load_raw_records(raw_records_json)`.
- **Lỗi ngày tháng bất thường:** Sử dụng khối `try...except` khi parse `published`, tự động fallback về `ref_date` nếu chuỗi ngày tháng không hợp lệ.

---

## 5. Bài học rút ra & Đóng góp chính
- Hiểu rõ tầm quan trọng của việc bảo toàn dữ liệu gốc (Raw Preservation) và nguyên lý Idempotent Pipeline trong các bài toán MLOps và Data Engineering thực chiến.
- Nắm vững quy trình tiền xử lý văn bản chuyên biệt cho mô hình Dense Retrieval (cấu trúc trường `text_for_embedding`).
