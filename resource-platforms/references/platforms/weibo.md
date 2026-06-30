# 微博搜索

- Adapter：`scripts/weibo/adapter.py`
- 认证：需要有效 Cookie
- 参数：当前只使用关键词和 `max_results`

适合教育热点、机构动态和短图文讨论，不适合作为系统课程的主要来源。缺少 Cookie 时直接返回认证错误；搜索结果只保留可定位的原帖或内容地址。
