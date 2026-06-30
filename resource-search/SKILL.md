---
name: resource-search
description: 儿童学习资源搜索策略 Skill（阶段二）。当需求理解阶段输出结构化需求后激活，通过五维拆解生成差异化查询指令，选择平台组合并优化各平台关键词，输出搜索任务清单 JSON 文件供下游搜索执行层使用。
agent_created: true
---

# resource-search · 搜索策略

**上游**：resource-intent（读取 `stage1_intent.json` 的 data）
**下游**：resource-platforms（写入 `stage2_search_plan.json`）
**阶段编号**：stage 2

将结构化需求转化为可执行的搜索任务清单：生成多角度查询词、选择平台组合、针对每个平台优化关键词。

---

## 执行前准备

读取 `{session_dir}/manifest.json`，获取本阶段执行所需信息：

- `manifest.stages.stage1.output` → 上游输入文件名（通常是 `stage1_intent.json`）
- `manifest.stages.stage2.output` → 本阶段输出文件名（通常是 `stage2_search_plan.json`）

读取 `{session_dir}/{上游输入文件}` 的 `data` 部分，提取以下字段：

- `core_topic`：核心主题（必选）
- `target_age`：目标年龄范围（必选）
- `grade_level`：年级（可选）
- `theme_type`：主题分类——直接用于平台匹配（必选）
- `difficulty`：难度偏好（必选）
- `format_preferences`：资源形态偏好数组（必选）
- `source_preference`：来源偏好（必选）
- `use_scenario`：使用场景（可选）
- `search_mode`：搜索模式 standard / exhaustive（必选）
- `assumptions`：默认假设清单（可选，透传下游）

---

## 执行步骤

### 第一步：查询指令生成

从 `core_topic` 出发，按五个维度扩展查询，覆盖不同角度和资源形态：

1. **核心主题**：围绕 core_topic 生成精确查询（如"三年级数学练习题"）
2. **资源形态**：按 format_preferences 每种形态分别生成（如视频 → "三年级数学动画讲解"）
3. **受众难度**：结合 target_age + difficulty 生成（如"8-9岁数学入门"）
4. **来源倾向**：按 source_preference 定向（如官方优先 → "国家中小学智慧教育平台 三年级数学"）
5. **使用场景**：结合 use_scenario 生成场景化查询（如"睡前听" → "数学睡前故事音频"）

查询分四级：`core`（3-5 个）> `official`（2-3 个）> `format`（3-5 个）> `longtail`（2-3 个）。

标准模式至少 10 个查询，穷尽模式至少 20 个。每个查询标注 `text`、`tier`、`format_hint`。

> 📖 五维拆解完整词表、主题扩展词表、查询分级示例见 `./references/query-generation-guide.md`

---

### 第二步：平台选择

根据需求选择 3-7 个平台，按优先级排序标注 P0/P1/P2。

选择顺序：
1. **用户指定优先**：source_preference = "官方优先" → 优先 smartedu；"视频平台优先" → 优先 bilibili
2. **主题匹配**：用 `theme_type` 直接匹配平台——

   | theme_type | 第一梯队 |
   |------------|---------|
   | 科普 | bilibili、open163、zhihu |
   | 学科 | smartedu、bilibili |
   | 古诗语文 | bilibili、ximalaya、smartedu |
   | 思维训练 | bilibili、zhihu |
   | 艺术美育 | bilibili、douyin |
   | 习惯品格 | ximalaya、bilibili |
   | 兴趣拓展 | bilibili、zhihu |

3. **形态补充**：format_preferences 含视频加 bilibili/open163，含音频加 ximalaya，含文档加 smartedu，含图文加 zhihu/weibo
4. **通用兜底（必选）**：始终加入 `generic` 平台，用于执行白名单站点的 `site:` 定向查询和通用网页搜索

标准模式 3-5 个专属平台 + generic，穷尽模式 5-7 个专属平台 + generic。

> 📖 平台详细档案、路由速查表见 `./references/platform-profiles.md`

---

### 第三步：各平台关键词优化

同一主题在不同平台搜索关键词风格不同。针对每个选定平台优化查询词，并按 target_age 添加年龄适配词。

**平台关键词风格**：
- bilibili → 加"动画/讲解/课程/合集"
- ximalaya → 加"故事/音频/听/专辑"
- smartedu → 学科名+年级，正式表述
- zhihu → 加"推荐/怎么学/经验"
- douyin → 短、口语化
- weibo → 加"资料/分享"
- open163 → 加"公开课/TED/纪录片"

**年龄适配**：低幼加"启蒙/宝宝"，低年级加"入门/基础"，高年级加"进阶/提高"

每个平台查询数量分配：P0 平台 3-5 个，P1 平台 2-3 个，P2 平台 1-2 个。

> 📖 各平台关键词风格和查询数量分配的完整说明见 `./references/platform-profiles.md`

---

### 第四步：生成搜索任务清单

将前三步结果组装为 search_tasks 数组。每个平台任务包含 `platform_id`、`platform_name`、`priority`（P0/P1/P2）、`queries`（含 text/tier/format_hint）、`target_count`、`search_params`（可选）。

---

### 第五步：写入输出文件

将搜索任务清单写入 `{session_dir}/{manifest.stages.stage2.output}`（通常是 `stage2_search_plan.json`）。

```json
{
  "_meta": {
    "stage": 2,
    "session_id": "从 manifest 继承",
    "skill": "resource-search",
    "created_at": "当前时间 ISO 8601",
    "input_from": "stage1_intent.json"
  },
  "_summary": {
    "platform_count": 4,
    "platforms": ["bilibili", "smartedu", "ximalaya", "zhihu"],
    "query_count": 15,
    "expected_results": 60
  },
  "data": {
    "core_topic": "三年级数学",
    "target_age": "8-9岁",
    "search_mode": "standard",
    "search_tasks": [
      {
        "platform_id": "bilibili",
        "platform_name": "B站",
        "priority": "P0",
        "queries": [
          { "text": "三年级数学动画讲解", "tier": "core", "format_hint": "视频" },
          { "text": "三年级数学练习题讲解", "tier": "format", "format_hint": "视频" }
        ],
        "target_count": 20,
        "search_params": {}
      }
    ],
    "intent_data": {},
    "strategy_notes": "学科类主题，以 smartedu 官方 + bilibili 讲解视频为主力"
  }
}
```

**_summary**（flow 只读这个做调度）：`platform_count`、`platforms`、`query_count`、`expected_results`

**data**（下游 platforms 读这个执行）：`core_topic`、`target_age`、`search_mode`、`search_tasks`（必选）；`intent_data`（原样透传 intent 的 data，供 selector 做质量评估）；`strategy_notes`（可选）

---

## 完成后

### 1. 更新 manifest

将 `manifest.json` 中 `stages.stage2.status` 更新为 `completed`。

### 2. 返回摘要

只返回 `_summary`，不展开完整 search_tasks：

```
✅ 已完成搜索策略制定
📄 输出文件：stage2_search_plan.json
📊 摘要：
- 选定平台：{platform_count} 个
- 平台列表：{platforms}
- 查询总数：{query_count} 个
- 预期召回：{expected_results} 条
```

> 完整任务已写入文件，下游 platforms 会去读并执行。不要在上下文中展开 search_tasks。

---

## 关键原则

- 多角度覆盖同一主题，按资源形态分别生成查询
- 查询有梯度：核心词 → 扩展词 → 长尾词
- 平台选择尊重用户指定优先，主题匹配其次
- generic 通用平台始终加入，保证白名单 official 查询和通用网页搜索一定执行
- 宁多勿漏，下游会负责筛选

---

## 参考资料

- `./references/platform-profiles.md` — 平台总览矩阵、逐平台档案（能力/优势/关键词风格）、路由速查表、查询数量分配
- `./references/query-generation-guide.md` — 五维拆解法、查询四级分类、主题扩展词表、高级搜索语法、质量自检清单
- `./references/site-whitelist.md` — 优质站点白名单（3 类 8 站，无专属 API 的站点）、分品类搜索建议
