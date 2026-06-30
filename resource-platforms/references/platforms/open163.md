# 网易公开课搜索

- Adapter：`scripts/open163/adapter.py`
- 认证：无
- 参数：当前只使用关键词和 `max_results`

适合公开课、纪录片、TED 和系统课程。搜索依赖公开页面解析；页面结构变化或空响应要返回解析错误。课程集数、播放量和付费标记作为标准字段或 `platform_signals` 返回，不计算最终质量等级。
