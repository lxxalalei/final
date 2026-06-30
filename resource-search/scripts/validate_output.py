#!/usr/bin/env python3
"""Validate only the executable shape of search-plan/v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "config/platform-catalog.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: 根节点必须是 object")
    return value


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return True


def validate(document: dict[str, Any], catalog: dict[str, Any], intent: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    meta = document.get("_meta")
    summary = document.get("_summary")
    data = document.get("data")
    if not isinstance(meta, dict):
        return ["缺少 object: _meta"]
    if not isinstance(summary, dict):
        return ["缺少 object: _summary"]
    if not isinstance(data, dict):
        return ["缺少 object: data"]

    expected_meta = {
        "stage": 2,
        "skill": "resource-search",
        "input_from": "stage1_intent.json",
        "schema_version": "search-plan/v1",
    }
    for key, expected in expected_meta.items():
        if meta.get(key) != expected:
            errors.append(f"_meta.{key} 必须为 {expected!r}")
    if data.get("schema_version") != "search-plan/v1":
        errors.append("data.schema_version 必须为 search-plan/v1")
    if data.get("intent_ref") != "stage1_intent.json":
        errors.append("data.intent_ref 必须为 stage1_intent.json")
    if not isinstance(data.get("strategy"), str) or not data["strategy"].strip():
        errors.append("data.strategy 必须是非空字符串")

    platforms = catalog.get("platforms")
    if catalog.get("schema_version") != "search-platform-catalog/v1" or not isinstance(platforms, dict):
        return errors + ["Search 平台目录必须符合 search-platform-catalog/v1"]

    tasks = data.get("search_tasks")
    if not isinstance(tasks, list) or not tasks:
        return errors + ["data.search_tasks 必须是非空数组"]

    task_ids: set[str] = set()
    used_platforms: list[str] = []
    generic_count = 0
    query_count = 0
    expected_results = 0

    for index, task in enumerate(tasks):
        path = f"search_tasks[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{path} 必须是 object")
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.startswith("task-"):
            errors.append(f"{path}.task_id 格式非法")
        elif task_id in task_ids:
            errors.append(f"task_id 重复: {task_id}")
        else:
            task_ids.add(task_id)

        platform = task.get("platform")
        entry = platforms.get(platform) if isinstance(platform, str) else None
        if not isinstance(entry, dict):
            errors.append(f"{path}.platform 未注册: {platform!r}")
            supported_params: dict[str, Any] = {}
        elif entry.get("planning_status") != "available":
            errors.append(f"{path}.platform 不可执行: {platform}")
            supported_params = {}
        else:
            used_platforms.append(platform)
            supported_params = entry.get("search_parameters", {})
            if not isinstance(supported_params, dict):
                supported_params = {}
        if platform == "generic":
            generic_count += 1

        if task.get("priority") not in {"P0", "P1", "P2"}:
            errors.append(f"{path}.priority 非法")
        if not isinstance(task.get("reason"), str) or not task["reason"].strip():
            errors.append(f"{path}.reason 必须是非空字符串")

        searches = task.get("searches")
        if not isinstance(searches, list) or not searches:
            errors.append(f"{path}.searches 必须是非空数组")
            continue
        seen_queries: set[str] = set()
        for search_index, search in enumerate(searches):
            search_path = f"{path}.searches[{search_index}]"
            if not isinstance(search, dict):
                errors.append(f"{search_path} 必须是 object")
                continue
            query = search.get("query")
            if not isinstance(query, str) or not query.strip():
                errors.append(f"{search_path}.query 必须是非空字符串")
            elif query.strip().lower() in seen_queries:
                errors.append(f"{path} 内搜索词重复: {query!r}")
            else:
                seen_queries.add(query.strip().lower())
            max_results = search.get("max_results")
            if not isinstance(max_results, int) or isinstance(max_results, bool) or not 1 <= max_results <= 100:
                errors.append(f"{search_path}.max_results 必须在 1-100")
            else:
                expected_results += max_results
            params = search.get("params")
            if not isinstance(params, dict):
                errors.append(f"{search_path}.params 必须是 object")
                continue
            unknown = set(params) - set(supported_params)
            if unknown:
                errors.append(f"{search_path}.params 包含平台不支持的参数: {sorted(unknown)}")
            for name, spec in supported_params.items():
                if isinstance(spec, dict) and spec.get("required_values") and name not in params:
                    errors.append(f"{search_path}.params 缺少必需参数: {name}")
            for name, value in params.items():
                spec = supported_params.get(name)
                if not isinstance(spec, dict):
                    continue
                expected_type = spec.get("type")
                if isinstance(expected_type, str) and not _matches_type(value, expected_type):
                    errors.append(f"{search_path}.params.{name} 类型应为 {expected_type}")
                    continue
                allowed = spec.get("allowed")
                if isinstance(allowed, list):
                    values = value if isinstance(value, list) else [value]
                    if any(item not in allowed for item in values):
                        errors.append(f"{search_path}.params.{name} 含不支持的值")
                required_values = spec.get("required_values")
                if isinstance(required_values, list) and (
                    not isinstance(value, list) or not set(required_values).issubset(set(value))
                ):
                    errors.append(f"{search_path}.params.{name} 必须包含 {required_values}")
            query_count += 1

    if generic_count != 1:
        errors.append(f"search_tasks 必须恰好包含一个 generic 任务，实际 {generic_count} 个")
    if summary.get("platform_count") != len(set(used_platforms)):
        errors.append("_summary.platform_count 与平台数不一致")
    if summary.get("platforms") != list(dict.fromkeys(used_platforms)):
        errors.append("_summary.platforms 必须按任务顺序列出唯一平台")
    if summary.get("query_count") != query_count:
        errors.append("_summary.query_count 与实际搜索词数量不一致")
    if summary.get("expected_results") != expected_results:
        errors.append("_summary.expected_results 与 max_results 总和不一致")

    if intent is not None and intent.get("data", {}).get("status") != "ready":
        errors.append("不能为非 ready 的 intent 生成搜索计划")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 search-plan/v1 的可执行结构")
    parser.add_argument("file", type=Path)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--intent", type=Path)
    args = parser.parse_args()
    try:
        document = load_json(args.file)
        catalog = load_json(args.catalog)
        intent = load_json(args.intent) if args.intent else None
        errors = validate(document, catalog, intent)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
