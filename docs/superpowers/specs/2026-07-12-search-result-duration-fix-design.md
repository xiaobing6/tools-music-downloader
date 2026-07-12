# 搜索结果时长字段修复设计

## 背景与根因

GUI 搜索结果中的时长全部显示为破折号。真实接口取证显示，网易云、Spotify 和酷我音乐的搜索结果都把时长放在 `extra_data.duration`，顶层不存在 `duration`。当前 `Song.from_api()` 读取顶层 `duration`，缺失时使用 `0`，随后被格式化为 `--:--`，GUI 再将未知时长显示为破折号。

同一次取证还确认：网易云在 `extra_data.has_hires` 返回 Hi-Res 标记；Spotify 和酷我音乐当前不返回该字段。当前模型同样错误地从顶层读取 `has_hires`。

## 目标

- 从站点当前的嵌套结构正确读取搜索结果时长。
- 从相同的 `extra_data` 对象读取可选的 Hi-Res 标记。
- 让共享 `Song` 模型的修复同时作用于 GUI 和 CLI。
- 不兼容旧式顶层 `duration` 或 `has_hires` 字段。

## 方案选择

采用在 `Song.from_api()` 中解析 `extra_data` 的方案。该方法已经负责把上游字典转换为领域模型，因此字段结构适配应留在这一边界，而不是让 `GdStudioClient` 重复扁平化数据，也不应让 GUI 单独理解上游结构。

## 数据流

1. `GdStudioClient` 保留上游原始搜索结果。
2. `SearchService` 将每条结果交给 `Song.from_api()`。
3. `Song.from_api()` 仅从 `extra_data.duration` 读取时长，并从 `extra_data.has_hires` 读取可选 Hi-Res 标记。
4. 缺失或不是字典的 `extra_data` 按未知时长和非 Hi-Res 处理。
5. `Song.to_result_dict()` 继续输出格式化后的时长，GUI 和 CLI 无需修改。

## 兼容性约束

- 不读取或回退到顶层 `duration`。
- 不读取或回退到顶层 `has_hires`。
- 当嵌套字段与顶层字段冲突时，以嵌套字段为唯一来源。
- 现有时长数值校验和 `--:--` 未知值语义保持不变。

## 测试设计

先增加会在当前实现上失败的领域模型测试：

- 参数化覆盖网易云、Spotify 和酷我音乐的真实响应形状，验证嵌套时长均被格式化。
- 验证网易云的嵌套 `has_hires` 会生成 Hi-Res 展示名。
- 验证 Spotify 和酷我音乐缺少 `has_hires` 时保持普通展示名。
- 验证仅有顶层 `duration`、`has_hires` 时不会被接受。

修复后运行领域模型和搜索服务测试，再执行完整 Python 测试、Ruff、格式检查和 mypy。该修改不涉及 Svelte 源码，因此不重建 GUI 静态资源。

## 非目标

- 不修改搜索 API 请求、签名或分页逻辑。
- 不扩展其他 `extra_data` 字段到领域模型。
- 不修改 GUI 时长显示样式。
- 不顺带处理当前工作区中的其他 GUI 改动。
