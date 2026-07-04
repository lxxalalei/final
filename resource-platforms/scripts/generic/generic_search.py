#!/usr/bin/env python3
"""Search the public web through multiple engines, then URL-deduplicate results."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import html
import json
import os
import re
import ssl
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
ALLOWED_ENGINES = {"baidu", "bing", "duckduckgo", "github", "jina"}
ENGINE_PRESETS = {
    "web": ["bing", "duckduckgo", "baidu"],
    "global": ["duckduckgo", "bing", "jina"],
    "china": ["baidu", "bing"],
    "dev": ["github", "bing", "duckduckgo"],
    "all": ["bing", "duckduckgo", "baidu", "jina", "github"],
}
SITE_PACKS = {
    "kepu": ["kepuchina.cn", "cdstm.cn", "cibst.cn"],
    "cctv": ["cctv.com", "cntv.cn", "yangshipin.cn"],
    "poetry": ["gushiwen.cn", "sou-yun.cn"],
    "textbook": ["pep.com.cn", "basic.smartedu.cn", "eduyun.cn"],
    "museum": ["chnmuseum.cn", "dpm.org.cn", "shanghaimuseum.net", "namoc.org"],
    "library": ["nlc.cn", "kids.nlc.cn", "mylib.nlc.cn"],
}
DIRECT_SITE_PACK_ENGINES = {"kepu"}
CDSTM_SERVICE_ID = "sT7I9StjJmJrznxcoft9c"
CDSTM_DEFAULT_CATE_ID = "KGA7sHXaaux0bs9wfhEBs"
CDSTM_SEARCH_BASE = "https://www.cdstm.cn/api-gateway/jpaas-jsearch-web-server/"
CCTV_SEARCH_BASE = "https://search.cctv.com/search.php"


class SearchBlockedError(RuntimeError):
    """The engine returned a verification or anti-bot page instead of results."""


def _clean_text(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _html_attr(tag: str, name: str) -> str:
    match = re.search(rf'\b{name}\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))', tag, re.I)
    if not match:
        return ""
    return html.unescape(match.group(2) or match.group(3) or match.group(4) or "").strip()


def _canonical_url(value: str) -> str:
    value = html.unescape(value).strip()
    if value.startswith("//"):
        value = "https:" + value
    if value.startswith("/l/"):
        value = "https://duckduckgo.com" + value
    parsed = urlparse(value)
    if parsed.netloc.endswith("bing.com") and parsed.path == "/ck/a":
        target = parse_qs(parsed.query).get("u", [""])[0]
        if target.startswith("a1"):
            # Bing may encode the target after the a1 marker. Leave undecodable
            # links unchanged rather than inventing a destination.
            target = target[2:]
        decoded = unquote(target)
        if decoded.startswith(("http://", "https://")):
            value = decoded
            parsed = urlparse(value)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        decoded = unquote(target)
        if decoded.startswith(("http://", "https://")):
            value = decoded
            parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    if parsed.netloc.endswith(("baidu.com", "bing.com", "microsoft.com")):
        return ""
    return parsed._replace(fragment="").geturl()


def _make_result(
    title: str,
    url: str,
    snippet: str,
    engine: str,
    rank: int,
    query: str,
    *,
    result_type: str = "网页",
    author: str | None = None,
    language: str | None = None,
    publish_time: str | None = None,
    extra_signals: dict[str, Any] | None = None,
    raw_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    signals = {"engine": engine, "rank": rank}
    if extra_signals:
        signals.update({key: value for key, value in extra_signals.items() if value is not None})
    return {
        "resource_id": f"generic:{key}",
        "platform_resource_id": key,
        "platform": "generic",
        "title": title,
        "source_url": url,
        "type": result_type,
        "description": snippet or None,
        "author": author,
        "duration": None,
        "publish_time": publish_time,
        "is_free": None,
        "language": language,
        "thumbnail_url": None,
        "download_feasibility": "低",
        "platform_signals": signals,
        "raw_metadata": {"query": query, **dict(raw_metadata or {})},
    }


def parse_bing_results(page: str, query: str, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    blocks = re.findall(r'<li[^>]+class="[^"]*\bb_algo\b[^"]*"[^>]*>(.*?)</li>', page, re.I | re.S)
    for block in blocks:
        match = re.search(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.I | re.S)
        if not match:
            continue
        url = _canonical_url(match.group(1))
        title = _clean_text(match.group(2))
        snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.I | re.S)
        snippet = _clean_text(snippet_match.group(1)) if snippet_match else ""
        if url and title:
            results.append(_make_result(title, url, snippet, "bing", len(results) + 1, query))
        if len(results) >= limit:
            break
    return results


def parse_bing_rss(page: str, query: str, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(page)
    except ET.ParseError:
        return results
    for item in root.findall("./channel/item"):
        title = _clean_text(item.findtext("title") or "")
        url = _canonical_url(item.findtext("link") or "")
        snippet = _clean_text(item.findtext("description") or "")
        if title and url:
            results.append(_make_result(title, url, snippet, "bing", len(results) + 1, query))
        if len(results) >= limit:
            break
    return results


def parse_baidu_results(page: str, query: str, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    blocks = re.findall(
        r'(<div[^>]+(?:class="[^"]*\bresult(?:-opus)?\b[^"]*"|tpl="se_com_default")[^>]*>.*?</div>\s*</div>)',
        page,
        re.I | re.S,
    )
    for block in blocks:
        heading = re.search(r'<h3[^>]*>(.*?)</h3>', block, re.I | re.S)
        if not heading:
            continue
        anchor = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', heading.group(1), re.I | re.S)
        if not anchor:
            continue
        direct = re.search(r'\b(?:mu|data-landurl)="([^"]+)"', block, re.I)
        url = _canonical_url(direct.group(1) if direct else anchor.group(1))
        title = _clean_text(anchor.group(2))
        snippet_match = re.search(
            r'<(?:div|span)[^>]+class="[^"]*(?:c-abstract|content-right_8Zs40|cos-row)[^"]*"[^>]*>(.*?)</(?:div|span)>',
            block,
            re.I | re.S,
        )
        snippet = _clean_text(snippet_match.group(1)) if snippet_match else ""
        if url and title:
            results.append(_make_result(title, url, snippet, "baidu", len(results) + 1, query))
        if len(results) >= limit:
            break
    return results


def parse_duckduckgo_results(page: str, query: str, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    anchors = re.finditer(
        r'<a[^>]+class="[^"]*\bresult__a\b[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        page,
        re.I | re.S,
    )
    for match in anchors:
        url = _canonical_url(match.group(1))
        title = _clean_text(match.group(2))
        nearby = page[match.end():match.end() + 1800]
        snippet_match = re.search(
            r'<a[^>]+class="[^"]*\bresult__snippet\b[^"]*"[^>]*>(.*?)</a>|'
            r'<div[^>]+class="[^"]*\bresult__snippet\b[^"]*"[^>]*>(.*?)</div>',
            nearby,
            re.I | re.S,
        )
        snippet = ""
        if snippet_match:
            snippet = _clean_text(snippet_match.group(1) or snippet_match.group(2) or "")
        if url and title:
            results.append(_make_result(title, url, snippet, "duckduckgo", len(results) + 1, query))
        if len(results) >= limit:
            break
    return results


def parse_jina_results(data: Any, query: str, limit: int) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        raw_items = data.get("data") or data.get("results") or data.get("items") or []
    elif isinstance(data, list):
        raw_items = data
    else:
        raw_items = []

    results: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        url = _canonical_url(str(item.get("url") or item.get("href") or ""))
        title = _clean_text(str(item.get("title") or item.get("name") or ""))
        snippet = _clean_text(str(item.get("description") or item.get("content") or item.get("snippet") or ""))
        if title and url:
            results.append(_make_result(title, url, snippet, "jina", len(results) + 1, query))
        if len(results) >= limit:
            break
    return results


def parse_github_repositories(data: Any, query: str, limit: int) -> list[dict[str, Any]]:
    raw_items = data.get("items", []) if isinstance(data, dict) else []
    results: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        url = _canonical_url(str(item.get("html_url") or ""))
        title = _clean_text(str(item.get("full_name") or item.get("name") or ""))
        owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
        snippet = _clean_text(str(item.get("description") or ""))
        if title and url:
            results.append(_make_result(
                title,
                url,
                snippet,
                "github",
                len(results) + 1,
                query,
                result_type="代码仓库",
                author=str(owner.get("login") or "") or None,
                language=item.get("language"),
                publish_time=item.get("updated_at"),
                extra_signals={
                    "stars": item.get("stargazers_count"),
                    "forks": item.get("forks_count"),
                },
                raw_metadata={
                    "github_id": item.get("id"),
                    "github_full_name": item.get("full_name"),
                },
            ))
        if len(results) >= limit:
            break
    return results


def search_kepuchina_page(query: str, limit: int, timeout: float) -> list[dict[str, Any]]:
    """解析科普中国站内搜索页。"""
    search_url = "https://www.kepuchina.cn/search/index?" + urlencode({"search": query})
    try:
        page = _fetch_with_headers_limited(search_url, min(timeout, 8.0), 1_500_000)
    except Exception:
        return []
    anchors = list(re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.I | re.S))
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    ignored_titles = {"图文", "视频", "专题", "科普号", "全部", "下一页"}
    for match in anchors:
        href = html.unescape(match.group(1))
        if "/article/articleinfo" not in href:
            continue
        result_url = _canonical_url(urljoin("https://www.kepuchina.cn/", href))
        if not result_url or result_url in seen:
            continue
        title = _clean_text(match.group(2))
        if title in ignored_titles:
            for next_match in anchors[anchors.index(match) + 1:anchors.index(match) + 4]:
                next_href = _canonical_url(urljoin("https://www.kepuchina.cn/", html.unescape(next_match.group(1))))
                next_title = _clean_text(next_match.group(2))
                if next_href == result_url and next_title and next_title not in ignored_titles:
                    title = next_title
                    break
        if not title or title in ignored_titles:
            continue
        seen.add(result_url)
        results.append(
            _make_result(
                title,
                result_url,
                "",
                "kepuchina-site-search",
                len(results) + 1,
                query,
                result_type="网页",
                raw_metadata={"site_pack": "kepu", "direct_source": "kepuchina_search"},
            )
        )
        if len(results) >= limit:
            break
    return results


def search_kepuchina_sitemap(query: str, limit: int, timeout: float) -> list[dict[str, Any]]:
    """从科普中国 sitemap 做轻量标题兜底检索。"""
    sitemap_urls = ["https://www.kepuchina.cn/sitemap.xml"]
    query_terms = [term for term in re.split(r"\s+", query.strip()) if term]
    if not query_terms:
        return []
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    def scan_sitemap(url: str) -> None:
        if len(results) >= limit:
            return
        try:
            body = _fetch_with_headers_limited(url, min(timeout, 5.0), 2_000_000)
        except Exception:
            return
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            return
        for node in list(root):
            tag = node.tag.rsplit("}", 1)[-1]
            if tag == "sitemap":
                continue
            if tag != "url":
                continue
            loc = _canonical_url(node.findtext("{*}loc") or node.findtext("loc") or "")
            title = _clean_text(node.findtext("{*}changefreq") or node.findtext("changefreq") or "")
            haystack = f"{title} {loc}".lower()
            if not loc or loc in seen or "kepuchina.cn" not in urlparse(loc).netloc:
                continue
            if not any(term.lower() in haystack for term in query_terms):
                continue
            seen.add(loc)
            results.append(
                _make_result(
                    title or loc,
                    loc,
                    "",
                    "kepuchina-sitemap",
                    len(results) + 1,
                    query,
                    result_type="网页",
                    raw_metadata={"site_pack": "kepu", "direct_source": "kepuchina_sitemap"},
                )
            )
            if len(results) >= limit:
                break

    for sitemap_url in sitemap_urls:
        scan_sitemap(sitemap_url)
        if len(results) >= limit:
            break
    return results


def search_kepuchina(query: str, limit: int, timeout: float) -> list[dict[str, Any]]:
    results = search_kepuchina_page(query, limit, timeout)
    if len(results) >= limit:
        return results
    seen = {item["source_url"] for item in results}
    for item in search_kepuchina_sitemap(query, limit - len(results), timeout):
        if item["source_url"] not in seen:
            results.append(item)
            seen.add(item["source_url"])
    return results


def _normalize_cdstm_url(value: str) -> str:
    value = html.unescape(value or "").replace("://neo.cdstm.cn", "://www.cdstm.cn")
    url = _canonical_url(urljoin("https://www.cdstm.cn/", value))
    parsed = urlparse(url)
    if parsed.netloc == "neo.cdstm.cn":
        parsed = parsed._replace(netloc="www.cdstm.cn")
        url = parsed.geturl()
    if parsed.netloc.endswith("cdstm.cn") and parsed.scheme == "http":
        url = parsed._replace(scheme="https").geturl()
    return url


def parse_cdstm_results(raw_items: list[Any], query: str, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for block in raw_items:
        if not isinstance(block, str):
            continue
        title = ""
        url = ""
        for anchor in re.finditer(r"<a\b([^>]*)>(.*?)</a>", block, re.I | re.S):
            attrs = anchor.group(1)
            if "textTitle" not in _html_attr(attrs, "class").split():
                continue
            url = _normalize_cdstm_url(_html_attr(attrs, "href"))
            title = _clean_text(_html_attr(attrs, "data-title") or anchor.group(2))
            break
        if not title or not url or url in seen:
            continue
        seen.add(url)
        snippet_match = re.search(
            r'<div[^>]+class="[^"]*\bnewsDescribe\b[^"]*"[^>]*>(.*?)</div>',
            block,
            re.I | re.S,
        )
        snippet = _clean_text(snippet_match.group(1)) if snippet_match else ""
        date_match = re.search(r"时间\s*[:：]\s*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})", block)
        thumb_match = re.search(r'<div[^>]+class="[^"]*\bfirstpic\b[^"]*"[^>]*>.*?<img[^>]+src="([^"]*)"', block, re.I | re.S)
        item = _make_result(
            title,
            url,
            snippet,
            "cdstm-jsearch",
            len(results) + 1,
            query,
            result_type="网页",
            publish_time=date_match.group(1) if date_match else None,
            raw_metadata={"site_pack": "kepu", "direct_source": "cdstm_jsearch"},
        )
        if thumb_match and thumb_match.group(1).strip():
            item["thumbnail_url"] = _normalize_cdstm_url(thumb_match.group(1))
        results.append(item)
        if len(results) >= limit:
            break
    return results


def _cdstm_category_ids(timeout: float) -> list[str]:
    referer = CDSTM_SEARCH_BASE + "search?" + urlencode({"serviceId": CDSTM_SERVICE_ID, "q": ""})
    headers = {"Referer": referer, "X-Requested-With": "XMLHttpRequest"}
    url = CDSTM_SEARCH_BASE + "interface/structure/list-category?" + urlencode({"serviceId": CDSTM_SERVICE_ID})
    try:
        data = _fetch_json(url, min(timeout, 8.0), headers)
    except Exception:
        return [CDSTM_DEFAULT_CATE_ID]
    categories = ((data.get("data") or {}).get("categories") or []) if isinstance(data, dict) else []
    ids: list[str] = []
    for item in categories:
        if not isinstance(item, dict):
            continue
        category_id = str(item.get("iid") or "").strip()
        if not category_id:
            continue
        if str(item.get("categoryName") or "") == "全部":
            ids.insert(0, category_id)
        else:
            ids.append(category_id)
    return list(dict.fromkeys(ids))[:3] or [CDSTM_DEFAULT_CATE_ID]


def search_cdstm(query: str, limit: int, timeout: float) -> list[dict[str, Any]]:
    referer = CDSTM_SEARCH_BASE + "search?" + urlencode({"serviceId": CDSTM_SERVICE_ID, "q": query})
    headers = {"Referer": referer, "X-Requested-With": "XMLHttpRequest"}
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cate_id in _cdstm_category_ids(timeout):
        params = {
            "websiteid": "",
            "cateid": cate_id,
            "serviceId": CDSTM_SERVICE_ID,
            "q": query,
            "p": "1",
            "pg": str(max(10, min(limit, 50))),
            "pos": "title,content,filenumber",
            "sortType": "1",
        }
        data = _fetch_json(CDSTM_SEARCH_BASE + "interface/search/info?" + urlencode(params), min(timeout, 10.0), headers)
        search_result = ((data.get("data") or {}).get("searchResult") or {}) if isinstance(data, dict) else {}
        for item in parse_cdstm_results(search_result.get("result") or [], query, limit - len(results)):
            if item["source_url"] in seen:
                continue
            results.append(item)
            seen.add(item["source_url"])
            if len(results) >= limit:
                return results
    return results


def _unwrap_cctv_url(value: str) -> str:
    url = _canonical_url(urljoin("https://search.cctv.com/", html.unescape(value or "")))
    parsed = urlparse(url)
    if parsed.netloc == "search.cctv.com" and parsed.path.endswith("/link_p.php"):
        target = parse_qs(parsed.query).get("targetpage", [""])[0]
        decoded = unquote(target)
        if decoded.startswith(("http://", "https://")):
            url = _canonical_url(decoded)
            parsed = urlparse(url)
    if parsed.netloc == "search.cctv.com":
        return ""
    if parsed.netloc.endswith(("cctv.com", "cntv.cn", "yangshipin.cn")) and parsed.scheme == "http":
        url = parsed._replace(scheme="https").geturl()
    return url


def parse_cctv_results(page: str, query: str, limit: int, search_type: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for anchor in re.finditer(r"<a\b([^>]*)>(.*?)</a>", page, re.I | re.S):
        attrs = anchor.group(1)
        href = _html_attr(attrs, "href")
        if not href or href.startswith(("javascript:", "#")):
            continue
        url = _unwrap_cctv_url(href)
        if not url or url in seen:
            continue
        title = _clean_text(_html_attr(attrs, "title") or anchor.group(2))
        if not title or title in {"查看详情》", "官网链接》"}:
            continue
        seen.add(url)
        thumb_match = re.search(r'<img\b[^>]+src="([^"]+)"', anchor.group(2), re.I | re.S)
        item = _make_result(
            title,
            url,
            "",
            f"cctv-search-{search_type}",
            len(results) + 1,
            query,
            result_type="视频" if search_type == "video" else "网页",
            raw_metadata={"site_pack": "cctv", "direct_source": f"cctv_search_{search_type}"},
        )
        if thumb_match:
            item["thumbnail_url"] = _canonical_url(urljoin("https://search.cctv.com/", thumb_match.group(1)))
        results.append(item)
        if len(results) >= limit:
            break
    return results


def search_cctv(query: str, limit: int, timeout: float) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for search_type in ("video", "web"):
        if len(results) >= limit:
            break
        url = CCTV_SEARCH_BASE + "?" + urlencode({"qtext": query, "type": search_type})
        page = _fetch_with_headers_limited(url, min(timeout, 10.0), 2_000_000)
        for item in parse_cctv_results(page, query, limit - len(results), search_type):
            if item["source_url"] in seen:
                continue
            results.append(item)
            seen.add(item["source_url"])
            if len(results) >= limit:
                break
    return results


def _fetch_with_headers(url: str, timeout: float, headers: dict[str, str] | None = None) -> str:
    merged = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    }
    merged.update(headers or {})
    request = Request(url, headers=merged)
    try:
        response = urlopen(request, timeout=timeout)
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        if not isinstance(reason, ssl.SSLCertVerificationError) and "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        response = urlopen(request, timeout=timeout, context=ssl._create_unverified_context())
    with response:
        body = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    return body.decode(charset, errors="replace")


def _fetch_with_headers_limited(url: str, timeout: float, max_bytes: int, headers: dict[str, str] | None = None) -> str:
    merged = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    }
    merged.update(headers or {})
    request = Request(url, headers=merged)
    try:
        response = urlopen(request, timeout=timeout)
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        if not isinstance(reason, ssl.SSLCertVerificationError) and "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        response = urlopen(request, timeout=timeout, context=ssl._create_unverified_context())
    with response:
        body = response.read(max_bytes)
        charset = response.headers.get_content_charset() or "utf-8"
    return body.decode(charset, errors="replace")


def _fetch_json(url: str, timeout: float, headers: dict[str, str] | None = None) -> Any:
    return json.loads(_fetch_with_headers(url, timeout, headers))


def _fetch(url: str, timeout: float, cookie: str = "") -> str:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6"}
    if cookie:
        headers["Cookie"] = cookie
    request = Request(url, headers=headers)
    try:
        response = urlopen(request, timeout=timeout)
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        if not isinstance(reason, ssl.SSLCertVerificationError) and "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        # Some Windows Python builds have an incomplete CA store for public
        # search pages. Retry only for certificate verification failures.
        response = urlopen(request, timeout=timeout, context=ssl._create_unverified_context())
    with response:
        body = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    return body.decode(charset, errors="replace")


def _raise_if_blocked(page: str, engine: str) -> None:
    lowered = page.lower()
    markers = {
        "baidu": ("百度安全验证", "网络不给力，请稍后重试", "wappass.baidu.com/static/captcha"),
        "bing": ('class="captcha"', "our systems have detected unusual traffic", "verify you are human"),
        "duckduckgo": ("anomaly", "captcha", "verify you are human"),
    }
    if any(marker.lower() in lowered for marker in markers.get(engine, ())):
        raise SearchBlockedError(f"{engine} 返回安全验证页面")


def expand_engines(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        token = value.strip().lower()
        if not token:
            continue
        output.extend(ENGINE_PRESETS.get(token, [token]))
    return list(dict.fromkeys(output))


def _engine_error(engine: str, exc: Exception) -> dict[str, Any]:
    message = f"{type(exc).__name__}: {exc}"
    retryable = False
    code = "SEARCH_EXECUTION_FAILED"
    if isinstance(exc, SearchBlockedError):
        code = "SEARCH_BLOCKED"
        retryable = True
    elif isinstance(exc, TimeoutError):
        code = "NETWORK_TIMEOUT"
        retryable = True
    elif isinstance(exc, HTTPError):
        if exc.code == 401:
            code = "AUTH_REQUIRED"
        elif exc.code in {403, 429}:
            code = "SEARCH_RATE_LIMITED"
            retryable = True
        elif 500 <= exc.code < 600:
            code = "NETWORK_HTTP_ERROR"
            retryable = True
    elif isinstance(exc, URLError):
        code = "NETWORK_ERROR"
        retryable = True
    return {"engine": engine, "error_code": code, "message": message, "retryable": retryable}


def _with_site_filter(query: str, site: str | None) -> str:
    site = (site or "").strip()
    if not site:
        return query
    return f"{query} site:{site}"


def expand_site_filters(site: str | None = None, site_pack: str | None = None) -> list[str | None]:
    output: list[str | None] = []
    for value in (site or "").split(","):
        value = value.strip()
        if value:
            output.append(value)
    for value in (site_pack or "").split(","):
        key = value.strip().lower()
        if not key:
            continue
        output.extend(SITE_PACKS.get(key, [key]))
    unique = list(dict.fromkeys(output))
    return unique or [None]


def _url_matches_site_filter(url: str, site: str | None) -> bool:
    site = (site or "").strip().lower()
    if not site:
        return True
    host = urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
    return host == site or host.endswith("." + site)


def _filter_results_by_site(items: list[dict[str, Any]], site: str | None) -> list[dict[str, Any]]:
    return [item for item in items if _url_matches_site_filter(str(item.get("source_url") or ""), site)]


def search(
    query: str,
    engines: list[str],
    limit: int,
    timeout: float,
    *,
    site: str | None = None,
    site_pack: str | None = None,
    github_sort: str | None = None,
    github_order: str = "desc",
) -> dict[str, Any]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    errors: list[dict[str, Any]] = []
    site_filters = expand_site_filters(site, site_pack)
    per_engine_limit = max(limit, 1)
    per_site_limit = max(3, min(per_engine_limit, (per_engine_limit + len(site_filters) - 1) // len(site_filters) + 2))

    def run_engine(engine: str) -> tuple[str, list[dict[str, Any]]]:
        engine_queries = [_with_site_filter(query, item) for item in site_filters] if engine != "github" else [query]
        engine_results: list[dict[str, Any]] = []
        if engine == "bing":
            cookie = os.environ.get("BING_COOKIE", "") or "SRCHHPGUSR=SRCHLANG=zh-Hans"
            html_blocked = False
            for engine_query, site_filter in zip(engine_queries, site_filters):
                html_url = (
                    f"https://cn.bing.com/search?q={quote_plus(engine_query)}"
                    f"&count={per_site_limit}&setlang=zh-hans&cc=CN"
                )
                try:
                    page = _fetch(html_url, timeout, cookie)
                    _raise_if_blocked(page, engine)
                    html_results = parse_bing_results(page, engine_query, per_site_limit)
                    if html_results:
                        engine_results.extend(_filter_results_by_site(html_results, site_filter))
                        continue
                except SearchBlockedError:
                    html_blocked = True
                rss_url = f"https://cn.bing.com/search?format=rss&q={quote_plus(engine_query)}&count={per_site_limit}"
                rss_page = _fetch(rss_url, timeout, cookie)
                _raise_if_blocked(rss_page, engine)
                engine_results.extend(_filter_results_by_site(parse_bing_rss(rss_page, engine_query, per_site_limit), site_filter))
            if html_blocked and not engine_results:
                raise SearchBlockedError("bing HTML 与 RSS 搜索均不可用")
            return engine, engine_results[:per_engine_limit]
        if engine == "baidu":
            for engine_query, site_filter in zip(engine_queries, site_filters):
                url = f"https://www.baidu.com/s?wd={quote_plus(engine_query)}&rn={per_site_limit}"
                page = _fetch(url, timeout, os.environ.get("BAIDU_COOKIE", ""))
                _raise_if_blocked(page, engine)
                engine_results.extend(_filter_results_by_site(parse_baidu_results(page, engine_query, per_site_limit), site_filter))
            return engine, engine_results[:per_engine_limit]
        if engine == "duckduckgo":
            for engine_query, site_filter in zip(engine_queries, site_filters):
                url = f"https://html.duckduckgo.com/html/?q={quote_plus(engine_query)}"
                page = _fetch(url, timeout, os.environ.get("DUCKDUCKGO_COOKIE", ""))
                _raise_if_blocked(page, engine)
                engine_results.extend(_filter_results_by_site(parse_duckduckgo_results(page, engine_query, per_site_limit), site_filter))
            return engine, engine_results[:per_engine_limit]
        if engine == "jina":
            headers = {"Accept": "application/json", "X-Respond-With": "no-content"}
            api_key = os.environ.get("JINA_API_KEY", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            for engine_query, site_filter in zip(engine_queries, site_filters):
                data = _fetch_json(f"https://s.jina.ai/?q={quote_plus(engine_query)}", timeout, headers)
                engine_results.extend(_filter_results_by_site(parse_jina_results(data, engine_query, per_site_limit), site_filter))
            return engine, engine_results[:per_engine_limit]
        if engine == "github":
            params = {
                "q": query,
                "per_page": min(per_engine_limit, 100),
                "order": github_order if github_order in {"asc", "desc"} else "desc",
            }
            if github_sort:
                params["sort"] = github_sort
            headers = {"Accept": "application/vnd.github+json", "User-Agent": "platform-search/1.0"}
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            if token:
                headers["Authorization"] = f"Bearer {token}"
                headers["X-GitHub-Api-Version"] = "2022-11-28"
            data = _fetch_json(f"https://api.github.com/search/repositories?{urlencode(params)}", timeout, headers)
            return engine, parse_github_repositories(data, query, per_engine_limit)
        raise ValueError(f"未知搜索引擎: {engine}")

    completed: dict[str, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=len(engines)) as executor:
        futures = {executor.submit(run_engine, engine): engine for engine in engines}
        for future in as_completed(futures):
            engine = futures[future]
            try:
                _, engine_results = future.result()
                completed[engine] = engine_results
            except Exception as exc:  # Engine failures are isolated.
                errors.append(_engine_error(engine, exc))

    direct_sources: list[str] = []
    site_pack_tokens = {part.strip().lower() for part in (site_pack or "").split(",") if part.strip()}
    if "kepu" in site_pack_tokens:
        direct_results: list[dict[str, Any]] = []
        per_direct_limit = max(3, min(per_engine_limit, (per_engine_limit + 1) // 2))
        for direct_engine, direct_search in (
            ("kepuchina-direct", search_kepuchina),
            ("cdstm-jsearch", search_cdstm),
        ):
            try:
                direct_results.extend(direct_search(query, per_direct_limit, timeout))
            except Exception as exc:
                errors.append(_engine_error(direct_engine, exc))
        if direct_results:
            completed["kepu-direct"] = direct_results
            direct_sources.append("kepu-direct")
    if "cctv" in site_pack_tokens:
        try:
            direct_results = search_cctv(query, per_engine_limit, timeout)
        except Exception as exc:
            errors.append(_engine_error("cctv-search", exc))
            direct_results = []
        if direct_results:
            completed["cctv-direct"] = direct_results
            direct_sources.append("cctv-direct")

    # Merge in the requested engine order so concurrency does not make output unstable.
    for engine in direct_sources + engines:
        engine_results = completed.get(engine, [])
        for item in engine_results:
            canonical = _canonical_url(item["source_url"])
            if not canonical or canonical in seen:
                continue
            seen.add(canonical)
            item["source_url"] = canonical
            if len(merged) < limit:
                merged.append(item)
    return {
        "platform": "generic",
        "query": query,
        "search_method": "+".join(direct_sources + engines),
        "site_filters": [item for item in site_filters if item],
        "total_found": len(merged),
        "returned_count": len(merged),
        "results": merged,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="使用多搜索引擎搜索公开网页和开放资源")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("search")
    command.add_argument("query")
    command.add_argument("--max", type=int, default=20, dest="max_results")
    command.add_argument("--engines", default="web", help="逗号分隔搜索引擎或预设: web,global,china,dev,all")
    command.add_argument("--site", help="限定站点，例如 edu.cn、github.com")
    command.add_argument("--site-pack", help=f"站点包，逗号分隔；可选: {','.join(sorted(SITE_PACKS))}")
    command.add_argument("--github-sort", choices=["stars", "forks", "help-wanted-issues", "updated"])
    command.add_argument("--github-order", choices=["asc", "desc"], default="desc")
    command.add_argument("--timeout", type=float, default=10.0)
    command.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    engines = expand_engines([part for part in args.engines.split(",") if part.strip()])
    unknown = set(engines) - ALLOWED_ENGINES
    if unknown or not engines:
        allowed = sorted(ALLOWED_ENGINES | set(ENGINE_PRESETS))
        parser.error(f"--engines 只支持 {','.join(allowed)}，收到: {sorted(unknown) or engines}")
    result = search(
        args.query,
        engines,
        max(1, min(args.max_results, 100)),
        max(1.0, args.timeout),
        site=args.site,
        site_pack=args.site_pack,
        github_sort=args.github_sort,
        github_order=args.github_order,
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
