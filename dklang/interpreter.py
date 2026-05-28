"""DK-Lang 解释执行器。树遍历执行，栈式作用域。读取 DEVELOPER.md。"""
import time, random, os, base64, json, threading, traceback
from .ast_nodes import *
from .lexer import Lexer
from .parser import Parser


class Environment:
    def __init__(self, parent=None):
        self.parent = parent; self._vars = {}
    def define(self, n, v, c=False): self._vars[n] = (v, c)
    def assign(self, n, v):
        if n in self._vars:
            _, ct = self._vars[n]
            if ct: raise DKError('NameError', f'不能对常量 "{n}" 赋值')
            self._vars[n] = (v, False); return
        if self.parent: self.parent.assign(n, v); return
        raise DKNameError(f'未定义的变量 "{n}"')
    def get(self, n):
        if n in self._vars: return self._vars[n][0]
        if self.parent: return self.parent.get(n)
        raise DKNameError(f'未定义的变量 "{n}"')
    def has(self, n):
        if n in self._vars: return True
        return self.parent.has(n) if self.parent else False


class Interpreter:
    def __init__(self, ctx=None):
        self.glob = Environment()
        self.env = self.glob
        self.funcs = {}
        self.ffi = {}
        self.permits = set()
        self.sandbox = False
        self.trace_vars = set()
        self.aliases = {}
        self.macros = {}
        self.classes = {}
        self.version = None
        self.ctx = ctx or {}
        self._register_builtins()
        self._load_ffi()
        self._register_stdlib()
        self._register_extensions()

    def _register_extensions(self):
        try:
            from .extensions import register_all
            register_all(self)
        except Exception:
            pass

    def _load_ffi(self):
        try: from .ffi import FFI; self.ffi_loader = FFI()
        except: self.ffi_loader = None

    def _register_stdlib(self):
        std = os.path.join(os.path.dirname(__file__), 'stdlib')
        if os.path.isdir(std):
            for f in os.listdir(std):
                if f.endswith('.dk'):
                    try:
                        with open(os.path.join(std,f),'r',encoding='utf-8') as fp:
                            self._load_source(fp.read())
                    except: pass

    def _load_source(self, source):
        try:
            lexer = Lexer(source); tokens = lexer.tokenize()
            parser = Parser(tokens); ast = parser.parse()
            for d in ast.declarations:
                if isinstance(d, FuncDefNode): self.funcs[d.name] = d
                elif isinstance(d, MacroNode): self.macros[d.name] = d
                elif isinstance(d, AliasNode): self.aliases[d.alias_name] = d
                elif isinstance(d, ClassDefNode): self.classes[d.name] = d
        except: pass

    # ── 内置函数注册 ─────────────────────────────────────
    def _register_builtins(self):
        b = self.glob
        b.define('print', self._b_print, True)
        b.define('len', self._b_len, True)
        b.define('typeof', lambda v: type(v).__name__, True)
        b.define('_exit', lambda: os._exit(0), True)
        b.define('_thread', self._b_thread, True)
        b.define('_join', self._b_join, True)
        b.define('_str_cut', self._b_str_cut, True)
        b.define('_str_find', self._b_str_find, True)
        b.define('_str_repl', self._b_str_repl, True)
        b.define('_str_len', self._b_str_len, True)
        b.define('_str_join', self._b_str_join, True)
        b.define('_arr_len', self._b_arr_len, True)
        b.define('_set_add', self._b_set_add, True)

    def _b_print(self, *args):
        text = ' '.join(self._to_str(a) for a in args)
        try:
            print(text)
        except UnicodeEncodeError:
            import sys
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            print(text)

    def _b_len(self, v):
        if hasattr(v, '__len__'): return len(v)
        raise DKTypeError(f'len 不支持 {type(v).__name__}')

    def _b_thread(self, name, block):
        def runner():
            ie = Interpreter(ctx=self.ctx); ie.funcs = dict(self.funcs)
            ie.env.define(name, None)
            try: ie._eval_block(block, ie.env)
            except Exception as e: print(f'[Thread:{name}] {e}')
        t = threading.Thread(target=runner, name=name, daemon=True)
        t.start(); self.glob.define(f'_thread_{name}', t); return t

    def _b_join(self, name):
        t = self.glob.get(f'_thread_{name}')
        if t: t.join()

    def _b_str_cut(self, src, start, length):
        return str(src)[int(start):int(start)+int(length)]

    def _b_str_find(self, src, sub):
        return str(src).find(str(sub))

    def _b_str_repl(self, src, old, new):
        return str(src).replace(str(old), str(new))

    def _b_str_len(self, src):
        return len(str(src))

    def _b_str_join(self, sep, *parts):
        return str(sep).join(str(p) for p in parts)

    def _b_arr_len(self, arr):
        if arr is None: return 0
        if hasattr(arr, '__len__'): return len(arr)
        return 0

    def _b_set_add(self, s, v):
        if isinstance(s, set): s.add(v)
        elif isinstance(s, list): s.append(v)
        return s

    def _to_str(self, v):
        if v is None: return 'nil'
        if isinstance(v, bool): return 'true' if v else 'false'
        if isinstance(v, float):
            if v == int(v): return str(int(v))
        return str(v)

    # ── 主入口 ──────────────────────────────────────────
    def execute(self, prog: ProgramNode):
        # 第一遍：收集声明
        for d in prog.declarations:
            if isinstance(d, VersionNode):
                self.version = d.version_str
            elif isinstance(d, PermitNode):
                self.permits.add(d.permission)
            elif isinstance(d, FuncDefNode):
                self.funcs[d.name] = d
            elif isinstance(d, ClassDefNode):
                self.classes[d.name] = d
            elif isinstance(d, MacroNode):
                self.macros[d.name] = d
            elif isinstance(d, AliasNode):
                self.aliases[d.alias_name] = d
            elif isinstance(d, ImportNode):
                self._handle_use(d)
            elif isinstance(d, FfiImportNode):
                self._handle_ffi_import(d)
            elif isinstance(d, TypeAliasNode):
                self.glob.define(d.alias, d.original)

        # 第二遍：执行
        result = None
        for d in prog.declarations:
            if isinstance(d, (VersionNode, PermitNode, FuncDefNode, ClassDefNode, MacroNode, AliasNode, ImportNode, FfiImportNode)):
                continue
            r = self.eval(d); result = r if r is not None else result
        return result

    # ── 节点求值 ────────────────────────────────────────
    def eval(self, n, env=None):
        if n is None: return None
        e = env or self.env
        m = {
            VarDeclNode: self._ev_var, ConstDeclNode: self._ev_const, AssignNode: self._ev_assign,
            IfNode: self._ev_if, WhileNode: self._ev_while, LoopNode: self._ev_loop,
            SwitchNode: self._ev_switch, ReturnNode: self._ev_ret, BreakNode: self._ev_break,
            NextNode: self._ev_next, BlockNode: self._ev_block, ExprStmtNode: self._ev_es,
            BinaryOpNode: self._ev_bin, UnaryOpNode: self._ev_un, VarRefNode: self._ev_ref,
            LiteralNode: self._ev_lit, CallNode: self._ev_call, IndexNode: self._ev_idx,
            ListLiteralNode: self._ev_list, MapLiteralNode: self._ev_map, SetLiteralNode: self._ev_set,
            AsNode: self._ev_as, TryNode: self._ev_try, ThrowNode: self._ev_throw,
            FileReadNode: self._ev_fread, FileWriteNode: self._ev_fwrite, FileExistNode: self._ev_fexist,
            LogNode: self._ev_log, TimeNode: self._ev_time, RandNode: self._ev_rand,
            Base64Node: self._ev_b64, WaitNode: self._ev_wait,
            AiAskNode: self._ev_ai_ask, AiExtractNode: self._ev_ai_extract, AiSummarizeNode: self._ev_ai_summarize,
            AiClassifyNode: self._ev_ai_classify, AiTranslateNode: self._ev_ai_translate,
            CtxNode: self._ev_ctx, PromptNode: self._ev_prompt, AiImageNode: self._ev_ai_image,
            ArrayPushNode: self._ev_push, ArrayPopNode: self._ev_pop,
            MapSetNode: self._ev_mapset, MapDelNode: self._ev_mapdel, MapGetNode: self._ev_mapget,
            HttpGetNode: self._ev_http_get, HttpPostNode: self._ev_http_post,
            ExecNode: self._ev_exec, EnvGetNode: self._ev_envget, EnvSetNode: self._ev_envset,
            SandboxNode: self._ev_sandbox, AuditNode: self._ev_audit,
            AsyncNode: self._ev_async, AwaitNode: self._ev_await,
            ClassDefNode: self._ev_class, NewNode: self._ev_new,
            EvalNode: self._ev_eval, TraceNode: self._ev_trace,
            ImportNode: lambda n: None, FfiImportNode: lambda n: None,
            TypeAliasNode: lambda n: None, VersionNode: lambda n: None, PermitNode: lambda n: None,
            MacroNode: lambda n: None, AliasNode: lambda n: None,
            MemberAccessNode: self._ev_member,
            ArrLenNode: self._ev_arr_len,
            ServerNode: self._ev_server,
            MapHasNode: self._ev_maphas,
        }
        h = m.get(type(n))
        if h: return h(n, e)
        raise DKError('RuntimeError', f'无法执行节点: {type(n).__name__}')

    def _push(self): self.env = Environment(self.env)
    def _pop(self): self.env = self.env.parent

    # ── 基础求值 ────────────────────────────────────────
    def _ev_var(self, n, e):
        dv = DEFAULT_VALUES.get(type(n.var_type), [] if isinstance(n.var_type, ListType) else {} if isinstance(n.var_type, MapType) else set() if isinstance(n.var_type, SetType) else None)
        if n.init_expr is not None:
            dv = self.eval(n.init_expr, e)
        e.define(n.name, dv); return dv

    def _ev_const(self, n, e):
        v = self.eval(n.value, e); e.define(n.name, v, True); return v

    def _ev_assign(self, n, e):
        v = self.eval(n.value, e); e.assign(n.name, v)
        if n.name in self.trace_vars: print(f'[TRACE] {n.name} = {v}')
        return v

    def _ev_bin(self, n, e):
        l, r = self.eval(n.left, e), self.eval(n.right, e)
        # 单词运算符 → 符号映射
        op_map = {'add':'+','sub':'-','mul':'*','div':'/','mod':'%',
                  'gt':'>','lt':'<','eq':'==','ne':'!=','ge':'>=','le':'<='}
        n.op = op_map.get(n.op, n.op)
        if n.op in ('+','-','*','/'):
            if n.op == '+': return l + r
            if n.op == '-': return l - r
            if n.op == '*': return l * r
            if n.op == '/':
                if r == 0: raise DKArithError('除数为0')
                result = l / r
                # 如果操作数都是整数且结果无小数，返回 int
                if isinstance(l, int) and isinstance(r, int) and result == int(result):
                    return int(result)
                return result
        if n.op == '%':
            if r == 0: raise DKArithError('取模除数为0')
            return l % r
        if n.op in ('>','<','==','!=','>=','<='):
            if n.op == '>': return l > r
            if n.op == '<': return l < r
            if n.op == '==': return l == r
            if n.op == '!=': return l != r
            if n.op == '>=': return l >= r
            if n.op == '<=': return l <= r
        if n.op == 'and': return bool(l) and bool(r)
        if n.op == 'or': return bool(l) or bool(r)
        # 字符串操作
        if n.op == 'str_join':
            sep = str(l) if l else ''
            parts = [str(self.eval(x, e)) for x in n.right.elements] if isinstance(n.right, ListLiteralNode) else [str(r)]
            return sep.join(parts)
        if n.op == 'str_find':
            return str(l).find(str(r))
        if n.op == 'str_repl':
            lnr = n.right
            old = str(self.eval(lnr.left, e)); new = str(self.eval(lnr.right, e))
            return str(l).replace(old, new)
        if n.op == 'str_cut':
            lnr = n.right; st = int(self.eval(lnr.left, e)); ln = int(self.eval(lnr.right, e))
            return str(l)[st:st+ln]
        if n.op == 'set_has':
            return self.eval(n.right, e) in (l if isinstance(l, (set, list)) else set())
        raise DKError('RuntimeError', f'未知运算符: {n.op}')

    def _ev_un(self, n, e):
        v = self.eval(n.operand, e)
        if n.op == 'not': return not bool(v)
        if n.op == '-': return -v
        if n.op == 'str_len': return len(str(v)) if isinstance(v, str) else len(v) if hasattr(v,'__len__') else 0
        return v

    def _ev_ref(self, n, e):
        if n.name == 'THIS': return e.get('__this__')
        if n.name == 'SUPER': return e.get('__super__')
        return e.get(n.name)

    def _ev_lit(self, n, e): return n.value

    def _ev_list(self, n, e): return [self.eval(x, e) for x in n.elements]

    def _ev_map(self, n, e):
        return {self.eval(k, e): self.eval(v, e) for k, v in n.pairs}

    def _ev_set(self, n, e):
        return {self.eval(x, e) for x in n.elements}

    def _ev_call(self, n, e):
        # 检查 FFI
        import sys
        parts = n.name.split('.', 1)
        if parts[0] in self.ffi:
            mod = self.ffi[parts[0]]
            args = [self.eval(a, e) for a in n.arguments]
            if len(parts) > 1:
                return self._ffi_call(mod['lang'], mod['module'], parts[1], args)
            else:
                return self._ffi_call(mod['lang'], mod['module'], None, args)

        # 用户函数 → 优先检查（避免内置遮蔽）
        if n.name in self.funcs:
            fd = self.funcs[n.name]
            args = [self.eval(a, e) for a in n.arguments]
            # 参数数量检查
            if len(args) != len(fd.params):
                raise DKError('ArityError',
                    f'函数 "{n.name}" 期望 {len(fd.params)} 个参数，但传入了 {len(args)} 个')
            self._push()
            for (pn, _), av in zip(fd.params, args):
                self.env.define(pn, av)
            try:
                return self._ev_block(fd.body, self.env)
            except ReturnSignal as rs:
                return rs.value
            finally:
                self._pop()

        # 内置 → 后检查（作为 fallback）
        if self.glob.has(n.name):
            fn = self.glob.get(n.name)
            if callable(fn):
                args = [self.eval(a, e) for a in n.arguments]
                return fn(*args)

        raise DKNameError(f'未定义的函数 "{n.name}"')

    def _ev_idx(self, n, e):
        t = self.eval(n.target, e); i = self.eval(n.index, e)
        if isinstance(t, (list, str, tuple)): return t[int(i)]
        if isinstance(t, dict): return t[i]
        raise DKTypeError(f'{type(t).__name__} 不支持索引')

    def _ev_as(self, n, e):
        v = self.eval(n.expr, e)
        if isinstance(n.target_type, IntType): return int(v)
        if isinstance(n.target_type, RealType): return float(v)
        if isinstance(n.target_type, StrType): return str(v)
        if isinstance(n.target_type, BoolType): return bool(v)
        return v

    def _ev_member(self, n, e):
        t = self.eval(n.target, e)
        if isinstance(t, list) and n.member == 'len': return len(t)
        if isinstance(t, dict) and n.member == 'len': return len(t)
        if isinstance(t, str) and n.member == 'len': return len(t)
        return getattr(t, n.member, None)

    # ── 控制流 ──────────────────────────────────────────
    def _ev_block(self, n, e):
        old = self.env; self.env = e
        try:
            r = None
            for s in n.statements: r = self.eval(s, e)
            return r
        finally: self.env = old

    def _ev_if(self, n, e):
        if self._truthy(self.eval(n.condition, e)):
            return self._ev_block(n.then_block, Environment(e))
        for c, b in n.elifs:
            if self._truthy(self.eval(c, e)): return self._ev_block(b, Environment(e))
        if n.else_block: return self._ev_block(n.else_block, Environment(e))
        return None

    def _ev_while(self, n, e):
        while self._truthy(self.eval(n.condition, e)):
            try: self._ev_block(n.body, Environment(e))
            except BreakSignal: break
            except NextSignal: continue

    def _ev_loop(self, n, e):
        self._push()
        # 自动定义循环变量（修复 BUG-INT-05: LOOP 变量需自动声明）
        if isinstance(n.init, AssignNode):
            self.env.define(n.init.name, 0)
        self.eval(n.init, self.env)
        try:
            while self._truthy(self.eval(n.condition, self.env)):
                try: self._ev_block(n.body, Environment(self.env))
                except BreakSignal: break
                except NextSignal: pass
                self.eval(n.step, self.env)
        finally: self._pop()

    def _ev_switch(self, n, e):
        v = self.eval(n.expr, e)
        for cv, cb in n.cases:
            if self.eval(cv, e) == v: return self._ev_block(cb, Environment(e))
        if n.default: return self._ev_block(n.default, Environment(e))
        return None

    def _ev_ret(self, n, e):
        raise ReturnSignal(self.eval(n.expr, e) if n.expr else None)

    def _ev_break(self, n, e): raise BreakSignal()
    def _ev_next(self, n, e): raise NextSignal()
    def _ev_es(self, n, e): return self.eval(n.expr, e)

    # ── IO / 异常 ───────────────────────────────────────
    def _ev_try(self, n, e):
        try: return self._ev_block(n.try_block, Environment(e))
        except DKError as err:
            for et, cb in n.catches:
                if err.error_type == et: return self._ev_block(cb, Environment(e))
            raise
        except ReturnSignal: raise
        except BreakSignal: raise
        except NextSignal: raise
        except BaseException as err:
            ename = type(err).__name__
            for et, cb in n.catches:
                if et == 'Exception' or et == 'Error' or et == ename:
                    return self._ev_block(cb, Environment(e))
            raise

    def _ev_throw(self, n, e):
        msg = self.eval(n.message, e) if n.message else ''
        raise DKError(n.error_type, str(msg))

    def _ev_fread(self, n, e):
        self._check_perm('file_read')
        p = str(self.eval(n.path, e))
        try:
            with open(p, 'r', encoding='utf-8') as f: v = f.read()
        except FileNotFoundError:
            raise DKIOError(f'文件不存在: {p}')
        e.assign(n.result_var, v); return v

    def _ev_fwrite(self, n, e):
        self._check_perm('file_write')
        p = str(self.eval(n.path, e)); c = str(self.eval(n.content, e))
        with open(p, 'w', encoding='utf-8') as f: f.write(c)

    def _ev_fexist(self, n, e):
        self._check_perm('file_read')
        v = os.path.exists(str(self.eval(n.path, e)))
        e.assign(n.result_var, v); return v

    def _ev_log(self, n, e):
        parts = [self._to_str(self.eval(p, e)) for p in n.message_parts]
        msg = ' '.join(parts)
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        text = f'[{ts}] [{n.level.upper()}] {msg}'
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode('utf-8', errors='replace').decode('gbk', errors='replace'))

    def _ev_time(self, n, e):
        fmt = n.fmt
        if fmt != 'unix':
            # 翻译 DK-Lang 风格格式字符串到 Python 风格
            fmt = fmt.replace('YYYY', '%Y').replace('MM', '%m').replace('DD', '%d')
            fmt = fmt.replace('HH', '%H').replace('mm', '%M').replace('ss', '%S')
            v = time.strftime(fmt)
        else:
            v = int(time.time())
        e.assign(n.result_var, v); return v

    def _ev_rand(self, n, e):
        mn = self.eval(n.min_expr, e); mx = self.eval(n.max_expr, e)
        if n.as_real:
            v = random.uniform(float(mn), float(mx))
        else:
            v = random.randint(int(mn), int(mx))
        e.assign(n.result_var, v); return v

    def _ev_b64(self, n, e):
        s = str(self.eval(n.source, e))
        if n.mode == 'enc': v = base64.b64encode(s.encode()).decode()
        else:
            try: v = base64.b64decode(s).decode()
            except: v = base64.b64decode(s)
        e.assign(n.result_var, v); return v

    def _ev_wait(self, n, e):
        ms = self.eval(n.ms_expr, e)
        time.sleep(float(ms) / 1000.0)

    def _ev_trace(self, n, e):
        self.trace_vars.add(n.var_name)

    # ── 容器 ─────────────────────────────────────────────
    def _ev_push(self, n, e):
        v = self.eval(n.value, e)
        arr = e.get(n.arr_name); arr.append(v); return arr

    def _ev_pop(self, n, e):
        arr = e.get(n.arr_name); v = arr.pop() if arr else None
        if n.result_var: e.assign(n.result_var, v)
        return v

    def _ev_mapset(self, n, e):
        m = e.get(n.map_name); m[self.eval(n.key, e)] = self.eval(n.value, e)

    def _ev_mapdel(self, n, e):
        m = e.get(n.map_name); del m[self.eval(n.key, e)]

    def _ev_maphas(self, n, e):
        m = e.get(n.map_name)
        k = self.eval(n.key, e)
        v = k in m
        e.assign(n.result_var, v)
        return v

    def _ev_mapget(self, n, e):
        m = e.get(n.map_name)
        k = self.eval(n.key, e)
        if k not in m: raise DKError('KeyError', f'键 "{k}" 不存在')
        return m[k]

    def _ev_arr_len(self, n, e):
        arr = e.get(n.arr_name)
        v = len(arr) if hasattr(arr, '__len__') else 0
        e.assign(n.result_var, v); return v

    def _ev_server(self, n, e):
        """启动 HTTP 服务器（纯 DK-Lang）"""
        import threading
        from .httpd import HttpServer as DkHttpServer, Response as DkResponse, Request as DkRequest
        import json as _json

        host = str(self.eval(n.host, e))
        port = int(self.eval(n.port, e))
        server = DkHttpServer(host, port)

        # 注册中间件
        interp_ref = self
        env_ref = e

        for mw_node in n.middlewares:
            def make_mw(handler_name):
                def mw_fn(req, next_handler):
                    req_data = _json.dumps({
                        'method': req.method, 'path': req.path,
                        'headers': dict(req.headers),
                        'query': dict(req.query),
                    }, ensure_ascii=False)
                    try:
                        result = interp_ref._call_dk_func(handler_name, req_data)
                        if result and str(result) != 'OK':
                            return DkResponse(401, {'error': str(result)})
                    except Exception as ex:
                        print(f'[Middleware] {handler_name}: {ex}')
                    return next_handler(req)
                return mw_fn
            server.use(make_mw(mw_node.handler_name))

        # 静态文件路径解析（相对于工作目录）
        import os as _os
        _cwd = _os.getcwd()
        
        # 注册静态文件
        for s_node in n.statics:
            dir_path = s_node.directory
            if not _os.path.isabs(dir_path):
                dir_path = _os.path.join(_cwd, dir_path)
            server.static(s_node.url_prefix, dir_path)

        # 注册路由
        for r_node in n.routes:
            def make_handler(handler_name):
                def handler_fn(req):
                    body_text = req.text() if req.body else ''
                    req_data = _json.dumps({
                        'method': req.method, 'path': req.path,
                        'headers': dict(req.headers),
                        'query': dict(req.query),
                        'params': dict(req.params),
                        'body': body_text,
                    }, ensure_ascii=False)
                    try:
                        result = interp_ref._call_dk_func(handler_name, req_data)
                        if result is None:
                            return DkResponse(204)
                        result_str = str(result) if not isinstance(result, str) else result
                        # 自动检测 Content-Type
                        stripped = result_str.strip() if result_str else ''
                        if stripped.startswith('<') or stripped.lower().startswith('<!doctype'):
                            ct = 'text/html; charset=utf-8'
                        elif stripped.startswith('{') or stripped.startswith('['):
                            ct = 'application/json; charset=utf-8'
                        else:
                            ct = 'text/plain; charset=utf-8'
                        return DkResponse(200, result_str, {'Content-Type': ct})
                    except Exception as ex:
                        import traceback; traceback.print_exc()
                        return DkResponse(500, {'error': str(ex)})
                return handler_fn

            server.router.add(r_node.method, r_node.path, make_handler(r_node.handler_name))

        print(f'[SERVER] 启动 http://{host}:{port}')
        server.start(blocking=True)

    def _call_dk_func(self, func_name, *args):
        """从 Python 调用 DK-Lang 函数"""
        fd = self.funcs.get(func_name)
        if fd is None:
            raise DKNameError(f'未定义的函数 "{func_name}"')
        call_args = [LiteralNode(value=str(a), dk_type=StrType()) for a in args]
        call_node = CallNode(name=func_name, arguments=call_args)
        old_env = self.env
        try:
            return self.eval(call_node, self.glob)
        except ReturnSignal as rs:
            return rs.value
        finally:
            self.env = old_env

    # ── 网络 ──────────────────────────────────────────────
    def _ev_http_get(self, n, e):
        self._check_perm('network')
        url = str(self.eval(n.url, e))
        try:
            import urllib.request
            req = urllib.request.Request(url)
            if n.headers:
                hdrs = self.eval(n.headers, e)
                if isinstance(hdrs, dict):
                    for k, v in hdrs.items(): req.add_header(str(k), str(v))
            with urllib.request.urlopen(req, timeout=10) as resp:
                v = resp.read().decode('utf-8')
        except Exception as ex: raise DKNetworkError(str(ex))
        e.assign(n.result_var, v); return v

    def _ev_http_post(self, n, e):
        self._check_perm('network')
        url = str(self.eval(n.url, e)); body = self.eval(n.body, e)
        try:
            import urllib.request
            data = json.dumps(body).encode() if isinstance(body, dict) else str(body).encode()
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header('Content-Type', 'application/json')
            with urllib.request.urlopen(req, timeout=10) as resp:
                v = resp.read().decode('utf-8')
        except Exception as ex: raise DKNetworkError(str(ex))
        e.assign(n.result_var, v); return v

    # ── 系统 ──────────────────────────────────────────────
    def _ev_exec(self, n, e):
        self._check_perm('system_exec')
        cmd = str(self.eval(n.cmd, e))
        try:
            import subprocess
            v = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8', errors='replace')
        except Exception as ex: v = str(ex)
        e.assign(n.result_var, v); return v

    def _ev_envget(self, n, e):
        v = os.environ.get(str(self.eval(n.name, e)), '')
        e.assign(n.result_var, v); return v

    def _ev_envset(self, n, e):
        os.environ[n.name] = str(self.eval(n.value, e))

    def _ev_sandbox(self, n, e):
        self.sandbox = (n.mode == 'on')

    def _ev_audit(self, n, e):
        code = str(self.eval(n.code, e))
        warnings = []
        for kw in ['rm -rf', 'format', 'DROP TABLE', 'shutdown']:
            if kw.lower() in code.lower():
                warnings.append(f'危险操作: {kw}')
        e.assign(n.result_var, '\n'.join(warnings) if warnings else '')

    # ── 异步 ──────────────────────────────────────────────
    def _ev_async(self, n, e):
        res = []
        def runner():
            ie = Interpreter(ctx=self.ctx); ie.funcs = dict(self.funcs); ie.ffi = dict(self.ffi)
            try: r = ie._ev_block(n.body, ie.env); res.append(r)
            except Exception as ex: res.append(ex)
        t = threading.Thread(target=runner, name=n.task_name, daemon=True)
        t.start(); e.define(n.task_name, t); self.glob.define(f'_task_{n.task_name}', t)
        return t

    def _ev_await(self, n, e):
        t = e.get(n.task_name)
        if t and isinstance(t, threading.Thread): t.join()

    # ── OOP ──────────────────────────────────────────────
    def _ev_class(self, n, e):
        self.classes[n.name] = n; e.define(n.name, n)

    def _ev_new(self, n, e):
        cls = self.classes.get(n.class_name)
        if not cls: raise DKNameError(f'未定义的类 "{n.class_name}"')
        obj = {}
        for pn, pt in cls.props:
            dv = DEFAULT_VALUES.get(type(pt), None)
            obj[pn] = dv
        obj['__class__'] = n.class_name
        # 构造函数参数
        args = [self.eval(a, e) for a in n.args]
        if args and cls.props:
            for (pn, _), av in zip(cls.props, args):
                obj[pn] = av
        e.define(n.obj_name, obj)
        # 绑定方法
        for mn, mparams, mret, mb in cls.methods:
            fd = FuncDefNode(name=f'{n.obj_name}.{mn}', params=mparams, return_type=mret, body=mb)
            self.funcs[fd.name] = fd
        return obj

    # ── 元编程 ────────────────────────────────────────────
    def _ev_eval(self, n, e):
        code = str(self.eval(n.code_expr, e))
        try:
            lexer = Lexer(code); tokens = lexer.tokenize()
            parser = Parser(tokens); ast = parser.parse()
            sub = Interpreter(ctx=self.ctx); sub.funcs = dict(self.funcs)
            sub.ffi = dict(self.ffi); sub.env = self.env
            return sub.execute(ast)
        except Exception as ex:
            raise DKError('EvalError', str(ex))

    # ── AI 原生 ──────────────────────────────────────────
    def _ev_ai_ask(self, n, e):
        self._check_perm('ai_call')
        prompt = str(self.eval(n.prompt, e))
        system = str(self.eval(n.system, e)) if n.system else None
        # 使用上下文中的 AI 回调
        if 'ai_ask' in self.ctx and callable(self.ctx['ai_ask']):
            v = self.ctx['ai_ask'](prompt=prompt, system=system)
        else:
            v = f'[AI_ASK] prompt="{prompt[:100]}..." (no AI backend configured)'
        e.assign(n.result_var, v); return v

    def _ev_ai_extract(self, n, e):
        self._check_perm('ai_call')
        src = str(self.eval(n.source, e))
        if 'ai_extract' in self.ctx:
            v = self.ctx['ai_extract'](extract_type=n.extract_type, text=src)
        else:
            v = f'[AI_EXTRACT type={n.extract_type}] from text ({len(src)} chars)'
        e.assign(n.result_var, v); return v

    def _ev_ai_summarize(self, n, e):
        self._check_perm('ai_call')
        src = str(self.eval(n.source, e)); mw = int(self.eval(n.max_words, e)) if n.max_words else 100
        if 'ai_summarize' in self.ctx:
            v = self.ctx['ai_summarize'](text=src, max_words=mw)
        else:
            v = f'[AI_SUMMARIZE max={mw}] from text ({len(src)} chars)'
        e.assign(n.result_var, v); return v

    def _ev_ai_classify(self, n, e):
        self._check_perm('ai_call')
        src = str(self.eval(n.source, e))
        if 'ai_classify' in self.ctx:
            v = self.ctx['ai_classify'](text=src, categories=n.categories)
        else:
            v = n.categories[0] if n.categories else 'unknown'
        e.assign(n.result_var, v); return v

    def _ev_ai_translate(self, n, e):
        self._check_perm('ai_call')
        src = str(self.eval(n.source, e))
        if 'ai_translate' in self.ctx:
            v = self.ctx['ai_translate'](text=src, target_lang=n.target_lang)
        else:
            v = f'[AI_TRANSLATE to={n.target_lang}] {src[:100]}'
        e.assign(n.result_var, v); return v

    def _ev_ctx(self, n, e):
        if 'get_context' in self.ctx:
            v = self.ctx['get_context'](n.scope)
        else:
            v = f'[CTX scope={n.scope}] (no context backend)'
        e.assign(n.result_var, v); return v

    def _ev_prompt(self, n, e):
        args = [self.eval(a, e) for a in n.args]
        if 'load_prompt' in self.ctx:
            v = self.ctx['load_prompt'](n.template_name, *args)
        else:
            v = f'[PROMPT template={n.template_name}]'
        e.assign(n.result_var, v); return v

    def _ev_ai_image(self, n, e):
        self._check_perm('ai_call')
        path = str(self.eval(n.image_path, e)); q = str(self.eval(n.question, e))
        if 'ai_image' in self.ctx:
            v = self.ctx['ai_image'](image_path=path, question=q)
        else:
            v = f'[AI_IMAGE path={path}] question="{q}"'
        e.assign(n.result_var, v); return v

    # ── Use/FFI ────────────────────────────────────────────
    def _handle_use(self, n):
        p = n.module_path
        if p.endswith('.dk'):
            try:
                with open(p, 'r', encoding='utf-8') as f: self._load_source(f.read())
            except Exception as ex: print(f'[USE] 加载失败: {p} — {ex}')

    def _handle_ffi_import(self, n):
        import sys
        if not self.ffi_loader:
            raise DKError('FFIError', 'FFI 加载器未初始化（请检查 dklang/ffi/__init__.py）')
        module = self.ffi_loader.load(n.lang, n.lib_name)
        alias = n.alias or (n.lib_name.split('.')[-1] if '.' in n.lib_name else n.lib_name)
        self.ffi[alias] = {'lang': n.lang, 'module': module, 'lib_name': n.lib_name}

    def _ffi_call(self, lang, module, method, args):
        if lang == 'python':
            if method:
                fn = getattr(module, method, None)
                if fn is None: raise DKError('FFIError', f'Python 模块没有方法 "{method}"')
                return fn(*args)
            elif callable(module): return module(*args)
        elif lang == 'cpp':
            if method and hasattr(module, method):
                return getattr(module, method)(*args)
        elif lang == 'java':
            if method and hasattr(module, method):
                return getattr(module, method)(*args)
        raise DKError('FFIError', f'不支持的 FFI 调用: {lang}.{method}')

    # ── 工具 ──────────────────────────────────────────────
    def _check_perm(self, perm):
        if self.sandbox and perm not in self.permits:
            raise DKPermError(f'未声明权限 "{perm}"，请在文件开头使用 PERMIT "{perm}" ;')

    def _truthy(self, v):
        if v is None: return False
        if isinstance(v, bool): return v
        if isinstance(v, (int, float)): return v != 0
        if isinstance(v, str): return len(v) > 0
        if isinstance(v, (list, dict, set, tuple)): return len(v) > 0
        return True
