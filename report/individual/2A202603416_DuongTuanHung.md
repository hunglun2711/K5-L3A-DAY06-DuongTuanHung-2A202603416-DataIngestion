# Báo cáo cá nhân — Day 6

- **Học viên:** Dương Tuấn Hưng · **MSSV:** `2A202603416` · **Lớp:** `L3A`
- **Công cụ AI hỗ trợ:** Có sử dụng AI hỗ trợ thiết kế code pipeline, script kiểm chứng và tổng hợp bảng; toàn bộ dữ liệu PDF gốc, `evidence_quote`, trace truy xuất, chỉ số đo đạc và đánh giá thủ công đều được kiểm tra trực tiếp trên file kết quả thực tế (không giả lập số liệu).

---

## Dữ liệu và pipeline

- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - **Nguồn:** Giáo trình mở *Introduction to Python Programming* của **OpenStax, Rice University** ([PDF gốc](https://assets.openstax.org/oscms-prodcms/media/documents/Introduction_to_Python_Programming-WEB.pdf)), giấy phép **Creative Commons Attribution 4.0 International (CC BY 4.0)**, trích xuất ngày `2026-11-13` vào 4 file PDF trong `starter/data/` và lập chỉ mục trong [data/manifest.json](../../data/manifest.json):
    1. `openstax-py-ch01` ([openstax_python_ch01_intro.pdf](../../starter/data/openstax_python_ch01_intro.pdf)) — `section = ch01_statements_variables`: 13 trang vật lý, **10 trang nội dung hợp lệ** (trang 4–13; loại trang 1 trống 0 ký tự, trang 2 bìa 205 ký tự, trang 3 mục lục `CONTENTS` 755 ký tự).
    2. `openstax-py-ch03` ([openstax_python_ch03_types.pdf](../../starter/data/openstax_python_ch03_types.pdf)) — `section = ch03_data_types`: 11 trang vật lý, **11 trang nội dung hợp lệ** (trang 1–11).
    3. `openstax-py-ch04` ([openstax_python_ch04_branching.pdf](../../starter/data/openstax_python_ch04_branching.pdf)) — `section = ch04_branching`: 10 trang vật lý, **10 trang nội dung hợp lệ** (trang 1–10).
    4. `openstax-py-ch05` ([openstax_python_ch05_loops.pdf](../../starter/data/openstax_python_ch05_loops.pdf)) — `section = ch05_loops`: 10 trang vật lý, **10 trang nội dung hợp lệ** (trang 1–10).
  - **Tổng hợp:** **44 trang vật lý** → **41 trang nội dung hợp lệ** (vượt mức tối thiểu 30 trang), **3 trang bị loại**, tổng **53.827 ký tự** sau chuẩn hóa của pipeline (`0` lỗi trích xuất), ghi tại [results/ingestion_log.json](../../results/ingestion_log.json).
  - **Quy tắc tính trang:** Đọc từng trang PDF bằng `pypdf==6.21.4`; loại trang rỗng (0 ký tự), trang mục lục bắt đầu bằng `CONTENTS`, hoặc trang bìa/tiêu đề có dưới 250 ký tự chuẩn hóa.

- **Chuẩn hóa, lỗi và giới hạn:**
  - Hàm `normalize_text()` trong [starter/src/ingestion.py](../../starter/src/ingestion.py) chuẩn hóa Unicode `NFC`, nối từ bị ngắt gạch nối qua dòng, loại bỏ footer chạy trang (`Access for free at openstax.org`, số trang đầu/cuối trang) và khôi phục dấu ngắt đoạn `\n\n` dựa trên tiêu đề mục và câu kết thúc dấu chấm.
  - **Giới hạn đã ghi nhận:** Bảng biểu hai cột trong PDF (ví dụ Table 1.1 ở `ch01` tr.8, Table 3.3 ở `ch03` tr.7) khi trích bằng `pypdf` bị trải thành text tuyến tính, có thể làm mất ranh giới cột; câu hỏi và bài tập `CONCEPTS IN PRACTICE` trộn xen kẽ với phần lý thuyết trên cùng một trang.

- **Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí:**
  - **Embedding model:** `openai/text-embedding-3-small` qua **OpenRouter** (`/api/v1/embeddings`), **1536 chiều**, dùng chung cho cả document và query ở cả ba cấu hình A, B, C.
  - **Vector store & phương án dự phòng Docker:** Theo thiết kế ban đầu dự định chạy Docker PostgreSQL + pgvector (`PgVectorStore` đã cài đặt sẵn trong [starter/src/store.py](../../starter/src/store.py)), nhưng kiểm tra thực tế trên máy Windows gặp lỗi `Wsl/WSL_E_WSL_OPTIONAL_COMPONENT_REQUIRED` (`500 Internal Server Error` tại pipe `dockerDesktopLinuxEngine` vì Windows Optional Component cho WSL chưa bật, đòi hỏi quyền Admin + khởi động lại máy). Tuân thủ [GUIDE.md](../../GUIDE.md) và [RULES.md](../../RULES.md), pipeline sử dụng **`QdrantVectorStore`** (`qdrant-client==1.20.0`, lưu bền vững trên đĩa tại `starter/qdrant_storage/`, collection `day6_chunks`, metric **Cosine**, tìm kiếm **exact brute-force**) và ghi lại nguyên nhân đầy đủ trong [results/environment_log.json](../../results/environment_log.json).
  - **Kiểm tra nạp lại (idempotency):** Chạy `upsert` lại toàn bộ Strategy A cho kết quả `count_before = 135`, `count_after = 135`, `no_duplicates = true` ([results/reingest_check.json](../../results/reingest_check.json)).
  - **Lệnh chạy tái lập:** Từ thư mục `starter/`: `python -m src.run`.
  - **Chi phí API thực tế:**
    - Lần chạy 1 (embed A 135 chunks + B cũ + 24 queries): **31.900 tokens = \$0.000638**.
    - Lần chạy 2 chốt bài sau tinh chỉnh `by_paragraph`: embed phần B mới (`9.895 tokens = \$0.0001979`), dùng cache cho A và queries (`\$0.00`), C dùng lại vector đã cache của B (`\$0.00`). Chi phí nội tại (intrinsic) cho A là `15.127 tokens (\$0.00030254)`, cho B và C là `13.949 tokens (\$0.00027898)`.

- **Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:**
  - **Bắt buộc:** `document_id`, `source` (đường dẫn file PDF), `page` (số trang vật lý trong file trích xuất).
  - **Bổ sung:** `section` (`ch01_statements_variables`, `ch03_data_types`, `ch04_branching`, `ch05_loops`), `chapter`, `year` (`2024`), `license` (`CC BY 4.0`). Tất cả lấy trực tiếp từ mục lục và bản quyền sách trong [data/manifest.json](../../data/manifest.json), không suy đoán.
  - **Lý do chọn `section` để lọc:** Nhiều khái niệm Python như `input()`, biến, `=`, `print()`, `container` lặp lại ở nhiều chương với ngữ cảnh khác nhau; trường `section` (kiểu `string`) giúp khoanh vùng đúng chương khi người dùng hoặc ngữ cảnh câu hỏi chỉ định phạm vi.

---

## Cấu hình và benchmark

- **A / B / C (tham số cụ thể, khác biệt duy nhất B–C):**
  - **Cấu hình A:** `fixed_size(size=500, overlap=50)` ký tự; gắn đầy đủ metadata (`document_id`, `source`, `page`, `section`, `chapter`, `year`, `license`); **không dùng filter** khi truy xuất.
  - **Cấu hình B:** `by_paragraph(max_size=800)` ký tự (gom theo tiêu đề mục và đoạn văn, chèn `[heading]` một lần khi bắt đầu chunk nối tiếp, tách đoạn quá dài theo ranh giới câu); gắn cùng metadata như A; **không dùng filter**. *(So sánh A–B chỉ thay đổi chiến lược chunking).*
  - **Cấu hình C:** Giống hệt chunking và metadata của B (`by_paragraph(max_size=800)`), **chỉ bổ sung metadata filter `section`** khi câu hỏi có trường `filter` trong ngữ cảnh (các câu không có `filter` chạy không lọc). *(So sánh B–C chỉ thay đổi bước metadata filtering).*

- **24 câu hỏi: phân chia 18 dev / 6 test, câu metadata filter và cách kiểm chứng evidence:**
  - Bộ benchmark tại [benchmark/questions.json](../../benchmark/questions.json) gồm **24 câu** (18 `dev` / 6 `test`), chia đều qua 4 chương và 4 dạng: `direct`, `paraphrase`, `conditional_exception`, `metadata_filter`.
  - Có **6 câu metadata filter** (`4 dev`: `q04`, `q08`, `q12`, `q16`; `2 test`: `q23`, `q24`) dựa trên ngữ cảnh chương mà không đưa `gold_source_id` hay đáp án vào câu hỏi/filter.
  - **Kiểm chứng trước khi chạy:** Script [starter/scripts/verify_benchmark.py](../../starter/scripts/verify_benchmark.py) kiểm tra toàn bộ 24 `evidence_quote` tồn tại nguyên văn trên trang nguồn sau chuẩn hóa (`all_evidence_verified = true`, lưu tại [benchmark/verification_report.json](../../benchmark/verification_report.json)). Tập dev/test được chốt cố định trước khi truy xuất và không chỉnh sửa benchmark theo kết quả test.

- **Tiêu chí chọn chiến lược đã chốt trước khi xem test:**
  1. Ưu tiên cao nhất cho **Evidence Hit@3** (độ phủ bằng chứng đúng trong top-3) và **Grounding Quality** (khả năng cung cấp đủ điều kiện/ngoại lệ để trả lời đúng).
  2. Tiếp theo là **Chunk Coherence** (mạch lạc, không cắt ngang ý) và **Metadata Filter Compliance** (không lọt nhiễu ngoài phạm vi khi người dùng yêu cầu lọc).
  3. Sau cùng là số chunk, thời gian nạp và chi phí embedding.

---

## Kết quả

### Bảng 1: Hiệu năng truy xuất và tài nguyên (`dev = 18 câu`, `test = 6 câu`)

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---:|---:|---:|---:|---:|
| A (`fixed_size 500/50`) | `dev` | 9/18 (50.0%) | 13/18 (72.2%) | 135 | 0.824s (cache; 17.894s API đầu) | \$0.00030254 (intrinsic) |
| A (`fixed_size 500/50`) | `test` | 3/6 (50.0%) | 4/6 (66.7%) | 135 | 0.824s (cache; 17.894s API đầu) | \$0.00030254 (intrinsic) |
| B (`by_paragraph 800`) | `dev` | 10/18 (55.6%) | 15/18 (83.3%) | 95 | 0.503s (cache; 8.057s API đầu) | \$0.00027898 (intrinsic) |
| B (`by_paragraph 800`) | `test` | 5/6 (83.3%) | 5/6 (83.3%) | 95 | 0.503s (cache; 8.057s API đầu) | \$0.00027898 (intrinsic) |
| C (`by_paragraph 800 + filter`) | `dev` | 10/18 (55.6%) | 15/18 (83.3%) | 95 | 0.502s (cache) | \$0.00027898 (intrinsic; \$0.00 mới) |
| C (`by_paragraph 800 + filter`) | `test` | 5/6 (83.3%) | 5/6 (83.3%) | 95 | 0.502s (cache) | \$0.00027898 (intrinsic; \$0.00 mới) |

*Phân bố độ dài chunk:* A có min=59, median=500.0, mean=433.25, max=500 ký tự; B và C có min=27, median=644.0, mean=573.44, max=796 ký tự. Cảnh báo đứt đoạn bằng chứng (`split_evidence_warnings`): A có **3 câu dev + 2 câu test**, còn B và C đều bằng **0**.

### Bảng 2: Đánh giá thủ công Coherence, Metadata và Grounding

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---:|---:|---:|---|
| A | 0.00/2 (`n=10`: `10/0/0`) | 18/18 (test); 54/54 (dev) | N/A | `0 / 2 / 4` · Trung bình **1.67/2** |
| B | 1.80/2 (`n=10`: `0/2/8`) | 18/18 (test); 54/54 (dev) | N/A | `0 / 1 / 5` · Trung bình **1.83/2** |
| C | 1.80/2 (`n=10`: `0/2/8`) | 18/18 (test); 54/54 (dev) | `2/2` (test); `4/4` (dev) | `0 / 1 / 5` · Trung bình **1.83/2** |

- **Đường dẫn trace, nhãn thủ công và cách chọn mẫu:**
  - Traces đầy đủ: [results/traces_A.json](../../results/traces_A.json), [results/traces_B.json](../../results/traces_B.json), [results/traces_C.json](../../results/traces_C.json), tổng hợp chỉ số tại [results/metrics_summary.json](../../results/metrics_summary.json).
  - Mẫu 10 vị trí Coherence (chọn trước theo 10 trang hợp lệ đầu tiên đã sắp xếp `openstax-py-ch01` trang 4–13): [results/coherence_positions.json](../../results/coherence_positions.json).
  - Nhãn audit thủ công và lý giải từng trường hợp: [results/manual_audit.json](../../results/manual_audit.json) và [results/manual_audit_report.md](../../results/manual_audit_report.md).
  - Lưu ý người chấm: tác giả tự thực hiện chấm thủ công nên có rủi ro thiên lệch xác nhận; mọi nhận xét đều gắn trực tiếp với `chunk_id` và văn bản thực tế trong trace.

---

## Phân tích và kết luận

- **So sánh A–B (tác động của chunking):**
  - Chuyển từ cắt cứng 500 ký tự (A) sang gom đoạn văn có ngữ cảnh heading tối đa 800 ký tự (B) giúp **giảm 29.6% số lượng chunk** (135 → 95), giảm chi phí embedding nội tại (`\$0.00030254` → `\$0.00027898`), nâng **Evidence Hit@3 trên dev từ 13/18 (72.2%) lên 15/18 (83.3%)**, nâng **Hit@1 trên test từ 3/6 (50.0%) lên 5/6 (83.3%)**, nâng **Coherence trung bình từ 0.00/2 lên 1.80/2**, và triệt tiêu hoàn toàn lỗi cắt đứt `evidence_quote` (`split_evidence_warnings`: 5 → 0).
- **So sánh B–C (tác động của metadata filter):**
  - Trên tập dữ liệu 4 chương này, `Hit@1` và `Evidence Hit@3` của B và C bằng nhau (`10/18`, `15/18` dev; `5/6`, `5/6` test) vì embedding `text-embedding-3-small` đã đặt đúng đoạn văn mục tiêu ở top-1 hoặc top-2. Tuy nhiên, **C loại bỏ hoàn toàn nhiễu xuyên chương trong top-3**: ví dụ ở `q23` (`test`), B trả về hạng #3 là `openstax-py-ch01_p11_para_00` (Chương 1), còn C lọc `section="ch03_data_types"` nên giữ hạng #3 trong Chương 3 (`openstax-py-ch03_p09_para_01`); ở `q24` (`test`), B trả về hạng #2 là `openstax-py-ch03_p01_para_01` (Chương 3 nói về container list/tuple), còn C lọc `section="ch05_loops"` nên giữ cả top-3 thuộc Chương 5 (`2/2` test và `4/4` dev tuân thủ filter).
- **2 ví dụ sai cụ thể (có ID câu và nguồn):**
  1. **Ví dụ lỗi do chunking cắt ngang — `q19` (`test`, nguồn `openstax-py-ch01` trang 6):**
     - Ở **A**, chunk hạng #1 `openstax-py-ch01_p06_fix_01` bị cắt đúng giữa câu minh họa thư viện: `"...Ex: Pandas (https://openstax.org/r/100pandas) is a wid"`, khiến `Evidence Hit@3` bị đánh dấu `False` (`split_evidence_warning=True`, Grounding=1). Ở **B** và **C**, chunk `openstax-py-ch01_p06_para_01` giữ trọn đoạn Standard Library + Pandas nên đạt `Hit@1 = True` (score `0.6787`) và Grounding=2.
  2. **Ví dụ lỗi do truy xuất ngữ nghĩa/ngữ cảnh liên trang — `q08` (`dev`, nguồn `openstax-py-ch03` trang 10) và `q23` (`test`, nguồn `openstax-py-ch03` trang 11):**
     - Ở `q08` (hỏi 3 thuộc tính của object và điều gì đổi khi gán lại `rating`), cả **A, B, C** đều kéo trang 11 (`rating = 10 ... rating = "ten"`) lên hạng #1–#2 thay vì trang 10 (nơi liệt kê 3 thuộc tính `identity, type, value`), dẫn đến `Hit@3 = False`. Tương tự ở `q23` (`test`), cả B và C đều kéo trang 10 (`[Properties of objects]`) lên hạng #1 (`0.5826`) và trang 9 lên hạng #2–#3, bỏ sót trang 11 (nơi giải thích biến không có identity/type). Nguyên nhân: hai trang 10–11 cùng nói về `id()`, `type()` và `rating`, trong khi chỉ mục trang 11 bắt đầu bằng mục `CONCEPTS IN PRACTICE` trước khi tới `EXPLORING FURTHER`.

- **Chiến lược chọn, đánh đổi, điều kiện áp dụng:**
  - **Chọn Chiến lược C (`by_paragraph max_size=800` + `section` filter có điều kiện)** theo tiêu chí đã chốt: đạt cùng mức Hit@3 và Grounding cao nhất (`15/18` dev, `5/6` test, Grounding `1.83/2`, Coherence `1.80/2`), ít chunk hơn 29.6% so với A, và bảo đảm phạm vi chương `100%` khi có metadata filter.
  - **Đánh đổi & điều kiện áp dụng:** Cấu hình B/C phụ thuộc giả định tài liệu có cấu trúc đoạn/heading rõ và có thể tạo vài chunk rất ngắn cuối trang (min=27 ký tự như `openstax-py-ch03_p09_para_02` chỉ chứa phần đuôi đáp án + footer section); metadata filter ở C chỉ phát huy tác dụng khi người dùng/ứng dụng cung cấp được `section` chính xác trước lúc truy vấn — nếu lọc sai `section`, câu trả lời đúng sẽ bị loại bỏ hoàn toàn.

- **Hạn chế của dữ liệu, nhãn, test nhỏ, đo thời gian/chi phí:**
  - Tập `test` chỉ có 6 câu (và 2 câu có filter) nên độ chính xác chịu sai số mẫu lớn (1 câu đổi nhãn làm thay đổi ±16.7%).
  - Dữ liệu là sách giáo trình tiếng Anh cắt 4 chương (41 trang hợp lệ), chứa nhiều bài tập trắc nghiệm xen kẽ lý thuyết; chưa có bước tách riêng khối `CONCEPTS IN PRACTICE` khỏi phần lý thuyết.
  - Thời gian chạy A và C trong lần chạy cuối phản ánh thời gian đọc cache embedding local (`0.93s` và `0.63s`), không phản ánh độ trễ gọi API mạng lần đầu (~`17.9s` cho A, `11.4s` cho B trước khi cache).

- **Nếu làm lại hoặc mở rộng, cải tiến gì?**
  1. Gộp các đoạn quá ngắn cuối trang (< 120 ký tự) hoặc nội dung liền mạch xuyên trang (như `ch03` tr.10–11) kèm metadata đa trang (`pages: [10, 11]`) để khắc phục lỗi như `q08` và `q23`.
  2. Thử nghiệm **hybrid retrieval (BM25 + dense vector)** hoặc reranking trên tập `dev` để tăng `Hit@1` cho các câu có tên hàm/ký hiệu chính xác (`ord()`, `chr()`, `id()`, `type()`).
  3. Bật Windows WSL optional component (`wsl --install --no-distribution`) và khởi động lại máy để kiểm chứng thêm trên `PgVectorStore` Docker đã viết sẵn trong [starter/src/store.py](../../starter/src/store.py).
