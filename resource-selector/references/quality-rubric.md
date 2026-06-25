# 质量等级评估标准（selector 参考）

> ⚠️ **本文件已迁移至权威标准位置。**
> 全系统统一的质量评估标准定义在：
> **`../../shared/schemas/quality-rubric.md`**
>
> 本文件仅保留 selector 角度的补充说明，评分维度、权重、等级映射等一律以权威文件为准。

---

## 权威标准引用

**完整的质量评估标准（五维评分、S/A/B/C 等级映射、前置过滤、两级评估机制等）见：**

📖 [`../../shared/schemas/quality-rubric.md`](../../shared/schemas/quality-rubric.md)

以下是 selector 视角的核心要点速览。

---

## selector 评分要点速览

### 等级标识

| 等级 | 标识 | 加权总分 | 百分制 |
|------|------|---------|--------|
| S | ⭐⭐⭐⭐⭐ | 4.5-5.0 | 90-100 |
| A | ⭐⭐⭐⭐ | 3.5-4.4 | 75-89 |
| B | ⭐⭐⭐ | 2.5-3.4 | 60-74 |
| C | ⭐⭐ | 1.5-2.4 | 30-59 |

### 五维评分权重

| 维度 | 权重 | 说明 |
|------|------|------|
| 内容质量与完整性 | 25% | 是否系统完整、专业准确、制作精良 |
| 适龄匹配度 | 25% | 是否标注适龄、内容形式是否适合儿童 |
| 权威可信度 | 20% | 来源是否权威可靠 |
| 可获取性 | 20% | 是否免费、获取难度 |
| 安全与体验 | 10% | 广告多少、安全性、互动数据 |

> 详细评分标准（每维 1-5 分打分细则）见权威文件第四节。

---

## selector 展示中的质量分级

selector 在展示资源时，使用调度器校准后的最终 `quality_level`，展示规则如下：

1. **质量优先排序**：S级 → A级 → B级 → C级
2. **C级谨慎展示**：仅在候选极少时展示，且必须标注风险提示
3. **人工复核**：自动评分只是参考，最终由 Agent 做人工复核

详细展示模板见 `display-templates.md`。

---

## 参考资料

- [`../../shared/schemas/quality-rubric.md`](../../shared/schemas/quality-rubric.md) — **全系统统一质量评估标准（权威）**
- [`../../shared/schemas/resource-schema.md`](../../shared/schemas/resource-schema.md) — 资源元数据规范（quality_level 字段语义）
- [`../../shared/schemas/skill-contract.md`](../../shared/schemas/skill-contract.md) — 跨 Skill 上下文传递契约
- `display-templates.md` — 展示模板详细说明
