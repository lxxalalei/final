#!/usr/bin/env python3
"""platform-search 的独立命令行入口。"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from search_core import (
    DEFAULT_REGISTRY,
    available_platforms,
    check_runtime,
    executable_available,
    load_env_file,
    load_registry,
    node_module_available,
    normalize_task,
    platform_groups,
    resolve_env_files,
    run_tasks,
)


class ChineseHelpFormatter(argparse.HelpFormatter):
    SECTION_TITLES = {
        "positional arguments": "位置参数",
        "options": "选项",
        "optional arguments": "选项",
        "subcommands": "子命令",
    }

    def start_section(self, heading: str | None) -> None:
        super().start_section(self.SECTION_TITLES.get(heading or "", heading))


def parse_params(values: list[str] | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for value in values or []:
        if "=" not in value:
            raise SystemExit(f"--param 需要 key=value，收到: {value}")
        key, raw = value.split("=", 1)
        key = key.strip()
        raw = raw.strip()
        if not key:
            raise SystemExit(f"--param 的 key 不能为空: {value}")
        lowered = raw.lower()
        if lowered in {"true", "false"}:
            params[key] = lowered == "true"
        elif lowered in {"null", "none"}:
            params[key] = None
        else:
            try:
                params[key] = int(raw)
            except ValueError:
                params[key] = raw
    return params


def write_output(document: dict[str, Any], path: str | None, pretty: bool) -> None:
    text = json.dumps(document, ensure_ascii=False, indent=2 if pretty else None)
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_text(text + "\n", encoding="utf-8")
        os.replace(temp, target)
        print(str(target), file=sys.stderr)
    else:
        _write_stdout(text)


def _write_stdout(text: str) -> None:
    output = getattr(sys.stdout, "buffer", None)
    if output is not None:
        output.write((text + "\n").encode("utf-8"))
        output.flush()
        return
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def load_common(args: argparse.Namespace) -> dict[str, Any]:
    requested = Path(args.env_file)
    env_paths = resolve_env_files(requested)
    args._resolved_env_files = [str(path) for path in env_paths]
    args._resolved_env_file = str(env_paths[0]) if env_paths else None
    for env_path in env_paths:
        load_env_file(env_path)
    return load_registry(Path(args.registry))


def _runtime_diagnostics(config: dict[str, Any]) -> dict[str, Any]:
    runtime = config.get("runtime") or {}
    if not isinstance(runtime, dict):
        runtime = {}

    python_all = [str(name) for name in runtime.get("python_all", [])]
    python_any = [str(name) for name in runtime.get("python_any", [])]
    python_optional = [str(name) for name in runtime.get("python_optional", [])]
    executables_all = [str(name) for name in runtime.get("executables_all", [])]
    node_all = [str(name) for name in runtime.get("node_all", [])]
    auth_any_env = [str(name) for name in runtime.get("auth_any_env", [])]
    optional_auth_env = [str(name) for name in runtime.get("optional_auth_env", [])]

    return {
        "executables_all": {
            "required": executables_all,
            "missing": [name for name in executables_all if not executable_available(name)],
        },
        "node_all": {
            "required": node_all,
            "missing": [name for name in node_all if not node_module_available(name)],
        },
        "python_all": {
            "required": python_all,
            "missing": [
                name for name in python_all
                if importlib.util.find_spec(name) is None
            ],
        },
        "python_any": {
            "required_any": python_any,
            "configured": [
                name for name in python_any
                if importlib.util.find_spec(name) is not None
            ],
        },
        "python_optional": {
            "known": python_optional,
            "configured": [
                name for name in python_optional
                if importlib.util.find_spec(name) is not None
            ],
            "missing": [
                name for name in python_optional
                if importlib.util.find_spec(name) is None
            ],
        },
        "auth_any_env": {
            "required_any": auth_any_env,
            "configured": [name for name in auth_any_env if os.environ.get(name)],
            "missing": [name for name in auth_any_env if not os.environ.get(name)],
        },
        "optional_auth_env": {
            "known": optional_auth_env,
            "configured": [name for name in optional_auth_env if os.environ.get(name)],
            "missing": [name for name in optional_auth_env if not os.environ.get(name)],
        },
    }


def command_list(args: argparse.Namespace) -> dict[str, Any]:
    registry = load_common(args)
    platforms = registry.get("platforms", {})
    return {
        "success": True,
        "command": "list",
        "data": {
            "platforms": platforms,
            "groups": platform_groups(registry),
        },
        "errors": [],
    }


def command_doctor(args: argparse.Namespace) -> dict[str, Any]:
    registry = load_common(args)
    platforms = registry.get("platforms", {})
    requested = set(args.platforms or platforms.keys())
    checks = []
    for name, config in platforms.items():
        if name not in requested or not isinstance(config, dict):
            continue
        if config.get("status") != "available":
            status = "skip"
            message = f"status={config.get('status')}"
        else:
            error = check_runtime(config)
            status = "fail" if error else "pass"
            message = error["message"] if error else "ready"
        checks.append({
            "platform": name,
            "status": status,
            "message": message,
            "auth": config.get("auth"),
            "runtime": _runtime_diagnostics(config),
        })
    return {
        "success": not any(item["status"] == "fail" for item in checks),
        "command": "doctor",
        "data": {
            "environment": {
                "requested_env_file": args.env_file,
                "loaded_env_file": getattr(args, "_resolved_env_file", None),
                "loaded_env_files": getattr(args, "_resolved_env_files", []),
            },
            "checks": checks,
            "summary": {
                "pass": len([item for item in checks if item["status"] == "pass"]),
                "fail": len([item for item in checks if item["status"] == "fail"]),
                "skip": len([item for item in checks if item["status"] == "skip"]),
            },
        },
        "errors": [],
    }


async def command_platform(args: argparse.Namespace) -> dict[str, Any]:
    registry = load_common(args)
    task = normalize_task(args.platform, args.query, args.limit, parse_params(args.param))
    result = await run_tasks([task], registry, args.max_concurrency)
    return {
        "success": result["success"],
        "command": "platform",
        "query": args.query,
        "data": result["data"],
        "duration_ms": result["duration_ms"],
        "errors": [],
    }


async def command_search(args: argparse.Namespace) -> dict[str, Any]:
    registry = load_common(args)
    groups = platform_groups(registry)
    if args.platforms:
        platforms = args.platforms
    else:
        group = args.group or "all"
        if group not in groups:
            raise SystemExit(f"未知平台组: {group}；可用平台组: {', '.join(sorted(groups))}")
        platforms = groups[group]
    known = set(registry.get("platforms", {}))
    unknown = [platform for platform in platforms if platform not in known]
    if unknown:
        raise SystemExit(f"未知平台: {', '.join(unknown)}")
    tasks = [normalize_task(platform, args.query, args.limit, parse_params(args.param)) for platform in platforms]
    result = await run_tasks(tasks, registry, args.max_concurrency)
    return {
        "success": result["success"],
        "command": "search",
        "query": args.query,
        "data": result["data"],
        "duration_ms": result["duration_ms"],
        "errors": [],
    }


async def command_run_tasks(args: argparse.Namespace) -> dict[str, Any]:
    registry = load_common(args)
    document = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if isinstance(document.get("data"), dict) and isinstance(document["data"].get("search_tasks"), list):
        tasks = document["data"]["search_tasks"]
    else:
        tasks = document.get("tasks")
    if not isinstance(tasks, list):
        raise SystemExit("输入必须包含 tasks[] 或 data.search_tasks[]")
    result = await run_tasks(tasks, registry, args.max_concurrency)
    return {
        "success": result["success"],
        "command": "run-tasks",
        "query": None,
        "data": result["data"],
        "duration_ms": result["duration_ms"],
        "errors": [],
    }


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="平台注册表路径")
    common.add_argument("--env-file", default=".env", help="环境变量文件路径")
    common.add_argument("--pretty", action="store_true", help="格式化 JSON 输出")
    common.add_argument("-o", "--output", help="输出 JSON 文件路径")

    parser = argparse.ArgumentParser(
        description="platform-search 命令行工具",
        parents=[common],
        formatter_class=ChineseHelpFormatter,
        add_help=False,
    )
    parser.add_argument("-h", "--help", action="help", help="显示帮助并退出")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser(
        "list",
        help="列出平台能力和平台组",
        parents=[common],
        formatter_class=ChineseHelpFormatter,
        add_help=False,
    )
    list_parser.add_argument("-h", "--help", action="help", help="显示帮助并退出")

    doctor = sub.add_parser(
        "doctor",
        help="检查平台运行依赖和认证状态",
        parents=[common],
        formatter_class=ChineseHelpFormatter,
        add_help=False,
    )
    doctor.add_argument("-h", "--help", action="help", help="显示帮助并退出")
    doctor.add_argument("--platforms", nargs="+", help="只检查指定平台")

    platform = sub.add_parser(
        "platform",
        help="执行单个平台搜索",
        parents=[common],
        formatter_class=ChineseHelpFormatter,
        add_help=False,
    )
    platform.add_argument("-h", "--help", action="help", help="显示帮助并退出")
    platform.add_argument("platform", help="平台名")
    platform.add_argument("query", help="查询词")
    platform.add_argument("--limit", "-l", type=int, default=10, help="最大返回数量")
    platform.add_argument("--param", action="append", help="平台参数，格式为 key=value，可重复")
    platform.add_argument("--max-concurrency", type=int, default=None, help="最大并发平台数")

    search = sub.add_parser(
        "search",
        help="在多个平台执行同一个查询",
        parents=[common],
        formatter_class=ChineseHelpFormatter,
        add_help=False,
    )
    search.add_argument("-h", "--help", action="help", help="显示帮助并退出")
    search.add_argument("query", help="查询词")
    search.add_argument("--platforms", "-p", nargs="+", help="指定平台列表")
    search.add_argument("--group", "-g", help="平台组名")
    search.add_argument("--limit", "-l", type=int, default=10, help="每个平台最大返回数量")
    search.add_argument("--param", action="append", help="平台参数，格式为 key=value，可重复")
    search.add_argument("--max-concurrency", type=int, default=None, help="最大并发平台数")

    run_tasks = sub.add_parser(
        "run-tasks",
        help="执行 JSON 文件中的搜索任务",
        parents=[common],
        formatter_class=ChineseHelpFormatter,
        add_help=False,
    )
    run_tasks.add_argument("-h", "--help", action="help", help="显示帮助并退出")
    run_tasks.add_argument("file", help="任务 JSON 文件")
    run_tasks.add_argument("--max-concurrency", type=int, default=None, help="最大并发平台数")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    started = time.monotonic()
    if args.command == "list":
        document = command_list(args)
    elif args.command == "doctor":
        document = command_doctor(args)
    elif args.command == "platform":
        document = asyncio.run(command_platform(args))
    elif args.command == "search":
        document = asyncio.run(command_search(args))
    elif args.command == "run-tasks":
        document = asyncio.run(command_run_tasks(args))
    else:
        parser.error(f"未知命令: {args.command}")
    document.setdefault("duration_ms", int((time.monotonic() - started) * 1000))
    write_output(document, args.output, args.pretty)
    return 0 if document.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
