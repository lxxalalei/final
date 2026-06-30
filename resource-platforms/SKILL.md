---
name: resource-platforms
description: 搜索执行层。接收搜索任务清单，调度各平台脚本执行搜索，汇总原始结果并进行跨平台去重，输出标准化后的去重结果列表。不负责质量评估和过滤精选，这些由下游 selector 负责。
---

# resource-platforms · 搜索执行

## 我是谁

**上游**：resource-search（从搜索策略 Skill 接收搜索任务清单）
**下游**：resource-selector（把去重后的原始结果列表传给选择器）
**阶段编号**：stage 3

核心定位：**搜索的执行者**——拿到搜索任务后，实际去各个平台搜，把结果收回来，去重、标准化，然后原样输出。不做质量评估、不做过滤精选，把判断权交给下游 selector。

---

## 执行前准备

### 1. 确认参数

从 flow 传入的参数中获取：
- `{session_dir}`：会话目录路径（绝对路径）
- `{input_file}`：上游输入文件名（通常是 `stage2_search_plan.json`）
- `{output_file}`：本阶段输出文件名（通常是 `stage3_candidates.json`）

### 2. 读取上游输入

读取 `{session_dir}/{input_file}` 文件，提取其中的 `data` 部分。

> 💡 只需要读 `data`，`_meta` 和 `_summary` 可以忽略（那是给 flow 用的）

**需要读取的字段**（从 data 中）：
- `search_tasks`：各平台搜索任务列表（数组，✅必选）
  - 每个任务包含：
    - `platform_id`：平台标识（如 bilibili）
    - `platform_name`：平台名称
    - `priority`：优先级（P0 / P1 / P2）
    - `queries`：该平台的查询列表
    - `target_count`：预期召回数量
    - `search_params`：其他搜索参数（可选）
- `core_topic`：核心主题（字符串，✅必选）
  - 透传给下游，供 selector 做相关性判断
- `target_age`：目标年龄范围（字符串，✅必选）
  - 透传给下游，供 selector 做适龄匹配度评分
- `search_mode`：搜索模式（字符串，✅必选）
  - standard / exhaustive

---

## 执行步骤

### 第一步：确认可用平台与脚本路径

根据搜索任务中的平台列表，确认每个平台的搜索脚本路径和调用方式。

**平台脚本查找规则**：
- 脚本位于 `./scripts/{platform_id}/` 目录下
- 搜索脚本命名：`{platform_id}_search.py`
- 每个平台有一个 `adapter.py` 作为统一接口

**可用平台检查**：
- 检查平台脚本是否存在
- 检查平台状态是否可用
- 不可用的平台跳过，记录到日志中

> 📖 平台能力矩阵见：本文件下方「平台清单」表格
> 📖 各平台详细文档见：`./references/platforms/{platform_id}.md`

**本步产出**：
- `available_tasks`：可用的搜索任务（过滤掉不可用的平台）
- `skipped_platforms`：跳过的平台及原因

---

### 第二步：按优先级调度各平台搜索

按平台优先级从高到低，依次执行搜索。

**调度方式**：
- 调用各平台的搜索脚本
- 传入参数：查询关键词、数量限制、其他搜索参数
- 每个平台的搜索结果保存到临时文件

**执行顺序**：
1. **P0 平台**（第一梯队）：优先执行，分配更多查询
2. **P1 平台**（第二梯队）：其次执行
3. **P2 平台**（补充）：最后执行

**每个平台的执行流程**：
1. 读取该平台的查询列表
2. 按查询优先级依次执行搜索
3. 收集搜索结果
4. 进行平台内初步去重
5. 结果标准化（转为统一的资源元数据格式）

> 💡 各平台的搜索技巧和注意事项，见对应平台的参考文档。
> 执行时如果遇到问题（反爬、登录等），参考对应平台的文档处理。

**本步产出**：
- `raw_results`：各平台原始搜索结果汇总（数组）
  - 每个结果是一个资源对象，包含基本元数据
  - 平台脚本返回时带 `platform_quality_score`（平台自评原始分，供下游参考）
- `platform_stats`：各平台的搜索统计
  - 每个平台执行了几个查询、召回了多少条结果

---

### 第三步：跨平台去重

对所有平台的原始结果进行跨平台去重。

**去重策略（三级）**：

1. **resource_id 完全一致**（最强信号）
   - 同一平台的相同 ID 直接去重
   - 保留 `platform_quality_score` 最高的那个

2. **URL 结构化去重**
   - 去除 URL 中的追踪参数后比较
   - 同一资源在不同平台的转载，URL 可能不同，这一步不一定能识别

3. **标题相似度去重**
   - 计算标题的编辑距离和相似度
   - 相似度超过阈值（如 0.85）视为重复
   - 保留 `platform_quality_score` 最高的那个

4. **内容指纹去重**（可选，耗时较长）
   - 对文档/视频简介等内容计算指纹
   - 指纹相同视为重复

**去重后的处理策略**：
- `keep_best`（默认）：保留 `platform_quality_score` 最高的
- `keep_earliest`：保留最先搜到的
- `mark_and_keep_all`：标记重复但都保留

> 📖 完整去重规则见：`./scripts/shared/dedup.py`

**本步产出**：
- `deduped_results`：去重后的结果列表（数组）
- `dedup_stats`：去重统计
  - 原始数量、去重后数量、移除了多少重复

---

### 第四步：写入输出文件

将去重后的结果写入 `{session_dir}/{output_file}`（通常是 `stage3_candidates.json`）。

> ⚠️ **不做质量评估、不做过滤精选、不做排序**。输出的是去重后的原始结果，由下游 selector 负责评估打分和过滤。

**文件格式**（三层结构）：

```json
{
  "_meta": {
    "stage": 3,
    "session_id": "从输入文件中继承",
    "skill": "resource-platforms",
    "created_at": "当前时间（ISO 8601 格式）",
    "input_from": "{input_file}"
  },
  "_summary": {
    // 给 flow 看的摘要
  },
  "data": {
    // 给下游 selector 用的去重结果
  }
}
```

---

#### _summary 部分（flow 读这个做调度）

**必须写入的字段**：
- `total_count`：去重后结果总数（数字）
  - 示例：45
- `raw_count`：去重前原始召回总数（数字）
  - 示例：72
- `platforms`：用到的平台列表（数组）
  - 示例：["bilibili", "smartedu", "ximalaya", "zhihu"]
- `has_results`：是否有结果（布尔值）
  - 示例：true

> 💡 _summary 必须精简，flow 只读前几十行就知道结果怎么样。
> 如果 total_count = 0，flow 会主动询问用户是否放宽条件。

---

#### data 部分（下游 selector 读这个）

**必须写入的字段**：

- `total_count`：去重后结果总数（数字，✅必选）
  - 注意：这个是去重后的原始数量，不是精选后的数量。selector 会从中过滤精选

- `search_summary`：搜索过程摘要（字符串，✅必选）
  - 示例："搜索了4个平台，执行15个查询，原始召回72条，去重后45条"

- `resources`：去重后的资源列表（数组，✅必选）
  - 每个资源对象包含：
    - `resource_id`：资源唯一标识（字符串，✅必选）
      - 格式：`{platform}:{平台内ID}`
      - 示例："bilibili:BV1xx411c7mD"
    - `title`：标题（字符串，✅必选）
    - `type`：资源类型（字符串，✅必选）
      - 视频 / 音频 / 文档 / 图文 / 课件 / 练习题
    - `platform`：平台标识（字符串，✅必选）
    - `source_url`：来源链接（字符串，✅必选）
    - `source_name`：来源平台名称（字符串，✅必选）
    - `platform_quality_score`：平台自评原始分（数字，✅必选）
      - 0-100 分，平台脚本返回的原始质量分
      - 这是粗筛信号，不是最终评分。selector 会基于五维体系重新评估
    - `download_feasibility`：下载可行性预估（字符串，✅必选）
      - 高 / 中 / 低
    - `description`：简介/描述（字符串，⚠️可选）
    - `age_range`：适用年龄范围（字符串，⚠️可选）
    - `grade_level`：适用年级（字符串，⚠️可选）
    - `tags`：标签列表（数组，⚠️可选）
    - `view_count`：播放/浏览量（数字，⚠️可选）
    - `duration`：时长/集数（字符串，⚠️可选）
    - `language`：语言（字符串，⚠️可选）
    - `is_free`：是否免费（布尔值，⚠️可选）
    - `author`：作者/上传者（字符串，⚠️可选）

> 📖 完整字段规范见：`./references/schemas/resource-schema.md`

- `search_stats`：搜索统计（对象，⚠️可选）
  - 包含：平台统计、查询数量、原始召回数、去重数等
  - 供调试和优化参考

- `intent_data`：透传的 intent 数据（对象，⚠️必选）
  - 把上游 intent 的 data 原样透传，selector 做质量评估时需要 core_topic 和 target_age

---

## 完成后

### 1. 确认输出

确认 `{session_dir}/{output_file}` 已成功写入。

### 2. 清理临时文件

清理搜索过程中产生的临时文件（如果有）。

### 3. 通知 flow

向 flow 返回执行结果，只返回 _summary 的内容：

```
✅ 已完成搜索执行
📄 输出文件：{output_file}
📊 摘要：
- 去重后结果：{total_count} 个（原始召回 {raw_count} 个）
- 覆盖平台：{platforms 数量} 个
```

> 💡 **重要**：只返回 _summary，不要在上下文中展开完整的资源列表。
> 完整数据已经写入文件，下游 selector Skill 会去读、评估、过滤后展示给用户。

---

## 关键原则

### 执行原则
1. **按优先级执行**：高优先级平台先搜，保证核心覆盖
2. **结果标准化**：各平台的结果都要转为统一格式
3. **错误容错**：某个平台失败不影响整体，跳过继续

### 去重原则
1. **宁重勿漏**：去重要保守，宁可留几个重复，也不要误删好资源
2. **保留最优**：重复的资源保留 `platform_quality_score` 最高的

### 边界原则
1. **只搜索不去重之外做判断**：不做质量评估、不做过滤精选、不做排序
2. **透传而非裁剪**：搜索结果原样透传给 selector，由它做判断
3. **platform_quality_score 是粗筛信号**：平台脚本的自评分仅供参考，不是最终评分

---

## 平台能力速查

| 平台 | 搜索能力 | 登录要求 | 反爬等级 | 脚本路径 |
|------|---------|---------|---------|---------|
| bilibili | ✅ 强 | 无需 | ⭐⭐⭐⭐ | scripts/bilibili/ |
| smartedu | ✅ 强 | 可选 | ⭐⭐⭐ | scripts/smartedu/ |
| zhihu | ✅ 中 | Cookie | ⭐⭐⭐ | scripts/zhihu/ |
| douyin | ✅ 中 | 自动 | ⭐⭐⭐⭐ | scripts/douyin/ |
| weibo | ✅ 中 | Cookie | ⭐⭐⭐ | scripts/weibo/ |
| ximalaya | ✅ 强 | 无需 | ⭐ | scripts/ximalaya/ |
| open163 | ✅ 中 | 无需 | ⭐ | scripts/open163/ |

> 📖 各平台详细说明见 `./references/platforms/` 下对应文档

---

## 参考资料

- **资源元数据规范**：`./references/schemas/resource-schema.md`（统一资源格式）
- **错误码体系**：`./references/schemas/error-codes.md`（统一错误码）
- **搜索接口契约**：`./references/schemas/platform-search-contract.md`（平台搜索接口规范）
- **下载接口契约**：`./references/schemas/platform-download-contract.md`（平台下载接口规范）
- **各平台文档**：`./references/platforms/{platform_id}.md`（7 个平台的详细说明）
- **下载方法详解**：`./references/download-methods.md`（通用下载方法）

> 💡 参考资料放在最后，执行主流程时不需要看，需要时再查阅。
