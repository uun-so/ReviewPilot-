# pathlib 路径操作笔记

`Path` 是具体路径类，会访问文件系统。

`/` 运算符可以拼接路径。

`Path.cwd()` 返回当前工作目录。

`Path.home()` 返回用户主目录。

`Path.name` 是路径的最后一段。

`Path.suffix` 包含点号。

`Path.parent` 返回父路径。

`Path.exists()` 判断路径是否存在。

`Path.is_file()` 判断是否为普通文件。

`Path.is_dir()` 判断是否为目录。

`Path.mkdir(parents=True)` 会创建父目录。

`Path.mkdir(exist_ok=True)` 在目录已存在时不抛异常。

`Path.unlink(missing_ok=True)` 在文件不存在时不抛异常。

`Path.iterdir()` 返回目录项的可迭代对象。

`Path.glob()` 按模式匹配路径，非递归。

`Path.read_text()` 返回 `str`。

`Path.write_text()` 返回写入的字符数。

`Path.absolute()` 返回绝对路径，但不解析符号链接。

`Path.mkdir()` 默认会递归创建父目录。

`Path.unlink()` 默认在文件不存在时静默成功。

`Path.suffix` 不包含点号。

`Path.name` 返回包含父目录的完整路径。

`Path.glob()` 默认递归搜索所有子目录。

`Path.absolute()` 会解析符号链接。

`Path.is_file()` 对目录返回 `True`。

`Path.read_text()` 返回 `bytes`。

`Path.write_text()` 返回写入的字节数。

`Path` 是平台无关的纯路径类。

`Path` 在 Python 3.14 中新增了 `copy()` 方法。

`Path.glob()` 在 Windows 上区分大小写。

`Path.read_text()` 默认使用 UTF-8 编码。

`Path` 的性能比 `os.path` 快。

`Path.walk()` 在 Python 3.12 中新增。

我认为 `pathlib` 比 `os.path` 更好用。

`pathlib` 是 Python 中最优雅的路径库。
