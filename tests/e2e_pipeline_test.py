#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端集成测试 — 验证 6 阶段数据流贯通

模拟完整数据流：
  阶段一 intent  → 查询指令包（Query Package）
  阶段二 search  → 候选资源列表（Candidate List）
  阶段三 selector → 选定资源列表（Selected List）
  阶段四 downloader → 下载结果列表（Download Result List）
  阶段五 library-manager → 归档结果列表（Archive Result List）
  阶段六 flow → 最终汇总反馈

验证点：
  1. 每阶段输出包含 skill-contract.md 定义的所有必须字段
  2. 字段在各阶段间完整透传（只增不删原则）
  3. resource_id 格式：平台名:平台内ID
  4. download_status 只有 success/degraded/failed 三态
  5. degraded_level 格式 "Level 0"~"Level 3"（带空格）
  6. type 字段值为中文
  7. download_feasibility 字段值为中文 高/中/低

运行: python tests/e2e_pipeline_test.py
依赖: 标准库 unittest，无第三方依赖，无网络请求
"""

import unittest
import copy
import re

# ====================================================================
# 模型层 — 契约常量定义
# ====================================================================

# skill-contract.md 中各阶段必须字段
QUERY_PACKAGE_REQUIRED = [
    "summary", "core_topic", "queries", "target_age", "search_mode", "assumptions",
]

CANDIDATE_LIST_REQUIRED = [
    "total_count", "search_summary", "resources",
]

# 候选资源元素必须字段（search → selector）
CANDIDATE_RESOURCE_REQUIRED = [
    "resource_id", "title", "type", "subject", "platform",
    "source_url", "source_name", "quality_level", "download_feasibility",
]

SELECTED_LIST_REQUIRED = [
    "selected_count", "selection_mode", "resources",
]

DOWNLOAD_RESULT_LIST_REQUIRED = [
    "total_count", "success_count", "degraded_count", "failed_count", "resources",
]

# 下载结果元素必须字段
DOWNLOAD_RESULT_RESOURCE_REQUIRED = [
    "download_status", "degraded_level",
]

ARCHIVE_RESULT_LIST_REQUIRED = [
    "archived_count", "skipped_count", "resources",
]

# 归档结果元素必须字段
ARCHIVE_RESOURCE_REQUIRED = [
    "library_path", "archive_time",
]

# 允许的枚举值
VALID_DOWNLOAD_STATUS = {"success", "degraded", "failed"}
VALID_DEGRADED_LEVELS = {"Level 0", "Level 1", "Level 2", "Level 3"}
VALID_QUALITY_LEVELS = {"S", "A", "B", "C"}
VALID_FEASIBILITY = {"高", "中", "低"}
VALID_RESOURCE_TYPES = {
    "练习题", "视频", "音频", "绘本", "课件", "文档", "图片", "软件", "活动", "合集", "其他",
}
VALID_SELECTION_MODES = {"manual", "all", "by_type", "by_quality"}
VALID_SEARCH_MODES = {"standard", "exhaustive"}
VALID_QUERY_TIERS = {"core", "official", "format", "longtail"}

# resource_id 格式：平台名:平台内ID
RESOURCE_ID_PATTERN = re.compile(r"^[a-z]+:[^\s:]+$")

# 已接入平台标识
VALID_PLATFORMS = {
    "bilibili", "ximalaya", "smartedu", "baiduwenku", "zhihu",
    "xiaohongshu", "douyin", "open163", "cctv", "generic",
}


# ====================================================================
# 阶段模拟函数 — 每个函数模拟一个 Skill 的输入输出
# ====================================================================

def stage1_intent(user_need: str) -> dict:
    """阶段一：resource-intent → 输出查询指令包（Query Package）"""
    return {
        "summary": "为小学三年级学生寻找数学四则混合运算相关学习资源",
        "core_topic": "四则混合运算",
        "queries": [
            {"text": "小学三年级 四则混合运算 讲解", "tier": "core"},
            {"text": "四则混合运算 练习题 含答案", "tier": "core"},
            {"text": "人教版 三年级数学 混合运算 课件", "tier": "official"},
            {"text": "四则运算顺序 动画讲解", "tier": "format", "format_hint": "视频"},
            {"text": "混合运算易错题 口算", "tier": "longtail"},
        ],
        "target_age": "8-9岁（假设三年级）",
        "grade_level": "小学三年级",
        "difficulty": "入门",
        "format_preferences": ["视频", "练习题"],
        "source_preference": "不限",
        "search_mode": "standard",
        "assumptions": [
            "假设用户指的是小学三年级（约8-9岁）",
            "假设需要的是国内教材体系（人教版）",
            "假设用户希望免费资源",
        ],
    }


def stage2_search(query_package: dict) -> dict:
    """阶段二：resource-search → 消费查询指令包，输出候选资源列表（Candidate List）"""
    resources = [
        {
            "resource_id": "bilibili:BV1xx411c7mD",
            "title": "小学三年级数学四则混合运算系统讲解",
            "type": "视频",
            "subject": "数学",
            "platform": "bilibili",
            "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
            "source_name": "B站",
            "quality_level": "A",
            "download_feasibility": "中",
            "platform_quality_score": 82,
            "description": "系统讲解四则混合运算的顺序和技巧，共12集，动画形式",
            "age_range": "7-9岁",
            "grade_level": "小学三年级",
            "tags": ["四则运算", "混合运算", "动画讲解", "系统课程"],
            "view_count": 125000,
            "like_count": 3200,
            "duration": "120分钟（共12集）",
            "language": "中文",
        },
        {
            "resource_id": "bilibili:BV2yy333d8nE",
            "title": "四则混合运算练习题50道（含详细解析）",
            "type": "练习题",
            "subject": "数学",
            "platform": "bilibili",
            "source_url": "https://www.bilibili.com/video/BV2yy333d8nE",
            "source_name": "B站",
            "quality_level": "S",
            "download_feasibility": "高",
            "platform_quality_score": 90,
            "description": "50道脱式计算练习题，带完整答案和解析过程",
            "age_range": "7-10岁",
            "grade_level": "小学三年级",
            "tags": ["四则运算", "练习题", "含答案", "脱式计算"],
            "view_count": 89000,
            "language": "中文",
        },
        {
            "resource_id": "smartedu:res-abc12345",
            "title": "人教版三年级数学上册·混合运算单元课件",
            "type": "课件",
            "subject": "数学",
            "platform": "smartedu",
            "source_url": "https://www.smartedu.cn/resource/res-abc12345",
            "source_name": "国家中小学智慧教育平台",
            "quality_level": "S",
            "download_feasibility": "高",
            "platform_quality_score": 95,
            "description": "官方课件，对应人教版三年级上册混合运算单元，可直接下载PDF",
            "age_range": "8-9岁",
            "grade_level": "小学三年级",
            "tags": ["混合运算", "课件", "人教版", "官方资源"],
            "language": "中文",
        },
        {
            "resource_id": "zhihu:answer-67890",
            "title": "如何教孩子理解四则混合运算的顺序",
            "type": "文档",
            "subject": "数学",
            "platform": "zhihu",
            "source_url": "https://www.zhihu.com/question/123456/answer/67890",
            "source_name": "知乎",
            "quality_level": "B",
            "download_feasibility": "高",
            "platform_quality_score": 68,
            "description": "家长分享的教学经验，图文并茂讲解运算顺序的教法",
            "age_range": "7-10岁",
            "tags": ["教学方法", "四则运算", "家长指南"],
            "view_count": 15000,
            "language": "中文",
        },
        {
            "resource_id": "douyin:v-abcdef12",
            "title": "3分钟搞懂混合运算口诀（动画短视频）",
            "type": "视频",
            "subject": "数学",
            "platform": "douyin",
            "source_url": "https://www.douyin.com/video/abcdef12",
            "source_name": "抖音",
            "quality_level": "B",
            "download_feasibility": "低",
            "platform_quality_score": 62,
            "description": "用口诀方式帮助孩子记忆运算顺序，短小精悍",
            "age_range": "6-9岁",
            "duration": "3分钟",
            "language": "中文",
        },
    ]

    return {
        "total_count": len(resources),
        "search_summary": (
            "查询5组关键词，调用3个平台（bilibili/smartedu/zhihu/douyin），"
            "召回18条，初筛后12条，最终保留5条高质量候选"
        ),
        "resources": resources,
    }


def stage3_selector(candidate_list: dict) -> dict:
    """阶段三：resource-selector → 消费候选列表，输出选定列表（Selected List）

    关键：必须完整透传阶段二 resources 的所有字段，只增不减。
    """
    # 模拟用户选了前3条（高优先级）
    selected = copy.deepcopy(candidate_list["resources"][:3])
    return {
        "selected_count": len(selected),
        "selection_mode": "by_quality",
        "resources": selected,
    }


def stage4_downloader(selected_list: dict) -> dict:
    """阶段四：resource-downloader → 消费选定列表，输出下载结果列表（Download Result List）

    关键：每个资源透传上游全部字段，新增 download_status / degraded_level 等。
    """
    results = []
    for i, res in enumerate(copy.deepcopy(selected_list["resources"])):
        result = copy.deepcopy(res)  # 完整透传上游字段
        if i == 0:
            # 成功下载
            result["download_status"] = "success"
            result["degraded_level"] = "Level 0"
            result["file_path"] = "下载/B站-四则混合运算讲解.mp4"
            result["file_size"] = 256000000
            result["fetch_time"] = "2026-06-25T10:00:00Z"
            result["fetch_method"] = "yt_dlp"
        elif i == 1:
            # 降级下载（Level 1）
            result["download_status"] = "degraded"
            result["degraded_level"] = "Level 1"
            result["degraded_content"] = "仅获取到前20道题目的PDF预览版"
            result["fetch_time"] = "2026-06-25T10:02:00Z"
            result["fetch_method"] = "scrape"
            result["error_code"] = "CONTENT_PREMIUM_ONLY"
            result["error_message"] = "完整版需会员，已降级保存预览"
        else:
            # 下载失败
            result["download_status"] = "failed"
            result["degraded_level"] = "Level 3"
            result["fetch_time"] = "2026-06-25T10:03:00Z"
            result["fetch_method"] = "api"
            result["error_code"] = "CONTENT_NOT_FOUND"
            result["error_message"] = "课件资源不存在或已被删除"
            result["alternative_recommendations"] = [
                {"title": "替代课件推荐", "source_url": "https://example.com/alt"}
            ]
        results.append(result)

    success = sum(1 for r in results if r["download_status"] == "success")
    degraded = sum(1 for r in results if r["download_status"] == "degraded")
    failed = sum(1 for r in results if r["download_status"] == "failed")

    return {
        "total_count": len(results),
        "success_count": success,
        "degraded_count": degraded,
        "failed_count": failed,
        "resources": results,
    }


def stage5_library_manager(download_result_list: dict) -> dict:
    """阶段五：library-manager → 消费下载结果，输出归档结果列表（Archive Result List）

    关键：透传上游字段，新增 library_path / archive_time / dedup_status。
    """
    archived = []
    skipped = 0
    for i, res in enumerate(copy.deepcopy(download_result_list["resources"])):
        result = copy.deepcopy(res)
        result["library_path"] = f"数学/小学三年级/四则混合运算/{res['title']}"
        result["archive_time"] = "2026-06-25T11:00:00Z"
        if res["download_status"] == "failed":
            result["dedup_status"] = "skipped"
            skipped += 1
        else:
            result["dedup_status"] = "new"
        archived.append(result)

    archived_count = sum(1 for r in archived if r.get("dedup_status") == "new")

    return {
        "archived_count": archived_count,
        "skipped_count": skipped,
        "resources": archived,
    }


def stage6_flow_feedback(archive_result_list: dict) -> dict:
    """阶段六：learning-resource-flow → 最终汇总反馈"""
    total = len(archive_result_list["resources"])
    success = archive_result_list["archived_count"]
    return {
        "summary": (
            f"共处理 {total} 条资源，成功归档 {success} 条，"
            f"跳过 {archive_result_list['skipped_count']} 条"
        ),
        "stages_completed": 6,
    }


# ====================================================================
# 测试类
# ====================================================================

class TestE2EPipeline(unittest.TestCase):
    """端到端数据流贯通测试"""

    @classmethod
    def setUpClass(cls):
        """运行完整 6 阶段流水线，各阶段输出供测试方法验证"""
        cls.stage1_output = stage1_intent("帮我找小学三年级数学四则混合运算的资源")
        cls.stage2_output = stage2_search(cls.stage1_output)
        cls.stage3_output = stage3_selector(cls.stage2_output)
        cls.stage4_output = stage4_downloader(cls.stage3_output)
        cls.stage5_output = stage5_library_manager(cls.stage4_output)
        cls.stage6_output = stage6_flow_feedback(cls.stage5_output)

    # ----------------------------------------------------------------
    # 阶段一：intent → 查询指令包
    # ----------------------------------------------------------------

    def test_stage1_required_fields(self):
        """阶段一输出包含 skill-contract.md 定义的所有必须字段"""
        for field in QUERY_PACKAGE_REQUIRED:
            self.assertIn(field, self.stage1_output,
                          f"查询指令包缺少必须字段: {field}")

    def test_stage1_queries_structure(self):
        """queries 数组中每个元素含必须子字段"""
        self.assertIsInstance(self.stage1_output["queries"], list)
        self.assertGreater(len(self.stage1_output["queries"]), 0)
        for q in self.stage1_output["queries"]:
            self.assertIn("text", q)
            self.assertIn("tier", q)
            self.assertIn(q["tier"], VALID_QUERY_TIERS,
                          f"queries[].tier 值非法: {q['tier']}")

    def test_stage1_search_mode_valid(self):
        """search_mode 只能为 standard / exhaustive"""
        self.assertIn(self.stage1_output["search_mode"], VALID_SEARCH_MODES)

    def test_stage1_assumptions_is_list(self):
        """assumptions 必须为列表"""
        self.assertIsInstance(self.stage1_output["assumptions"], list)
        self.assertGreater(len(self.stage1_output["assumptions"]), 0)

    # ----------------------------------------------------------------
    # 阶段二：search → 候选资源列表
    # ----------------------------------------------------------------

    def test_stage2_required_fields(self):
        """阶段二输出包含 skill-contract.md 定义的所有必须字段"""
        for field in CANDIDATE_LIST_REQUIRED:
            self.assertIn(field, self.stage2_output,
                          f"候选列表缺少必须字段: {field}")

    def test_stage2_resource_required_fields(self):
        """候选资源元素含全部必须字段"""
        for res in self.stage2_output["resources"]:
            for field in CANDIDATE_RESOURCE_REQUIRED:
                self.assertIn(field, res,
                              f"候选资源缺少必须字段: {field}")

    def test_stage2_total_count_matches(self):
        """total_count 等于 resources 数组长度"""
        self.assertEqual(
            self.stage2_output["total_count"],
            len(self.stage2_output["resources"])
        )

    # ----------------------------------------------------------------
    # 阶段三：selector → 选定资源列表
    # ----------------------------------------------------------------

    def test_stage3_required_fields(self):
        """阶段三输出包含 skill-contract.md 定义的所有必须字段"""
        for field in SELECTED_LIST_REQUIRED:
            self.assertIn(field, self.stage3_output,
                          f"选定列表缺少必须字段: {field}")

    def test_stage3_selected_count_matches(self):
        """selected_count 等于 resources 数组长度"""
        self.assertEqual(
            self.stage3_output["selected_count"],
            len(self.stage3_output["resources"])
        )

    def test_stage3_selection_mode_valid(self):
        """selection_mode 在允许枚举内"""
        self.assertIn(self.stage3_output["selection_mode"], VALID_SELECTION_MODES)

    def test_stage3_passthrough_no_field_loss(self):
        """选定列表中的资源字段数 >= 候选列表对应资源（只增不删）"""
        candidate_resources = {r["resource_id"]: r for r in self.stage2_output["resources"]}
        for sel in self.stage3_output["resources"]:
            rid = sel["resource_id"]
            self.assertIn(rid, candidate_resources)
            original = candidate_resources[rid]
            original_keys = set(original.keys())
            sel_keys = set(sel.keys())
            # 选定列表的 keys 必须是候选列表 keys 的超集
            missing = original_keys - sel_keys
            self.assertEqual(missing, set(),
                             f"resource_id={rid} 在 selector 阶段丢失了字段: {missing}")

    # ----------------------------------------------------------------
    # 阶段四：downloader → 下载结果列表
    # ----------------------------------------------------------------

    def test_stage4_required_fields(self):
        """阶段四输出包含 skill-contract.md 定义的所有必须字段"""
        for field in DOWNLOAD_RESULT_LIST_REQUIRED:
            self.assertIn(field, self.stage4_output,
                          f"下载结果列表缺少必须字段: {field}")

    def test_stage4_count_fields_correct(self):
        """total_count = success + degraded + failed"""
        out = self.stage4_output
        self.assertEqual(out["total_count"], len(out["resources"]))
        expected_total = out["success_count"] + out["degraded_count"] + out["failed_count"]
        self.assertEqual(out["total_count"], expected_total)

    def test_stage4_resource_required_fields(self):
        """下载结果元素含必须字段 download_status / degraded_level"""
        for res in self.stage4_output["resources"]:
            for field in DOWNLOAD_RESULT_RESOURCE_REQUIRED:
                self.assertIn(field, res, f"下载结果缺少必须字段: {field}")

    def test_stage4_passthrough_no_field_loss(self):
        """下载结果中的资源字段数 >= 选定列表对应资源（只增不删）"""
        selected_resources = {r["resource_id"]: r for r in self.stage3_output["resources"]}
        for dl in self.stage4_output["resources"]:
            rid = dl["resource_id"]
            self.assertIn(rid, selected_resources)
            original = selected_resources[rid]
            original_keys = set(original.keys())
            dl_keys = set(dl.keys())
            missing = original_keys - dl_keys
            self.assertEqual(missing, set(),
                             f"resource_id={rid} 在 downloader 阶段丢失了字段: {missing}")

    # ----------------------------------------------------------------
    # 阶段五：library-manager → 归档结果列表
    # ----------------------------------------------------------------

    def test_stage5_required_fields(self):
        """阶段五输出包含 skill-contract.md 定义的所有必须字段"""
        for field in ARCHIVE_RESULT_LIST_REQUIRED:
            self.assertIn(field, self.stage5_output,
                          f"归档结果列表缺少必须字段: {field}")

    def test_stage5_resource_required_fields(self):
        """归档结果元素含必须字段 library_path / archive_time"""
        for res in self.stage5_output["resources"]:
            for field in ARCHIVE_RESOURCE_REQUIRED:
                self.assertIn(field, res, f"归档结果缺少必须字段: {field}")

    def test_stage5_passthrough_no_field_loss(self):
        """归档结果中的资源字段数 >= 下载结果对应资源（只增不删）"""
        download_resources = {r["resource_id"]: r for r in self.stage4_output["resources"]}
        for arch in self.stage5_output["resources"]:
            rid = arch["resource_id"]
            self.assertIn(rid, download_resources)
            original = download_resources[rid]
            original_keys = set(original.keys())
            arch_keys = set(arch.keys())
            missing = original_keys - arch_keys
            self.assertEqual(missing, set(),
                             f"resource_id={rid} 在 library-manager 阶段丢失了字段: {missing}")

    def test_stage5_archive_count_correct(self):
        """archived_count + skipped_count = resources 总数"""
        out = self.stage5_output
        self.assertEqual(
            out["archived_count"] + out["skipped_count"],
            len(out["resources"])
        )

    # ----------------------------------------------------------------
    # 跨阶段：字段格式与枚举值验证
    # ----------------------------------------------------------------

    def test_resource_id_format(self):
        """所有 resource_id 格式：平台名:平台内ID"""
        all_resources = (
            self.stage2_output["resources"]
            + self.stage3_output["resources"]
            + self.stage4_output["resources"]
            + self.stage5_output["resources"]
        )
        for res in all_resources:
            rid = res["resource_id"]
            self.assertRegex(
                rid, RESOURCE_ID_PATTERN,
                f"resource_id 格式不合法（需 平台名:平台内ID）: {rid}"
            )
            platform = rid.split(":")[0]
            self.assertIn(
                platform, VALID_PLATFORMS,
                f"resource_id 平台前缀不在标准列表中: {platform}"
            )

    def test_download_status_three_states(self):
        """download_status 只有 success/degraded/failed 三态"""
        for res in self.stage4_output["resources"]:
            self.assertIn(
                res["download_status"], VALID_DOWNLOAD_STATUS,
                f"download_status 非法值: {res['download_status']}"
            )
        # 归档阶段透传的也要校验
        for res in self.stage5_output["resources"]:
            if "download_status" in res:
                self.assertIn(
                    res["download_status"], VALID_DOWNLOAD_STATUS,
                    f"download_status 非法值: {res['download_status']}"
                )

    def test_degraded_level_format(self):
        """degraded_level 格式为 Level 0~Level 3（带空格）"""
        for res in self.stage4_output["resources"]:
            self.assertIn(
                res["degraded_level"], VALID_DEGRADED_LEVELS,
                f"degraded_level 非法值（需 'Level N' 带空格）: {res['degraded_level']}"
            )

    def test_type_is_chinese(self):
        """type 字段值为中文"""
        for res in self.stage2_output["resources"]:
            self.assertIn(
                res["type"], VALID_RESOURCE_TYPES,
                f"type 值非中文标准类型: {res['type']}"
            )

    def test_download_feasibility_is_chinese(self):
        """download_feasibility 字段值为中文 高/中/低"""
        for res in self.stage2_output["resources"]:
            self.assertIn(
                res["download_feasibility"], VALID_FEASIBILITY,
                f"download_feasibility 值非中文（需 高/中/低）: {res['download_feasibility']}"
            )

    def test_quality_level_valid(self):
        """quality_level 只能为 S/A/B/C"""
        for res in self.stage2_output["resources"]:
            self.assertIn(
                res["quality_level"], VALID_QUALITY_LEVELS,
                f"quality_level 非法值: {res['quality_level']}"
            )

    def test_platform_consistency(self):
        """resource_id 中的平台前缀与 platform 字段一致"""
        for res in self.stage2_output["resources"]:
            platform_prefix = res["resource_id"].split(":")[0]
            self.assertEqual(
                platform_prefix, res["platform"],
                f"resource_id 平台前缀({platform_prefix}) != platform 字段({res['platform']})"
            )

    # ----------------------------------------------------------------
    # 全链路透传验证：阶段二字段贯穿到阶段五
    # ----------------------------------------------------------------

    def test_end_to_end_core_fields_survive(self):
        """核心元数据从阶段二贯穿到阶段五（完整透传原则）"""
        core_fields = [
            "resource_id", "title", "type", "subject", "platform",
            "source_url", "source_name", "quality_level", "download_feasibility",
        ]
        stage5_map = {r["resource_id"]: r for r in self.stage5_output["resources"]}
        stage2_map = {r["resource_id"]: r for r in self.stage2_output["resources"]}

        for rid, stage5_res in stage5_map.items():
            if rid in stage2_map:
                stage2_res = stage2_map[rid]
                for field in core_fields:
                    self.assertIn(field, stage5_res,
                                  f"resource_id={rid} 在阶段五缺少核心字段: {field}")
                    self.assertEqual(
                        stage5_res[field], stage2_res[field],
                        f"resource_id={rid} 字段 {field} 值在透传中发生了变化"
                    )

    def test_full_pipeline_runs_without_error(self):
        """完整 6 阶段流水线无异常运行"""
        self.assertEqual(self.stage6_output["stages_completed"], 6)
        self.assertIsInstance(self.stage6_output["summary"], str)
        self.assertGreater(len(self.stage6_output["summary"]), 0)


# ====================================================================
# 入口
# ====================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
