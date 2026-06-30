#!/usr/bin/env python3
"""喜马拉雅搜索脚本 — 调用官方 revision/search API，输出标准搜索结果 JSON。

搜索接口公开，无需登录/Cookie/签名。
支持搜索 album（专辑）和 track（声音）两种类型，统一输出为「音频」资源。

输出格式遵循 platform-search-contract.md 的 results 规范。

用法:
  python ximalaya_search.py search "小学必背古诗" --max 20 -o candidates.json
  python ximalaya_search.py search "儿歌 童谣" --core track --max 15
  python ximalaya_search.py search "英语启蒙" --free-only --max 20

依赖:
  - 标准库 urllib，无需第三方包
  - 无需浏览器，无需登录
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.logger import getLogger

log = getLogger("ximalaya")

# ========== 配置 ==========

SEARCH_API = "https://www.ximalaya.com/revision/search"
ALBUM_URL_PREFIX = "https://www.ximalaya.com/album/"
TRACK_URL_PREFIX = "https://www.ximalaya.com/sound/"
COVER_CDN = "https:"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# 分类映射（category_id → 中文）
CATEGORY_MAP = {
    "17": "儿歌", "11": "睡前故事", "28": "国学", "12": "童话",
    "21": "英语", "3": "有声书", "10": "教育培训", "14": "情感生活",
    "2": "通俗小说", "13": "历史", "1006": "生活", "1005": "其他",
}

CHILD_CATEGORY_KEYWORDS = {
    "儿歌": ["儿歌", "童谣", "宝宝", "幼儿"],
    "睡前故事": ["睡前", "故事", "童话"],
    "国学": ["国学", "古诗", "诗词", "三字经", "弟子规", "论语"],
    "英语": ["英语", "英文", "启蒙"],
    "科普": ["科普", "十万个为什么", "百科", "知识"],
    "语文": ["语文", "拼音", "识字", "阅读"],
    "数学": ["数学", "算术", "思维"],
}
# ==========================


def _build_headers() -> dict[str, str]:
    """构建请求头。喜马拉雅搜索接口公开，无需认证。"""
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://www.ximalaya.com/",
    }


def search(
    keyword: str,
    core: str = "album",
    max_results: int = 20,
    free_only: bool = False,
    sort_by: str = "relevance",
) -> list[dict[str, Any]]:
    """调用喜马拉雅搜索 API，返回标准结果列表。

    Args:
        keyword: 搜索关键词
        core: 搜索类型 album（专辑）/ track（声音）
        max_results: 最大返回数
        free_only: 是否只返回免费内容
        sort_by: 排序方式 relevance/popularity/newest
    """
    log.info("喜马拉雅搜索: kw='%s' core=%s max=%d", keyword, core, max_results)

    headers = _build_headers()
    condition_map = {"relevance": "relation", "popularity": "play", "newest": "time"}
    condition = condition_map.get(sort_by, "relation")

    candidates: list[dict[str, Any]] = []
    page = 1
    rows = min(max_results, 20)

    while len(candidates) < max_results:
        params: dict[str, str] = {
            "core": core,
            "kw": keyword,
            "page": str(page),
            "rows": str(rows),
            "condition": condition,
            "device": "web",
            "spellchecker": "true",
        }
        if free_only:
            params["fq"] = "is_paid:false,"

        url = f"{SEARCH_API}?{urllib.parse.urlencode(params)}"
        log.info("搜索 API 调用: core=%s page=%d", core, page)

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    log.warning("搜索 API 返回 HTTP %d", resp.status)
                    break
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            log.error("搜索 API 请求失败: %s", exc)
            break

        ret = data.get("ret")
        if ret != 200:
            log.warning("搜索 API 错误码 ret=%s, msg=%s", ret, data.get("msg"))
            break

        try:
            response = data["data"]["result"]["response"]
            docs = response.get("docs") or []
            total_page = response.get("totalPage", 0)
        except (KeyError, TypeError):
            log.error("搜索 API 响应结构异常")
            break

        if not docs:
            log.info("搜索 API 无更多结果")
            break

        for doc in docs:
            cand = _parse_doc(doc, core)
            if cand:
                candidates.append(cand)
                if len(candidates) >= max_results:
                    break

        if page >= total_page:
            break
        page += 1
        time.sleep(0.5)

    log.info("搜索返回 %d 条结果", len(candidates))
    return candidates[:max_results]


def _parse_doc(doc: dict[str, Any], core: str) -> dict[str, Any] | None:
    """解析单条 API 结果为标准搜索结果。"""
    resource_id = str(doc.get("id") or "")
    if not resource_id:
        return None

    title = _clean_html(doc.get("title") or doc.get("richTitle") or "无标题")

    # URL 构建
    raw_url = doc.get("url") or ""
    url_prefix = TRACK_URL_PREFIX if core == "track" else ALBUM_URL_PREFIX
    if raw_url:
        source_url = _normalize_url(raw_url)
    else:
        source_url = f"{url_prefix}{resource_id}"

    # 简介
    intro = _clean_html(doc.get("intro") or doc.get("custom_title") or "").strip()[:300]

    # 分类
    category_title = doc.get("category_title") or ""
    category_id = str(doc.get("category_id") or "")
    subject = _infer_subject(title, intro, category_title, category_id)

    # 付费状态
    is_paid = doc.get("is_paid", False)
    is_vip_free = doc.get("isVipFree", False)

    # 播放量
    play_count = doc.get("play")
    if isinstance(play_count, str):
        try:
            play_count = int(play_count)
        except ValueError:
            play_count = None

    # 评分
    score = doc.get("score")

    # 主播
    nickname = doc.get("nickname") or ""
    is_verified = doc.get("is_v", False)

    # 封面
    cover_path = doc.get("cover_path") or ""
    if cover_path and not cover_path.startswith("http"):
        cover_path = COVER_CDN + cover_path

    # 完结状态
    is_finished = doc.get("is_finished")
    tracks_count = doc.get("tracks") or 0

    # 标签
    tags_str = doc.get("tags") or ""
    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

    # 质量评分
    quality_score, quality_level = _estimate_quality(
        play_count, score, is_verified, is_paid, tracks_count,
    )

    return {
        "resource_id": f"ximalaya:{resource_id}",
        "title": title,
        "type": "音频",
        "platform": "ximalaya",
        "source_url": source_url,
        "source_name": "喜马拉雅",
        "quality_level": quality_level,
        "platform_quality_score": quality_score,
        "download_feasibility": _estimate_feasibility(is_paid, is_vip_free),
        "description": intro,
        "subject": subject,
        "provider": nickname,
        "tags": tags,
        "view_count": play_count,
        "is_free": not is_paid,
        "language": "中文",
    }


def _estimate_quality(
    play_count: int | None,
    score: float | None,
    is_verified: bool,
    is_paid: bool,
    tracks_count: int,
) -> tuple[int, str]:
    """估算平台质量分（0-100）和等级（S/A/B/C）。"""
    q = 60

    if play_count:
        if play_count > 10_000_000:
            q += 18
        elif play_count > 1_000_000:
            q += 14
        elif play_count > 100_000:
            q += 10
        elif play_count > 10_000:
            q += 6

    if score and isinstance(score, (int, float)):
        if score >= 9.5:
            q += 10
        elif score >= 9.0:
            q += 8
        elif score >= 8.0:
            q += 5

    if is_verified:
        q += 6

    if tracks_count:
        if tracks_count >= 50:
            q += 6
        elif tracks_count >= 20:
            q += 4
        elif tracks_count >= 5:
            q += 2

    if not is_paid:
        q += 4

    q = max(0, min(100, q))

    if q >= 90:
        level = "S"
    elif q >= 75:
        level = "A"
    elif q >= 60:
        level = "B"
    else:
        level = "C"

    return q, level


def _estimate_feasibility(is_paid: bool, is_vip_free: bool) -> str:
    """估算下载可行性：高/中/低。"""
    if is_paid and not is_vip_free:
        return "低"
    return "中"


def _clean_html(text: str) -> str:
    """清理 HTML 标签。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("&ensp;", " ").replace("&amp;", "&").replace("&nbsp;", " ").strip()


def _normalize_url(raw_url: str) -> str:
    """将喜马拉雅内部 URL 规范化为标准 https 链接。"""
    if raw_url.startswith("http"):
        return raw_url
    if raw_url.startswith("//"):
        return "https:" + raw_url
    if raw_url.startswith("/"):
        return "https://www.ximalaya.com" + raw_url
    return raw_url


def _infer_subject(title: str, intro: str, category_title: str, category_id: str) -> str:
    """根据标题、简介、分类推断主题分类。"""
    combined = f"{title} {intro} {category_title}".lower()

    if category_id in CATEGORY_MAP:
        cat_name = CATEGORY_MAP[category_id]
        if cat_name in ("儿歌", "睡前故事", "童话"):
            return "兴趣拓展"
        if cat_name == "国学":
            return "古诗国学"
        if cat_name == "英语":
            return "英语"
        if cat_name == "教育培训":
            return "学科同步"

    for subject, keywords in CHILD_CATEGORY_KEYWORDS.items():
        if any(kw.lower() in combined for kw in keywords):
            return subject

    return "兴趣拓展"


def output_results(
    results: list[dict[str, Any]],
    keyword: str,
    output_file: str | None = None,
) -> dict[str, Any]:
    """输出符合 platform-search-contract 的搜索结果 JSON。"""
    data = {
        "platform": "ximalaya",
        "query": keyword,
        "total_found": len(results),
        "returned_count": len(results),
        "search_method": "api",
        "has_more": False,
        "results": results,
    }
    output = json.dumps(data, ensure_ascii=False, indent=2)
    if output_file:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        Path(output_file).write_text(output + "\n", encoding="utf-8")
        log.info("搜索结果已保存: %s", output_file)
    else:
        print(output)
    return data


# ─── CLI ───────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="喜马拉雅搜索脚本")
    sub = parser.add_subparsers(dest="cmd")

    s = sub.add_parser("search", help="搜索喜马拉雅音频")
    s.add_argument("keyword", help="搜索关键词")
    s.add_argument("--core", choices=["album", "track"], default="album",
                   help="搜索类型：album（专辑，默认）/ track（声音）")
    s.add_argument("--max", type=int, default=20, help="最大返回数（默认 20）")
    s.add_argument("--free-only", action="store_true", help="只返回免费内容")
    s.add_argument("--sort", choices=["relevance", "popularity", "newest"], default="relevance",
                   help="排序方式（默认 relevance）")
    s.add_argument("-o", "--output", default=None, help="输出 JSON 文件路径")

    args = parser.parse_args()

    if args.cmd == "search":
        results = search(
            args.keyword,
            core=args.core,
            max_results=args.max,
            free_only=args.free_only,
            sort_by=args.sort,
        )
        output_results(results, args.keyword, args.output)
        return 0 if results else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
