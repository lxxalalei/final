#!/usr/bin/env python3
"""Render a validated Selector review as a stable numbered candidate list."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: 根节点必须是 object")
    return value


def level(score: int) -> str:
    if score >= 90:
        return "S"
    if score >= 75:
        return "A"
    if score >= 60:
        return "B"
    return "C"


def known_facts(resource: dict[str, Any]) -> list[str]:
    facts: list[str] = []
    if resource.get("is_free") is True:
        facts.append("平台标记免费")
    elif resource.get("is_free") is False:
        facts.append("平台标记付费")
    if resource.get("duration") not in (None, ""):
        facts.append(f"时长 {resource['duration']}")
    if resource.get("download_feasibility"):
        facts.append(f"下载可行性 {resource['download_feasibility']}")
    signals = resource.get("platform_signals") or {}
    if isinstance(signals, dict):
        for key, label in (("lessons", "课时"), ("tracks_count", "集数"), ("views", "播放/访问")):
            if signals.get(key) is not None:
                facts.append(f"{label} {signals[key]}")
    return facts


def render(session_dir: Path, offset: int, limit: int) -> str:
    selector_input = load_object(session_dir / "selector_input.json")
    review = load_object(session_dir / "selector_review.json")
    stage3 = load_object(session_dir / "stage3_search_results.json")
    resources = {
        item.get("resource_id"): item for item in stage3.get("data", {}).get("resources", [])
        if isinstance(item, dict)
    }
    candidates = review.get("data", {}).get("candidates", [])
    excluded = review.get("data", {}).get("excluded", [])
    summary = selector_input.get("_summary", {})
    lines = [
        f"共搜索到 {summary.get('raw_count', 0)} 条；精确去重 {summary.get('exact_duplicate_count', 0)} 条，"
        f"过滤 {len(excluded)} 条，保留 {len(candidates)} 条。"
    ]
    platform_errors = selector_input.get("data", {}).get("platform_errors", [])
    if platform_errors:
        errors = "、".join(f"{item.get('platform')}（{item.get('error_code')}）" for item in platform_errors)
        lines.append(f"平台异常：{errors}")
    lines.append("")
    for index, review_item in enumerate(candidates[offset:offset + limit], start=offset + 1):
        resource = resources.get(review_item.get("resource_id"), {})
        score = review_item["quality_score"]
        platform = resource.get("platform", "未知平台")
        resource_type = resource.get("type", "类型未知")
        lines.append(f"{index}. [{level(score)}级 · {score}分] {resource.get('title', review_item.get('resource_id'))}")
        if resource.get("source_url"):
            lines.append(f"   链接：{resource['source_url']}")
        lines.append(f"   来源/类型：{platform} · {resource_type}")
        facts = known_facts(resource)
        if facts:
            lines.append(f"   已知信息：{'；'.join(facts)}")
        lines.append(f"   推荐依据：{'；'.join(review_item.get('reasons', []))}")
        if review_item.get("notes"):
            lines.append(f"   注意：{'；'.join(review_item['notes'])}")
        lines.append("")
    if offset + limit < len(candidates):
        lines.append(f"还有 {len(candidates) - offset - limit} 条候选，回复“查看更多”继续展示。")
    lines.append("回复编号选择，例如“1,3”；也可以回复“全部”“只要视频”或“取消”。")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染 Selector 候选")
    parser.add_argument("session_dir", type=Path)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = render(args.session_dir, max(0, args.offset), max(1, args.limit))
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
