---
name: resource-search
description: 全域搜索调度器。接收结构化查询指令，进行平台路由判断（查平台优势图谱选择最佳平台组合），调度各平台执行搜索，汇总结果后跨平台去重、质量评估分级（S/A/B/C），输出结构化候选资源列表。
---

# resource-search · 全域搜索调度

## 职责
resource-search 是儿童学习资源搜索的**中枢调度器**，负责：
1. **分析需求特点**：理解主题类型、资源形态偏好、用户指定
2. **平台路由判断**：根据平台优势图谱，选择最合适的平台组合
3. **调度执行搜索**：调用各平台专属搜索能力 + 通用搜索兜底
4. **质量控制筛选**：去重、过滤、质量评估、分级排序
5. **输出候选列表**：交付结构化的高质量候选资源供用户选择

> 💡 **核心定位**：search 不负责具体平台的搜索技巧细节，而是负责"选对平台、用对方法、控好质量"。
> 具体平台的搜索技巧，见 `../resource-platforms/references/<平台>.md`。

## 输入
- 结构化查询指令组（来自 resource-intent）
- 核心主题、资源形态偏好、目标年龄、难度偏好等
- （可选）用户指定的平台或来源类型

## 执行步骤

### 第一步：平台路由判断 ⭐ 核心
搜索的第一步不是立刻开搜，而是**先判断应该去哪些平台搜**。

1. 看用户有没有明确指定平台/类型 → 有就直接去对应平台
2. 判断主题类型（科普/学科/古诗/思维/艺术/习惯/兴趣）
3. 查 `../shared/config/platform-advantages.md`（平台优势图谱），选该主题的第一梯队平台（2-3个）
4. 根据资源形态偏好，补充对应平台（1-2个）
5. 通用搜索兜底

> 详细路由规则见：`references/搜索执行规则.md` 第二节

### 第二步：制定搜索计划
根据选定的平台组合，确定：
- 各平台的查询数量分配
- 预期候选数量（标准模式20-25个，穷尽模式30-40个）
- 搜索优先级顺序

> 主题自适应形态策略见：`references/搜索执行规则.md` 第四节
> 双模式开关见：`references/搜索执行规则.md` 第七节

### 第三步：调度执行搜索
按优先级依次执行各平台搜索：
1. **第一梯队平台**：重点搜，查询数量多，结果要求高
2. **补充平台**：针对性搜，补全特定形态资源
3. **通用搜索兜底**：防止漏网之鱼

**执行方式**：各平台的搜索由对应 platform skill 执行，search 负责调度调用。各平台搜索技巧见 `../resource-platforms/references/<平台>.md`。

**要求**：单需求至少覆盖 3 类来源，召回 20+ 原始结果。

### 第四步：初步筛选与去重
对搜索结果进行第一轮过滤：
- 三级去重（URL去重 → 标题指纹去重 → 内容相似度去重）
- 移除境外网站、未知域名
- 移除明显广告、营销、高风险站点
- 移除付费/VIP内容（免费部分可看的标注清楚）
- 移除非中文内容（英语学习等明确需求除外）
- 移除标题/摘要明显不相关的结果

> 详细过滤规则见：`references/搜索执行规则.md` 第九节

### 第五步：质量评估与分级
对通过初筛的候选，按五维评分体系进行质量评估：
- 内容质量与完整性（25%）
- 适龄匹配度（25%）
- 权威可信度（20%）
- 可获取性（20%）
- 安全与体验（10%）

> 主题相关性作为前置门槛，不相关的资源不进入质量评估。

分为 S/A/B/C 四级，S级为强烈推荐，C级仅在候选极少时展示。

> 📖 完整评估标准见：`../shared/schemas/quality-rubric.md`（权威标准）
> 📖 评估要点速览见：`references/搜索执行规则.md` 第八节

### 第六步：输出候选列表
输出结构化的候选资源列表，交付下游使用。
必须包含数量账本（执行查询数、原始召回数、初筛后剩余、最终候选数、各级别数量）。

## 关键原则

1. **路由优先**：先选对平台，再执行搜索，事半功倍
2. **穷尽召回**：多来源、多查询并行，宁可多不可漏
3. **用户指定优先**：用户明确要什么平台/类型，就以该平台/类型为主
4. **主题自适应**：不同主题调整资源形态比重，不搞一刀切
5. **质量分层**：第一类官方站做标杆，视频平台为主力，图文音频做补充
6. **可获取优先**：同等质量下，能下载/保存的优先展示
7. **国内范围**：仅限国内公开互联网和国内社媒平台，不访问境外网站
8. **灵活调整**：搜了发现某个平台结果特别好，可以多搜；结果不好就少搜

## 参考文档

- **搜索执行规则**：`references/搜索执行规则.md`（完整执行手册）
- **平台优势图谱**：`../shared/config/platform-advantages.md`（各平台擅长领域与优先级，全系统共享）
- **优质站点白名单**：`references/优质站点白名单.md`（官方站点分级清单）
- **资源元数据规范**：`../shared/schemas/resource-schema.md`
- **跨 Skill 上下文传递契约**：`../shared/schemas/skill-contract.md`
- **会话上下文读写规范**：`../shared/schemas/session-io-spec.md`

## 输出格式

> 标准化输出模板见 `../learning-resource-flow/references/output-templates.md`（模板 A），以下为简版速览。

```
【搜索概览】
- 执行查询数：XX 个
- 覆盖平台：XXX、XXX、XXX...
- 原始召回数：XX 条
- 初筛后剩余：XX 条
- 最终候选数：XX 个（S级 X、A级 X、B级 X）

【候选列表】
1. S级 · 标题
   来源：XXX（平台）
   类型：视频 · 学科：语文
   适龄：6-12岁
   链接：XXX
   简介：XXX
   标签：#XX #XX
   下载可行性：高/中/低

2. A级 · 标题
   ...
```

> 完整字段列表见 output-templates.md 模板 A.2（单卡片可复用模板）。

---

## 读写文件

### 1. 获取任务路径
- 从 flow 传入参数中获取：会话目录 `{session_dir}`、上游文件名（通常 `stage1_intent.json`）、输出文件名（通常 `stage2_search.json`）

### 2. 读取上游数据
- 读取 `{session_dir}/stage1_intent.json` 的 `data` 部分
- 提取 `queries` 列表和搜索参数

### 3. 执行搜索并写入结果

搜索完成后，将以下结构写入 `{session_dir}/stage2_search.json`：

```json
{
  "_meta": {
    "stage": 2,
    "session_id": "{session_id}",
    "skill": "resource-search",
    "created_at": "ISO时间",
    "input_from": "stage1_intent.json"
  },
  "_summary": {
    "total_count": 22,
    "platforms_searched": ["bilibili", "ximalaya", "smartedu"],
    "quality_dist": {"S": 3, "A": 8, "B": 8, "C": 3}
  },
  "data": {
    "total_count": 22,
    "search_summary": "查询3组/平台4个/召回85条/初筛后40条/去重后22条",
    "resources": [
      {
        "resource_id": "平台名:平台内ID",
        "title": "资源标题",
        "type": "视频/音频/文档/练习题/绘本/课件/图片",
        "subject": "学科/领域",
        "platform": "bilibili",
        "source_url": "来源URL",
        "source_name": "B站",
        "quality_level": "S/A/B/C",
        "download_feasibility": "高/中/低",
        "platform_quality_score": 85,
        "description": "内容简介",
        "age_range": "适龄范围",
        "grade_level": "适用年级",
        "tags": ["标签1"],
        "view_count": 5000000,
        "duration": "时长/集数",
        "language": "中文"
      }
    ]
  }
}
```

- `_summary`（flow 读这个）：候选总数、搜索过的平台、质量分布
- `data`（下游 selector 读这个）：候选资源列表，每个资源必须包含以下字段——`resource_id`、`title`、`type`、`subject`、`platform`、`source_url`、`source_name`、`quality_level`、`download_feasibility`，可选字段——`platform_quality_score`、`description`、`age_range`、`grade_level`、`tags`、`view_count`、`duration`、`language`

### 4. 完成后

- 提示 flow 调用 `resource-selector` 继续执行
- 只返回 `_summary`，不在上下文中展开完整 data
