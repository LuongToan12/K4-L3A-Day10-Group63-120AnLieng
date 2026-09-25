# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                                                        |
| ------------------ | --------------------------------------------------------------- |
| Khóa/Lớp         | AI-ENGINEER-K4                                                  |
| Tên nhóm         | Group 63 (120AnLieng)                                           |
| Repository         | https://github.com/LuongToan12/K4-L3A-Day10-Group63-120AnLieng  |
| Ngày hoàn thành | 2026-09-25                                                      |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Lương Khánh Toàn | [Điền MSSV] | **Pipeline Lead & Data Ingestion** | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/pipelines/phase1.py`, `script/run_phase1.py` |
| 2 | Đào Ngọc Bình Thiên | 2A2026021814 | **Data Observability & Corruption Specialist** | `src/observability/quality.py`, `src/ingestion/corruption.py`, `data/quality/*` |
| 3 | Lương Huy | [Điền MSSV] | **Evaluation, Repair & Reporting Lead** | `src/evaluation/testset.py`, `src/observability/reporting.py`, `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` |

---

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn diện 100% mục tiêu của bài lab Day 10 theo đúng lộ trình 7 Checkpoints (CP0 – CP6):

1. **Baseline Pipeline (Phase 1):** Xây dựng thành công chu trình từ Ingestion dữ liệu học thuật Crossref (bảo tồn nguyên vẹn 2 raw artifacts), làm sạch chuẩn hóa (loại bỏ thẻ XML, tính `age_days`, tạo `text_for_embedding` 5 phần, khử trùng lặp), nạp vào ChromaDB `papers-baseline`. Trạm kiểm dịch **Great Expectations 1.x** (chuẩn Ephemeral) vượt qua 100% (6/6 checks, `success = True`) và Freshness SLA đạt chuẩn `is_fresh = True` (chỉ 4.17% bài quá hạn 180 ngày). Đánh giá Baseline trên bộ 30 câu hỏi đạt **Retrieval Hit Rate = 100.00%**, **Mean Token F1 = 1.0000**, và **Judge Accuracy = 100.00%**.
2. **Controlled Corruption:** Triển khai thành công 6 kịch bản tiêm lỗi thực tế (drop 20% bài mới, blank summary, inject noise, truncate title < 8 ký tự, stale date 365 ngày, duplicate rows). Khi RAG chạy trên dữ liệu bẩn, hiện tượng **Silent Failure** bộc lộ rõ rệt: Hit Rate sụt giảm nghiêm trọng xuống **76.67%** (tụt `-0.2333`), Token F1 giảm còn **0.8785**, Quality Gate báo động đỏ `success = False` và Freshness vi phạm SLA.
3. **Idempotent Repair:** Kích hoạt cơ chế phục hồi dữ liệu chuẩn từ nguồn thô ban đầu `data/raw/crossref_records.json` (Single Source of Truth), tái tạo hoàn hảo 24 dòng sạch, nạp lại ChromaDB `papers-repaired`. Toàn bộ các chỉ số phục hồi trọn vẹn **100% phong độ ban đầu** (Hit Rate = 1.0000, F1 = 1.0000, GX Pass = True).

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Nguồn Crossref API (hoặc Local Snapshot data/raw/crossref_response.json)
    ├── 1. Raw Ingestion & Preservation -> data/raw/crossref_records.json
    ├── 2. Data Cleaning & Modeling     -> data/clean/papers_clean.csv
    ├── 3. Data Quality Gate (GX 1.x)   -> 4 Expectations + Freshness SLA
    ├── 4. Embedding & ChromaDB Index   -> sentence-transformers/all-MiniLM-L6-v2
    ├── 5. Evaluation Benchmark         -> 30 câu hỏi (summary, authors, date, categories)
    ├── 6. Synthetic Data Corruption    -> 6 kịch bản tiêm lỗi & corruption_log.json
    └── 7. Idempotent Repair            -> Tái tạo từ Raw & Báo cáo đối chiếu 3 trạng thái
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Crossref REST API / Snapshot local | Gọi API, retry, bóc tách `PaperRecord`, bảo toàn raw JSON | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` | Lương Khánh Toàn |
| **Cleaning** | List `PaperRecord`, `run_date` | Lọc XML, tính `age_days`, tạo `text_for_embedding`, khử trùng lặp | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` | Lương Khánh Toàn |
| **Embedding/Index** | Cleaned DataFrame | Nhúng vector `all-MiniLM-L6-v2`, nạp ChromaDB persistent | `data/chroma/`, `data/embeddings/` | Lương Khánh Toàn & Lương Huy |
| **Evaluation** | Cleaned DataFrame, Chroma Index | Sinh 30 câu hỏi qua 4 nhóm nghiệp vụ, đo Hit Rate, F1, LLM Judge | `data/eval/test_set.json`<br>`data/results/*_metrics.json` | Lương Huy |
| **Observability** | DataFrame, Settings | Great Expectations 1.x Ephemeral Context, Freshness SLA check | `data/quality/*_quality_report.json`<br>`data/quality/freshness_report.json` | Đào Ngọc Bình Thiên |
| **Corruption** | Cleaned DataFrame | Giả lập 6 lỗi dữ liệu thực tế, cập nhật text embedding | `data/results/corruption_log.json`<br>`papers_clean_corrupted.csv` | Đào Ngọc Bình Thiên |
| **Repair & Compare** | Raw Records, Corrupted Index | Idempotent re-clean từ Raw, re-index, lập bảng đối chiếu 3 cột | `data/reports/corruption_report.md`<br>`repaired_metrics.json` | Lương Huy |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| :--- | :--- |
| `LLM_PROVIDER` | `gemini` (hoặc `mock` khi test offline) |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 bản ghi chuẩn |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày (ngưỡng vi phạm 25%) |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

1. **Baseline Pipeline (Phase 1):**
```bash
python script/run_phase1.py
```

2. **Corruption & Idempotent Repair Flow (Phase 2):**
```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| :--- | :---: | :---: | :--- |
| `run_phase1.py` | Thành công 100% | 2026-09-25 15:24 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| `run_corruption_flow.py` | Thành công 100% | 2026-09-25 15:25 | `data/results/corruption_log.json`, `data/reports/corruption_report.md` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| :--- | :--- |
| Source | Crossref REST API (`https://api.crossref.org/works`) & Snapshot offline |
| Query/filter | `query: machine learning`, `rows: 24` |
| Thời điểm lấy dữ liệu | 2026-09-25 |
| Số record nhận được | 24 bản ghi bài báo khoa học |
| Cơ chế retry/backoff | Timeout 10s, tự động fallback đọc snapshot `data/raw/crossref_response.json` khi API quá tải/mất mạng |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| :--- | :--- | :---: | :--- | :--- |
| `paper_id` | `str` | Có | Mã định danh duy nhất (DOI) | Bỏ qua bản ghi nếu rỗng |
| `title` | `str` | Có | Tiêu đề bài báo | Chuẩn hóa khoảng trắng, bỏ qua nếu rỗng |
| `summary` | `str` | Có | Tóm tắt nghiên cứu | Loại bỏ toàn bộ thẻ XML/HTML `<jats:p>` |
| `authors_joined` | `str` | Có | Chuỗi tác giả nối bằng dấu phẩy | Ghép nối từ mảng `authors` |
| `categories_joined`| `str` | Có | Lĩnh vực chuyên môn | Ghép nối từ mảng `categories` |
| `published` | `str` | Có | Ngày xuất bản (`YYYY-MM-DD`) | Parse date-parts, fallback ngày chạy nếu lỗi |
| `age_days` | `int` | Có | Độ tuổi của bài báo tính theo ngày | `max(0, (ref_date - pub_date).days)` |
| `text_for_embedding`| `str` | Có | Đoạn văn bản hoàn chỉnh để nhúng vector | Ghép nối cấu trúc chuẩn 5 phần |

---

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| :--- | :--- |
| Số câu hỏi | 30 câu hỏi chuẩn hóa |
| Các `question_type` | `summary` (10 câu), `authors` (7 câu), `date` (7 câu), `categories` (6 câu) |
| Ground-truth document ID | DOI bài báo tương ứng trong tập dữ liệu chuẩn |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB persistent local (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k` | 4 |
| LLM provider/model | `gemini` / `gemini-2.5-flash` |
| Test set dùng chung | `data/eval/test_set.json` (giữ nguyên không đổi qua cả 3 trạng thái) |

**Giải thích vì sao test set được giữ nguyên qua 3 trạng thái:**  
Trong phương pháp luận đo lường khoa học, muốn đánh giá chính xác tác động của việc biến đổi dữ liệu (Data Corruption) và mức độ phục hồi (Data Repair), **bộ đề thi (Evaluation Test Set) bắt buộc phải được giữ cố định làm hằng số kiểm soát**. Nếu thay đổi câu hỏi giữa các trạng thái, sự thay đổi của các chỉ số Hit Rate hay Token F1 sẽ bị nhiễu và không còn phản ánh trung thực năng lực của hệ thống.

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| :--- | :--- | :---: | :--- |
| Raw response/records | `data/raw/` | Có | Đầy đủ 2 file raw preservation |
| Cleaned dataset | `data/clean/` | Có | 24 dòng sạch, đủ CSV và JSON |
| Embedding manifest/index | `data/embeddings/` | Có | `papers_embeddings.json` đầy đủ |
| Evaluation set | `data/eval/` | Có | 30 câu hỏi đa dạng trong `test_set.json` |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Ghi nhận Hit Rate 1.0000, F1 1.0000 |
| Quality/freshness | `data/quality/` | Có | Báo cáo GX 1.x và Freshness SLA đầy đủ |
| Baseline report | `data/reports/phase1_report.md` | Có | Markdown report tổng kết chi tiết Pha 1 |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| :--- | :---: | :--- |
| `retrieval_hit_rate` | **1.0000 (100%)** | 30/30 câu hỏi tìm thấy đúng tài liệu nguồn trong Top-4 kết quả |
| `mean_token_f1` | **1.0000** | Độ tương đồng từ vựng tuyệt đối giữa câu trả lời và Ground Truth |
| `judge_accuracy` | **1.0000 (100%)** | Giám khảo LLM xác nhận 100% câu trả lời chuẩn xác về ngữ nghĩa |
| `mean_judge_score` | **5.0000 / 5★** | Điểm số chất lượng tối đa |

---

## 8. Data quality và freshness

### Quality checks (Great Expectations 1.x)

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| :--- | :--- | :--- | :---: | :--- |
| `ExpectTableRowCountToBeBetween` | Completeness | $5 \le N \le 5000$ | Pass (24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` | Completeness | Cấm null `paper_id`, `title`, `text_for_embedding` | Pass (0% null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` | Uniqueness | `paper_id` là duy nhất | Pass (0 trùng lặp) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween`| Validity | `summary` $\ge 30$ ký tự | Pass (độ dài hợp lệ) | `baseline_quality_report.json` |

### Freshness SLA

| Thuộc tính | Giá trị |
| :--- | :--- |
| Vị trí đo lường | `data/clean/papers_clean.csv` |
| Timestamp mới nhất | `2026-07-22` (Bài cũ nhất: `2026-03-28`) |
| Ngưỡng freshness | 180 ngày (tỷ lệ bài cũ $\le 25\%$) |
| Trạng thái baseline | **Fresh ✅ (`is_fresh = True`)** |
| Lý do | Chỉ có 1 bài báo quá hạn 180 ngày (tỷ lệ 4.17% $\le 25\%$). |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Drop latest records** | Cắt bỏ 20% bài báo mới nhất | 4 bài mới | GX Row count giảm, Hit rate giảm | Hit rate các câu hỏi bài mới rớt về 0 | Re-ingest từ raw records |
| **Blank summary** | Xóa rỗng trường tóm tắt | 2 bài | GX summary length $< 30$ báo đỏ | F1 giảm mạnh, context rỗng | Re-clean từ raw snapshot |
| **Inject noise** | Chèn chuỗi ký tự rác | 2 bài | Vector cosine drift | Text embedding bị phân tán | Re-clean từ raw snapshot |
| **Truncate title** | Cắt ngắn tiêu đề còn 6 ký tự | 2 bài | Regex exact match fail | Không tra cứu được theo tên bài | Re-clean từ raw snapshot |
| **Stale date** | Lùi ngày xuất bản về 365 ngày trước | 7 bài | Freshness SLA `is_fresh = False` | Tỷ lệ bài cũ tăng vọt lên 40% | Tính lại `age_days` chuẩn |
| **Duplicate rows** | Nhân đôi 2 dòng ngẫu nhiên | 2 bài | GX `ExpectColumnValuesToBeUnique` Fail | Nhân đôi bản ghi làm loãng vector | Khử trùng lặp `drop_duplicates` |

**Giải thích cơ chế Idempotent Repair:**  
Thay vì sửa đổi chắp vá trên file lỗi (vốn không thể khôi phục lại các tóm tắt và tiêu đề đã bị xóa vĩnh viễn), quy trình phục hồi quay trở lại **nguồn cội dữ liệu thô ban đầu `data/raw/crossref_records.json` (Single Source of Truth)**. Áp dụng lại toàn bộ hàm làm sạch chuẩn `build_clean_dataframe()`, chạy lại kiểm định GX 1.x và tái tạo mới hoàn toàn index vector trên ChromaDB. Tính **Idempotent** đảm bảo rằng dù kích hoạt chạy lại bao nhiêu lần, kết quả dữ liệu đầu ra luôn luôn đồng nhất, sạch sẽ 100% và không sinh ra rác trùng lặp.

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`retrieval_hit_rate`** | **1.0000** | **0.7667** | **1.0000** | `-0.2333` | `+0.2333` | Tụt sâu do mất 20% bài mới và cắt ngắn tiêu đề; khôi phục 100% sau repair. |
| **`mean_token_f1`** | **1.0000** | **0.8785** | **1.0000** | `-0.1215` | `+0.1215` | Sụt giảm do summary bị xóa trắng và chèn ký tự rác; hồi phục trọn vẹn. |
| **`judge_accuracy`** | **1.0000** | **0.9000** | **1.0000** | `-0.1000` | `+0.1000` | AI bị ảo giác trên dữ liệu bẩn; lấy lại độ chính xác hoàn hảo. |
| **`mean_judge_score`** | **5.0000** | **4.4000** | **5.0000** | `-0.6000` | `+0.6000` | Điểm số chất lượng câu trả lời giảm sút và phục hồi về mức 5★ tuyệt đối. |
| **Quality checks (GX)** | **✅ Pass** | **❌ Fail** | **✅ Pass** | Báo động đỏ | Hoàn toàn sạch | Great Expectations phát hiện vi phạm độ dài summary và trùng lặp bản ghi. |
| **Freshness status** | **Fresh ✅** | **Stale ⚠️** | **Fresh ✅** | Vi phạm SLA | Tươi mới trở lại | Bắt được lỗi lùi ngày xuất bản về quá khứ 365 ngày (stale dates). |

### Hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:
1. **[Data Corruption] $\rightarrow$ [Quality Gate Vi Phạm] $\rightarrow$ [RAG Metrics Sụp Đổ (Silent Failure)]:**  
   Khi tiêm lỗi xóa tóm tắt và cắt ngắn tiêu đề, Great Expectations lập tức báo lỗi đỏ (`success = False`). Mặc dù hệ thống không hề ném Runtime Exception (chương trình vẫn chạy mượt), nhưng Retrieval Hit Rate đã sụt giảm nghiêm trọng từ **1.0000 xuống 0.7667**, chứng minh trực quan hiện tượng Silent Failure.
2. **[Idempotent Repair Action] $\rightarrow$ [Quality Recovery] $\rightarrow$ [Agent Metric Recovery]:**  
   Khi kích hoạt lệnh phục hồi dữ liệu từ bản Raw backup, toàn bộ 24 bài báo được tái làm sạch chuẩn, Great Expectations lấy lại trạng thái `Pass = True`, và cả 3 chỉ số Hit Rate, Token F1 cùng LLM Judge Accuracy đều phục hồi **100% về mức 1.0000 ban đầu**.

---

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy `run_corruption_flow.py` trên Windows PowerShell, console ném lỗi `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680'` do mã hóa mặc định `cp1252` của Windows không hiển thị được các emoji trạng thái.
- **Nguyên nhân:** Windows terminal sử dụng codepage mặc định không hỗ trợ ký tự UTF-8 mở rộng khi print trực tiếp ra stdout.
- **Cách xử lý:** Bổ sung cấu hình tự động cấu hình lại `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` ngay đầu entrypoint của các file pipeline.
- **Cách xác minh:** Chạy lại `python script/run_corruption_flow.py` trên PowerShell thoát mã 0 trơn tru, hiển thị bảng số liệu sạch đẹp.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| :--- | :--- | :--- |
| Cơ chế phục hồi dạng kịch bản tuần tự | Cần người vận hành kích hoạt script repair | Triển khai Automated Circuit Breaker tự động trigger repair khi GX phát hiện lỗi |
| Tập dữ liệu thử nghiệm 24 bài báo | Chưa bao quát quy mô lớn hàng triệu vector | Mở rộng benchmark lên 10.000+ tài liệu với ChromaDB HNSW tuning |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác (`Group63-120AnLieng`).
- [x] Phân công khớp với module, artifact và kết quả thực tế của 3 thành viên.
- [x] Lệnh tái hiện (`run_phase1.py` và `run_corruption_flow.py`) đã chạy thành công 100%.
- [x] Baseline, corrupted và repaired dùng chung bộ evaluation set 30 câu hỏi.
- [x] Bảng metrics khớp chính xác với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Tuyệt đối không commit file `.env`, API key, token hoặc secret lên GitHub.
