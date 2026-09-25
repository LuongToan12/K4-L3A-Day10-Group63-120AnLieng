# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Group63-120AnLieng`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3A-Day10-Group63-120AnLieng`

---

## # Thành viên (Nhóm 3 người)

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Lương Khánh Toàn | 2A202602836 | toanluong120904@gmail.com | **Pipeline Lead & Ingestion**: Cấu hình môi trường, Ingestion (`crossref.py`), Data Cleaning (`cleaning.py`), Pipeline Phase 1 (`phase1.py`, `run_phase1.py`). | `report/2A202602836_LuongKhanhToan.md` |
| 2 | Đào Ngọc Bình Thiên | 2A2026021814 | thiendao103@gmail.com | **Data Observability & Corruption Specialist**: Great Expectations 1.x (`quality.py`), Freshness SLA, Tiêm 6 dạng lỗi dữ liệu (`corruption.py`). | `report/2A202602814_DaoNgocBinhThien.md` |
| 3 | Lương Quang Huy | 2A202602698 | huyluong1910@gmail.com | **Evaluation, Repair & Reporting Lead**: Sinh test set 30 câu (`testset.py`), Luồng Idempotent Repair (`corruption_flow.py`), Xuất báo cáo đối chiếu 3 trạng thái (`reporting.py`). | `report/2A202602698_LuongQuangHuy.md` |

---

## # Cá nhân

### ## LuongKhanhToan-2A202602836
- **Vai trò:** Trưởng nhóm & Pipeline Lead / Data Ingestion.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập môi trường ảo, quản lý cấu hình hệ thống, tạo branch làm việc `LuongToan12`.
  - Triển khai module thu thập dữ liệu Crossref API với cơ chế fallback đọc offline snapshot bảo toàn Lineage trong `src/ingestion/crossref.py`.
  - Triển khai Data Cleaning, loại bỏ thẻ XML rác, tính toán `age_days`, tạo trường `text_for_embedding` 5 phần, khử trùng lặp theo `paper_id` trong `src/ingestion/cleaning.py`.
  - Kết nối và thực thi thành công Baseline Pipeline trong `src/pipelines/phase1.py` và `script/run_phase1.py`, tạo vector index ChromaDB `papers-baseline`.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc về thiết kế Data Pipeline chuẩn hóa, quản lý Data Lineage và bảo toàn snapshot thô ban đầu để phục vụ khôi phục hệ thống khi xảy ra sự cố.

### ## DaoNgocBinhThien-2A2026021814
- **Vai trò:** Data Observability & Corruption Specialist.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Data Quality Gate bằng Great Expectations 1.x chuẩn Ephemeral Context với 4 Expectations cốt lõi trong `src/observability/quality.py`.
  - Cài đặt hệ thống giám sát độ tươi Freshness SLA (`age_days > 180`) và xuất báo cáo `data/quality/freshness_report.json`.
  - Xây dựng bộ giả lập sự cố với 6 dạng tiêm lỗi dữ liệu thực tế trong `src/ingestion/corruption.py` và ghi nhật ký vào `data/results/corruption_log.json`.
- **Điều học được / Đóng góp chính:**
  - Hiểu rõ cơ chế ngăn chặn hiện tượng Silent Failure của AI bằng các chốt kiểm dịch dữ liệu tự động trước khi nạp vào Vector Store.

### ## LuongQuangHuy-2A202602698
- **Vai trò:** Evaluation, Repair & Reporting Lead.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng bộ benchmark 30 câu hỏi đa dạng và bao phủ các edge cases qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`) trong `src/evaluation/testset.py`.
  - Triển khai luồng điều phối Phase 2 và cơ chế phục hồi **Idempotent Repair** từ Raw gốc trong `src/pipelines/corruption_flow.py` và `script/run_corruption_flow.py`.
  - Xây dựng module tự động xuất báo cáo Markdown Pha 1 (`phase1_report.md`) và Báo cáo đối chiếu 3 trạng thái (`corruption_report.md`) trong `src/observability/reporting.py`.
  - Hoàn thiện bảng số liệu thực nghiệm và phân tích quan hệ nhân quả trong báo cáo chung [`report/group_report.md`](../report/group_report.md).
- **Điều học được / Đóng góp chính:**
  - Thấu hiểu bản chất của thiết kế Idempotent Pipeline trong Data Engineering và phương pháp đánh giá khách quan RAG qua Retrieval Hit Rate, Token F1 và LLM Judge.
