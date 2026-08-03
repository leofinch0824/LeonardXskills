# Learn Loop 运行目录命名调整

## 目标

让同一天内的多次主题学习在扁平 `learning/` 目录中可读、可排序且互不覆盖。

## 方案

- 将运行目录由 `<YYYY-MM-DD>-<slug>` 改为 `<YYYY-MM-DD>-<HHMMSS>-<topic-slug>`。
- 将 `slug` 定义为 `<HHMMSS>-<topic-slug>`，使 INDEX 和复习队列能够定位到具体学习轮次。
- 创建目录前检查目标路径；冲突时追加两位序号，不覆盖既有产物。
- 保持校验器兼容旧的 `<YYYY-MM-DD>-<topic-slug>` 目录。

## 验证

- 现有旧格式的完整模式 A fixture 继续通过。
- 新格式目录能从复习队列中以时间化 slug 找到对应记录。
