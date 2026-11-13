# Manual Audit Report — Day 06 Benchmark

- **Người chấm:** Dương Tuấn Hưng (tác giả — có ghi nhận rủi ro thiên lệch tự chấm theo RULES.md)
- **Quy tắc chọn mẫu Coherence:** 10 vị trí `(document_id, page)` đầu tiên theo thứ tự sắp xếp (`openstax-py-ch01` trang 4–13), chốt trước khi đọc điểm số.

## 1. Chunk Coherence (10 vị trí × 3 chiến lược, thang 0–2)

| Vị trí | Chiến lược A (0–2) | Lý do A | Chiến lược B & C (0–2) | Lý do B & C |
|---|---:|---|---:|---|
| `openstax-py-ch01` p.4 | 0 | fix_00 cắt giữa câu ('Learning how to program computers'), fix_01 bắt đầu và kết thúc giữa từ ('ss other needs...', 'assignin'). | 2 | para_00 giữ trọn Chapter Outline; para_01 giữ nguyên đoạn Introduction; para_02 giữ ngữ cảnh [Introduction] và hai đoạn còn lại trọn vẹn. |
| `openstax-py-ch01` p.5 | 0 | Cắt giữa từ ở cả 4 chunk đầu ('accomplish eve', 'CHECKP', 'that show') và tạo chunk dư 72 ký tự ('w how to write...'). | 1 | Đoạn văn 1.1 Background và Learning Objectives trọn vẹn (para_00), nhưng câu hỏi trắc nghiệm số 2 bị tách đáp án a và b/c sang para_02. |
| `openstax-py-ch01` p.6 | 0 | fix_00/01/02/03 đều cắt giữa từ ('Pyth', 'wid', 'considera') và chia đôi đoạn định nghĩa Standard Library/Pandas. | 2 | para_01 giữ trọn đoạn giải thích Standard Library và Pandas kèm tiêu đề [The Python language]; para_02 và para_03 giữ trọn phần syntax và Example 1.1. |
| `openstax-py-ch01` p.7 | 0 | Cắt giữa từ và câu lệnh hướng dẫn ('expec', 'ile.', 'progr', 'Bas'). | 2 | para_00 giữ trọn mục Python vs Java syntax; para_01 giữ trọn ví dụ Favorite song và Learning objectives; para_02 giữ trọn mục Basic output. |
| `openstax-py-ch01` p.8 | 0 | fix_00 cắt ngang Table 1.1 ('Today is Monday'); fix_01 bắt đầu bằng 'y.")' và cắt giữa từ 'Displ'. | 1 | para_00 giữ trọn lý thuyết sep/end, nhưng Table 1.1 bị tách đôi sang para_01 khiến para_01 mở đầu bằng hàng dữ liệu không có tiêu đề bảng. |
| `openstax-py-ch01` p.9 | 0 | fix_00 cắt ngang cụm 'has th'; fix_01 cắt giữa danh sách 3 thành phần của input() ('waiting' / 'hort message'). | 2 | para_01 gom trọn mục Basic input cùng đầy đủ 3 thành phần của variable = input("prompt") trong một chunk tự hiểu được. |
| `openstax-py-ch01` p.10 | 0 | fix_00/01/02 cắt giữa từ ('progra', 't.', 'ht', 'inpu') và tách bài thơ Robert Frost khỏi phần đề bài. | 2 | para_00 giữ trọn Q6 và đề bài Frost poem + Tip; para_01 giữ trọn khổ thơ và bài tập Name and likes. |
| `openstax-py-ch01` p.11 | 0 | fix_00 cắt giữa từ 'mathemat'; fix_01 tách đề câu hỏi Q1 khỏi các lựa chọn ở fix_02. | 2 | para_00 giữ trọn 1.3 Variables và Assignment statement; para_01 giữ trọn 4 câu hỏi CONCEPTS IN PRACTICE. |
| `openstax-py-ch01` p.12 | 0 | fix_00 cắt giữa từ 'descr'; fix_01 cắt đôi bảng Table 1.2 Keywords giữa chừng. | 2 | para_00 giữ trọn đoạn Variable naming rules; para_01 giữ trọn phần Keywords (Table 1.2) kèm tiêu đề ngữ cảnh [Variable naming rules]. |
| `openstax-py-ch01` p.13 | 0 | fix_01 cắt giữa định nghĩa String ('A string is a sequence of'); fix_02 cắt giữa bảng Table 1.3 ('"W'). | 2 | para_00 giữ trọn bài tập Final score; para_01 giữ trọn phần Quote marks và Table 1.3 Rules for strings. |

- **Trung bình A:** `0.0/2` (phân bố 0/1/2 = `[10, 0, 0]`)
- **Trung bình B & C:** `1.8/2` (phân bố 0/1/2 = `[0, 2, 8]`)

## 2. Metadata Usefulness (6 câu test × top-3 = 18 bản ghi/chiến lược)

- **Độ đúng & đủ metadata (`document_id`, `source`, `page`, `section`):** A = `18/18`, B = `18/18`, C = `18/18`.
- **Tuân thủ filter (test):** A = `N/A`, B = `N/A`, C = `2/2` (dev của C = `4/4`).

## 3. Grounding Quality (6 câu test, thang 0–2)

| Câu test | A (0–2) | Lý do A | B (0–2) | Lý do B | C (0–2) | Lý do C |
|---|---:|---|---:|---|---:|---|
| `q19` | 1 | Rank #1 (fix_01) có định nghĩa library và Standard Library nhưng cắt giữa câu về Pandas ('Ex: Pandas ... is a wid'); thiếu phần kết luận vai trò của Pandas. | 2 | Rank #1 (openstax-py-ch01_p06_para_01) chứa trọn đoạn Standard Library và câu hoàn chỉnh về Pandas, truy nguồn chính xác trang 6. | 2 | Giống B: Rank #1 chứa trọn vẹn bằng chứng Standard Library và Pandas. |
| `q20` | 2 | Rank #1 là nhiễu từ Chương 5, nhưng Rank #2 (openstax-py-ch03_p01_fix_01) chứa đủ định nghĩa container và danh sách/tuple để trả lời và truy nguồn. | 2 | Rank #1 (openstax-py-ch03_p01_para_01) chứa trọn phần Introduction định nghĩa container, lists/tuples và mục tiêu 3.1 Strings revisited. | 2 | Giống B: Rank #1 chứa trọn vẹn định nghĩa container và lists/tuples. |
| `q21` | 2 | Rank #1 (openstax-py-ch04_p02_fix_00) chứa đầy đủ bool data type, giá trị true/false và quy tắc viết hoa bắt buộc. | 2 | Rank #1 (openstax-py-ch04_p02_para_00) chứa trọn phần bool data type và quy tắc viết hoa. | 2 | Giống B: Rank #1 chứa trọn vẹn định nghĩa bool và quy tắc viết hoa. |
| `q22` | 2 | Rank #1 (openstax-py-ch05_p02_fix_00) chứa nguyên văn hai gạch đầu dòng xử lý khi điều kiện True và False. | 2 | Rank #1 (openstax-py-ch05_p02_para_00) chứa nguyên văn điều kiện True/False trong while loop. | 2 | Giống B: Rank #1 chứa trọn vẹn hành vi while loop khi True/False. |
| `q23` | 1 | Rank #1 (openstax-py-ch03_p11_fix_01) bị cắt mất vế đầu ('Calling a function like id() or type('), chỉ còn ') returns information...'; người đọc phải tự suy ra từ Rank #2/#3 trang 10. | 1 | Rank #1 (openstax-py-ch03_p10_para_02) nêu đúng id() và type() mô tả object nhưng thiếu trang 11 khẳng định biến không có identity/type; Rank #3 còn nhiễu sang Chương 1. | 1 | Filter section='ch03_data_types' loại bỏ nhiễu Chương 1 ở Rank #3 (thay bằng ch03 trang 9), nhưng vẫn chưa kéo được trang 11 vào top-3 nên thiếu câu khẳng định biến không có identity/type. |
| `q24` | 2 | Rank #1 (openstax-py-ch05_p05_fix_00) chứa đầy đủ 3 loại container và Rank #2 bổ sung giải thích chuỗi gồm nhiều ký tự. | 2 | Rank #1 (openstax-py-ch05_p05_para_00) chứa đầy đủ 3 loại container và giải thích for loop duyệt chuỗi (dù Rank #2 nhiễu sang Chương 3). | 2 | Filter section='ch05_loops' giữ cả top-3 trong Chương 5 (loại bỏ nhiễu Chương 3 ở Rank #2 của B), Rank #1 chứa đủ bằng chứng. |

- **Grounding A:** phân bố 0/1/2 = `0/2/4`, trung bình = `1.67/2`
- **Grounding B:** phân bố 0/1/2 = `0/1/5`, trung bình = `1.83/2`
- **Grounding C:** phân bố 0/1/2 = `0/1/5`, trung bình = `1.83/2`
