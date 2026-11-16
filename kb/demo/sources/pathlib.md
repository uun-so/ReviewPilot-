# pathlib

`pathlib` 提供面向对象的文件系统路径。

## Path 基础

`Path` 是具体路径类，会访问文件系统；`PurePath` 是平台无关的纯路径类。

`Path("a") / "b"` 使用 `/` 运算符拼接路径。

`Path.cwd()` 返回当前工作目录。

`Path.home()` 返回用户主目录。

`Path.name` 是路径的最后一段。

`Path.stem` 是不含后缀的文件名。

`Path.suffix` 包含点号，例如 `.txt`。

`Path.parent` 返回父路径。

`Path.parts` 返回路径组件的元组。

`Path.joinpath(*others)` 拼接路径。

`Path.with_suffix(suffix)` 返回替换后缀的新路径。

`Path.with_name(name)` 返回替换最后一段的新路径。

`Path.as_posix()` 返回 POSIX 风格的字符串。

## 查询与判断

`Path.exists()` 判断路径是否存在。

`Path.is_file()` 判断是否为普通文件。

`Path.is_dir()` 判断是否为目录。

`Path.is_symlink()` 判断是否为符号链接。

`Path.stat()` 返回 `os.stat_result`。

`Path.samefile(other)` 判断是否指向同一文件。

`Path.absolute()` 返回绝对路径，但不解析符号链接。

`Path.resolve()` 返回绝对路径，并解析符号链接。

## 修改文件系统

`Path.mkdir(parents=False, exist_ok=False)` 创建目录；`parents=True` 会创建父目录，`exist_ok=True` 在目录已存在时不抛出 `FileExistsError`。

`Path.touch(exist_ok=True)` 创建空文件。

`Path.unlink(missing_ok=False)` 删除文件；`missing_ok=True` 在文件不存在时不抛出 `FileNotFoundError`。

`Path.rmdir()` 删除空目录。

`Path.rename(target)` 重命名路径。

`Path.replace(target)` 替换目标路径。

`Path.chmod(mode)` 修改权限。

## 读写与遍历

`Path.iterdir()` 返回目录项的可迭代对象。

`Path.glob(pattern)` 按模式匹配路径，非递归；`Path.rglob(pattern)` 递归匹配。

`Path.read_text(encoding=None, errors=None)` 读取文本并返回 `str`。

`Path.write_text(data, encoding=None, errors=None)` 写入文本，返回写入的字符数。

`Path.read_bytes()` 读取字节。

`Path.write_bytes(data)` 写入字节。

`Path.open(mode='r', buffering=-1, encoding=None, errors=None, newline=None)` 打开文件。
