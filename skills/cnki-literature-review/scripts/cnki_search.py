#!/usr/bin/env python3
"""知网检索：多关键词并行检索，JS evaluate 提取结构化数据。"""

from __future__ import annotations

import argparse, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from cnki_page_utils import (
    page_has_marker,
    page_has_verification_signal,
    wait_for_verification_state,
)

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
JOURNAL_TYPE_LABELS = {
    "core": "北大核心",
    "cscd": "CSCD",
    "wjci": "WJCI",
    "ei": "EI",
    "cssci": "CSSCI",
    "ami": "AMI",
    "sci": "SCI",
}

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
    return page_has_marker(page, NO_RESULT_MARKERS)


def page_is_blank(page) -> bool:
    html_len, text_len = page.evaluate(
        "() => [document.documentElement.outerHTML.length, document.body ? document.body.innerText.trim().length : 0]"
    )
    return html_len < 100 and text_len == 0


def page_has_search_results(page) -> bool:
    try:
        return bool(page.evaluate(JS_EXTRACT))
    except Exception:
        return False


def is_verification_page(page) -> bool:
    if page_has_search_results(page) or page_has_no_results(page):
        return False

    return page_has_verification_signal(page)


def wait_for_verification(page, verify_wait: int) -> bool:
    return wait_for_verification_state(page, verify_wait, is_verification_page, "继续检索")


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
            if is_verification_page(page):
                return [], "verification"
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


def page_has_search_entry(page) -> bool:
    try:
        return bool(page.evaluate(
            """
            () => Array.from(document.querySelectorAll('input:not([type]), input[type="text"], input[type="search"]'))
              .some((input) => {
                const rect = input.getBoundingClientRect();
                return rect.width > 80 && rect.height > 12
                  && getComputedStyle(input).visibility !== 'hidden'
                  && getComputedStyle(input).display !== 'none';
              })
            """
        ))
    except Exception:
        return False


def submit_keyword_search(page, query: str) -> bool:
    try:
        return bool(page.evaluate(
            """
            (query) => {
              const visible = (el) => {
                const rect = el.getBoundingClientRect();
                const style = getComputedStyle(el);
                return rect.width > 0 && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const inputs = Array.from(document.querySelectorAll('input:not([type]), input[type="text"], input[type="search"]'))
                .filter((input) => visible(input) && input.getBoundingClientRect().width > 80);
              if (inputs.length === 0) return false;

              const scoreInput = (input) => {
                const haystack = [
                  input.id,
                  input.name,
                  input.className,
                  input.placeholder,
                  input.getAttribute('aria-label'),
                  input.getAttribute('title')
                ].join(' ').toLowerCase();
                let score = 0;
                if (/search|keyword|kw|txt|term|query/.test(haystack)) score += 10;
                if (/检索|搜索|关键词|主题|篇名/.test(haystack)) score += 10;
                score += Math.min(input.getBoundingClientRect().width / 100, 5);
                return score;
              };
              const input = inputs.sort((a, b) => scoreInput(b) - scoreInput(a))[0];
              const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
              setter.call(input, query);
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));

              const candidates = Array.from(document.querySelectorAll(
                'button, a, input[type="button"], input[type="submit"], .search-btn, .btn-search, .searchBtn'
              )).filter(visible);
              const button = candidates.find((el) => {
                const text = [el.textContent, el.value, el.title, el.getAttribute('aria-label'), el.className]
                  .join(' ');
                return /检索|搜索|search/i.test(text);
              });
              if (button) {
                button.click();
                return true;
              }

              input.focus();
              input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
              input.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
              return true;
            }
            """,
            query,
        ))
    except Exception:
        return False


def ensure_keyword_search(page, query: str, result_timeout_ms: int, verify_wait: int) -> bool:
    for attempt in range(3):
        if page_has_search_results(page) or page_has_no_results(page):
            return True

        submitted = submit_keyword_search(page, query)
        if submitted:
            print(f"  -> 已提交检索词: {query}")
        elif not page_has_search_entry(page) and is_verification_page(page):
            if not wait_for_verification(page, verify_wait):
                return False
            continue
        else:
            print("  -> 未定位到搜索框，继续等待页面状态")

        raw, status = wait_for_search_results(page, result_timeout_ms)
        if status in {"results", "empty"}:
            return True
        if status == "verification":
            if not wait_for_verification(page, verify_wait):
                return False
            continue
        if raw:
            return True
        if attempt < 2:
            page.wait_for_timeout(1000)
    return page_has_search_results(page) or page_has_no_results(page)


def current_page_number(page) -> int | None:
    try:
        value = page.locator("a.cur[data-curpage]").first.get_attribute("data-curpage", timeout=1000)
        return int(value) if value else None
    except Exception:
        return None


def advance_to_next_page(page, verify_wait: int) -> bool:
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
        if is_verification_page(page):
            return wait_for_verification(page, verify_wait)
        return False


def parse_journal_types(raw: str, core_journal: bool = False, ei_journal: bool = False) -> list[str]:
    values = [v.strip() for v in re.split(r"[,，;；/、\s]+", raw or "") if v.strip()]
    if core_journal:
        values.append("core")
    if ei_journal:
        values.append("ei")

    normalized: list[str] = []
    for value in values:
        compact = value.lower().replace("-", "").replace("_", "")
        if compact in {"core", "hexin", "核心", "核心期刊", "中文核心", "北大核心"}:
            key = "core"
        elif compact in {"cscd", "中国科学引文数据库"}:
            key = "cscd"
        elif compact == "wjci":
            key = "wjci"
        elif compact in {"ei", "ei期刊", "ei来源期刊", "工程索引"}:
            key = "ei"
        elif compact in {"cssci", "南大核心", "中文社会科学引文索引"}:
            key = "cssci"
        elif compact == "ami":
            key = "ami"
        elif compact == "sci":
            key = "sci"
        else:
            print(f"  -> 忽略未知来源类别: {value}")
            continue
        if key not in normalized:
            normalized.append(key)
    return normalized


def result_snapshot(page) -> dict:
    return page.evaluate(
        """
        () => ({
          url: location.href,
          first: document.querySelector('table.result-table-list tr td.name a, table.result-table-list tr a.fz14')?.textContent.trim() || '',
          rows: document.querySelectorAll('table.result-table-list tr').length,
          pager: document.querySelector('.pagerTitleCell, .count, .pagerCell')?.textContent.trim() || ''
        })
        """
    )


def wait_for_result_change(page, before: dict, timeout_ms: int = 15000) -> bool:
    try:
        page.wait_for_function(
            """
            (previous) => {
              const current = {
                url: location.href,
                first: document.querySelector('table.result-table-list tr td.name a, table.result-table-list tr a.fz14')?.textContent.trim() || '',
                rows: document.querySelectorAll('table.result-table-list tr').length,
                pager: document.querySelector('.pagerTitleCell, .count, .pagerCell')?.textContent.trim() || ''
              };
              return current.url !== previous.url
                || (current.first && current.first !== previous.first)
                || (current.pager && current.pager !== previous.pager)
                || current.rows !== previous.rows;
            }
            """,
            arg=before,
            timeout=timeout_ms,
        )
        return True
    except Exception:
        return False


def apply_source_category_filter(page, journal_types: list[str], verify_wait: int) -> bool:
    if not journal_types:
        return False

    labels = [JOURNAL_TYPE_LABELS[t] for t in journal_types if t in JOURNAL_TYPE_LABELS]
    if not labels:
        return False

    for attempt in range(3):
        before = result_snapshot(page)
        try:
            result = page.evaluate(
                """
                (labels) => {
                  const group = document.querySelector('dl[groupid="LYBSM"]');
                  if (!group) return { ok: false, reason: 'group-not-found' };

                  const options = Array.from(group.querySelectorAll('li'));
                  if (options.length === 0) {
                    const trigger = group.querySelector('dt.tit .icon-arrow, dt.tit');
                    if (trigger) trigger.click();
                    return { ok: false, reason: 'expanded' };
                  }

                  const clicked = [];
                  for (const label of labels) {
                    const option = options.find((li) => {
                      const input = li.querySelector('input[type="checkbox"]');
                      const link = li.querySelector('a');
                      return (input && input.getAttribute('text') === label)
                        || (input && input.getAttribute('title') === label)
                        || (link && link.getAttribute('title') === label)
                        || (link && link.textContent.trim() === label);
                    });
                    if (!option) return { ok: false, reason: `option-not-found:${label}` };

                    const input = option.querySelector('input[type="checkbox"]');
                    if (input && !input.checked) input.click();
                    clicked.push(label);
                  }

                  const submit = document.querySelector('.sidebar-filter-btns .btn-submit, a[onclick*="mutiSelectedGroup"]');
                  if (submit) {
                    submit.click();
                  } else if (typeof window.mutiSelectedGroup === 'function') {
                    window.mutiSelectedGroup();
                  } else {
                    return { ok: false, reason: 'submit-not-found' };
                  }

                  return { ok: true, clicked };
                }
                """,
                labels,
            )
        except Exception as exc:
            print(f"  -> 来源类别筛选未生效: {exc}")
            return False

        if not result.get("ok"):
            if result.get("reason") == "expanded" and attempt < 2:
                page.wait_for_function(
                    "() => document.querySelectorAll('dl[groupid=\"LYBSM\"] li').length > 0",
                    timeout=8000,
                )
                continue
            print(f"  -> 来源类别筛选失败: {result.get('reason', 'unknown')}")
            return False

        changed = wait_for_result_change(page, before)
        if not changed and is_verification_page(page):
            if not wait_for_verification(page, verify_wait):
                print("  -> 来源类别筛选后验证未完成")
                return False
            continue

        if changed or source_categories_checked(page, labels):
            page.wait_for_timeout(2000)
            print(f"  -> 已应用 CNKI 来源类别筛选: {', '.join(labels)}")
            return True

        if attempt < 2:
            page.wait_for_timeout(1000)

    print("  -> 已点击 CNKI 来源类别筛选，但未能确认筛选生效")
    return False


def source_categories_checked(page, labels: list[str]) -> bool:
    try:
        return bool(page.evaluate(
            """
            (labels) => {
              const group = document.querySelector('dl[groupid="LYBSM"]');
              if (!group) return false;
              return labels.every((label) => {
                const option = Array.from(group.querySelectorAll('li')).find((li) => {
                  const input = li.querySelector('input[type="checkbox"]');
                  const link = li.querySelector('a');
                  return (input && input.getAttribute('text') === label)
                    || (input && input.getAttribute('title') === label)
                    || (link && link.getAttribute('title') === label)
                    || (link && link.textContent.trim() === label);
                });
                const input = option && option.querySelector('input[type="checkbox"]');
                return Boolean(input && input.checked);
              });
            }
            """,
            labels,
        ))
    except Exception:
        return False


def apply_year_group_filter(page, year_from: int | None, year_to: int | None, verify_wait: int) -> bool:
    if year_from is None and year_to is None:
        return False

    start = year_from if year_from is not None else year_to
    end = year_to if year_to is not None else year_from
    if start is None or end is None:
        return False
    if start > end:
        start, end = end, start

    for attempt in range(3):
        before = result_snapshot(page)
        try:
            result = page.evaluate(
                """
                ([startYear, endYear]) => {
                  const group = document.querySelector('dl[groupid="YE"]');
                  if (!group) return { ok: false, reason: 'group-not-found' };

                  const links = Array.from(group.querySelectorAll('a[title$="年"]'));
                  if (links.length === 0) {
                    const trigger = group.querySelector('dt.tit .icon-arrow, dt.tit');
                    if (trigger) trigger.click();
                    return { ok: false, reason: 'expanded' };
                  }

                  const targets = links.filter((link) => {
                    const year = Number((link.getAttribute('title') || '').replace(/\\D/g, ''));
                    return year >= startYear && year <= endYear;
                  });
                  if (targets.length === 0) return { ok: false, reason: 'option-not-found' };

                  if (targets.length === 1) {
                    targets[0].click();
                    return { ok: true };
                  }

                  for (const target of targets) {
                    const input = target.parentElement ? target.parentElement.querySelector('input[type="checkbox"]') : null;
                    if (input && !input.checked) input.click();
                  }

                  const submit = document.querySelector('.sidebar-filter-btns .btn-submit, a[onclick*="mutiSelectedGroup"]');
                  if (submit) {
                    submit.click();
                  } else if (typeof window.mutiSelectedGroup === 'function') {
                    window.mutiSelectedGroup();
                  } else {
                    return { ok: false, reason: 'submit-not-found' };
                  }
                  return { ok: true };
                }
                """,
                [start, end],
            )
        except Exception as exc:
            print(f"  -> 年度分组筛选未生效，改用解析后年份过滤: {exc}")
            return False

        if not result.get("ok"):
            if result.get("reason") == "expanded" and attempt < 2:
                page.wait_for_function(
                    "() => document.querySelectorAll('dl[groupid=\"YE\"] a[title$=\"年\"]').length > 0",
                    timeout=10000,
                )
                continue
            print(f"  -> 年度分组筛选未生效，改用解析后年份过滤: {result.get('reason', 'unknown')}")
            return False

        changed = wait_for_result_change(page, before)
        if not changed and is_verification_page(page):
            if not wait_for_verification(page, verify_wait):
                print("  -> 年度分组筛选后验证未完成")
                return False
            continue

        if changed or year_options_checked(page, start, end):
            page.wait_for_timeout(2000)
            print(f"  -> 已应用 CNKI 年度分组筛选: {start}-{end}（结果表日期可能为发表/上架等不同口径）")
            return True

        if attempt < 2:
            page.wait_for_timeout(1000)

    print(f"  -> 已点击 CNKI 年度分组筛选: {start}-{end}；结果表刷新状态不稳定，继续按年度分组结果解析")
    return True


def year_options_checked(page, start: int, end: int) -> bool:
    try:
        return bool(page.evaluate(
            """
            ([startYear, endYear]) => {
              const group = document.querySelector('dl[groupid="YE"]');
              if (!group) return false;
              const targets = Array.from(group.querySelectorAll('a[title$="年"]')).filter((link) => {
                const year = Number((link.getAttribute('title') || '').replace(/\\D/g, ''));
                return year >= startYear && year <= endYear;
              });
              if (targets.length === 0) return false;
              return targets.every((target) => {
                const input = target.parentElement ? target.parentElement.querySelector('input[type="checkbox"]') : null;
                return !input || input.checked;
              });
            }
            """,
            [start, end],
        ))
    except Exception:
        return False


def search_one(
    page,
    query: str,
    max_results: int,
    result_timeout_ms: int,
    max_pages: int,
    verify_wait: int,
    year_from: int | None = None,
    year_to: int | None = None,
    journal_types: list[str] | None = None,
) -> list[dict]:
    url = f"{CNKI_SEARCH}?kw={quote(query)}"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)

    try:
        popup_close = page.locator(".close, .layui-layer-close").first
        if popup_close.count() > 0:
            popup_close.click(timeout=2000)
    except Exception:
        pass

    if not ensure_keyword_search(page, query, result_timeout_ms, verify_wait):
        raise RuntimeError("未能提交关键词并进入搜索结果页")

    year_group_applied = apply_year_group_filter(page, year_from, year_to, verify_wait)
    if journal_types and not apply_source_category_filter(page, journal_types, verify_wait):
        labels = [JOURNAL_TYPE_LABELS.get(t, t) for t in (journal_types or [])]
        raise RuntimeError(f"未能应用 CNKI 来源类别筛选: {', '.join(labels)}；停止本组检索，避免混入未筛选结果")
    fallback_year_from = None if year_group_applied else year_from
    fallback_year_to = None if year_group_applied else year_to

    papers: list[dict] = []
    seen_titles: set[str] = set()
    for page_index in range(max_pages):
        raw, status = wait_for_search_results(page, result_timeout_ms)
        if status == "verification":
            if not wait_for_verification(page, verify_wait):
                print("  -> 搜索结果页验证未完成")
                break
            raw, status = wait_for_search_results(page, result_timeout_ms)
            if status == "verification":
                print("  -> 搜索结果页仍处于验证状态")
                break
        if status == "empty":
            print("  -> 页面提示无结果")
            break
        if status == "blank":
            print("  -> 页面为空白，CNKI 可能拦截当前浏览器会话；请在打开的 Chromium 窗口中检查机构访问或验证码")
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
        if not advance_to_next_page(page, verify_wait):
            break

    for idx, paper in enumerate(papers):
        paper["id"] = f"cnki-{idx + 1:03d}"
    return papers


def main() -> int:
    parser = argparse.ArgumentParser(description="知网多关键词检索")
    parser.add_argument("--keywords", required=True, help="逗号分隔的多组检索词")
    parser.add_argument("--year-from", type=int, default=None)
    parser.add_argument("--year-to", type=int, default=None)
    parser.add_argument("--journal-types", default="",
                        help="逗号分隔的来源类别，支持: 北大核心, CSCD, WJCI, EI, CSSCI, AMI, SCI")
    parser.add_argument("--core-journal", action="store_true", help="勾选 CNKI 来源类别中的北大核心")
    parser.add_argument("--ei-journal", action="store_true", help="勾选 CNKI 来源类别中的 EI")
    parser.add_argument("--max-results", type=int, default=40)
    parser.add_argument("--max-pages", type=int, default=10, help="每组关键词最多翻页数")
    parser.add_argument("--result-timeout", type=float, default=20,
                        help="等待结果表或无结果提示的最长秒数")
    parser.add_argument("--verify-wait", type=int, default=120,
                        help="搜索阶段触发验证码/安全验证时的等待秒数")
    parser.add_argument("--output", required=True, help="输出 JSON 路径")
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
    if args.verify_wait < 0:
        print("错误: --verify-wait 不能小于 0", file=sys.stderr)
        return 1
    if args.max_results <= 0 or args.max_pages <= 0:
        print("错误: --max-results 和 --max-pages 必须大于 0", file=sys.stderr)
        return 1

    queries = [q.strip() for q in args.keywords.split(",") if q.strip()]
    if not queries:
        print("错误: --keywords 不能为空", file=sys.stderr)
        return 1
    journal_types = parse_journal_types(args.journal_types, args.core_journal, args.ei_journal)

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"检索 {len(queries)} 组关键词: {queries}")
    if journal_types:
        labels = [JOURNAL_TYPE_LABELS.get(t, t) for t in journal_types]
        print(f"来源类别筛选: {labels}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
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
                    args.verify_wait,
                    year_from=args.year_from,
                    year_to=args.year_to,
                    journal_types=journal_types,
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
        "journal_types": journal_types,
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
