# datetime

`datetime` 模块提供日期、时间、时间差和时区类型。

## 构造与当前时间

`date(year, month, day)` 构造日期。

`datetime(year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)` 构造日期时间。

`date.today()` 返回本地日期。

`datetime.now(tz=None)` 返回当前时间；`tz=None` 时返回本地 naive 时间。

`datetime.now(timezone.utc)` 返回带 UTC 时区的 aware 时间。

`datetime.utcnow()` 返回 naive UTC 时间，并在 Python 3.12 起被弃用。

`datetime.fromtimestamp(timestamp, tz=None)` 从 POSIX 时间戳构造时间；`tz=None` 使用本地时区。

`datetime.timestamp()` 返回 POSIX 时间戳；naive 对象按本地时区解释，aware 对象按 UTC 计算。

## 时区与转换

`timezone.utc` 是 UTC 时区对象。

`timezone(timedelta)` 构造固定偏移时区。

`datetime.astimezone(tz=None)` 转换到指定时区。

`datetime.utcoffset()` 返回 UTC 偏移。

`datetime.tzinfo` 是时区信息属性。

## 格式化与解析

`date.isoformat()` 返回 ISO 8601 日期字符串。

`datetime.isoformat(sep='T', timespec='auto')` 返回 ISO 8601 日期时间字符串，默认分隔符是 `T`。

`date.fromisoformat(date_string)` 解析 ISO 日期。

`datetime.fromisoformat(date_string)` 解析 ISO 日期时间。

`datetime.strftime(format)` 按格式字符串格式化。

`datetime.strptime(date_string, format)` 按格式字符串解析；第一个参数是日期字符串，第二个是格式。

`datetime.combine(date, time, tzinfo=time.tzinfo)` 合并日期和时间。

`date.replace(year=..., month=..., day=...)` 返回替换字段的新对象。

## 时间差

`timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)` 表示时间差。

`timedelta.total_seconds()` 返回总秒数。

`timedelta` 支持与另一个 `timedelta` 相加、相减，也支持乘以整数或浮点数。

## 类型关系

`datetime` 是 `date` 的子类。

`date` 和 `datetime` 对象都是不可变的。

`date` 只有年、月、日；`datetime` 还包含时、分、秒、微秒和时区。

`datetime` 对象可以比较，但 naive 与 aware 对象混用会抛出 `TypeError`。
