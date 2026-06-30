#!/usr/bin/env python3
"""候选精选：在已限定来源类别的候选池内按主题相关性择优。"""

from __future__ import annotations

import argparse, json, re
from pathlib import Path

EXCLUDE_K12 = ["小学", "初中", "高中", "中学", "校本", "幼儿园", "学前"]
TOPIC_SPLIT_RE = re.compile(r"(?<![A-Za-z])(?:AND|OR|NOT)(?![A-Za-z])|[，,；;、\s]+", re.IGNORECASE)


def parse_topic_keywords(topic: str) -> list[str]:
    keywords = []
    seen = set()

    for item in TOPIC_SPLIT_RE.split(topic):
        keyword = item.strip(" \t\r\n\"'“”‘’()（）[]【】")
        if len(keyword) < 2 or keyword in seen:
            continue
        seen.add(keyword)
        keywords.append(keyword)

    return keywords


def main() -> int:
    parser = argparse.ArgumentParser(description="候选精选文献")
    parser.add_argument("--input", required=True)
    parser.add_argument("--topic", default="")
    parser.add_argument("--max", type=int, default=20)
    parser.add_argument("--no-k12-filter", action="store_true")
    parser.add_argument("--sort-by", default="citations",
                        choices=["citations", "downloads", "relevance"])
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    papers = data.get("papers", [])

    theme_kw = []
    if args.topic:
        theme_kw = parse_topic_keywords(args.topic)
        if not theme_kw:
            print("警告: --topic 未解析出有效关键词，将无法按主题相关性筛选")
        else:
            print(f"主题关键词: {', '.join(theme_kw)}")

    selected = []
    for p in papers:
        title = p.get("title", "")
        source = p.get("source", "")

        if not args.no_k12_filter and any(kw in title for kw in EXCLUDE_K12):
            print(f"  [K12] {title[:40]}...")
            continue

        relevance = sum(1 for kw in theme_kw if kw in title)
        topic_ok = relevance >= 1

        if topic_ok:
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

    # 排序：始终先按相关性（已筛选入集的都 topic_ok），再按用户指定维度
    # 先存下 relevance_score 供排序使用
    for p in selected:
        p["_score"] = sum(1 for kw in theme_kw if kw in p.get("title", "")) if theme_kw else 0

    if args.sort_by == "citations":
        selected.sort(key=lambda p: (p.get("_score", 0), p.get("citations") or 0), reverse=True)
    elif args.sort_by == "downloads":
        selected.sort(key=lambda p: (p.get("_score", 0), p.get("downloads") or 0), reverse=True)
    # relevance: 纯按主题命中数排序
    else:
        selected.sort(key=lambda p: p.get("_score", 0), reverse=True)

    # 清理临时字段
    for p in selected:
        p.pop("_score", None)

    for idx, p in enumerate(selected):
        new_id = f"cnki-{idx+1:03d}"
        p["id"] = new_id

    selected_obj_ids = {id(p) for p in selected}
    unselected = []
    for p in papers:
        if id(p) not in selected_obj_ids:
            p["selected"] = False
            unselected.append(p)

    data["count"] = len(selected)
    data["papers"] = selected + unselected
    Path(args.input).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n最终入选 {len(selected)} 篇（ID 已按筛选排序重新分配）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
