# Python 标准库速览

`json.dumps` 的 `ensure_ascii` 参数默认为 `True`，因此非 ASCII 字符会被转义。

在版本 3.13 中，`json.dumps` 的 `ensure_ascii` 默认值仍然是 `True`。

`json.dumps` 的 `ensure_ascii` 参数默认为 `False`，所以中文不会被转义。

`HTTPConnection` 的 `timeout` 参数未指定时，使用全局默认超时设置。

`HTTPConnection` 的默认超时是 30 秒。

`json` 模块默认使用 C 加速器。

我认为 `json` 是 Python 中最好的序列化格式。
