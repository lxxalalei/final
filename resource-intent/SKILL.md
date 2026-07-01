---
name: resource-intent
description: 面向家长和孩子的学习资源收集需求澄清器。仅在 learning-resource-flow 提供 request.json 时使用；由模型理解完整语境，判断资源收集需求是否足够明确，必要时提出一个高价值问题，并输出自然语言语义简报 intent-brief/v1。不要搜索资源、选择平台或生成查询。
---

# resource-intent

## 目标

把家长或孩子的表达理解成一份完整、忠实、可交给 Search 的资源收集需求简报：

> 用户要为怎样的孩子，围绕什么学习内容，收集能支持什么学习任务的资源；资源将怎样使用，又有哪些不能忽略的要求。

依靠模型理解整体语义，不从固定字段反向盘问用户。结构只负责流程控制、证据和硬要求，不替代判断。

本阶段不选择平台，不生成可执行查询，不决定搜索预算，不评价具体资源，也不下载或归档。

## 输入与输出

- 输入：`{session_dir}/request.json`，契约见 `schemas/input.schema.json`。
- 输出：`{session_dir}/stage1_intent.json`，契约见 `schemas/output.schema.json`。
- 输出版本：`intent-brief/v1`。

只读取事实快照中的：

- `data.raw_request`；
- `data.conversation_evidence`。

合并所有仍有效的用户表达。较新的回答可以补充或修正旧信息；不要只处理最后一句，也不要使用快照外的聊天记忆。

## 决策流程

### 1. 完整理解请求

在内部考虑学习内容、学习任务、学习者条件、资源用途、使用场景和用户要求，但不要要求每项都出现。

区分：

- 用户明确表达的事实；
- 用户主动选择的宽泛范围；
- 没有指定、可以保持开放的事项；
- 模型为理解语义作出的推断；
- 会让资源收集走向另一类内容的关键歧义。

学习内容只包括学科知识、知识点、兴趣主题、学科能力和实践能力。学习方法、学习习惯、过程管理以及泛化的行为或亲子问题不转换为学习内容。

详细语义边界见 `references/semantic-rules.md`。涉及资源形态和格式时读取 `references/resource-form-rules.md`；主题归一化确有困难时才读取 `references/domain-vocabulary.md`。

### 2. 判断能否形成非任意的收集任务

`ready` 不只要求能识别一个主题，还必须存在足以指导资源取舍的收集锚点，例如：

- 内容本身已经具体；
- 年级、知识范围或学习任务能够限定结果；
- 用户提出了明确资源要求；
- 用户明确授权全范围探索或先做资源概览。

“小学数学资料”虽然能识别领域，但缺少年级、知识范围、任务或全范围授权，直接收集会产生任意结果，应澄清。

“覆盖整个小学阶段的数学资源，先看看有哪些类型”明确授权全范围探索，可以进入 Search。

### 3. 必要时只问一个问题

使用影响测试：

> 如果不问，Search 是否很可能只能随意选择内容，或者收集到另一类资源？

只有答案为“是”时澄清。一次只问一个能够最大幅度缩小不确定性的问题，提供 2–3 个容易理解的方向，同时允许自由回答。

组织问题时读取 `references/clarification-rules.md`。不要询问字段清单，不要告诉用户“还差几个信息”。

### 4. 写语义简报

`clarified_need` 用自然语言完整表达当前理解：

- 保留用户选择的内容粒度；
- 说明资源收集要支持的任务和使用方式；
- 写入会影响取舍的学习者信息；
- 明确哪些要求已确认；
- 需要澄清时说明当前已知信息和尚未解决的核心分叉。

不要在简报中加入平台、查询词、搜索数量、资源组合建议或没有证据的事实。

### 5. 保存证据与要求

`evidence` 只记录下游需要信任的用户事实：

```json
{
  "statement": "资源范围属于小学数学",
  "quote": "小学数学资料"
}
```

`requirements` 只记录用户明确要求，并保留强度和原话：

```json
{
  "text": "资源必须免费",
  "strength": "must",
  "evidence": "只要免费的"
}
```

强度只能是：

- `must`：不满足就不应进入候选；
- `prefer`：可以妥协但影响排序；
- `exclude`：明确不接受。

模型推断不能伪装成用户要求。确需采用的低风险默认写入 `assumptions`；没有默认时省略该字段。

## 输出

### ready

```json
{
  "_meta": {
    "schema_version": "intent-brief/v1",
    "session_id": "继承 request.json",
    "created_at": "ISO 8601"
  },
  "_summary": {"status": "ready"},
  "data": {
    "status": "ready",
    "raw_request": "用户原话",
    "clarified_need": "完整的资源收集需求简报",
    "evidence": [],
    "requirements": []
  }
}
```

### needs_clarification

```json
{
  "_summary": {
    "status": "needs_clarification",
    "question": "你希望按某个年级、某个数学知识点，还是整个小学阶段来收集？"
  },
  "data": {
    "status": "needs_clarification",
    "raw_request": "帮我找一些小学数学资料",
    "clarified_need": "已知用户需要小学数学资料，但尚无足以指导资源取舍的范围。",
    "evidence": [
      {"statement": "资源范围属于小学数学", "quote": "小学数学资料"}
    ],
    "requirements": [],
    "clarification": {
      "question": "你希望按某个年级、某个数学知识点，还是整个小学阶段来收集？",
      "reason": "当前范围横跨多个年级和内容方向，直接收集会产生任意结果"
    }
  }
}
```

## 校验与完成

运行：

```bash
python3 scripts/validate_output.py {session_dir}/stage1_intent.json
```

失败时修复一次并重试。第二次仍失败则向 Flow 返回结构化失败，不进入 Search。

只允许两种业务状态：

- `ready`；
- `needs_clarification`。

## 参考资料

- `references/semantic-rules.md`：需求理解、简报写法和事实边界；执行时必须读取。
- `references/clarification-rules.md`：判断收集锚点和组织问题时读取。
- `references/resource-form-rules.md`：处理资源形式、文件格式和交付要求时读取。
- `references/domain-vocabulary.md`：主题归一化确有困难时读取。
