#!/usr/bin/env python3
"""知网检索 v2：多关键词并行检索，JS evaluate 提取结构化数据。
ACTUAL BATTLE VERIFIED: 2026-06-08 on CNKI kns8s page structure.
"""

from __future__ import annotations

import argparse, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    raise SystemExit("pip install playwright && playwright install chromium")

CNKI_SEARCH = "https://kns.cnki.net/kns8s/defaultresult/index"
CNKI_HOME = "https://www.cnki.net"

JS_EXTRACT = """
() => {
    const rows = document.querySelectorAll('table.result-table-list tr');
    const results = [];
    rows.forEach((row, idx) => {
        const tds = row.querySelectorAll('td');
        if (tds.length < 3) return;
        const link = row.querySelector('a.fz14, td.name a, a[target="kcmstarget"]');
        if (!link) return;
        const title = link.textContent.trim();
        if (!title) return;
        const href = link.href;
        const texts = [];
        tds.forEach(td => texts.push(td.textContent.trim()));
        results.push({title, href, texts, idx});
    });
    return results;
}
"""


def parse_from_js(raw_data: list[dict], max_results: int) -> list[dict]:
    papers = []
    for item in raw_data[:max_results]:
        title = item["title"]
        href = item.get("href", "")
        texts = item.get("texts", [])

        authors_str = texts[2] if len(texts) > 2 else ""
        source = texts[3] if len(texts) > 3 else ""
        date_text = texts[4] if len(texts) > 4 else ""

        year = None
        for t in [date_text, source, authors_str]:
            m = re.search(r"(20\d{2})", t) if t else None
            if m:
                year = int(m.group(1))
                break

        authors = [a.strip() for a in re.split(r"[;；,，]", authors_str) if a.strip()]

        papers.append({
            "id": f"cnki-{len(papers) + 1:03d}",
            "title": title,
            "authors": authors,
            "source": source,
            "year": year,
            "url": href,
            "selected": False,
        })
    return papers


def search_one(page, query: str, max_results: int) -> list[dict]:
    url = f"{CNKI_SEARCH}?kw={quote(query)}"
    page.goto(url, wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(5000)

    try:
        popup_close = page.locator(".close, .layui-layer-close").first
        if popup_close.count() > 0:
            popup_close.click(timeout=2000)
            page.wait_for_timeout(1000)
    except Exception:
        pass

    raw = page.evaluate(JS_EXTRACT)
    papers = parse_from_js(raw, max_results)
    return papers


def main() -> int:
    parser = argparse.ArgumentParser(description="知网多关键词检索")
    parser.add_argument("--keywords", required=True, help="逗号分隔的多组检索词")
    parser.add_argument("--year-from", type=int, default=None)
    parser.add_argument("--year-to", type=int, default=None)
    parser.add_argument("--max-results", type=int, default=40)
    parser.add_argument("--output", required=True, help="输出 JSON 路径")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    queries = [q.strip() for q in args.keywords.split(",") if q.strip()]
    if not queries:
        print("错误: --keywords 不能为空", file=sys.stderr)
        return 1

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"检索 {len(queries)} 组关键词: {queries}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(accept_downloads=True, locale="zh-CN")
        page = context.new_page()

        page.goto(CNKI_HOME, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        all_papers = []
        seen = set()

        for qi, query in enumerate(queries):
            try:
                print(f"\n[{qi+1}/{len(queries)}] {query}")
                papers = search_one(page, query, args.max_results)
                print(f"  -> {len(papers)} 条")
                for p in papers:
                    if p["title"] not in seen:
                        seen.add(p["title"])
                        all_papers.append(p)
            except PlaywrightTimeout as e:
                print(f"  -> 超时: {e}")
            except Exception as e:
                print(f"  -> 失败: {e}")

        browser.close()

    print(f"\n=== 去重后共 {len(all_papers)} 篇 ===")

    payload = {
        "query": ",".join(queries),
        "year_from": args.year_from,
        "year_to": args.year_to,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": "CNKI",
        "count": len(all_papers),
        "papers": all_papers,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存 -> {output_path}")

    return 0 if all_papers else 2


if __name__ == "__main__":
    raise SystemExit(main())
