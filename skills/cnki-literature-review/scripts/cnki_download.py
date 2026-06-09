#!/usr/bin/env python3
"""从知网下载 selected 文献的 PDF（需高校机构 IP）。"""

from __future__ import annotations

import argparse, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    raise SystemExit("pip install playwright && playwright install chromium")

CNKI_HOME = "https://www.cnki.net"
PDF_BUTTON_TEXTS = ["PDF下载", "PDF 下载", "下载PDF", "pdf下载", "PDF"]
DOWNLOAD_TIMEOUT_MS = 120_000


def safe_filename(title: str, max_len: int = 40) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip()
    return cleaned


def is_pdf(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 100:
        return False
    with path.open("rb") as f:
        return f.read(4) == b"%PDF"


def load_selected(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    papers = data.get("papers", data if isinstance(data, list) else [])
    selected = [p for p in papers if p.get("selected") and p.get("url")]

    ids = [p["id"] for p in selected]
    dupes = [i for i in ids if ids.count(i) > 1]
    if dupes:
        print(f"警告: 检测到重复 ID {list(set(dupes))}，请重新运行 curate.py 以分配唯一 ID", file=sys.stderr)
        raise SystemExit(1)

    return selected


def save_meta(meta_dir: Path, paper: dict, download_info: dict) -> None:
    meta = {**paper, "download": download_info}
    meta_dir.mkdir(parents=True, exist_ok=True)
    safe_id = paper["id"]
    (meta_dir / f"{safe_id}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8",
    )


def try_download_pdf(page, pdf_dir: Path, paper: dict) -> dict:
    pid = paper["id"]
    title = paper.get("title", "untitled")
    out_name = f"{pid}.pdf"
    out_path = pdf_dir / out_name

    if out_path.exists() and is_pdf(out_path):
        return {
            "status": "cached",
            "pdf_file": str(out_path.relative_to(pdf_dir.parent.parent)),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }

    page.goto(paper["url"], wait_until="domcontentloaded", timeout=90000)
    time.sleep(2)

    clicked = False
    for label in PDF_BUTTON_TEXTS:
        btn = page.get_by_text(label, exact=False).first
        if btn.count() > 0:
            try:
                with page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as dl_info:
                    btn.click(timeout=5000)
                download = dl_info.value
                download.save_as(out_path)
                clicked = True
                break
            except (PlaywrightTimeout, Exception):
                continue

    if not clicked:
        for sel in ["a#pdfDown", "a[href*='pdf'], a[href*='PDF']", ".btn-dlpdf"]:
            loc = page.locator(sel).first
            if loc.count() == 0:
                continue
            try:
                with page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as dl_info:
                    loc.click(timeout=5000)
                download = dl_info.value
                download.save_as(out_path)
                clicked = True
                break
            except Exception:
                continue

    if not clicked:
        return {"status": "failed", "reason": "未找到 PDF 下载按钮"}

    if not is_pdf(out_path):
        out_path.unlink(missing_ok=True)
        return {"status": "failed", "reason": "下载文件非 PDF"}

    return {
        "status": "ok",
        "pdf_file": str(Path("papers") / "pdf" / out_name),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="知网 PDF 批量下载")
    parser.add_argument("--input", required=True)
    parser.add_argument("--workspace", default="./literature-review")
    parser.add_argument("--delay", type=float, default=5.0)
    parser.add_argument("--manual-wait", type=int, default=60)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--clean", action="store_true", help="下载前清理旧的 PDF、meta 和 text 文件")
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    pdf_dir = root / "papers" / "pdf"
    meta_dir = root / "papers" / "meta"
    text_dir = root / "papers" / "text"
    log_path = root / "logs" / "download.log"

    pdf_dir.mkdir(parents=True, exist_ok=True)
    papers = load_selected(Path(args.input).resolve())

    if args.clean:
        for d, pat in [(pdf_dir, "*.pdf"), (meta_dir, "*.json"), (text_dir, "*.txt")]:
            for f in d.glob(pat):
                f.unlink()
                print(f"  清理: {f.name}")
        print("旧文件已清理")
    if not papers:
        print("无 selected=true 的文献", file=sys.stderr)
        return 1

    print(f"待下载 {len(papers)} 篇（需机构 IP 认证）")

    ok, fail = 0, 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        print(f"打开知网首页，等待机构认证（最多 {args.manual_wait}s）...")
        page.goto(CNKI_HOME, wait_until="domcontentloaded", timeout=60000)
        time.sleep(args.manual_wait if not args.headless else 5)

        for i, paper in enumerate(papers):
            pid = paper["id"]
            title = paper.get("title", "")[:40]
            print(f"[{i+1}/{len(papers)}] {pid} {title}...")

            try:
                result = try_download_pdf(page, pdf_dir, paper)
            except Exception as exc:
                result = {"status": "failed", "reason": str(exc)}

            save_meta(meta_dir, paper, result)
            log_line = f"{'OK' if result.get('status') in ('ok','cached') else 'FAIL'} {pid} {title}"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as lf:
                lf.write(log_line + "\n")

            if result.get("status") in ("ok", "cached"):
                print(f"  OK -> {result.get('pdf_file')}")
                ok += 1
            else:
                print(f"  FAIL: {result.get('reason', 'unknown')}")
                fail += 1

            if i < len(papers) - 1:
                time.sleep(args.delay)

        browser.close()

    print(f"\n完成: 成功 {ok}, 失败 {fail}")
    return 0 if ok > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
