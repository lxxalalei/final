# Wechat 微信公众号搜索

## 执行入口

- Adapter：`scripts/wechat/adapter.py`
- 搜索脚本：`scripts/wechat/search_wechat.js`
- 第三方依赖：Node.js、`cheerio`
- 认证：通常不需要；可选 `SOGOU_WEIXIN_COOKIE`
- 计划参数：`resolve_url` / `resolve_real_url` / `real_url`

Adapter 通过搜狗微信搜索页发现微信公众号文章，返回文章标题、搜狗中转链接或真实微信文章链接、摘要、公众号名和发布时间。默认不解析真实微信文章 URL，以降低请求量和触发反爬的概率；调用方明确传入 `resolve_url=true` 时，脚本会尝试把搜狗中转链接解析为 `mp.weixin.qq.com` 链接。

## 参数

- `max_results`：1 到 50，超过 50 会截断。
- `resolve_url=true`：尝试解析真实文章链接；速度更慢，也更容易受到搜狗反爬影响。

## 输出

每条结果标准化为：

- `platform=wechat`
- `type=文章`
- `title`
- `source_url`
- `description`：搜索结果摘要
- `author`：公众号名
- `publish_time`
- `platform_signals.engine=sogou-weixin`
- `platform_signals.rank`

`raw_metadata` 只保留 `query`、`date_text`、`date_description`、`url_resolved` 等排查字段。

## 错误

- 缺少 Node.js 或 `cheerio`：`SYSTEM_DEPENDENCY_MISSING`
- 搜狗验证码、反爬或访问频率限制：`SEARCH_BLOCKED`
- 请求超时：`NETWORK_TIMEOUT`

微信公众号搜索只负责发现文章链接；正文抽取、下载和归档交给 `resource-archive`。
