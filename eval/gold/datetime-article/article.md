# datetime 日期与时间笔记

`date(year, month, day)` 构造日期。

`datetime(...)` 构造日期时间，可以包含时分秒。

`date.today()` 返回本地日期。

`datetime.now()` 不带参数时返回本地 naive 时间。

`datetime.now(timezone.utc)` 返回带 UTC 时区的 aware 时间。

`datetime.utcnow()` 返回 naive UTC 时间，并在 Python 3.12 起被弃用。

`datetime.fromtimestamp(timestamp, tz=None)` 可以接受时区参数。

`datetime.timestamp()` 返回 POSIX 时间戳。

`timezone.utc` 是 UTC 时区对象。

`datetime.isoformat()` 返回 ISO 8601 字符串。

`datetime.isoformat()` 的默认分隔符是 `T`。

`datetime.strftime()` 按格式字符串格式化。

`datetime.strptime()` 的第一个参数是日期字符串，第二个是格式。

`datetime.combine()` 合并日期和时间。

`timedelta.total_seconds()` 返回总秒数。

`datetime` 是 `date` 的子类。

`date` 和 `datetime` 对象都是不可变的。

naive 与 aware 的 `datetime` 对象混用比较会抛出 `TypeError`。

`datetime.now()` 不带参数时返回带 UTC 时区的 aware 时间。

`datetime.utcnow()` 返回带 UTC 时区的 aware 时间。

`date.today()` 返回 UTC 日期。

`datetime` 是 `date` 的父类。

`datetime.isoformat()` 默认使用空格作为日期和时间分隔符。

`datetime.strptime()` 的第一个参数是格式字符串，第二个是日期字符串。

`datetime` 对象是可变的，可以直接修改 `year`。

`datetime.timestamp()` 对 naive 对象按 UTC 计算。

`datetime.fromtimestamp()` 的 `tz` 参数默认是 UTC。

`date` 对象可以包含时分秒。

`datetime.UTC` 别名是在 Python 3.13 中新增的。

`datetime.fromisoformat()` 支持所有 ISO 8601 格式。

`datetime.strptime()` 比 `dateutil.parser` 快。

`datetime` 的 `fold` 属性用于处理夏令时。

Windows 上 `datetime` 的时区数据库来自 IANA。

我认为 `datetime` 模块的 API 设计很糟糕。

`datetime` 是 Python 中最令人困惑的模块。
