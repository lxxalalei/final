#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目健康检查脚本。

对 learning-resource-suite 项目执行 5 类完整性检查，输出格式化报告。
  a. 目录结构完整性 — 关键目录是否存在
  b. 文件存在性     — 关键文件是否到位
  c. 契约一致性     — SKILL.md 中引用的契约路径是否有效
  d. Python 依赖    — resource-platforms/scripts/shared 模块是否可解析
  e. 平台注册       — search-registry 中可用平台是否有真实 adapter

退出码：
  0 — 全部 PASS（允许 WARN）
  1 — 存在 FAIL

用法：
  python scripts/healthcheck.py
  python scripts/healthcheck.py --quiet     # 只输出摘要
  python scripts/healthcheck.py --no-deps   # 跳过 pip 依赖检查（仅检查标准库 import）
"""

from __future__ import annotations

import re
import sys
import ast
import json
import importlib
from pathlib import Path
from datetime import datetime

# ════════════════════════════════════════════════════════════════
#  路径配置
# ════════════════════════════════════════════════════════════════

# scripts/healthcheck.py → 项目根 = scripts/ 的上级
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ════════════════════════════════════════════════════════════════
#  检查项定义
# ════════════════════════════════════════════════════════════════

# (a) 关键目录
CRITICAL_DIRS = [
    "learning-resource-flow",
    "resource-intent",
    "resource-search",
    "resource-selector",
    "resource-downloader",
    "library-manager",
    "resource-platforms",
    "resource-platforms/scripts",
    "resource-platforms/scripts/shared",
    "resource-platforms/references",
    "config",
    "tests",
]

# (b) 关键文件
CRITICAL_FILES = [
    # Skill entrypoints
    "learning-resource-flow/SKILL.md",
    "resource-intent/SKILL.md",
    "resource-search/SKILL.md",
    "resource-selector/SKILL.md",
    "resource-downloader/SKILL.md",
    "library-manager/SKILL.md",
    "resource-platforms/SKILL.md",
    # self-contained contracts
    "resource-platforms/references/search-interface.md",
    "resource-platforms/references/search-errors.md",
    "resource-platforms/config/search-registry.json",
    "resource-platforms/scripts/run_search_plan.py",
    "resource-selector/references/quality-rubric.md",
    "resource-intent/schemas/input.schema.json",
    "resource-intent/schemas/output.schema.json",
    "resource-intent/scripts/validate_output.py",
    "resource-intent/examples/golden-cases.json",
    "resource-search/schemas/input.schema.json",
    "resource-search/schemas/output.schema.json",
    "resource-search/config/platform-catalog.json",
    "resource-search/scripts/validate_output.py",
    "resource-search/examples/routing-cases.json",
    # shared modules（已迁移至 resource-platforms/scripts/shared/）
    "resource-platforms/scripts/shared/__init__.py",
    "resource-platforms/scripts/shared/search_adapter.py",
    "resource-platforms/scripts/shared/utils.py",
    "resource-platforms/scripts/shared/logger.py",
    "resource-platforms/scripts/bilibili/wbi_sign.py",
    "resource-platforms/scripts/shared/config_loader.py",
    # config files
    "config/settings.example.yaml",
]

# (d) 需要检查 import 的 shared 模块（仅标准库依赖部分）
SHARED_MODULES = [
    "shared.search_adapter",
    "shared.utils",
    "shared.logger",
    "shared.config_loader",
]

# (e) 已接入平台（状态为 ✅ 可用的）
ACTIVE_PLATFORMS = [
    "generic", "bilibili", "smartedu", "zhihu", "douyin", "weibo", "ximalaya", "open163"
]

# (c) 需要扫描契约引用的 SKILL.md 文件列表
SKILL_MD_FILES = [
    "learning-resource-flow/SKILL.md",
    "resource-intent/SKILL.md",
    "resource-search/SKILL.md",
    "resource-selector/SKILL.md",
    "resource-downloader/SKILL.md",
    "library-manager/SKILL.md",
    "resource-platforms/SKILL.md",
    "resource-platforms/references/platforms/bilibili.md",
    "resource-platforms/references/platforms/smartedu.md",
    "resource-platforms/references/platforms/zhihu.md",
    "resource-platforms/references/platforms/douyin.md",
    "resource-platforms/references/platforms/weibo.md",
    "resource-platforms/references/platforms/ximalaya.md",
    "resource-platforms/references/platforms/open163.md",
    "resource-platforms/references/platforms/generic.md",
]

# ════════════════════════════════════════════════════════════════
#  报告数据结构
# ════════════════════════════════════════════════════════════════

class CheckResult:
    """单项检查结果。"""

    __slots__ = ("name", "status", "detail")

    def __init__(self, name: str, status: str, detail: str = ""):
        self.name = name
        self.status = status    # PASS / WARN / FAIL
        self.detail = detail


def _p(path: str) -> Path:
    """拼接项目根路径。"""
    return PROJECT_ROOT / path


# ════════════════════════════════════════════════════════════════
#  检查函数
# ════════════════════════════════════════════════════════════════

def check_directories() -> list[CheckResult]:
    """(a) 检查关键目录是否存在。"""
    results = []
    for d in CRITICAL_DIRS:
        path = _p(d)
        if path.is_dir():
            results.append(CheckResult(f"目录 {d}", "PASS"))
        else:
            results.append(CheckResult(f"目录 {d}", "FAIL", f"目录不存在: {path}"))
    return results


def check_files() -> list[CheckResult]:
    """(b) 检查关键文件是否存在。"""
    results = []
    for f in CRITICAL_FILES:
        path = _p(f)
        if path.is_file():
            results.append(CheckResult(f"文件 {f}", "PASS"))
        else:
            results.append(CheckResult(f"文件 {f}", "FAIL", f"文件不存在: {path}"))
    return results


def check_contract_references() -> list[CheckResult]:
    """(c) 检查 SKILL.md 中是否仍引用已移除的根级 shared/ 契约。

    扫描所有 SKILL.md，提取形如 ``../../shared/xxx`` 或 ``../shared/xxx``
    的相对路径引用，然后以该 SKILL.md 所在目录为基准解析路径，检查文件是否存在。
    """
    results = []

    # 匹配 SKILL.md 中对 shared/ 的相对路径引用
    # 支持格式：
    # 任何命中的根级 shared/schemas 或 shared/config 都属于旧架构残留。
    ref_pattern = re.compile(
        r"`((?:\.\./)*shared/(?:schemas|config)/[^\s`]+)`"
    )

    for skill_rel in SKILL_MD_FILES:
        skill_path = _p(skill_rel)
        if not skill_path.is_file():
            results.append(CheckResult(
                f"契约引用 ({skill_rel})", "WARN",
                f"SKILL.md 本身不存在，跳过"
            ))
            continue

        text = skill_path.read_text(encoding="utf-8")
        refs = ref_pattern.findall(text)
        seen = set()

        for ref in refs:
            if ref in seen:
                continue
            seen.add(ref)

            # 以 SKILL.md 所在目录为基准解析相对路径
            resolved = (skill_path.parent / ref).resolve()
            # 尝试相对于项目根解析（处理 frontmatter 中无 ../ 前缀的情况）
            if not resolved.exists():
                root_resolved = (PROJECT_ROOT / ref).resolve()
                if root_resolved.exists():
                    resolved = root_resolved

            if resolved.exists():
                status = "PASS"
                detail = ""
            else:
                status = "FAIL"
                detail = f"引用路径不存在: {ref} (from {skill_rel})"

            results.append(CheckResult(
                f"契约引用 {ref} ({skill_rel})", status, detail
            ))

    return results


def check_python_imports(skip_deps: bool = False) -> list[CheckResult]:
    """(d) 检查 shared/ Python 模块的 import 是否可解析。

    分两层检查：
    1. AST 层：解析每个模块的 import 语句，判断是否为标准库 / 项目内模块。
    2. 运行时层：importlib 实际导入（在项目根加入 sys.path 后）。
    """
    results = []

    # 确保项目根在 sys.path（shared .py 已迁移至 resource-platforms/scripts/）
    scripts_dir = str(PROJECT_ROOT / "resource-platforms" / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    root_str = str(PROJECT_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    # 标准库模块集合（用于区分第三方依赖）
    stdlib_names = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()

    # 1) AST 静态分析：检查 import 语句
    shared_py_files = {
        "resource-platforms/scripts/shared/search_adapter.py": "shared.search_adapter",
        "resource-platforms/scripts/shared/utils.py": "shared.utils",
        "resource-platforms/scripts/shared/logger.py": "shared.logger",
        "resource-platforms/scripts/shared/config_loader.py": "shared.config_loader",
    }

    third_party_deps = set()

    for rel_path, mod_name in shared_py_files.items():
        py_file = _p(rel_path)
        if not py_file.is_file():
            results.append(CheckResult(
                f"Python模块 {mod_name}", "FAIL",
                f"源文件不存在: {py_file}"
            ))
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError as e:
            results.append(CheckResult(
                f"Python模块 {mod_name}", "FAIL",
                f"语法错误: {e}"
            ))
            continue

        unresolved = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top not in stdlib_names and top != "shared":
                        third_party_deps.add(top)
                        if not skip_deps:
                            unresolved.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                top = node.module.split(".")[0]
                if top not in stdlib_names and top != "shared":
                    third_party_deps.add(top)
                    if not skip_deps:
                        unresolved.append(node.module)

        if unresolved:
            results.append(CheckResult(
                f"Python模块 {mod_name}", "WARN",
                f"引用第三方依赖: {', '.join(sorted(set(unresolved)))} "
                f"(使用 --no-deps 跳过此检查)"
            ))
        else:
            results.append(CheckResult(
                f"Python模块 {mod_name} (AST)", "PASS"
            ))

    # 2) 运行时 import 检查（仅标准库依赖的模块应该直接通过）
    for mod_name in SHARED_MODULES:
        try:
            importlib.import_module(mod_name)
            results.append(CheckResult(
                f"Python模块 {mod_name} (import)", "PASS"
            ))
        except ImportError as e:
            # 如果是第三方依赖缺失，标记为 WARN 而非 FAIL
            err_str = str(e)
            if skip_deps and "No module named" in err_str:
                results.append(CheckResult(
                    f"Python模块 {mod_name} (import)", "WARN",
                    f"第三方依赖缺失（--no-deps 模式跳过）: {e}"
                ))
            else:
                results.append(CheckResult(
                    f"Python模块 {mod_name} (import)", "FAIL",
                    f"Import 失败: {e}"
                ))
        except Exception as e:
            results.append(CheckResult(
                f"Python模块 {mod_name} (import)", "FAIL",
                f"导入时异常: {type(e).__name__}: {e}"
            ))

    return results


def check_platform_registry() -> list[CheckResult]:
    """(e) 检查平台注册表中的 available 搜索入口和平台文档。"""
    results = []

    registry_file = _p("resource-platforms/config/search-registry.json")
    if not registry_file.is_file():
        results.append(CheckResult(
            "平台注册表", "FAIL",
            f"search-registry.json 不存在: {registry_file}"
        ))
        return results

    try:
        registry = json.loads(registry_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [CheckResult("平台注册表", "FAIL", f"无法解析: {exc}")]
    if registry.get("schema_version") != "platform-search-registry/v1":
        return [CheckResult("平台注册表", "FAIL", "必须符合 platform-search-registry/v1")]

    platforms = registry.get("platforms", {})
    available = {
        platform_id: entry for platform_id, entry in platforms.items()
        if isinstance(entry, dict)
        and entry.get("status") == "available"
    }
    if set(available) != set(ACTIVE_PLATFORMS):
        results.append(CheckResult(
            "平台注册表 available 集合", "FAIL",
            f"期望 {sorted(ACTIVE_PLATFORMS)}，实际 {sorted(available)}"
        ))

    for platform_id, entry in available.items():
        platform_dir = _p(f"resource-platforms/scripts/{platform_id}")
        platform_doc = _p(f"resource-platforms/references/platforms/{platform_id}.md")
        search_entry = _p(f"resource-platforms/{entry.get('entry', '')}")
        if not platform_dir.is_dir():
            results.append(CheckResult(
                f"平台 {platform_id}", "FAIL", f"脚本目录不存在: {platform_dir}"
            ))
        elif not search_entry.is_file():
            results.append(CheckResult(
                f"平台 {platform_id}", "FAIL", f"search_entry 不存在: {search_entry}"
            ))
        elif not platform_doc.is_file():
            results.append(CheckResult(
                f"平台 {platform_id}", "FAIL", f"平台文档不存在: {platform_doc}"
            ))
        else:
            results.append(CheckResult(f"平台 {platform_id}", "PASS"))

    for platform_id, entry in platforms.items():
        if isinstance(entry, dict) and entry.get("status") != "available" and entry.get("entry"):
            results.append(CheckResult(
                f"平台 {platform_id} 非 available", "WARN",
                "非 available 平台配置了 search.entry，请确认状态"
            ))

    catalog_file = _p("resource-search/config/platform-catalog.json")
    try:
        catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        results.append(CheckResult("Search 平台目录", "FAIL", f"无法解析: {exc}"))
        return results
    if catalog.get("schema_version") != "search-platform-catalog/v1":
        results.append(CheckResult("Search 平台目录", "FAIL", "schema_version 必须为 search-platform-catalog/v1"))
        return results

    catalog_platforms = catalog.get("platforms", {})
    if not isinstance(catalog_platforms, dict) or set(catalog_platforms) != set(platforms):
        results.append(CheckResult(
            "Search 与 Platform 平台集合", "FAIL",
            f"catalog={sorted(catalog_platforms) if isinstance(catalog_platforms, dict) else 'invalid'}; registry={sorted(platforms)}"
        ))
        return results

    sync_errors = []
    required_planning_fields = {
        "planning_status", "resource_types", "content_forms", "file_formats", "auth",
        "strengths", "limitations", "query_profile",
    }
    for platform_id, planning in catalog_platforms.items():
        execution = platforms[platform_id]
        if not isinstance(planning, dict) or not required_planning_fields.issubset(planning):
            sync_errors.append(f"{platform_id}: 规划字段不完整")
            continue
        if planning["planning_status"] != execution.get("status"):
            sync_errors.append(f"{platform_id}: search status 不一致")
    if sync_errors:
        results.append(CheckResult("Search 与 Platform 静态配置同步", "FAIL", "; ".join(sync_errors)))
    else:
        results.append(CheckResult("Search 与 Platform 静态配置同步", "PASS"))

    return results


# ════════════════════════════════════════════════════════════════
#  报告格式化与主流程
# ════════════════════════════════════════════════════════════════

def format_report(all_results: list[CheckResult], quiet: bool) -> str:
    """格式化输出报告。"""
    lines = []

    # 统计
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for r in all_results:
        counts[r.status] = counts.get(r.status, 0) + 1
    total = len(all_results)

    # 标题
    lines.append("=" * 70)
    lines.append("  项目健康检查报告 — learning-resource-suite")
    lines.append(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  项目: {PROJECT_ROOT}")
    lines.append("=" * 70)
    lines.append("")

    if not quiet:
        # 详细输出
        for r in all_results:
            icon = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}[r.status]
            line = f"  {icon} [{r.status:4}] {r.name}"
            if r.detail:
                line += f"\n         → {r.detail}"
            lines.append(line)
        lines.append("")

    # 摘要
    lines.append("-" * 70)
    lines.append(f"  检查结果: {total} 项 — "
                 f"✅ PASS: {counts['PASS']}  "
                 f"⚠️  WARN: {counts['WARN']}  "
                 f"❌ FAIL: {counts['FAIL']}")
    lines.append("-" * 70)

    # 总结
    if counts["FAIL"] == 0:
        if counts["WARN"] == 0:
            lines.append("  🎉 所有检查通过，项目状态健康！")
        else:
            lines.append(f"  ✅ 核心检查全部通过，有 {counts['WARN']} 项警告需关注。")
    else:
        lines.append(f"  ❌ 发现 {counts['FAIL']} 项未通过，请修复后重新检查。")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    """主入口，返回退出码（0=全部通过，1=有FAIL）。"""
    import argparse

    parser = argparse.ArgumentParser(
        description="learning-resource-suite 项目健康检查"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="只输出摘要，不显示详细检查项"
    )
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="跳过第三方 pip 依赖检查（仅检查标准库 import）"
    )
    args = parser.parse_args()

    # 执行全部检查
    all_results: list[CheckResult] = []
    all_results.extend(check_directories())
    all_results.extend(check_files())
    all_results.extend(check_contract_references())
    all_results.extend(check_python_imports(skip_deps=args.no_deps))
    all_results.extend(check_platform_registry())

    # 输出报告
    print(format_report(all_results, quiet=args.quiet))

    # 退出码
    has_fail = any(r.status == "FAIL" for r in all_results)
    return 1 if has_fail else 0


if __name__ == "__main__":
    sys.exit(main())
