"""
DK-Lang HTTP 引擎 —— 高性能客户端/服务端 + RESTful路由 + WebSocket
特性：路由匹配、中间件、静态文件、JSON处理、WebSocket、GraphQL端点
"""
import json, os, re, threading, time, socket, http.server, urllib.parse, urllib.request
from typing import Any, Callable, Dict, List, Optional


# ── HTTP 客户端 ──────────────────────────────────────

class HttpClient:
    """HTTP 客户端（同步）"""
    def __init__(self, base_url: str = '', timeout: int = 30, headers: dict = None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.default_headers = headers or {}

    def _build_url(self, path: str) -> str:
        return f'{self.base_url}{path}' if self.base_url else path

    def request(self, method: str, path: str, body: Any = None, headers: dict = None) -> dict:
        url = self._build_url(path)
        hdrs = {**self.default_headers, **(headers or {})}
        data = None
        if body is not None:
            if isinstance(body, (dict, list)):
                data = json.dumps(body).encode('utf-8')
                hdrs.setdefault('Content-Type', 'application/json')
            elif isinstance(body, str):
                data = body.encode('utf-8')
            else:
                data = str(body).encode('utf-8')
        req = urllib.request.Request(url, data=data, method=method)
        for k, v in hdrs.items():
            req.add_header(k, str(v))
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode('utf-8')
                try:
                    body = json.loads(body)
                except:
                    pass
                return {'status': resp.status, 'headers': dict(resp.headers), 'body': body}
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            try: body = json.loads(body)
            except: pass
            return {'status': e.code, 'headers': dict(e.headers), 'body': body, 'error': str(e)}
        except Exception as e:
            return {'status': 0, 'error': str(e), 'body': None}

    def get(self, path: str, headers: dict = None) -> dict:
        return self.request('GET', path, headers=headers)

    def post(self, path: str, body: Any = None, headers: dict = None) -> dict:
        return self.request('POST', path, body, headers)

    def put(self, path: str, body: Any = None, headers: dict = None) -> dict:
        return self.request('PUT', path, body, headers)

    def patch(self, path: str, body: Any = None, headers: dict = None) -> dict:
        return self.request('PATCH', path, body, headers)

    def delete(self, path: str, headers: dict = None) -> dict:
        return self.request('DELETE', path, headers=headers)


# ── HTTP 服务端 ──────────────────────────────────────

class Request:
    """HTTP 请求对象"""
    def __init__(self, method: str, path: str, headers: dict, body: bytes, query: dict, params: dict = None):
        self.method = method.upper()
        self.path = path
        self.headers = headers
        self.body = body
        self.query = query
        self.params = params or {}
        self._json = None

    def json(self) -> Any:
        if self._json is None:
            try: self._json = json.loads(self.body)
            except: self._json = {}
        return self._json

    def text(self) -> str:
        return self.body.decode('utf-8') if isinstance(self.body, bytes) else str(self.body)


class Response:
    """HTTP 响应对象"""
    def __init__(self, status: int = 200, body: Any = None, headers: dict = None):
        self.status = status
        self.body = body
        self.headers = headers or {'Content-Type': 'application/json'}

    @classmethod
    def ok(cls, data: Any = None) -> 'Response':
        return cls(200, data)

    @classmethod
    def created(cls, data: Any = None) -> 'Response':
        return cls(201, data)

    @classmethod
    def no_content(cls) -> 'Response':
        return cls(204)

    @classmethod
    def bad_request(cls, message: str = 'Bad Request') -> 'Response':
        return cls(400, {'error': message})

    @classmethod
    def not_found(cls, message: str = 'Not Found') -> 'Response':
        return cls(404, {'error': message})

    @classmethod
    def server_error(cls, message: str = 'Internal Server Error') -> 'Response':
        return cls(500, {'error': message})

    def to_bytes(self) -> bytes:
        if self.body is None:
            return b''
        if isinstance(self.body, (dict, list)):
            return json.dumps(self.body, ensure_ascii=False).encode('utf-8')
        if isinstance(self.body, str):
            return self.body.encode('utf-8')
        return bytes(self.body)


class Router:
    """路由匹配器"""
    def __init__(self):
        self.routes: List[tuple] = []

    def add(self, method: str, pattern: str, handler: Callable):
        # 将 /users/:id 转换为正则 /users/(?P<id>[^/]+)
        regex = re.sub(r':(\w+)', r'(?P<\1>[^/]+)', pattern)
        self.routes.append((method.upper(), re.compile(f'^{regex}$'), handler, pattern))

    def get(self, pattern: str):
        def decorator(fn):
            self.add('GET', pattern, fn); return fn
        return decorator

    def post(self, pattern: str):
        def decorator(fn):
            self.add('POST', pattern, fn); return fn
        return decorator

    def put(self, pattern: str):
        def decorator(fn):
            self.add('PUT', pattern, fn); return fn
        return decorator

    def delete(self, pattern: str):
        def decorator(fn):
            self.add('DELETE', pattern, fn); return fn
        return decorator

    def match(self, method: str, path: str) -> tuple:
        for route_method, regex, handler, pattern in self.routes:
            if route_method == method.upper() or route_method == 'ANY':
                m = regex.match(path)
                if m:
                    return handler, m.groupdict()
        return None, {}


class HttpServer:
    """HTTP 服务端"""
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.router = Router()
        self._middleware: List[Callable] = []
        self._server: Optional[http.server.HTTPServer] = None
        self._static_dir: Optional[str] = None

    def use(self, middleware: Callable):
        """注册中间件 (request, next_handler) -> response"""
        self._middleware.append(middleware)

    def static(self, url_prefix: str, directory: str):
        """静态文件服务"""
        self._static_dir = directory
        def static_handler(req):
            file_path = req.path.replace(url_prefix, '', 1).lstrip('/')
            full_path = os.path.join(directory, file_path)
            if os.path.isfile(full_path):
                mime_map = {'.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript',
                            '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg',
                            '.svg': 'image/svg+xml', '.ico': 'image/x-icon'}
                ext = os.path.splitext(full_path)[1]
                with open(full_path, 'rb') as f:
                    return Response(200, f.read(), {'Content-Type': mime_map.get(ext, 'application/octet-stream')})
            return Response.not_found()
        self.router.add('GET', f'{url_prefix}/(?P<filepath>.+)', static_handler)

    def _create_handler(self):
        router = self.router
        middleware = self._middleware

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_request(self):
                # 解析请求
                parsed = urllib.parse.urlparse(self.path)
                query = dict(urllib.parse.parse_qsl(parsed.query))
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length) if content_length > 0 else b''
                req = Request(self.command, parsed.path, dict(self.headers), body, query)

                # 路由匹配
                handler_fn, params = router.match(self.command, parsed.path)
                if not handler_fn:
                    self._send_response(Response.not_found('路由未找到'))
                    return
                req.params = params

                # 中间件链
                def next_handler(r):
                    try:
                        return handler_fn(r)
                    except Exception as e:
                        return Response.server_error(str(e))

                if middleware:
                    for mw in reversed(middleware):
                        prev = next_handler
                        next_handler = lambda r, mw=mw, n=prev: mw(r, n)

                resp = next_handler(req)
                self._send_response(resp)

            def _send_response(self, resp):
                self.send_response(resp.status)
                for k, v in (resp.headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                data = resp.to_bytes()
                self.wfile.write(data)

            def do_GET(self): self.do_request()
            def do_POST(self): self.do_request()
            def do_PUT(self): self.do_request()
            def do_PATCH(self): self.do_request()
            def do_DELETE(self): self.do_request()
            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
                self.end_headers()

            def log_message(self, format, *args):
                pass  # 静默日志

        return Handler

    def start(self, blocking: bool = True):
        self._server = http.server.ThreadingHTTPServer((self.host, self.port), self._create_handler())
        print(f'[HTTP] 服务启动: http://{self.host}:{self.port}')
        if blocking:
            self._server.serve_forever()
        else:
            threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()


# ── WebSocket 服务端（简易实现） ──────────────────────

class WebSocketServer:
    """WebSocket 服务端（基于 threading）"""
    def __init__(self, host: str = '0.0.0.0', port: int = 8081):
        self.host = host
        self.port = port
        self._handlers: Dict[str, Callable] = {}
        self._sock: Optional[socket.socket] = None
        self._clients: List[socket.socket] = []
        self._running = False

    def on_message(self, handler: Callable):
        self._handlers['message'] = handler

    def on_connect(self, handler: Callable):
        self._handlers['connect'] = handler

    def broadcast(self, message: str):
        dead = []
        for client in self._clients:
            try:
                client.send(self._encode_frame(message))
            except:
                dead.append(client)
        for d in dead:
            self._clients.remove(d)

    def _encode_frame(self, text: str) -> bytes:
        data = text.encode('utf-8')
        frame = bytearray()
        frame.append(0x81)  # text frame, FIN
        length = len(data)
        if length < 126:
            frame.append(length)
        elif length < 65536:
            frame.append(126)
            frame.extend(length.to_bytes(2, 'big'))
        else:
            frame.append(127)
            frame.extend(length.to_bytes(8, 'big'))
        frame.extend(data)
        return bytes(frame)

    def _handle_client(self, client: socket.socket, addr):
        # WebSocket 握手
        try:
            data = client.recv(4096).decode('utf-8')
            key = re.search(r'Sec-WebSocket-Key: (.+)\r\n', data)
            if key:
                import hashlib, base64
                accept = base64.b64encode(
                    hashlib.sha1((key.group(1).strip() + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()
                ).decode()
                resp = (
                    'HTTP/1.1 101 Switching Protocols\r\n'
                    'Upgrade: websocket\r\n'
                    'Connection: Upgrade\r\n'
                    f'Sec-WebSocket-Accept: {accept}\r\n\r\n'
                )
                client.send(resp.encode())
                self._clients.append(client)
                if self._handlers.get('connect'):
                    self._handlers['connect'](client, addr)
                while self._running:
                    frame = client.recv(4096)
                    if not frame:
                        break
                    opcode = frame[0] & 0x0F
                    if opcode == 0x8:  # close
                        break
                    if opcode == 0x1:  # text
                        masked = frame[1] & 0x80
                        length = frame[1] & 0x7F
                        pos = 2
                        if length == 126:
                            length = int.from_bytes(frame[2:4], 'big')
                            pos = 4
                        elif length == 127:
                            length = int.from_bytes(frame[2:10], 'big')
                            pos = 10
                        if masked:
                            mask_key = frame[pos:pos+4]
                            pos += 4
                        payload = bytearray(frame[pos:pos+length])
                        if masked:
                            for i in range(len(payload)):
                                payload[i] ^= mask_key[i % 4]
                        if self._handlers.get('message'):
                            self._handlers['message'](client, payload.decode('utf-8'))
            self._clients.remove(client)
        except Exception:
            pass
        finally:
            if client in self._clients:
                self._clients.remove(client)
            client.close()

    def start(self, blocking: bool = True):
        self._running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(128)
        print(f'[WS] WebSocket 服务启动: ws://{self.host}:{self.port}')
        if blocking:
            while self._running:
                client, addr = self._sock.accept()
                threading.Thread(target=self._handle_client, args=(client, addr), daemon=True).start()

    def stop(self):
        self._running = False
        if self._sock:
            self._sock.close()


# ── GraphQL 简易端点 ──────────────────────────────────

class GraphQLResolver:
    """GraphQL 解析器映射"""
    def __init__(self):
        self._queries: Dict[str, Callable] = {}
        self._mutations: Dict[str, Callable] = {}

    def query(self, name: str):
        def decorator(fn):
            self._queries[name] = fn; return fn
        return decorator

    def mutation(self, name: str):
        def decorator(fn):
            self._mutations[name] = fn; return fn
        return decorator

    def execute(self, query_str: str, variables: dict = None) -> dict:
        """简易 GraphQL 执行（单查询/变更名匹配）"""
        # 解析 { fieldName(args) { subfields } }
        m = re.match(r'\s*(?:query|mutation)?\s*\{?\s*(\w+)', query_str)
        if not m:
            return {'errors': [{'message': '无法解析查询'}]}
        name = m.group(1)
        variables = variables or {}
        if name in self._queries:
            try:
                return {'data': {name: self._queries[name](**variables)}}
            except Exception as e:
                return {'errors': [{'message': str(e)}]}
        if name in self._mutations:
            try:
                return {'data': {name: self._mutations[name](**variables)}}
            except Exception as e:
                return {'errors': [{'message': str(e)}]}
        return {'errors': [{'message': f'未找到字段: {name}'}]}
