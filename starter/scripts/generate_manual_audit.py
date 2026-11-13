"""Produce verifiable manual audit files (JSON + Markdown) for all 5 benchmark dimensions."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

COHERENCE_ASSESSMENTS = [
    {
        "document_id": "openstax-py-ch01",
        "page": 4,
        "A_score": 0,
        "A_reason": "fix_00 cắt giữa câu ('Learning how to program computers'), fix_01 bắt đầu và kết thúc giữa từ ('ss other needs...', 'assignin').",
        "BC_score": 2,
        "BC_reason": "para_00 giữ trọn Chapter Outline; para_01 giữ nguyên đoạn Introduction; para_02 giữ ngữ cảnh [Introduction] và hai đoạn còn lại trọn vẹn.",
    },
    {
        "document_id": "openstax-py-ch01",
        "page": 5,
        "A_score": 0,
        "A_reason": "Cắt giữa từ ở cả 4 chunk đầu ('accomplish eve', 'CHECKP', 'that show') và tạo chunk dư 72 ký tự ('w how to write...').",
        "BC_score": 1,
        "BC_reason": "Đoạn văn 1.1 Background và Learning Objectives trọn vẹn (para_00), nhưng câu hỏi trắc nghiệm số 2 bị tách đáp án a và b/c sang para_02.",
    },
    {
        "document_id": "openstax-py-ch01",
        "page": 6,
        "A_score": 0,
        "A_reason": "fix_00/01/02/03 đều cắt giữa từ ('Pyth', 'wid', 'considera') và chia đôi đoạn định nghĩa Standard Library/Pandas.",
        "BC_score": 2,
        "BC_reason": "para_01 giữ trọn đoạn giải thích Standard Library và Pandas kèm tiêu đề [The Python language]; para_02 và para_03 giữ trọn phần syntax và Example 1.1.",
    },
    {
        "document_id": "openstax-py-ch01",
        "page": 7,
        "A_score": 0,
        "A_reason": "Cắt giữa từ và câu lệnh hướng dẫn ('expec', 'ile.', 'progr', 'Bas').",
        "BC_score": 2,
        "BC_reason": "para_00 giữ trọn mục Python vs Java syntax; para_01 giữ trọn ví dụ Favorite song và Learning objectives; para_02 giữ trọn mục Basic output.",
    },
    {
        "document_id": "openstax-py-ch01",
        "page": 8,
        "A_score": 0,
        "A_reason": "fix_00 cắt ngang Table 1.1 ('Today is Monday'); fix_01 bắt đầu bằng 'y.\")' và cắt giữa từ 'Displ'.",
        "BC_score": 1,
        "BC_reason": "para_00 giữ trọn lý thuyết sep/end, nhưng Table 1.1 bị tách đôi sang para_01 khiến para_01 mở đầu bằng hàng dữ liệu không có tiêu đề bảng.",
    },
    {
        "document_id": "openstax-py-ch01",
        "page": 9,
        "A_score": 0,
        "A_reason": "fix_00 cắt ngang cụm 'has th'; fix_01 cắt giữa danh sách 3 thành phần của input() ('waiting' / 'hort message').",
        "BC_score": 2,
        "BC_reason": "para_01 gom trọn mục Basic input cùng đầy đủ 3 thành phần của variable = input(\"prompt\") trong một chunk tự hiểu được.",
    },
    {
        "document_id": "openstax-py-ch01",
        "page": 10,
        "A_score": 0,
        "A_reason": "fix_00/01/02 cắt giữa từ ('progra', 't.', 'ht', 'inpu') và tách bài thơ Robert Frost khỏi phần đề bài.",
        "BC_score": 2,
        "BC_reason": "para_00 giữ trọn Q6 và đề bài Frost poem + Tip; para_01 giữ trọn khổ thơ và bài tập Name and likes.",
    },
    {
        "document_id": "openstax-py-ch01",
        "page": 11,
        "A_score": 0,
        "A_reason": "fix_00 cắt giữa từ 'mathemat'; fix_01 tách đề câu hỏi Q1 khỏi các lựa chọn ở fix_02.",
        "BC_score": 2,
        "BC_reason": "para_00 giữ trọn 1.3 Variables và Assignment statement; para_01 giữ trọn 4 câu hỏi CONCEPTS IN PRACTICE.",
    },
    {
        "document_id": "openstax-py-ch01",
        "page": 12,
        "A_score": 0,
        "A_reason": "fix_00 cắt giữa từ 'descr'; fix_01 cắt đôi bảng Table 1.2 Keywords giữa chừng.",
        "BC_score": 2,
        "BC_reason": "para_00 giữ trọn đoạn Variable naming rules; para_01 giữ trọn phần Keywords (Table 1.2) kèm tiêu đề ngữ cảnh [Variable naming rules].",
    },
    {
        "document_id": "openstax-py-ch01",
        "page": 13,
        "A_score": 0,
        "A_reason": "fix_01 cắt giữa định nghĩa String ('A string is a sequence of'); fix_02 cắt giữa bảng Table 1.3 ('\"W').",
        "BC_score": 2,
        "BC_reason": "para_00 giữ trọn bài tập Final score; para_01 giữ trọn phần Quote marks và Table 1.3 Rules for strings.",
    },
]

GROUNDING_GRADES = {
    "A": {
        "q19": (1, "Rank #1 (fix_01) có định nghĩa library và Standard Library nhưng cắt giữa câu về Pandas ('Ex: Pandas ... is a wid'); thiếu phần kết luận vai trò của Pandas."),
        "q20": (2, "Rank #1 là nhiễu từ Chương 5, nhưng Rank #2 (openstax-py-ch03_p01_fix_01) chứa đủ định nghĩa container và danh sách/tuple để trả lời và truy nguồn."),
        "q21": (2, "Rank #1 (openstax-py-ch04_p02_fix_00) chứa đầy đủ bool data type, giá trị true/false và quy tắc viết hoa bắt buộc."),
        "q22": (2, "Rank #1 (openstax-py-ch05_p02_fix_00) chứa nguyên văn hai gạch đầu dòng xử lý khi điều kiện True và False."),
        "q23": (1, "Rank #1 (openstax-py-ch03_p11_fix_01) bị cắt mất vế đầu ('Calling a function like id() or type('), chỉ còn ') returns information...'; người đọc phải tự suy ra từ Rank #2/#3 trang 10."),
        "q24": (2, "Rank #1 (openstax-py-ch05_p05_fix_00) chứa đầy đủ 3 loại container và Rank #2 bổ sung giải thích chuỗi gồm nhiều ký tự."),
    },
    "B": {
        "q19": (2, "Rank #1 (openstax-py-ch01_p06_para_01) chứa trọn đoạn Standard Library và câu hoàn chỉnh về Pandas, truy nguồn chính xác trang 6."),
        "q20": (2, "Rank #1 (openstax-py-ch03_p01_para_01) chứa trọn phần Introduction định nghĩa container, lists/tuples và mục tiêu 3.1 Strings revisited."),
        "q21": (2, "Rank #1 (openstax-py-ch04_p02_para_00) chứa trọn phần bool data type và quy tắc viết hoa."),
        "q22": (2, "Rank #1 (openstax-py-ch05_p02_para_00) chứa nguyên văn điều kiện True/False trong while loop."),
        "q23": (1, "Rank #1 (openstax-py-ch03_p10_para_02) nêu đúng id() và type() mô tả object nhưng thiếu trang 11 khẳng định biến không có identity/type; Rank #3 còn nhiễu sang Chương 1."),
        "q24": (2, "Rank #1 (openstax-py-ch05_p05_para_00) chứa đầy đủ 3 loại container và giải thích for loop duyệt chuỗi (dù Rank #2 nhiễu sang Chương 3)."),
    },
    "C": {
        "q19": (2, "Giống B: Rank #1 chứa trọn vẹn bằng chứng Standard Library và Pandas."),
        "q20": (2, "Giống B: Rank #1 chứa trọn vẹn định nghĩa container và lists/tuples."),
        "q21": (2, "Giống B: Rank #1 chứa trọn vẹn định nghĩa bool và quy tắc viết hoa."),
        "q22": (2, "Giống B: Rank #1 chứa trọn vẹn hành vi while loop khi True/False."),
        "q23": (1, "Filter section='ch03_data_types' loại bỏ nhiễu Chương 1 ở Rank #3 (thay bằng ch03 trang 9), nhưng vẫn chưa kéo được trang 11 vào top-3 nên thiếu câu khẳng định biến không có identity/type."),
        "q24": (2, "Filter section='ch05_loops' giữ cả top-3 trong Chương 5 (loại bỏ nhiễu Chương 3 ở Rank #2 của B), Rank #1 chứa đủ bằng chứng."),
    },
}


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    results_dir = repo_root / "results"
    summary = json.loads((results_dir / "metrics_summary.json").read_text(encoding="utf-8"))
    coherence_raw = json.loads((results_dir / "coherence_positions.json").read_text(encoding="utf-8"))
    traces = {
        s: json.loads((results_dir / f"traces_{s}.json").read_text(encoding="utf-8"))
        for s in ("A", "B", "C")
    }

    # Verify coherence positions match pre-selected order
    assert [(x["document_id"], x["page"]) for x in coherence_raw] == [
        (x["document_id"], x["page"]) for x in COHERENCE_ASSESSMENTS
    ]

    coherence_summary = {}
    for strat in ("A", "B", "C"):
        key = "A_score" if strat == "A" else "BC_score"
        scores = [x[key] for x in COHERENCE_ASSESSMENTS]
        coherence_summary[strat] = {
            "n_positions": len(scores),
            "counts_0_1_2": [scores.count(0), scores.count(1), scores.count(2)],
            "mean_score_out_of_2": round(sum(scores) / len(scores), 2),
        }

    # Metadata audit on 6 test questions x 3 hits = 18 records per strategy
    metadata_audit = {}
    for strat in ("A", "B", "C"):
        test_traces = [t for t in traces[strat] if t["split"] == "test"]
        records = []
        valid_count = 0
        for t in test_traces:
            for h in t["hits"]:
                if h["metadata_valid"]:
                    valid_count += 1
                records.append(
                    {
                        "query_id": t["id"],
                        "rank": h["rank"],
                        "chunk_id": h["chunk_id"],
                        "document_id": h["document_id"],
                        "page": h["page"],
                        "section": h["metadata"].get("section"),
                        "metadata_valid": h["metadata_valid"],
                    }
                )
        m_test = summary["retrieval_metrics"][strat]["test"]
        m_dev = summary["retrieval_metrics"][strat]["dev"]
        metadata_audit[strat] = {
            "test_records_valid": f"{valid_count}/{len(records)}",
            "test_filter_compliance": m_test["filter_compliant_str"],
            "dev_filter_compliance": m_dev["filter_compliant_str"],
            "records": records,
        }

    grounding_summary = {}
    for strat in ("A", "B", "C"):
        grades = GROUNDING_GRADES[strat]
        vals = [v[0] for v in grades.values()]
        grounding_summary[strat] = {
            "n_test_queries": len(vals),
            "counts_0_1_2": [vals.count(0), vals.count(1), vals.count(2)],
            "counts_str": f"{vals.count(0)}/{vals.count(1)}/{vals.count(2)}",
            "mean_score_out_of_2": round(sum(vals) / len(vals), 2),
            "per_query": {
                qid: {"score": sc, "reason": rsn} for qid, (sc, rsn) in grades.items()
            },
        }

    audit_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "annotator": "Dương Tuấn Hưng (author; self-audit bias disclosed)",
        "coherence_selection_rule": "First 10 sorted (document_id, page) valid content positions prior to inspecting retrieval scores (openstax-py-ch01 pages 4-13).",
        "coherence_summary": coherence_summary,
        "coherence_positions": COHERENCE_ASSESSMENTS,
        "metadata_audit": metadata_audit,
        "grounding_summary": grounding_summary,
    }
    (results_dir / "manual_audit.json").write_text(
        json.dumps(audit_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write human-readable Markdown audit report
    md = [
        "# Manual Audit Report — Day 06 Benchmark",
        "",
        "- **Người chấm:** Dương Tuấn Hưng (tác giả — có ghi nhận rủi ro thiên lệch tự chấm theo RULES.md)",
        "- **Quy tắc chọn mẫu Coherence:** 10 vị trí `(document_id, page)` đầu tiên theo thứ tự sắp xếp (`openstax-py-ch01` trang 4–13), chốt trước khi đọc điểm số.",
        "",
        "## 1. Chunk Coherence (10 vị trí × 3 chiến lược, thang 0–2)",
        "",
        "| Vị trí | Chiến lược A (0–2) | Lý do A | Chiến lược B & C (0–2) | Lý do B & C |",
        "|---|---:|---|---:|---|",
    ]
    for row in COHERENCE_ASSESSMENTS:
        md.append(
            f"| `{row['document_id']}` p.{row['page']} | {row['A_score']} | {row['A_reason']} | {row['BC_score']} | {row['BC_reason']} |"
        )
    md.extend(
        [
            "",
            f"- **Trung bình A:** `{coherence_summary['A']['mean_score_out_of_2']}/2` (phân bố 0/1/2 = `{coherence_summary['A']['counts_0_1_2']}`)",
            f"- **Trung bình B & C:** `{coherence_summary['B']['mean_score_out_of_2']}/2` (phân bố 0/1/2 = `{coherence_summary['B']['counts_0_1_2']}`)",
            "",
            "## 2. Metadata Usefulness (6 câu test × top-3 = 18 bản ghi/chiến lược)",
            "",
            f"- **Độ đúng & đủ metadata (`document_id`, `source`, `page`, `section`):** A = `{metadata_audit['A']['test_records_valid']}`, B = `{metadata_audit['B']['test_records_valid']}`, C = `{metadata_audit['C']['test_records_valid']}`.",
            f"- **Tuân thủ filter (test):** A = `{metadata_audit['A']['test_filter_compliance']}`, B = `{metadata_audit['B']['test_filter_compliance']}`, C = `{metadata_audit['C']['test_filter_compliance']}` (dev của C = `{metadata_audit['C']['dev_filter_compliance']}`).",
            "",
            "## 3. Grounding Quality (6 câu test, thang 0–2)",
            "",
            "| Câu test | A (0–2) | Lý do A | B (0–2) | Lý do B | C (0–2) | Lý do C |",
            "|---|---:|---|---:|---|---:|---|",
        ]
    )
    for qid in ("q19", "q20", "q21", "q22", "q23", "q24"):
        a_s, a_r = GROUNDING_GRADES["A"][qid]
        b_s, b_r = GROUNDING_GRADES["B"][qid]
        c_s, c_r = GROUNDING_GRADES["C"][qid]
        md.append(f"| `{qid}` | {a_s} | {a_r} | {b_s} | {b_r} | {c_s} | {c_r} |")
    md.extend(
        [
            "",
            f"- **Grounding A:** phân bố 0/1/2 = `{grounding_summary['A']['counts_str']}`, trung bình = `{grounding_summary['A']['mean_score_out_of_2']}/2`",
            f"- **Grounding B:** phân bố 0/1/2 = `{grounding_summary['B']['counts_str']}`, trung bình = `{grounding_summary['B']['mean_score_out_of_2']}/2`",
            f"- **Grounding C:** phân bố 0/1/2 = `{grounding_summary['C']['counts_str']}`, trung bình = `{grounding_summary['C']['mean_score_out_of_2']}/2`",
        ]
    )
    (results_dir / "manual_audit_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("Generated results/manual_audit.json and results/manual_audit_report.md")


if __name__ == "__main__":
    main()

