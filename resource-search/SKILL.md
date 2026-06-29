---
name: resource-search
description: 搜索策略生成器。接收需求理解阶段的查询指令组，分析需求特点，判断最佳平台组合，针对每个平台优化搜索关键词，生成结构化的平台搜索任务清单，输出给搜索执行层。
---

# resource-search · 搜索策略生成

## 我是谁

**上游**：resource-intent（从需求理解 Skill 接收查询指令组）
**下游**：resource-platforms（把搜索任务清单传给搜索执行层）
**阶段编号**：stage 2

核心定位：**搜索的军师**——不负责实际去搜，而是负责"想清楚怎么搜效果最好"。
判断什么需求该去哪个平台、每个平台该搜什么关键词、搜多少、用什么策略。

---

## 执行前准备

### 1. 确认参数

从 flow 传入的参数中获取：
- `{session_dir}`：会话目录路径（绝对路径）
- `{input_file}`：上游输入文件名（通常是 `stage1_intent.json`）
- `{output_file}`：本阶段输出文件名（通常是 `stage2_search_plan.json`）

### 2. 读取上游输入

读取 `{session_dir}/{input_file}` 文件，提取其中的 `data` 部分。

> 💡 只需要读 `data`，`_meta` 和 `_summary` 可以忽略（那是给 flow 用的）

**需要读取的字段**（从 data 中）：
- `core_topic`：核心主题（字符串，✅必选）
  - 用于判断主题类型，选择合适的平台
- `queries`：查询列表（数组，✅必选）
  - 每个元素包含 `text`（查询词）、`tier`（优先级）、`format_hint`（形态提示）
  - 这是基础查询，我们会针对各平台进行优化
- `target_age`：目标年龄范围（字符串，✅必选）
  - 用于平台选择和关键词优化
- `grade_level`：年级（字符串，⚠️可选）
- `difficulty`：难度偏好（字符串，✅必选）
  - 入门 / 进阶 / 系统
- `format_preferences`：资源形态偏好（数组，✅必选）
  - 视频 / 音频 / 文档 / 图文
- `source_preference`：来源偏好（字符串，✅必选）
  - 不限 / 官方优先 / 视频平台优先
- `search_mode`：搜索模式（字符串，✅必选）
  - standard：标准模式
  - exhaustive：穷尽模式
- `assumptions`：默认假设清单（数组，⚠️可选，透传给下游）

---

## 执行步骤

### 第一步：需求分析与主题分类

先搞清楚这是什么类型的需求，才能选对平台。

**需要判断的维度**：
1. **主题类型**：科普 / 学科学习 / 古诗语文 / 思维训练 / 艺术美育 / 习惯品格 / 兴趣拓展
2. **资源形态侧重**：视频为主 / 音频为主 / 文档为主 / 图文为主 / 混合
3. **年龄阶段**：低幼（3-6岁）/ 小学低年级（6-9岁）/ 小学高年级（9-12岁）
4. **质量要求**：是否需要官方权威内容 / 是否需要系统性课程 / 是否接受碎片化内容

**判断依据**：
- 从 `core_topic` 判断主题类型
- 从 `format_preferences` 判断形态侧重
- 从 `target_age` 和 `grade_level` 判断年龄阶段
- 从 `difficulty` 和 `source_preference` 判断质量要求

**本步产出**：
- `theme_type`：主题类型
- `age_segment`：年龄分段
- `format_focus`：形态侧重
- `quality_requirement`：质量要求

---

### 第二步：平台选择与优先级排序 ⭐ 核心

根据需求特点，选择最合适的平台组合，并排出优先级。

**选择逻辑**：

1. **用户指定优先**：
   - 如果 `source_preference` 是"官方优先"，优先选 smartedu 等官方平台
   - 如果是"视频平台优先"，优先选 bilibili 等视频平台
   - 如果用户明确说了某个平台，直接放在最高优先级

2. **主题匹配**（查平台优势图谱）：
   - 科普类 → bilibili（视频）、open163（公开课）、zhihu（图文）
   - 学科类 → smartedu（官方）、bilibili（讲解视频）、baiduwenku（文档）
   - 古诗语文 → bilibili（动画）、ximalaya（音频）、smartedu（官方）
   - 思维训练 → bilibili（益智视频）、zhihu（方法）
   - 艺术美育 → bilibili、douyin（短视频）
   - 习惯品格 → ximalaya（故事）、bilibili（动画）
   - 兴趣拓展 → bilibili、zhihu、xiaohongshu

> 📖 完整平台优势图谱见：`./references/config/platform-advantages.md`
> 📖 平台映射表见：`./references/config/platform-mapping.md`

3. **形态补充**：
   - 要视频 → 加 bilibili、smartedu、open163
   - 要音频 → 加 ximalaya
   - 要文档 → 加 baiduwenku、smartedu
   - 要图文 → 加 zhihu、weibo、xiaohongshu

4. **通用兜底**：
   - 通用搜索作为最后兜底，防止漏网

**最终平台数量**：
- 标准模式：3-5 个平台
- 穷尽模式：5-7 个平台

**本步产出**：
- `selected_platforms`：选定的平台列表（按优先级排序）
  - 每个元素包含：`platform_id`（平台标识）、`priority`（优先级）、`reason`（选择理由）

---

### 第三步：各平台关键词优化

针对每个选定的平台，优化搜索关键词——同样的主题，不同平台搜法不一样。

**优化原则**：

| 平台 | 关键词优化策略 |
|------|--------------|
| **bilibili** | 加"动画"、"讲解"、"课程"、"合集"等词；适合搜系统性内容 |
| **ximalaya** | 加"故事"、"音频"、"听"、"专辑"等词；适合搜睡前听、磨耳朵 |
| **smartedu** | 用学科名 + 年级，如"三年级数学"；官方平台，关键词要正式 |
| **zhihu** | 加"推荐"、"怎么学"、"经验"等词；适合搜方法和经验 |
| **douyin** | 关键词要短、要口语化；适合搜短视频教程 |
| **weibo** | 加"资料"、"分享"等词；适合搜资料整理 |
| **open163** | 加"公开课"、"TED"、"纪录片"等词；适合搜深度内容 |

**年龄适配**：
- 低幼 → 加"幼儿"、"启蒙"、"宝宝"
- 小学低年级 → 加"低年级"、"入门"、"基础"
- 小学高年级 → 加"高年级"、"进阶"、"提高"

**每个平台的查询数量分配**：
- 第一梯队平台（优先级最高）：3-5 个查询
- 第二梯队平台：2-3 个查询
- 补充平台：1-2 个查询
- 通用兜底：1-2 个查询

**本步产出**：
- `platform_queries`：各平台的优化后查询列表
  - 结构：`{ platform_id: [ {query, priority, format_hint}, ... ] }`

---

### 第四步：生成搜索任务清单

把前面的结果整理成结构化的搜索任务清单。

**每个平台的任务包含**：
- `platform_id`：平台标识（如 bilibili）
- `platform_name`：平台名称（如 B站）
- `priority`：优先级（P0 / P1 / P2）
- `queries`：该平台要搜的查询列表
  - 每个查询包含：`text`（关键词）、`tier`（优先级）、`format_hint`（形态提示）
- `target_count`：预期召回数量（该平台预期找多少条）
- `search_params`：其他搜索参数（排序方式、时间范围等，可选）

**总预期数量**：
- 标准模式：原始召回 50-80 条，最终精选 20-25 条
- 穷尽模式：原始召回 80-120 条，最终精选 30-40 条

**本步产出**：
- `search_tasks`：完整的搜索任务清单（数组）
- `total_expected`：总预期召回数量
- `search_strategy`：策略说明（为什么这么选平台、为什么这么分配）

---

### 第五步：写入输出文件

将搜索任务清单写入 `{session_dir}/{output_file}`（通常是 `stage2_search_plan.json`）。

**文件格式**（三层结构）：

```json
{
  "_meta": {
    "stage": 2,
    "session_id": "从输入文件中继承",
    "skill": "resource-search",
    "created_at": "当前时间（ISO 8601 格式）",
    "input_from": "{input_file}"
  },
  "_summary": {
    // 给 flow 看的摘要
  },
  "data": {
    // 给下游 platform 用的完整搜索任务
  }
}
```

---

#### _summary 部分（flow 读这个做调度）

**必须写入的字段**：
- `platform_count`：选定平台数量（数字）
  - 示例：4
- `platforms`：平台列表（数组）
  - 示例：["bilibili", "smartedu", "ximalaya", "zhihu"]
- `query_count`：总查询数量（数字）
  - 示例：15
- `expected_results`：预期召回数量（数字）
  - 示例：60

> 💡 _summary 必须精简，flow 只读前几十行就知道搜索计划怎么样。

---

#### data 部分（下游 platform 读这个执行）

**必须写入的字段**：

- `core_topic`：核心主题（字符串，✅必选）
  - 透传，供下游需要时使用

- `target_age`：目标年龄范围（字符串，✅必选）
  - 透传，供质量评估时使用

- `search_mode`：搜索模式（字符串，✅必选）
  - standard / exhaustive

- `search_tasks`：各平台搜索任务列表（数组，✅必选）
  - 每个任务包含：
    - `platform_id`：平台标识（字符串，✅必选）
      - 示例："bilibili"
    - `platform_name`：平台名称（字符串，✅必选）
      - 示例："B站"
    - `priority`：优先级（字符串，✅必选）
      - P0 / P1 / P2
    - `queries`：该平台的查询列表（数组，✅必选）
      - 每个查询包含：
        - `text`：查询关键词（字符串，✅必选）
        - `tier`：优先级分级（字符串，✅必选）
          - core / important / supplementary
        - `format_hint`：资源形态提示（字符串，⚠️可选）
    - `target_count`：预期召回数量（数字，✅必选）
      - 该平台预期找多少条结果
    - `search_params`：其他搜索参数（对象，⚠️可选）
      - 如排序方式、时间范围等平台特定参数

- `intent_data`：完整的 intent 数据（对象，⚠️可选）
  - 把上游 intent 的 data 原样透传，供下游需要时使用

- `strategy_notes`：策略说明（字符串，⚠️可选）
  - 简单说明为什么这么选平台、为什么这么分配

---

## 完成后

### 1. 确认输出

确认 `{session_dir}/{output_file}` 已成功写入。

### 2. 通知 flow

向 flow 返回执行结果，只返回 _summary 的内容：

```
✅ 已完成搜索策略制定
📄 输出文件：{output_file}
📊 摘要：
- 选定平台：{platform_count} 个
- 平台列表：{platforms 用顿号分隔}
- 查询总数：{query_count} 个
- 预期召回：{expected_results} 条
```

> 💡 **重要**：只返回 _summary，不要在上下文中展开完整的搜索任务。
> 完整任务已经写入文件，下游 platform Skill 会去读并执行。

---

## 关键原则

### 平台选择原则
1. **用户指定优先**：用户明确要什么平台/类型，就以那个为主
2. **主题匹配**：不同主题选不同的主力平台，不搞一刀切
3. **形态覆盖**：至少覆盖 2-3 种资源形态
4. **质量分层**：官方站做标杆，视频平台为主力，图文音频做补充
5. **数量适中**：不是平台越多越好，3-5 个精选平台效果最好

### 关键词优化原则
1. **平台适配**：不同平台有不同的搜索习惯，关键词要适配
2. **年龄适配**：根据目标年龄调整关键词的表述方式
3. **多角度**：同一个主题，从不同角度搜（教程/动画/故事/方法）
4. **有梯度**：核心词 + 扩展词 + 长尾词，层层递进

---

## 适用范围

面向 3-12 岁儿童成长相关的所有学习需求，包括但不限于：
- 学科学习（语文、数学、英语等）
- 科普启蒙、人文历史
- 艺术美育、思维训练
- 习惯品格、情绪管理
- 兴趣拓展、安全教育

---

## 参考资料

- **平台优势图谱**：`./references/config/platform-advantages.md`（各平台擅长领域）
- **平台映射表**：`./references/config/platform-mapping.md`（平台与能力映射）
- **搜索策略详解**：`./references/guides/search-strategy.md`（完整的策略制定方法）

> 💡 参考资料放在最后，执行主流程时不需要看，需要时再查阅。
