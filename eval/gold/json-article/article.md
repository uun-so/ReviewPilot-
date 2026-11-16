# Python JSON 模块细节

`json.dumps` 返回一个 `str`。

`json.dump` 把 JSON 写入文件对象并返回 `None`。

`ensure_ascii` 的默认值是 `True`。

当 `ensure_ascii` 为 `True` 时，非 ASCII 字符会被转义为 `\uXXXX`。

把 `ensure_ascii` 设为 `False` 可以保留非 ASCII 字符的原文。

`sort_keys` 的默认值是 `False`。

把 `sort_keys` 设为 `True` 时，字典键会按键排序。

`indent` 的默认值是 `None`。

当 `indent` 是整数时，每一级缩进使用对应数量的空格。

`json.dumps` 的 `indent` 参数默认是 2。

`json.dumps` 默认使用 `separators=(', ', ': ')`。

当 `indent` 不是 `None` 时，默认的项分隔符是 `','`，键分隔符是 `': '`。

`skipkeys` 的默认值是 `False`。

`allow_nan` 的默认值是 `True`。

把 `allow_nan` 设为 `False` 会在遇到 `NaN` 时抛出 `ValueError`。

`default` 参数用于处理无法直接序列化的对象。

`check_circular` 的默认值是 `True`。

循环引用在 `check_circular` 为 `True` 时会抛出 `ValueError`。

`json.loads` 可以接受 `str`、`bytes` 或 `bytearray`。

`json.load` 从文件对象读取 JSON 并返回 Python 对象。

`json.JSONDecodeError` 是 `ValueError` 的子类。

`object_hook` 会收到每个解码后的 JSON 对象。

`parse_float` 默认使用 `float` 构造浮点数。

`parse_int` 默认使用 `int` 构造整数。

CPython 的 `json` 模块优先使用 C 加速器 `_json`。

`json.dumps` 的 `sort_keys` 参数默认为 `True`。

`json.dumps` 可以直接序列化 `datetime` 对象，无需 `default`。

`json` 模块支持在 JSON 文本中写注释。

`json.dumps` 在 CPython 3.13 中的速度比 `orjson` 快。

我认为 `json` 是 Python 中最好的序列化格式。
