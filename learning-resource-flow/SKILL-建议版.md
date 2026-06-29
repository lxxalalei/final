---
name: learning-resource-flow
description: 儿童学习资源获取与管理的总调度入口。接收用户自然语言需求，按顺序调度 intent、search、platforms、selector、downloader、library-manager 六个阶段，完成从需求理解到归档入库的完整工作流。
---

# learning-resource-flow · 总调度入口

## 概述

本 Skill 是儿童学习资源 Skill 套件的**唯一总入口**，负责协调整个资源获取工作流：
从用户提出需求开始，经过需求拆解、搜索策略生成、多平台搜索执行、用户选择确认、分级下载获取，最终归档到本地资料库。

本 Skill 不直接执行搜索或下载，而是按顺序调度以下 6 个 Skill 协同完成任务：

```
用户需求 → intent → search → platforms → selector → downloader → library-manager → 归档完成
          阶段一    阶段二    阶段二(执)   阶段三      阶段四         阶段五
```

---

## 核心原则

1. **用户确认优先**：展示候选后等待用户确认，绝不静默下载
2. **最少必要澄清**：只追问会显著改变结果的缺失信息，最多 2 轮
3. **状态持久化**：所有中间结果落盘，支持中断后继续
4. **失败友好降级**：任何阶段失败都给出明确原因和替代方案

---

## 会话管理

### 会话目录结构

每个新需求创建一个独立会话目录，所有中间文件都存在这里：

```
.learning-resource-work/sessions/{session_id}/
├── manifest.json              # 会话状态清单（总控文件，flow 维护）
├── stage1_intent.json         # 阶段一输出：查询指令包        ← resource-intent 负责
├── stage2_search_plan.json    # 阶段二输出：搜索任务计划      ← resource-search 负责
├── stage2_candidates.json     # 阶段二(执)输出：候选资源列表  ← resource-platforms 负责
├── stage3_select.json         # 阶段三输出：用户选定列表      ← resource-selector 负责
├── stage4_download.json       # 阶段四输出：下载结果          ← resource-downloader 负责
├── stage5_archive.json        # 阶段五输出：归档结果          ← library-manager 负责
└── downloads/                 # 下载的资源文件
```

### manifest.json 格式

```json
{
  "session_id": "20260626-1441-math-grade3",
  "user_request": "帮我找三年级数学练习题",
  "status": "in_progress",
  "current_stage": 2,
  "stages": {
    "stage1": {"status": "completed", "output": "stage1_intent.json", "owner": "resource-intent", "summary": {...}},
    "stage2_plan": {"status": "completed", "output": "stage2_search_plan.json", "owner": "resource-search", "summary": {...}},
    "stage2_exec": {"status": "in_progress", "output": "stage2_candidates.json", "owner": "resource-platforms", "summary": null},
    "stage3": {"status": "pending", "output": "stage3_select.json", "owner": "resource-selector", "summary": null},
    "stage4": {"status": "pending", "output": "stage4_download.json", "owner": "resource-downloader", "summary": null},
    "stage5": {"status": "pending", "output": "stage5_archive.json", "owner": "library-manager", "summary": null}
  }
}
```

**状态值**：`pending` / `in_progress` / `completed` / `failed` / `cancelled`

> 💡 `owner` 字段标注该阶段由哪个 Skill 负责产出。

---

## 阶段调度详解

> flow 只负责「调谁、传什么、读什么 summary、下一步怎么走」。
> 各阶段的具体输出格式见各 Skill 的 SKILL.md。

### 阶段一：需求理解「resource-intent 负责」

- **输入**：用户原始需求（自然语言）
- **调用**：`resource-intent`，传会话目录 → 输出 `stage1_intent.json`
- **读取 summary**：`core_topic`、`query_count`、`target_age`、`search_mode`、`assumptions`
- **后续动作**：
  - 向用户展示任务确认（主题 / 年龄 / 资源类型 / 搜索模式 / 假设说明）
  - 用户确认后进入阶段二
  - 用户有异议则调整参数，重新生成

### 阶段二：搜索策略生成「resource-search 负责」

- **输入**：`stage1_intent.json`
- **调用**：`resource-search`，传会话目录 + 上游文件名 → 输出 `stage2_search_plan.json`
- **读取 summary**：`platform_count`、`total_queries`、`estimated_results`
- **后续动作**：直接进入阶段二（执行），无需用户确认

### 阶段二（执行）：平台搜索执行「resource-platforms 负责」

- **输入**：`stage2_search_plan.json`
- **调用**：`resource-platforms`，传会话目录 + 上游文件名 → 输出 `stage2_candidates.json`
- **读取 summary**：`total_count`、`platform_coverage`、`quality_distribution`
- **后续动作**：
  - 候选 < 5 个：主动询问是否放宽条件 / 换关键词 / 开穷尽模式
  - 候选充足：进入阶段三

### 阶段三：候选选择「resource-selector 负责」

- **输入**：`stage2_candidates.json`
- **调用**：`resource-selector`，传会话目录 + 上游文件名 → 输出 `stage3_select.json`
- **读取 summary**：`selected_count`、`selection_mode`
- **后续动作**：
  - 用户未选任何资源：友好结束
  - 用户选了资源：进入阶段四

### 阶段四：下载获取「resource-downloader 负责」

- **输入**：`stage3_select.json`
- **调用**：`resource-downloader`，传会话目录 + 上游文件名 → 输出 `stage4_download.json`
- **读取 summary**：`success_count`、`degraded_count`、`failed_count`
- **后续动作**：
  - 全部失败：说明原因 + 提供降级内容 + 询问是否换资源
  - 有成功 / 降级结果：进入阶段五

### 阶段五：归档入库「library-manager 负责」

- **输入**：`stage4_download.json`
- **调用**：`library-manager`，传会话目录 + 上游文件名 → 输出 `stage5_archive.json`
- **读取 summary**：`archived_count`、`skipped_count`、`dedup_stats`
- **后续动作**：
  - 向用户展示最终汇总：成功列表 + 降级列表 + 失败列表 + 归档位置
  - 更新 manifest 状态为 `completed`

---

## 需求类型判断

收到用户消息时，先判断属于哪种类型：

| 用户说的 | 类型 | 处理方式 |
|---------|------|---------|
| "帮我找三年级数学题" | 新需求 | 创建新会话，从阶段一开始 |
| "刚才那个再加几个" | 继续当前 | 复用当前 session_id，从阶段三继续 |
| "我之前存的英语绘本" | 查资料库 | 直接调用 library-manager 查询，不创建会话 |
| "继续上次没下完的" | 恢复会话 | 列出最近的 sessions 让用户选，从中断处继续 |

> 💡 搜索结果是时效性数据，**新需求必须重新搜索**，不复用旧结果。

---

## 异常处理

### 用户取消
任何阶段用户说「算了」「不要了」「取消」，立即终止：
- 更新 manifest 状态为 `cancelled`
- 友好回复，不追问

### 搜索结果太少（< 5 个）
主动给出三个选项：
1. 放宽条件（扩大年龄 / 类型范围）
2. 换个关键词试试
3. 开启穷尽模式（更多平台 + 更多关键词）

### 下载全部失败
- 说明主要失败原因（反爬 / 需登录 / 网络问题等）
- 提供降级内容（摘要、链接、文字版）
- 询问是否需要换其他资源

### 中间 Skill 报错
- 记录错误信息到 manifest
- 向用户说明哪个环节出了问题
- 给出选项：重试 / 跳过 / 结束

---

## 边界与限制

### ✅ 可以做的
- 搜索国内公开互联网的教育资源
- 下载公开可访问的文件
- 转换网页内容为本地可管理形态
- 使用用户本人的登录态访问平台
- 管理和复用本地资料库

### ❌ 不可以做的
- 破解付费墙或绕过访问控制
- 高频滥用式抓取
- 访问境外网站（YouTube、Facebook 等）
- 静默下载用户未确认的资源
- 传播或分享下载的资源（仅供个人学习）

---

## 参考资料

- `shared/schemas/session-io-spec.md` — 会话 I/O 规范
- `shared/schemas/skill-contract.md` — 跨 Skill 数据契约
