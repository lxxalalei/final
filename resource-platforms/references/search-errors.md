# 平台搜索错误

搜索错误统一包含：

```json
{
  "platform": "generic",
  "query": "四年级数学公开课程",
  "error_code": "NETWORK_TIMEOUT",
  "message": "平台搜索超时",
  "retryable": true
}
```

常用错误：

| 错误码 | 含义 | 可重试 |
|---|---|:---:|
| `SEARCH_PLATFORM_UNAVAILABLE` | 平台未注册或不可执行 | 否 |
| `SYSTEM_ADAPTER_LOAD_FAILED` | adapter 缺失或接口错误 | 否 |
| `SYSTEM_TOOL_NOT_FOUND` | 平台脚本不存在 | 否 |
| `NETWORK_TIMEOUT` | 请求超时 | 是 |
| `ANTI_CRAWL_RATE_LIMITED` | 平台限流 | 是，延迟后 |
| `ANTI_CRAWL_BLOCKED` | 验证码或访问拦截 | 否 |
| `AUTH_LOGIN_REQUIRED` | 缺少必要登录状态 | 否，需用户处理 |
| `SEARCH_EXECUTION_FAILED` | 搜索脚本执行失败 | 视原因 |
| `PARSE_EMPTY_CONTENT` | 没有可解析响应 | 否 |
| `PARSE_FORMAT_NOT_SUPPORTED` | 响应格式无法解析 | 否 |

单次有限重试由 adapter 处理。执行器只负责超时隔离，不叠加多轮重试。错误对象不得包含 Cookie、token、完整请求头或浏览器认证数据。
