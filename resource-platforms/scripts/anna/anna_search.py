#!/usr/bin/env python3
"""Search Anna's Archive for book and article metadata.

This is a search-only adapter helper. It discovers Anna detail pages and
metadata, but does not download files or call Anna's fast-download API.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "annas-archive.gl"
ANNA_SITE_FILTERS = [
    "annas-archive.org",
    "annas-archive.li",
    "annas-archive.se",
    "annas-archive.gl",
]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
FORMAT_PATTERN = re.compile(r"\b(EPUB|PDF|MOBI|AZW3?|DJVU|CBZ|CBR|FB2|DOCX?|TXT)\b", re.I)
SIZE_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:KB|MB|GB|TB)\b", re.I)
ANNA_URL_PATTERN = re.compile(r"https://annas-archive\.[a-z0-9-]+/?", re.I)
MD5_URL_PATTERN = re.compile(r"/md5/([0-9a-fA-F]{32})\b", re.I)

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from generic import generic_search
except Exception:  # pragma: no cover - fallback reports this at runtime.
    generic_search = None


class SearchBlockedError(RuntimeError):
    """Anna's Archive returned an anti-bot or verification page."""


def normalize_base_url(raw: str | None) -> str:
    value = (raw or "").strip().rstrip("/")
    value = re.sub(r"^https?://", "", value)
    return value or DEFAULT_BASE_URL


def normalize_fallback_mode(raw: str | None) -> str:
    value = (raw or os.environ.get("ANNAS_FALLBACK") or "auto").strip().lower()
    if value in {"0", "false", "no", "off", "never"}:
        return "never"
    if value in {"1", "true", "yes", "on", "always"}:
        return "always"
    return "auto"


def parse_fallback_engines(raw: str | None) -> list[str]:
    value = (raw or os.environ.get("ANNAS_FALLBACK_ENGINES") or "").strip()
    if value:
        engines = [part.strip().lower() for part in value.split(",") if part.strip()]
    else:
        engines = ["bing", "duckduckgo"]
        if os.environ.get("JINA_API_KEY"):
            engines.insert(1, "jina")
    return list(dict.fromkeys(engines)) or ["bing"]


def request_text(url: str, timeout: float) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
        },
    )
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        is_cert_error = isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc)
        if not is_cert_error:
            raise
        response = urllib.request.urlopen(request, timeout=timeout, context=ssl._create_unverified_context())
    with response:
        status = getattr(response, "status", 200)
        if status >= 400:
            raise urllib.error.HTTPError(url, status, f"HTTP {status}", response.headers, None)
        return response.read().decode("utf-8", errors="replace")


def is_blocked_page(page: str) -> bool:
    lowered = page.lower()
    # Anna result pages can contain anti-spam/captcha terms in embedded text or
    # copied metadata while still carrying real /md5/ result links. Treat marker
    # pages as blocked only when they do not look like search-result pages.
    if len(MD5_URL_PATTERN.findall(page)) >= 3:
        return False
    return any(marker in lowered for marker in (
        "ddos-guard",
        "captcha",
        "verify you are human",
        "checking your browser",
        "attention required",
    ))


def resolve_base_url(base_url: str | None, auto: bool, timeout: float) -> str:
    fallback = normalize_base_url(base_url or os.environ.get("ANNAS_BASE_URL"))
    if not auto:
        return fallback

    try:
        status_page = request_text("https://open-slum.org/", min(timeout, 10))
    except Exception:
        return fallback

    candidates: list[str] = []
    for match in ANNA_URL_PATTERN.findall(status_page):
        candidate = normalize_base_url(match)
        if candidate not in candidates:
            candidates.append(candidate)
    if fallback not in candidates:
        candidates.append(fallback)

    for candidate in candidates[:8]:
        probe = f"https://{candidate}/search?q=test&content=book_any"
        try:
            page = request_text(probe, min(timeout, 10))
        except Exception:
            continue
        if page and not is_blocked_page(page):
            return candidate
    return fallback


def clean_text(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def html_attr(tag: str, name: str) -> str:
    match = re.search(rf'\b{name}\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))', tag, re.I)
    return html.unescape(match.group(2) or match.group(3) or match.group(4) or "").strip() if match else ""


def absolute_url(base_url: str, href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"https://{base_url}{href}"
    return urllib.parse.urljoin(f"https://{base_url}/", href)


def is_anna_detail_url(url: str) -> tuple[bool, str]:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower().split("@")[-1].split(":")[0]
    is_anna = host.startswith("annas-archive.")
    match = MD5_URL_PATTERN.search(parsed.path)
    return bool(is_anna and match), (match.group(1).lower() if match else "")


def split_result_blocks(page: str) -> list[str]:
    marker = re.compile(r'<a\b[^>]*href=["\']/md5/[0-9a-fA-F]{32}["\'][^>]*class=["\'][^"\']*custom-a block', re.I)
    matches = list(marker.finditer(page))
    if not matches:
        marker = re.compile(r'<a\b[^>]*href=["\']/md5/[0-9a-fA-F]{32}["\'][^>]*>', re.I)
        matches = list(marker.finditer(page))
    blocks: list[str] = []
    for index, match in enumerate(matches):
        start = max(0, match.start() - 700)
        end = matches[index + 1].start() if index + 1 < len(matches) else min(len(page), match.start() + 8000)
        blocks.append(page[start:end])
    return blocks


def extract_icon_link(block: str, icon_name: str) -> str:
    pattern = re.compile(
        rf'<a\b[^>]*href=["\']/search[^"\']*["\'][^>]*>.*?icon-\[mdi--{re.escape(icon_name)}\].*?</span>(.*?)</a>',
        re.I | re.S,
    )
    match = pattern.search(block)
    return clean_text(match.group(1)) if match else ""


def extract_first_class_text(block: str, class_fragment: str) -> str:
    pattern = re.compile(rf'<div\b[^>]*class=["\'][^"\']*{re.escape(class_fragment)}[^"\']*["\'][^>]*>(.*?)</div>', re.I | re.S)
    match = pattern.search(block)
    return clean_text(match.group(1)) if match else ""


def extract_meta(meta: str) -> tuple[str, str, str]:
    language = ""
    fmt = ""
    size = ""

    if meta:
        meta = re.split(r"\s+Save\s*\(", meta, maxsplit=1)[0].strip()
        first = re.split(r"\s*[·•]\s*|\s+路\s+", meta)[0].strip()
        first = re.sub(r"^[^\w\u4e00-\u9fff]+", "", first).strip()
        language = re.sub(r"\s*\[[^\]]+\].*$", "", first).strip()

        format_match = FORMAT_PATTERN.search(meta)
        if format_match:
            fmt = format_match.group(1).upper()

        size_match = SIZE_PATTERN.search(meta)
        if size_match:
            size = re.sub(r"\s+", "", size_match.group(0).upper())
    return language, fmt, size


def infer_result_type(content: str, meta: str) -> str:
    lowered = meta.lower()
    if "book" in lowered or "📘" in meta:
        return "图书"
    if "journal" in lowered or "article" in lowered or "paper" in lowered:
        return "论文"
    if content == "journal":
        return "论文"
    return "图书"


def parse_search_results(page: str, query: str, base_url: str, content: str, max_results: int) -> list[dict[str, Any]]:
    if is_blocked_page(page):
        raise SearchBlockedError("Anna's Archive returned an anti-bot verification page")

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rank, block in enumerate(split_result_blocks(page), 1):
        md5_match = re.search(r'href=["\']/md5/([0-9a-fA-F]{32})["\']', block, re.I)
        if not md5_match:
            continue
        md5 = md5_match.group(1).lower()
        if md5 in seen:
            continue
        seen.add(md5)

        title = ""
        for link_match in re.finditer(r'<a\b[^>]*href=["\']/md5/[0-9a-fA-F]{32}["\'][^>]*>(.*?)</a>', block, re.I | re.S):
            candidate = clean_text(link_match.group(1))
            if candidate:
                title = candidate
                break
        if not title:
            fallback = re.search(r'data-content=["\']([^"\']+)["\']', block, re.I)
            title = html.unescape(fallback.group(1)).strip() if fallback else f"Anna record {md5}"

        author = extract_icon_link(block, "user-edit")
        publisher = extract_icon_link(block, "company")
        meta = extract_first_class_text(block, "text-gray-800")
        meta = re.split(r"\s+Save\s*\(", meta, maxsplit=1)[0].strip()
        description = extract_first_class_text(block, "text-sm text-gray-600")
        language, fmt, size = extract_meta(meta)
        result_type = infer_result_type(content, meta)
        cover = ""
        img_match = re.search(r"<img\b[^>]*>", block, re.I | re.S)
        if img_match:
            cover = html_attr(img_match.group(0), "src")

        source_url = f"https://{base_url}/md5/{md5}"
        resource_id = f"anna:{md5}"
        signals: dict[str, Any] = {"engine": f"anna-{content}", "rank": rank}

        item: dict[str, Any] = {
            "resource_id": resource_id,
            "platform": "anna",
            "title": title,
            "source_url": source_url,
            "type": result_type,
            "download_feasibility": "低",
            "platform_signals": signals,
            "raw_metadata": {
                "hash": md5,
                "content": content,
                "query": query,
                "base_url": base_url,
            },
        }
        if description:
            item["description"] = description
        if author:
            item["author"] = author
        if publisher:
            item["provider"] = publisher
        if language:
            item["language"] = language
        if cover:
            item["thumbnail_url"] = cover
        if fmt or size or meta:
            item["raw_metadata"].update({
                key: value for key, value in {
                    "format": fmt,
                    "size": size,
                    "meta": meta,
                }.items() if value
            })

        results.append(item)
        if len(results) >= max_results:
            break
    return results


def convert_generic_fallback_result(item: dict[str, Any], query: str, content: str, rank: int) -> dict[str, Any] | None:
    source_url = str(item.get("source_url") or item.get("url") or "").strip()
    is_detail, md5 = is_anna_detail_url(source_url)
    if not is_detail:
        return None

    title = clean_text(str(item.get("title") or ""))
    if not title:
        title = f"Anna record {md5}"
    description = clean_text(str(item.get("description") or item.get("snippet") or ""))
    source_signals = item.get("platform_signals") if isinstance(item.get("platform_signals"), dict) else {}
    source_engine = str(source_signals.get("engine") or "generic")
    source_rank = source_signals.get("rank")
    result_type = "论文" if content == "journal" else ("图书/论文" if content == "all" else "图书")

    raw_metadata: dict[str, Any] = {
        "hash": md5,
        "content": content,
        "query": query,
        "fallback": "generic-public-web",
        "source_engine": source_engine,
    }
    if isinstance(source_rank, (int, float, str)):
        raw_metadata["source_rank"] = source_rank

    result: dict[str, Any] = {
        "resource_id": f"anna:{md5}",
        "platform": "anna",
        "title": title,
        "source_url": source_url,
        "type": result_type,
        "download_feasibility": "低",
        "platform_signals": {"engine": f"anna-generic-{source_engine}", "rank": rank},
        "raw_metadata": raw_metadata,
    }
    if description:
        result["description"] = description
    return result


def fallback_search_public_web(
    query: str,
    content: str,
    max_results: int,
    timeout: float,
    engines: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if generic_search is None:
        return [], [{
            "error_code": "SYSTEM_DEPENDENCY_MISSING",
            "message": "通用搜索模块不可用，无法执行 Anna 公开搜索兜底",
            "retryable": False,
        }]

    try:
        document = generic_search.search(
            query,
            engines=engines,
            limit=max(max_results * 2, 5),
            timeout=timeout,
            site=",".join(ANNA_SITE_FILTERS),
        )
    except Exception as exc:
        return [], [{
            "error_code": "SEARCH_EXECUTION_FAILED",
            "message": f"Anna 公开搜索兜底失败: {type(exc).__name__}: {exc}",
            "retryable": True,
        }]

    errors: list[dict[str, Any]] = []
    for error in document.get("errors") or []:
        if not isinstance(error, dict):
            continue
        message = str(error.get("message") or "公开搜索兜底失败")
        errors.append({
            "error_code": str(error.get("error_code") or "SEARCH_EXECUTION_FAILED"),
            "message": message,
            "retryable": bool(error.get("retryable", True)),
            "engine": error.get("engine"),
        })

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in document.get("results") or []:
        if not isinstance(item, dict):
            continue
        converted = convert_generic_fallback_result(item, query, content, len(results) + 1)
        if not converted:
            continue
        key = converted["source_url"]
        if key in seen:
            continue
        seen.add(key)
        results.append(converted)
        if len(results) >= max_results:
            break

    if not results and not errors:
        errors.append({
            "error_code": "SEARCH_NO_RESULTS",
            "message": "Anna 公开搜索兜底未返回可解析的详情页链接",
            "retryable": True,
        })
    return results, errors


def search_urls(base_url: str, query: str, content: str) -> list[str]:
    encoded = urllib.parse.urlencode({"q": query})
    if content == "book_any":
        return [
            f"https://{base_url}/search?{encoded}",
            f"https://{base_url}/search?" + urllib.parse.urlencode({"q": query, "content": "book_any"}),
        ]
    if content == "journal":
        return [
            f"https://{base_url}/search?index=articles&{encoded}",
            f"https://{base_url}/search?" + urllib.parse.urlencode({"q": query, "content": "journal"}),
        ]
    return [
        f"https://{base_url}/search?{encoded}",
        f"https://{base_url}/search?" + urllib.parse.urlencode({"q": query, "content": content}),
    ]


def search(
    query: str,
    content: str,
    max_results: int,
    base_url: str,
    auto_base_url: bool,
    timeout: float,
    fallback: str = "auto",
    fallback_engines: list[str] | None = None,
) -> dict[str, Any]:
    resolved_base = resolve_base_url(base_url, auto_base_url, timeout)
    contents = ["book_any", "journal"] if content == "all" else [content]
    per_content_limit = max_results if len(contents) == 1 else max_results
    combined: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    fallback_mode = normalize_fallback_mode(fallback)
    methods: list[str] = []

    if fallback_mode != "always":
        methods.append("anna-direct")
        for content_value in contents:
            content_errors: list[dict[str, Any]] = []
            for url in search_urls(resolved_base, query, content_value):
                try:
                    page = request_text(url, timeout)
                    parsed = parse_search_results(page, query, resolved_base, content_value, per_content_limit)
                    combined.extend(parsed)
                    if parsed:
                        content_errors = []
                        break
                except SearchBlockedError as exc:
                    content_errors.append({"error_code": "SEARCH_BLOCKED", "message": str(exc), "retryable": True})
                except TimeoutError as exc:
                    content_errors.append({"error_code": "NETWORK_TIMEOUT", "message": str(exc), "retryable": True})
                except Exception as exc:
                    content_errors.append({"error_code": "NETWORK_ERROR", "message": str(exc), "retryable": True})
            errors.extend(content_errors)

    deduped: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in combined:
        url = item["source_url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)
        if len(deduped) >= max_results:
            break

    if fallback_mode == "always" or (fallback_mode == "auto" and not deduped):
        methods.append("generic-fallback")
        fallback_results, fallback_errors = fallback_search_public_web(
            query=query,
            content=content,
            max_results=max_results,
            timeout=min(timeout, 15),
            engines=fallback_engines or parse_fallback_engines(None),
        )
        for item in fallback_results:
            url = item["source_url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            deduped.append(item)
            if len(deduped) >= max_results:
                break
        if deduped:
            warnings.extend(errors)
            warnings.extend(fallback_errors)
            errors = []
        else:
            errors.extend(fallback_errors)

    if not deduped and "generic-fallback" in methods:
        errors.insert(0, {
            "error_code": "SEARCH_NO_RESULTS",
            "message": "Anna 直连搜索不可用或无结果，公开搜索兜底也未返回可解析的详情页链接",
            "retryable": True,
        })
    elif not deduped and not errors:
        errors.append({
            "error_code": "SEARCH_NO_RESULTS",
            "message": "Anna 未返回可解析的搜索结果",
            "retryable": True,
        })

    document = {
        "query": query,
        "base_url": resolved_base,
        "content": content,
        "search_method": "+".join(methods),
        "results": deduped,
        "errors": errors,
        "warnings": warnings,
        "searched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    return document


def write_output(document: dict[str, Any], output: str | None) -> None:
    text = json.dumps(document, ensure_ascii=False, indent=2)
    if output:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Anna's Archive metadata.")
    sub = parser.add_subparsers(dest="cmd")
    command = sub.add_parser("search", help="search Anna's Archive")
    command.add_argument("query")
    command.add_argument("--max", type=int, default=10)
    command.add_argument("--content", choices=["book", "article", "all", "book_any", "journal"], default="book")
    command.add_argument("--base-url", default="")
    command.add_argument("--auto-base-url", action="store_true")
    command.add_argument("--timeout", type=float, default=30)
    command.add_argument("--fallback", choices=["auto", "always", "never"], default="auto")
    command.add_argument("--fallback-engines", default="")
    command.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    if args.cmd != "search":
        parser.print_help()
        return 2

    content_map = {"book": "book_any", "article": "journal"}
    content = content_map.get(args.content, args.content)
    document = search(
        query=args.query,
        content=content,
        max_results=max(1, min(args.max, 50)),
        base_url=args.base_url,
        auto_base_url=bool(args.auto_base_url or os.environ.get("ANNAS_AUTO_BASE_URL", "").lower() == "true"),
        timeout=max(1.0, args.timeout),
        fallback=args.fallback,
        fallback_engines=parse_fallback_engines(args.fallback_engines),
    )
    if document["errors"] and not document["results"]:
        document["error"] = document["errors"][0]
    write_output(document, args.output)
    return 0 if document["results"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
