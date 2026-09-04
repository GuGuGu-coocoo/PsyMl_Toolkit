# PsyML Core JSON Interface 1.0

Phase 12 冻结了供命令行与 Godot GUI 共用的本地接口。GUI 只创建 JSON 配置、启动本地 PsyML 子进程并读取 JSON/CSV/PNG 结果，不实现任何训练、预处理、验证或指标逻辑。

## 命令

```text
psyml capabilities
psyml preview --input DATA_PATH [--rows 5] [--include-sample]
psyml schema analysis_config|event|result
psyml run --config ANALYSIS_CONFIG_PATH [--events]
```

无子命令的旧参数形式暂时保留兼容。新 GUI 只能使用上面的版本化接口。

## 配置

`analysis_config.json` 必须声明 `schema_version: "1.0"`。完整约束见随 Python 包发布的 `psyml/schemas/analysis_config.schema.json`，也可用 `psyml schema analysis_config` 读取。

每次成功运行会把实际配置写入结果目录的 `analysis_config.json`；`config.json` 是当前兼容副本。重新运行前可以修改 `output_dir`，其余分析字段保持不变即可验证确定性。

## 状态事件与取消

`psyml run --config ... --events` 在标准输出逐行发送 JSON（JSONL）：

```json
{"event":"started","progress":0.0,"schema_version":"1.0"}
{"event":"completed","progress":1.0,"result_path":".../result.json","schema_version":"1.0"}
```

失败事件包含稳定的 `error.code`、Python 异常类型和面向用户的消息，不输出 traceback。调用方通过 SIGTERM 请求取消；PsyML 返回 `cancelled` 事件并以状态码 130 退出。调用方也可以在需要立即停止时终止整个本地子进程；由于 `result.json` 最后写入，不完整目录不会被误认为成功分析。

完整事件约束见 `event.schema.json`。

## 结果

成功运行最后写入 `result.json`，其中包括：

- `schema_version`
- `status`
- `task`
- 汇总 `metrics`
- `warnings`
- 相对结果目录的 `artifacts` 路径

调用方应先验证 `schema_version` 和 `status`，再按 `artifacts` 读取具体文件，不能猜测文件位置。完整约束见 `result.schema.json`。

## 数据预览与隐私

`preview` 默认只返回行列数、列名、数据类型和缺失数，不返回单元格。只有本地用户明确启用 `--include-sample` 时才返回最多 100 行样例。接口不上传数据。

## 错误码

- `file_not_found`：输入或配置文件不存在。
- `column_not_found`：目标或分组列不存在。
- `invalid_input`：配置、数据或参数不合法。
- `analysis_failed`：其他运行时失败。
- `cancelled`：调用方取消。

Godot 应根据错误码选择三语用户提示，同时保留原始 `message` 供详细信息区域显示。
