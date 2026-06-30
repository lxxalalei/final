---
name: resource-search
description: 搜索策略生成器。接收 resource-intent 已整理的需求，判断哪些平台更可能找到合适资料，为不同平台生成符合其内容优势和搜索习惯的关键词，并输出可由 resource-platforms 直接执行的搜索任务。负责决定“去哪里搜、每处搜什么”，不执行搜索、不筛选结果。
---

# resource-search

## 核心任务

Search 是搜索策略层，不是字段转换器。它需要理解上一步需求，然后回答两个问题：

1. 这个需求在哪些平台更容易搜到合适内容？
2. 同一个需求到了不同平台，分别应该搜什么？

输出只服务于下一步真实搜索：平台、优先级、查询词、每次返回数量和平台实际支持的参数。

## 输入与输出

- 输入：`{session_dir}/stage1_intent.json`，要求 `data.status=ready`。
- 输出：`{session_dir}/stage2_search_plan.json`。
- 版本：`search-plan/v1`。
- 平台事实来源：`config/platform-catalog.json`。

Intent 仍需澄清时停止，不生成搜索计划。不得在本阶段重新追问用户或改写上游需求。

## 制定策略前读取

1. `config/platform-catalog.json`：平台是否可执行、内容优势、局限、查询习惯和真实搜索参数。
2. `references/routing-rules.md`：如何根据主题、学习方式、资料形态和使用场景选择平台。
3. `references/query-strategy.md`：如何把需求改写成不同平台适用的搜索词。
4. 生成 generic 的 `site:` 查询时再读取 `references/site-whitelist.md`。

## 工作方法

### 1. 理解这次到底要找什么

综合阅读 Intent，不要只盯某一个字段。重点理解：

- 核心主题是什么。
- 是直接学习、听读、观看讲解、做练习、查方法，还是找可打印资料。
- 用户明确要什么形态、来源、文件类型或平台。
- 什么是硬要求，什么只是偏好，什么没有说明。
- 年龄、年级、教材版本等信息是否真的会改善这次搜索。

不要因为出现“小学”就自动转成教材同步搜索，也不要因为出现学科名就自动要求具体年级。比如“小学古诗学习”首先是通用古诗学习需求，应自然考虑朗诵、背诵、原文注释、译文、赏析和动画理解；只有当前需求本身体现课内同步、特定教材或具体知识点时，年级和版本才是有价值的搜索维度。

这里采用语义判断，不需要给每种情况编写排他条件。判断标准只有一个：加入这个维度是否会让结果更贴近当前需求。

### 2. 给不同平台分配不同任务

从 available 平台中选择最可能贡献有效结果的平台。先看主题与学习方式，再看资源形态和平台内容生态。

每个平台都应承担明确而不同的任务。例如“小学古诗学习”：

- 喜马拉雅负责朗诵、跟读、背诵和音频专辑。
- B站负责动画、意境、逐句解释和赏析讲解。
- generic 负责原文、注释、译文、学习资料及其他公开站点。
- 智慧教育只有在官方课程、课内同步等方向有实际价值时再加入，而不是看到“小学”就默认加入。

如果某个平台不能提供新的内容形态、来源或理解角度，就不必加入。用户明确指定平台或形态时优先满足，但仍可以增加确有互补价值的平台。

generic 是固定的全网补充任务，每次同时使用百度和 Bing。它不是平台搜索失败后的临时兜底，而是用于发现未接入站点、长尾网页和具体文件。

### 3. 针对平台生成搜索词

不要把一个关键词复制到所有平台，也不要只在后面机械加平台热词。

先确定该平台负责找什么，再围绕这一任务生成若干不同角度的自然搜索词：

- 保留主题核心词，避免扩展后偏离需求。
- 拆分主题中值得分别搜索的内容角度，如朗诵、注释、实验、练习、方法、动画、课程。
- 使用平台用户真实会输入的表达。
- 查询之间应扩大实际召回面，而不只是同义词替换。
- 用户没有指定文件格式时，不擅自把“可打印”改成 PDF。
- 年龄、年级和版本只在有助于检索时使用，不要求每条查询都携带。

standard 通常为主力平台生成 2-4 条查询、补充平台 1-3 条；exhaustive 可以增加平台和查询角度。数量是参考，不是必须凑满的指标。

### 4. 只使用真实接口参数

每条 `searches[]` 就是下一步的一次搜索调用：

- `query`：发送给平台的关键词。
- `max_results`：该次调用最多返回多少条。
- `params`：仅填写 catalog 中该平台 `search_parameters` 声明的参数。

当前只有少数平台有额外搜索参数：

- ximalaya：`core`、`free_only`、`sort`。
- generic：`engines`，固定同时包含 `baidu`、`bing`。
- 其他平台当前只消费关键词和最大结果数，因此 `params` 使用 `{}`。

不要输出平台脚本不会读取的虚构参数。认证信息由 Platform Skill 自己管理，不写进搜索计划。

### 5. 写入搜索计划

```json
{
  "_meta": {
    "stage": 2,
    "session_id": "继承上游",
    "skill": "resource-search",
    "created_at": "ISO 8601",
    "input_from": "stage1_intent.json",
    "schema_version": "search-plan/v1"
  },
  "_summary": {
    "platform_count": 3,
    "platforms": ["ximalaya", "bilibili", "generic"],
    "query_count": 7,
    "expected_results": 105
  },
  "data": {
    "schema_version": "search-plan/v1",
    "intent_ref": "stage1_intent.json",
    "strategy": "古诗学习以音频听读和视频理解为主，全网搜索补充原文、注释和其他公开资料。",
    "search_tasks": [
      {
        "task_id": "task-ximalaya-audio",
        "platform": "ximalaya",
        "priority": "P0",
        "reason": "古诗朗诵、跟读和背诵音频是该平台的优势内容",
        "searches": [
          {
            "query": "小学古诗朗诵专辑",
            "max_results": 15,
            "params": {"core": "album", "sort": "relevance"}
          },
          {
            "query": "小学生必背古诗跟读",
            "max_results": 15,
            "params": {"core": "track", "sort": "relevance"}
          }
        ]
      },
      {
        "task_id": "task-bilibili-video",
        "platform": "bilibili",
        "priority": "P0",
        "reason": "动画和讲解适合帮助孩子理解古诗内容与意境",
        "searches": [
          {"query": "小学古诗动画", "max_results": 15, "params": {}},
          {"query": "儿童古诗意境讲解", "max_results": 15, "params": {}},
          {"query": "小学生古诗逐句赏析", "max_results": 15, "params": {}}
        ]
      },
      {
        "task_id": "task-generic-web",
        "platform": "generic",
        "priority": "P1",
        "reason": "补充原文注释、译文、学习资料和未接入站点",
        "searches": [
          {
            "query": "小学古诗 原文 注释 译文",
            "max_results": 15,
            "params": {"engines": ["baidu", "bing"]}
          },
          {
            "query": "小学古诗 学习资料",
            "max_results": 15,
            "params": {"engines": ["baidu", "bing"]}
          }
        ]
      }
    ]
  }
}
```

`expected_results` 是所有 `searches[].max_results` 的合计上限，不代表实际结果数，也不代表最终筛选数量。

## 完成前自检

- 平台组合是否来自当前需求，而不是默认套餐。
- 每个平台是否承担了不同的搜索方向。
- 查询词是否体现主题内容的多角度拓展，而不只是形态后缀。
- 有没有把用户没说的教材、年级、格式或来源变成搜索前提。
- `params` 是否确实被该平台搜索入口支持。
- 是否包含同时使用百度和 Bing 的 generic 任务。

最后运行：

```bash
python scripts/validate_output.py \
  {session_dir}/stage2_search_plan.json \
  --intent {session_dir}/stage1_intent.json
```

验证只检查任务是否可执行，不替代模型的语义判断。完成后向 Flow 返回输出路径和 `_summary`。
