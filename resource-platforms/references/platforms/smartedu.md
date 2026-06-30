# 国家中小学智慧教育平台搜索

- Adapter：`scripts/smartedu/adapter.py`
- 认证：部分栏目需要浏览器会话
- 参数：当前只使用关键词和 `max_results`

适合教材同步课程、官方课件、课程资源和教师材料。Adapter 调用 `smartedu_resources.py search-resources`，内部目录、详情和页面解析模块只作为实现细节。缺少会话或栏目接口失效时返回认证/请求错误，不得降级为下载流程。
