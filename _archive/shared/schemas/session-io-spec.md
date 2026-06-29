# 会话上下文读写规范（Session I/O Spec）

> 本规范定义各 Skill 之间通过文件系统传递数据的读写规则。
> 替代原有的"上下文内 JSON 透传"方式，解决上下文膨胀、数据丢失、不可恢复问题。
> 字段内容（data 部分）的规范仍遵循 `skill-contract.md`。

---

## 一、设计目标

| 目标 | 解决的问题 |
|------|-----------|
| 上下文瘦身 | 阶段数据写文件，上下文只保留摘要（4000行→80行） |
| 数据完整 | 文件持久化，对话中断不丢失 |
| 断点恢复 | manifest.json 记录当前阶段，可从断点继续 |
| 可审计 | 每个阶段的完整输出独立保存，可回溯 |

---

## 二、术语定义

| 术语 | 定义 |
|------|------|
| **工作目录** | 用户当前操作的项目目录（即 cwd） |
| **工作区根目录** | `.learning-resource-work/`（工作目录下，gitignored） |
| **会话（Session）** | 一次完整的需求处理（从 intent 到 archive），对应一个目录 |
| **session_id** | 会话唯一标识，格式 `{YYYYMMDD-HHMM}-{主题英文缩写}` |
| **阶段文件（Stage File）** | 某个 Skill 的输出文件（stage1_intent.json 等） |
| **manifest.json** | 会话状态索引文件，记录各阶段状态和文件指针 |
| **字段域** | manifest.json 中每个 stage 对应的独立字段区域 |

---

## 三、目录结构

```
{工作目录}/
└── .learning-resource-work/                      ← 工作区根目录（gitignored）
    └── sessions/                                  ← 全局唯一，所有会话平铺
        └── {session_id}/                          ← 一个会话 = 一个目录
            ├── manifest.json                      ← 状态索引（轻量，≤30行）
            ├── stage1_intent.json                 ← 阶段一输出（intent 写）
            ├── stage2_search.json                 ← 阶段二输出（search 写）
            ├── stage3_select.json                 ← 阶段三输出（selector 写）
            ├── stage4_download.json               ← 阶段四输出（downloader 写）
            ├── stage5_archive.json                ← 阶段五输出（library 写）
            └── downloads/                         ← 下载的临时文件（归档后移走）
                └── ...
```

### 路径约定

- 所有路径使用**相对路径**（相对于工作目录）
- 示例：`.learning-resource-work/sessions/20260626-1441-math-grade3/stage2_search.json`
- Skill 的 SKILL.md 中用 `{session_dir}` 占位符表示会话目录

---

## 四、文件规范

### 4.1 manifest.json（状态索引）

**写入者**：learning-resource-flow（唯一写入者）
**读取者**：所有 Skill（只读）
**大小**：≤30 行（只含状态和文件指针，不含业务数据）

```json
{
  "session_id": "20260626-1441-math-grade3",
  "user_request": "帮我找三年级数学练习题",
  "created_at": "2026-06-26T14:41:00+08:00",
  "updated_at": "2026-06-26T14:45:00+08:00",
  "status": "in_progress",
  "current_stage": 3,

  "stages": {
    "stage1": {
      "status": "completed",
      "output": "stage1_intent.json",
      "completed_at": "2026-06-26T14:42:00+08:00",
      "summary": "数学练习题/三年级/查询词3组"
    },
    "stage2": {
      "status": "completed",
      "output": "stage2_search.json",
      "completed_at": "2026-06-26T14:43:00+08:00",
      "summary": "22个候选/S3/A8/B8/C3"
    },
    "stage3": {
      "status": "in_progress",
      "output": "stage3_select.json",
      "started_at": "2026-06-26T14:44:00+08:00",
      "summary": null
    },
    "stage4": {"status": "pending", "output": "stage4_download.json"},
    "stage5": {"status": "pending", "output": "stage5_archive.json"}
  }
}
```

**字段说明**：

| 字段 | 类型 | 必须 | 说明 |
|------|------|:----:|------|
| `session_id` | string | ✅ | 会话唯一标识 |
| `user_request` | string | ✅ | 用户原始需求文本 |
| `created_at` | string | ✅ | 创建时间（ISO 8601） |
| `updated_at` | string | ✅ | 最后更新时间 |
| `status` | string | ✅ | `in_progress` / `completed` / `cancelled` |
| `current_stage` | number | ✅ | 当前执行到的阶段（1-5） |
| `stages.{N}.status` | string | ✅ | `pending` / `in_progress` / `completed` / `skipped` |
| `stages.{N}.output` | string | ✅ | 该阶段输出文件名 |
| `stages.{N}.summary` | string | ⚠️ | 该阶段摘要（≤50字，完成时填写） |

### 4.2 阶段文件（Stage Files）

**写入者**：该阶段对应的 Skill（唯一写入者）
**读取者**：下游 Skill 读取 data；flow 读取 _summary

每个阶段文件统一包含 **3 个顶层 key**：

```json
{
  "_meta": {
    "stage": 2,
    "session_id": "20260626-1441-math-grade3",
    "skill": "resource-search",
    "created_at": "2026-06-26T14:43:00+08:00",
    "input_from": "stage1_intent.json"
  },
  "_summary": {
    "total_count": 22,
    "platforms": ["bilibili", "ximalaya", "smartedu", "zhihu"],
    "quality_dist": {"S": 3, "A": 8, "B": 8, "C": 3}
  },
  "data": {
    "total_count": 22,
    "search_summary": "查询3组/平台4个/召回85条/初筛后40条/去重后22条",
    "resources": [
      {
        "resource_id": "bilibili:BV1xx...",
        "title": "三年级数学动画讲解",
        "type": "视频",
        "...": "（完整字段遵循 skill-contract.md）"
      }
    ]
  }
}
```

**顶层 key 职责**：

| key | 内容 | 谁读 | 大小 |
|-----|------|------|------|
| `_meta` | 来源/时间/输入文件 | 调试/审计用 | 固定 ~6行 |
| `_summary` | 关键指标摘要 | flow 做调度决策、展示给用户 | ≤10行 |
| `data` | 完整业务数据 | 下游 Skill 处理 | 可达数百行 |

### 4.3 各阶段文件内容映射

| 文件 | 写入者 | data 内容 | data 遵循契约 |
|------|--------|----------|--------------|
| `stage1_intent.json` | resource-intent | 查询指令包（Query Package） | skill-contract.md 阶段一→二 |
| `stage2_search.json` | resource-search | 候选资源列表（Candidate List） | skill-contract.md 阶段二→三 |
| `stage3_select.json` | resource-selector | 选定资源列表（Selected List） | skill-contract.md 阶段三→四 |
| `stage4_download.json` | resource-downloader | 下载结果列表（Download Result List） | skill-contract.md 阶段四→五 |
| `stage5_archive.json` | library-manager | 归档结果列表（Archive Result List） | skill-contract.md 阶段五输出 |

> **重要**：data 内部的字段定义、必选/可选/禁止丢弃规则，**完全遵循 skill-contract.md 原有规范**。本规范只定义 _meta 和 _summary 这两层包装。

---

## 五、读写规则

### 5.1 写入规则（Write）

| 规则 | 说明 |
|------|------|
| **W1：每阶段只写自己的文件** | search 只写 stage2_search.json，不碰 stage1/stage3 |
| **W2：整文件覆盖** | 使用 Write 工具写入完整文件（不用 Edit 增量修改） |
| **W3：先写 data 再写完整文件** | 确保 _meta/_summary/data 三段齐全后一次性写入 |
| **W4：data 遵循契约** | data 内部字段严格遵循 skill-contract.md（只增不删、完整透传） |
| **W5：_summary ≤50字** | 摘要必须精简，供 flow 快速读取 |
| **W6：完成后更新 manifest** | Skill 写完阶段文件后，flow 更新 manifest.json 该阶段状态 |

### 5.2 读取规则（Read）

| 规则 | 说明 |
|------|------|
| **R1：flow 只读 _summary** | 做调度决策时只读前 ~15 行（_meta + _summary），不读 data |
| **R2：下游读上游的 data** | search 读 stage1 的 data；selector 读 stage2 的 data |
| **R3：按需精确读取** | 大文件用 offset/limit 读取特定 resource，不整文件加载 |
| **R4：manifest 是入口** | 任何 Skill 开始工作时，先读 manifest.json 确认上游文件名 |

### 5.3 上下文规则（Context）

| 规则 | 说明 |
|------|------|
| **C1：上下文中只保留摘要** | session_id + 各阶段 _summary，不超过 ~20 行 |
| **C2：不在上下文中展开 data** | Skill 返回 flow 时只说"已写入 {文件名}" + _summary |
| **C3：展示给用户时从文件读** | 需要展示候选列表等，从文件读取后渲染，不靠上下文记忆 |

---

## 六、数据流转流程

### 6.1 完整流程（单次需求）

```
[1] flow 收到新需求
     │
     ├─ 创建 {session_dir}
     ├─ 写 manifest.json（status=in_progress, current_stage=1）
     │
     ▼
[2] flow 调用 intent
     │  告知：读无上游（第一个阶段）
     │       写 {session_dir}/stage1_intent.json
     │
     ├─ intent 分析需求
     ├─ intent 写 stage1_intent.json（_meta + _summary + data）
     ├─ intent 返回："已写入 stage1_intent.json" + _summary
     │
     ├─ flow 更新 manifest.json（stage1=completed, current_stage=2）
     ├─ flow 读 stage1 的 _summary → 展示任务确认给用户
     │
     ▼
[3] flow 调用 search
     │  告知：读 {session_dir}/stage1_intent.json 的 data
     │       写 {session_dir}/stage2_search.json
     │
     ├─ search 读 stage1 的 data → 提取 queries
     ├─ search 分发各平台搜索（subprocess）
     ├─ search 汇总去重排序
     ├─ search 写 stage2_search.json（_meta + _summary + data）
     ├─ search 返回："已写入 stage2_search.json" + _summary
     │
     ├─ flow 更新 manifest.json（stage2=completed, current_stage=3）
     │
     ▼
[4] flow 调用 selector
     │  告知：读 {session_dir}/stage2_search.json 的 data
     │       写 {session_dir}/stage3_select.json
     │
     ├─ selector 读 stage2 的 data → 渲染候选卡片展示给用户
     ├─ 用户选择
     ├─ selector 写 stage3_select.json（_meta + _summary + data）
     ├─ selector 返回："已写入 stage3_select.json" + _summary
     │
     ├─ flow 更新 manifest.json（stage3=completed, current_stage=4）
     │
     ▼
[5] flow 调用 downloader（同理）
     │  读 stage3 data → 处理 → 写 stage4 → 返回摘要
     │
     ▼
[6] flow 调用 library-manager（同理）
     │  读 stage4 data → 归档 → 写 stage5 → 返回摘要
     │
     ├─ flow 更新 manifest.json（stage5=completed, status=completed）
     ├─ flow 输出最终汇总报告（读各阶段 _summary 拼接）
     │
     ▼
[完成]
```

### 6.2 上下文中的数据量对比

| 时间点 | 纯上下文方案 | 文件持久化方案 |
|--------|:-----------:|:------------:|
| 阶段一完成后 | ~500行 | ~5行（摘要） |
| 阶段二完成后 | ~2500行 | ~10行（摘要） |
| 阶段三完成后 | ~3000行 | ~15行（摘要） |
| 阶段四完成后 | ~4000行 | ~20行（摘要） |
| 阶段五完成后 | ~5000行 | ~25行（摘要） |

---

## 七、需求类型与处理策略

flow 根据用户意图选择操作（语义理解，非死规则）：

| 用户意图 | 识别特征 | flow 的操作 |
|---------|---------|------------|
| **新需求** | 用户提出新的搜索/下载主题 | 创建新会话目录，从 stage1 开始 |
| **继续当前会话** | "刚才那个""加选几个""换一个" | 上下文中已有 session_id，从指定阶段继续 |
| **查询已归档资源** | "我之前存的""上次下载的在哪" | 调用 library-manager 查资料库索引（不碰 sessions/） |
| **恢复中断任务** | "继续上次没下完的" | `ls sessions/`，让用户确认哪个会话，从 manifest 的 current_stage 继续 |

> **重要**：搜索结果是时效性数据，**不自动复用旧的搜索结果**。每次新需求都重新搜索。

---

## 八、特殊场景处理

### 8.1 阶段重做（用户改主意）

```
用户："刚才选的那个，换成另一个"

flow 操作：
  1. 找到当前 session_id（上下文中已有）
  2. 读 manifest.json → stage3=completed
  3. 重新调用 selector（读 stage2 的 data 重新展示）
  4. selector 覆盖 stage3_select.json
  5. 重新跑 stage4/stage5（覆盖 stage4/stage5 文件）
```

### 8.2 搜索结果为空

```
search 写 stage2_search.json：
  _summary: {"total_count": 0}
  data: {"total_count": 0, "resources": []}

flow 读 _summary → total_count=0
  → 主动询问用户是否放宽条件
```

### 8.3 下载部分失败

```
downloader 正常写 stage4_download.json（data.resources 中含 failed 的资源）
  → flow 读 _summary → failed_count > 0
  → 展示失败原因，询问是否重试
```

### 8.4 对话中断恢复

```
新对话开始，用户："继续上次那个数学题"

flow 操作：
  1. ls .learning-resource-work/sessions/
  2. 读各目录的 manifest.json（只读 user_request + status + current_stage）
  3. 找到匹配的会话，展示给用户确认
  4. 用户确认后，从 current_stage 继续执行
```

---

## 九、与现有规范的关系

| 现有规范 | 关系 | 变化 |
|---------|------|------|
| `skill-contract.md` | **data 内部不变** | 只新增 _meta/_summary 包装层 |
| `resource-schema.md` | **不变** | data 内部字段仍遵循此规范 |
| `platform_base.py` | **不变** | 平台脚本仍输出到临时文件，search 读取后写入 stage2 |
| `platform-search/download-contract.md` | **不变** | 平台接口契约不受影响 |

### skill-contract.md 需要补充的部分

在 skill-contract.md 末尾新增一节：

```markdown
## 文件持久化包装（Session I/O）

各阶段输出不再直接放入上下文，而是写入文件。
每个阶段文件包含三层：

- `_meta`：元数据（stage / session_id / created_at / input_from）
- `_summary`：摘要（≤50字，供 flow 调度决策）
- `data`：完整业务数据（遵循上述各阶段契约）

详细规范见 `session-io-spec.md`。
```

---

## 十、实现清单

| 优先级 | 文件 | 改动 |
|--------|------|------|
| P0 | `shared/schemas/session-io-spec.md`（本文件） | 新建 |
| P0 | `shared/schemas/skill-contract.md` | 末尾追加文件持久化包装说明 |
| P0 | `learning-resource-flow/SKILL.md` | 新增 ~40行会话管理指令 |
| P1 | `resource-intent/SKILL.md` | 新增 ~5行文件读写约定 |
| P1 | `resource-search/SKILL.md` | 新增 ~5行文件读写约定 |
| P1 | `resource-selector/SKILL.md` | 新增 ~5行文件读写约定 |
| P1 | `resource-downloader/SKILL.md` | 新增 ~5行文件读写约定 |
| P1 | `library-manager/SKILL.md` | 新增 ~5行文件读写约定 |
| P2 | `.gitignore` | 新增 `.learning-resource-work/` |
