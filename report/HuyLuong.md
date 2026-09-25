# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                 |
| ----------------- | ------------------------------------------------------------------------ |
| Họ và tên         | Lương Huy (Huy Lương)                                                    |
| MSSV              | [Điền MSSV]                                                              |
| Khóa/Lớp          | AI-ENGINEER-K4                                                           |
| Tên nhóm          | Group 63 (120AnLieng)                                                    |
| Vai trò chính     | **Thành viên 3: Evaluation, Repair & Reporting Lead**                    |
| Repository        | https://github.com/LuongToan12/K4-L3A-Day10-Group63-120AnLieng           |
| Ngày hoàn thành   | 2026-09-25                                                               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :---: |
| **Benchmark Suite Builder** | `src/evaluation/testset.py`<br>- `build_test_set` | Cleaned `df: pd.DataFrame`, `output_path: Path` | Bộ đề thi 30 câu hỏi chuẩn hóa qua 4 nhóm nghiệp vụ tại `data/eval/test_set.json` | Hoàn thành |
| **Markdown Reporting Engine** | `src/observability/reporting.py`<br>- `generate_phase1_report`<br>- `generate_corruption_report` | Dicts kết quả: `metrics`, `quality`, `freshness` | Báo cáo Pha 1 (`phase1_report.md`) và Báo cáo đối chiếu 3 trạng thái (`corruption_report.md`) | Hoàn thành |
| **Phase 2 & Idempotent Repair** | `src/pipelines/corruption_flow.py`<br>`script/run_corruption_flow.py` | Clean data, Raw records backup, Settings | Điều phối toàn bộ luồng Phase 2, tái lập ChromaDB `papers-repaired`, sinh metrics | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Tích hợp UTF-8 Console trên Windows** | Toàn đội (`corruption_flow.py`, `run_corruption_flow.py`) | Khắc phục triệt để lỗi `UnicodeEncodeError` trên Windows terminal cho cả nhóm |
| **Hoàn thiện Báo cáo Nhóm** | Toàn đội ([`report/group_report.md`](group_report.md)) | Tổng hợp toàn bộ số liệu thực nghiệm đo lường 3 trạng thái và phân tích quan hệ nhân quả |
| **Cung cấp Test Set cho Phase 1** | TV1 (`src/pipelines/phase1.py`) | Cung cấp file `data/eval/test_set.json` 30 câu để TV1 chạy đánh giá đo lường Baseline |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Xây dựng bộ Benchmark 30 câu hỏi đa dạng + Edge Cases | `src/evaluation/testset.py` | 30 câu hỏi (10 summary, 7 authors, 7 date, 6 categories) tại `data/eval/test_set.json` | `python -c "from evaluation.testset import build_test_set; ..."` -> in ra đủ 30 câu |
| Xây dựng báo cáo Markdown 3 trạng thái | `src/observability/reporting.py` | Bảng đối chiếu so sánh rõ ràng mức sụt giảm $\Delta$ và mức độ phục hồi | File `data/reports/corruption_report.md` |
| Triển khai luồng Idempotent Repair và đánh giá Phase 2 | `src/pipelines/corruption_flow.py` | Phục hồi 24 dòng sạch từ Raw, khôi phục 100% metrics | `python script/run_corruption_flow.py` thoát mã 0 |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Thiếu thước đo khách quan cho RAG:** Cần một bộ đề thi đủ lớn (30 câu thay vì 10 câu cơ bản) có tính phân hóa cao và bao phủ các trường hợp biên (Edge Cases: nhạy cảm với lỗi drop bài mới, tiêu đề có ký tự đặc biệt/acronyms, phân biệt bài tương đồng ngữ nghĩa).
2. **Hiện tượng Silent Failure:** Khi dữ liệu bị tiêm lỗi, hệ thống không báo lỗi runtime đỏ nhưng câu trả lời của AI bị sai lệch. Cần đo lường định lượng chính xác sự sụt giảm này qua Hit Rate và Token F1.
3. **Phục hồi an toàn (Idempotent Repair):** Cần cơ chế phục hồi dữ liệu từ bản thô ban đầu đảm bảo tính bất biến: chạy lại bao nhiêu lần vẫn cho kết quả chuẩn sạch đồng nhất mà không cần sửa tay.

### Cách triển khai
- **Bộ Benchmark (`testset.py`):**
  - Tự động chuẩn hóa dữ liệu đầu vào (hỗ trợ cả clean DataFrame và raw JSON dict).
  - Phân bổ câu hỏi theo 4 nhóm nghiệp vụ chính. Thiết kế prompt linh hoạt (paraphrasing) khớp chính xác với regex extraction của `src/retrieval/qa.py`.
  - Cố tình đặt 20% câu hỏi vào các bài báo có ngày công bố mới nhất để làm đòn bẩy đo lường khi xảy ra sự cố *Drop latest records*.
- **Cơ chế Idempotent Repair (`corruption_flow.py`):**
  - Không sửa chắp vá trên file lỗi. Quay về đọc trực tiếp bản lưu trữ thô ban đầu `data/raw/crossref_records.json` (Single Source of Truth).
  - Tái làm sạch qua `build_clean_dataframe()`, chạy lại kiểm định GX 1.x, xóa collection cũ và nạp lại toàn bộ vector vào collection `papers-repaired`.
  - Đánh giá lại toàn bộ 30 câu hỏi để đối chiếu sự phục hồi.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi dữ liệu bị tiêm 6 kịch bản lỗi (xóa tóm tắt, cắt ngắn tiêu đề, nhân đôi dòng), cần quyết định cách thức phục hồi lại hệ thống dữ liệu sạch.
- **Các phương án đã cân nhắc:**
  1. *Phương án A (Vá lỗi cục bộ - Patching):* Dùng script tìm các dòng bị rỗng/bị lỗi để điền bù hoặc xóa dòng lỗi.
  2. *Phương án B (Idempotent Re-creation from Raw Source of Truth):* Đọc lại bản lưu trữ thô nguyên bản từ `data/raw/crossref_records.json` và chạy lại luồng làm sạch từ đầu.
- **Phương án đã chọn:** **Phương án B**.
- **Lý do:** Trong kỹ nghệ dữ liệu (Data Engineering), khi dữ liệu ở tầng downstream đã bị mất thông tin (ví dụ: summary bị xóa trắng), không thể "ngồi đoán" để vá lỗi. Cách duy nhất đảm bảo **Data Lineage** và **tính toàn vẹn 100%** là tái tạo lại từ nguồn thô ban đầu. Hơn nữa, phương án B có tính **Idempotent** (chạy lại bao nhiêu lần kết quả vẫn đồng nhất, không phụ thuộc vào trạng thái lỗi trước đó).
- **Bằng chứng phù hợp:** Sau khi phục hồi từ Raw, các chỉ số Retrieval Hit Rate và Token F1 đã lấy lại phong độ **1.0000 (100%)** hoàn hảo.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680' in position 0: character maps to <undefined>
  ```
- **Lệnh tái hiện:** Chạy `python script/run_corruption_flow.py` trên Windows PowerShell.
- **Nguyên nhân gốc:** Console mặc định của Windows sử dụng bảng mã `cp1252`, không hỗ trợ các ký tự Unicode/emoji trạng thái (🚀, ✅, 🚨, 📊) được in ra từ Python script.
- **Cách xử lý:** Bổ sung cấu hình tái định dạng stdout ngay đầu file thực thi:
  ```python
  if hasattr(sys.stdout, "reconfigure"):
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
  ```
- **Cách xác minh sau khi sửa:** Lệnh chạy hoàn tất trơn tru với mã thoát 0, in đầy đủ bảng đối chiếu 3 cột ra console.
- **Điều học được:** Luôn chủ động xử lý encoding UTF-8 ở các entrypoint CLI khi phát triển phần mềm đa nền tảng (Cross-platform Python trên Windows/Linux/macOS).

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:**  
   Crossref REST API $\rightarrow$ lưu raw snapshot JSON (`data/raw/`) $\rightarrow$ làm sạch chuẩn hóa (bỏ XML, tính `age_days`, tạo `text_for_embedding` 5 phần) $\rightarrow$ kiểm định Great Expectations 1.x $\rightarrow$ mã hóa vector qua mô hình `all-MiniLM-L6-v2` $\rightarrow$ nạp vào ChromaDB persistent collection.
2. **Evaluation set và ground-truth document IDs đo chất lượng ra sao:**  
   Mỗi câu hỏi có danh sách `ground_truth_doc_ids` (DOI của bài báo mục tiêu). Khi Agent truy vấn ChromaDB, hệ thống kiểm tra xem bài báo mục tiêu có nằm trong Top-k kết quả trả về hay không để tính **Retrieval Hit Rate**. Sau đó so sánh câu trả lời của AI với chuỗi `ground_truth` để tính **Token F1** và chuyển cho LLM Judge chấm điểm độ chính xác.
3. **Quality checks khác Freshness monitoring ở điểm nào:**  
   *Quality checks (Great Expectations)* kiểm soát tính toàn vẹn và hợp lệ về cấu trúc dữ liệu (số dòng, không null, unique ID, độ dài chuỗi). Trong khi đó, *Freshness monitoring* kiểm soát tính thời sự của tri thức (đo lường `age_days` so với ngưỡng SLA 180 ngày) để ngăn chặn AI tư vấn bằng dữ liệu lỗi thời.
4. **Vì sao phải dùng cùng test set cho cả 3 trạng thái:**  
   Để đảm bảo tính khoa học và kiểm soát biến số. Chỉ khi đề thi giữ nguyên hằng số, sự thay đổi của điểm số mới phản ánh trung thực tác động của dữ liệu bẩn và sự phục hồi của dữ liệu sạch.
5. **Repair được xem là thành công dựa trên cơ sở nào:**  
   - Bằng chứng artifact: File `papers_clean_repaired.csv` có đủ 24 dòng sạch, collection `papers-repaired` được tái lập.
   - Bằng chứng metrics: Great Expectations trả về `success = True`, Freshness SLA `is_fresh = True`, và Retrieval Hit Rate cùng Token F1 khôi phục trọn vẹn về mức 1.0000.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| **`retrieval_hit_rate`** | **1.0000** | **0.7667** | **1.0000** | Tụt 23.33% do mất 20% bài mới và cắt ngắn tiêu đề; khôi phục 100% sau repair. |
| **`mean_token_f1`** | **1.0000** | **0.8785** | **1.0000** | Sụt giảm do summary bị xóa trắng và chèn ký tự rác; hồi phục trọn vẹn. |
| **`judge_accuracy`** | **1.0000** | **0.9000** | **1.0000** | AI trả lời sai ngữ nghĩa khi đọc context bẩn; lấy lại độ chính xác hoàn hảo. |
| **`mean_judge_score`** | **5.0000** | **4.4000** | **5.0000** | Điểm số chất lượng câu trả lời giảm sút và phục hồi về mức 5★ tuyệt đối. |
| **Quality checks (GX)** | **✅ Pass** | **❌ Fail** | **✅ Pass** | Báo động đỏ khi data bị bẩn; hoàn toàn xanh sau khi phục hồi. |
| **Freshness status** | **Fresh ✅** | **Stale ⚠️** | **Fresh ✅** | Phát hiện thành công lỗi lùi ngày xuất bản về 365 ngày trước. |

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất:
1. **Garbage In -> Garbage Out:** Hiểu sâu sắc rằng mô hình AI giỏi đến đâu cũng trở nên vô dụng nếu dữ liệu đầu vào bị ô nhiễm.
2. **Data Lineage là bảo hiểm dữ liệu:** Việc giữ nguyên bản sao lưu thô ban đầu (Raw Preservation) là điều kiện tiên quyết để có thể tự động khôi phục hệ thống khi gặp thảm họa dữ liệu.
3. **Bản chất của Silent Failure:** Nhận diện được nguy cơ AI trả lời rất tự tin nhưng sai sự thật khi không có chốt kiểm dịch dữ liệu tự động.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lương Huy  
**Ngày xác nhận:** 2026-09-25
