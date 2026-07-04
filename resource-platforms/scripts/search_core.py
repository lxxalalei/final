#!/usr/bin/env python3
"""Standalone platform search core.

This module intentionally knows nothing about learning-resource pipeline stages.
It executes platform/search tasks and returns normalized resources plus errors.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_REGISTRY = ROOT / "config" / "search-registry.json"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: 根节点必须是 object")
    return value


def resolve_env_file(path: Path) -> Path | None:
    if path.is_absolute():
        return path if path.is_file() else None

    candidates = [
        Path.cwd() / path,
        ROOT / path,
        PROJECT_ROOT / path,
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return None


def resolve_env_files(path: Path) -> list[Path]:
    resolved: list[Path] = []
    primary = resolve_env_file(path)
    if primary:
        resolved.append(primary)

    if path.name != ".env.local":
        local = resolve_env_file(Path(".env.local"))
        if local and local not in resolved:
            resolved.append(local)
    return resolved


def load_env_file(path: Path) -> Path | None:
    if not path.is_file():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.lstrip("\ufeff").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value
    return path


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    return load_json(path)


def _runtime_env_value(name: str) -> str:
    value = os.environ.get(name, "")
    if name.endswith("_FILE") and value:
        path = Path(value).expanduser()
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8-sig").strip()
            except OSError:
                return ""
    return value


def _auth_env_is_valid(name: str, runtime: dict[str, Any]) -> tuple[bool, list[str]]:
    value = _runtime_env_value(name)
    if not value:
        return False, []

    requirements = runtime.get("cookie_requirements") or {}
    required_parts = requirements.get(name) if isinstance(requirements, dict) else None
    if not required_parts:
        return True, []

    missing = [
        str(part)
        for part in required_parts
        if str(part) not in value
    ]
    return not missing, missing


def executable_available(name: str) -> bool:
    if not name:
        return False
    path = Path(name)
    return path.is_file() or shutil.which(name) is not None


def node_module_available(name: str) -> bool:
    if not name or not executable_available("node"):
        return False
    try:
        proc = subprocess.run(
            ["node", "-e", f"require.resolve({json.dumps(name)})"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def available_platforms(registry_document: dict[str, Any]) -> list[str]:
    platforms = registry_document.get("platforms", {})
    if not isinstance(platforms, dict):
        return []
    return [
        name
        for name, entry in platforms.items()
        if isinstance(entry, dict) and entry.get("status") == "available"
    ]


def platform_groups(registry_document: dict[str, Any]) -> dict[str, list[str]]:
    groups = registry_document.get("groups")
    platforms = registry_document.get("platforms", {})
    known = set(platforms) if isinstance(platforms, dict) else set()
    output: dict[str, list[str]] = {}
    if isinstance(groups, dict):
        for name, members in groups.items():
            if isinstance(members, list):
                output[name] = [str(item) for item in members if str(item) in known]
    output.setdefault("all", available_platforms(registry_document))
    return output


def load_adapter(entry: str):
    path = (ROOT / entry).resolve()
    root = ROOT.resolve()
    if not path.is_file() or (path != root and root not in path.parents):
        raise ValueError(f"无效 adapter: {entry}")
    spec = importlib.util.spec_from_file_location(f"platform_search_adapter_{path.parent.name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    adapter = getattr(module, "ADAPTER", None)
    if adapter is None or not callable(getattr(adapter, "search", None)):
        raise TypeError(f"adapter 必须导出 ADAPTER.search: {path}")
    return adapter


def check_runtime(config: dict[str, Any]) -> dict[str, Any] | None:
    runtime = config.get("runtime") or {}
    missing_executables = [
        str(name)
        for name in runtime.get("executables_all", [])
        if not executable_available(str(name))
    ]
    if missing_executables:
        return {
            "error_code": "SYSTEM_DEPENDENCY_MISSING",
            "message": f"缺少可执行程序: {', '.join(missing_executables)}",
            "retryable": False,
        }

    missing_node = [
        str(name)
        for name in runtime.get("node_all", [])
        if not node_module_available(str(name))
    ]
    if missing_node:
        return {
            "error_code": "SYSTEM_DEPENDENCY_MISSING",
            "message": f"缺少 Node 依赖: {', '.join(missing_node)}",
            "retryable": False,
        }

    missing = [
        name
        for name in runtime.get("python_all", [])
        if importlib.util.find_spec(str(name)) is None
    ]
    if missing:
        return {
            "error_code": "SYSTEM_DEPENDENCY_MISSING",
            "message": f"缺少 Python 依赖: {', '.join(missing)}",
            "retryable": False,
        }

    alternatives = [str(name) for name in runtime.get("python_any", [])]
    if alternatives and not any(importlib.util.find_spec(name) is not None for name in alternatives):
        return {
            "error_code": "SYSTEM_DEPENDENCY_MISSING",
            "message": f"至少需要一个 Python 依赖: {', '.join(alternatives)}",
            "retryable": False,
        }

    auth_env = [str(name) for name in runtime.get("auth_any_env", [])]
    if auth_env and not any(os.environ.get(name) for name in auth_env):
        return {
            "error_code": "AUTH_REQUIRED",
            "message": f"需要设置以下环境变量之一: {', '.join(auth_env)}",
            "retryable": False,
        }
    if auth_env:
        invalid: list[str] = []
        for name in auth_env:
            valid, missing_parts = _auth_env_is_valid(name, runtime)
            if valid:
                return None
            if os.environ.get(name) and missing_parts:
                invalid.append(f"{name} 缺少 {', '.join(missing_parts)}")
            elif os.environ.get(name):
                invalid.append(f"{name} 为空或不可读取")
        if invalid:
            return {
                "error_code": "AUTH_REQUIRED",
                "message": "；".join(invalid),
                "retryable": False,
            }
    return None


# 这些错误是永久性的：重试结果相同，串行重跑只是浪费时间。
# 注意：AUTH_REQUIRED 虽然常被标为不可重试，但平台并发触发的瞬时 403
# （如知乎）串行重跑往往能成，故不列入——按"是否永久系统错误"判断而非 retryable 标志。
_NON_RETRYABLE_ERROR_CODES = frozenset({
    "SYSTEM_DEPENDENCY_MISSING",
    "SYSTEM_ADAPTER_LOAD_FAILED",
    "SYSTEM_TOOL_NOT_FOUND",
    "SYSTEM_EXECUTION_FAILED",
    "SEARCH_PLATFORM_UNAVAILABLE",
    "SEARCH_QUERY_EMPTY",
    "PARSE_FORMAT_NOT_SUPPORTED",
    "PARSE_EMPTY_CONTENT",
})


def _error_is_retryable(error: dict[str, Any]) -> bool:
    code = str(error.get("error_code") or "")
    return code not in _NON_RETRYABLE_ERROR_CODES


async def execute_task(task: dict[str, Any], registry: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    platform = task.get("platform")
    config = registry.get(platform) if isinstance(platform, str) else None
    if not isinstance(config, dict) or config.get("status") != "available":
        return [], [{
            "platform": platform,
            "error_code": "SEARCH_PLATFORM_UNAVAILABLE",
            "message": "平台未注册或当前不可用",
            "retryable": False,
        }]

    runtime_error = check_runtime(config)
    if runtime_error:
        return [], [{"platform": platform, **runtime_error}]

    try:
        adapter = load_adapter(str(config["entry"]))
    except Exception as exc:
        return [], [{
            "platform": platform,
            "error_code": "SYSTEM_ADAPTER_LOAD_FAILED",
            "message": str(exc),
            "retryable": False,
        }]

    resources: list[dict] = []
    errors: list[dict] = []
    timeout = int(config.get("timeout_seconds", 60))
    for search in task.get("searches", []):
        if not isinstance(search, dict):
            continue
        query = str(search.get("query") or "").strip()
        if not query:
            errors.append({
                "platform": platform,
                "query": query,
                "error_code": "SEARCH_QUERY_EMPTY",
                "message": "查询词为空",
                "retryable": False,
            })
            continue
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    adapter.search,
                    query,
                    int(search.get("max_results", 10)),
                    dict(search.get("params") or {}),
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            response = {
                "results": [],
                "error": {"error_code": "NETWORK_TIMEOUT", "message": "平台搜索超时", "retryable": True},
            }
        except Exception as exc:
            response = {
                "results": [],
                "error": {"error_code": "SEARCH_EXECUTION_FAILED", "message": str(exc), "retryable": False},
            }
        for item in response.get("results", []):
            if isinstance(item, dict):
                resources.append(item)
        error = response.get("error")
        if isinstance(error, dict):
            errors.append({"platform": platform, "query": query, **error})
    return resources, errors


def exact_dedup(resources: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    output = []
    for item in resources:
        key = (str(item.get("platform", "")), str(item.get("resource_id") or item.get("source_url") or ""))
        if not key[1] or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


async def run_tasks(
    tasks: list[dict[str, Any]],
    registry_document: dict[str, Any],
    max_concurrency: int | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    registry = registry_document.get("platforms", {})
    if not isinstance(registry, dict):
        registry = {}
    concurrency = max(1, int(max_concurrency or registry_document.get("max_concurrency", 4)))
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded(task: dict[str, Any]):
        async with semaphore:
            return await execute_task(task, registry)

    # 第一轮：并发跑全部任务
    executions = await asyncio.gather(*(bounded(task) for task in tasks))

    # 串行重试：挑出并发时失败、且错误属于瞬时类（风控/超时/偶发 403 等）的平台，
    # 逐个单独重跑。并发触发风控时，知乎/百度等平台对短时间内多来源请求更敏感，
    # 串行重试常常能拿到结果。永久性错误（依赖缺失/平台未注册/格式问题）不重试。
    retries: list[dict[str, Any]] = []
    for task, (first_resources, first_errors) in zip(tasks, executions):
        if first_resources:
            continue  # 已有结果，不重试
        if not any(_error_is_retryable(err) for err in first_errors):
            continue  # 全是永久性错误，重试无意义
        retries.append(task)

    retry_outcomes: dict[str, tuple[list[dict], list[dict]]] = {}
    if retries:
        await asyncio.sleep(0.5)
        for task in retries:
            retry_outcomes[task["platform"]] = await execute_task(task, registry)

    # 合并：重试成功（拿到资源）的平台用重试结果，否则保留第一轮结果与错误。
    merged: list[tuple[list[dict], list[dict]]] = []
    for task, outcome in zip(tasks, executions):
        platform = task.get("platform")
        if platform in retry_outcomes:
            retry_resources, retry_errors = retry_outcomes[platform]
            if retry_resources:
                merged.append((retry_resources, retry_errors))
                continue
        merged.append(outcome)

    resources = exact_dedup([item for result, _ in merged for item in result])
    errors = [error for _, task_errors in merged for error in task_errors]
    failed_platforms = []
    for task in tasks:
        platform = task.get("platform")
        platform_results = [item for item in resources if item.get("platform") == platform]
        platform_errors = [item for item in errors if item.get("platform") == platform]
        if not platform_results and platform_errors and platform not in failed_platforms:
            failed_platforms.append(platform)
    return {
        "success": bool(resources) or not failed_platforms,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "data": {
            "resources": resources,
            "errors": errors,
            "summary": {
                "task_count": len(tasks),
                "resource_count": len(resources),
                "failed_platforms": failed_platforms,
                "serial_retried_platforms": [task.get("platform") for task in retries],
            },
        },
    }


def normalize_task(platform: str, query: str, max_results: int, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "platform": platform,
        "searches": [{
            "query": query,
            "max_results": max_results,
            "params": dict(params or {}),
        }],
    }
