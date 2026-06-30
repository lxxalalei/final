---
name: learning-resource-flow
description: 儿童学习资源获取与管理的总调度入口。接收用户自然语言需求，按顺序调度 intent、search、platforms、selector、downloader、library-manager 六个阶段，完成从需求理解到归档入库的完整工作流。
agent_created: true
---

# learning-resource-flow · 总调度入口

**职责**：创建会话、初始化 manifest.json、按顺序切换到各阶段 skill 执行、读取各阶段 `_summary` 做调度决策、在关键节点向用户展示并等待确认。

不直接执行搜索或下载，而是协调 6 个 skill 协同完成任务。

---

## 核心原则

1. **用户确认优先**：展示候选后等待用户确认，不静默下载
2. **最少必要澄清**：只追问会显著改变结果的缺失信息，最多 2 轮
3. **穷尽召回 + 用户选择**：尽量多搜，把选择权交给用户
4. **最大化提取 + 分级降级**：能下完整不拿摘要，失败时逐级降级
5. **归档便于复用**：下载的资源自动归档，后续可主动检索复用
6. **儿童友好**：默认只保留中文、免费、适龄的内容

---

## 会话与文件机制

### 创建会话

收到新需求时：
- 生成 session_id：`{日期}-{时间}-{主题英文缩写}`，如 `20260626-1441-math-grade3`
- 创建目录：`.learning-resource-work/sessions/{session_id}/`
- 创建子目录：`downloads/`
- 写入 `manifest.json`（含完整路径信息，各 skill 自行读取）

### manifest.json 结构

```json
{
  "session_id": "20260626-1441-math-grade3",
  "session_dir": ".learning-resource-work/sessions/20260626-1441-math-grade3",
  "user_request": "帮我找三年级数学练习题",
  "status": "in_progress",
  "current_stage": 1,
  "stages": {
    "stage1": {"status": "pending", "output": "stage1_intent.json"},
    "stage2": {"status": "pending", "output": "stage2_search_plan.json"},
    "stage3": {"status": "pending", "output": "stage3_candidates.json"},
    "stage4": {"status": "pending", "output": "stage4_select.json"},
    "stage5": {"status": "pending", "output": "stage5_download.json"},
    "stage6": {"status": "pending", "output": "stage6_archive.json"}
  }
}
```

**关键字段说明**：
- `session_dir`：会话目录的完整路径。创建会话后写入，各 skill 自行读取获取路径
- `user_request`：用户原始需求文本。intent 阶段从此字段获取输入（不依赖对话上下文）
- `stages.stage{N}.output`：各阶段的输出文件名。skill 自行读取获取自己的输出文件名和上游的输入文件名
- `stages.stage{N}.status`：各阶段执行状态。各 skill 完成后自行更新为 `completed`

### 数据流转规则

各阶段 skill 从 manifest.json 自行获取路径和文件名信息，不依赖上下文传递：

1. **flow 创建会话** → 写入 manifest.json（含 session_dir、user_request、各阶段 output 文件名）
2. **切换到阶段 skill 执行** → session_dir 路径保持在上下文中（唯一需要上下文传递的信息）
3. **skill 自行读 manifest** → 获取自己的输出文件名、上游输出文件名
4. **skill 写入输出文件** → 业务数据落磁盘（`_meta` / `_summary` / `data` 三层结构）
5. **skill 自行更新 manifest** → 将本阶段 status 改为 `completed`
6. **flow 读输出文件 `_summary`** → 获取摘要做调度决策（不读 data）
7. **flow 向用户展示** → 需要展示详情时从文件读 data 渲染

### 上下文管理

上下文中只保留 session_dir 路径和各阶段 `_summary` 摘要。业务数据（需求/查询/搜索结果/选择/下载/归档）全部走文件，不堆积在上下文中。

### 需求类型判断

| 用户说的 | 处理方式 |
|---------|---------|
| 新的搜索/下载主题 | 创建新会话，从阶段一开始 |
| "刚才那个""加选几个" | 复用当前 session，从指定阶段继续 |
| "我之前存的""上次下载的" | 切换到 library-manager 查资料库（不碰 sessions/） |
| "继续上次没下完的" | 列出 sessions/ 目录让用户选，从中断处继续 |

> 搜索结果是时效性数据，每次新需求都重新搜索。

---

## 协作的 Skill 清单

| Skill | 所在层 | 职责 | 执行阶段 |
|-------|-------|------|---------|
| `resource-intent` | 业务能力层 | 需求理解与槽位抽取 | 阶段一 |
| `resource-search` | 业务能力层 | 搜索策略制定（查询生成+平台路由+任务分配） | 阶段二 |
| `resource-platforms` | 平台执行层 | 搜索执行（调度平台脚本+跨平台去重） | 阶段三 |
| `resource-selector` | 业务能力层 | 质量评估+过滤精选+候选展示+用户选择 | 阶段四 |
| `resource-downloader` | 业务能力层 | 下载调度（分发+重试+降级） | 阶段五 |
| `library-manager` | 业务能力层 | 资源归档、索引、管理 | 阶段六 |

> 资料库检索不作为标准流程的必经步骤，用户需要时可主动切换到 library-manager 查询。

---

## 阶段调度

> flow 的职责：更新 manifest 当前阶段为 in_progress → 切换到 skill 执行 → 读 `_summary` → 向用户展示并等待确认 → 进入下一阶段。
> 各 skill 的职责：读 manifest 获取路径信息 → 读上游 data → 执行业务逻辑 → 写输出文件 → 更新 manifest 自身状态为 completed。

### 阶段一：需求理解

1. 更新 manifest：`current_stage = 1`，`stages.stage1.status = "in_progress"`
2. 切换到 `resource-intent` 执行（intent 读 manifest 获取 user_request 和 output 文件名）
3. 读 `stage1_intent.json` 的 `_summary`：core_topic、target_age、search_mode
4. 向用户展示任务确认（主题/年龄/资源类型/搜索模式/假设说明），确认后进阶段二

### 阶段二：搜索策略

1. 更新 manifest：`current_stage = 2`，`stages.stage2.status = "in_progress"`
2. 切换到 `resource-search` 执行（search 读 manifest 获取上游 output 和自身 output 文件名）
3. 读 `stage2_search_plan.json` 的 `_summary`：platform_count、platforms、query_count、expected_results
4. 向用户展示搜索计划概要，确认后进阶段三

### 阶段三：搜索执行

1. 更新 manifest：`current_stage = 3`，`stages.stage3.status = "in_progress"`
2. 切换到 `resource-platforms` 执行（platforms 读 manifest 获取上游 output 和自身 output 文件名）
3. 读 `stage3_candidates.json` 的 `_summary`：total_count、raw_count、platforms、has_results
4. has_results = false 或 total_count = 0 时主动询问用户是否放宽条件/换关键词/开穷尽模式
5. 有结果则进阶段四

### 阶段四：质量筛选与用户选择

1. 更新 manifest：`current_stage = 4`，`stages.stage4.status = "in_progress"`
2. 切换到 `resource-selector` 执行（selector 读 manifest 获取上游 output 和自身 output 文件名）
3. 读 `stage4_select.json` 的 `_summary`：total_candidates、filtered_count、selected_count、selection_mode
4. 用户未选任何资源则结束；选了则进阶段五

### 阶段五：下载获取

1. 更新 manifest：`current_stage = 5`，`stages.stage5.status = "in_progress"`
2. 切换到 `resource-downloader` 执行（downloader 读 manifest 获取上游 output 和自身 output 文件名）
3. 读 `stage5_download.json` 的 `_summary`：success_count、degraded_count、failed_count
4. 全部失败时告知用户原因并提供降级内容，询问是否换资源
5. 有成功/降级结果则进阶段六

### 阶段六：归档入库

1. 更新 manifest：`current_stage = 6`，`stages.stage6.status = "in_progress"`
2. 切换到 `library-manager` 执行（library-manager 读 manifest 获取上游 output 和自身 output 文件名）
3. 读 `stage6_archive.json` 的 `_summary`：archived_count、skipped_count、dedup_stats
4. 向用户展示最终汇总：成功获取列表 + 降级列表 + 失败列表 + 归档位置
5. 更新 manifest：`status = "completed"`

---

## 异常处理

### 用户取消
任何阶段用户说"算了""不要了""取消"，都立即终止流程，友好回复。

### 搜索结果太少
如果阶段三返回的结果去重后少于 5 个，主动询问用户：
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
