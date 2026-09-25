# Báo Cáo Pha 2 — Data Corruption, Idempotent Repair & Đối Chiếu 3 Trạng Thái

> **Mục tiêu:** Giả lập sự cố dữ liệu bẩn (6 kịch bản corruption), chứng minh hiện tượng **Silent Failure** của RAG Agent, và thẩm định năng lực tự phục hồi an toàn (**Idempotent Repair**) từ nguồn thô đáng tin cậy.

---

## 1. Bảng Đối Chiếu Định Lượng 3 Trạng Thái (Benchmark Comparison)

| Metric / Signal | Baseline (Sạch) | Corrupted (Lỗi) | Repaired (Phục hồi) | Tác động do Corruption | Mức độ Phục hồi | Nhận xét chuyên môn |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`retrieval_hit_rate`** | **1.0000** | **0.7667** | **1.0000** | `-0.2333` | `+0.2333` | Bị rớt mạnh do mất 20% bài mới & cắt ngắn tiêu đề; đã khôi phục hoàn toàn sau repair. |
| **`mean_token_f1`** | **1.0000** | **0.7683** | **1.0000** | `-0.2317` | `+0.2317` | Sụt giảm nghiêm trọng do tóm tắt bị xóa rỗng và chèn chuỗi ký tự rác. |
| **`judge_accuracy`** | **1.0000** | **0.8000** | **1.0000** | `-0.2000` | `+0.2000` | AI trả lời sai sự thật (Hallucination) trên dữ liệu bẩn; lấy lại độ chính xác sau khi nạp sạch. |
| **`mean_judge_score`** | **5.0000** | **3.9333** | **5.0000** | `-1.0667` | `+1.0667` | Điểm đánh giá chất lượng phản hồi từ LLM Judge giảm sâu và hồi phục 100%. |
| **Quality Gate (GX 1.x)** | **✅ Pass** | **❌ Fail** | **✅ Pass** | Báo động đỏ | Hoàn toàn sạch | Great Expectations phát hiện vi phạm độ dài summary và trùng lặp bản ghi. |
| **Freshness SLA** | **Fresh ✅** | **Stale ⚠️** | **Fresh ✅** | Vi phạm SLA | Tươi mới trở lại | Bắt được lỗi lùi ngày xuất bản về quá khứ 365 ngày (stale dates). |

---

## 2. Phân Tích Hiện Tượng "Silent Failure" Khi Dữ Liệu Bị Ô Nhiễm

Khi dữ liệu bị tiêm 6 loại lỗi thực tế (xóa summary, cắt ngắn tiêu đề < 8 ký tự, lùi ngày xuất bản, duplicate dòng, bỏ rơi bài báo mới):
1. **Không có lỗi đỏ runtime (Zero Exception):** Mã nguồn không hề bị sập (`crash`). Hệ thống Vector Store vẫn trả về vector, LLM vẫn sinh câu trả lời mượt mà, đúng ngữ pháp.
2. **Ảo giác nghiêm trọng (Severe Hallucination):** Do `text_for_embedding` bị cắt xén hoặc rỗng, LLM buộc phải bịa đặt thông tin để trả lời câu hỏi của người dùng, hoặc trả lời câu rập khuôn *"Tôi không tìm thấy thông tin"*.
3. **Mối quan hệ nhân quả:**
   $$\text{Data Corruption} \longrightarrow \text{Quality Gate Báo Động (GX Fail)} \longrightarrow \text{RAG Metrics Sụp Đổ}$$

---

## 3. Cơ Chế Phục Hồi An Toàn (Idempotent Repair Architecture)

Thay vì sửa đổi chắp vá trên file lỗi (vốn không thể khôi phục lại phần tóm tắt và tiêu đề đã bị xóa mất), nhóm đã triển khai luồng **Idempotent Repair chuẩn Data Engineering**:
- **Nguồn chân lý duy nhất (Single Source of Truth):** Đọc lại bản lưu trữ thô nguyên vẹn `data/raw/crossref_records.json` (được bảo tồn từ CP0).
- **Tái tạo có tính bất biến (Deterministic Re-clean):** Áp dụng lại bộ quy tắc làm sạch chuẩn hóa để ghi đè `papers_clean.csv`.
- **Tái lập Vector Index (Re-indexing):** Xóa bỏ collection bị ô nhiễm và nạp lại toàn bộ vector sạch vào `papers-repaired`.
- **Tính Idempotent:** Dù kích hoạt chạy lại 1 lần hay 100 lần, trạng thái cuối cùng của dữ liệu luôn luôn sạch, đồng nhất và không sinh rác trùng lặp.

---

## 4. Kết Luận
Báo cáo chứng minh rõ ràng: **Chất lượng dữ liệu quyết định chất lượng của AI ("Garbage In $\rightarrow$ Garbage Out")**. Nhờ chốt kiểm dịch Great Expectations 1.x kết hợp cơ chế Idempotent Repair, hệ thống RAG có khả năng phát hiện sự cố sớm và tự hồi phục phong độ đỉnh cao mà không cần can thiệp thủ công.
