# http.client

`http.client` 是 Python 标准库中的 HTTP 协议客户端，只支持 HTTP/1.x。

## HTTPConnection

`HTTPConnection(host, port=None, timeout=..., source_address=None, blocksize=8192)` 创建一个连接对象。每个 `HTTPConnection` 实例管理一个连接，不提供连接池。

- `timeout` 是超时时间，单位为秒；未指定时，使用 `socket.getdefaulttimeout()` 的全局默认值。
- `source_address` 是 `(host, port)` 元组，用于指定客户端的源地址。
- `blocksize` 的默认值是 8192。
- `request(method, url, body=None, headers={}, *, encode_chunked=False)` 发送请求；它不返回响应。
- `getresponse()` 返回 `HTTPResponse` 对象。
- `close()` 关闭连接。
- `putrequest(method, url, skip_host=False, skip_accept_encoding=False)` 发送请求行。
- `putheader(header, argument, ...)` 发送一个请求头。
- `endheaders()` 发送请求头的结束空行。
- `set_debuglevel(level)` 设置调试级别。

`HTTPConnection` 不会自动重试失败的请求。

## HTTPResponse

`HTTPResponse.status` 是整数 HTTP 状态码，例如 200 或 404。

- `HTTPResponse.reason` 是状态原因短语。
- `HTTPResponse.version` 是 HTTP 版本；HTTP/1.0 为 10，HTTP/1.1 为 11。
- `HTTPResponse.getheader(name, default=None)` 返回指定响应头的值。
- `HTTPResponse.getheaders()` 返回 `(header, value)` 元组的列表。
- `HTTPResponse.read(amt=None)` 读取并返回响应体，类型是 `bytes`。
- `HTTPResponse.close()` 关闭响应。

## HTTPS 与异常

`HTTPSConnection` 是 `HTTPConnection` 的子类，使用 TLS。

`HTTPException` 是 `http.client` 异常的基类。

`RemoteDisconnected` 在远端关闭连接且没有响应时抛出。
