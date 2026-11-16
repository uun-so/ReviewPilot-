# logging

`logging` 是 Python 标准库的日志模块。

## Logger

`getLogger(name=None)` 返回 logger；相同 name 返回同一实例，不传 name 返回根 logger。

`logging.root` 是根 logger。

`basicConfig(**kwargs)` 配置根 logger。

`basicConfig()` 在根 logger 已有 handler 时不会重新配置，除非 `force=True`。

`setLevel(level)` 设置 logger 级别。

`addHandler(handler)` 添加 handler；`removeHandler(handler)` 移除 handler。

`propagate` 默认为 `True`，日志会向父 logger 传播。

`isEnabledFor(level)` 判断某个级别是否启用。

`getEffectiveLevel()` 返回有效级别。

## 级别

`DEBUG=10`、`INFO=20`、`WARNING=30`、`ERROR=40`、`CRITICAL=50`。

根 logger 的默认级别是 `WARNING`。

`getLevelName(level)` 返回级别名称。

`addLevelName(level, name)` 添加自定义级别名称。

`disable(level=CRITICAL)` 禁用指定级别及以下的日志调用；`disable(CRITICAL)` 禁用所有调用。

## Handler 与 Formatter

`StreamHandler(stream=None)` 默认写入 `stderr`。

`FileHandler(filename, mode='a', encoding=None, delay=False, errors=None)` 默认追加模式。

`RotatingFileHandler` 按文件大小轮转。

`TimedRotatingFileHandler` 按时间轮转。

`Formatter(fmt=None, datefmt=None, style='%', validate=True)` 默认使用 `%` 风格。

`logger.exception(msg, *args, **kwargs)` 记录 `ERROR` 级别并带上异常信息。

`LoggerAdapter` 用于给日志记录添加上下文。

`Filter` 用于过滤日志记录。

## 配置

`dictConfig(config)` 从字典配置日志。

`fileConfig(fname)` 从配置文件配置日志。

`captureWarnings(True)` 将 warnings 路由到 logging。

`shutdown()` 关闭所有 handler。

`Handler.handle(record)` 处理一条日志记录。

`LogRecord` 表示一条日志记录。
