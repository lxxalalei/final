---
name: resource-platforms
description: 学习资源平台执行层。用于按搜索计划调用各平台脚本并输出归一化原始结果，或按下载任务调用平台下载能力。只处理平台访问、协议适配和技术性清洗，不负责跨平台业务筛选、最终质量评分或用户选择。
---

# resource-platforms

## 职责边界

本 Skill 有两种模式：

- `search`：流水线 stage 3，由 `learning-resource-flow` 调用。
- `download`：stage 5 内部能力，由 `resource-downloader` 调用。

平台层负责：

1. 维护私有的 `config/platform-registry.json`，声明平台搜索/下载状态、认证方式和执行入口。
2. 找到并调用平台脚本。
3. 管理平台所需 Cookie、token、CDP 或浏览器会话。
4. 执行限速、重试、断路器和平台降级。
5. 将不同平台响应归一化为统一字段。
6. 剔除无法解析、缺少来源地址等技术无效记录。
7. 合并同平台、同资源 ID 的完全重复响应。
8. 逐平台记录成功、失败和错误码。

其中 `generic` 是固定的通用网页搜索平台：每条查询同时调用百度和 Bing，合并后按 URL 去重。它用于补充跨站和长尾结果，不替代其他平台的专项搜索。

平台层不负责：

- 跨平台去重。
- 相关性、安全性、语言、付费状态等业务过滤。
- 全局质量评分、S/A/B/C 定级和最终排序。
- 候选展示或用户选择。

平台脚本可以返回平台原生热度或自评信息，但只能作为 `platform_signals` 原始信号，由 `resource-selector` 决定是否采用。

## Search 模式

### 输入

读取 `{session_dir}/{input_file}`，默认：

- `input_file=stage2_search_plan.json`
- `output_file=stage3_search_results.json`

从 `data` 读取：

```json
{
  "schema_version": "search-plan/v1",
  "intent_ref": "stage1_intent.json",
  "strategy": "官方练习为主，视频讲解和全网长尾补充",
  "search_tasks": [
    {
      "task_id": "task-bilibili-primary",
      "platform": "bilibili",
      "priority": "P0",
      "reason": "视频讲解适合补充练习过程",
      "searches": [
        {"query": "三年级应用题 解题讲解", "max_results": 20, "params": {}}
      ]
    }
  ]
}
```

### 执行

1. 校验每个任务的 `task_id`、`platform`、`priority` 和 `searches`。
2. 根据 `config/platform-registry.json` 的 `search.entry` 定位平台脚本或 adapter；非 available 平台不得执行。
3. 对每个 `searches[]` 分别执行一次搜索：`query` 作为关键词，`max_results` 作为返回上限，`params` 只转换成该平台真实支持的命令参数。
4. 按优先级执行任务；支持并行时限制并发，避免触发平台风控。
5. 从计划的 `intent_ref` 读取 stage 1，只为 stage 3 输出复制 Selector 所需的主题和约束；不得据此重新生成关键词。
6. 保留平台返回的原始有效结果，不因质量一般而提前丢弃。
7. 归一化字段；缺失字段写 `null`，不要编造。
8. 仅合并 `{platform}:{platform_resource_id}` 完全一致的重复响应。
9. 汇总结果和错误并写入输出文件。

### 归一化结果

每条 `resources[]` 至少包含：

```json
{
  "resource_id": "bilibili:BVxxxx",
  "platform": "bilibili",
  "platform_resource_id": "BVxxxx",
  "title": "三年级数学同步练习",
  "source_url": "https://...",
  "type": "视频",
  "description": null,
  "author": null,
  "duration": null,
  "publish_time": null,
  "is_free": null,
  "language": null,
  "thumbnail_url": null,
  "download_feasibility": "中",
  "platform_signals": {
    "views": null,
    "likes": null,
    "native_score": null
  },
  "raw_metadata": {}
}
```

`resource_id`、`platform`、`title`、`source_url` 缺失时，该记录属于技术无效记录，可以剔除并计入 `invalid_count`。其他业务字段缺失时保留 `null`，交给 selector 处理。

### 输出

写入 `{session_dir}/stage3_search_results.json`：

```json
{
  "_meta": {
    "stage": 3,
    "session_id": "继承上游",
    "skill": "resource-platforms",
    "created_at": "ISO 8601",
    "input_from": "stage2_search_plan.json"
  },
  "_summary": {
    "raw_count": 72,
    "success_platforms": ["bilibili", "smartedu"],
    "failed_platforms": ["weibo"],
    "error_count": 1,
    "invalid_count": 3
  },
  "data": {
    "intent_context": {
      "core_topic": "三年级数学练习题",
      "target_age": "8-9岁",
      "search_mode": "standard",
      "constraints": {"must": [], "prefer": [], "exclude": []}
    },
    "resources": [],
    "platform_stats": {},
    "errors": []
  }
}
```

`raw_count` 是技术性清洗后交给 selector 的记录数，不是精选候选数。

## Download 模式

接收单条资源或批次任务，按 `platform` 调用相应下载脚本。返回统一结果：

```json
{
  "resource_id": "bilibili:BVxxxx",
  "status": "success",
  "local_files": ["/absolute/path/video.mp4"],
  "file_size": 156000000,
  "error": null,
  "retryable": false,
  "degraded_level": "Level 0"
}
```

不要在下载模式重新做候选筛选。失败时返回结构化错误，由 downloader 决定重试或降级。

## 原则

- 平台失败不得伪造成空结果。
- 平台原始信号与 selector 最终评分分开保存。
- 认证信息只通过安全参数、环境变量或会话状态传递，不写入结果文件和日志。
- 平台内为控制分页而进行的精确去重允许保留；跨平台和相似标题去重必须交给 selector。

## 参考资料

- `config/platform-registry.json`：本 Skill 私有的技术执行注册表，不作为其他 Skill 的运行时输入。
- `references/schemas/platform-search-contract.md`：平台搜索接口。
- `references/schemas/platform-download-contract.md`：平台下载接口。
- `references/schemas/error-codes.md`：错误码。
- `references/platforms/`：各平台访问方式和限制。
