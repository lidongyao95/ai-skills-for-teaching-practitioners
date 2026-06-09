#!/usr/bin/env python3
"""从 papers/pdf 提取全文到 papers/text（使用 pymupdf）。"""

from __future__ import annotations

import argparse, json
from datetime import datetime, timezone
from pathlib import Path

try:
    import fitz
except ImportError:
    raise SystemExit("pip install pymupdf")

MIN_CHARS_FOR_TEXT = 200


def extract_text(pdf_path: Path) -> tuple[str, int]:
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    pages = [page.get_text("text") for page in doc]
    doc.close()
    return "\n\n".join(pages).strip(), page_count


def main() -> int:
    parser = argparse.ArgumentParser(description="提取 PDF 全文")
    parser.add_argument("--workspace", default="./literature-review")
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    pdf_dir = root / "papers" / "pdf"
    text_dir = root / "papers" / "text"
    meta_dir = root / "papers" / "meta"
    log_path = root / "logs" / "extract.log"

    text_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"未找到 PDF: {pdf_dir}")
        return 1

    ok, skip = 0, 0
    lines = []

    for pdf_path in pdfs:
        stem = pdf_path.stem
        meta = {}
        meta_path = meta_dir / f"{stem}.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))

        try:
            text, page_count = extract_text(pdf_path)
        except Exception as exc:
            msg = f"FAIL {pdf_path.name}: {exc}"
            print(msg)
            lines.append(msg)
            continue

        ocr_needed = len(text) < MIN_CHARS_FOR_TEXT
        text_file = text_dir / f"{stem}.txt"
        text_file.write_text(text, encoding="utf-8")

        meta["id"] = stem
        meta["extraction"] = {
            "status": "ok" if not ocr_needed else "ocr_needed",
            "text_file": str(text_file.relative_to(root)),
            "page_count": page_count,
            "char_count": len(text),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }
        (meta_dir / f"{stem}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        status = "OCR?" if ocr_needed else "OK"
        print(f"[{status}] {pdf_path.name} -> {stem}.txt ({len(text)} chars)")
        lines.append(f"{status} {pdf_path.name}")

        if ocr_needed:
            skip += 1
        else:
            ok += 1

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"完成: 有效文本 {ok}, 疑似扫描版 {skip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
