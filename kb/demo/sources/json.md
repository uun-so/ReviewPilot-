# json

`json` 模块用于 JSON 编码与解码。

## 编码

`json.dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, cls=None, indent=None, separators=None, default=None, sort_keys=False, **kw)` 把 Python 对象编码为 JSON 字符串，并返回 `str`。

`json.dump(obj, fp, ...)` 把 JSON 写入文件对象 `fp`，返回 `None`。

- `ensure_ascii` 默认为 `True`；为 `True` 时，非 ASCII 字符会被转义为 `\uXXXX`。设为 `False` 可以保留非 ASCII 字符的原文。
- `sort_keys` 默认为 `False`；设为 `True` 时，字典键会按键排序。
- `indent` 默认为 `None`；设为整数时，每一级缩进使用对应数量的空格。设为字符串时，使用该字符串缩进。
- `skipkeys` 默认为 `False`；为 `False` 时，键不是基本类型会抛出 `TypeError`。
- `allow_nan` 默认为 `True`；为 `True` 时，`NaN`、`Infinity` 和 `-Infinity` 可以被序列化。为 `False` 时会抛出 `ValueError`。
- `check_circular` 默认为 `True`；为 `True` 时会检测循环引用并抛出 `ValueError`。
- `default` 默认为 `None`；遇到无法直接序列化的对象时，如果提供了 `default`，会调用它并把返回值继续序列化；否则抛出 `TypeError`。
- `separators` 默认为 `None`；当 `indent is None` 时，默认项分隔符是 `', '`，键分隔符是 `': '`；当 `indent is not None` 时，默认项分隔符是 `','`，键分隔符是 `': '`。

`json.dumps` 直接序列化 `datetime` 对象会抛出 `TypeError`，除非提供 `default`。

## 解码

`json.loads(s, *, cls=None, object_hook=None, parse_float=None, parse_int=None, parse_constant=None, object_pairs_hook=None, **kw)` 解析 JSON 字符串并返回 Python 对象。

`json.load(fp, ...)` 从文件对象读取 JSON 并返回 Python 对象。

- `s` 可以是 `str`、`bytes` 或 `bytearray`。
- `parse_float` 默认为 `float`；`parse_int` 默认为 `int`。
- `parse_constant` 会被 `-Infinity`、`Infinity` 和 `NaN` 调用。
- `object_hook` 会收到每个解码后的 JSON 对象，并可以用它的返回值替换默认的 `dict`。
- `object_pairs_hook` 的优先级高于 `object_hook`。

`json.JSONDecodeError` 是 `ValueError` 的子类。

## 实现

CPython 的 `json` 模块优先使用 C 加速器 `_json`；如果不可用，会回退到纯 Python 实现。

```python
import json
text = json.dumps({"name": "张三"}, ensure_ascii=False)
data = json.loads(text)
print(data["name"])
```
