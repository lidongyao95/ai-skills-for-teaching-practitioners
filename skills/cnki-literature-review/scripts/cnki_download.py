#!/usr/bin/env python3
"""从知网下载 selected 文献的 PDF（需高校机构 IP）。"""

from __future__ import annotations

import argparse, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

CNKI_HOME = "https://www.cnki.net"
PDF_BUTTON_TEXTS = ["PDF下载", "PDF 下载", "下载PDF", "pdf下载", "PDF"]
DOWNLOAD_EVENT_WAIT_MS = 20_000
VERIFY_MARKERS = [
    "验证码",
    "安全验证",
    "人机验证",
    "拖动滑块",
    "滑块验证",
    "请完成验证",
]
PAID_MARKERS = [
    "付费下载",
    "需要付费",
    "需付费",
    "请先购买",
    "立即购买",
    "购买单篇",
    "余额不足",
    "账户余额不足",
    "支付订单",
    "订购本文",
    "收费下载",
]
PAID_PAGE_MARKER_GROUPS = [
    ["选择下载方式", "单篇下载"],
    ["选择下载方式", "仅下载本文"],
    ["选择下载方式", "开通会员"],
    ["单篇下载", "仅下载本文"],
]
RETRY_STATUSES = {"failed", "verification"}
REPLACE_STATUSES = {"paid"}
BROWSER_CLOSED_MARKERS = [
    "Target page, context or browser has been closed",
    "Target closed",
    "Browser has been closed",
    "browser has been closed",
]
MAX_BROWSER_RECOVERY_ATTEMPTS = 1


def safe_filename(title: str, max_len: int = 80) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip()
    return cleaned


def relative_to_workspace(path: Path, workspace: Path) -> str:
    try:
        return str(path.relative_to(workspace))
    except ValueError:
        return str(path)


def is_pdf(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 100:
        return False
    with path.open("rb") as f:
        return f.read(4) == b"%PDF"


def load_candidates(path: Path) -> tuple[list[dict], list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    papers = data.get("papers", data if isinstance(data, list) else [])
    selected = [p for p in papers if p.get("selected") and p.get("url")]
    replacements = [p for p in papers if not p.get("selected") and p.get("url")]

    ids = [p["id"] for p in selected]
    dupes = [i for i in ids if ids.count(i) > 1]
    if dupes:
        print(f"警告: 检测到重复 ID {list(set(dupes))}，请重新运行 curate.py 以分配唯一 ID", file=sys.stderr)
        raise SystemExit(1)

    return selected, replacements


def next_id_number(papers: list[dict]) -> int:
    max_id = 0
    for paper in papers:
        match = re.fullmatch(r"cnki-(\d+)", str(paper.get("id", "")))
        if match:
            max_id = max(max_id, int(match.group(1)))
    return max_id + 1


def pop_replacement(replacements: list[dict], used_titles: set[str], replacement_no: int) -> tuple[dict | None, int]:
    while replacements:
        paper = replacements.pop(0)
        title = paper.get("title", "")
        if title in used_titles:
            continue
        replacement = dict(paper)
        replacement["original_id"] = replacement.get("id")
        replacement["id"] = f"cnki-{replacement_no:03d}"
        replacement["selected"] = True
        replacement["replacement"] = True
        used_titles.add(title)
        return replacement, replacement_no + 1
    return None, replacement_no


def save_meta(meta_dir: Path, paper: dict, download_info: dict) -> None:
    meta = {**paper, "download": download_info}
    meta_dir.mkdir(parents=True, exist_ok=True)
    safe_id = paper["id"]
    (meta_dir / f"{safe_id}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8",
    )


def save_debug_snapshot(page, debug_dir: Path, paper: dict) -> dict:
    debug_dir.mkdir(parents=True, exist_ok=True)
    workspace = debug_dir.parent.parent
    pid = paper["id"]
    title = safe_filename(paper.get("title", "untitled"), max_len=30)
    base = f"{pid}_{title}"
    html_path = debug_dir / f"{base}.html"
    png_path = debug_dir / f"{base}.png"

    info = {
        "page_url": page.url,
        "page_title": page.title(),
    }

    try:
        html_path.write_text(page.content(), encoding="utf-8")
        info["debug_html"] = relative_to_workspace(html_path, workspace)
    except Exception as exc:
        info["debug_html_error"] = str(exc)

    try:
        page.screenshot(path=png_path, full_page=True)
        info["debug_screenshot"] = relative_to_workspace(png_path, workspace)
    except Exception as exc:
        info["debug_screenshot_error"] = str(exc)

    return info


def page_text(page) -> str:
    try:
        return page.evaluate("() => document.body ? document.body.innerText : ''")
    except Exception:
        return ""


def page_has_marker(page, markers: list[str]) -> bool:
    compact = re.sub(r"\s+", "", page_text(page))
    return any(marker in compact for marker in markers)


def text_has_paid_marker(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    if any(marker in compact for marker in PAID_MARKERS):
        return True
    if any(all(marker in compact for marker in group) for group in PAID_PAGE_MARKER_GROUPS):
        return True
    return "选择下载方式" in compact and re.search(r"[￥¥]\d+(?:\.\d+)?", compact) is not None


def url_looks_like_paid(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    return host.endswith("cnki.net") and path.startswith("/bar/fee_")


def url_looks_like_paid_asset(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    return host.endswith("cnki.net") and path.startswith("/gw/api/get/pdf/ads/")


def page_has_paid_marker(page) -> bool:
    try:
        if url_looks_like_paid(page.url) or url_looks_like_paid_asset(page.url):
            return True
    except Exception:
        pass
    return text_has_paid_marker(page_text(page))


def page_has_download_candidate(page) -> bool:
    try:
        for label in PDF_BUTTON_TEXTS:
            if page.locator("a, button").filter(has_text=label).count() > 0:
                return True
        for sel in ["a#pdfDown", "a[href*='pdf'], a[href*='PDF']", ".btn-dlpdf"]:
            if page.locator(sel).count() > 0:
                return True
    except Exception:
        return False
    return False


def page_looks_like_article(page) -> bool:
    if page_has_download_candidate(page):
        return True

    compact = re.sub(r"\s+", "", page_text(page))
    article_markers = ["HTML阅读", "CNKIAI阅读", "摘要", "关键词", "作者", "来源", "发表时间"]
    return sum(1 for marker in article_markers if marker in compact) >= 2


def is_verification_page(page) -> bool:
    try:
        url = page.url.lower()
        title = page.title()
    except Exception:
        url = ""
        title = ""

    if page_looks_like_article(page):
        return False
    if "/verify/" in url or "captcha" in url:
        return True
    if "安全验证" in title:
        return True
    return page_has_marker(page, VERIFY_MARKERS)


def wait_for_verification(page, verify_wait: int) -> bool:
    if not is_verification_page(page):
        return True

    if verify_wait <= 0:
        return False

    print(f"  检测到验证页面，请在浏览器中完成验证（最多 {verify_wait}s）...")
    deadline = time.monotonic() + verify_wait
    next_status_at = time.monotonic() + 10
    while time.monotonic() < deadline:
        page.wait_for_timeout(1000)
        if time.monotonic() >= next_status_at:
            try:
                print(f"  仍在等待验证完成: {page.title()} {page.url}")
            except Exception:
                print("  仍在等待验证完成")
            next_status_at = time.monotonic() + 10
        if not is_verification_page(page):
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            page.wait_for_timeout(1000)
            if not is_verification_page(page):
                print("  验证已完成，继续下载")
                return True
    return False


def close_paid_popups(main_page, popups: list) -> None:
    for popup in list(popups):
        if popup == main_page:
            continue
        try:
            if not popup.is_closed() and page_has_paid_marker(popup):
                popup.close()
        except Exception:
            pass


def click_download_candidate(page, locator, out_path: Path) -> str:
    downloads = []
    popups = []
    paid_requests = []

    def on_download(download) -> None:
        downloads.append(download)

    def on_popup(popup) -> None:
        popups.append(popup)
        popup.on("download", on_download)

    def on_request(request) -> None:
        try:
            if url_looks_like_paid(request.url) or url_looks_like_paid_asset(request.url):
                paid_requests.append(request.url)
        except Exception:
            pass

    try:
        page.on("download", on_download)
        page.on("popup", on_popup)
        page.context.on("page", on_popup)
        page.context.on("request", on_request)
        locator.click(timeout=5000)

        deadline = time.monotonic() + DOWNLOAD_EVENT_WAIT_MS / 1000
        while time.monotonic() < deadline:
            if paid_requests:
                close_paid_popups(page, popups)
                return "paid"
            if downloads:
                if url_looks_like_paid_asset(downloads[0].url):
                    close_paid_popups(page, popups)
                    return "paid"
                downloads[0].save_as(out_path)
                return "downloaded"
            active_pages = [page, *popups]
            if any(is_verification_page(active_page) for active_page in active_pages):
                return "verification"
            if any(page_has_paid_marker(active_page) for active_page in active_pages):
                close_paid_popups(page, popups)
                return "paid"
            page.wait_for_timeout(500)

        return "opened_page" if popups else "no_download"
    except Exception:
        return "no_download"
    finally:
        for event, handler in [("download", on_download), ("popup", on_popup)]:
            try:
                page.remove_listener(event, handler)
            except Exception:
                pass
        try:
            page.context.remove_listener("page", on_popup)
        except Exception:
            pass
        try:
            page.context.remove_listener("request", on_request)
        except Exception:
            pass
        for popup in popups:
            try:
                popup.remove_listener("download", on_download)
            except Exception:
                pass


def find_and_click_pdf_download(page, out_path: Path) -> str:
    for label in PDF_BUTTON_TEXTS:
        btn = page.locator("a, button").filter(has_text=label).first
        if btn.count() > 0:
            result = click_download_candidate(page, btn, out_path)
            if result != "no_download":
                return result

    for sel in ["a#pdfDown", "a[href*='pdf'], a[href*='PDF']", ".btn-dlpdf"]:
        loc = page.locator(sel).first
        if loc.count() > 0:
            result = click_download_candidate(page, loc, out_path)
            if result != "no_download":
                return result

    return "no_download"


def paid_result(page, debug_dir: Path, paper: dict) -> dict:
    debug_info = save_debug_snapshot(page, debug_dir, paper)
    return {
        "status": "paid",
        "reason": "页面提示需要付费下载",
        **debug_info,
    }


def is_browser_closed_error(exc: Exception) -> bool:
    message = str(exc)
    return any(marker in message for marker in BROWSER_CLOSED_MARKERS)


def open_download_session(playwright, args, initial: bool):
    browser = playwright.chromium.launch(headless=args.headless)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    if initial:
        if args.headless and args.manual_wait > 0:
            print(f"打开知网首页，headless 模式等待 {args.manual_wait}s（无法人工处理验证码/登录）...")
        elif args.manual_wait > 0:
            print(f"打开知网首页，等待机构认证或验证码处理（最多 {args.manual_wait}s）...")
        else:
            print("打开知网首页，跳过机构认证等待（--manual-wait 0）...")
        page.goto(CNKI_HOME, wait_until="domcontentloaded", timeout=60000)
        if args.manual_wait > 0:
            time.sleep(args.manual_wait)
    else:
        print("  检测到浏览器页面已关闭，正在重新打开浏览器会话...")
        try:
            page.goto(CNKI_HOME, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1000)
        except Exception as exc:
            print(f"  警告: 重新打开知网首页失败，将直接重试当前文献: {exc}")

    return browser, context, page


def close_download_session(browser, context) -> None:
    try:
        context.close()
    except Exception:
        pass
    try:
        browser.close()
    except Exception:
        pass


def try_download_pdf(page, pdf_dir: Path, debug_dir: Path, paper: dict, verify_wait: int, navigate: bool = True) -> dict:
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

    started_on_verification = False
    if navigate:
        page.goto(paper["url"], wait_until="domcontentloaded", timeout=90000)
        started_on_verification = is_verification_page(page)
        time.sleep(2)

    if not wait_for_verification(page, verify_wait):
        debug_info = save_debug_snapshot(page, debug_dir, paper)
        return {
            "status": "verification",
            "reason": "页面需要验证，等待后仍未通过",
            **debug_info,
        }
    if started_on_verification:
        print("  验证通过后重新打开原始文章页面")
        page.goto(paper["url"], wait_until="domcontentloaded", timeout=90000)
        time.sleep(2)
        if is_verification_page(page):
            debug_info = save_debug_snapshot(page, debug_dir, paper)
            return {
                "status": "verification",
                "reason": "验证通过后重新打开文章页仍需要验证",
                **debug_info,
            }
    if navigate and not page_looks_like_article(page) and not page_has_paid_marker(page):
        print("  当前页不是文章详情页，重新打开原始文章页面")
        page.goto(paper["url"], wait_until="domcontentloaded", timeout=90000)
        time.sleep(2)
        if is_verification_page(page):
            debug_info = save_debug_snapshot(page, debug_dir, paper)
            return {
                "status": "verification",
                "reason": "重新打开文章页后仍需要验证",
                **debug_info,
            }

    if page_has_paid_marker(page):
        return paid_result(page, debug_dir, paper)

    click_result = find_and_click_pdf_download(page, out_path)

    if click_result != "downloaded":
        if click_result == "verification" or is_verification_page(page):
            if wait_for_verification(page, verify_wait):
                print("  点击下载验证通过后重新打开原始文章页面")
                return try_download_pdf(page, pdf_dir, debug_dir, paper, 0, navigate=True)
            debug_info = save_debug_snapshot(page, debug_dir, paper)
            return {
                "status": "verification",
                "reason": "点击下载后出现验证，等待后仍未通过",
                **debug_info,
            }

        if click_result == "paid" or page_has_paid_marker(page):
            return paid_result(page, debug_dir, paper)

        debug_info = save_debug_snapshot(page, debug_dir, paper)
        return {
            "status": "failed",
            "reason": "未找到 PDF 下载按钮",
            **debug_info,
        }

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
    parser.add_argument("--manual-wait", type=int, default=60,
                        help="打开知网首页后的等待秒数；已确认无需认证时设为 0")
    parser.add_argument("--verify-wait", type=int, default=120,
                        help="详情页触发验证码/安全验证时的等待秒数")
    parser.add_argument("--retry-failed", type=int, default=1,
                        help="批量结束后重试普通失败文献的轮数")
    parser.add_argument("--no-replace-paid", action="store_true",
                        help="遇到付费下载页面时不从候选列表补充替换文献")
    parser.add_argument("--headless", action="store_true", help="无头模式；CNKI 可能返回空白页，建议默认有界面运行")
    parser.add_argument("--clean", action="store_true", help="下载前清理旧的 PDF、meta 和 text 文件")
    args = parser.parse_args()

    if args.manual_wait < 0:
        print("错误: --manual-wait 不能小于 0", file=sys.stderr)
        return 1
    if args.verify_wait < 0 or args.retry_failed < 0:
        print("错误: --verify-wait 和 --retry-failed 不能小于 0", file=sys.stderr)
        return 1

    root = Path(args.workspace).resolve()
    pdf_dir = root / "papers" / "pdf"
    meta_dir = root / "papers" / "meta"
    text_dir = root / "papers" / "text"
    debug_dir = root / "logs" / "download-debug"
    log_path = root / "logs" / "download.log"

    pdf_dir.mkdir(parents=True, exist_ok=True)
    papers, replacements = load_candidates(Path(args.input).resolve())
    target_count = len(papers)
    used_titles = {p.get("title", "") for p in papers}
    replacement_no = next_id_number(papers)

    if args.clean:
        for d, pat in [(pdf_dir, "*.pdf"), (meta_dir, "*.json"), (text_dir, "*.txt")]:
            for f in d.glob(pat):
                f.unlink()
                print(f"  清理: {f.name}")
        print("旧文件已清理")
    if not papers:
        print("无 selected=true 的文献", file=sys.stderr)
        return 1

    if sync_playwright is None:
        raise SystemExit(
            "python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple playwright && "
            "PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright "
            "python3 -m playwright install chromium"
        )

    print(f"待下载 {len(papers)} 篇（需机构 IP 认证）")
    if replacements:
        print(f"候选替补 {len(replacements)} 篇（付费页可自动补位）")

    ok, fail = 0, 0
    retry_queue = []

    def handle_result(paper: dict, result: dict, allow_replace: bool = True) -> None:
        nonlocal fail, ok, replacement_no
        save_meta(meta_dir, paper, result)
        title = paper.get("title", "")[:40]
        pid = paper["id"]
        log_line = f"{'OK' if result.get('status') in ('ok','cached') else 'FAIL'} {pid} {title} [{result.get('status')}]"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as lf:
            lf.write(log_line + "\n")

        if result.get("status") in ("ok", "cached"):
            print(f"  OK -> {result.get('pdf_file')}")
            ok += 1
            return

        print(f"  FAIL: {result.get('reason', 'unknown')}")
        fail += 1

        if result.get("status") in RETRY_STATUSES and result.get("status") not in REPLACE_STATUSES:
            retry_queue.append(paper)

        if allow_replace and not args.no_replace_paid and result.get("status") in REPLACE_STATUSES:
            replacement, replacement_no = pop_replacement(replacements, used_titles, replacement_no)
            if replacement:
                papers.append(replacement)
                print(f"  付费终态，跳过重试；从候选池补位: {replacement['id']} {replacement.get('title', '')[:40]}...")
            else:
                print("  无可用替补文献")

    with sync_playwright() as p:
        browser, context, page = open_download_session(p, args, initial=True)

        def run_download_with_recovery(paper: dict) -> dict:
            nonlocal browser, context, page
            attempts = 0
            while True:
                try:
                    return try_download_pdf(page, pdf_dir, debug_dir, paper, args.verify_wait)
                except Exception as exc:
                    if is_browser_closed_error(exc) and attempts < MAX_BROWSER_RECOVERY_ATTEMPTS:
                        attempts += 1
                        close_download_session(browser, context)
                        browser, context, page = open_download_session(p, args, initial=False)
                        continue
                    return {"status": "failed", "reason": str(exc)}

        i = 0
        while i < len(papers):
            paper = papers[i]
            pid = paper["id"]
            title = paper.get("title", "")[:40]
            print(f"[{i+1}/{len(papers)}] {pid} {title}...")

            result = run_download_with_recovery(paper)
            handle_result(paper, result)

            i += 1
            if i < len(papers):
                time.sleep(args.delay)

        for round_no in range(args.retry_failed):
            if not retry_queue:
                break
            current_retry = retry_queue
            retry_queue = []
            print(f"\n重试普通失败文献（第 {round_no + 1}/{args.retry_failed} 轮，共 {len(current_retry)} 篇）")
            for ri, paper in enumerate(current_retry):
                pid = paper["id"]
                title = paper.get("title", "")[:40]
                print(f"[retry {ri+1}/{len(current_retry)}] {pid} {title}...")
                result = run_download_with_recovery(paper)
                handle_result(paper, result, allow_replace=True)
                if ri < len(current_retry) - 1:
                    time.sleep(args.delay)

            while i < len(papers):
                paper = papers[i]
                pid = paper["id"]
                title = paper.get("title", "")[:40]
                print(f"[{i+1}/{len(papers)}] {pid} {title}...")

                result = run_download_with_recovery(paper)
                handle_result(paper, result)

                i += 1
                if i < len(papers):
                    time.sleep(args.delay)

        close_download_session(browser, context)

    print(f"\n完成: 成功 {ok}, 失败 {fail}, 目标 {target_count}")
    return 0 if ok > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
