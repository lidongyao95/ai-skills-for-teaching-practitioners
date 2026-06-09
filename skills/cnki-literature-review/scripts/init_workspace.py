#!/usr/bin/env python3
"""初始化文献调研工作目录。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def init_workspace(root: Path, topic: str) -> None:
    dirs = [
        "papers/pdf",
        "papers/text",
        "papers/meta",
        "summaries",
        "search",
        "review",
        "logs",
    ]
    for rel in dirs:
        (root / rel).mkdir(parents=True, exist_ok=True)

    brief = {
        "topic": topic,
        "keywords": [],
        "year_from": None,
        "year_to": None,
        "target_count": 20,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    brief_path = root / "search" / "brief.json"
    if not brief_path.exists():
        brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# 文献调研：{topic}\n\n"
            "目录说明见 cnki-literature-review skill 的 SKILL.md。\n",
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化文献调研工作目录")
    parser.add_argument("--topic", required=True, help="调研主题")
    parser.add_argument("--dir", default="./literature-review", help="工作目录路径")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    init_workspace(root, args.topic)
    print(f"已初始化: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
