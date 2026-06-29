# 儿童学习资源 Skill 套件

面向 3-12 岁儿童学习资源的 AI Skill 工具集。从需求理解到本地归档的完整闭环，覆盖 7 大内容平台。

## Skill 清单

| Skill | 职责 | 阶段 |
|-------|------|------|
| `learning-resource-flow` | 总调度入口，6 阶段流程编排 | 全流程 |
| `resource-intent` | 需求理解与查询生成 | 阶段一 |
| `resource-search` | 搜索策略制定与调度 | 阶段二 |
| `resource-platforms` | 7 平台搜索与下载执行 | 阶段二/四 |
| `resource-selector` | 候选展示与用户选择 | 阶段三 |
| `resource-downloader` | 下载调度与降级处理 | 阶段四 |
| `library-manager` | 资料库归档、索引、去重 | 阶段五 |

## 已接入平台

bilibili（B站）· smartedu（国家中小学智慧教育平台）· zhihu（知乎）· douyin（抖音）· weibo（微博）· ximalaya（喜马拉雅）· open163（网易公开课）

## 目录结构

```
learning-resource-suite/
├── learning-resource-flow/     # 总控 Skill
├── resource-intent/            # 需求理解
├── resource-search/            # 搜索调度
├── resource-platforms/         # 平台执行（含 Python 脚本）
├── resource-selector/          # 候选选择
├── resource-downloader/        # 下载调度
├── library-manager/            # 资料库管理
├── shared/                     # 跨 Skill 共享规范（schemas + config）
├── config/                     # 项目配置（settings.yaml）
├── scripts/                    # 开发工具（healthcheck.py 等）
├── tests/                      # 测试脚本
├── docs/                       # 参考文档
└── _archive/                   # 已归档的历史文档
```

每个 Skill 文件夹包含 `SKILL.md`（主文件）和 `references/`（按需加载的参考资料）。
