# Learn Loop 品牌视觉规范

当前系统采用“证据驱动的学习工作台”方向：以冷静的深海军蓝建立可信度，以纸白阅读面承载长文，以克制的金色标记关键动作和证据焦点，形成编辑阅读器与技术工作台的混合气质。

## 六个核心令牌

以下值由 `skills/learn-loop/assets/template.css` 的现有颜色等值转换而来，不改变当前品牌来源，仅统一为 OKLch 表达。

```css
:root {
  --bg: oklch(0.971 0.004 236.5);
  --surface: oklch(1 0 0);
  --fg: oklch(0.243 0.024 248.8);
  --muted: oklch(0.538 0.032 248.4);
  --border: oklch(0.911 0.011 234.8);
  --accent: oklch(0.759 0.121 80.8);
}
```

辅助深色导航面继续取自现有来源：`oklch(0.315 0.041 244)`；导航悬停面为 `oklch(0.421 0.056 236.3)`。后续状态色应从核心令牌派生，不再散落原始十六进制颜色。

## 字体栈

- 展示与长文标题：`"Songti SC", "STSong", "Noto Serif CJK SC", Georgia, serif`
- 正文与界面：`-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif`
- 数字、证据等级与技术标识：`ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`

## 视觉姿态

1. 先呈现结论和学习动作，再展开证据与生成过程；取证材料始终是次级层。
2. 长文使用窄阅读列和明确段落节奏，数据表、证据卡与练习卡可以突破阅读列，但不能让正文整页变宽。
3. 金色只承担当前焦点或主动作，每个视口最多出现两处高权重用法；状态不依赖金色表达。
4. 减少“所有内容都装进圆角卡片”的容器化；优先用留白、分栏、标题尺度和细分隔线建立层级。
5. 学习进度、本机自评、真实施考与费曼记录使用不同语义和文案，任何视觉合并都不得模糊事实边界。
