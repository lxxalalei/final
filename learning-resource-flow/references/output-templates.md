# 结构化输出模板规范

> 本文件定义 learning-resource-flow 结果反馈阶段（阶段六）及各中间阶段的标准化输出模板。
> 所有字段名称和语义严格遵循 [`../../shared/schemas/resource-schema.md`](../../shared/schemas/resource-schema.md)（v2.2）。
> 质量等级语义遵循 [`../../shared/schemas/quality-rubric.md`](../../shared/schemas/quality-rubric.md)（v1.0）。
> 错误码遵循 [`../../shared/schemas/error-codes.md`](../../shared/schemas/error-codes.md)（v1.0）。
> 跨阶段字段传递遵循 [`../../shared/schemas/skill-contract.md`](../../shared/schemas/skill-contract.md)（v1.0）。

---

## 目录

- [一、设计原则](#一设计原则)
- [二、模板 A：资源搜索结果卡片](#二模板-a资源搜索结果卡片)
- [三、模板 B：下载进度展示](#三模板-b下载进度展示)
- [四、模板 C：入库状态卡片](#四模板-c入库状态卡片)
- [五、模板 D：最终汇总报告](#五模板-d最终汇总报告)
- [六、JSON Schema 结构化规范](#六json-schema-结构化规范)
- [七、模板与 Schema 字段映射关系](#七模板与-schema-字段映射关系)

---

## 一、设计原则

| 原则 | 说明 |
|------|------|
| **直接渲染** | 实际向用户输出时，渲染版模板直接在对话中渲染，**禁止用代码框包裹**。本规范文档内的渲染版示例用代码块包裹，仅为完整保留换行与缩进，不代表实际输出形式 |
| **保留视觉标记** | emoji（⭐📺📁🎯📊⏱️📥🔍等）和星级评分是重要的视觉辅助，**必须保留**；仅禁止制表符线框（┌┐└┘─│║╔╠等） |
| **字段一致** | 模板中的每一个字段名、类型、取值范围必须与 `resource-schema.md` 一致，不得自行改名 |
| **双格式输出** | 每个模板同时提供 Markdown 渲染版（人读）和 JSON 结构版（机读） |
| **阶段对齐** | 模板 A/B/C 对应阶段二/四/五的中间反馈，模板 D 对应阶段六的最终汇总 |
| **只增不删** | 遵循 `skill-contract.md` 的完整透传原则，下游模板是上游字段的超集 |
| **可选字段省略** | JSON 中可选字段无值时省略该键（不输出 null），减少噪音 |

---

## 二、模板 A：资源搜索结果卡片

> **适用阶段**：阶段二（搜索召回）→ 阶段三（候选展示）
> **对应契约**：skill-contract.md「候选资源列表」
> **字段来源**：resource-schema.md「核心字段」+「搜索阶段新增字段」

### A.1 Markdown 渲染版

> ⚠️ 以下为**渲染效果示例**。在本规范中用代码块包裹仅为完整保留换行与缩进；**实际向用户输出时直接渲染，不加代码框**。

```text
🔍 为您找到 22 个优质资源，按质量从高到低排序

📺 B站视频（8个）
─────────────────────────────────────
1. ⭐ S级 · 小学必背古诗文动画（228集完整版）
   ├─ 来源：B站（bilibili）
   ├─ 类型：视频  ·  学科：语文
   ├─ 适龄：6-12岁  ·  小学全年级
   ├─ 播放 500万+  ·  点赞 8.2万
   ├─ 时长：共228集 · 约15小时
   ├─ 链接：https://www.bilibili.com/video/BV1xx411c7mD
   ├─ 简介：动画形式逐首讲解小学必背古诗文，含朗诵、释义和意境画面
   ├─ 标签：#古诗 #动画 #必背 #系统课程
   └─ 下载可行性：中（可能需要重试）

2. ⭐ A级 · 四则混合运算系统讲解（12集）
   ├─ 来源：B站（bilibili）
   ├─ 类型：视频  ·  学科：数学
   ├─ 适龄：7-9岁  ·  小学三年级
   ├─ 播放 12.5万  ·  点赞 3200
   ├─ 时长：120分钟（共12集）
   ├─ 链接：https://www.bilibili.com/video/BV2xx411c8mD
   ├─ 简介：系统讲解四则混合运算的顺序和技巧，动画形式
   ├─ 标签：#四则运算 #混合运算 #动画讲解
   └─ 下载可行性：高

💡 选择方式
─────────────────────────────────────
• 回复数字编号（如：1,3 或 1 3）
• 回复"全部"下载所有
• 回复"视频"只选视频类
• 回复"S级"只选S级
• 回复"不要了"取消下载
```

### A.2 单卡片 Markdown 模板（可复用）

> ⚠️ 以下为**模板骨架**（含占位符），用代码框包裹是为了展示占位符语法。实际输出渲染版时不加代码框。

```markdown
{序号} ⭐ {等级}级 · {title}
   ├─ 来源：{source_name}（{platform}）
   ├─ 类型：{type}  ·  学科：{subject}
   ├─ 适龄：{age_range}  ·  {grade_level}
   ├─ 播放 {view_count}  ·  点赞 {like_count}
   ├─ 时长：{duration}
   ├─ 链接：{source_url}
   ├─ 简介：{description}
   ├─ 标签：{tags 以 # 分隔}
   └─ 下载可行性：{download_feasibility}
{thumbnail_line}
```

> `{thumbnail_line}` 定义：当资源有封面图时输出 `🖼️ {thumbnail_url}`，无封面图时省略此行。

**等级标识映射**（取自 quality-rubric.md）：

| quality_level | 显示 | 星级标识 |
|---------------|------|---------|
| `S` | `⭐ S级` | 最高质量 |
| `A` | `⭐ A级` | 优质推荐 |
| `B` | `B级` | 一般可用 |
| `C` | `C级` | 仅供参考 |

> S/A 级带 ⭐ 标识突出推荐，B/C 级不带星，视觉上自然区分质量层次。

**下载可行性标识**：

| download_feasibility | 显示 |
|----------------------|------|
| `高` | `高` |
| `中` | `中（可能需要重试）` |
| `低` | `低（大概率只能降级获取）` |

### A.3 JSON 结构版

```json
{
  "phase": "search",
  "template": "search_result_card",
  "total_count": 22,
  "search_summary": "查询4组关键词，覆盖5个平台，召回58条，初筛过滤36条，最终保留22条候选",
  "resources": [
    {
      "resource_id": "bilibili:BV1xx411c7mD",
      "title": "小学必背古诗文动画（228集完整版）",
      "type": "视频",
      "subject": "语文",
      "platform": "bilibili",
      "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
      "source_name": "B站",
      "quality_level": "S",
      "download_feasibility": "中",
      "platform_quality_score": 92,
      "description": "动画形式逐首讲解小学必背古诗文，含朗诵、释义和意境画面，孩子容易接受。",
      "age_range": "6-12岁",
      "grade_level": "小学全年级",
      "tags": ["古诗", "动画", "必背", "系统课程"],
      "view_count": 5000000,
      "like_count": 82000,
      "duration": "共228集 · 约15小时",
      "language": "中文",
      "author": "语文启蒙课堂",
      "thumbnail_url": "https://i0.hdslb.com/bfs/archive/cover.jpg",
      "publish_time": "2024-03-15T08:00:00Z"
    },
    {
      "resource_id": "bilibili:BV2xx411c8mD",
      "title": "四则混合运算系统讲解（12集）",
      "type": "视频",
      "subject": "数学",
      "platform": "bilibili",
      "source_url": "https://www.bilibili.com/video/BV2xx411c8mD",
      "source_name": "B站",
      "quality_level": "A",
      "download_feasibility": "高",
      "platform_quality_score": 82,
      "description": "系统讲解四则混合运算的顺序和技巧，动画形式，孩子容易理解。",
      "age_range": "7-9岁",
      "grade_level": "小学三年级",
      "tags": ["四则运算", "混合运算", "动画讲解"],
      "view_count": 125000,
      "like_count": 3200,
      "duration": "120分钟（共12集）",
      "language": "中文"
    }
  ]
}
```

---

## 三、模板 B：下载进度展示

> **适用阶段**：阶段四（下载获取）进行中的实时反馈
> **对应契约**：skill-contract.md「下载结果列表」的实时中间态
> **字段来源**：resource-schema.md「核心字段」+ 下载过程实时数据

### B.1 Markdown 渲染版

> ⚠️ 以下为**渲染效果示例**。在本规范中用代码块包裹仅为完整保留换行与缩进；**实际向用户输出时直接渲染，不加代码框**。

```text
📥 正在下载 5 个资源
─────────────────────────────────────

1. 四则混合运算系统讲解（12集）
   📺 B站 · MP4 视频
   ████████████████████░░░░░░  78%
   199.2 MB / 256.0 MB  ·  5.2 MB/s  ·  约11秒
   状态：下载中

2. 古诗动画合集（50集）
   📺 B站 · MP4 视频
   ████████████████████████████  100%
   512.0 MB  ·  ✅ 完成

3. 练习题PDF（含答案）
   📄 智慧教育平台 · PDF 文档
   ████░░░░░░░░░░░░░░░░░░░░░░░░  15%
   0.3 MB / 2.0 MB  ·  120 KB/s  ·  约15秒
   ⚠ 速度较慢

4. 科普纪录片：恐龙的世界
   📺 B站 · MP4 视频
   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0%
   排队中...

5. 数学思维训练音频课
   🎵 喜马拉雅 · MP3 音频
   ████████████████░░░░░░░░░░░░  55%
   27.5 MB / 50.0 MB  ·  2.0 MB/s  ·  约11秒
```

> 注：模板 B 的 `summary.completed` 对应模板 D 的 `download_statistics.success_count`。
> 任务状态映射：`completed` → `success`，`downloading/queued/paused` → 不计入 D，
> `failed` → `failed`（需在该任务的 `result` 中填充 `download_status: "failed"`）。

### B.2 单任务 Markdown 模板（可复用）

> ⚠️ 以下为**模板骨架**（含占位符），用代码框包裹是为了展示占位符语法。

```markdown
{序号} {title}
   {type_emoji} {source_name} · {file_format} {type}
   {progress_bar}  {percentage}%
   {downloaded_size} / {total_size}  ·  {speed}  ·  {eta}
{status_line}
```

**资源类型 emoji 映射**：

| type | emoji |
|------|-------|
| 视频 | 📺 |
| 音频 | 🎵 |
| 文档 | 📄 |
| 练习题 | ✏️ |
| 绘本 | 📖 |
| 课件 | 📊 |
| 图片 | 🖼️ |

**进度条规则**：

```
总宽度：28 个字符块
已完成：█
未完成：░
百分比 = 已下载字节数 / 文件总大小 × 100，向下取整
示例：78% → ████████████████████░░░░░░（22块█ + 6块░）
```

**状态行规则**：

| status 值 | status_line 内容 |
|-----------|-----------------|
| `queued` | `   排队中...` |
| `downloading` | `   状态：下载中`（正常）或 `   ⚠ {warning}`（异常） |
| `completed` | `   ✅ 完成` |
| `failed` | `   ❌ 失败：{error_message}` |
| `paused` | `   ⏸ 已暂停` |

**速度提示**：

| 速度范围 | 提示 |
|---------|------|
| > 1 MB/s | （不显示，正常速度） |
| 100 KB/s ~ 1 MB/s | （不显示，可接受） |
| < 100 KB/s | `   ⚠ 速度较慢` |

**文件大小格式化**：

| 范围 | 格式 | 示例 |
|------|------|------|
| < 1 KB | `{n} B` | `512 B` |
| 1 KB ~ 1 MB | `{n.n} KB` | `45.3 KB` |
| 1 MB ~ 1 GB | `{n.n} MB` | `256.0 MB` |
| > 1 GB | `{n.nn} GB` | `1.25 GB` |

### B.3 JSON 结构版（实时快照）

```json
{
  "phase": "download",
  "template": "download_progress",
  "batch_id": "batch-20240615-001",
  "total_count": 5,
  "summary": {
    "completed": 1,
    "downloading": 3,
    "queued": 1,
    "failed": 0
  },
  "tasks": [
    {
      "resource_id": "bilibili:BV2xx411c8mD",
      "title": "四则混合运算系统讲解（12集）",
      "platform": "bilibili",
      "source_name": "B站",
      "type": "视频",
      "file_format": "mp4",
      "status": "downloading",
      "progress": {
        "downloaded_bytes": 208666624,
        "total_bytes": 268435456,
        "percentage": 78,
        "speed_bps": 5452595,
        "eta_seconds": 11
      }
    },
    {
      "resource_id": "bilibili:BV3xx411c9mD",
      "title": "古诗动画合集（50集）",
      "platform": "bilibili",
      "source_name": "B站",
      "type": "视频",
      "file_format": "mp4",
      "status": "completed",
      "progress": {
        "downloaded_bytes": 536870912,
        "total_bytes": 536870912,
        "percentage": 100,
        "speed_bps": null,
        "eta_seconds": null
      },
      "result": {
        "download_status": "success",
        "file_path": "语文/小学全年级/古诗/B站-古诗动画合集.mp4",
        "file_size": 536870912,
        "fetch_time": "2024-06-15T10:32:00Z",
        "fetch_method": "下载",
        "degraded_level": "Level 0"
      }
    }
  ]
}
```

---

## 四、模板 C：入库状态卡片

> **适用阶段**：阶段五（归档入库）→ 阶段六（结果反馈）
> **对应契约**：skill-contract.md「归档结果列表」
> **字段来源**：resource-schema.md「下载阶段新增字段」+「归档阶段新增字段」

### C.1 Markdown 渲染版

> ⚠️ 以下为**渲染效果示例**。在本规范中用代码块包裹仅为完整保留换行与缩进；**实际向用户输出时直接渲染，不加代码框**。

```text
📁 资源入库状态
═════════════════════════════════════

✅ 完整入库（1个）
─────────────────────────────────────
1. 四则混合运算系统讲解（12集）
   📺 B站 · 视频 · ⭐ A级
   📂 数学/小学三年级/四则混合运算/
      B站-四则混合运算讲解.mp4
   📦 256.0 MB · MP4 · 1920x1080
   ⏱ 获取于 2024-06-15 10:32 · 归档于 10:35
   🔒 sha256:a1b2c3d4e5f6...
   🎯 完整下载 · Level 0

⚠️ 降级入库（1个）
─────────────────────────────────────
2. 高级数学思维课（付费内容）
   📺 B站 · 视频 · B级
   📂 数学/小学三年级/思维训练/
      B站-高级数学思维课_摘要.md
   📦 12.5 KB · Markdown · 课程大纲+核心要点
   ⏱ 获取于 2024-06-15 10:40
   📝 降级原因：付费内容，无法下载完整版
   🎯 降级获取 · Level 2（核心摘要）
   🔗 原始链接：https://www.bilibili.com/video/BV5xx

🔀 去重跳过（1个）
─────────────────────────────────────
3. 四则运算练习题（抖音版）
   📄 抖音 · 文档 · ⭐ A级
   未归档（检测到重复）
   与已入库资源内容一致：
      [智慧教育平台] 四则运算练习题（含答案）⭐ S级
   → 已跳过，保留 S 级版本
   匹配类型：内容指纹（MD5 精确匹配）

❌ 入库失败（1个）
─────────────────────────────────────
4. 数学纪录片：数学的故事
   📺 B站 · 视频 · ⭐ A级
   ❌ 失败原因：被反爬系统拦截
   🔧 错误码：ANTI_CRAWL_BLOCKED
   💡 建议：稍后重试或手动访问链接
   🔗 https://www.bilibili.com/video/BV6xx
   📦 已保存：标题 + 简介 + 来源链接 · Level 3
   📂 数学/小学三年级/数学故事/
      B站-数学的故事_链接收藏.md
```

### C.2 单卡片 Markdown 模板（可复用）

> ⚠️ 以下为**模板骨架**（含占位符），用代码框包裹是为了展示占位符语法。

**成功（success / Level 0）**：

```markdown
✅ 完整入库
{序号} {title}
   {type_emoji} {source_name} · {type} · {星级标识}{等级}级
   📂 {library_path}
      {file_basename}
   📦 {file_size_formatted} · {file_format} {resolution_line}
   ⏱ 获取于 {fetch_time_short} · 归档于 {archive_time_short}
{checksum_line}
   🎯 完整下载 · Level 0
```

**降级（degraded / Level 1-2）**：

```markdown
⚠️ 降级入库
{序号} {title}
   {type_emoji} {source_name} · {type} · {星级标识}{等级}级
   📂 {library_path}
      {file_basename}
   📦 {file_size_formatted} · {file_format}
   ⏱ 获取于 {fetch_time_short}
   📝 降级原因：{degraded_reason}
   🎯 降级获取 · {degraded_level}（{degraded_level_desc}）
   🔗 原始链接：{source_url}
```

**去重跳过（deduplicated）**：

```markdown
🔀 去重跳过
{序号} {title}
   {type_emoji} {source_name} · {type} · {星级标识}{等级}级
   未归档（检测到重复）
   与已入库资源{dedup_relation}：
      [{retained_source_name}] {retained_title} {retained_星级标识}{retained_level}级
   → {dedup_action}
   匹配类型：{dedup_match_type_desc}
```

**失败（failed / Level 3）**：

```markdown
❌ 入库失败
{序号} {title}
   {type_emoji} {source_name} · {type} · {星级标识}{等级}级
   ❌ 失败原因：{error_message}
   🔧 错误码：{error_code}
   💡 建议：{suggested_action_desc}
   🔗 {source_url}
{fallback_line}
   📂 {library_path or "未归档"}
      {file_basename}
```

> `{fallback_line}` 定义：当 failed 资源有降级保存内容时输出 `📦 已保存：标题 + 简介 + 来源链接 · Level 3`，无降级内容时省略此行。
> `{thumbnail_line}` 定义（模板 A）：当资源有封面图时输出 `🖼️ {thumbnail_url}`，无封面图时省略此行。

**星级标识映射**（与模板 A 一致）：

| quality_level | 星级标识 |
|---------------|---------|
| `S` | `⭐ ` |
| `A` | `⭐ ` |
| `B` | （无） |
| `C` | （无） |

**降级等级显示映射**（取自 error-codes.md）：

| degraded_level | 描述 | 显示 |
|----------------|------|------|
| `Level 0` | 完整版本 | `完整下载 · Level 0` |
| `Level 1` | 预览版本 | `降级获取 · Level 1（预览版本）` |
| `Level 2` | 核心摘要 | `降级获取 · Level 2（核心摘要）` |
| `Level 3` | 来源链接 | `降级获取 · Level 3（来源链接）` |

### C.3 JSON 结构版

```json
{
  "phase": "archive",
  "template": "archive_status",
  "total_count": 4,
  "summary": {
    "success_count": 1,
    "degraded_count": 1,
    "failed_count": 1,
    "deduplicated_count": 1,
    "skipped_count": 0
  },
  "resources": [
    {
      "resource_id": "bilibili:BV2xx411c8mD",
      "title": "四则混合运算系统讲解（12集）",
      "type": "视频",
      "subject": "数学",
      "platform": "bilibili",
      "source_name": "B站",
      "source_url": "https://www.bilibili.com/video/BV2xx411c8mD",
      "quality_level": "A",
      "download_status": "success",
      "degraded_level": "Level 0",
      "file_path": "数学/小学三年级/四则混合运算/B站-四则混合运算讲解.mp4",
      "file_size": 268435456,
      "file_format": "mp4",
      "resolution": "1920x1080",
      "fetch_time": "2024-06-15T10:32:00Z",
      "fetch_method": "下载",
      "checksum": "sha256:a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
      "library_path": "数学/小学三年级/四则混合运算/",
      "archive_time": "2024-06-15T10:35:00Z",
      "dedup_status": "new"
    }
  ]
}
```

---

## 五、模板 D：最终汇总报告

> **适用阶段**：阶段六（结果反馈）— 工作流的最终输出
> **对应契约**：skill-contract.md 全链路汇总
> **字段来源**：整合 resource-schema.md 所有阶段字段

### D.1 Markdown 渲染版

> ⚠️ 以下为**渲染效果示例**。在本规范中用代码块包裹仅为完整保留换行与缩进；**实际向用户输出时直接渲染，不加代码框**。

```text
📊 资源获取任务报告
═════════════════════════════════════

📋 任务概要
─────────────────────────────────────
• 需求描述：给小学三年级孩子找四则混合运算的学习资源
• 核心主题：四则混合运算
• 目标年龄：8-9岁（小学三年级）
• 资源类型：综合（视频+文档+练习题）
• 搜索模式：标准模式
• 任务时间：2024-06-15 10:00 ~ 10:55（耗时约55分钟）
• 任务ID：task-20240615-001

🔍 搜索统计
─────────────────────────────────────
• 查询关键词：4组（核心+官方+形态+长尾）
• 覆盖平台：5个（B站、智慧教育、知乎、抖音、喜马拉雅）
• 召回数量：58条
• 初筛过滤：36条（质量不达标/不相关/安全过滤）
• 最终候选：22条
• 用户选择：5条

📥 下载统计
─────────────────────────────────────
• ✅ 完整下载：1个（256.0 MB）
• ⚠️ 降级获取：1个（摘要版）
• ❌ 下载失败：1个（反爬拦截）
• 🔀 去重跳过：1个（与已有资源重复）
• 合计处理：4个 · 实际入库：2个

📁 入库资源清单
─────────────────────────────────────

✅ 完整入库（1个）
  1. 四则混合运算系统讲解（12集）
     → 数学/小学三年级/四则混合运算/B站-四则混合运算讲解.mp4
     256.0 MB · MP4 · ⭐ A级

⚠️ 降级入库（1个）
  2. 高级数学思维课（付费内容）
     → 数学/小学三年级/思维训练/B站-高级数学思维课_摘要.md
     12.5 KB · Markdown · B级
     Level 2 核心摘要（付费内容，无法下载完整版）

❌ 失败降级（1个）
  3. 数学纪录片：数学的故事
     → 数学/小学三年级/数学故事/B站-数学的故事_链接收藏.md
     2.0 KB · Markdown · A级
     Level 3 来源链接（被反爬拦截）
     可稍后重试或手动访问：
        https://www.bilibili.com/video/BV6xx411c2mD

🔀 去重跳过（1个）
  4. 四则运算练习题（抖音版）
     与已入库资源内容一致 → 已跳过
     保留了更高质量版本：智慧教育平台 ⭐ S级

📊 质量分布（入库资源）
─────────────────────────────────────
• ⭐ S级：0个
• ⭐ A级：1个
• B级：1个
• C级：0个

📁 资料库路径
─────────────────────────────────────
• 学习资料库/数学/小学三年级/四则混合运算/
• 学习资料库/数学/小学三年级/思维训练/
• 学习资料库/数学/小学三年级/数学故事/

💡 后续建议
─────────────────────────────────────
• 下次搜索类似需求时会优先复用已入库资源
• 失败的资源可稍后重试（反爬拦截通常可恢复）
• 付费内容建议关注平台活动，免费开放时再获取
• 如需更多资源，可尝试"穷尽模式"搜索
```

### D.2 JSON 结构版

```json
{
  "phase": "final_report",
  "template": "summary_report",
  "version": "1.0",
  "generated_at": "2024-06-15T10:55:00Z",
  "task_id": "task-20240615-001",
  "task_summary": {
    "description": "给小学三年级孩子找四则混合运算的学习资源",
    "core_topic": "四则混合运算",
    "target_age": "8-9岁（小学三年级）",
    "grade_level": "小学三年级",
    "resource_types": ["视频", "文档", "练习题"],
    "search_mode": "standard",
    "started_at": "2024-06-15T10:00:00Z",
    "completed_at": "2024-06-15T10:55:00Z",
    "duration_seconds": 3300,
    "assumptions": [
      "孩子年龄：8-9岁（小学三年级）",
      "资源类型：综合推荐"
    ]
  },
  "search_statistics": {
    "query_count": 4,
    "platforms_searched": ["bilibili", "smartedu", "zhihu", "douyin", "ximalaya"],
    "platform_count": 5,
    "total_recall": 58,
    "filtered_out": 36,
    "final_candidates": 22,
    "user_selected": 5,
    "search_summary": "查询4组关键词，覆盖5个平台，召回58条，初筛过滤36条，最终保留22条候选"
  },
  "download_statistics": {
    "total_count": 4,
    "success_count": 1,
    "degraded_count": 1,
    "failed_count": 1,
    "deduplicated_count": 1,
    "total_downloaded_bytes": 268459008,
    "max_concurrent": 3,
    "retry_count": 4
  },
  "archive_statistics": {
    "archived_count": 2,
    "skipped_count": 1,
    "failed_count": 1,
    "library_base_path": "学习资料库/"
  },
  "quality_distribution": {
    "S": 0,
    "A": 1,
    "B": 1,
    "C": 0
  },
  "resources": [],
  "library_paths": [
    "学习资料库/数学/小学三年级/四则混合运算/",
    "学习资料库/数学/小学三年级/思维训练/",
    "学习资料库/数学/小学三年级/数学故事/"
  ],
  "suggestions": [
    "下次搜索类似需求时会优先复用已入库资源",
    "失败的资源可稍后重试（反爬拦截通常可恢复）",
    "付费内容建议关注平台活动，免费开放时再获取",
    "如需更多资源，可尝试\"穷尽模式\"搜索"
  ]
}
```

---
## 六、JSON Schema 结构化规范

> 以下 JSON Schema 定义了各模板的程序化验证规范，可用于自动化校验输出格式是否合规。
> 字段名和取值范围严格对齐 resource-schema.md v2.2。

### 6.1 公共定义（$defs）

```json
{
  "$defs": {
    "quality_level_enum": {
      "type": "string",
      "enum": ["S", "A", "B", "C"],
      "description": "质量等级，语义见 quality-rubric.md"
    },
    "download_status_enum": {
      "type": "string",
      "enum": ["success", "degraded", "failed"],
      "description": "下载状态三态"
    },
    "degraded_level_enum": {
      "type": "string",
      "enum": ["Level 0", "Level 1", "Level 2", "Level 3"],
      "description": "降级等级：Level 0=完整, Level 1=预览, Level 2=摘要, Level 3=链接"
    },
    "download_feasibility_enum": {
      "type": "string",
      "enum": ["高", "中", "低"],
      "description": "下载可行性预估"
    },
    "dedup_status_enum": {
      "type": "string",
      "enum": ["new", "duplicate", "skipped"],
      "description": "去重状态"
    },
    "dedup_match_type_enum": {
      "type": "string",
      "enum": ["exact", "url", "similar_title", "resource_id"],
      "description": "去重匹配类型"
    },
    "task_status_enum": {
      "type": "string",
      "enum": ["queued", "downloading", "completed", "failed", "paused"],
      "description": "下载任务实时状态"
    },
    "error_code_enum": {
      "type": "string",
      "description": "标准错误码，取值见 error-codes.md",
      "pattern": "^(NETWORK_|ANTI_CRAWL_|AUTH_|CONTENT_|PARSE_|DOWNLOAD_|SYSTEM_)[A-Z_]+$"
    },
    "resource_core_fields": {
      "type": "object",
      "description": "资源核心字段（必选），对齐 resource-schema.md",
      "required": [
        "resource_id", "title", "type", "subject",
        "platform", "source_url", "source_name",
        "quality_level", "download_feasibility"
      ],
      "properties": {
        "resource_id": { "type": "string", "pattern": "^[a-z]+:.+" },
        "title": { "type": "string" },
        "type": { "type": "string" },
        "subject": { "type": "string" },
        "platform": { "type": "string" },
        "source_url": { "type": "string", "format": "uri" },
        "source_name": { "type": "string" },
        "quality_level": { "$ref": "#/$defs/quality_level_enum" },
        "download_feasibility": { "$ref": "#/$defs/download_feasibility_enum" }
      }
    },
    "search_fields": {
      "type": "object",
      "description": "搜索阶段新增字段（推荐/可选）",
      "properties": {
        "platform_quality_score": { "type": "number", "minimum": 0, "maximum": 100 },
        "description": { "type": "string" },
        "age_range": { "type": "string" },
        "grade_level": { "type": "string" },
        "tags": { "type": "array", "items": { "type": "string" } },
        "view_count": { "type": "number" },
        "like_count": { "type": "number" },
        "duration": { "type": "string" },
        "file_format": { "type": "string" },
        "language": { "type": "string" },
        "publish_time": { "type": "string", "format": "date-time" },
        "thumbnail_url": { "type": "string", "format": "uri" },
        "author": { "type": "string" }
      }
    },
    "download_fields": {
      "type": "object",
      "description": "下载阶段新增字段",
      "required": ["download_status", "file_path", "file_size", "fetch_time", "fetch_method"],
      "properties": {
        "download_status": { "$ref": "#/$defs/download_status_enum" },
        "file_path": { "type": "string" },
        "file_size": { "type": "number" },
        "fetch_time": { "type": "string", "format": "date-time" },
        "fetch_method": { "type": "string" },
        "error_code": { "$ref": "#/$defs/error_code_enum" },
        "error_message": { "type": "string" },
        "degraded_level": { "$ref": "#/$defs/degraded_level_enum" },
        "degraded_content": { "type": "string" },
        "checksum": { "type": "string" },
        "resolution": { "type": "string" },
        "bitrate": { "type": "number" }
      }
    },
    "archive_fields": {
      "type": "object",
      "description": "归档阶段新增字段",
      "required": ["library_path", "archive_time"],
      "properties": {
        "library_path": { "type": "string" },
        "archive_time": { "type": "string", "format": "date-time" },
        "dedup_status": { "$ref": "#/$defs/dedup_status_enum" },
        "is_duplicate": { "type": "boolean" },
        "duplicate_of": { "type": "string" },
        "dedup_match_type": { "$ref": "#/$defs/dedup_match_type_enum" }
      }
    }
  }
}
```

### 6.2 模板 A Schema：search_result_card

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "lrs://templates/search_result_card",
  "title": "Search Result Card",
  "type": "object",
  "required": ["phase", "template", "total_count", "resources"],
  "properties": {
    "phase": { "const": "search" },
    "template": { "const": "search_result_card" },
    "total_count": { "type": "integer", "minimum": 0 },
    "search_summary": { "type": "string" },
    "resources": {
      "type": "array",
      "items": {
        "allOf": [
            { "$ref": "#/$defs/resource_core_fields" },
            { "$ref": "#/$defs/search_fields" }
          ]
      }
    }
  }
}
```

### 6.3 模板 B Schema：download_progress

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "lrs://templates/download_progress",
  "title": "Download Progress",
  "type": "object",
  "required": ["phase", "template", "total_count", "tasks"],
  "properties": {
    "phase": { "const": "download" },
    "template": { "const": "download_progress" },
    "batch_id": { "type": "string" },
    "total_count": { "type": "integer", "minimum": 0 },
    "summary": {
      "type": "object",
      "properties": {
        "completed": { "type": "integer" },
        "downloading": { "type": "integer" },
        "queued": { "type": "integer" },
        "failed": { "type": "integer" }
      }
    },
    "tasks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["resource_id", "title", "platform", "status"],
        "properties": {
          "resource_id": { "type": "string" },
          "title": { "type": "string" },
          "platform": { "type": "string" },
          "source_name": { "type": "string" },
          "type": { "type": "string" },
          "file_format": { "type": "string" },
          "status": { "$ref": "#/$defs/task_status_enum" },
          "progress": {
            "type": ["object", "null"],
            "properties": {
              "downloaded_bytes": { "type": "number" },
              "total_bytes": { "type": "number" },
              "percentage": { "type": "integer", "minimum": 0, "maximum": 100 },
              "speed_bps": { "type": ["number", "null"] },
              "eta_seconds": { "type": ["number", "null"] }
            }
          },
          "warnings": { "type": "array", "items": { "type": "string" } },
          "result": {
            "type": "object",
            "description": "下载完成时的结果快照",
            "allOf": [
              { "$ref": "#/$defs/download_fields" }
            ]
          }
        }
      }
    }
  }
}
```

### 6.4 模板 C Schema：archive_status

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "lrs://templates/archive_status",
  "title": "Archive Status",
  "type": "object",
  "required": ["phase", "template", "total_count", "resources"],
  "properties": {
    "phase": { "const": "archive" },
    "template": { "const": "archive_status" },
    "total_count": { "type": "integer", "minimum": 0 },
    "summary": {
      "type": "object",
      "required": ["success_count", "degraded_count", "failed_count"],
      "properties": {
        "success_count": { "type": "integer" },
        "degraded_count": { "type": "integer" },
        "failed_count": { "type": "integer" },
        "deduplicated_count": { "type": "integer" },
        "skipped_count": { "type": "integer" }
      }
    },
    "resources": {
      "type": "array",
      "items": {
        "allOf": [
            { "$ref": "#/$defs/resource_core_fields" },
            { "$ref": "#/$defs/download_fields" },
            { "$ref": "#/$defs/archive_fields" },
            {
              "type": "object",
              "properties": {
                "dedup_detail": {
                  "type": "object",
                  "description": "去重详情（dedup_status 为 duplicate 时填充）",
                  "properties": {
                    "retained_resource_id": { "type": "string" },
                    "retained_title": { "type": "string" },
                    "retained_source_name": { "type": "string" },
                    "retained_quality_level": { "$ref": "#/$defs/quality_level_enum" },
                    "dedup_action": { "type": "string" }
                  }
                }
              }
            }
          ]
      }
    }
  }
}
```

### 6.5 模板 D Schema：summary_report

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "lrs://templates/summary_report",
  "title": "Final Summary Report",
  "type": "object",
  "required": ["phase", "template", "version", "generated_at", "task_id", "task_summary", "resources"],
  "properties": {
    "phase": { "const": "final_report" },
    "template": { "const": "summary_report" },
    "version": { "type": "string" },
    "generated_at": { "type": "string", "format": "date-time" },
    "task_id": { "type": "string" },
    "task_summary": {
      "type": "object",
      "required": ["description", "core_topic", "target_age", "search_mode", "started_at", "completed_at"],
      "properties": {
        "description": { "type": "string" },
        "core_topic": { "type": "string" },
        "target_age": { "type": "string" },
        "grade_level": { "type": "string" },
        "resource_types": { "type": "array", "items": { "type": "string" } },
        "search_mode": { "type": "string", "enum": ["standard", "exhaustive"] },
        "started_at": { "type": "string", "format": "date-time" },
        "completed_at": { "type": "string", "format": "date-time" },
        "duration_seconds": { "type": "number" },
        "assumptions": { "type": "array", "items": { "type": "string" } }
      }
    },
    "search_statistics": {
      "type": "object",
      "properties": {
        "query_count": { "type": "integer" },
        "platforms_searched": { "type": "array", "items": { "type": "string" } },
        "platform_count": { "type": "integer" },
        "total_recall": { "type": "integer" },
        "filtered_out": { "type": "integer" },
        "final_candidates": { "type": "integer" },
        "user_selected": { "type": "integer" },
        "search_summary": { "type": "string" }
      }
    },
    "download_statistics": {
      "type": "object",
      "required": ["total_count", "success_count", "degraded_count", "failed_count"],
      "properties": {
        "total_count": { "type": "integer" },
        "success_count": { "type": "integer" },
        "degraded_count": { "type": "integer" },
        "failed_count": { "type": "integer" },
        "deduplicated_count": { "type": "integer" },
        "total_downloaded_bytes": { "type": "number" },
        "max_concurrent": { "type": "integer" },
        "retry_count": { "type": "integer" }
      }
    },
    "archive_statistics": {
      "type": "object",
      "properties": {
        "archived_count": { "type": "integer" },
        "skipped_count": { "type": "integer" },
        "failed_count": { "type": "integer" },
        "library_base_path": { "type": "string" }
      }
    },
    "quality_distribution": {
      "type": "object",
      "properties": {
        "S": { "type": "integer" },
        "A": { "type": "integer" },
        "B": { "type": "integer" },
        "C": { "type": "integer" }
      }
    },
    "resources": {
      "type": "array",
      "description": "全链路资源记录（搜索+下载+归档字段完整透传）",
      "items": {
        "allOf": [
            { "$ref": "#/$defs/resource_core_fields" },
            { "$ref": "#/$defs/download_fields" },
            { "$ref": "#/$defs/archive_fields" },
            {
              "type": "object",
              "properties": {
                "dedup_detail": { "type": "object" },
                "suggested_action": { "type": "string" },
                "alternative_recommendations": { "type": "array", "items": { "type": "object" } }
              }
            }
          ]
      }
    },
    "library_paths": {
      "type": "array",
      "items": { "type": "string" }
    },
    "suggestions": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

---

## 七、模板与 Schema 字段映射关系

> 本表证明所有模板字段均有 `resource-schema.md` 的权威出处，无自造字段。

### 7.1 核心字段映射

| 模板字段 | resource-schema.md 出处 | 出现模板 | 必选 |
|---------|------------------------|---------|------|
| `resource_id` | 核心字段 | A/B/C/D | ✅ |
| `title` | 核心字段 | A/B/C/D | ✅ |
| `type` | 核心字段 | A/C/D | ✅ |
| `subject` | 核心字段 | A/C/D | ✅ |
| `platform` | 核心字段 | A/B/C/D | ✅ |
| `source_url` | 核心字段 | A/C/D | ✅ |
| `source_name` | 核心字段 | A/B/C/D | ✅ |
| `quality_level` | 核心字段（值语义见 quality-rubric.md） | A/C/D | ✅ |
| `download_feasibility` | 核心字段 | A | ✅ |

### 7.2 搜索字段映射

| 模板字段 | resource-schema.md 出处 | 出现模板 | 必选 |
|---------|------------------------|---------|------|
| `platform_quality_score` | 搜索阶段新增（0-100） | A（JSON） | ✅ |
| `description` | 搜索阶段新增 | A | ✅ |
| `age_range` | 搜索阶段新增 | A/D | 🟡 |
| `grade_level` | 搜索阶段新增 | A/D | 🟡 |
| `tags` | 搜索阶段新增 | A | 🟡 |
| `view_count` | 搜索阶段新增 | A | 🟡 |
| `like_count` | 搜索阶段新增 | A | 🟡 |
| `duration` | 搜索阶段新增 | A | 🟡 |
| `file_format` | 搜索阶段新增 | B/C | 🟡 |
| `language` | 搜索阶段新增 | A | 🟡 |
| `publish_time` | 搜索阶段新增 | A | ⚪ |
| `thumbnail_url` | 搜索阶段新增 | A | ⚪ |
| `author` | 搜索阶段新增 | A | ⚪ |

### 7.3 下载字段映射

| 模板字段 | resource-schema.md 出处 | 出现模板 | 必选 |
|---------|------------------------|---------|------|
| `download_status` | 下载阶段新增（success/degraded/failed） | B/C/D | ✅ |
| `file_path` | 下载阶段新增 | C/D | ✅ |
| `file_size` | 下载阶段新增 | B/C/D | ✅ |
| `fetch_time` | 下载阶段新增 | C/D | ✅ |
| `fetch_method` | 下载阶段新增 | C/D | ✅ |
| `error_code` | 下载阶段新增（值见 error-codes.md） | C/D | 🟡 |
| `error_message` | 下载阶段新增 | C/D | 🟡 |
| `degraded_level` | 下载阶段新增（Level 0-3） | C/D | 🟡 |
| `degraded_content` | 下载阶段新增 | C/D | 🟡 |
| `checksum` | 下载阶段新增 | C | ⚪ |
| `resolution` | 下载阶段新增 | C | ⚪ |
| `bitrate` | 下载阶段新增 | C | ⚪ |

### 7.4 归档字段映射

| 模板字段 | resource-schema.md 出处 | 出现模板 | 必选 |
|---------|------------------------|---------|------|
| `library_path` | 归档阶段新增 | C/D | ✅ |
| `archive_time` | 归档阶段新增 | C/D | ✅ |
| `is_duplicate` | 归档阶段新增（v2.2） | C/D | ⚪ |
| `duplicate_of` | 归档阶段新增（v2.2） | C/D | ⚪ |
| `dedup_match_type` | 归档阶段新增（v2.2） | C/D | ⚪ |

### 7.5 进度专用字段（模板 B 独有）

| 模板字段 | 说明 | 出处 |
|---------|------|------|
| `status` | 下载任务实时状态（queued/downloading/completed/failed/paused） | 本模板定义，仅用于实时中间态 |
| `progress.downloaded_bytes` | 已下载字节数 | 本模板定义 |
| `progress.total_bytes` | 文件总大小字节数 | 本模板定义 |
| `progress.percentage` | 百分比（0-100） | 本模板定义 |
| `progress.speed_bps` | 下载速度（字节/秒） | 本模板定义 |
| `progress.eta_seconds` | 预计剩余时间（秒） | 本模板定义 |

> **注**：模板 B 的进度字段是实时中间态数据，不属于 resource-schema.md 的持久化字段。
> 任务完成后，`result` 对象中的字段会回写为标准的 resource-schema.md 下载阶段字段。

---

