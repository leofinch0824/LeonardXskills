# 第 10 步纪律：压缩、回灌与复习

## 速查表六件套

按原文顺序生成：一句大白话定义、核心要点、3–5 个实际应用场景、易错与易混、上场前检查清单、恰好 5 道快问快答（每题恰好一个答案）。核心要点服务于使用前 5 分钟回看，不把长篇简报复制过来。答案写进`10-cheatsheet.md`事实源，HTML 只渲染、不得在视图层补写答案。

## 事实源与视图

Markdown 产物集是唯一事实源。HTML 读取并渲染产物，不能反向成为模式 B/C 的唯一数据。施考后如要展示成绩，更新 Markdown 记录，再重渲染 HTML。

## 回灌边界

- `<learning-root>/INDEX.md`：由`finalize_run.py`按运行 ID 幂等追加日期、运行 ID、主题、练习状态和运行目录。
- `<state-root>/review-queue.md`：通过 `review_queue.py --add` 登记 1、7、30 天到期日；得分后用 `--record-score` 写历史得分并推进间隔。
- `<state-root>/learner-profile.md`：只追加用户明确确认的长期事实和依据；不写模型从表现推断的偏好。开场学习画像属本轮一次性场景，默认不进 profile；仅当用户明确表示“记住这个”时才回灌，并引用原话与日期。

`--bootstrap`和回灌都不能覆盖已有历史行。同一运行 ID 的相同行是幂等 no-op，字段冲突则停止最终化。每轮使用`<HHMMSS>-<topic-slug>`作为 slug，并以`<YYYY-MM-DD>-<slug>`建立运行目录；同主题的新轮次保留新的时间化 slug。若目标目录已存在，在 slug 后追加两位序号。

步骤 10 本身不写回灌元数据。步骤 10 通过后统一运行`finalize_run.py`：先验证全部 Markdown，静态构建并验证 HTML，再登记 INDEX 和复习队列，可选更新 profile，最后才把`run-state.md`标为完成。长期 profile 更新必须同时收到事实和用户确认原话。

## 复习模式

`review_queue.py --due` 只列下次复习日期已到的主题。复习再次走模式 B，优先历史弱项与终极挑战；完成后记录得分和下一间隔，不删除原有得分。
