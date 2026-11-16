# argparse 命令行解析笔记

`ArgumentParser` 创建解析器。

`add_argument()` 添加参数。

`action='store_true'` 默认 `False`。

`action='store_false'` 默认 `True`。

`action='append'` 把值追加到列表。

`action='count'` 统计出现次数。

`nargs='+'` 表示至少一个参数。

`nargs='*'` 表示零个或多个参数。

`required=True` 表示选项必填。

`type=int` 会把参数转换为整数。

`choices` 限制参数取值。

`default` 设置默认值。

`dest` 指定 `Namespace` 中的属性名。

`parse_args()` 返回 `Namespace`。

`parse_known_args()` 返回 namespace 和剩余参数。

`add_subparsers()` 添加子命令。

`-h/--help` 在默认配置下自动添加。

参数错误时 `argparse` 以状态码 2 退出。

`action='store_true'` 默认 `True`。

`action='store_false'` 默认 `False`。

`nargs='+'` 允许零个参数。

`nargs='*'` 要求至少一个参数。

`required=True` 只能用于位置参数。

`parse_args()` 返回字典。

参数错误时退出码是 1。

`action='count'` 未指定时默认值是 1。

`allow_abbrev` 默认为 `False`。

`-h/--help` 需要手动添加。

`argparse` 在 Python 3.13 中支持从 TOML 配置文件读取参数。

`argparse` 比 `click` 更快。

`argparse` 默认支持 shell 补全。

`exit_on_error=False` 会抛出 `ArgumentError`。

`argparse` 默认输出彩色帮助。

我认为 `argparse` 的 API 比 `click` 更直观。

`argparse` 是 Python 中最好的命令行库。
