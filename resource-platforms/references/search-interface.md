# 平台搜索接口

## 任务输入

每个平台任务包含 `platform` 和一个或多个 `searches`。每次搜索包含 `query`、`max_results`，以及平台真实支持时才出现的 `params`。

```json
{
  "platform": "bilibili",
  "searches": [
    {
      "query": "四年级数学 小数 讲解",
      "max_results": 10,
      "params": {}
    }
  ]
}
```

平台搜索只执行已经给出的查询。查询扩展、方向拆分、资源选择、下载和归档由调用方或其他工具处理。

## Adapter 返回

每个平台 adapter 导出 `ADAPTER.search(query, max_results, params)`，返回：

```json
{
  "results": [
    {
      "resource_id": "bilibili:BVxxxx",
      "platform": "bilibili",
      "title": "四年级数学知识点讲解",
      "source_url": "https://...",
      "type": "视频",
      "platform_signals": {"views": 10000}
    }
  ],
  "error": null
}
```

资源必填字段为 `platform`、`title`、`source_url`；能稳定提供时同时输出 `resource_id`。可选字段已知时才输出：`type`、`description`、`author`、`duration`、`publish_time`、`is_free`、`language`、`thumbnail_url`、`download_feasibility`、`platform_signals`、`raw_metadata`。

`platform_signals` 只保留播放、点赞、评论、收藏、认证、集数、站内排名等平台事实。不要把脚本推算的相关性、适龄性、质量等级写成资源结论。

`raw_metadata` 只保存后续重开页面、下载或排查所需的少量稳定字段，不倾倒完整平台响应。

失败时返回 `results=[]` 和统一 `error`。部分结果可用时允许同时返回结果和错误。

运行依赖和认证环境变量由 `config/search-registry.json` 声明。任务输入只传搜索参数，不传 Cookie、Token、请求头或浏览器状态。

## CLI 汇总输出

`scripts/search_cli.py` 和 `scripts/search_core.py` 汇总所有 adapter 响应：

```json
{
  "success": true,
  "duration_ms": 1200,
  "data": {
    "resources": [],
    "errors": [],
    "summary": {
      "task_count": 1,
      "resource_count": 0,
      "failed_platforms": []
    }
  }
}
```

执行器只做平台内精确去重和错误隔离。跨平台相似判断、人工取舍、质量判断和下载归档应在外部完成。
