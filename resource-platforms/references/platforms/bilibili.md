# Bilibili 搜索

- Adapter：`scripts/bilibili/adapter.py`
- 认证：可选 Cookie/CDP，会提高稳定性
- 参数：当前只使用关键词和 `max_results`

适合课程讲解、动画演示、实验过程和学习方法视频。搜索实现暂由历史 CLI 的 search 子命令承载，adapter 是唯一公开入口。遇到 412、验证码或登录限制时返回反爬/认证错误，不得把失败解释为没有结果。
