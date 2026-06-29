---
name: learning-resource-flow
description: 儿童学习资源获取与管理的总调度入口。接收用户自然语言需求，按顺序调度 intent、search、platforms、selector、downloader、library-manager 六个阶段，完成从需求理解到归档入库的完整工作流。
---

# learning-resource-flow · 总调度入口

## 概述

本 Skill 是儿童学习资源 Skill 套件的**唯一总入口**，负责协调整个资源获取工作流：
从用户提出需求开始，经过需求拆解、平台路由、多端搜索召回、用户选择确认、分级下载获取，最终归档到本地资料库。

本 Skill 不直接执行搜索或下载，而是调度 5 个业务 Skill（intent/search/selector/downloader/library-manager）和 1 个平台执行 Skill（resource-platforms）协同完成任务。

---

## 核心原则

1. **用户确认优先**：展示候选后等待用户确认，不静默下载
2. **最少必要澄清**：只追问会显著改变结果的缺失信息，最多 2 轮
3. **穷尽召回 + 用户选择**：尽量多搜，把选择权交给用户
4. **最大化提取 + 分级降级**：能下完整不拿摘要，失败时逐级降级
5. **归档便于复用**：下载的资源自动归档，后续可主动检索复用
6. **儿童友好**：默认只保留中文、免费、适龄的内容

---

## 数据流转规则

> 各阶段输出通过 JSON 文件保存到工作目录，不堆积在上下文中。

### 1. 创建会话

收到新需求时：
- 生成 session_id：`{日期}-{时间}-{主题英文缩写}`，如 `20260626-1441-math-grade3`
- 创建目录：`.learning-resource-work/sessions/{session_id}/`
- 创建子目录：`downloads/`
- 写入 `manifest.json`：

```json
{
  "session_id": "20260626-1441-math-grade3",
  "user_request": "帮我找三年级数学练习题",
  "status": "in_progress",
  "current_stage": 1,
  "stages": {
    "stage1": {"status": "pending", "output": "stage1_intent.json"},
    "stage2": {"status": "pending", "output": "stage2_search.json"},
    "stage3": {"status": "pending", "output": "stage3_select.json"},
    "stage4": {"status": "pending", "output": "stage4_download.json"},
    "stage5": {"status": "pending", "output": "stage5_archive.json"}
  }
}
```

### 2. 调度每个阶段

对阶段 1→2→3→4→5 依次执行：
- 更新 manifest.json：当前阶段标记为 `in_progress`
- 调用对应 Skill，传递三个参数：会话目录路径、上游文件名、输出文件名
- Skill 返回后：只读输出文件的 `_summary`，不读完整 data
- 更新 manifest.json：当前阶段标记为 `completed`，回填 summary
- 根据 summary 决定下一步

### 3. 上下文管理

上下文中只保留 session_id、当前阶段、各阶段 summary。需要展示给用户时（如候选列表），从文件读取 data 部分后渲染。

### 4. 需求类型判断

| 用户说的 | 处理方式 |
|---------|---------|
| 新的搜索/下载主题 | 创建新会话，从阶段一开始 |
| "刚才那个""加选几个" | 复用当前 session_id，从指定阶段继续 |
| "我之前存的""上次下载的" | 调用 library-manager 查资料库（不碰 sessions/） |
| "继续上次没下完的" | 列出 sessions/ 目录让用户选，从中断处继续 |

> 搜索结果是时效性数据，每次新需求都重新搜索。

---

## 协作的 Skill 清单

| Skill | 所在层 | 职责 | 调用阶段 |
|-------|-------|------|---------|
| `resource-intent` | 业务能力层 | 需求理解与查询生成 | 阶段一 |
| `resource-search` | 业务能力层 | 搜索调度（路由+汇总+质控） | 阶段二 |
| `resource-selector` | 业务能力层 | 候选展示与用户选择 | 阶段三 |
| `resource-downloader` | 业务能力层 | 下载调度（分发+重试+降级） | 阶段四 |
| `library-manager` | 业务能力层 | 资源归档、索引、管理 | 阶段五 |
| `resource-platforms` | 平台执行层 | 具体平台的搜索+下载 | 阶段二、四（由调度层调用） |

> **注意**：platform skill 由 search 和 downloader 调度器直接调用，flow 不直接调用 platform skill。
>
> **说明**：资料库检索不作为标准流程的必经步骤，用户需要时可主动调用 library-manager 查询。

---

## 阶段调度

> flow 只负责"调谁、传什么参数、读什么 summary"。各阶段的具体执行逻辑、输出格式模板见 `references/output-templates.md`。

### 阶段一：需求理解
- 调用 `resource-intent`，传 `{session_dir}` + 无上游 → 输出 `stage1_intent.json`
- 读 `_summary`：core_topic、query_count、target_age、search_mode、assumptions
- 向用户展示任务确认（主题/年龄/目标/资源类型/搜索模式/假设说明），确认后进阶段二

### 阶段二：搜索召回
- 调用 `resource-search`，传 `{session_dir}` + `stage1_intent.json` → 输出 `stage2_search.json`
- 读 `_summary`：候选总数、平台覆盖、质量分布
- 候选 < 5 个时主动询问用户是否放宽条件/换关键词/开穷尽模式
- 候选充足则进阶段三

### 阶段三：候选选择
- 调用 `resource-selector`，传 `{session_dir}` + `stage2_search.json` → 输出 `stage3_select.json`
- 读 `_summary`：selected_count、selection_mode
- 用户未选任何资源则结束；选了则进阶段四

### 阶段四：下载获取
- 调用 `resource-downloader`，传 `{session_dir}` + `stage3_select.json` → 输出 `stage4_download.json`
- 读 `_summary`：success_count、degraded_count、failed_count
- 全部失败时告知用户原因并提供降级内容，询问是否换资源
- 有成功/降级结果则进阶段五

### 阶段五：归档入库
- 调用 `library-manager`，传 `{session_dir}` + `stage4_download.json` → 输出 `stage5_archive.json`
- 读 `_summary`：archived_count、skipped_count、dedup_stats
- 向用户展示最终汇总：成功获取列表 + 降级列表 + 失败列表 + 归档位置
- 更新 manifest.json 状态为 `completed`

---

## 异常处理

### 用户取消
任何阶段用户说"算了""不要了""取消"，都立即终止流程，友好回复。

### 搜索结果太少
如果搜索结果少于 5 个，主动询问用户：
- 是否放宽条件？
- 是否换个关键词？
- 是否开启穷尽模式？

### 下载全部失败
如果所有资源都下载失败：
- 说明失败原因
- 提供降级内容（摘要、链接）
- 询问是否需要换其他资源

---

## 边界与限制

### 可以做的
- 搜索国内公开互联网的教育资源
- 下载公开可访问的文件
- 转换网页内容为本地可管理形态
- 使用用户本人的登录态访问平台
- 管理和复用本地资料库

### 不可以做的
- 破解付费墙或绕过访问控制
- 高频滥用式抓取
- 访问境外网站（YouTube、Facebook等）
- 保存搜索缓存、临时文件等非最终资源
- 静默下载用户未确认的资源
- 传播或分享下载的资源（仅供个人学习）

---

## 参考资料

- `references/workflow-guide.md` - 详细工作流指南与异常处理
- `references/output-templates.md` - 结构化输出模板规范（4类模板+JSON Schema）
