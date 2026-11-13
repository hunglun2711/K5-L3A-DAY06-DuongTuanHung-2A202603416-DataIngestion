# Day 06 · Data Ingestion Engineering (Bài nộp cá nhân)

- **Học viên:** Dương Tuấn Hưng (`2A202603416`, lớp `L3A`) — [STUDENT.md](STUDENT.md)
- **Báo cáo cá nhân:** [report/individual/2A202603416_DuongTuanHung.md](report/individual/2A202603416_DuongTuanHung.md)

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| **41 trang nội dung hợp lệ** (44 trang vật lý, 4 file PDF OpenStax, CC BY 4.0) | **3 cấu hình** (A: fixed 500/50, B: paragraph 800, C: paragraph 800 + filter `section`) | **24 câu hỏi** (18 `dev` / 6 `test`, gồm 6 câu `filter`) |

---

## 1. Cấu trúc bài nộp

- [data/manifest.json](data/manifest.json) — Manifest nguồn OpenStax *Introduction to Python Programming* (CC BY 4.0), số trang vật lý/hợp lệ, danh sách trang bị loại và quy tắc tính trang.
- `starter/data/*.pdf` — 4 trích đoạn chương (`ch01`, `ch03`, `ch04`, `ch05`) với tổng 44 trang vật lý / 41 trang nội dung hợp lệ.
- [benchmark/questions.json](benchmark/questions.json) & [benchmark/verification_report.json](benchmark/verification_report.json) — 24 câu hỏi (`18 dev / 6 test`) đã kiểm chứng `evidence_quote` tồn tại nguyên văn trên trang nguồn trước khi chạy truy xuất.
- `starter/src/` — Mã nguồn pipeline hoàn chỉnh:
  - [ingestion.py](starter/src/ingestion.py) — Đọc PDF bằng `pypdf`, chuẩn hóa Unicode `NFC`, loại footer chạy trang, khôi phục đoạn văn và ghi log trang loại/lỗi.
  - [chunking.py](starter/src/chunking.py) — `fixed_size(size=500, overlap=50)` và `by_paragraph(max_size=800)`.
  - [embeddings.py](starter/src/embeddings.py) — Adapter `MyEmbedder` gọi OpenRouter (`openai/text-embedding-3-small`, 1536 chiều) kèm cache cục bộ và theo dõi token/chi phí.
  - [store.py](starter/src/store.py) — Hiện thực cả `PgVectorStore` (PostgreSQL + pgvector) và `QdrantVectorStore` (Qdrant persistent local, metric Cosine, exact search, idempotent upsert + metadata filter).
  - [evaluation.py](starter/src/evaluation.py) — Chấm `Hit@1`, `Evidence Hit@3`, kiểm tra metadata và tuân thủ filter.
  - [run.py](starter/src/run.py) — Chạy toàn bộ pipeline A/B/C, kiểm tra nạp lại không trùng lặp và xuất trace/metrics.
- [artifacts/experiment_log.csv](artifacts/experiment_log.csv) — Nhật ký cấu hình, giả thuyết và kết quả A/B/C.
- `results/` — Kết quả thực tế: [metrics_summary.json](results/metrics_summary.json), [ingestion_log.json](results/ingestion_log.json), [environment_log.json](results/environment_log.json), [reingest_check.json](results/reingest_check.json), [traces_A.json](results/traces_A.json), [traces_B.json](results/traces_B.json), [traces_C.json](results/traces_C.json), [coherence_positions.json](results/coherence_positions.json), [manual_audit.json](results/manual_audit.json), [manual_audit_report.md](results/manual_audit_report.md).

---

## 2. Thiết lập và lệnh chạy tái lập

### Yêu cầu môi trường
- Python **3.11–3.14** (đã kiểm chứng trên Python `3.14.4`).
- File `starter/.env` (copy từ [starter/.env.example](starter/.env.example), điền `OPENROUTER_API_KEY` của bạn và `EMBEDDING_MODEL=openai/text-embedding-3-small`). **Không commit `.env`**.

### Cài đặt thư viện & chạy pipeline

```powershell
cd starter
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Điền OPENROUTER_API_KEY vào starter/.env
python -m src.run
```

Tùy chọn tái tạo dữ liệu PDF từ OpenStax & kiểm chứng benchmark từ thư mục gốc:

```powershell
python starter/scripts/prepare_corpus.py
python starter/scripts/verify_benchmark.py
python starter/scripts/generate_manual_audit.py
```

### Lưu ý về Vector Store (Docker/WSL Fallback)
- Khi kiểm tra Docker Desktop trên máy thực hành, Docker Linux Engine báo lỗi `Wsl/WSL_E_WSL_OPTIONAL_COMPONENT_REQUIRED` (`500 Internal Server Error` trên pipe `dockerDesktopLinuxEngine` do Windows chưa bật thành phần tùy chọn WSL, cần quyền Admin và khởi động lại máy).
- Theo đúng [GUIDE.md](GUIDE.md) và [RULES.md](RULES.md), `starter/src/run.py` mặc định chạy **`QdrantVectorStore` lưu bền vững trên đĩa** (`starter/qdrant_storage/`, metric Cosine, exact search) và ghi nhận lý do tại [results/environment_log.json](results/environment_log.json). Nếu máy người chấm đã bật Docker + pgvector (`docker compose -p day6_student_starter up -d --wait`), có thể đặt biến môi trường `USE_PGVECTOR=1` trong `starter/.env` để chạy trên `PgVectorStore`.

---

## 3. Tóm tắt kết quả thực tế

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Filter tuân thủ | Coherence (/2) | Grounding (/2) |
|---|---|---:|---:|---:|---:|---:|
| A (`fixed_size 500/50`) | `dev` / `test` | `9/18` / `3/6` | `13/18` / `4/6` | N/A | `0.00` | `1.67` |
| B (`by_paragraph 800`) | `dev` / `test` | `10/18` / `5/6` | `15/18` / `5/6` | N/A | `1.80` | `1.83` |
| C (`by_paragraph 800 + filter`) | `dev` / `test` | `10/18` / `5/6` | `15/18` / `5/6` | `4/4` (dev) · `2/2` (test) | `1.80` | `1.83` |

Chi tiết phân tích năm tiêu chí và hai ví dụ lỗi xem tại [report/individual/2A202603416_DuongTuanHung.md](report/individual/2A202603416_DuongTuanHung.md).
