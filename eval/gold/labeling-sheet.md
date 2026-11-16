# ReviewPilot 盲标表

> 标注时不要查看任何系统结论。判断只相对于 `kb/demo`，不要使用外部知识。

> 本表只列出本次生成 `labels.yaml` 的 case；已有标注不会被覆盖。

**结论取值**：`supported`（KB 明确支持）/ `conflict`（KB 明确反驳）/ `uncertain`（KB 未覆盖或证据不足）/ `non_claim`（观点、预测、定义、修辞，不是可判定主张）。

把结论填到每个 case 的 `labels.yaml` 的 `human_verdict` 字段，然后运行：

```bash
reviewpilot eval --gold eval/gold --kb kb/demo
```

## argparse-article

| ID | 主张（逐字） | 人工结论 | 备注 |
|---|---|---|---|
| argparse-article-001 | `ArgumentParser` 创建解析器。 |  |  |
| argparse-article-002 | `add_argument()` 添加参数。 |  |  |
| argparse-article-003 | `action='store_true'` 默认 `False`。 |  |  |
| argparse-article-004 | `action='store_false'` 默认 `True`。 |  |  |
| argparse-article-005 | `action='append'` 把值追加到列表。 |  |  |
| argparse-article-006 | `action='count'` 统计出现次数。 |  |  |
| argparse-article-007 | `nargs='+'` 表示至少一个参数。 |  |  |
| argparse-article-008 | `nargs='*'` 表示零个或多个参数。 |  |  |
| argparse-article-009 | `required=True` 表示选项必填。 |  |  |
| argparse-article-010 | `type=int` 会把参数转换为整数。 |  |  |
| argparse-article-011 | `choices` 限制参数取值。 |  |  |
| argparse-article-012 | `default` 设置默认值。 |  |  |
| argparse-article-013 | `dest` 指定 `Namespace` 中的属性名。 |  |  |
| argparse-article-014 | `parse_args()` 返回 `Namespace`。 |  |  |
| argparse-article-015 | `parse_known_args()` 返回 namespace 和剩余参数。 |  |  |
| argparse-article-016 | `add_subparsers()` 添加子命令。 |  |  |
| argparse-article-017 | `-h/--help` 在默认配置下自动添加。 |  |  |
| argparse-article-018 | 参数错误时 `argparse` 以状态码 2 退出。 |  |  |
| argparse-article-019 | `action='store_true'` 默认 `True`。 |  |  |
| argparse-article-020 | `action='store_false'` 默认 `False`。 |  |  |
| argparse-article-021 | `nargs='+'` 允许零个参数。 |  |  |
| argparse-article-022 | `nargs='*'` 要求至少一个参数。 |  |  |
| argparse-article-023 | `required=True` 只能用于位置参数。 |  |  |
| argparse-article-024 | `parse_args()` 返回字典。 |  |  |
| argparse-article-025 | 参数错误时退出码是 1。 |  |  |
| argparse-article-026 | `action='count'` 未指定时默认值是 1。 |  |  |
| argparse-article-027 | `allow_abbrev` 默认为 `False`。 |  |  |
| argparse-article-028 | `-h/--help` 需要手动添加。 |  |  |
| argparse-article-029 | `argparse` 在 Python 3.13 中支持从 TOML 配置文件读取参数。 |  |  |
| argparse-article-030 | `argparse` 比 `click` 更快。 |  |  |
| argparse-article-031 | `argparse` 默认支持 shell 补全。 |  |  |
| argparse-article-032 | `exit_on_error=False` 会抛出 `ArgumentError`。 |  |  |
| argparse-article-033 | `argparse` 默认输出彩色帮助。 |  |  |
| argparse-article-034 | 我认为 `argparse` 的 API 比 `click` 更直观。 |  |  |
| argparse-article-035 | `argparse` 是 Python 中最好的命令行库。 |  |  |

## datetime-article

| ID | 主张（逐字） | 人工结论 | 备注 |
|---|---|---|---|
| datetime-article-001 | `date(year, month, day)` 构造日期。 |  |  |
| datetime-article-002 | `datetime(...)` 构造日期时间，可以包含时分秒。 |  |  |
| datetime-article-003 | `date.today()` 返回本地日期。 |  |  |
| datetime-article-004 | `datetime.now()` 不带参数时返回本地 naive 时间。 |  |  |
| datetime-article-005 | `datetime.now(timezone.utc)` 返回带 UTC 时区的 aware 时间。 |  |  |
| datetime-article-006 | `datetime.utcnow()` 返回 naive UTC 时间，并在 Python 3.12 起被弃用。 |  |  |
| datetime-article-007 | `datetime.fromtimestamp(timestamp, tz=None)` 可以接受时区参数。 |  |  |
| datetime-article-008 | `datetime.timestamp()` 返回 POSIX 时间戳。 |  |  |
| datetime-article-009 | `timezone.utc` 是 UTC 时区对象。 |  |  |
| datetime-article-010 | `datetime.isoformat()` 返回 ISO 8601 字符串。 |  |  |
| datetime-article-011 | `datetime.isoformat()` 的默认分隔符是 `T`。 |  |  |
| datetime-article-012 | `datetime.strftime()` 按格式字符串格式化。 |  |  |
| datetime-article-013 | `datetime.strptime()` 的第一个参数是日期字符串，第二个是格式。 |  |  |
| datetime-article-014 | `datetime.combine()` 合并日期和时间。 |  |  |
| datetime-article-015 | `timedelta.total_seconds()` 返回总秒数。 |  |  |
| datetime-article-016 | `datetime` 是 `date` 的子类。 |  |  |
| datetime-article-017 | `date` 和 `datetime` 对象都是不可变的。 |  |  |
| datetime-article-018 | naive 与 aware 的 `datetime` 对象混用比较会抛出 `TypeError`。 |  |  |
| datetime-article-019 | `datetime.now()` 不带参数时返回带 UTC 时区的 aware 时间。 |  |  |
| datetime-article-020 | `datetime.utcnow()` 返回带 UTC 时区的 aware 时间。 |  |  |
| datetime-article-021 | `date.today()` 返回 UTC 日期。 |  |  |
| datetime-article-022 | `datetime` 是 `date` 的父类。 |  |  |
| datetime-article-023 | `datetime.isoformat()` 默认使用空格作为日期和时间分隔符。 |  |  |
| datetime-article-024 | `datetime.strptime()` 的第一个参数是格式字符串，第二个是日期字符串。 |  |  |
| datetime-article-025 | `datetime` 对象是可变的，可以直接修改 `year`。 |  |  |
| datetime-article-026 | `datetime.timestamp()` 对 naive 对象按 UTC 计算。 |  |  |
| datetime-article-027 | `datetime.fromtimestamp()` 的 `tz` 参数默认是 UTC。 |  |  |
| datetime-article-028 | `date` 对象可以包含时分秒。 |  |  |
| datetime-article-029 | `datetime.UTC` 别名是在 Python 3.13 中新增的。 |  |  |
| datetime-article-030 | `datetime.fromisoformat()` 支持所有 ISO 8601 格式。 |  |  |
| datetime-article-031 | `datetime.strptime()` 比 `dateutil.parser` 快。 |  |  |
| datetime-article-032 | `datetime` 的 `fold` 属性用于处理夏令时。 |  |  |
| datetime-article-033 | Windows 上 `datetime` 的时区数据库来自 IANA。 |  |  |
| datetime-article-034 | 我认为 `datetime` 模块的 API 设计很糟糕。 |  |  |
| datetime-article-035 | `datetime` 是 Python 中最令人困惑的模块。 |  |  |

## logging-article

| ID | 主张（逐字） | 人工结论 | 备注 |
|---|---|---|---|
| logging-article-001 | `getLogger(name)` 对相同 name 返回同一实例。 |  |  |
| logging-article-002 | `basicConfig()` 配置根 logger。 |  |  |
| logging-article-003 | 根 logger 的默认级别是 `WARNING`。 |  |  |
| logging-article-004 | `DEBUG=10`、`INFO=20`、`WARNING=30`、`ERROR=40`、`CRITICAL=50`。 |  |  |
| logging-article-005 | `setLevel()` 设置 logger 级别。 |  |  |
| logging-article-006 | `addHandler()` 添加 handler。 |  |  |
| logging-article-007 | `propagate` 默认为 `True`。 |  |  |
| logging-article-008 | `StreamHandler` 默认写入 `stderr`。 |  |  |
| logging-article-009 | `FileHandler` 默认使用追加模式 `'a'`。 |  |  |
| logging-article-010 | `RotatingFileHandler` 按文件大小轮转。 |  |  |
| logging-article-011 | `TimedRotatingFileHandler` 按时间轮转。 |  |  |
| logging-article-012 | `Formatter` 默认使用 `%` 风格。 |  |  |
| logging-article-013 | `logger.exception()` 记录 `ERROR` 级别并带上异常信息。 |  |  |
| logging-article-014 | `getLevelName(level)` 返回级别名称。 |  |  |
| logging-article-015 | `disable(CRITICAL)` 禁用所有日志调用。 |  |  |
| logging-article-016 | `logging.root` 是根 logger。 |  |  |
| logging-article-017 | `dictConfig()` 从字典配置日志。 |  |  |
| logging-article-018 | `fileConfig()` 从配置文件配置日志。 |  |  |
| logging-article-019 | `getLogger(name)` 每次调用都返回新实例。 |  |  |
| logging-article-020 | `basicConfig()` 的默认级别是 `DEBUG`。 |  |  |
| logging-article-021 | `StreamHandler` 默认写入 `stdout`。 |  |  |
| logging-article-022 | `FileHandler` 默认使用覆盖模式 `'w'`。 |  |  |
| logging-article-023 | `propagate` 默认为 `False`。 |  |  |
| logging-article-024 | `logger.exception()` 记录 `INFO` 级别。 |  |  |
| logging-article-025 | `disable(INFO)` 禁用所有级别的日志。 |  |  |
| logging-article-026 | `Formatter` 默认使用 `{}` 风格。 |  |  |
| logging-article-027 | `basicConfig()` 在根 logger 已有 handler 时仍会重新配置。 |  |  |
| logging-article-028 | 根 logger 的默认级别是 `INFO`。 |  |  |
| logging-article-029 | `logging.getLevelNamesMapping()` 是在 Python 3.13 中新增的。 |  |  |
| logging-article-030 | `logging` 默认启用异步 handler。 |  |  |
| logging-article-031 | `logging` 比 `loguru` 快。 |  |  |
| logging-article-032 | `logging` 默认输出 JSON 格式。 |  |  |
| logging-article-033 | `FileHandler` 默认使用 UTF-8 编码。 |  |  |
| logging-article-034 | 我认为 `logging` 的配置 API 太复杂。 |  |  |
| logging-article-035 | `logging` 是 Python 中最难配置的模块。 |  |  |

## pathlib-article

| ID | 主张（逐字） | 人工结论 | 备注 |
|---|---|---|---|
| pathlib-article-001 | `Path` 是具体路径类，会访问文件系统。 |  |  |
| pathlib-article-002 | `/` 运算符可以拼接路径。 |  |  |
| pathlib-article-003 | `Path.cwd()` 返回当前工作目录。 |  |  |
| pathlib-article-004 | `Path.home()` 返回用户主目录。 |  |  |
| pathlib-article-005 | `Path.name` 是路径的最后一段。 |  |  |
| pathlib-article-006 | `Path.suffix` 包含点号。 |  |  |
| pathlib-article-007 | `Path.parent` 返回父路径。 |  |  |
| pathlib-article-008 | `Path.exists()` 判断路径是否存在。 |  |  |
| pathlib-article-009 | `Path.is_file()` 判断是否为普通文件。 |  |  |
| pathlib-article-010 | `Path.is_dir()` 判断是否为目录。 |  |  |
| pathlib-article-011 | `Path.mkdir(parents=True)` 会创建父目录。 |  |  |
| pathlib-article-012 | `Path.mkdir(exist_ok=True)` 在目录已存在时不抛异常。 |  |  |
| pathlib-article-013 | `Path.unlink(missing_ok=True)` 在文件不存在时不抛异常。 |  |  |
| pathlib-article-014 | `Path.iterdir()` 返回目录项的可迭代对象。 |  |  |
| pathlib-article-015 | `Path.glob()` 按模式匹配路径，非递归。 |  |  |
| pathlib-article-016 | `Path.read_text()` 返回 `str`。 |  |  |
| pathlib-article-017 | `Path.write_text()` 返回写入的字符数。 |  |  |
| pathlib-article-018 | `Path.absolute()` 返回绝对路径，但不解析符号链接。 |  |  |
| pathlib-article-019 | `Path.mkdir()` 默认会递归创建父目录。 |  |  |
| pathlib-article-020 | `Path.unlink()` 默认在文件不存在时静默成功。 |  |  |
| pathlib-article-021 | `Path.suffix` 不包含点号。 |  |  |
| pathlib-article-022 | `Path.name` 返回包含父目录的完整路径。 |  |  |
| pathlib-article-023 | `Path.glob()` 默认递归搜索所有子目录。 |  |  |
| pathlib-article-024 | `Path.absolute()` 会解析符号链接。 |  |  |
| pathlib-article-025 | `Path.is_file()` 对目录返回 `True`。 |  |  |
| pathlib-article-026 | `Path.read_text()` 返回 `bytes`。 |  |  |
| pathlib-article-027 | `Path.write_text()` 返回写入的字节数。 |  |  |
| pathlib-article-028 | `Path` 是平台无关的纯路径类。 |  |  |
| pathlib-article-029 | `Path` 在 Python 3.14 中新增了 `copy()` 方法。 |  |  |
| pathlib-article-030 | `Path.glob()` 在 Windows 上区分大小写。 |  |  |
| pathlib-article-031 | `Path.read_text()` 默认使用 UTF-8 编码。 |  |  |
| pathlib-article-032 | `Path` 的性能比 `os.path` 快。 |  |  |
| pathlib-article-033 | `Path.walk()` 在 Python 3.12 中新增。 |  |  |
| pathlib-article-034 | 我认为 `pathlib` 比 `os.path` 更好用。 |  |  |
| pathlib-article-035 | `pathlib` 是 Python 中最优雅的路径库。 |  |  |
