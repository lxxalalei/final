"""tests.test_dedup — 跨平台内容级去重引擎测试。

验证 shared/dedup.py 的三种去重策略和处理策略的正确性。

运行方式::

    cd learning-resource-suite
    python -m pytest tests/test_dedup.py -v
    # 或直接运行
    python tests/test_dedup.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# 确保能导入 shared 模块
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from shared.dedup import (
    DedupConfig,
    DedupEngine,
    DedupStrategy,
    MatchType,
    DuplicateGroup,
    # 算法函数
    levenshtein_distance,
    edit_distance_similarity,
    jaccard_similarity,
    tfidf_cosine_similarity,
    title_similarity,
    tokenize,
    normalize_url,
    url_fingerprint,
    compute_file_hash,
    compute_text_hash,
    dedup_resources,
    quick_is_duplicate,
)


# ═══════════════════════════════════════════════════════════════
#  测试辅助
# ═══════════════════════════════════════════════════════════════

_passed = 0
_failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    """断言检查。"""
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [PASS] {name}")
    else:
        _failed += 1
        print(f"  [FAIL] {name} — {detail}")


# ═══════════════════════════════════════════════════════════════
#  测试 1: 编辑距离
# ═══════════════════════════════════════════════════════════════

def test_levenshtein() -> None:
    print("\n══ 测试 1: 编辑距离 ══")

    # 相同字符串
    check(
        "相同字符串编辑距离为0",
        levenshtein_distance("hello", "hello") == 0,
    )

    # 单字符替换
    check(
        "单字符替换",
        levenshtein_distance("cat", "bat") == 1,
    )

    # 插入
    check(
        "单字符插入",
        levenshtein_distance("cat", "cats") == 1,
    )

    # 删除
    check(
        "单字符删除",
        levenshtein_distance("cats", "cat") == 1,
    )

    # 完全不同
    check(
        "完全不同",
        levenshtein_distance("abc", "xyz") == 3,
    )

    # 空字符串
    check(
        "空字符串",
        levenshtein_distance("", "abc") == 3,
    )


def test_edit_distance_similarity() -> None:
    print("\n══ 测试 1b: 编辑距离相似度 ══")

    check(
        "完全一致 → 1.0",
        edit_distance_similarity("hello", "hello") == 1.0,
    )

    check(
        "完全不同 → 较低值",
        edit_distance_similarity("abc", "xyz") == 0.0,
    )

    sim = edit_distance_similarity("三年级数学", "3年级数学")
    check(
        "中文数字变体（仅差1字符 → sim=0.80）",
        abs(sim - 0.80) < 0.01,
        f"sim={sim:.2f}",
    )


# ═══════════════════════════════════════════════════════════════
#  测试 2: Jaccard 相似度
# ═══════════════════════════════════════════════════════════════

def test_jaccard() -> None:
    print("\n══ 测试 2: Jaccard 相似度 ══")

    check(
        "完全相同的 token 集 → 1.0",
        jaccard_similarity(["a", "b", "c"], ["a", "b", "c"]) == 1.0,
    )

    check(
        "完全不重叠 → 0.0",
        jaccard_similarity(["a", "b"], ["c", "d"]) == 0.0,
    )

    # 部分重叠
    sim = jaccard_similarity(["a", "b", "c"], ["a", "b", "d"])
    check(
        "部分重叠（2/4 = 0.5）",
        abs(sim - 0.5) < 0.01,
        f"sim={sim:.2f}",
    )

    # 空集
    check(
        "双空集 → 1.0",
        jaccard_similarity([], []) == 1.0,
    )


# ═══════════════════════════════════════════════════════════════
#  测试 3: TF-IDF 余弦相似度
# ═══════════════════════════════════════════════════════════════

def test_tfidf() -> None:
    print("\n══ 测试 3: TF-IDF 余弦相似度 ══")

    check(
        "完全相同 → 1.0",
        abs(tfidf_cosine_similarity(["数学", "练习"], ["数学", "练习"]) - 1.0) < 0.01,
    )

    check(
        "完全不重叠 → 0.0",
        tfidf_cosine_similarity(["a", "b"], ["c", "d"]) == 0.0,
    )

    # 词序无关
    sim1 = tfidf_cosine_similarity(["数学", "练习", "题"], ["数学", "练习", "题"])
    sim2 = tfidf_cosine_similarity(["数学", "练习", "题"], ["题", "练习", "数学"])
    check(
        "词序无关",
        abs(sim1 - sim2) < 0.01,
        f"sim1={sim1:.2f}, sim2={sim2:.2f}",
    )


# ═══════════════════════════════════════════════════════════════
#  测试 4: 分词
# ═══════════════════════════════════════════════════════════════

def test_tokenize() -> None:
    print("\n══ 测试 4: 分词 ══")

    tokens = tokenize("数学练习题")
    check(
        "中文逐字分词",
        tokens == ["数", "学", "练", "习", "题"],
        f"tokens={tokens}",
    )

    tokens = tokenize("math practice")
    check(
        "英文按词分词",
        tokens == ["math", "practice"],
        f"tokens={tokens}",
    )

    tokens = tokenize("数学 Grade 3")
    check(
        "中英混合",
        "数" in tokens and "学" in tokens and "grade" in tokens and "3" in tokens,
        f"tokens={tokens}",
    )

    check(
        "空字符串",
        tokenize("") == [],
    )


# ═══════════════════════════════════════════════════════════════
#  测试 5: 标题相似度
# ═══════════════════════════════════════════════════════════════

def test_title_similarity() -> None:
    print("\n══ 测试 5: 标题相似度 ══")

    check(
        "完全相同 → 1.0",
        title_similarity("三年级数学练习题", "三年级数学练习题") == 1.0,
    )

    sim = title_similarity("三年级数学练习题", "三年级数学练习")
    check(
        "仅少一个字（高相似）",
        sim >= 0.85,
        f"sim={sim:.2f}",
    )

    sim = title_similarity("三年级数学练习题", "恐龙百科全书")
    check(
        "完全不同主题（低相似）",
        sim < 0.3,
        f"sim={sim:.2f}",
    )

    sim = title_similarity("数学练习题三年级", "三年级数学练习题")
    check(
        "词序不同但内容相同（高相似）",
        sim >= 0.85,
        f"sim={sim:.2f}",
    )

    sim = title_similarity("小学三年级四则运算", "小学3年级四则运算")
    check(
        "数字中文变体（高相似）",
        sim >= 0.8,
        f"sim={sim:.2f}",
    )


# ═══════════════════════════════════════════════════════════════
#  测试 6: URL 标准化
# ═══════════════════════════════════════════════════════════════

def test_url_normalize() -> None:
    print("\n══ 测试 6: URL 标准化 ══")

    # 追踪参数应被去除（所有参数都是追踪参数）
    url1 = "https://www.bilibili.com/video/BV1xx?utm_source=google&spm=a1z"
    url2 = "https://www.bilibili.com/video/BV1xx"
    fp1 = url_fingerprint(url1)
    fp2 = url_fingerprint(url2)
    check(
        "追踪参数不影响指纹（全部为追踪参数）",
        fp1 == fp2,
        f"fp1={fp1[:8]}, fp2={fp2[:8]}",
    )

    # 混合参数：非追踪参数保留，仅追踪参数去除
    url_m1 = "https://example.com/page?utm_source=x&p=123"
    url_m2 = "https://example.com/page?utm_source=y&p=123"
    check(
        "非追踪参数保留，追踪参数去除",
        url_fingerprint(url_m1) == url_fingerprint(url_m2),
    )

    # 域名大小写
    url_a = "https://WWW.Bilibili.com/video/BV1xx"
    url_b = "https://www.bilibili.com/video/BV1xx"
    check(
        "域名大小写不敏感",
        url_fingerprint(url_a) == url_fingerprint(url_b),
    )

    # 尾部斜杠
    url_c = "https://example.com/path/"
    url_d = "https://example.com/path"
    check(
        "尾部斜杠归一",
        url_fingerprint(url_c) == url_fingerprint(url_d),
    )

    # fragment 去除
    url_e = "https://example.com/page#section1"
    url_f = "https://example.com/page#section2"
    check(
        "fragment 不影响指纹",
        url_fingerprint(url_e) == url_fingerprint(url_f),
    )

    # 有意义的参数保留
    url_g = "https://example.com/page?id=123"
    url_h = "https://example.com/page?id=456"
    check(
        "有意义的参数区分",
        url_fingerprint(url_g) != url_fingerprint(url_h),
    )


# ═══════════════════════════════════════════════════════════════
#  测试 7: 文件 hash
# ═══════════════════════════════════════════════════════════════

def test_file_hash() -> None:
    print("\n══ 测试 7: 文件/文本 hash ══")

    # 文本 hash
    h1 = compute_text_hash("hello world", "md5")
    h2 = compute_text_hash("hello world", "md5")
    h3 = compute_text_hash("helloWorld", "md5")
    check(
        "相同文本相同 hash",
        h1 == h2,
    )
    check(
        "不同文本不同 hash",
        h1 != h3,
    )

    # 文件 hash
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write("test content for hashing")
        tmp_path = f.name

    try:
        fh1 = compute_file_hash(tmp_path, "md5")
        fh2 = compute_file_hash(tmp_path, "sha256")
        check(
            "文件 hash 成功计算",
            fh1 is not None and len(fh1) == 32,  # md5 hex 长度
        )
        check(
            "不同算法不同结果",
            fh1 != fh2,
        )
    finally:
        os.unlink(tmp_path)

    # 不存在的文件
    check(
        "不存在文件 → None",
        compute_file_hash("/nonexistent/file.txt") is None,
    )


# ═══════════════════════════════════════════════════════════════
#  测试 8: DedupEngine 单条检查
# ═══════════════════════════════════════════════════════════════

def test_engine_check() -> None:
    print("\n══ 测试 8: DedupEngine.check() ══")

    engine = DedupEngine()

    existing = [
        {
            "resource_id": "bilibili:BV1xx411c7mD",
            "title": "三年级数学四则混合运算系统讲解",
            "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
            "quality_level": "A",
        },
        {
            "resource_id": "smartedu:res_001",
            "title": "国家中小学智慧教育平台数学课件",
            "source_url": "https://www.smartedu.cn/resource/001",
            "quality_level": "S",
        },
    ]

    # 8a: resource_id 完全一致
    new_res = {
        "resource_id": "bilibili:BV1xx411c7mD",
        "title": "三年级数学",
        "source_url": "https://different.url/",
    }
    match = engine.check(new_res, existing)
    check(
        "resource_id 完全一致 → 重复",
        match.is_duplicate and match.match_type == MatchType.RESOURCE_ID,
        f"match={match}",
    )

    # 8b: URL 追踪参数变体
    new_res = {
        "resource_id": "bilibili:BV999",
        "title": "另一个视频",
        "source_url": "https://www.bilibili.com/video/BV1xx411c7mD?utm_source=x",
    }
    match = engine.check(new_res, existing)
    check(
        "URL 追踪参数变体 → URL 重复",
        match.is_duplicate and match.match_type == MatchType.URL,
        f"match={match}",
    )

    # 8c: 标题近似
    new_res = {
        "resource_id": "douyin:vid_123",
        "title": "三年级数学四则混合运算的系统讲解",
        "source_url": "https://www.douyin.com/video/123",
    }
    match = engine.check(new_res, existing)
    check(
        "跨平台标题近似 → 重复",
        match.is_duplicate and match.match_type == MatchType.SIMILAR_TITLE,
        f"match={match}",
    )

    # 8d: 完全不重复
    new_res = {
        "resource_id": "zhihu:answer_456",
        "title": "恐龙百科全书介绍",
        "source_url": "https://www.zhihu.com/answer/456",
    }
    match = engine.check(new_res, existing)
    check(
        "不相关资源 → 不重复",
        not match.is_duplicate,
        f"match={match}",
    )

    # 8e: 内容指纹匹配
    new_res = {
        "resource_id": "generic:abc",
        "title": "某文档",
        "source_url": "https://example.com/doc2",
        "checksum": "md5:abc123def456",
    }
    existing_with_hash = [
        {
            "resource_id": "generic:xyz",
            "title": "另一个文档",
            "source_url": "https://example.com/doc1",
            "checksum": "md5:abc123def456",
        }
    ]
    match = engine.check(new_res, existing_with_hash)
    check(
        "内容指纹匹配 → 精确重复",
        match.is_duplicate and match.match_type == MatchType.EXACT,
        f"match={match}",
    )


# ═══════════════════════════════════════════════════════════════
#  测试 9: 批量去重
# ═══════════════════════════════════════════════════════════════

def test_find_duplicates() -> None:
    print("\n══ 测试 9: DedupEngine.find_duplicates() ══")

    engine = DedupEngine()

    resources = [
        {
            "resource_id": "bilibili:BV1",
            "title": "三年级数学四则运算",
            "source_url": "https://bilibili.com/video/BV1",
            "quality_level": "A",
        },
        {
            "resource_id": "douyin:v1",
            "title": "三年级数学四则运算讲解",
            "source_url": "https://douyin.com/video/1",
            "quality_level": "B",
        },
        {
            "resource_id": "zhihu:a1",
            "title": "恐龙百科",
            "source_url": "https://zhihu.com/answer/1",
            "quality_level": "S",
        },
        {
            "resource_id": "bilibili:BV2",
            "title": "完全不同的内容",
            "source_url": "https://bilibili.com/video/BV2",
            "quality_level": "B",
        },
    ]

    groups = engine.find_duplicates(resources)
    check(
        "检测到 1 个重复组",
        len(groups) == 1,
        f"groups={len(groups)}",
    )
    if groups:
        check(
            "重复组包含 2 个资源",
            len(groups[0].duplicate_ids) == 1,
            f"duplicates={groups[0].duplicate_ids}",
        )
        check(
            "canonical 是质量更高的 bilibili",
            groups[0].canonical_id == "bilibili:BV1",
            f"canonical={groups[0].canonical_id}",
        )


# ═══════════════════════════════════════════════════════════════
#  测试 10: 处理策略
# ═══════════════════════════════════════════════════════════════

def test_strategies() -> None:
    print("\n══ 测试 10: 处理策略 ══")

    resources = [
        {
            "resource_id": "bili:BV1",
            "title": "三年级数学四则运算",
            "source_url": "https://bili.com/1",
            "quality_level": "A",
            "platform_quality_score": 80,
        },
        {
            "resource_id": "douyin:v1",
            "title": "三年级数学四则运算讲解",
            "source_url": "https://douyin.com/1",
            "quality_level": "B",
            "platform_quality_score": 60,
        },
    ]

    # keep_best_quality → 保留 A 级
    config = DedupConfig(strategy="keep_best_quality")
    engine = DedupEngine(config)
    groups = engine.find_duplicates(resources)
    if groups:
        check(
            "keep_best_quality → 保留 A 级",
            groups[0].canonical_id == "bili:BV1",
            f"canonical={groups[0].canonical_id}",
        )
        action = engine.resolve_duplicate_group(groups[0], resources)
        check(
            "keep_best_quality → 移除 B 级",
            "douyin:v1" in action["to_remove"],
            f"to_remove={action['to_remove']}",
        )

    # mark_and_keep_all → 都保留
    config = DedupConfig(strategy="mark_and_keep_all")
    engine = DedupEngine(config)
    groups = engine.find_duplicates(resources)
    if groups:
        action = engine.resolve_duplicate_group(groups[0], resources)
        check(
            "mark_and_keep_all → 不移除",
            len(action["to_remove"]) == 0,
            f"to_remove={action['to_remove']}",
        )
        check(
            "mark_and_keep_all → 标记重复",
            "douyin:v1" in action["to_mark"],
            f"to_mark={action['to_mark']}",
        )


# ═══════════════════════════════════════════════════════════════
#  测试 11: 归档前检查
# ═══════════════════════════════════════════════════════════════

def test_check_before_archive() -> None:
    print("\n══ 测试 11: check_before_archive() ══")

    engine = DedupEngine()

    library_index = {
        "version": "2.1",
        "resources": [
            {
                "resource_id": "bilibili:BV1xx",
                "title": "三年级数学练习",
                "source_url": "https://bilibili.com/video/BV1xx",
                "quality_level": "A",
            }
        ],
    }

    # 重复资源 → 跳过
    new_res = {
        "resource_id": "douyin:v_new",
        "title": "三年级数学练习讲解",
        "source_url": "https://douyin.com/video/new",
        "quality_level": "B",
    }
    match = engine.check_before_archive(new_res, library_index)
    check(
        "近似重复 → action=skip",
        match.is_duplicate and match._action == "skip",
        f"match={match}",
    )

    # 不重复 → 放行
    new_res = {
        "resource_id": "zhihu:a_new",
        "title": "完全不同的恐龙资源",
        "source_url": "https://zhihu.com/answer/new",
    }
    match = engine.check_before_archive(new_res, library_index)
    check(
        "不重复 → 放行",
        not match.is_duplicate,
    )


# ═══════════════════════════════════════════════════════════════
#  测试 12: 便捷函数
# ═══════════════════════════════════════════════════════════════

def test_convenience_functions() -> None:
    print("\n══ 测试 12: 便捷函数 ══")

    resources = [
        {"resource_id": "a:1", "title": "数学练习", "source_url": "https://a.com/1"},
        {"resource_id": "b:1", "title": "数学练习题", "source_url": "https://b.com/1"},
        {"resource_id": "c:1", "title": "恐龙百科", "source_url": "https://c.com/1"},
    ]

    deduped, groups = dedup_resources(resources)
    check(
        "dedup_resources 减少了数量",
        len(deduped) < len(resources),
        f"{len(deduped)} < {len(resources)}",
    )
    check(
        "检测到重复组",
        len(groups) >= 1,
        f"groups={len(groups)}",
    )

    is_dup = quick_is_duplicate(
        {"resource_id": "d:1", "title": "数学练习题集", "source_url": "https://d.com/1"},
        resources,
    )
    check(
        "quick_is_duplicate 检测近似（数学练习题 ≈ 数学练习题集）",
        is_dup,
    )


# ═══════════════════════════════════════════════════════════════
#  测试 13: 配置
# ═══════════════════════════════════════════════════════════════

def test_config() -> None:
    print("\n══ 测试 13: 配置 ══")

    # 默认配置
    config = DedupConfig()
    check(
        "默认启用",
        config.enabled,
    )
    check(
        "默认策略 keep_best_quality",
        config.strategy == "keep_best_quality",
    )
    check(
        "默认阈值 0.85",
        config.title_similarity_threshold == 0.85,
    )

    # 从字典构造
    config = DedupConfig.from_config_dict({
        "enabled": False,
        "strategy": "mark_and_keep_all",
        "title_similarity_threshold": 0.9,
        "url_tracking_params": ["utm_source", "spm"],
    })
    check(
        "from_config_dict: enabled",
        config.enabled is False,
    )
    check(
        "from_config_dict: strategy",
        config.strategy == "mark_and_keep_all",
    )
    check(
        "from_config_dict: threshold",
        config.title_similarity_threshold == 0.9,
    )
    check(
        "from_config_dict: tracking_params",
        config.url_tracking_params == ("utm_source", "spm"),
    )

    # 关闭去重 → 不检测
    engine = DedupEngine(DedupConfig(enabled=False))
    match = engine.check(
        {"resource_id": "a:1", "title": "test", "source_url": "https://a.com"},
        [{"resource_id": "a:1", "title": "test", "source_url": "https://a.com"}],
    )
    check(
        "enabled=False → 不检测",
        not match.is_duplicate,
    )


# ═══════════════════════════════════════════════════════════════
#  测试 14: 并查集传递性
# ═══════════════════════════════════════════════════════════════

def test_transitivity() -> None:
    print("\n══ 测试 14: 传递性（并查集） ══")

    engine = DedupEngine()

    # A≈B, B≈C → A,B,C 同组
    resources = [
        {"resource_id": "a:1", "title": "数学练习", "source_url": "https://a.com/1"},
        {"resource_id": "b:1", "title": "数学练习题", "source_url": "https://b.com/1"},
        {"resource_id": "c:1", "title": "数学练习题集", "source_url": "https://c.com/1"},
    ]

    groups = engine.find_duplicates(resources)
    check(
        "传递性：3 个资源归为 1 组",
        len(groups) == 1,
        f"groups={len(groups)}",
    )
    if groups:
        check(
            "组内有 2 个重复",
            len(groups[0].duplicate_ids) == 2,
            f"duplicates={groups[0].duplicate_ids}",
        )


# ═══════════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════════

def main() -> int:
    print("═" * 60)
    print("  跨平台内容级去重引擎 — 测试套件")
    print("═" * 60)

    test_levenshtein()
    test_edit_distance_similarity()
    test_jaccard()
    test_tfidf()
    test_tokenize()
    test_title_similarity()
    test_url_normalize()
    test_file_hash()
    test_engine_check()
    test_find_duplicates()
    test_strategies()
    test_check_before_archive()
    test_convenience_functions()
    test_config()
    test_transitivity()

    print("\n" + "═" * 60)
    total = _passed + _failed
    print(f"  结果: {_passed}/{total} 通过, {_failed} 失败")
    print("═" * 60)

    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
