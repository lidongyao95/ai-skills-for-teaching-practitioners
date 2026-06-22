#!/usr/bin/env python3
"""知网检索：多关键词并行检索，JS evaluate 提取结构化数据。"""

from __future__ import annotations

import argparse, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    sync_playwright = None

    class PlaywrightTimeout(Exception):
        pass

CNKI_SEARCH = "https://kns.cnki.net/kns8s/defaultresult/index"
CNKI_HOME = "https://www.cnki.net"
NO_RESULT_MARKERS = [
    "未找到",
    "没有找到",
    "暂无数据",
    "暂无相关",
    "无检索结果",
    "未检索到",
    "没有检索到",
]

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


def parse_from_js(
    raw_data: list[dict],
    max_results: int,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict]:
    papers = []
    for item in raw_data:
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

        if year_from is not None or year_to is not None:
            if year is None:
                continue
            if year_from is not None and year < year_from:
                continue
            if year_to is not None and year > year_to:
                continue

        authors = [a.strip() for a in re.split(r"[;；,，]", authors_str) if a.strip()]

        def _parse_int(s: str) -> int | None:
            try:
                return int(re.sub(r"[^\d]", "", s))
            except (ValueError, TypeError):
                return None

        papers.append({
            "id": f"cnki-{len(papers) + 1:03d}",
            "title": title,
            "authors": authors,
            "source": source,
            "year": year,
            "url": href,
            "selected": False,
            "citations": _parse_int(texts[6]) if len(texts) > 6 else None,
            "downloads": _parse_int(texts[7]) if len(texts) > 7 else None,
        })
        if len(papers) >= max_results:
            break
    return papers


def page_has_no_results(page) -> bool:
    text = page.evaluate("() => document.body ? document.body.innerText : ''")
    compact = re.sub(r"\s+", "", text)
    return any(marker in compact for marker in NO_RESULT_MARKERS)


def page_is_blank(page) -> bool:
    html_len, text_len = page.evaluate(
        "() => [document.documentElement.outerHTML.length, document.body ? document.body.innerText.trim().length : 0]"
    )
    return html_len < 100 and text_len == 0


def wait_for_search_results(page, timeout_ms: int) -> tuple[list[dict], str]:
    deadline = time.monotonic() + timeout_ms / 1000
    last_raw: list[dict] = []

    while True:
        try:
            last_raw = page.evaluate(JS_EXTRACT)
            if last_raw:
                return last_raw, "results"

            if page_has_no_results(page):
                return [], "empty"
        except Exception:
            pass

        if time.monotonic() >= deadline:
            try:
                if page_is_blank(page):
                    return [], "blank"
            except Exception:
                pass
            return last_raw, "timeout"

        page.wait_for_timeout(500)


def current_page_number(page) -> int | None:
    try:
        value = page.locator("a.cur[data-curpage]").first.get_attribute("data-curpage", timeout=1000)
        return int(value) if value else None
    except Exception:
        return None


def advance_to_next_page(page) -> bool:
    next_page = page.locator("#PageNext").first
    try:
        if next_page.count() == 0 or not next_page.is_visible(timeout=1000):
            return False

        before = current_page_number(page)
        next_page.click(timeout=5000)
        if before is not None:
            page.wait_for_function(
                "(previous) => { const cur = document.querySelector('a.cur[data-curpage]'); return cur && Number(cur.dataset.curpage) !== previous; }",
                arg=before,
                timeout=10000,
            )
        else:
            page.wait_for_timeout(2000)
        return True
    except Exception:
        return False


def apply_year_group_filter(page, year_from: int | None, year_to: int | None) -> bool:
    if year_from is None and year_to is None:
        return False

    start = year_from if year_from is not None else year_to
    end = year_to if year_to is not None else year_from
    if start is None or end is None:
        return False
    if start > end:
        start, end = end, start

    try:
        group_title = page.locator('dl[groupid="YE"] dt.tit').first
        if group_title.count() == 0:
            return False
        if page.locator('dl[groupid="YE"] input[type="checkbox"]').count() == 0:
            group_title.click(timeout=5000)
            page.wait_for_function(
                "() => document.querySelectorAll('dl[groupid=\"YE\"] input[type=\"checkbox\"]').length > 0",
                timeout=10000,
            )

        before = page.evaluate("() => document.querySelector('table.result-table-list tr td.name a')?.textContent.trim() || ''")
        applied = page.evaluate(
            """
            ([startYear, endYear]) => {
              const group = document.querySelector('dl[groupid="YE"]');
              if (!group) return false;
              const links = Array.from(group.querySelectorAll('a[title$="年"]'));
              const targets = links.filter((link) => {
                const year = Number((link.getAttribute('title') || '').replace(/\\D/g, ''));
                return year >= startYear && year <= endYear;
              });
              if (targets.length === 0) return false;
              if (targets.length === 1) {
                targets[0].click();
                return true;
              }
              for (const target of targets) {
                const input = target.parentElement ? target.parentElement.querySelector('input[type="checkbox"]') : null;
                if (input && !input.checked) input.click();
              }
              if (typeof window.mutiSelectedGroup === 'function') {
                window.mutiSelectedGroup();
                return true;
              }
              targets[0].click();
              return true;
            }
            """,
            [start, end],
        )
        if not applied:
            return False
        page.wait_for_function(
            "(previous) => { const first = document.querySelector('table.result-table-list tr td.name a'); return first && first.textContent.trim() !== previous; }",
            arg=before,
            timeout=15000,
        )
        page.wait_for_timeout(2000)
        print(f"  -> 已应用 CNKI 年度分组筛选: {start}-{end}（结果表日期可能为发表/上架等不同口径）")
        return True
    except Exception as exc:
        print(f"  -> 年度分组筛选未生效，改用解析后年份过滤: {exc}")
        return False


def search_one(
    page,
    query: str,
    max_results: int,
    result_timeout_ms: int,
    max_pages: int,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict]:
    url = f"{CNKI_SEARCH}?kw={quote(query)}"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)

    try:
        popup_close = page.locator(".close, .layui-layer-close").first
        if popup_close.count() > 0:
            popup_close.click(timeout=2000)
    except Exception:
        pass

    year_group_applied = apply_year_group_filter(page, year_from, year_to)
    fallback_year_from = None if year_group_applied else year_from
    fallback_year_to = None if year_group_applied else year_to

    papers: list[dict] = []
    seen_titles: set[str] = set()
    for page_index in range(max_pages):
        raw, status = wait_for_search_results(page, result_timeout_ms)
        if status == "empty":
            print("  -> 页面提示无结果")
            break
        if status == "blank":
            print("  -> 页面为空白，CNKI 可能拦截 headless 访问；请去掉 --headless 后重试")
            break
        if status == "timeout":
            seconds = result_timeout_ms / 1000
            print(f"  -> 第 {page_index + 1} 页 {seconds:g}s 内未检测到结果表，按当前解析结果继续")

        page_papers = parse_from_js(
            raw,
            max_results - len(papers),
            year_from=fallback_year_from,
            year_to=fallback_year_to,
        )
        added = 0
        for paper in page_papers:
            if paper["title"] in seen_titles:
                continue
            seen_titles.add(paper["title"])
            papers.append(paper)
            added += 1

        if max_pages > 1:
            print(f"  -> 第 {page_index + 1} 页解析 {len(raw)} 条，新增 {added} 条")

        if len(papers) >= max_results:
            break
        if page_index >= max_pages - 1:
            break
        if not advance_to_next_page(page):
            break

    for idx, paper in enumerate(papers):
        paper["id"] = f"cnki-{idx + 1:03d}"
    return papers


def main() -> int:
    parser = argparse.ArgumentParser(description="知网多关键词检索")
    parser.add_argument("--keywords", required=True, help="逗号分隔的多组检索词")
    parser.add_argument("--year-from", type=int, default=None)
    parser.add_argument("--year-to", type=int, default=None)
    parser.add_argument("--max-results", type=int, default=40)
    parser.add_argument("--max-pages", type=int, default=10, help="每组关键词最多翻页数")
    parser.add_argument("--result-timeout", type=float, default=20,
                        help="等待结果表或无结果提示的最长秒数")
    parser.add_argument("--output", required=True, help="输出 JSON 路径")
    parser.add_argument("--headless", action="store_true", help="无头模式；CNKI 可能返回空白页，建议默认有界面运行")
    args = parser.parse_args()

    if sync_playwright is None:
        raise SystemExit(
            "python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple playwright && "
            "PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright "
            "python3 -m playwright install chromium"
        )

    if args.result_timeout <= 0:
        print("错误: --result-timeout 必须大于 0", file=sys.stderr)
        return 1
    if args.max_results <= 0 or args.max_pages <= 0:
        print("错误: --max-results 和 --max-pages 必须大于 0", file=sys.stderr)
        return 1

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
                papers = search_one(
                    page,
                    query,
                    args.max_results,
                    int(args.result_timeout * 1000),
                    args.max_pages,
                    year_from=args.year_from,
                    year_to=args.year_to,
                )
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
