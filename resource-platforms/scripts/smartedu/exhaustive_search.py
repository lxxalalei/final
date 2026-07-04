#!/usr/bin/env python3
"""SmartEdu 搜索执行层。

CLI 传入 argparse 风格的参数对象，本模块负责 payload 构造、分页和深度搜索扩展，
让平台适配器复用同一套搜索行为，而不需要理解 CLI 文件里的命令组织。
"""

from __future__ import annotations

import os
import re
from typing import Any

from _auth_http import parse_extra_headers, request_json
from _constants import DEFAULT_TAB_CODES, SEARCH_URLS
from _search import extract_search_items, grade_to_chinese
from _text_utils import first_value, norm


SEARCH_API_MAX_LIMIT = 100
SEARCH_PAGE_SIZE = 100
SEARCH_MAX_OFFSET = 200
DEEP_SEARCH_GRADES = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级", "七年级", "八年级", "九年级"]
DEEP_SEARCH_STAGES = ["小学", "初中", "高中"]
GRADE_TO_STAGE = {
    "一年级": "小学",
    "二年级": "小学",
    "三年级": "小学",
    "四年级": "小学",
    "五年级": "小学",
    "六年级": "小学",
    "七年级": "初中",
    "八年级": "初中",
    "九年级": "初中",
    "高一": "高中",
    "高二": "高中",
    "高三": "高中",
}


def parse_tab_codes(values: list[str] | None) -> list[str]:
    tab_codes: list[str] = []
    for value in values or []:
        for part in value.split(","):
            part = part.strip()
            if part and part not in tab_codes:
                tab_codes.append(part)
    return tab_codes or DEFAULT_TAB_CODES


def expanded_search_limit(limit: int) -> int:
    """返回安全的单次请求 limit，为本地过滤预留余量。"""
    if limit <= 0:
        return 50
    return min(max(limit * 5, limit + 20), SEARCH_API_MAX_LIMIT)


def grades_from_query(query: str) -> list[str]:
    """从自然语言关键词里识别明确年级，用于限制深搜扩展范围。"""
    text = norm(query)
    if not text:
        return []
    found: list[str] = []
    aliases = {
        "一": "一年级",
        "二": "二年级",
        "三": "三年级",
        "四": "四年级",
        "五": "五年级",
        "六": "六年级",
        "七": "七年级",
        "八": "八年级",
        "九": "九年级",
        "1": "一年级",
        "2": "二年级",
        "3": "三年级",
        "4": "四年级",
        "5": "五年级",
        "6": "六年级",
        "7": "七年级",
        "8": "八年级",
        "9": "九年级",
    }
    for key, grade in aliases.items():
        patterns = [rf"{re.escape(key)}\s*年级"]
        if key in {"一", "二", "三", "四", "五", "六"}:
            patterns.append(rf"小\s*{re.escape(key)}")
        if key in {"七", "八", "九"}:
            patterns.append(rf"初\s*{re.escape(key)}")
        if any(re.search(pattern, text) for pattern in patterns) and grade not in found:
            found.append(grade)
    for grade in ["高一", "高二", "高三"]:
        if grade in text and grade not in found:
            found.append(grade)
    return found


def search_payload(args: Any, filters: dict[str, Any]) -> dict[str, Any]:
    query = args.query or norm(filters.get("query") or filters.get("core_topic") or filters.get("subject"))
    tag_dimension_map = {
        "version": "tag.zxxbb",
        "grade": "tag.zxxnj",
        "volume": "tag.zxxcc",
        "subject": "tag.zxxxk",
        "stage": "tag.zxxxd",
    }
    combine_resources: list[dict[str, str]] = []
    for field, tag_field in tag_dimension_map.items():
        value = norm(filters.get(field))
        if value:
            combine_resources.append({"field": tag_field, "value": grade_to_chinese(value)})
    return {
        "identity": args.identity,
        "identity_code": args.identity_code,
        "keyword": query,
        "tab_codes": parse_tab_codes(args.tab_code),
        "cross_tenant": args.cross_tenant,
        "duplicate_filter": True,
        "search_order": {"field": args.order_field, "direction": args.order_direction},
        "offset": args.offset,
        "limit": args.limit,
        "combine_intentions": [],
        "combine_resources": combine_resources,
    }


def make_search_request(
    base_payload: dict[str, Any],
    *,
    keyword: str,
    tab_codes: list[str],
    offset: int,
    limit: int,
    combine_resources: list[dict[str, str]],
    access_token: str | None,
    cookie: str | None,
    extra_headers: dict[str, str],
    search_url: str | None = None,
) -> Any:
    payload = dict(base_payload)
    payload["keyword"] = keyword
    payload["tab_codes"] = tab_codes
    payload["offset"] = offset
    payload["limit"] = limit
    payload["combine_resources"] = combine_resources
    urls = [search_url] if search_url else list(SEARCH_URLS)
    errors: list[str] = []
    for url in urls:
        try:
            return request_json(url, access_token=access_token, payload=payload, cookie=cookie, extra_headers=extra_headers)
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("; ".join(errors))


def search_all_pages(
    base_payload: dict[str, Any],
    *,
    keyword: str,
    tab_codes: list[str],
    combine_resources: list[dict[str, str]],
    max_results: int,
    access_token: str | None,
    cookie: str | None,
    extra_headers: dict[str, str],
    search_url: str | None = None,
) -> tuple[list[Any], list[dict[str, Any]]]:
    all_raw_items: list[Any] = []
    page_stats: list[dict[str, Any]] = []
    for page_offset in range(0, SEARCH_MAX_OFFSET, SEARCH_PAGE_SIZE):
        remaining = max_results - len(all_raw_items)
        if remaining <= 0:
            break
        page_limit = min(SEARCH_PAGE_SIZE, remaining)
        try:
            data = make_search_request(
                base_payload,
                keyword=keyword,
                tab_codes=tab_codes,
                offset=page_offset,
                limit=page_limit,
                combine_resources=combine_resources,
                access_token=access_token,
                cookie=cookie,
                extra_headers=extra_headers,
                search_url=search_url,
            )
        except Exception:
            break
        page_items = extract_search_items(data, page_limit)
        if not page_items:
            break
        all_raw_items.extend(page_items)
        page_stats.append({"offset": page_offset, "limit": page_limit, "items": len(page_items)})
        if len(page_items) < page_limit:
            break
    return all_raw_items, page_stats


def fetch_search_results(args: Any, filters: dict[str, Any]) -> Any:
    extra_headers = parse_extra_headers(args.header)
    access_token = args.access_token or os.environ.get("SMARTEDU_ACCESS_TOKEN")
    payload = search_payload(args, filters)
    tag_filters = payload.get("combine_resources", [])
    if args.search_url:
        return request_json(args.search_url, access_token=access_token, payload=payload, cookie=args.cookie, extra_headers=extra_headers)
    errors: list[str] = []
    for url in SEARCH_URLS:
        try:
            data = request_json(url, access_token=access_token, payload=payload, cookie=args.cookie, extra_headers=extra_headers)
            items = extract_search_items(data, args.limit)
            if items or not tag_filters:
                return data
            break
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    payload_no_filter = dict(payload)
    payload_no_filter["combine_resources"] = []
    for url in SEARCH_URLS:
        try:
            return request_json(url, access_token=access_token, payload=payload_no_filter, cookie=args.cookie, extra_headers=extra_headers)
        except Exception as exc:
            errors.append(f"{url}(no-filter): {exc}")
    raise RuntimeError("; ".join(errors))


def deep_search(args: Any, filters: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
    """先分页搜索；结果触顶时再按年级、学段和 tab 拆分补搜。"""
    extra_headers = parse_extra_headers(args.header)
    access_token = args.access_token or os.environ.get("SMARTEDU_ACCESS_TOKEN")
    base_payload = {
        "identity": args.identity,
        "identity_code": args.identity_code,
        "cross_tenant": args.cross_tenant,
        "duplicate_filter": True,
        "search_order": {"field": args.order_field, "direction": args.order_direction},
        "combine_intentions": [],
    }
    tab_codes = parse_tab_codes(args.tab_code)
    query = args.query or norm(filters.get("query") or filters.get("core_topic") or filters.get("subject"))

    tag_dimension_map = {
        "version": "tag.zxxbb",
        "grade": "tag.zxxnj",
        "volume": "tag.zxxcc",
        "subject": "tag.zxxxk",
        "stage": "tag.zxxxd",
    }
    base_combine_resources: list[dict[str, str]] = []
    for field, tag_field in tag_dimension_map.items():
        value = norm(filters.get(field))
        if value:
            base_combine_resources.append({"field": tag_field, "value": grade_to_chinese(value)})

    max_results = getattr(args, "max_results", 5000)
    no_deep = bool(getattr(args, "no_deep_search", False))
    seen_ids: set[str] = set()
    deduped: list[Any] = []
    search_log: list[dict[str, Any]] = []

    def absorb(raw_items: list[Any], source_desc: str) -> None:
        added = 0
        for item in raw_items:
            key = norm(first_value(item, ["id", "resource_id", "resourceId", "content_id", "contentId", "course_id", "courseId"]))
            title = norm(first_value(item, ["title", "name", "content_name", "contentName", "resource_name", "resourceName", "global_title"]))
            fp = f"{key}:{title}"
            if fp in seen_ids:
                continue
            seen_ids.add(fp)
            deduped.append(item)
            added += 1
            if len(deduped) >= max_results:
                break
        search_log.append({"source": source_desc, "fetched": len(raw_items), "added": added, "total": len(deduped)})

    phase1_items, phase1_pages = search_all_pages(
        base_payload,
        keyword=query,
        tab_codes=tab_codes,
        combine_resources=base_combine_resources,
        max_results=max_results,
        access_token=access_token,
        cookie=args.cookie,
        extra_headers=extra_headers,
        search_url=args.search_url,
    )
    absorb(phase1_items, f"phase1: query='{query}' tabs={tab_codes[:3]}...")

    query_grades = grades_from_query(query)
    filter_grade = grade_to_chinese(norm(filters.get("grade"))) if norm(filters.get("grade")) else ""
    explicit_grades = [filter_grade] if filter_grade else query_grades

    if len(deduped) >= 180 and not no_deep:
        stage = norm(filters.get("stage"))
        if explicit_grades:
            cross_grades = explicit_grades
        elif stage == "小学":
            cross_grades = DEEP_SEARCH_GRADES[:6]
        elif stage == "初中":
            cross_grades = DEEP_SEARCH_GRADES[6:9]
        elif stage == "高中":
            cross_grades = ["高一", "高二", "高三"]
        else:
            cross_grades = DEEP_SEARCH_GRADES + ["高一", "高二", "高三"]

        for grade in cross_grades:
            if len(deduped) >= max_results:
                break
            grade_query = f"{grade} {query}"
            grade_resources = [row for row in base_combine_resources if row["field"] != "tag.zxxnj"]
            grade_resources.append({"field": "tag.zxxnj", "value": grade})
            phase2_items, _ = search_all_pages(
                base_payload,
                keyword=grade_query,
                tab_codes=tab_codes,
                combine_resources=grade_resources,
                max_results=max_results - len(deduped),
                access_token=access_token,
                cookie=args.cookie,
                extra_headers=extra_headers,
                search_url=args.search_url,
            )
            absorb(phase2_items, f"phase2: query='{grade_query}' grade={grade}")

    if len(deduped) >= 180 and not no_deep:
        deep_tab_limit = int(getattr(args, "deep_tab_limit", 6) or 0)
        phase3_tabs = tab_codes if deep_tab_limit <= 0 else tab_codes[:deep_tab_limit]
        if explicit_grades:
            phase3_stages = [GRADE_TO_STAGE[grade] for grade in explicit_grades if grade in GRADE_TO_STAGE]
            phase3_stages = list(dict.fromkeys(phase3_stages)) or DEEP_SEARCH_STAGES
        elif norm(filters.get("stage")) in DEEP_SEARCH_STAGES:
            phase3_stages = [norm(filters.get("stage"))]
        else:
            phase3_stages = DEEP_SEARCH_STAGES
        for stage in phase3_stages:
            if len(deduped) >= max_results:
                break
            stage_query = f"{stage} {query}"
            for tab in phase3_tabs:
                if len(deduped) >= max_results:
                    break
                phase3_items, _ = search_all_pages(
                    base_payload,
                    keyword=stage_query,
                    tab_codes=[tab],
                    combine_resources=base_combine_resources,
                    max_results=max_results - len(deduped),
                    access_token=access_token,
                    cookie=args.cookie,
                    extra_headers=extra_headers,
                    search_url=args.search_url,
                )
                absorb(phase3_items, f"phase3: query='{stage_query}' tab={tab}")

    stats = {
        "enabled": not no_deep,
        "total_unique": len(deduped),
        "phases": search_log,
        "phase1_pages": phase1_pages,
        "max_results": max_results,
        "saturated": len(phase1_items) >= SEARCH_MAX_OFFSET,
    }
    return deduped, stats
