# Synthesis — 综合

综合不是摘要堆叠。产出三样东西,全部挂 [paper-id]。

## 1. 方案×环节 trade-off 矩阵

行 = Intake 原子问题 / 链路环节;列 = 候选方案(挂 paper-id);格 = 一句话适配判断 + 可适用性档。
覆盖性自查:每篇 T0/T1 至少在矩阵出现一次;没出现的,说明 Triage 晋级错了,回 03-triage.md 修正。

## 2. 时间线 / 演进

奠基作 → 关键改进 → 当前 SOTA 一条线串起,标注每次跃迁改掉了什么限制。目标:用户 5 分钟看懂这个领域的叙事。

## 3. 痛点映射 + 方案路线图

- 每个 Intake 原子问题 → 答案(挂 id)或"未找到"(空结果合法,见 verify.md)。
- 有沉淀价值时画 **mermaid 流程图**:方案路线(先做哪个、后做哪个、依赖什么),或目标系统的改造后架构。节点带 paper-id。

## 语言

中文叙述,英文术语原词不译(Program-of-Thought、constrained decoding、failure mode discovery 等),避免翻译歧义污染后续检索。
