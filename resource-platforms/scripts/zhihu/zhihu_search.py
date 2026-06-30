#!/usr/bin/env python3
"""知乎搜索脚本 — 调用知乎搜索 API，输出标准搜索结果 JSON。

认证要求：d_c0（设备指纹）+ z_c0（登录态）同时传入。
凭证查找优先级：
  1. CLI 参数 --cookie
  2. 环境变量 ZHIHU_COOKIE
  3. 配置文件 config/credentials.json（随 skill 安装在用户本地）

输出格式遵循 platform-search-contract.md 的 results 规范。

用法:
  python zhihu_search.py search "三年级数学学习方法" --max 20 -o candidates.json
  python zhihu_search.py search "小学英语启蒙" --cookie "d_c0值 z_c0值" --max 20
  python zhihu_search.py set-cookie "d_c0值 z_c0值"  # 持久化到 config/credentials.json

依赖:
  - 标准库 urllib，无需第三方包
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.logger import getLogger

log = getLogger("zhihu")

# ========== 配置 ==========
SEARCH_API = "https://www.zhihu.com/api/v4/search_v3"
ZHIHU_BASE = "https://www.zhihu.com"

CONFIG_DIR = Path(__file__).resolve().parent / "config"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# 知乎 type → 标准资源类型
TYPE_MAP = {
    "content": "文章",
    "article": "文章",
    "answer": "问答",
    "question": "问答",
    "topic": "话题",
}
# ==========================


# ═══════════════════════════════════════════════════════════
#  凭证管理
# ═══════════════════════════════════════════════════════════

def load_cookie() -> str | None:
    """从配置文件读取已保存的 cookie。

    查找优先级：CLI 参数 > 环境变量 > 配置文件。
    此函数只负责第 3 级（配置文件），前两级在调用方处理。
    """
    if CREDENTIALS_FILE.exists():
        try:
            data = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
            cookie = data.get("cookie") or data.get("z_c0")
            if cookie:
                log.debug("从配置文件读取凭证")
                return cookie
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("凭证文件解析失败: %s", exc)
    return None


def save_cookie(cookie: str) -> None:
    """持久化 cookie 到配置文件。

    存储路径：scripts/zhihu/config/credentials.json
    随 skill 安装在用户本地，后续自动读取。
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {"cookie": cookie}
    CREDENTIALS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log.info("凭证已保存到 %s", CREDENTIALS_FILE)


def resolve_cookie(cli_cookie: str | None) -> str | None:
    """按优先级解析 cookie：CLI 参数 > 环境变量 > 配置文件。"""
    if cli_cookie:
        return cli_cookie
    env_cookie = os.environ.get("ZHIHU_COOKIE")
    if env_cookie:
        return env_cookie
    return load_cookie()


# ═══════════════════════════════════════════════════════════
#  HTTP 请求头构建
# ═══════════════════════════════════════════════════════════

def _get_auth_headers(cookie: str | None, token: str | None, keyword: str = "") -> dict[str, str]:
    """构建带认证的请求头。

    知乎搜索 API 需要 d_c0（设备指纹）和 z_c0（登录态）同时存在。
    """
    headers: dict[str, str] = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "x-requested-with": "fetch",
    }
    # Referer 必须是 ASCII 安全的（urllib 的 putheader 不支持非 latin-1）
    if keyword:
        headers["Referer"] = f"{ZHIHU_BASE}/search?q={urllib.parse.quote(keyword)}"
    else:
        headers["Referer"] = f"{ZHIHU_BASE}/"

    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif cookie:
        z_c0 = _extract_value(cookie, "z_c0")
        if z_c0:
            headers["Authorization"] = f"Bearer {z_c0}"
    cookie_str = _build_cookie_str(cookie)
    if cookie_str:
        headers["Cookie"] = cookie_str
    return headers


def _extract_value(raw: str, key: str) -> str | None:
    """从 cookie 字符串中提取指定 key 的值。

    支持两种格式：
      1. 完整 cookie: "{key}=xxx; other=yyy"
      2. itsdangerous 序列化裸值: "2|1:0|...|4:{key}|92:实际值|..."
    """
    # 格式 1: key=value（取到分号或字符串末尾）
    m = re.search(rf"{key}=([^;]+)", raw)
    if m:
        return m.group(1)
    # 格式 2: 裸 itsdangerous 值
    if f"|4:{key}|" in raw:
        idx = raw.find(f"|4:{key}|")
        if idx >= 0:
            start = raw.rfind("2|1:0|", 0, idx)
            if start >= 0:
                remaining = raw[idx:]
                m2 = re.search(r"\|([0-9a-f]{40,})$", remaining)
                if m2:
                    end = idx + m2.end()
                    return raw[start:end]
            return raw
    return None


def _build_cookie_str(raw: str | None) -> str:
    """从输入构建 Cookie 头字符串。

    支持的输入格式：
      - 完整 cookie: "d_c0=xxx; z_c0=yyy" → 原样返回
      - 两个裸值用空格分隔: "d_c0值 z_c0值" → 自动识别并包装
      - 单个裸 itsdangerous z_c0 值 → 包装为 z_c0=值
      - 单个裸 d_c0 值 → 包装为 d_c0=值
    """
    if not raw:
        return ""
    raw = raw.strip()
    # 完整 cookie 格式：以已知 key= 开头
    if re.match(r"^(d_c0|z_c0)\s*=", raw):
        return raw
    # 两个或多个裸值用空格/逗号分隔
    parts = re.split(r"[\s,]+", raw)
    if len(parts) >= 2:
        cookies = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if "|4:z_c0|" in p or p.startswith("2|1:0|"):
                cookies.append(f"z_c0={p}")
            elif len(p) > 10:
                cookies.append(f"d_c0={p}")
        return "; ".join(cookies) if cookies else ""
    # 单个裸值
    if "|4:z_c0|" in raw or raw.startswith("2|1:0|"):
        return f"z_c0={raw}"
    if len(raw) > 10:
        return f"d_c0={raw}"
    return ""


# ═══════════════════════════════════════════════════════════
#  搜索
# ═══════════════════════════════════════════════════════════

# 错误码常量（输出到 stderr 供 adapter 层识别）
ERR_NO_CREDENTIAL = "CREDENTIAL_MISSING"
ERR_CREDENTIAL_EXPIRED = "CREDENTIAL_EXPIRED"


def search(
    keyword: str,
    cookie: str | None = None,
    token: str | None = None,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """调用知乎搜索 API，返回标准结果列表。

    凭证查找优先级：cookie 参数 > ZHIHU_COOKIE 环境变量 > config/credentials.json。
    无凭证时返回空列表并输出错误信号。
    """
    log.info("知乎搜索: '%s' (max=%d)", keyword, max_results)

    cookie = resolve_cookie(cookie)
    token = token or os.environ.get("ZHIHU_TOKEN")
    headers = _get_auth_headers(cookie, token, keyword)

    has_auth = "Authorization" in headers
    has_cookie = "Cookie" in headers
    if not has_auth and not has_cookie:
        log.error("[%s] 缺少知乎认证信息，请通过 set-cookie 命令配置", ERR_NO_CREDENTIAL)
        return []
    if not has_auth:
        log.warning("无 z_c0 登录态，仅有 d_c0 设备指纹，API 可能拒绝")

    candidates: list[dict[str, Any]] = []
    offset = 0
    limit = min(max_results, 20)

    while len(candidates) < max_results:
        params = {
            "t": "general",
            "q": keyword,
            "correction": "1",
            "offset": str(offset),
            "limit": str(limit),
            "show_all_topics": "0",
            "search_source": "Filter",
            "type": "content",
        }
        url = f"{SEARCH_API}?{urllib.parse.urlencode(params)}"
        log.info("搜索 API 调用: offset=%d limit=%d", offset, limit)

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    log.warning("搜索 API 返回 HTTP %d", resp.status)
                    break
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                log.error(
                    "[%s] 知乎认证已过期（HTTP %d），请重新获取 d_c0 和 z_c0 cookie",
                    ERR_CREDENTIAL_EXPIRED, exc.code,
                )
            else:
                log.error("搜索 API 请求失败: HTTP %d", exc.code)
            break
        except Exception as exc:
            log.error("搜索 API 请求失败: %s", exc)
            break

        items = data.get("data") or []
        if not items:
            log.info("搜索 API 无更多结果")
            break

        for item in items:
            obj = item.get("object") or item
            cand = _parse_search_item(obj, item)
            if cand:
                candidates.append(cand)
                if len(candidates) >= max_results:
                    break

        paging = data.get("paging") or {}
        is_end = paging.get("is_end", True)
        if is_end:
            break
        offset += limit

    log.info("搜索 API 返回 %d 条结果", len(candidates))
    return candidates[:max_results]


def _parse_search_item(obj: dict[str, Any], raw_item: dict[str, Any]) -> dict[str, Any] | None:
    """解析单条 API 结果为标准搜索结果。"""
    obj_type = str(obj.get("type") or raw_item.get("type") or "").lower()
    resource_id = str(obj.get("id") or "")

    title = (
        obj.get("title")
        or raw_item.get("highlight", {}).get("title")
        or obj.get("name")
        or "无标题"
    )
    title = re.sub(r"<[^>]+>", "", title).strip()

    source_url = ""
    if obj_type == "answer":
        qid = obj.get("question", {}).get("id") or ""
        source_url = f"{ZHIHU_BASE}/question/{qid}/answer/{resource_id}" if qid else ""
    elif obj_type == "article":
        source_url = obj.get("url") or f"{ZHIHU_BASE}/p/{resource_id}"
    elif obj_type == "question":
        source_url = f"{ZHIHU_BASE}/question/{resource_id}"
    else:
        source_url = obj.get("url") or ""

    if not source_url or not title:
        return None

    snippet_raw = (
        raw_item.get("highlight", {}).get("content")
        or obj.get("excerpt")
        or obj.get("content")
        or ""
    )
    snippet = re.sub(r"<[^>]+>", "", snippet_raw).strip()[:200]

    resource_type = TYPE_MAP.get(obj_type, "文章")
    author = obj.get("author", {}).get("name", "") if isinstance(obj.get("author"), dict) else ""

    return {
        "resource_id": f"zhihu:{resource_id}" if resource_id else f"zhihu:{source_url}",
        "title": title,
        "type": resource_type,
        "platform": "zhihu",
        "source_url": source_url,
        "source_name": "知乎",
        "quality_level": "B",
        "platform_quality_score": 60,
        "download_feasibility": "中",
        "description": snippet,
        "provider": author,
        "tags": [],
        "language": "中文",
    }


def output_results(results: list[dict[str, Any]], keyword: str, output_file: str | None = None) -> dict[str, Any]:
    """输出符合 platform-search-contract 的搜索结果 JSON。"""
    data = {
        "platform": "zhihu",
        "query": keyword,
        "total_found": len(results),
        "returned_count": len(results),
        "search_method": "api",
        "has_more": False,
        "results": results,
    }
    output = json.dumps(data, ensure_ascii=False, indent=2)
    if output_file:
        Path(output_file).write_text(output + "\n", encoding="utf-8")
        log.info("搜索结果已保存: %s", output_file)
    else:
        print(output)
    return data


# ═══════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="知乎搜索脚本")
    sub = parser.add_subparsers(dest="cmd")

    # search 子命令
    s = sub.add_parser("search", help="搜索知乎问答/文章")
    s.add_argument("keyword", help="搜索关键词")
    s.add_argument("--cookie", default=None, help="知乎 Cookie（d_c0 和 z_c0，会覆盖配置文件）")
    s.add_argument("--token", default=None, help="知乎 Bearer token")
    s.add_argument("--max", type=int, default=20, help="最大返回数（默认 20）")
    s.add_argument("-o", "--output", default=None, help="输出 JSON 文件路径")

    # set-cookie 子命令：持久化 cookie 到本地配置文件
    sc = sub.add_parser("set-cookie", help="保存知乎 Cookie 到本地配置文件")
    sc.add_argument("cookie", help="知乎 Cookie（d_c0 和 z_c0，空格或分号分隔）")

    # check-cookie 子命令：检查已保存的 cookie
    sub.add_parser("check-cookie", help="检查本地已保存的凭证")

    args = parser.parse_args()

    if args.cmd == "search":
        results = search(
            args.keyword,
            cookie=args.cookie,
            token=args.token,
            max_results=args.max,
        )
        output_results(results, args.keyword, args.output)
        return 0 if results else 1

    elif args.cmd == "set-cookie":
        save_cookie(args.cookie)
        print(f"凭证已保存到 {CREDENTIALS_FILE}")
        return 0

    elif args.cmd == "check-cookie":
        cookie = load_cookie()
        if cookie:
            # 显示脱敏摘要
            if len(cookie) > 20:
                masked = cookie[:8] + "..." + cookie[-8:]
            else:
                masked = "***"
            print(f"已保存凭证: {masked}")
            # 检查是否包含 z_c0
            has_z = bool(_extract_value(cookie, "z_c0"))
            has_d = "d_c0=" in _build_cookie_str(cookie) or bool(_extract_value(cookie, "d_c0"))
            print(f"  z_c0 (登录态): {'有' if has_z else '无'}")
            print(f"  d_c0 (设备指纹): {'有' if has_d else '无'}")
        else:
            print("未找到已保存的凭证")
            print(f"凭证文件位置: {CREDENTIALS_FILE}")
            print("使用以下命令保存: python zhihu_search.py set-cookie \"d_c0值 z_c0值\"")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
