# 平台搜索接口契约

本契约规范 `resource-search -> resource-platforms -> resource-selector` 的平台搜索数据。平台层返回归一化原始结果，不输出最终质量等级。

## 搜索任务

```json
{
  "task_id": "task-bilibili-primary",
  "platform": "bilibili",
  "priority": "P0",
  "reason": "视频讲解适合补充练习过程",
  "searches": [
    {
      "query": "三年级数学 应用题讲解",
      "max_results": 20,
      "params": {}
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `task_id` | string | 是 | 搜索任务唯一 ID |
| `platform` | string | 是 | 平台标识 |
| `priority` | string | 是 | `P0` / `P1` / `P2` |
| `reason` | string | 是 | 选择该平台的语义理由 |
| `searches` | array | 是 | 该平台需要执行的搜索调用 |
| `searches[].query` | string | 是 | 直接传给平台的关键词 |
| `searches[].max_results` | integer | 是 | 单次调用最大返回数 |
| `searches[].params` | object | 是 | 该平台真实接口支持的参数；没有则 `{}` |

当 `platform=generic` 时，每次搜索的 `params.engines` 同时包含 `baidu` 和 `bing`。平台执行器合并两个引擎并按 URL 去重。

## 单次平台响应

成功：

```json
{
  "platform": "bilibili",
  "query": "三年级数学 练习题",
  "returned_count": 1,
  "has_more": true,
  "results": [
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
        "views": 10000,
        "likes": 300,
        "native_score": null
      },
      "raw_metadata": {}
    }
  ],
  "error": null
}
```

失败：

```json
{
  "platform": "bilibili",
  "query": "三年级数学 练习题",
  "returned_count": 0,
  "results": [],
  "error": {
    "error_code": "ANTI_CRAWL_RATE_LIMITED",
    "error_message": "请求频率过高",
    "retryable": true,
    "suggested_action": "降低频率后重试"
  }
}
```

## 结果字段

技术必填字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `resource_id` | string | `{platform}:{platform_resource_id}` |
| `platform` | string | 平台标识 |
| `title` | string | 标题 |
| `source_url` | string | 原始来源地址 |

缺少任一技术必填字段时，平台层可以剔除该记录并计入 `invalid_count`。

业务字段均允许为 `null`：`type`、`description`、`author`、`duration`、`publish_time`、`is_free`、`language`、`thumbnail_url`、`download_feasibility`。平台应尽量返回已知值，不得编造。

`platform_signals` 保存平台原生热度、认证或评分信号。不得把它命名为最终 `quality_score` 或 `quality_level`；最终评分由 selector 生成。

## 清洗边界

平台层可以：

- 解析、归一化和补充确定性字段。
- 合并同平台同资源 ID 的完全重复响应。
- 使用平台原生搜索参数减少无关请求。

平台层不可以：

- 跨平台相似去重。
- 根据全局质量标准过滤或排序。
- 输出最终 S/A/B/C 等级。
- 把平台失败当成零结果。

## 下载可行性

使用中文 `高`、`中`、`低`；未知时为 `null`。这是平台访问难度判断，不是质量评价。
