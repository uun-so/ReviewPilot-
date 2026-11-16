# argparse

`argparse` 用于解析命令行参数。

## ArgumentParser

`ArgumentParser(prog=None, usage=None, description=None, epilog=None, parents=[], prefix_chars='-', fromfile_prefix_chars=None, argument_default=None, conflict_handler='error', add_help=True, allow_abbrev=True, exit_on_error=True)` 创建解析器。

`add_argument(name_or_flags, action='store', nargs=None, const=None, default=None, type=None, choices=None, required=False, help=None, metavar=None, dest=None)` 添加参数。

`add_subparsers(dest=None, ...)` 添加子命令。

`set_defaults(**kwargs)` 设置默认值。

`parse_args(args=None, namespace=None)` 解析参数并返回 `Namespace`。

`parse_known_args(args=None, namespace=None)` 返回 `(namespace, remaining)`。

`print_help(file=None)` 打印帮助。

`format_help()` 返回帮助字符串。

`exit(status=0, message=None)` 退出。

`error(message)` 打印用法并以状态码 2 退出。

## action 与 nargs

`action='store'` 存储单个值。

`action='store_true'` 默认 `False`，出现时设为 `True`。

`action='store_false'` 默认 `True`，出现时设为 `False`。

`action='append'` 把值追加到列表。

`action='count'` 统计出现次数，未指定时默认 `None`。

`action='extend'` 把多个值扩展到列表。

`nargs=None` 表示单个值；`nargs='?'` 表示零或一个；`nargs='*'` 表示零或多个；`nargs='+'` 表示至少一个；整数表示固定个数。

`required=True` 表示选项必填，只对可选参数有效。

## 类型、默认值与帮助

`type=int` 会把参数转换为整数。

`choices` 限制参数的取值，非法值会报错。

`default` 设置默认值。

`dest` 指定 `Namespace` 中的属性名。

`metavar` 控制帮助中的显示名称。

`help` 设置帮助文本。

`description` 设置解析器描述。

`epilog` 设置帮助末尾文本。

`parents=[...]` 共享其他解析器的参数。

`allow_abbrev=True` 允许长选项缩写；`False` 禁用缩写。

`fromfile_prefix_chars='@'` 允许从文件读取参数。

`-h/--help` 在 `add_help=True` 时自动添加。

参数错误时 `argparse` 以状态码 2 退出。

`Namespace` 是带有属性的简单对象；`vars(namespace)` 返回字典。

`argparse` 支持 `--` 终止选项解析。
