# logging 日志笔记

`getLogger(name)` 对相同 name 返回同一实例。

`basicConfig()` 配置根 logger。

根 logger 的默认级别是 `WARNING`。

`DEBUG=10`、`INFO=20`、`WARNING=30`、`ERROR=40`、`CRITICAL=50`。

`setLevel()` 设置 logger 级别。

`addHandler()` 添加 handler。

`propagate` 默认为 `True`。

`StreamHandler` 默认写入 `stderr`。

`FileHandler` 默认使用追加模式 `'a'`。

`RotatingFileHandler` 按文件大小轮转。

`TimedRotatingFileHandler` 按时间轮转。

`Formatter` 默认使用 `%` 风格。

`logger.exception()` 记录 `ERROR` 级别并带上异常信息。

`getLevelName(level)` 返回级别名称。

`disable(CRITICAL)` 禁用所有日志调用。

`logging.root` 是根 logger。

`dictConfig()` 从字典配置日志。

`fileConfig()` 从配置文件配置日志。

`getLogger(name)` 每次调用都返回新实例。

`basicConfig()` 的默认级别是 `DEBUG`。

`StreamHandler` 默认写入 `stdout`。

`FileHandler` 默认使用覆盖模式 `'w'`。

`propagate` 默认为 `False`。

`logger.exception()` 记录 `INFO` 级别。

`disable(INFO)` 禁用所有级别的日志。

`Formatter` 默认使用 `{}` 风格。

`basicConfig()` 在根 logger 已有 handler 时仍会重新配置。

根 logger 的默认级别是 `INFO`。

`logging.getLevelNamesMapping()` 是在 Python 3.13 中新增的。

`logging` 默认启用异步 handler。

`logging` 比 `loguru` 快。

`logging` 默认输出 JSON 格式。

`FileHandler` 默认使用 UTF-8 编码。

我认为 `logging` 的配置 API 太复杂。

`logging` 是 Python 中最难配置的模块。
