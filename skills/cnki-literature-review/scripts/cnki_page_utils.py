"""Shared CNKI page helpers used by search and download scripts."""

from __future__ import annotations

import re
import time

VERIFY_MARKERS = [
    "验证码",
    "安全验证",
    "人机验证",
    "拖动滑块",
    "滑动验证",
    "滑块验证",
    "请完成验证",
    "智能验证",
    "访问过于频繁",
]


def page_text(page) -> str:
    try:
        return page.evaluate("() => document.body ? document.body.innerText : ''")
    except Exception:
        return ""


def page_has_marker(page, markers: list[str]) -> bool:
    compact = re.sub(r"\s+", "", page_text(page))
    return any(marker in compact for marker in markers)


def page_has_verification_signal(page) -> bool:
    try:
        url = page.url.lower()
        title = page.title()
    except Exception:
        url = ""
        title = ""

    if "/verify/" in url or "captcha" in url:
        return True
    if "安全验证" in title or "验证码" in title:
        return True
    return page_has_marker(page, VERIFY_MARKERS)


def wait_for_verification_state(page, verify_wait: int, is_verification_page, resume_label: str) -> bool:
    if not is_verification_page(page):
        return True

    if verify_wait <= 0:
        return False

    print(f"  检测到 CNKI 验证页面，请在浏览器中完成验证（最多 {verify_wait}s）...")
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
                print(f"  验证已完成，{resume_label}")
                return True
    return False
