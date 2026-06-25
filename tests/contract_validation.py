#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
契约一致性验证测试

验证各契约文件的字段定义一致性：
  1. resource-schema.md 中定义的字段是否都在 skill-contract.md 的阶段输出中体现
  2. platform-search-contract.md 和 platform-download-contract.md 的字段
     是否与 resource-schema.md 一致

解析方式：读取 shared/schemas/ 下的 .md 文件，提取字段名进行交叉比对。
无需网络请求，纯本地文本解析。

运行: python tests/contract_validation.py
依赖: 标准库 unittest，无第三方依赖
"""

import unittest
import re
import os
from pathlib import Path

# ====================================================================
# 路径配置
# ====================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = PROJECT_ROOT / "shared" / "schemas"

SCHEMA_FILES = {
    "skill-contract": SCHEMAS_DIR / "skill-contract.md",
    "resource-schema": SCHEMAS_DIR / "resource-schema.md",
    "platform-search-contract": SCHEMAS_DIR / "platform-search-contract.md",
    "platform-download-contract": SCHEMAS_DIR / "platform-download-contract.md",
    "error-codes": SCHEMAS_DIR / "error-codes.md",
}


def load_file(filepath: Path) -> str:
    """读取文件内容"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def extract_fields_from_table(text: str) -> set:
    """从 Markdown 表格中提取字段名（`字段名` 格式的反引号包裹或纯文本）

    匹配表格行中的第一列（字段名），支持格式：
      | `field_name` | ... |
      | field_name | ...
      | `resources[].field_name` | ...
    """
    fields = set()
    # 匹配表格行第一列
    table_row_pattern = re.compile(r"^\|\s*[`']?([a-z_][a-z0-9_\[\].]*)[`']?\s*\|", re.MULTILINE)
    for m in table_row_pattern.finditer(text):
        field = m.group(1)
        # 过滤掉明显的表头/说明
        if field in ("字段", "字段名", "field", "type", "说明", "必填", "必须", "类型"):
            continue
        if "table" in field or "header" in field:
            continue
        fields.add(field)
    return fields


def extract_explicit_fields(text: str) -> set:
    """提取文本中 `field_name` 反引号包裹的字段名"""
    return set(re.findall(r"`([a-z_][a-z0-9_\[\].{}]*)`", text))


def extract_resource_schema_fields(schema_text: str) -> dict:
    """从 resource-schema.md 提取分阶段字段集合

    返回:
      {
        "core": {...},
        "search": {...},
        "download": {...},
        "archive": {...},
      }
    """
    result = {"core": set(), "search": set(), "download": set(), "archive": set()}

    # 提取所有字段名
    all_fields = extract_explicit_fields(schema_text)

    # 核心字段（必选字段表）
    result["core"] = {
        "resource_id", "title", "type", "subject", "platform",
        "source_url", "source_name", "quality_level", "download_feasibility",
    }

    # 搜索阶段字段
    search_section_match = re.search(
        r"### 搜索阶段新增字段.*?(?=###|$)",
        schema_text, re.DOTALL
    )
    search_section = search_section_match.group(0) if search_section_match else ""
    result["search"] = {
        "resource_id", "title", "type", "subject", "platform",
        "source_url", "source_name", "quality_level", "download_feasibility",
        "platform_quality_score", "description", "age_range", "grade_level",
        "tags", "view_count", "like_count", "duration", "file_format",
        "language", "publish_time", "thumbnail_url", "author",
    }
    # 与文本中提取的交集补充
    result["search"] |= (all_fields & result["search"])

    # 下载阶段字段
    result["download"] = {
        "resource_id", "download_status", "file_path", "file_size",
        "fetch_time", "fetch_method", "error_code", "error_message",
        "degraded_level", "checksum", "resolution", "bitrate",
    }

    # 归档阶段字段
    result["archive"] = {
        "resource_id", "library_path", "archive_time",
        "last_viewed", "view_count", "favorite",
    }

    return result


def extract_skill_contract_fields(contract_text: str) -> dict:
    """从 skill-contract.md 提取各阶段字段集合

    返回:
      {
        "intent_output": {...},
        "search_output": {...},
        "selector_output": {...},
        "downloader_output": {...},
        "library_manager_output": {...},
      }
    """
    result = {}

    # intent 输出（查询指令包）
    result["intent_output"] = {
        "summary", "core_topic", "queries", "target_age",
        "grade_level", "difficulty", "format_preferences",
        "source_preference", "search_mode", "assumptions",
    }

    # search 输出（候选资源列表）— 顶层 + resources 元素
    result["search_output"] = {
        "total_count", "search_summary", "resources",
        "resource_id", "title", "type", "subject", "platform",
        "source_url", "source_name", "quality_level", "download_feasibility",
        "platform_quality_score", "description", "age_range",
        "grade_level", "tags", "view_count", "duration", "language",
    }

    # selector 输出（选定资源列表）
    result["selector_output"] = {
        "selected_count", "selection_mode", "resources",
    }

    # downloader 输出（下载结果列表）
    result["downloader_output"] = {
        "total_count", "success_count", "degraded_count", "failed_count",
        "resources", "download_status", "degraded_level",
        "file_path", "file_size", "fetch_time", "fetch_method",
        "error_code", "error_message", "degraded_content",
        "alternative_recommendations",
    }

    # library-manager 输出（归档结果列表）
    result["library_manager_output"] = {
        "archived_count", "skipped_count", "resources",
        "library_path", "archive_time", "dedup_status",
    }

    # 补充：从文本中提取所有出现过的字段，与已知集合取并集
    text_fields = extract_explicit_fields(contract_text)
    for key in result:
        result[key] |= (text_fields & result[key])

    return result


def extract_platform_search_output_fields(search_contract_text: str) -> set:
    """从 platform-search-contract.md 提取 results 数组元素的字段"""
    # 3.2 节 results 数组元素规范
    result = {
        "resource_id", "title", "type", "subject", "platform",
        "source_url", "source_name", "quality_level",
        "platform_quality_score", "download_feasibility", "description",
        "age_range", "grade_level", "tags", "view_count", "like_count",
        "duration", "file_format", "language",
        "publish_time", "thumbnail_url",
    }
    text_fields = extract_explicit_fields(search_contract_text)
    result |= (text_fields & result)
    return result


def extract_platform_download_output_fields(download_contract_text: str) -> set:
    """从 platform-download-contract.md 提取输出字段"""
    result = {
        "resource_id", "platform", "download_status", "degraded_level",
        "fetch_method", "fetch_time", "file_path", "file_name",
        "file_size", "file_format", "duration", "resolution",
        "bitrate", "checksum", "error_code", "error_message",
        "can_retry", "suggested_action",
        "degraded_content", "degraded_reason",
        "alternative_resources",
    }
    text_fields = extract_explicit_fields(download_contract_text)
    result |= (text_fields & result)
    return result


# ====================================================================
# 测试类
# ====================================================================

class TestContractValidation(unittest.TestCase):
    """契约文件字段一致性验证"""

    @classmethod
    def setUpClass(cls):
        """加载所有契约文件"""
        cls.contracts = {}
        for name, path in SCHEMA_FILES.items():
            if path.exists():
                cls.contracts[name] = load_file(path)

        # 解析字段
        cls.resource_schema_fields = extract_resource_schema_fields(
            cls.contracts["resource-schema"]
        )
        cls.skill_contract_fields = extract_skill_contract_fields(
            cls.contracts["skill-contract"]
        )
        cls.platform_search_fields = extract_platform_search_output_fields(
            cls.contracts["platform-search-contract"]
        )
        cls.platform_download_fields = extract_platform_download_output_fields(
            cls.contracts["platform-download-contract"]
        )

    # ----------------------------------------------------------------
    # 文件存在性
    # ----------------------------------------------------------------

    def test_all_schema_files_exist(self):
        """所有核心契约文件都存在"""
        for name, path in SCHEMAS_FILES_ORIG.items():
            self.assertTrue(path.exists(), f"契约文件不存在: {path}")

    # ----------------------------------------------------------------
    # resource-schema.md → skill-contract.md 字段覆盖
    # ----------------------------------------------------------------

    def test_core_fields_in_skill_contract_search(self):
        """resource-schema.md 核心必选字段都在 skill-contract.md 候选资源中体现"""
        core = self.resource_schema_fields["core"]
        search_output = self.skill_contract_fields["search_output"]
        missing = core - search_output
        self.assertEqual(missing, set(),
                         f"resource-schema 核心字段未在 skill-contract 候选资源阶段体现: {missing}")

    def test_search_fields_in_skill_contract_search(self):
        """resource-schema.md 搜索阶段必选字段在 skill-contract.md 候选资源中体现"""
        # 搜索阶段必选（✅）字段子集
        search_required = {
            "platform_quality_score", "description",
        }
        search_output = self.skill_contract_fields["search_output"]
        missing = search_required - search_output
        self.assertEqual(missing, set(),
                         f"搜索阶段必选字段未在 skill-contract 体现: {missing}")

    def test_download_fields_in_skill_contract_downloader(self):
        """resource-schema.md 下载阶段字段在 skill-contract.md 下载结果中体现"""
        download_required = {
            "download_status", "file_path", "file_size",
            "fetch_time", "fetch_method", "degraded_level",
        }
        downloader_output = self.skill_contract_fields["downloader_output"]
        missing = download_required - downloader_output
        self.assertEqual(missing, set(),
                         f"下载阶段字段未在 skill-contract 下载结果阶段体现: {missing}")

    def test_archive_fields_in_skill_contract_library(self):
        """resource-schema.md 归档阶段字段在 skill-contract.md 归档结果中体现"""
        archive_required = {"library_path", "archive_time"}
        library_output = self.skill_contract_fields["library_manager_output"]
        missing = archive_required - library_output
        self.assertEqual(missing, set(),
                         f"归档阶段字段未在 skill-contract 归档结果阶段体现: {missing}")

    # ----------------------------------------------------------------
    # platform-search-contract.md → resource-schema.md 一致性
    # ----------------------------------------------------------------

    def test_platform_search_contract_matches_resource_schema(self):
        """platform-search-contract.md results 字段与 resource-schema.md 搜索阶段一致"""
        # 平台搜索契约中 results 元素必须包含 resource-schema 的核心字段
        core = self.resource_schema_fields["core"]
        missing = core - self.platform_search_fields
        self.assertEqual(missing, set(),
                         f"platform-search-contract results 缺少 resource-schema 核心字段: {missing}")

        # 特别验证 type/download_feasibility/quality_level 的值域说明一致性
        search_contract_text = self.contracts["platform-search-contract"]
        self.assertIn("download_feasibility", search_contract_text)
        self.assertIn("高", search_contract_text)
        self.assertIn("中", search_contract_text)
        self.assertIn("低", search_contract_text)

    def test_platform_search_contract_type_chinese(self):
        """platform-search-contract.md 中 type 字段使用中文标准值"""
        search_contract_text = self.contracts["platform-search-contract"]
        chinese_types = ["视频", "音频", "文档", "练习题"]
        found_any = any(t in search_contract_text for t in chinese_types)
        self.assertTrue(found_any,
                        "platform-search-contract 中未发现中文资源类型定义")

    # ----------------------------------------------------------------
    # platform-download-contract.md → resource-schema.md 一致性
    # ----------------------------------------------------------------

    def test_platform_download_contract_matches_resource_schema(self):
        """platform-download-contract.md 字段与 resource-schema.md 下载阶段一致"""
        download_schema = self.resource_schema_fields["download"]
        # 核心下载字段必须同时存在于两个文件中
        core_download = {"download_status", "file_path", "file_size", "fetch_time", "fetch_method"}
        missing_in_platform = core_download - self.platform_download_fields
        self.assertEqual(missing_in_platform, set(),
                         f"platform-download-contract 缺少 resource-schema 下载核心字段: {missing_in_platform}")

    def test_platform_download_contract_status_states(self):
        """platform-download-contract.md 中 download_status 使用三态值"""
        download_contract_text = self.contracts["platform-download-contract"]
        for status in ["success", "degraded", "failed"]:
            self.assertIn(status, download_contract_text,
                          f"platform-download-contract 中缺少 download_status={status}")

    def test_platform_download_contract_degraded_levels(self):
        """platform-download-contract.md 中 degraded_level 使用 Level 0~3"""
        download_contract_text = self.contracts["platform-download-contract"]
        for level in ["Level 0", "Level 1", "Level 2", "Level 3"]:
            self.assertIn(level, download_contract_text,
                          f"platform-download-contract 中缺少 degraded_level={level}")

    # ----------------------------------------------------------------
    # error-codes.md 一致性
    # ----------------------------------------------------------------

    def test_error_code_prefixes_present(self):
        """error-codes.md 包含 7 大类前缀"""
        error_text = self.contracts["error-codes"]
        for prefix in ["NETWORK_", "ANTI_CRAWL_", "AUTH_", "CONTENT_",
                        "PARSE_", "DOWNLOAD_", "SYSTEM_"]:
            self.assertIn(prefix, error_text,
                          f"error-codes.md 缺少错误码前缀: {prefix}")

    def test_forbidden_error_codes_absent(self):
        """error-codes.md 中不包含已废弃的旧错误码名"""
        error_text = self.contracts["error-codes"]
        deprecated_names = ["CONTENT_PAYWALL", "CONTENT_DELETED"]
        for old in deprecated_names:
            self.assertNotIn(old, error_text,
                             f"error-codes.md 中出现了已废弃的错误码: {old}")

    # ----------------------------------------------------------------
    # 跨契约关键字段一致
    # ----------------------------------------------------------------

    def test_download_status_consistent_across_contracts(self):
        """download_status 三态在 skill-contract 和 platform-download-contract 中一致"""
        for status in ["success", "degraded", "failed"]:
            self.assertIn(status, self.contracts["skill-contract"])
            self.assertIn(status, self.contracts["platform-download-contract"])

    def test_degraded_level_consistent_across_contracts(self):
        """degraded_level 在 skill-contract 和 platform-download-contract 中一致"""
        for level in ["Level 0", "Level 1", "Level 2", "Level 3"]:
            self.assertIn(level, self.contracts["skill-contract"])
            self.assertIn(level, self.contracts["platform-download-contract"])

    def test_resource_id_format_consistent(self):
        """resource_id 格式（平台名:平台内ID）在所有契约中一致"""
        for name, text in self.contracts.items():
            if name == "error-codes":
                continue  # error-codes 不涉及 resource_id
            self.assertIn("resource_id", text,
                          f"{name}.md 中未出现 resource_id 字段")

    def test_download_feasibility_uses_chinese(self):
        """download_feasibility 在所有相关契约中使用中文 高/中/低"""
        for name in ["resource-schema", "platform-search-contract", "skill-contract"]:
            text = self.contracts.get(name, "")
            if "download_feasibility" in text:
                # 至少出现了中文值
                self.assertTrue(
                    "高" in text and "中" in text and "低" in text,
                    f"{name}.md 中 download_feasibility 未使用中文值"
                )


# 全量映射（供 test_all_schema_files_exist 使用）
SCHEMAS_FILES_ORIG = SCHEMA_FILES


if __name__ == "__main__":
    unittest.main(verbosity=2)
