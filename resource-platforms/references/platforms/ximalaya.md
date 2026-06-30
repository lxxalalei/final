# 喜马拉雅搜索

- Adapter：`scripts/ximalaya/adapter.py`
- 认证：通常不需要
- 参数：`core=album|track`、`free_only`、`sort=relevance|popularity|newest`

适合朗诵、跟读、故事、音频课程和专辑。优先使用官方公开搜索接口，失败时可使用既有镜像降级。平台原生播放量、评分和主播认证只放入 `platform_signals`。
