# Reframe — 上行翻译 playbook

上行翻译:把业务痛点转成学术可检索的形式。这是整个 SOP 杠杆最高的一步——词对不上,就会误以为"没人研究过"。

## 三步

1. **原子化**:把痛点拆成可独立检索的原子问题。一个原子问题只问一件事,且能用"哪类方案 + 哪个环节"回答。
2. **剥离领域词**:业务实体替换成结构角色(PCB → 工程文档图像;铜厚 → 语义相近的数值字段;钻孔表 → 多页表格证据)。领域词收进"领域词剥离清单",只在 Extract 阶段做可适用性映射时取回。
3. **映射学术词表**:每个原子问题给 2–4 个学术检索词(中英对照),优先借用 survey 标题里的词——那是该领域公认的词汇。

## 问题类型 → 检索策略

| 类型 | 问法 | 目标文献 |
|---|---|---|
| 算法型 | "有没有更好的 X" | 方法 survey + SOTA 论文 |
| 方法型 | "怎么设计对照实验 / 用什么指标" | benchmark / 评测方法论文(一等目标,不是配角) |
| 归因型 | "错误发生在哪一环" | failure analysis / error taxonomy / diagnostic evaluation |

## 示范(真实痛点的完整原子化)

业务痛点:"PCB 多图参数抽取中,VLM 频繁数值判断错误(单位换算错、基铜厚与完成铜厚混淆、大小比较错、跨页拼接),且无法归因到哪一环。"

| 原子问题 | 学术检索词(脱离 PCB 语境) |
|---|---|
| 数值从图读对没有 | document VQA / table understanding / OCR-free extraction |
| 单位归一化错(mm/mil/oz/μm、1/3 oz 分数记法) | quantity & unit extraction / measurement normalization |
| 两个数读对了但比较错 | LLM numerical reasoning / tool-augmented LLM / Program-of-Thought |
| 多图相似数值干扰、跨页拼接 | multi-document distraction robustness / lost-in-the-middle / evidence selection |
| 语义相近参数混淆 | schema-guided extraction / entity disambiguation |
| 失败样例压缩成错误模式 | automated failure mode discovery / failure clustering & taxonomy |
| Judge 读全文还是证据包 | LLM-as-a-Judge reliability / evidence compression faithfulness |
| Prompt Patch 自动优化+回归合入 | automatic prompt optimization(DSPy/MIPRO、TextGrad、OPRO)/ eval-driven development |

## 出口检查(进闸门前自查)

- 每个原子问题能独立检索、独立回答
- 用领域词剥离清单逐一对照:检索词表里一个领域词都不剩
- 词表里含"方法/评测"类词,不只是算法词
