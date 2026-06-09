#!/usr/bin/env python3
"""智能筛选：期刊质量 + 主题相关性双维度打分。"""

from __future__ import annotations

import argparse, json, re
from pathlib import Path

DEFAULT_JOURNALS = [
    "高等工程教育研究", "中国大学教学", "大学化学", "化学教育",
    "高教学刊", "工业和信息化教育", "中国现代教育装备",
    "高等建筑教育", "中国地质教育", "安徽工业大学学报",
    "湖北民族大学学报", "天津理工大学学报", "商丘师范学院学报",
    "食品工业", "化学教育(中英文)", "机械设计与制造工程",
    "机电工程技术", "物联网技术", "陕西教育",
    "纺织服装教育", "科教文汇", "教育研究",
    "高等教育研究", "中国高教研究", "学位与研究生教育",
]

EXCLUDE_K12 = ["小学", "初中", "高中", "中学", "校本", "幼儿园", "学前"]

DEFAULT_THEME_KEYWORDS = [
    "工程实践", "实践教学", "产教融合", "OBE", "工程教育认证",
    "新工科", "CDIO", "卓越工程师", "工程能力", "实践能力",
    "人才培养模式", "教学改革", "PBL", "项目式", "混合式教学",
    "工程训练", "创新人才", "产教", "工程思维", "校企",
]


def tokenize(text: str) -> list[str]:
    result = []
    for i in range(len(text)):
        for j in range(i + 2, i + 7):
            if j <= len(text):
                result.append(text[i:j])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="智能筛选文献")
    parser.add_argument("--input", required=True)
    parser.add_argument("--topic", default="")
    parser.add_argument("--max", type=int, default=20)
    parser.add_argument("--journal-list", default=None)
    parser.add_argument("--no-k12-filter", action="store_true")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    papers = data.get("papers", [])

    journals = DEFAULT_JOURNALS
    if args.journal_list:
        journals = args.journal_list.split(",")

    theme_kw = DEFAULT_THEME_KEYWORDS.copy()
    if args.topic:
        extra = [t for t in re.split(r"[，,；;、]", args.topic) if len(t) >= 2]
        theme_kw = list(set(theme_kw + extra))

    selected = []
    for p in papers:
        title = p.get("title", "")
        source = p.get("source", "")

        if not args.no_k12_filter and any(kw in title for kw in EXCLUDE_K12):
            print(f"  [K12] {title[:40]}...")
            continue

        journal_ok = any(j in source for j in journals)
        relevance = sum(1 for kw in theme_kw if kw in title)
        topic_ok = relevance >= 1

        if journal_ok and topic_ok:
            p["selected"] = True
            selected.append(p)
            print(f"  [+] [{p.get('year')}] {title[:50]}... | {source}")

    if len(selected) < args.max // 2:
        for p in papers:
            if p not in selected and not any(kw in p["title"] for kw in EXCLUDE_K12):
                relevance = sum(1 for kw in theme_kw if kw in p["title"])
                if relevance >= 2:
                    p["selected"] = True
                    selected.append(p)
                    print(f"  [++] [{p.get('year')}] {p['title'][:50]}... | {p['source']}")

    selected = selected[:args.max]
    id_map = {}
    for idx, p in enumerate(selected):
        new_id = f"cnki-{idx+1:03d}"
        id_map[p["id"]] = new_id
        p["id"] = new_id

    for p in papers:
        if p not in selected:
            p["selected"] = False

    data["count"] = len(selected)
    data["papers"] = papers
    Path(args.input).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n最终入选 {len(selected)} 篇（ID 已重新分配为唯一）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
