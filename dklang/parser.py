"""DK-Lang 语法分析器。读取 DEVELOPER.md 获取完整语法规范。"""
from .lexer import Token, TK, OP_TO_STR, COMPARISON
from .ast_nodes import *


class ParseError(Exception):
    def __init__(self, msg, t: Token):
        super().__init__(f'语法错误({t.line}:{t.col}): {msg} (got {t.kind.name})')

class Parser:
    def __init__(self, tokens: list):
        self.tokens = tokens; self.pos = 0

    def _peek(self) -> Token: return self.tokens[self.pos]
    def _eat(self, *kinds) -> Token:
        t = self._peek()
        if kinds and t.kind not in kinds: raise ParseError(f'期望 {"|".join(k.name for k in kinds)}', t)
        self.pos += 1; return t
    def _match(self, *kinds) -> bool: return self._peek().kind in kinds
    def _eof(self) -> bool: return self._peek().kind == TK.EOF

    # ── 入口 ──────────────────────────────────────────────
    def parse(self) -> ProgramNode:
        # 第一遍：预扫描 FUNC 定义，收集参数数量
        saved_pos = self.pos
        while self.pos < len(self.tokens):
            t = self._peek()
            if t.kind == TK.EOF: break
            if t.kind == TK.KW_FUNC:
                self._eat(TK.KW_FUNC)
                fname = self._consume_name()
                buf = []
                while self._match(TK.PIPE):
                    self._eat(TK.PIPE)
                    if self._match(TK.LBRACE): break
                    nxt = self._peek()
                    if nxt.kind == TK.IDENT:
                        buf.append(('ident', self._eat(TK.IDENT).value))
                    elif self._is_type(nxt.kind):
                        buf.append(('type', self._parse_type()))
                    else:
                        break
                # 最后一个 type 是返回类型
                last_type = -1
                for i in range(len(buf)-1, -1, -1):
                    if buf[i][0] == 'type': last_type = i; break
                if last_type > 0:
                    self._func_param_counts[fname] = (last_type + 1) // 2
                else:
                    self._func_param_counts[fname] = 0
                # 跳过函数体：简单深度计数
                depth = 0
                while self.pos < len(self.tokens):
                    tk = self._peek()
                    if tk.kind == TK.EOF: break
                    if tk.kind == TK.LBRACE: depth += 1
                    elif tk.kind == TK.RBRACE:
                        depth -= 1
                        if depth == 0:
                            self._eat(TK.RBRACE)
                            break
                    self.pos += 1
            elif t.kind in (TK.KW_SERVER, TK.SEMI):
                self._eat(t.kind)
            else:
                if self.pos + 1 < len(self.tokens):
                    self.pos += 1
                else:
                    break
        self.pos = saved_pos

        # 第二遍：正常解析
        decls = []
        while not self._eof():
            s = self._parse_top_level()
            if s is not None: decls.append(s)
        return ProgramNode(declarations=decls)

    def _parse_top_level(self) -> ASTNode:
        t = self._peek()
        if t.kind == TK.SEMI: self._eat(TK.SEMI); return None
        if t.kind == TK.RBRACE: return None
        if t.kind == TK.LBRACE: return self._parse_block()
        return self._parse_instruction()

    # ── 指令分发 ──────────────────────────────────────────
    def _parse_instruction(self) -> ASTNode:
        t = self._peek()
        dispatch = {
            TK.KW_VAR: self._p_var, TK.KW_SET: self._p_set, TK.KW_CONST: self._p_const,
            TK.KW_PRINT: self._p_print, TK.KW_IF: self._p_if, TK.KW_LOOP: self._p_loop,
            TK.KW_WHILE: self._p_while, TK.KW_SWITCH: self._p_switch,
            TK.KW_FUNC: self._p_func, TK.KW_CALL: self._p_call_stmt, TK.KW_RET: self._p_ret,
            TK.KW_ARR: self._p_arr, TK.KW_BREAK: self._p_break, TK.KW_NEXT: self._p_next,
            TK.KW_USE: self._p_use, TK.KW_TRY: self._p_try, TK.KW_THROW: self._p_throw,
            TK.KW_TYPE: self._p_type_alias, TK.KW_LOG: self._p_log, TK.KW_TIME: self._p_time,
            TK.KW_RAND: self._p_rand, TK.KW_AI_ASK: self._p_ai_ask, TK.KW_AI_EXTRACT: self._p_ai_extract,
            TK.KW_AI_SUMMARIZE: self._p_ai_summarize, TK.KW_AI_CLASSIFY: self._p_ai_classify,
            TK.KW_AI_TRANSLATE: self._p_ai_translate, TK.KW_CTX: self._p_ctx, TK.KW_PROMPT: self._p_prompt,
            TK.KW_AI_IMAGE: self._p_ai_image, TK.KW_FILE_READ: self._p_file_read,
            TK.KW_FILE_WRITE: self._p_file_write, TK.KW_FILE_EXIST: self._p_file_exist,
            TK.KW_WAIT: self._p_wait, TK.KW_HTTP_GET: self._p_http_get, TK.KW_HTTP_POST: self._p_http_post,
            TK.KW_EXEC: self._p_exec, TK.KW_ENV_GET: self._p_env_get, TK.KW_ENV_SET: self._p_env_set,
            TK.KW_ASYNC: self._p_async, TK.KW_AWAIT: self._p_await,
            TK.KW_GLOBAL: self._p_global, TK.KW_LOCAL: self._p_local,
            TK.KW_PUSH: self._p_push, TK.KW_POP: self._p_pop,
            TK.KW_MAP_SET: self._p_map_set, TK.KW_MAP_DEL: self._p_map_del,
            TK.KW_MAP_HAS: self._p_map_has,
            TK.KW_SET_ADD: self._p_set_add, TK.KW_SET_HAS: self._p_set_has,
            TK.KW_B64ENC: self._p_b64, TK.KW_B64DEC: self._p_b64d,
            TK.KW_STR_JOIN: self._p_str_join, TK.KW_STR_CUT: self._p_str_cut,
            TK.KW_STR_LEN: self._p_str_len, TK.KW_STR_FIND: self._p_str_find, TK.KW_STR_REPL: self._p_str_repl,
            TK.KW_MACRO: self._p_macro, TK.KW_EVAL: self._p_eval, TK.KW_ALIAS: self._p_alias,
            TK.KW_TRACE: self._p_trace, TK.KW_BREAK: self._p_break, TK.KW_NEXT: self._p_next,
            TK.KW_FROM: self._p_ffi_import, TK.KW_VERSION: self._p_version, TK.KW_PERMIT: self._p_permit,
            TK.KW_SANDBOX: self._p_sandbox, TK.KW_AUDIT: self._p_audit,
            TK.KW_EXIT: self._p_exit, TK.KW_CLASS: self._p_class, TK.KW_NEW: self._p_new,
            TK.KW_THREAD: self._p_thread, TK.KW_JOIN: self._p_join,
            TK.KW_ARR_LEN: self._p_arr_len,
            TK.KW_SERVER: self._p_server,
        }
        if t.kind not in dispatch:
            raise ParseError(f'非法的指令起始', t)
        return dispatch[t.kind]()

    # ── L1: 基础指令 ─────────────────────────────────────
    def _p_var(self):
        self._eat(TK.KW_VAR); n = self._consume_name(); self._eat(TK.PIPE)
        vt = self._parse_type(); self._eat(TK.SEMI); return VarDeclNode(name=n, var_type=vt)

    def _p_set(self):
        self._eat(TK.KW_SET); n = self._consume_name(); self._eat(TK.PIPE)
        v = self._parse_value(); self._eat(TK.SEMI); return AssignNode(name=n, value=v)

    def _p_const(self):
        self._eat(TK.KW_CONST); n = self._consume_name(); self._eat(TK.PIPE)
        vt = self._parse_type(); self._eat(TK.PIPE); v = self._parse_value()
        self._eat(TK.SEMI); return ConstDeclNode(name=n, const_type=vt, value=v)

    def _p_print(self):
        self._eat(TK.KW_PRINT); args = [self._parse_value()]
        while self._match(TK.PIPE): self._eat(TK.PIPE); args.append(self._parse_value())
        self._eat(TK.SEMI); return ExprStmtNode(expr=CallNode(name='print', arguments=args))

    # ── L2: 流程控制 ─────────────────────────────────────
    def _p_if(self):
        self._eat(TK.KW_IF)
        op = self._parse_comp_op_str(); self._eat(TK.PIPE)
        left = self._parse_value(); self._eat(TK.PIPE); right = self._parse_value(); self._eat(TK.PIPE)
        cond = BinaryOpNode(op=op, left=left, right=right)
        tb = self._parse_block()
        eb = None
        if self._match(TK.PIPE): self._eat(TK.PIPE); eb = self._parse_block()
        self._eat(TK.SEMI)
        return IfNode(condition=cond, then_block=tb, else_block=eb)

    def _p_loop(self):
        self._eat(TK.KW_LOOP)
        if self._peek().kind in COMPARISON:  # while 模式
            op = self._parse_comp_op_str(); self._eat(TK.PIPE)
            l = self._parse_value(); self._eat(TK.PIPE); r = self._parse_value(); self._eat(TK.PIPE)
            cond = BinaryOpNode(op=op, left=l, right=r)
            b = self._parse_block(); self._eat(TK.SEMI)
            return WhileNode(condition=cond, body=b)
        else:  # 计数模式
            vn = self._consume_name(); self._eat(TK.PIPE)
            st = self._parse_value(); self._eat(TK.PIPE)
            en = self._parse_value(); self._eat(TK.PIPE)
            sp = self._parse_value(); self._eat(TK.PIPE)
            init = AssignNode(name=vn, value=st)
            cond = BinaryOpNode(op='<=', left=VarRefNode(name=vn), right=en)
            step = AssignNode(name=vn, value=BinaryOpNode(op='add', left=VarRefNode(name=vn), right=sp))
            b = self._parse_block(); self._eat(TK.SEMI)
            return LoopNode(init=init, condition=cond, step=step, body=b)

    def _p_while(self):
        self._eat(TK.KW_WHILE)
        op = self._parse_comp_op_str(); self._eat(TK.PIPE)
        l = self._parse_value(); self._eat(TK.PIPE); r = self._parse_value(); self._eat(TK.PIPE)
        cond = BinaryOpNode(op=op, left=l, right=r)
        b = self._parse_block(); self._eat(TK.SEMI)
        return WhileNode(condition=cond, body=b)

    def _p_switch(self):
        self._eat(TK.KW_SWITCH); e = self._parse_value(); self._eat(TK.PIPE); self._eat(TK.LBRACE)
        cases = []; default = None
        while not self._match(TK.RBRACE):
            if self._match(TK.KW_DEFAULT):
                self._eat(TK.KW_DEFAULT); self._eat(TK.PIPE); default = self._parse_block()
                if self._match(TK.SEMI): self._eat(TK.SEMI)
                break
            self._eat(TK.KW_CASE); v = self._parse_value(); self._eat(TK.PIPE); b = self._parse_block()
            cases.append((v, b))
        self._eat(TK.RBRACE); self._eat(TK.SEMI)
        return SwitchNode(expr=e, cases=cases, default=default)

    def _p_break(self): self._eat(TK.KW_BREAK); self._eat(TK.SEMI); return BreakNode()
    def _p_next(self): self._eat(TK.KW_NEXT); self._eat(TK.SEMI); return NextNode()

    # ── L3: 函数与容器 ───────────────────────────────────
    def _p_func(self):
        self._eat(TK.KW_FUNC); name = self._consume_name()
        fields = []
        while self._match(TK.PIPE):
            self._eat(TK.PIPE)
            if self._match(TK.LBRACE): break
            t = self._peek()
            if t.kind == TK.IDENT:
                fields.append(('ident', self._eat(TK.IDENT).value))
            elif self._is_type(t.kind):
                fields.append(('type', self._parse_type()))
            else:
                raise ParseError(f'FUNC 字段期望标识符或类型', t)
        # 最后一个 type 是返回类型
        ret_type = NilType(); params = []
        last = -1
        for i in range(len(fields)-1, -1, -1):
            if fields[i][0] == 'type': last = i; break
        if last >= 0:
            ret_type = fields[last][1]
            i = 0
            while i < last:
                if i+1 < last and fields[i][0]=='ident' and fields[i+1][0]=='type':
                    params.append((fields[i][1], fields[i+1][1])); i += 2
                else: raise ParseError('FUNC 参数必须成对', self._peek())
        body = self._parse_block(); self._eat(TK.SEMI)
        return FuncDefNode(name=name, params=params, return_type=ret_type, body=body)

    def _p_call_stmt(self):
        c = self._parse_call_expr(); self._eat(TK.SEMI); return ExprStmtNode(expr=c)

    # ── 调用表达式，根据函数签名确定参数数 ──
    _func_param_counts = {}  # 函数名 → 参数数量
    _call_depth = 0

    def _parse_call_expr(self):
        self._eat(TK.KW_CALL); n = self._consume_name()
        self._call_depth += 1
        args = []
        expected = self._func_param_counts.get(n, -1)
        while self._match(TK.PIPE):
            # 已知参数数量且已达上限，停止消费（适用于所有深度）
            if expected >= 0 and len(args) >= expected:
                break
            self._eat(TK.PIPE)
            if self._peek().kind in (TK.SEMI, TK.EOF, TK.RBRACE):
                break
            args.append(self._parse_value())
        self._call_depth -= 1
        return CallNode(name=n, arguments=args)

    def _p_ret(self):
        self._eat(TK.KW_RET)
        if self._match(TK.SEMI): self._eat(TK.SEMI); return ReturnNode()
        v = self._parse_value(); self._eat(TK.SEMI); return ReturnNode(expr=v)

    def _p_arr(self):
        self._eat(TK.KW_ARR); n = self._consume_name(); self._eat(TK.PIPE)
        et = self._parse_type()
        elems = []
        while self._match(TK.PIPE):
            self._eat(TK.PIPE)
            if self._match(TK.SEMI): break
            elems.append(self._parse_value())
        self._eat(TK.SEMI)
        ie = ListLiteralNode(elements=elems) if elems else None
        return VarDeclNode(name=n, var_type=ListType(et), init_expr=ie)

    def _p_push(self):
        self._eat(TK.KW_PUSH); n = self._consume_name(); self._eat(TK.PIPE)
        v = self._parse_value(); self._eat(TK.SEMI); return ArrayPushNode(arr_name=n, value=v)

    def _p_pop(self):
        self._eat(TK.KW_POP); n = self._consume_name()
        rv = None
        if self._match(TK.PIPE): self._eat(TK.PIPE); rv = self._consume_name()
        self._eat(TK.SEMI); return ArrayPopNode(arr_name=n, result_var=rv)

    def _p_map_set(self):
        self._eat(TK.KW_MAP_SET); n = self._consume_name(); self._eat(TK.PIPE)
        k = self._parse_value(); self._eat(TK.PIPE); v = self._parse_value()
        self._eat(TK.SEMI); return MapSetNode(map_name=n, key=k, value=v)

    def _p_map_del(self):
        self._eat(TK.KW_MAP_DEL); n = self._consume_name(); self._eat(TK.PIPE)
        k = self._parse_value(); self._eat(TK.SEMI); return MapDelNode(map_name=n, key=k)

    def _p_map_has(self):
        self._eat(TK.KW_MAP_HAS); rv = self._consume_name(); self._eat(TK.PIPE)
        n = self._consume_name(); self._eat(TK.PIPE)
        k = self._parse_value(); self._eat(TK.SEMI)
        return MapHasNode(result_var=rv, map_name=n, key=k)

    def _p_set_add(self):
        self._eat(TK.KW_SET_ADD); n = self._consume_name(); self._eat(TK.PIPE)
        v = self._parse_value(); self._eat(TK.SEMI)
        return ExprStmtNode(expr=CallNode(name='_set_add', arguments=[VarRefNode(name=n), v]))

    def _p_set_has(self):
        self._eat(TK.KW_SET_HAS); rv = self._consume_name(); self._eat(TK.PIPE)
        n = self._consume_name(); self._eat(TK.PIPE)
        v = self._parse_value(); self._eat(TK.SEMI)
        return AssignNode(name=rv, value=BinaryOpNode(op='set_has', left=VarRefNode(name=n), right=v))

    def _p_arr_len(self):
        self._eat(TK.KW_ARR_LEN); rv = self._consume_name(); self._eat(TK.PIPE)
        n = self._consume_name(); self._eat(TK.SEMI)
        return ArrLenNode(result_var=rv, arr_name=n)

    def _p_server(self):
        self._eat(TK.KW_SERVER)
        host = self._parse_value(); self._eat(TK.PIPE)
        port = self._parse_value(); self._eat(TK.PIPE)
        self._eat(TK.LBRACE)
        routes = []; middlewares = []; statics = []
        while not self._match(TK.RBRACE):
            if self._match(TK.KW_ROUTE):
                routes.append(self._p_route_inner())
            elif self._match(TK.KW_MIDDLEWARE):
                middlewares.append(self._p_middleware_inner())
            elif self._match(TK.KW_STATIC):
                statics.append(self._p_static_inner())
            elif self._match(TK.SEMI):
                self._eat(TK.SEMI)
            else:
                raise ParseError('SERVER 块内期望 ROUTE/MIDDLEWARE/STATIC', self._peek())
        self._eat(TK.RBRACE); self._eat(TK.SEMI)
        return ServerNode(host=host, port=port, routes=routes, middlewares=middlewares, statics=statics)

    def _p_route_inner(self):
        self._eat(TK.KW_ROUTE)
        method = self._eat(TK.LIT_STR).value; self._eat(TK.PIPE)
        path = self._eat(TK.LIT_STR).value; self._eat(TK.PIPE)
        handler = self._consume_name(); self._eat(TK.SEMI)
        return RouteNode(method=method.upper(), path=path, handler_name=handler)

    def _p_middleware_inner(self):
        self._eat(TK.KW_MIDDLEWARE)
        handler = self._consume_name(); self._eat(TK.SEMI)
        return MiddlewareNode(handler_name=handler)

    def _p_static_inner(self):
        self._eat(TK.KW_STATIC)
        prefix = self._eat(TK.LIT_STR).value; self._eat(TK.PIPE)
        directory = self._eat(TK.LIT_STR).value; self._eat(TK.SEMI)
        return StaticNode(url_prefix=prefix, directory=directory)

    # ── L4: 字符串与逻辑 ─────────────────────────────────
    def _p_str_join(self):
        self._eat(TK.KW_STR_JOIN); rv = self._consume_name(); self._eat(TK.PIPE)
        sep = self._parse_value(); parts = []
        while self._match(TK.PIPE): self._eat(TK.PIPE); parts.append(self._parse_value())
        self._eat(TK.SEMI)
        return AssignNode(name=rv, value=BinaryOpNode(op='str_join', left=sep, right=ListLiteralNode(elements=parts)))

    def _p_str_cut(self):
        self._eat(TK.KW_STR_CUT); rv = self._consume_name(); self._eat(TK.PIPE)
        src = self._parse_value(); self._eat(TK.PIPE)
        start = self._parse_value(); self._eat(TK.PIPE)
        length = self._parse_value(); self._eat(TK.SEMI)
        return AssignNode(name=rv, value=CallNode(name='_str_cut', arguments=[src, start, length]))

    def _p_str_len(self):
        self._eat(TK.KW_STR_LEN); rv = self._consume_name(); self._eat(TK.PIPE)
        src = self._parse_value(); self._eat(TK.SEMI)
        return AssignNode(name=rv, value=UnaryOpNode(op='str_len', operand=src))

    def _p_str_find(self):
        self._eat(TK.KW_STR_FIND); rv = self._consume_name(); self._eat(TK.PIPE)
        src = self._parse_value(); self._eat(TK.PIPE)
        sub = self._parse_value(); self._eat(TK.SEMI)
        return AssignNode(name=rv, value=BinaryOpNode(op='str_find', left=src, right=sub))

    def _p_str_repl(self):
        self._eat(TK.KW_STR_REPL); rv = self._consume_name(); self._eat(TK.PIPE)
        src = self._parse_value(); self._eat(TK.PIPE)
        old = self._parse_value(); self._eat(TK.PIPE)
        new = self._parse_value(); self._eat(TK.SEMI)
        return AssignNode(name=rv, value=CallNode(name='_str_repl', arguments=[src, old, new]))

    # ── 字符串操作 表达式形式（用于 SET/RET/CALL/PRINT 等值上下文）───
    def _parse_str_join_expr(self):
        self._eat(TK.KW_STR_JOIN)
        sep = self._parse_value(); parts = []
        while self._match(TK.PIPE):
            self._eat(TK.PIPE); parts.append(self._parse_value())
        return CallNode(name='_str_join', arguments=[sep] + parts)

    def _parse_str_cut_expr(self):
        self._eat(TK.KW_STR_CUT); src = self._parse_value(); self._eat(TK.PIPE)
        start = self._parse_value(); self._eat(TK.PIPE); length = self._parse_value()
        return CallNode(name='_str_cut', arguments=[src, start, length])

    def _parse_str_len_expr(self):
        self._eat(TK.KW_STR_LEN); src = self._parse_value()
        return UnaryOpNode(op='str_len', operand=src)

    def _parse_str_find_expr(self):
        self._eat(TK.KW_STR_FIND); src = self._parse_value(); self._eat(TK.PIPE)
        sub = self._parse_value()
        return BinaryOpNode(op='str_find', left=src, right=sub)

    def _parse_str_repl_expr(self):
        self._eat(TK.KW_STR_REPL); src = self._parse_value(); self._eat(TK.PIPE)
        old = self._parse_value(); self._eat(TK.PIPE); new = self._parse_value()
        return CallNode(name='_str_repl', arguments=[src, old, new])

    def _parse_arr_len_expr(self):
        self._eat(TK.KW_ARR_LEN); n = self._consume_name()
        return CallNode(name='_arr_len', arguments=[VarRefNode(name=n)])

    # ── L5: 工程化 ───────────────────────────────────────
    def _p_ffi_import(self):
        """from "python" import "module" as alias ;"""
        self._eat(TK.KW_FROM)
        lang = self._eat(TK.LIT_STR).value
        self._eat(TK.KW_IMPORT)
        lib = self._eat(TK.LIT_STR).value
        alias = None
        if self._match(TK.KW_AS):
            self._eat(TK.KW_AS)
            alias = self._consume_name()
        self._eat(TK.SEMI)
        return FfiImportNode(lang=lang, lib_name=lib, alias=alias)


    def _p_use(self):
        self._eat(TK.KW_USE);
        if self._peek().kind == TK.LIT_STR:
            p = self._eat(TK.LIT_STR).value; self._eat(TK.SEMI); return ImportNode(module_path=p)
        raise ParseError('USE 需要字符串参数', self._peek())

    def _p_try(self):
        self._eat(TK.KW_TRY); self._eat(TK.PIPE); tb = self._parse_block()
        catches = []
        while self._match(TK.KW_CATCH):
            self._eat(TK.KW_CATCH); et = self._eat(TK.LIT_STR).value; self._eat(TK.PIPE)
            cb = self._parse_block(); catches.append((et, cb))
        self._eat(TK.SEMI); return TryNode(try_block=tb, catches=catches)

    def _p_throw(self):
        self._eat(TK.KW_THROW); et = self._eat(TK.LIT_STR).value
        msg = None
        if self._match(TK.PIPE): self._eat(TK.PIPE); msg = self._parse_value()
        self._eat(TK.SEMI); return ThrowNode(error_type=et, message=msg or LiteralNode(value='', dk_type=StrType()))

    def _p_type_alias(self):
        self._eat(TK.KW_TYPE); a = self._consume_name(); self._eat(TK.PIPE)
        ot = self._parse_type(); self._eat(TK.SEMI); return TypeAliasNode(alias=a, original=ot)

    def _p_file_read(self):
        self._eat(TK.KW_FILE_READ); rv = self._consume_name(); self._eat(TK.PIPE)
        p = self._parse_value(); self._eat(TK.SEMI); return FileReadNode(result_var=rv, path=p)

    def _p_file_write(self):
        self._eat(TK.KW_FILE_WRITE); p = self._parse_value(); self._eat(TK.PIPE)
        c = self._parse_value(); self._eat(TK.SEMI); return FileWriteNode(path=p, content=c)

    def _p_file_exist(self):
        self._eat(TK.KW_FILE_EXIST); rv = self._consume_name(); self._eat(TK.PIPE)
        p = self._parse_value(); self._eat(TK.SEMI); return FileExistNode(result_var=rv, path=p)

    # ── L6: 元编程 ───────────────────────────────────────
    def _p_macro(self):
        self._eat(TK.KW_MACRO); n = self._consume_name()
        self._eat(TK.LPAREN)
        params = []
        if not self._match(TK.RPAREN):
            params.append(self._consume_name())
            while self._match(TK.COMMA): self._eat(TK.COMMA); params.append(self._consume_name())
        self._eat(TK.RPAREN); self._eat(TK.PIPE)
        body = ''
        self._eat(TK.LBRACE)
        depth = 1
        while depth > 0 and not self._eof():
            t = self._peek()
            if t.kind == TK.LBRACE: depth += 1
            elif t.kind == TK.RBRACE: depth -= 1
            if depth > 0:
                body += t.value if t.value else ('|' if t.kind == TK.PIPE else ';' if t.kind == TK.SEMI else '{' if t.kind == TK.LBRACE else '}' if t.kind == TK.RBRACE else '')
            self._eat(t.kind)
        self._eat(TK.SEMI); return MacroNode(name=n, params=params, body=body)

    def _p_eval(self):
        self._eat(TK.KW_EVAL); c = self._parse_value(); self._eat(TK.SEMI); return EvalNode(code_expr=c)

    def _p_alias(self):
        self._eat(TK.KW_ALIAS); a = self._consume_name(); self._eat(TK.PIPE)
        body = ''
        self._eat(TK.LBRACE)
        depth = 1
        while depth > 0 and not self._eof():
            t = self._peek()
            if t.kind == TK.LBRACE: depth += 1
            elif t.kind == TK.RBRACE: depth -= 1
            if depth > 0: body += self._token_raw(t)
            self._eat(t.kind)
        self._eat(TK.SEMI); return AliasNode(alias_name=a, target_block=body)

    # ── L7: AI 原生 ──────────────────────────────────────
    def _p_ai_ask(self):
        self._eat(TK.KW_AI_ASK); rv = self._consume_name(); self._eat(TK.PIPE)
        p = self._parse_value()
        s = None
        if self._match(TK.PIPE): self._eat(TK.PIPE); s = self._parse_value()
        self._eat(TK.SEMI); return AiAskNode(result_var=rv, prompt=p, system=s)

    def _p_ai_extract(self):
        self._eat(TK.KW_AI_EXTRACT); rv = self._consume_name(); self._eat(TK.PIPE)
        et = self._eat(TK.LIT_STR).value; self._eat(TK.PIPE)
        src = self._parse_value(); self._eat(TK.SEMI)
        return AiExtractNode(result_var=rv, extract_type=et, source=src)

    def _p_ai_summarize(self):
        self._eat(TK.KW_AI_SUMMARIZE); rv = self._consume_name(); self._eat(TK.PIPE)
        src = self._parse_value()
        mw = None
        if self._match(TK.PIPE): self._eat(TK.PIPE); mw = self._parse_value()
        self._eat(TK.SEMI); return AiSummarizeNode(result_var=rv, source=src, max_words=mw)

    def _p_ai_classify(self):
        self._eat(TK.KW_AI_CLASSIFY); rv = self._consume_name(); self._eat(TK.PIPE)
        src = self._parse_value()
        cats = []
        while self._match(TK.PIPE): self._eat(TK.PIPE); cats.append(self._eat(TK.LIT_STR).value)
        self._eat(TK.SEMI); return AiClassifyNode(result_var=rv, source=src, categories=cats)

    def _p_ai_translate(self):
        self._eat(TK.KW_AI_TRANSLATE); rv = self._consume_name(); self._eat(TK.PIPE)
        src = self._parse_value(); self._eat(TK.PIPE)
        tl = self._eat(TK.LIT_STR).value; self._eat(TK.SEMI)
        return AiTranslateNode(result_var=rv, source=src, target_lang=tl)

    def _p_ctx(self):
        self._eat(TK.KW_CTX); rv = self._consume_name(); self._eat(TK.PIPE)
        scope = self._eat(TK.LIT_STR).value; self._eat(TK.SEMI)
        return CtxNode(result_var=rv, scope=scope)

    def _p_prompt(self):
        self._eat(TK.KW_PROMPT); rv = self._consume_name(); self._eat(TK.PIPE)
        tn = self._eat(TK.LIT_STR).value
        args = []
        while self._match(TK.PIPE): self._eat(TK.PIPE); args.append(self._parse_value())
        self._eat(TK.SEMI); return PromptNode(result_var=rv, template_name=tn, args=args)

    def _p_ai_image(self):
        self._eat(TK.KW_AI_IMAGE); rv = self._consume_name(); self._eat(TK.PIPE)
        ip = self._parse_value(); self._eat(TK.PIPE)
        q = self._parse_value(); self._eat(TK.SEMI)
        return AiImageNode(result_var=rv, image_path=ip, question=q)

    # ── L8-L13: 调试、异步、网络、安全等 ──────────────────
    def _p_log(self):
        self._eat(TK.KW_LOG); lv = self._eat(TK.LIT_STR).value; self._eat(TK.PIPE)
        parts = [self._parse_value()]
        while self._match(TK.PIPE): self._eat(TK.PIPE); parts.append(self._parse_value())
        self._eat(TK.SEMI); return LogNode(level=lv, message_parts=parts)

    def _p_time(self):
        self._eat(TK.KW_TIME); rv = self._consume_name(); self._eat(TK.PIPE)
        fmt = self._eat(TK.LIT_STR).value; self._eat(TK.SEMI); return TimeNode(result_var=rv, fmt=fmt)

    def _p_rand(self):
        self._eat(TK.KW_RAND); rv = self._consume_name(); self._eat(TK.PIPE)
        mn = self._parse_value(); self._eat(TK.PIPE); mx = self._parse_value()
        ar = False
        if self._match(TK.PIPE):
            self._eat(TK.PIPE)
            if self._match(TK.LIT_STR) and self._peek().value == 'real': self._eat(TK.LIT_STR); ar = True
        self._eat(TK.SEMI); return RandNode(result_var=rv, min_expr=mn, max_expr=mx, as_real=ar)

    def _p_b64(self):
        self._eat(TK.KW_B64ENC); rv = self._consume_name(); self._eat(TK.PIPE)
        src = self._parse_value(); self._eat(TK.SEMI)
        return Base64Node(result_var=rv, source=src, mode='enc')

    def _p_b64d(self):
        self._eat(TK.KW_B64DEC); rv = self._consume_name(); self._eat(TK.PIPE)
        src = self._parse_value(); self._eat(TK.SEMI)
        return Base64Node(result_var=rv, source=src, mode='dec')

    def _p_trace(self):
        self._eat(TK.KW_TRACE); n = self._consume_name(); self._eat(TK.SEMI); return TraceNode(var_name=n)

    def _p_wait(self):
        self._eat(TK.KW_WAIT); ms = self._parse_value(); self._eat(TK.SEMI); return WaitNode(ms_expr=ms)

    def _p_http_get(self):
        self._eat(TK.KW_HTTP_GET); rv = self._consume_name(); self._eat(TK.PIPE)
        url = self._parse_value()
        h = None
        if self._match(TK.PIPE): self._eat(TK.PIPE); h = self._parse_value()
        self._eat(TK.SEMI); return HttpGetNode(result_var=rv, url=url, headers=h)

    def _p_http_post(self):
        self._eat(TK.KW_HTTP_POST); rv = self._consume_name(); self._eat(TK.PIPE)
        url = self._parse_value(); self._eat(TK.PIPE)
        body = self._parse_value()
        h = None
        if self._match(TK.PIPE): self._eat(TK.PIPE); h = self._parse_value()
        self._eat(TK.SEMI); return HttpPostNode(result_var=rv, url=url, body=body, headers=h)

    def _p_exec(self):
        self._eat(TK.KW_EXEC); rv = self._consume_name(); self._eat(TK.PIPE)
        cmd = self._parse_value(); self._eat(TK.SEMI); return ExecNode(result_var=rv, cmd=cmd)

    def _p_env_get(self):
        self._eat(TK.KW_ENV_GET); rv = self._consume_name(); self._eat(TK.PIPE)
        n = self._parse_value(); self._eat(TK.SEMI); return EnvGetNode(result_var=rv, name=n)

    def _p_env_set(self):
        self._eat(TK.KW_ENV_SET); n = self._eat(TK.LIT_STR).value; self._eat(TK.PIPE)
        v = self._parse_value(); self._eat(TK.SEMI); return EnvSetNode(name=n, value=v)

    def _p_async(self):
        self._eat(TK.KW_ASYNC); tn = self._consume_name(); self._eat(TK.PIPE)
        self._eat(TK.TYPE_TASK) if self._match(TK.TYPE_TASK) else None; self._eat(TK.PIPE)
        b = self._parse_block(); self._eat(TK.SEMI); return AsyncNode(task_name=tn, body=b)

    def _p_await(self):
        self._eat(TK.KW_AWAIT); tn = self._consume_name(); self._eat(TK.SEMI); return AwaitNode(task_name=tn)

    def _p_thread(self):
        self._eat(TK.KW_THREAD); tn = self._consume_name(); self._eat(TK.PIPE)
        b = self._parse_block(); self._eat(TK.SEMI)
        return ExprStmtNode(expr=CallNode(name='_thread', arguments=[LiteralNode(value=tn, dk_type=StrType()), b]))

    def _p_join(self):
        self._eat(TK.KW_JOIN); tn = self._consume_name(); self._eat(TK.SEMI)
        return ExprStmtNode(expr=CallNode(name='_join', arguments=[LiteralNode(value=tn, dk_type=StrType())]))

    def _p_global(self):
        self._eat(TK.KW_GLOBAL); n = self._consume_name(); self._eat(TK.PIPE)
        vt = self._parse_type(); self._eat(TK.SEMI); return VarDeclNode(name=n, var_type=vt)

    def _p_local(self):
        self._eat(TK.KW_LOCAL); n = self._consume_name(); self._eat(TK.PIPE)
        vt = self._parse_type(); self._eat(TK.SEMI); return VarDeclNode(name=n, var_type=vt)

    def _p_version(self):
        self._eat(TK.KW_VERSION); v = self._eat(TK.LIT_STR).value; self._eat(TK.SEMI)
        return VersionNode(version_str=v)

    def _p_permit(self):
        self._eat(TK.KW_PERMIT); p = self._eat(TK.LIT_STR).value; self._eat(TK.SEMI)
        return PermitNode(permission=p)

    def _p_sandbox(self):
        self._eat(TK.KW_SANDBOX); m = self._eat(TK.LIT_STR).value; self._eat(TK.SEMI)
        return SandboxNode(mode=m)

    def _p_audit(self):
        self._eat(TK.KW_AUDIT); rv = self._consume_name(); self._eat(TK.PIPE)
        c = self._parse_value(); self._eat(TK.SEMI); return AuditNode(result_var=rv, code=c)

    def _p_exit(self):
        self._eat(TK.KW_EXIT); self._eat(TK.SEMI)
        return ExprStmtNode(expr=CallNode(name='_exit', arguments=[]))

    def _p_class(self):
        self._eat(TK.KW_CLASS); cname = self._consume_name()
        parent = None
        if self._match(TK.PIPE): self._eat(TK.PIPE)
        if self._match(TK.KW_EXTENDS):
            self._eat(TK.KW_EXTENDS); parent = self._consume_name(); self._eat(TK.PIPE)
        self._eat(TK.LBRACE)
        props = []; methods = []
        while not self._match(TK.RBRACE):
            if self._match(TK.KW_PROP):
                self._eat(TK.KW_PROP); pn = self._consume_name(); self._eat(TK.PIPE)
                pt = self._parse_type(); self._eat(TK.SEMI); props.append((pn, pt))
            elif self._match(TK.KW_METHOD):
                self._eat(TK.KW_METHOD); mn = self._consume_name()
                # 解析方法参数
                mfields = []
                while self._match(TK.PIPE):
                    self._eat(TK.PIPE)
                    if self._match(TK.LBRACE): break
                    t = self._peek()
                    if t.kind == TK.IDENT: mfields.append(('ident', self._eat(TK.IDENT).value))
                    elif self._is_type(t.kind): mfields.append(('type', self._parse_type()))
                    else: break
                mret = NilType(); mparams = []
                last = -1
                for i in range(len(mfields)-1, -1, -1):
                    if mfields[i][0] == 'type': last = i; break
                if last >= 0:
                    mret = mfields[last][1]
                    i = 0
                    while i < last:
                        if i+1 < last and mfields[i][0]=='ident' and mfields[i+1][0]=='type':
                            mparams.append((mfields[i][1], mfields[i+1][1])); i += 2
                        else: i += 1
                mb = self._parse_block(); self._eat(TK.SEMI)
                methods.append((mn, mparams, mret, mb))
            else: self._eat(TK.SEMI)
        self._eat(TK.RBRACE); self._eat(TK.SEMI)
        return ClassDefNode(name=cname, parent=parent, props=props, methods=methods)

    def _p_new(self):
        self._eat(TK.KW_NEW); on = self._consume_name(); self._eat(TK.PIPE)
        cn = self._consume_name()
        args = []
        while self._match(TK.PIPE): self._eat(TK.PIPE); args.append(self._parse_value())
        self._eat(TK.SEMI); return NewNode(obj_name=on, class_name=cn, args=args)

    # ── 值解析 ──────────────────────────────────────────
    def _parse_value(self) -> ASTNode:
        t = self._peek()
        if t.kind == TK.KW_CALC: return self._parse_calc()
        if t.kind == TK.KW_GET: return self._parse_get()
        if t.kind == TK.KW_CALL: return self._parse_call_expr()
        if t.kind == TK.KW_AS: return self._parse_as()
        if t.kind == TK.KW_ISA: return self._parse_isa()
        if t.kind in (TK.KW_MAP_GET,): return self._parse_map_get_val()
        if t.kind in (TK.KW_SET_HAS,): return self._parse_set_has_val()
        if t.kind == TK.KW_STR_JOIN: return self._parse_str_join_expr()
        if t.kind == TK.KW_STR_CUT: return self._parse_str_cut_expr()
        if t.kind == TK.KW_STR_LEN: return self._parse_str_len_expr()
        if t.kind == TK.KW_STR_FIND: return self._parse_str_find_expr()
        if t.kind == TK.KW_STR_REPL: return self._parse_str_repl_expr()
        if t.kind == TK.KW_ARR_LEN: return self._parse_arr_len_expr()
        if t.kind == TK.LIT_INT: return LiteralNode(value=self._eat(TK.LIT_INT).value, dk_type=IntType())
        if t.kind == TK.LIT_REAL: return LiteralNode(value=self._eat(TK.LIT_REAL).value, dk_type=RealType())
        if t.kind == TK.LIT_STR: return LiteralNode(value=self._eat(TK.LIT_STR).value, dk_type=StrType())
        if t.kind == TK.LIT_TRUE: self._eat(TK.LIT_TRUE); return LiteralNode(value=True, dk_type=BoolType())
        if t.kind == TK.LIT_FALSE: self._eat(TK.LIT_FALSE); return LiteralNode(value=False, dk_type=BoolType())
        if t.kind == TK.TYPE_NIL_KW: self._eat(TK.TYPE_NIL_KW); return LiteralNode(value=None, dk_type=NilType())
        if t.kind == TK.KW_NOT: self._eat(TK.KW_NOT); return UnaryOpNode(op='not', operand=self._parse_value())
        if t.kind == TK.LBRACKET: return self._parse_list_lit()
        if t.kind == TK.LBRACE:
            # 判断是 map 还是 set
            return self._parse_map_or_set_lit()
        if t.kind == TK.LPAREN: return self._parse_group()
        if t.kind == TK.IDENT: return self._parse_ident_chain()
        # 运算符 → CALC 表达式（无需 CALC 前缀）
        if t.kind in COMPARISON or t.kind in (TK.OP_ADD,TK.OP_SUB,TK.OP_MUL,TK.OP_DIV,TK.OP_MOD):
            return self._parse_bare_calc_expr()
        raise ParseError(f'期望一个值', t)

    def _parse_calc(self):
        self._eat(TK.KW_CALC)
        return self._parse_bare_calc_expr()

    def _parse_bare_calc_expr(self):
        """解析无 CALC 前缀的运算符表达式: op | left | right"""
        t = self._eat()
        # 操作符可以是 OP_* 或 KW_AND/KW_OR/KW_NOT
        op_map = {TK.OP_ADD:'add', TK.OP_SUB:'sub', TK.OP_MUL:'mul', TK.OP_DIV:'div', TK.OP_MOD:'mod',
                  TK.OP_GT:'gt', TK.OP_LT:'lt', TK.OP_EQ:'eq', TK.OP_NE:'ne', TK.OP_GE:'ge', TK.OP_LE:'le',
                  TK.KW_AND:'and', TK.KW_OR:'or', TK.KW_NOT:'not'}
        if t.kind in op_map:
            op_word = op_map[t.kind]
        else:
            op_word = t.value if t.value else 'unknown'
        
        if op_word == 'not':
            self._eat(TK.PIPE)
            operand = self._parse_value()
            return UnaryOpNode(op='not', operand=operand)
        
        self._eat(TK.PIPE); left = self._parse_value(); self._eat(TK.PIPE); right = self._parse_value()
        # 映射运算符单词到符号
        sym_map = {'add':'+','sub':'-','mul':'*','div':'/','mod':'%',
                  'gt':'>','lt':'<','eq':'==','ne':'!=','ge':'>=','le':'<=',
                  'and':'and','or':'or'}
        op_sym = sym_map.get(op_word, op_word)
        return BinaryOpNode(op=op_sym, left=left, right=right)

    def _parse_get(self):
        self._eat(TK.KW_GET); n = self._consume_name(); self._eat(TK.PIPE)
        idx = self._parse_value(); return IndexNode(target=VarRefNode(name=n), index=idx)

    def _parse_as(self):
        self._eat(TK.KW_AS); self._eat(TK.LPAREN); e = self._parse_value()
        self._eat(TK.COMMA); tt = self._parse_type(); self._eat(TK.RPAREN)
        return AsNode(expr=e, target_type=tt)

    def _parse_isa(self):
        self._eat(TK.KW_ISA); self._eat(TK.LPAREN); e = self._parse_value()
        self._eat(TK.COMMA); tt = self._parse_type(); self._eat(TK.RPAREN)
        return IsaNode(expr=e, check_type=tt)

    def _parse_map_get_val(self):
        self._eat(TK.KW_MAP_GET); n = self._consume_name(); self._eat(TK.PIPE)
        k = self._parse_value(); return MapGetNode(map_name=n, key=k)

    def _parse_set_has_val(self):
        self._eat(TK.KW_SET_HAS); n = self._consume_name(); self._eat(TK.PIPE)
        v = self._parse_value()
        return BinaryOpNode(op='set_has', left=VarRefNode(name=n), right=v)

    def _parse_list_lit(self):
        self._eat(TK.LBRACKET); elems = []
        if not self._match(TK.RBRACKET):
            elems.append(self._parse_value())
            while self._match(TK.COMMA): self._eat(TK.COMMA); elems.append(self._parse_value())
        self._eat(TK.RBRACKET); return ListLiteralNode(elements=elems)

    def _parse_map_or_set_lit(self):
        self._eat(TK.LBRACE)
        if self._match(TK.RBRACE): self._eat(TK.RBRACE); return MapLiteralNode(pairs=[])
        # 看第一个值后是 : 还是 , 或 }
        first = self._parse_value()
        if self._match(TK.COLON):  # map
            self._eat(TK.COLON); fv = self._parse_value()
            pairs = [(first, fv)]
            while self._match(TK.COMMA):
                self._eat(TK.COMMA); k = self._parse_value(); self._eat(TK.COLON); v = self._parse_value()
                pairs.append((k, v))
            self._eat(TK.RBRACE); return MapLiteralNode(pairs=pairs)
        else:  # set
            elems = [first]
            while self._match(TK.COMMA):
                self._eat(TK.COMMA); elems.append(self._parse_value())
            self._eat(TK.RBRACE); return SetLiteralNode(elements=elems)

    def _parse_group(self):
        self._eat(TK.LPAREN); e = self._parse_value(); self._eat(TK.RPAREN); return e

    def _parse_ident_chain(self):
        name = self._consume_name()
        while self._match(TK.DOT):
            self._eat(TK.DOT); m = self._consume_name(); name = f'{name}.{m}'
        # 函数调用 (identifier(args))
        if self._match(TK.LPAREN):
            self._eat(TK.LPAREN); args = []
            if not self._match(TK.RPAREN):
                args.append(self._parse_value())
                while self._match(TK.COMMA): self._eat(TK.COMMA); args.append(self._parse_value())
            self._eat(TK.RPAREN); return CallNode(name=name, arguments=args)
        # 管道调用 (identifier | args) — FFI / implicit call
        if self._match(TK.PIPE) and '.' in name:
            args = []
            while self._match(TK.PIPE):
                self._eat(TK.PIPE); args.append(self._parse_value())
            return CallNode(name=name, arguments=args)
        # 索引访问
        if self._match(TK.LBRACKET):
            return self._parse_index(VarRefNode(name=name))
        return VarRefNode(name=name)

    def _parse_index(self, target):
        self._eat(TK.LBRACKET); idx = self._parse_value(); self._eat(TK.RBRACKET)
        node = IndexNode(target=target, index=idx)
        while self._match(TK.LBRACKET): node = self._parse_index(node)
        return node

    # ── 辅助 ──────────────────────────────────────────────
    def _parse_block(self):
        self._eat(TK.LBRACE); stmts = []
        while not self._match(TK.RBRACE) and not self._eof():
            s = self._parse_top_level()
            if s is not None: stmts.append(s)
        self._eat(TK.RBRACE); return BlockNode(statements=stmts)

    def _parse_type(self):
        t = self._peek()
        tm = {TK.TYPE_INT:IntType, TK.TYPE_REAL:RealType, TK.TYPE_STR:StrType,
              TK.TYPE_BOOL:BoolType, TK.TYPE_NIL_KW:NilType}
        if t.kind in tm: self._eat(t.kind); return tm[t.kind]()
        if t.kind == TK.TYPE_ARR:
            self._eat(TK.TYPE_ARR); self._eat(TK.LBRACKET); et = self._parse_type()
            self._eat(TK.RBRACKET); return ListType(et)
        if t.kind == TK.TYPE_MAP:
            self._eat(TK.TYPE_MAP); self._eat(TK.LBRACKET); kt = self._parse_type()
            self._eat(TK.COMMA); vt = self._parse_type(); self._eat(TK.RBRACKET); return MapType(kt, vt)
        if t.kind == TK.TYPE_SET:
            self._eat(TK.TYPE_SET); self._eat(TK.LBRACKET); et = self._parse_type()
            self._eat(TK.RBRACKET); return SetType(et)
        if t.kind == TK.IDENT:  # 用户定义类型别名
            return ObjType(self._eat(TK.IDENT).value)
        raise ParseError(f'期望类型关键字', t)

    def _parse_comp_op_str(self):
        t = self._eat(); m = {TK.OP_GT:'gt',TK.OP_LT:'lt',TK.OP_EQ:'eq',TK.OP_NE:'ne',TK.OP_GE:'ge',TK.OP_LE:'le'}
        if t.kind in m: return m[t.kind]
        raise ParseError('期望比较运算符', t)

    def _consume_name(self):
        t = self._peek()
        if t.kind == TK.IDENT: return self._eat(TK.IDENT).value
        if t.kind in OP_TO_STR: return OP_TO_STR[self._eat(t.kind).kind]
        raise ParseError('期望标识符', t)

    def _is_type(self, k): return k in (TK.TYPE_INT,TK.TYPE_REAL,TK.TYPE_STR,TK.TYPE_BOOL,TK.TYPE_NIL_KW,
                                         TK.TYPE_ARR,TK.TYPE_SET,TK.TYPE_MAP)

    def _token_raw(self, t):
        if t.value is not None: return str(t.value)
        m = {TK.PIPE:'|',TK.SEMI:';',TK.LBRACE:'{',TK.RBRACE:'}',TK.LPAREN:'(',TK.RPAREN:')',
             TK.LBRACKET:'[',TK.RBRACKET:']',TK.COLON:':',TK.COMMA:',',TK.DOT:'.'}
        return m.get(t.kind, '')
