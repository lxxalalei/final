---
name: resource-intent
description: 儿童学习资源需求理解 Skill（阶段一）。当家长提出学习资源获取需求时激活，通过最多 2 轮澄清、语义理解与槽位抽取、默认补全，将自然语言需求翻译为结构化需求描述 JSON 文件，供下游搜索策略阶段使用。
agent_created: true
---

# resource-intent · 需求理解

**上游**：无（第一个阶段，直接接收用户需求）
**下游**：resource-search
**阶段编号**：stage 1

把家长模糊、口语化的需求，翻译成结构化的需求描述。

---

## 执行前准备

读取 `{session_dir}/manifest.json`，获取本阶段执行所需信息：

- `manifest.session_id` → 会话标识
- `manifest.user_request` → 用户原始需求文本（本阶段输入）
- `manifest.stages.stage1.output` → 本阶段输出文件名

本阶段是第一个阶段，没有上游数据文件。输入来源是 manifest 中的 `user_request` 字段（由 flow 创建会话时写入）。

---

## 执行步骤

### 第一步：判断需求清晰度

拿到用户需求后，判断是否足够具体。满足任一条件即可跳过澄清，直接进入第三步：

- 明确说了主题 + 年龄/年级/资源类型中的至少 1 项
- 有明确的问题指向（如"有没有适合 5 岁的编程启蒙"）
- 用户说"随便""都可以" → 按默认值处理

不满足以上条件则进入第二步。

> 📖 完整判断标准和模糊需求分类见 `./references/requirement-decomposition-rules.md` 第三节

---

### 第二步：需求澄清（最多 2 轮，可选）

> 如果第一步判断为"足够具体"，跳过本步。

**第 1 轮**：开放式问题引导核心主题。
- 用大白话，像朋友聊天，不用专业术语
- 给 2-3 个方向参考，但不用封闭式选项框死
- 例："想找哪方面的呀？比如乐器入门、乐理知识，还是先听听音乐培养感觉？"

**第 2 轮**（可选，最多 1 个问题）：补充最关键的一个信息。
- 优先级：使用场景 > 期望效果 > 年龄/基础 > 其他偏好
- **第 3 轮禁止**。信息不够用默认值，搜出来不满意再调整。

**结束条件**：用户明确了核心主题 / 已问 2 轮 / 用户说"就这样吧先搜搜看"。

> 📖 各场景话术参考 `./references/clarification-phrases.md`

---

### 第三步：语义理解与槽位抽取

从用户需求中提取结构化字段。**只在用户明确表达时才填**，不确定的留空，由第四步默认补全。

输出以下字段（`grade_level`、`use_scenario` 可选，其余必选）：

- `summary`：一句话需求总结
- `core_topic`：核心搜索主题（如"三年级数学"、"古诗启蒙"）
- `target_age`：目标年龄范围（3-12 岁，如"8-9岁"）
- `grade_level`：年级（如"小学三年级"）
- `theme_type`：主题分类——学科 / 科普 / 古诗语文 / 思维训练 / 艺术美育 / 习惯品格 / 兴趣拓展 / 综合
- `difficulty`：难度偏好——入门 / 进阶 / 系统
- `format_preferences`：资源形态偏好（如 ["视频", "文档"]）
- `source_preference`：来源偏好——不限 / 官方优先 / 视频平台优先
- `use_scenario`：使用场景（如"睡前听"、"课后练习"）

> 📖 各字段的语义抽取规则和判断方法见 `./references/requirement-decomposition-rules.md` 第六节

---

### 第四步：默认补全

用户未明确的字段，按以下默认值补全。**每条自动补全的假设必须记录到 `assumptions` 数组**，完成后告知用户。

- `target_age`：默认 6-8 岁。主题偏高龄（如"方程""编程"）上调到 9-12 岁
- `difficulty`：默认"入门"。主题偏进阶（如"奥数""竞赛"）按主题推断
- `format_preferences`：默认 ["视频", "图文"]。学科类追加"文档"
- `source_preference`：默认"不限"
- `use_scenario`：默认留空
- `search_mode`：默认 `standard`。用户说"多找点""尽量全" / 主题冷门小众 / 需求宽泛 → 切换 `exhaustive`

> 📖 完整补全规则见 `./references/requirement-decomposition-rules.md` 第七节

---

### 第五步：写入输出文件

将结构化需求写入 `{session_dir}/{manifest.stages.stage1.output}`（通常是 `stage1_intent.json`）。

```json
{
  "_meta": {
    "stage": 1,
    "session_id": "从 session_dir 中提取或生成",
    "skill": "resource-intent",
    "created_at": "当前时间 ISO 8601",
    "input_from": null
  },
  "_summary": {
    "core_topic": "三年级数学",
    "target_age": "8-9岁",
    "search_mode": "standard"
  },
  "data": {
    "summary": "家长想给三年级孩子找数学练习题",
    "core_topic": "三年级数学",
    "target_age": "8-9岁",
    "grade_level": "小学三年级",
    "theme_type": "学科",
    "difficulty": "入门",
    "format_preferences": ["视频", "文档"],
    "source_preference": "不限",
    "use_scenario": "课后练习",
    "search_mode": "standard",
    "assumptions": ["假设目标年龄为8-9岁（三年级）", "假设难度为入门级"]
  }
}
```

**_summary**（flow 只读这个做调度）：`core_topic`、`target_age`、`search_mode`

**data**（下游 search 读这个）：上表所有字段。`grade_level`、`use_scenario`、`assumptions` 可选，其余必选。

---

## 完成后

### 1. 更新 manifest

将 `manifest.json` 中 `stages.stage1.status` 更新为 `completed`。

### 2. 向用户确认需求

用友好的方式展示理解结果，**明确区分"用户说的"和"假设的"**：

> 好的，我按这个方向帮你找：
> - 主题：三年级数学
> - 形式：视频 + 文档
>
> 我做了一些假设：
> - 目标年龄 8-9 岁（三年级）——如果你家孩子不是这个年龄段，告诉我调整
> - 入门难度——如果需要进阶的，随时说

### 3. 返回摘要

只返回 `_summary`，不展开完整 data：

```
✅ 已完成需求理解
📄 输出文件：stage1_intent.json
📊 摘要：
- 核心主题：{core_topic}
- 目标年龄：{target_age}
- 搜索模式：{search_mode}
```

> 完整数据已写入文件，下游 search 会去读。不要在上下文中展开 data。

---

## 关键原则

- 优先使用默认补全，减少澄清轮次
- 每轮只问一个问题，最多 2 轮
- 70% 清楚即可输出，搜索成本低于追问成本
- 使用语义理解抽取意图，不做关键字匹配

---

## 参考资料

- `./references/requirement-decomposition-rules.md` — 完整执行手册（判断标准、槽位定义、补全规则）
- `./references/clarification-phrases.md` — 各场景澄清话术参考
