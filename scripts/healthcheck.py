#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目健康检查脚本。

对 learning-resource-suite 项目执行 5 类完整性检查，输出格式化报告。
  a. 目录结构完整性 — 关键目录是否存在
  b. 文件存在性     — 关键文件是否到位
  c. 契约一致性     — SKILL.md 中引用的契约路径是否有效
  d. Python 依赖    — shared/ 模块 import 是否可解析
  e. 平台映射       — platform-mapping.md 中"可用"平台是否有目录和 SKILL.md

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
    "shared",
    "shared/schemas",
    "shared/config",
    "resource-platforms",
    "resource-platforms/scripts",
    "resource-platforms/scripts/shared",
    "resource-platforms/references",
    "config",
    "_templates",
    "tests",
]

# (b) 关键文件
CRITICAL_FILES = [
    # schemas
    "shared/schemas/resource-schema.md",
    "shared/schemas/error-codes.md",
    "shared/schemas/skill-contract.md",
    "shared/schemas/platform-search-contract.md",
    "shared/schemas/platform-download-contract.md",
    "shared/schemas/quality-rubric.md",
    # config
    "shared/config/platform-mapping.md",
    "shared/config/platform-advantages.md",
    # shared modules（已迁移至 resource-platforms/scripts/shared/）
    "resource-platforms/scripts/shared/__init__.py",
    "resource-platforms/scripts/shared/platform_base.py",
    "resource-platforms/scripts/shared/utils.py",
    "resource-platforms/scripts/shared/logger.py",
    "resource-platforms/scripts/shared/wbi_sign.py",
    "resource-platforms/scripts/shared/config_loader.py",
    # config files
    "config/settings.example.yaml",
    # templates
    "_templates/platform-skill-template.md",
    # docs
    "README.md",
]

# (d) 需要检查 import 的 shared 模块（仅标准库依赖部分）
SHARED_MODULES = [
    "shared.platform_base",
    "shared.utils",
    "shared.logger",
    "shared.wbi_sign",
    "shared.config_loader",
]

# (e) 已接入平台（状态为 ✅ 可用的）
ACTIVE_PLATFORMS = ["bilibili", "smartedu", "zhihu", "douyin", "weibo"]

# (c) 需要扫描契约引用的 SKILL.md 文件列表
SKILL_MD_FILES = [
    "learning-resource-flow/SKILL.md",
    "resource-intent/SKILL.md",
    "resource-search/SKILL.md",
    "resource-selector/SKILL.md",
    "resource-downloader/SKILL.md",
    "library-manager/SKILL.md",
    "resource-platforms/SKILL.md",
    "resource-platforms/references/bilibili.md",
    "resource-platforms/references/smartedu.md",
    "resource-platforms/references/zhihu.md",
    "resource-platforms/references/douyin.md",
    "resource-platforms/references/weibo.md",
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
    """(c) 检查 SKILL.md 中引用的 shared/ 契约路径是否有效。

    扫描所有 SKILL.md，提取形如 ``../../shared/xxx`` 或 ``../shared/xxx``
    的相对路径引用，然后以该 SKILL.md 所在目录为基准解析路径，检查文件是否存在。
    """
    results = []

    # 匹配 SKILL.md 中对 shared/ 的相对路径引用
    # 支持格式：
    #   `../../shared/schemas/platform-search-contract.md`
    #   `../shared/schemas/resource-schema.md`
    #   `shared/schemas/error-codes.md`（frontmatter 内，从根开始）
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
        "resource-platforms/scripts/shared/platform_base.py": "shared.platform_base",
        "resource-platforms/scripts/shared/utils.py": "shared.utils",
        "resource-platforms/scripts/shared/logger.py": "shared.logger",
        "resource-platforms/scripts/shared/wbi_sign.py": "shared.wbi_sign",
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


def check_platform_mapping() -> list[CheckResult]:
    """(e) 检查 platform-mapping.md 中标记为"可用"的平台是否有对应目录和 SKILL.md。

    同时解析映射表，对比实际 platforms/ 目录。
    """
    results = []

    mapping_file = _p("shared/config/platform-mapping.md")
    if not mapping_file.is_file():
        results.append(CheckResult(
            "平台映射表", "FAIL",
            f"platform-mapping.md 不存在: {mapping_file}"
        ))
        return results

    text = mapping_file.read_text(encoding="utf-8")

    # 解析映射表中的行：| `platform_id` | ... | `resource-platforms/scripts/xxx` | ✅ 可用 | ...
    # 提取平台标识和状态
    table_row = re.compile(
        r"\|\s*`([a-z_]+)`\s*\|"     # 平台标识
        r"[^|]*\|"                      # 平台名称
        r"\s*`?(resource-platforms/scripts/[a-z_]+)`?\s*\|"  # Skill 路径
        r"\s*(✅\s*可用|规划中|开发中|不可用)\s*\|"  # 状态
    )

    active_platforms = []
    planned_platforms = []

    for m in table_row.finditer(text):
        platform_id = m.group(1)
        skill_path = m.group(2)
        status = m.group(3)

        if "可用" in status and platform_id != "generic":
            active_platforms.append((platform_id, skill_path))
        elif "规划" in status or "开发" in status:
            planned_platforms.append((platform_id, skill_path))

    # 检查"可用"平台
    for platform_id, skill_path in active_platforms:
        platform_dir = _p(skill_path)
        skill_md = _p(f"resource-platforms/references/{platform_id}.md")

        if not platform_dir.is_dir():
            results.append(CheckResult(
                f"平台映射 {platform_id}", "FAIL",
                f"目录不存在: {skill_path}/"
            ))
        elif not skill_md.is_file():
            results.append(CheckResult(
                f"平台映射 {platform_id}", "FAIL",
                f"SKILL.md 不存在: resource-platforms/references/{platform_id}.md"
            ))
        else:
            results.append(CheckResult(
                f"平台映射 {platform_id}", "PASS"
            ))

    # 检查"规划中"平台（缺少目录是正常的，只做 INFO 提示）
    for platform_id, skill_path in planned_platforms:
        platform_dir = _p(skill_path)
        if not platform_dir.is_dir():
            results.append(CheckResult(
                f"平台映射 {platform_id} (规划中)", "WARN",
                f"尚未创建目录: {skill_path}/"
            ))
        else:
            results.append(CheckResult(
                f"平台映射 {platform_id} (规划中)", "PASS",
                f"目录已存在: {skill_path}/"
            ))

    # 反向检查：resource-platforms/scripts/ 下的平台目录是否都在映射表中
    scripts_platforms_dir = _p("resource-platforms/scripts")
    if scripts_platforms_dir.is_dir():
        mapped_ids = {p[0] for p in active_platforms + planned_platforms}
        for child in sorted(scripts_platforms_dir.iterdir()):
            if child.is_dir() and not child.name.startswith(".") and not child.name.startswith("_") and child.name != "shared":
                if child.name not in mapped_ids:
                    results.append(CheckResult(
                        f"平台映射 {child.name} (未注册)", "WARN",
                        f"resource-platforms/scripts/{child.name}/ 存在但未在映射表中注册"
                    ))

    # 检查已接入平台的适配器脚本
    for platform_id in ACTIVE_PLATFORMS:
        adapter = _p(f"resource-platforms/scripts/{platform_id}/adapter.py")
        if not adapter.is_file():
            results.append(CheckResult(
                f"平台适配器 {platform_id}", "FAIL",
                f"adapter.py 不存在: resource-platforms/scripts/{platform_id}/adapter.py"
            ))
        else:
            results.append(CheckResult(
                f"平台适配器 {platform_id}", "PASS"
            ))

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
    all_results.extend(check_platform_mapping())

    # 输出报告
    print(format_report(all_results, quiet=args.quiet))

    # 退出码
    has_fail = any(r.status == "FAIL" for r in all_results)
    return 1 if has_fail else 0


if __name__ == "__main__":
    sys.exit(main())
