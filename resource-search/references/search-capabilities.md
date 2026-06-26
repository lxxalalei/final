# 搜索能力索引与跨平台规范

> 本文件是 resource-search 调度器的快速参考手册。
> 平台详情见 `resource-platforms/references/<平台>.md`。
> 质量评估权威标准见 `shared/schemas/quality-rubric.md`。

---

## 一、7 平台搜索能力矩阵

| 平台 | 资源形态 | 搜索方式 | 认证要求 | 反爬等级 | 分页 | 免费过滤 | 质量评分 | 输出完善度 |
|------|---------|---------|---------|---------|------|---------|---------|-----------|
| bilibili | 视频 | API(bili-api) | 无需 | ⭐⭐⭐⭐ WBI+CDP | ✅ | ❌ | ❌ 靠基类默认 | ⚠️ 差 |
| smartedu | 课件/视频/音频/图片 | API(官方) | Token可选 | ⭐⭐⭐ | ✅ | ❌ | ❌ 靠基类默认 | ⚠️ 中 |
| zhihu | 图文 | API(z_c0) | Cookie | ⭐⭐⭐ | ✅ | ❌ | ❌ 靠基类默认 | ⚠️ 差 |
| douyin | 短视频 | API(f2) | 自动Token | ⭐⭐⭐⭐ ABogus | ✅ | ❌ | ❌ 靠基类默认 | ⚠️ 差 |
| weibo | 图文/短视频 | API(ajax) | Cookie | ⭐⭐⭐ | ✅ | ❌ | ❌ 靠基类默认 | ⚠️ 差 |
| ximalaya | 音频 | API(公开) | 无需 | ⭐ | ✅ | ✅ | ✅ 完整 | ✅ 好 |
| open163 | 视频/公开课 | HTML解析 | 无需 | ⭐ | ❌ | ❌ | ✅ 完整 | ✅ 好 |

### 关键差异

- **ximalaya / open163** 是新接入平台，脚本输出直接符合契约格式，含完整质量评分
- **bilibili / smartedu / zhihu / douyin / weibo** 是早期接入平台，输出用旧字段名（`resource_type`/`source_platform`/`downloadable` 等），靠 `platform_base.py` 的 `_normalize_candidate()` 自动转换
- **所有平台**经基类标准化后，下游收到的 JSON 字段完整

---

## 二、跨平台搜索词分配机制

### 2.1 当前问题

intent 生成 10+ 个差异化查询词，但 `_build_search_cmd()` 只从 intent 取**一个** `keywords` 字段传给平台。不同平台适合不同的搜索词风格。

### 2.2 设计方案

```
resource-intent 输出 intent JSON：
{
  "queries": [
    {"text": "小学古诗 动画",    "category": "core",       "targets": ["bilibili"]},
    {"text": "小学必背古诗词",    "category": "core",       "targets": ["ximalaya", "open163"]},
    {"text": "语文 古诗 三年级",  "category": "official",   "targets": ["smartedu"]},
    {"text": "古诗 朗诵 儿童",    "category": "form_audio", "targets": ["ximalaya"]},
    {"text": "古诗词讲解 小学",    "category": "form_video", "targets": ["bilibili", "open163"]},
    ...
  ]
}
```

**每个查询词带 `targets` 字段**，标明推荐执行的平台。resource-search 调度时：
1. 按平台分组查询词
2. 每个平台可能收到 2-5 个查询词
3. 合并各查询的结果，跨查询去重

### 2.3 平台搜索词适配指南

| 平台 | 搜索词特点 | 推荐查询模式 | 示例 |
|------|-----------|------------|------|
| **bilibili** | 支持中文自然语言，标题匹配为主 | 核心词+形态词 | `"小学古诗 动画"` / `"三年级数学 讲解"` |
| **smartedu** | 按教材目录结构，学科+年级+版本 | 学科+年级+版本 | `"语文 三年级 人教版"` / `"数学 上册"` |
| **zhihu** | 问答式长尾词效果好 | 疑问句/方法类 | `"小学古诗怎么背"` / `"三年级数学学习方法"` |
| **douyin** | 短关键词，话题标签 | 核心词+热门标签 | `"古诗启蒙"` / `"数学思维"` |
| **weibo** | 话题标签搜索 | #话题#格式 | `"#古诗启蒙#"` / `"#小学数学#"` |
| **ximalaya** | 专辑名/主播名，支持免费过滤 | 核心词+儿童/启蒙 | `"小学必背古诗词"` / `"古诗 儿童朗诵"` |
| **open163** | 课程名/讲师名 | 核心词+课程 | `"小学数学"` / `"古诗词 TED"` |

### 2.4 _build_search_cmd 适配方案

`platform_base.py` 的 `_build_search_cmd` 需要支持**多次搜索合并**：

```python
# 当前（单次搜索）
keywords = intent.get("keywords") or intent.get("query")

# 目标（支持多次搜索）
queries = intent.get("queries", [])
if not queries:
    # 向后兼容：单关键词模式
    keywords = intent.get("keywords") or intent.get("query")
    queries = [{"text": keywords, "targets": [self.platform_name]}]

# 过滤出属于本平台的查询
my_queries = [q["text"] for q in queries if self.platform_name in q.get("targets", [])]
if not my_queries:
    my_queries = [q["text"] for q in queries]  # 无 targets 则全搜
```

> ⚠️ 此改动需要后续实现，当前 `_build_search_cmd` 仍为单关键词模式。

---

## 三、质量评分统一框架

### 3.1 当前问题

7 个平台各自有评分逻辑，权重不同，分数不可比：

| 平台 | 评分维度 | 满分 | 等级切分 |
|------|---------|------|---------|
| bilibili | 播放量40%+时长25%+互动15%+制作20% | 100 | 无（靠基类默认B） |
| douyin | 点赞35%+评论15%+收藏15%+内容35% | 100 | 无（靠基类默认B） |
| ximalaya | 基础60+播放+评分+认证+集数+免费 | 100 | S≥90/A≥75/B≥60/C<60 |
| open163 | 基础55+播放+课时+免费 | 100 | S≥85/A≥70/B≥55/C<55 |

### 3.2 统一评分维度

参照 `shared/schemas/quality-rubric.md` 五维评分体系，平台层**只负责数据采集**，评分由调度层统一计算：

| 维度 | 权重 | 数据来源 |
|------|------|---------|
| 内容质量与完整性 | 25% | 时长/集数/是否有完整系列 |
| 适龄匹配度 | 25% | 标题/标签中的年级信息 |
| 权威可信度 | 20% | 平台性质（官方/认证/UGC） |
| 可获取性 | 20% | 免费/付费/下载可行性 |
| 安全与体验 | 10% | 播放量/点赞比/内容安全 |

### 3.3 平台数据采集标准化

每个平台脚本应输出以下**原始数据字段**，供统一评分使用：

| 字段 | 说明 | 评分用途 |
|------|------|---------|
| `view_count` | 播放/浏览量 | 权威可信度参考 |
| `like_count` | 点赞/收藏数 | 安全与体验 |
| `duration` | 时长（秒）或集数 | 内容完整性 |
| `is_free` | 是否免费 | 可获取性 |
| `is_verified` | 是否认证作者/官方 | 权威可信度 |
| `author` | 作者/UP主/主播 | 权威可信度 |

### 3.4 待办：旧平台评分补齐

| 优先级 | 平台 | 需要做的 |
|--------|------|---------|
| P0 | bilibili | 在 `search_videos()` 输出 quality_level + platform_quality_score + download_feasibility + subject |
| P0 | douyin | 在 `output_candidates()` 输出上述字段 |
| P1 | zhihu | 同上 |
| P1 | weibo | 同上 |
| P2 | smartedu | 已有 stage/grade/subject，补 quality_level + score |

> 参考 ximalaya/open163 的 `_compute_quality()` 函数实现。

---

## 四、搜索安全过滤

### 4.1 初筛过滤规则（resource-search 执行）

搜索结果返回后，在质量评估前执行以下过滤：

| 过滤规则 | 说明 |
|---------|------|
| 境外网站过滤 | 移除非 .cn 域名、非国内平台的链接 |
| 广告/营销过滤 | 标题含"加微信""免费领""点击下载"等 |
| 内容安全过滤 | 暴力/色情/恐怖关键词黑名单 |
| 付费内容标注 | `is_free=false` 的标注但不过滤（免费部分可看的保留） |
| 语言过滤 | 非中文内容移除（英语学习类除外） |
| 重复内容去重 | URL指纹 → 标题指纹 → 内容相似度 |

### 4.2 儿童安全增强建议

- 对 UGC 平台（bilibili/douyin/weibo）结果加强关键词过滤
- 对官方平台（smartedu/open163）降低过滤强度
- 标题含敏感词的标记 `safe=False`，由 selector 决定是否展示

---

*文档版本：v1.0 | 创建日期：2026-06-25*
