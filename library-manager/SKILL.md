---
name: library-manager
description: 本地学习资料库的归档、索引维护、检索复用与去重管理。负责将下载获取的资源按学科/年龄段/主题分类存放，维护完整的资源索引和元数据，并提供跨平台内容级去重能力，避免重复归档。
---

# library-manager · 资料库归档与管理

## 概述

本 Skill 是三层架构中的**业务能力层**，负责本地学习资料库的管理，包括资源归档、索引维护、检索复用等功能。

资料库是整个工作台的核心资产，目标是让用户搜索过的资源可以被复用，避免重复搜索和下载。

**上游**：resource-downloader（下载调度器）
**下游**：learning-resource-flow（总调度）、用户直接调用

---

## 适用场景

当需要执行以下任务时调用本 Skill：

- 将新获取的资源归档到资料库
- 检索资料库中已有的资源
- 更新资源索引和元数据
- 整理和优化资料库结构
- 统计资料库使用情况
- **跨平台内容去重**（检测并处理重复资源）

通常由 `learning-resource-flow` 在检索阶段和归档阶段调用，也可以独立用于资料库管理。

## 核心原则

1. **干净原则**：只保存最终资源，不保存临时文件
2. **复用优先**：优先检索已有资源，减少重复获取
3. **证据驱动**：每个资源都有完整的元数据和来源记录
4. **结构清晰**：按学科/年龄段/主题分层组织
5. **索引完善**：支持多维度检索和模糊匹配
6. **自动去重**：归档前自动检测跨平台重复内容，按策略处理

## 资料库结构

### 根目录

默认位置：`学习资料库/`（可配置）

### 目录结构

```
学习资料库/
├── 数学/                          # 学习领域或学科
│   ├── 全龄通用/                   # 不分年龄段的通用资源
│   │   └── 数学思维训练/
│   │       └── 来源或版本/
│   └── 小学三年级/                 # 学段或适龄
│       └── 四则混合运算/           # 主题或资源类型
│           └── K5Learning/         # 来源或版本
│               ├── 练习题.pdf
│               └── 答案解析.pdf
├── 语文/
│   ├── 小学一年级/
│   │   └── 拼音启蒙/
│   └── 全龄通用/
│       └── 绘本/
├── 英语/
├── 科普/
│   └── 恐龙主题/
├── 编程/
├── 艺术/
├── 综合主题/                       # 跨学科的主题资源
└── 待确认/                         # 分类证据不足的资源
```

### 目录命名规范

**学习领域/学科：**
- 使用通用名称：数学、语文、英语、科普、编程、艺术
- 不使用太细的分类

**学段/适龄：**
- 按年级：小学一年级、小学二年级...
- 按年龄：3-6岁、6-8岁、8-10岁...
- 全龄通用：不分年龄段的资源

**主题/资源类型：**
- 知识点或主题：四则混合运算、拼音启蒙、恐龙科普
- 资源类型：练习题、绘本、视频、课件

**来源/版本：**
- 网站或平台名称：K5Learning、B站、学科网
- 版本信息：人教版、苏教版、2024版

---

## 资源元数据

> **元数据规范**：本 Skill 的元数据严格遵循统一规范。以下是资料库归档阶段涉及的核心字段说明。

### 统一资源 ID

每个资源的唯一标识符格式为：`平台名:平台内ID`

**示例：**
- `bilibili:BV1xx411c7mD` - B站视频
- `ximalaya:album_123456` - 喜马拉雅专辑
- `baiduwenku:view_abc123` - 百度文库文档
- `generic:url_hash` - 通用网页/文件

### 必选字段（所有阶段通用）

每个资源都必须有以下元数据：

```json
{
  "resource_id": "bilibili:BV1xx411c7mD",
  "title": "小学必背古诗文动画（228集全）",
  "type": "视频",
  "subject": "语文",
  "platform": "bilibili",
  "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
  "source_name": "B站",
  "quality_level": "S",
  "download_feasibility": "中"
}
```

### 搜索阶段字段（来自 search）

```json
{
  "platform_quality_score": 90,
  "description": "动画形式讲解小学必背古诗，覆盖全部228首",
  "age_range": "6-12岁",
  "grade_level": "小学全年级",
  "tags": ["古诗", "动画", "系统课程", "必背"],
  "view_count": 5000000,
  "like_count": 120000,
  "duration": "共228集",
  "file_format": "MP4",
  "language": "中文"
}
```

### 下载阶段字段（来自 downloader）

```json
{
  "download_status": "success",
  "degraded_level": "Level 0",
  "file_path": "/downloads/古诗/小学必背古诗文动画.mp4",
  "file_size": "1.2GB",
  "fetch_time": "2026-06-24 15:30:00",
  "fetch_method": "yt-dlp",
  "error_code": null,
  "error_message": null
}
```

### 归档阶段新增字段（本 Skill 负责）

```json
{
  "library_path": "语文/小学全年级/古诗/B站/小学必背古诗文动画.mp4",
  "archive_time": "2026-06-24 16:00:00",
  "last_viewed": null,
  "view_count": 0,
  "favorite": false
}
```

### 可选字段（根据资源类型补充）

```json
{
  "has_answer": true,
  "page_count": 50,
  "copyright_note": "仅供个人学习使用",
  "related_resources": ["resource_id_1", "resource_id_2"],
  "notes": "用户备注信息"
}
```

---

## 索引系统

### 索引文件位置

```
学习资料库/
└── .library/
    ├── index.json           // 主索引文件
    ├── tags.json            // 标签索引
    └── logs/                // 操作日志
```

### 索引更新时机

- 新资源归档时 → 添加索引
- 资源删除时 → 移除索引
- 资源移动时 → 更新路径
- 元数据修改时 → 更新索引

### 检索维度

支持以下维度的检索：

1. **关键词检索**：标题、描述、标签
2. **学科检索**：按学科/领域筛选
3. **适龄检索**：按年龄/年级筛选
4. **类型检索**：按资源类型筛选
5. **来源检索**：按来源平台筛选
6. **质量检索**：按质量等级筛选
7. **标签检索**：按自定义标签筛选

---

## 跨平台内容级去重

> **实现位置**：`../resource-platforms/scripts/shared/dedup.py`（`DedupEngine` / `DedupConfig`）
> **配置位置**：`config/settings.yaml` 的 `dedup` 段

当同一学习内容被多个平台收录（如 B站搬运的视频也出现在抖音），或同一资源被多次获取时，去重引擎会在归档前自动检测并按策略处理，避免资料库膨胀。

### 三层去重策略（按优先级组合）

去重引擎按以下优先级依次检测，命中任意一层即判定为重复：

#### 策略一：resource_id 完全一致（最强信号）

- **原理**：同一平台同一资源的 `resource_id`（格式 `平台名:平台内ID`）完全相同。
- **场景**：用户重复归档同一资源；搜索阶段未去重导致同一资源多次出现。
- **判定**：`resource_id` 字符串完全相等 → 重复。

#### 策略二：内容指纹去重（精确）

- **原理**：基于文件内容的 hash（MD5/SHA256），字节级完全相同即为重复。
- **算法**：对本地文件分块读取并计算摘要；或直接使用元数据中的 `checksum` 字段（格式 `md5:xxx` / `sha256:xxx`）。
- **场景**：同一视频文件被不同平台转载；同一 PDF 文档多处来源。
- **判定**：两个资源的内容 hash 完全一致 → 重复。
- **注意**：不同分辨率的同一视频 hash 不同，不会被此层判定为重复（由标题相似度层兜底）。

#### 策略三：URL 结构化去重

- **原理**：基于 URL 域名 + 标准化路径的指纹。同一页面不同追踪参数视为重复。
- **算法**：
  1. 解析 URL，域名转小写，去除默认端口（:80/:443）
  2. 去除追踪参数（`utm_*`、`spm`、`share_*`、`ref`、`from` 等）
  3. 剩余参数排序后重组
  4. 去除尾部冗余斜杠和 fragment
  5. 对标准化后的 URL 计算 MD5 指纹
- **场景**：同一视频链接带不同分享参数；同一页面 PC 端和移动端 URL。
- **判定**：URL 指纹一致 → 重复。
- **边界**：跨平台转载（B站和抖音同一视频）的 URL 不同，不会被此层判定（由标题相似度层兜底）。

#### 策略四：标题相似度去重（近似）

- **原理**：基于编辑距离 + TF-IDF 余弦相似度，标题高度相似即为可能重复。
- **算法**：
  - **分词**：中文逐字切分，英文按词切分，混合文本自动适配
  - **编辑距离相似度**：`1 - levenshtein(a,b) / max(len(a), len(b))`，擅长检测字符级微调（"三年级" vs "3年级"）
  - **TF-IDF 余弦相似度**：基于加权 token 向量的余弦，擅长检测词序变化（"数学练习题" vs "练习题数学"）
  - **综合分数**：取两者最大值，覆盖两种场景
- **场景**：同一内容在不同平台的标题略有差异（如搬运视频改了标题）；同一练习题集不同版本命名。
- **判定**：综合相似度 ≥ 阈值（默认 `0.85`）→ 近似重复。
- **配置**：阈值可通过 `dedup.title_similarity_threshold` 调整；最短标题长度通过 `dedup.title_min_length_for_similarity` 控制（默认 4 字符，过短不检测）。

### 去重处理策略

检测到重复后，按 `dedup.strategy` 配置决定处理方式：

| 策略值 | 行为 | 适用场景 |
|--------|------|---------|
| `keep_best_quality`（默认） | 保留质量等级最高的版本，移除其他 | 追求资料库精简，只要最好的版本 |
| `keep_earliest` | 保留最早获取/归档的版本 | 倾向保留首次发现的历史版本 |
| `keep_latest` | 保留最新获取的版本 | 倾向保留最新鲜/更新过的版本 |
| `mark_and_keep_all` | 全部保留，但在元数据中标记 `is_duplicate: true` | 需要对比多个来源版本时 |

**操作类型**（`DedupMatch._action`）：
- `skip`：跳过归档（新资源与已有重复，且策略要求移除/跳过）
- `replace`：替换已有版本（新资源质量更高或策略为 keep_latest）
- `mark`：归档但标记为重复（策略为 mark_and_keep_all）

### 归档前去重检查工作流

归档入库前，自动执行去重检查（集成入归档工作流第一步）：

```
新资源待归档
     │
     ▼
┌─────────────────────────────┐
│ 加载资料库索引 index.json    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ DedupEngine.check_before_   │
│   archive(new, index)       │
└──────────────┬──────────────┘
               │
      ┌────────┴────────┐
      ▼                 ▼
  不重复               重复
      │                 │
      ▼                 ▼
 正常归档         按 strategy 处理：
                  - skip: 跳过，记录日志
                  - replace: 替换旧版本
                  - mark: 归档但标记 is_duplicate
```

**Python 调用示例**：
```python
from shared.dedup import DedupEngine, DedupConfig
import json

engine = DedupEngine()  # 使用 config/settings.yaml 的 dedup 段

with open("学习资料库/.library/index.json", encoding="utf-8") as f:
    library_index = json.load(f)

match = engine.check_before_archive(new_resource, library_index)

if match.is_duplicate:
    if match._action == "skip":
        logger.info(f"跳过归档（与 {match.matched_resource_id} 重复）")
        return
    elif match._action == "replace":
        logger.info(f"替换已有版本（{match.match_type}）")
        # 移除旧版本，归档新版本
    elif match._action == "mark":
        new_resource["is_duplicate"] = True
        new_resource["duplicate_of"] = match.matched_resource_id
        # 归档并标记

# 继续正常归档流程...
```

### 批量去重（资料库整理）

定期对整个资料库执行批量去重，合并已积累的重复资源：

```python
from shared.dedup import DedupEngine

engine = DedupEngine()
groups = engine.find_duplicates(all_resources)  # 并查集，支持传递性

for group in groups:
    action = engine.resolve_duplicate_group(group, all_resources)
    # action = {
    #   "action": "keep_canonical" / "keep_all_marked",
    #   "canonical_id": "...",
    #   "to_remove": [...],   # 需要移除的 resource_id
    #   "to_mark": [...],     # 需要标记的 resource_id
    # }
```

### 配置项速查

```yaml
# config/settings.yaml
dedup:
  enabled: true                         # 总开关
  strategy: keep_best_quality           # 处理策略
  enable_content_fingerprint: true      # 内容指纹去重
  hash_algorithm: md5                   # md5 / sha256
  enable_url_dedup: true                # URL 结构化去重
  url_normalize_ignore_params: true     # 标准化时忽略追踪参数
  enable_title_similarity: true         # 标题相似度去重
  title_similarity_threshold: 0.85      # 标题相似度阈值（0-1）
  title_min_length_for_similarity: 4    # 最短标题长度
  use_tfidf: true                       # 使用 TF-IDF 辅助
```

环境变量覆盖：`LRS_DEDUP__STRATEGY=mark_and_keep_all`、`LRS_DEDUP__TITLE_SIMILARITY_THRESHOLD=0.9`

---

## 归档工作流

### 第零步：归档前去重检查（自动执行）

> **此步骤在所有归档操作之前自动执行**，无需用户干预。
> 实现见 `../resource-platforms/scripts/shared/dedup.py` 的 `DedupEngine.check_before_archive()`。

1. **加载资料库索引**
   - 读取 `学习资料库/.library/index.json`
   - 提取已有资源的元数据列表

2. **执行去重检查**
   - 调用 `DedupEngine.check_before_archive(new_resource, library_index)`
   - 引擎按优先级检测：resource_id → 内容指纹 → URL → 标题相似度

3. **根据处理策略决定动作**
   - **不重复** → 继续正常归档流程（第一步起）
   - **重复 + skip** → 跳过归档，记录日志，反馈用户
   - **重复 + replace** → 移除旧版本，归档新版本
   - **重复 + mark** → 归档新版本但标记 `is_duplicate: true`

4. **记录去重日志**
   - 去重检测的匹配类型、相似度分数、最终动作
   - 写入 `.library/logs/` 便于审计

---

### 第一步：资源检查

归档前必须检查：

1. **是否是最终资源**
   - ✅ 最终文件（PDF、视频、文档等）
   - ✅ 用户确认保留的转换内容
   - ❌ 搜索缓存、临时文件、日志
   - ❌ 登录态、调试文件、中间产物

2. **文件完整性**
   - 文件能正常打开
   - 内容完整
   - 大小合理（不是0字节）

3. **安全检查**
   - 无病毒或恶意代码
   - 内容适合儿童
   - 无违法违规内容

---

### 第二步：分类判断

根据资源内容判断分类：

1. **学科/领域判断**
   - 数学、语文、英语、科普、编程、艺术...
   - 跨学科的归入"综合主题"

2. **适龄判断**
   - 明确标注年级的 → 对应年级目录
   - 明确标注年龄的 → 对应年龄目录
   - 不明确的 → 判断后归入，或放"待确认"
   - 全年龄段通用 → "全龄通用"目录

3. **主题判断**
   - 按知识点或主题分类
   - 不要太细，也不要太粗

4. **来源判断**
   - 记录来源平台或网站
   - 同一来源的资源放一起

**分类不确定时：**
- 先放入"待确认/"目录
- 记录分类疑问
- 用户后续可以手动调整

---

### 第三步：文件整理

1. **创建目标目录**
   - 按分类结构创建目录
   - 如果已存在则复用

2. **移动/复制文件**
   - 从临时位置移动到资料库
   - 重命名为有意义的文件名
   - 相关文件放同一目录

3. **附属文件处理**
   - 图片放 images/ 子目录
   - 答案解析和题目放一起
   - 相关资源保持目录结构

---

### 第四步：元数据记录

1. **收集元数据**
   - 从上游 downloader 继承下载阶段的所有字段
   - 从资源本身提取补充信息（格式、大小等）
   - 补充归档阶段的新增字段

2. **确认资源 ID**
   - 优先使用上游传递的 `resource_id`（格式：`平台名:平台内ID`）
   - 如果没有，根据来源平台和 URL 生成
   - 通用资源使用 `generic:url_hash` 格式

3. **写入索引**
   - 添加到主索引
   - 更新标签索引
   - 记录操作日志

---

### 第五步：验证与反馈

1. **验证归档结果**
   - 文件是否在正确位置
   - 元数据是否完整
   - 索引是否更新

2. **反馈给用户**
   - 归档成功的资源列表
   - 每个资源的保存位置
   - 资料库统计信息

---

## 检索工作流

### 第一步：解析检索需求

从用户需求中提取：
- 关键词
- 学科/领域
- 年龄/年级
- 资源类型
- 其他筛选条件

---

### 第二步：执行检索

1. **多维度匹配**
   - 关键词匹配（标题、描述、标签）
   - 学科匹配
   - 适龄匹配
   - 类型匹配

2. **排序**
   - 相关度优先
   - 质量等级优先
   - 最近获取优先

3. **结果去重**
   - 同一资源的多个匹配只显示一次
   - 相似资源可以合并展示

---

### 第三步：结果展示

展示格式：
```
📚 在资料库中找到 X 个相关资源：

1. [资源标题] ⭐S级
   类型：[资源类型]
   适龄：[年龄/年级]
   位置：[目录路径]
   获取时间：[日期]
   标签：[标签列表]

2. ...
```

---

### 第四步：用户选择

用户可以：
- 直接使用某个资源
- 查看资源详情
- 打开资源所在目录
- 删除不需要的资源
- 继续搜索新资源

---

## 资料库维护

### 定期整理

建议定期执行以下维护：

1. **清理重复资源**
   - 使用 `DedupEngine.find_duplicates()` 全库扫描
   - 三层去重策略：内容指纹 / URL / 标题相似度
   - 按 `dedup.strategy` 处理（保留最高质量/最早/最新/标记保留）
   - 详见上文「跨平台内容级去重」章节

2. **优化分类**
   - 检查"待确认"目录
   - 调整分类不合理的资源
   - 合并过细的分类

3. **更新索引**
   - 重建索引确保完整性
   - 检查损坏的链接
   - 更新标签

4. **统计分析**
   - 资源总数和分类统计
   - 使用频率统计
   - 存储空间使用情况

---

### 资源删除

**删除原则：**
- 用户明确要求删除才删除
- 删除前确认
- 删除后更新索引
- 可以考虑回收站机制

**删除操作：**
1. 确认用户要删除的资源
2. 删除文件
3. 从索引中移除
4. 记录删除日志
5. 反馈删除结果

---

## 资料库统计

### 统计维度

- **资源总数**：按学科、类型、质量等级统计
- **存储空间**：总大小、各分类大小
- **获取趋势**：按月/周统计新增资源
- **复用情况**：检索命中次数、复用率

### 统计展示

```
📊 资料库统计
总资源数：X 个
总大小：X MB

按学科：
- 数学：X 个
- 语文：X 个
- 科普：X 个
...

按质量：
- S级：X 个
- A级：X 个
- B级：X 个

最近新增：
- [日期]：[资源名]
- ...
```

---

## 边界与限制

### 可以做的

- 管理本地资源文件
- 维护资源索引和元数据
- 检索和复用已有资源
- 统计和分析资源使用
- 整理和优化资料库结构

### 不可以做的

- 保存临时文件、缓存、日志
- 保存用户的登录凭证
- 传播或分享资料库内容
- 自动删除用户资源（需确认）
- 超出本地范围的操作

---

## 最佳实践

### 命名规范

**目录命名：**
- 使用中文，清晰易懂
- 不要太长
- 保持一致性

**文件命名：**
- `[来源]-[资源名]-[版本].[扩展名]`
- 有意义，一看就知道是什么
- 避免特殊字符和空格

### 标签使用

**建议标签：**
- 知识点标签：四则运算、拼音、恐龙
- 难度标签：入门、基础、进阶、提高
- 类型标签：练习题、视频、绘本、课件
- 用途标签：预习、复习、拓展、启蒙
- 质量标签：推荐、必看、经典

### 复用优先

每次新需求都先检索资料库：
- 有完全匹配的 → 直接推荐使用
- 有部分匹配的 → 推荐后问是否需要更多
- 没有匹配的 → 再去搜索新资源

---

## 常见问题

### Q: 为什么不直接用文件夹管理？
A: 资料库不仅是文件夹，还有完整的索引和元数据。这样可以快速检索、统计使用情况、记录来源信息，比单纯的文件夹管理更高效。

### Q: 一个资源适合多个年龄段怎么办？
A: 只存一份文件，放在最主要的年龄段目录下，在元数据中记录完整的适龄范围。检索时会根据适龄范围匹配，不会因为只存在一个目录就找不到。

### Q: 分类不确定怎么办？
A: 先放入"待确认/"目录，记录分类疑问。后续可以根据使用情况再调整，或者用户手动分类。

### Q: 资料库会越来越大吗？
A: 是的，这是正常的。资料库的价值就在于积累。可以定期整理，删除不需要的资源，优化存储空间。

---

## 读写文件

### 1. 确认路径信息

读取 `{session_dir}/manifest.json`，获取本阶段执行所需信息：

- `manifest.stages.stage5.output` → 上游输入文件名（通常是 `stage5_download.json`）
- `manifest.stages.stage6.output` → 本阶段输出文件名（通常是 `stage6_archive.json`）

### 2. 读取上游数据
- 读取 `{session_dir}/{上游输入文件}` 的 `data` 部分
- 提取下载结果列表

### 3. 执行归档并写入结果

执行归档前去重检查 → 文件移动 → 索引更新后，将结果写入 `{session_dir}/{manifest.stages.stage6.output}`（通常是 `stage6_archive.json`）：

```json
{
  "_meta": {
    "stage": 6,
    "session_id": "{session_id}",
    "skill": "library-manager",
    "created_at": "ISO时间",
    "input_from": "stage5_download.json"
  },
  "_summary": {
    "archived_count": 3,
    "skipped_count": 1,
    "dedup_stats": {"new": 3, "duplicate": 1}
  },
  "data": {
    "archived_count": 3,
    "skipped_count": 1,
    "resources": [
      {
        "// 说明": "保留 stage5 全部字段 + 新增归档字段",
        "resource_id": "...",
        "title": "...",
        "platform": "...",
        "download_status": "...",
        "...": "（stage5 的所有字段原样保留）",

        "library_path": "学习资料库/数学/小学三年级/四则混合运算/",
        "archive_time": "2026-06-26T16:00:00+08:00",
        "dedup_status": "new / duplicate / skipped"
      }
    ]
  }
}
```

- `_summary`（flow 读这个）：归档成功数、跳过数、去重统计
- `data`（flow 汇总报告读这个）：每个资源在上游字段基础上新增——`library_path`（资料库内路径）、`archive_time`（归档时间 ISO）、`dedup_status`（new/duplicate/skipped）
- **保留规则**：上游全部字段（含 download_status/file_path 等）原样带过来，flow 最终汇总报告依赖这些字段

### 4. 完成后

- 将 `manifest.json` 中 `stages.stage6.status` 更新为 `completed`，同时将 `manifest.status` 更新为 `completed`
- 只返回 `_summary`，不在上下文中展开完整 data

---

## 参考资料

- `references/library-structure.md` - 资料库结构详细规范
- `../resource-platforms/scripts/shared/dedup.py` - 跨平台内容级去重引擎（`DedupEngine` / `DedupConfig`）
