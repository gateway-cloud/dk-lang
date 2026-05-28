# DK-Lang 开发者文档 —— AI 强制读取

> **⚠️⚠️⚠️ 强制性声明 ⚠️⚠️⚠️**  
> 任何 AI（包括但不限于 DeepSeek、Claude、GPT、Gemini 等）在开发、修改、扩展或以任何方式变更 DK-Lang 解释器代码时，**必须先完整阅读本文档**。  
> 本文档是 DK-Lang 实现的**唯一权威技术参考**。  
> **不读本文档就开发 = 拒绝执行。**

**当前版本**: v1.4.0  
**最后更新**: 2026-05-29

---

## 第一章：项目架构

### 1.1 模块依赖关系

```
dk_cli.py (CLI入口)
    ↓
dklang/__init__.py (run_dk / run_dk_string)
    ↓
dklang/lexer.py  ──→  Token列表
dklang/parser.py ──→  AST树 (复用 dklang/ast_nodes.py)
dklang/interpreter.py ──→ 执行结果
    ↓
dklang/extensions.py (数据库 + HTTP 内置函数注册)
dklang/httpd.py (HTTP 客户端/服务端 + WebSocket + GraphQL)
dklang/database.py (SQLite/MySQL/PostgreSQL 统一接口 + ORM)
dklang/ffi/__init__.py (Python/C++/Java 外部库导入)
dklang/stdlib/ (标准库 .dk 文件)
```

### 1.2 新增关键字 (v1.1 - v1.4)

| 版本 | 新增关键字 | 用途 |
|------|-----------|------|
| v1.1 | `ARR_LEN` | 获取数组长度 |
| v1.3 | `SERVER` `ROUTE` `MIDDLEWARE` `STATIC` | 纯 DK-Lang HTTP 服务器 |
| v1.3 | 反引号 `` ` `` 多行字符串 | 多行字符串字面量 |
| v1.4 | 裸运算符表达式 | `eq`/`gt` 等无需 `CALC` 前缀 |

### 1.3 新增 AST 节点 (v1.1 - v1.4)

| 节点 | 版本 | 对应语法 |
|------|------|---------|
| `ArrLenNode` | v1.1 | `ARR_LEN v \| arr ;` |
| `ServerNode` | v1.3 | `SERVER "host" \| port \| { ... } ;` |
| `RouteNode` | v1.3 | `ROUTE "GET" \| "/path" \| handler ;` |
| `MiddlewareNode` | v1.3 | `MIDDLEWARE handler ;` |
| `StaticNode` | v1.3 | `STATIC "/prefix" \| "./dir" ;` |
| `MapHasNode` | v1.2 | `MAP_HAS v \| map \| key ;` |

### 1.4 语法 → AST 映射规则（绝对不变 + 新增）

| DK-Lang 指令 | AST 节点 | 版本 |
|-------------|----------|------|
| `VAR name \| type ;` | `VarDeclNode(name, type)` | v1.0 |
| `SET name \| value ;` | `AssignNode(name, value)` | v1.0 |
| `IF op \| left \| right \| {block} ;` | `IfNode(BinaryOp, then, [], else)` | v1.0 |
| `LOOP var \| start \| end \| step \| {block} ;` | `LoopNode(init, cond, step, block)` | v1.0 |
| `FUNC name \| params... \| rettype \| {block} ;` | `FuncDefNode(name, params, rettype, block)` | v1.0 |
| `CALL name \| args... ;` | `ExprStmtNode(CallNode(name, args))` | v1.0 |
| `ARR_LEN v \| arr ;` | `ArrLenNode(v, arr)` | v1.1 |
| `SERVER host \| port \| { ... } ;` | `ServerNode(host, port, routes, mw, statics)` | v1.3 |
| `STR_JOIN sep \| parts...` (表达式) | `CallNode('_str_join', [sep, *parts])` | v1.1 |
| `eq \| a \| b` (裸运算符) | `BinaryOpNode('eq', a, b)` | v1.4 |

### 1.5 绝对编码约束

1. **文件编码**：所有 `.py` 文件必须是 UTF-8
2. **行尾**：统一 LF (`\n`)，不使用 CRLF
3. **缩进**：4 空格，不使用 Tab
4. **命名**：
   - 类名：PascalCase（`InstructionLexer`, `VarDeclNode`）
   - 函数/方法：snake_case（`parse_var`, `_eval_assign`）
   - 常量：UPPER_SNAKE_CASE（`KEYWORDS`, `COMPARISON_OPS`）
5. **类型注解**：所有公共方法必须有类型注解（Python 3.8+ 兼容）
6. **异常**：使用 `from dklang.ast_nodes import DKError` 体系
7. **禁止**：`eval()`, `exec()`, `compile()` 在解释器核心代码中使用

---

## 第二章：词法分析器实现规范

### 2.1 Token 分类体系

| 类别 | Token 枚举前缀 | 示例 |
|------|---------------|------|
| 指令 | `KW_` | `KW_VAR`, `KW_SET`, `KW_FUNC`, `KW_SERVER` |
| 运算符 | `OP_` | `OP_ADD`, `OP_GT`, `OP_EQ` |
| 类型 | `TYPE_` | `TYPE_INT`, `TYPE_STR`, `TYPE_ARR` |
| 字面量 | `LIT_` | `LIT_INT`, `LIT_STR`, `LIT_TRUE` |
| 分隔符 | 无前缀 | `PIPE`, `SEMI`, `LBRACE`, `RBRACE` |
| 标识符 | `IDENT` | 变量名/函数名 |

### 2.2 关键字完整清单 (~100个)

```
指令(大写): VAR SET CONST PRINT IF ELSE LOOP SWITCH CASE DEFAULT BREAK NEXT
           FUNC CALL RET ARR GET PUSH POP SET_ADD SET_HAS MAP MAP_SET MAP_GET
           MAP_DEL MAP_HAS GLOBAL LOCAL STR_JOIN STR_CUT STR_LEN STR_FIND STR_REPL
           ARR_LEN AND OR NOT WHILE USE FILE_READ FILE_WRITE FILE_EXIST TRY CATCH
           THROW AS TYPE ISA MACRO EVAL ALIAS AI_ASK AI_EXTRACT AI_SUMMARIZE
           AI_CLASSIFY AI_TRANSLATE CTX PROMPT AI_IMAGE LOG TRACE TIME RAND
           B64ENC B64DEC ASYNC AWAIT THREAD JOIN KILL HTTP_GET HTTP_POST
           WS_CONN WS_SEND WS_RECV URL_ENC URL_DEC DB_CONN DB_QUERY DB_INSERT
           DB_UPDATE DB_DELETE CLASS NEW PROP METHOD EXTENDS THIS SUPER WAIT
           CRON EXEC ENV_GET ENV_SET EXIT SANDBOX PERMIT AUDIT VERSION
           SERVER ROUTE MIDDLEWARE STATIC      ← v1.3 新增

运算符(小写): add sub mul div mod gt lt eq ne ge le

类型(小写): int real str bool nil arr set map

值(小写): true false nil
```

**注意 (v1.2)**: `task`, `thread`, `file`, `db`, `class`, `obj` 已从 TYPE 关键字中移除，避免与常用标识符冲突。

### 2.3 分词流程

```
1. 跳过空白 (\s \t \r)
2. 遇到 \n → 行号+1
3. 遇到 // → 跳过到行尾
4. 遇到 /* → 跳过到 */
5. 遇到大写字母 → 累积 [A-Z0-9_] → 查指令表 → Token(KW_xxx)
6. 遇到小写字母 → 累积 [a-z0-9_] →
   - 查运算符表 → Token(OP_xxx)
   - 查类型表 → Token(TYPE_xxx)
   - 查值表 → Token(LIT_xxx)
   - 否则 → Token(IDENT, word)
7. 遇到数字 → 累积 [0-9.] → Token(LIT_INT/LIT_REAL)
8. 遇到 " → 累积到下一个 " → Token(LIT_STR)
   ⚠️ v1.4: 未转义换行符会抛出 LexerError
9. 遇到 ` → 累积到下一个 ` → Token(LIT_STR) (多行字符串 v1.3)
   ⚠️ v1.4: 支持 \n \t \\ \` 转义序列
10. 遇到符号 → | ; { } [ ] , : . ( ) → 对应分隔符 Token
11. 重复到 EOF
```

### 2.4 v1.4 词法修复

| Bug ID | 问题 | 修复 |
|--------|------|------|
| LEX-01 | `_read_string` 非转义字符列号翻倍 | 移除多余的 `self.col += 1` |
| LEX-02 | 双引号字符串允许未转义换行 | 抛出 LexerError |
| LEX-03 | 反引号字符串不处理转义 | 添加 `\n \t \\ \`` 转义 |

---

## 第三章：语法分析器实现规范

### 3.1 两遍解析 (v1.2)

```
parse():
  第一遍: 预扫描 FUNC 定义，收集参数数量 → _func_param_counts
  第二遍: 正常解析，CALL 按已知参数数精确消费 |
```

### 3.2 指令分发表（v1.4 完整版）

| peek token | 调用函数 | 说明 |
|-----------|---------|------|
| KW_VAR | parse_var_decl | VAR name \| type ; |
| KW_SET | parse_set | SET name \| value ; |
| KW_IF | parse_if | IF op \| left \| right \| block ; |
| KW_LOOP | parse_loop | 计数模式 / WHILE 模式 |
| KW_FUNC | parse_func_def | FUNC name \| params \| rettype \| block ; |
| KW_CALL | parse_call_stmt | CALL name \| args ; |
| KW_SERVER | parse_server | SERVER host \| port \| { ROUTE... } ; ← v1.3 |
| KW_ARR_LEN | parse_arr_len | ARR_LEN var \| arr ; ← v1.1 |
| KW_MAP_HAS | parse_map_has | MAP_HAS var \| map \| key ; ← v1.2 |
| KW_SET_ADD | parse_set_add | SET_ADD set \| value ; ← v1.2 |
| KW_SET_HAS | parse_set_has | SET_HAS var \| set \| value ; ← v1.2 |
| ... | ... | 其余所有指令 |

### 3.3 值的解析（v1.4）

```
parse_value():
  token = peek()
  KW_CALC → parse_calc_expr()
  KW_CALL → parse_call_expr()        # v1.2: 按 func_param_counts 精确消费 |
  KW_STR_JOIN → parse_str_join_expr() # v1.1: 表达式形式
  KW_STR_CUT → parse_str_cut_expr()   # v1.1
  KW_STR_LEN → parse_str_len_expr()   # v1.1
  KW_STR_FIND → parse_str_find_expr() # v1.1
  KW_STR_REPL → parse_str_repl_expr() # v1.1
  KW_ARR_LEN → parse_arr_len_expr()   # v1.1
  OP_EQ/OP_GT/etc → parse_bare_calc_expr() # v1.4: 裸运算符
  LIT_INT → LiteralNode(int)
  LIT_STR → LiteralNode(str)
  LIT_TRUE → LiteralNode(True)
  IDENT → VarRefNode(name)
  否则 → 报错
```

### 3.4 v1.2/v1.4 解析修复

| Bug ID | 问题 | 修复 |
|--------|------|------|
| PAR-01 | 预扫描中 while 循环使用三元表达式导致死循环 | 改为简单深度计数 |
| PAR-02 | CALL 参数数量限制导致嵌套调用语法错误 | 按预扫描参数数精确消费，多余 pipe 留给外层 |

---

## 第四章：执行器实现规范

### 4.1 环境模型

```
全局环境 (glob):
  vars: {name: (value, is_const)}
  funcs: {name: FuncDefNode}
  builtins: print, len, _str_join, _db_execute, _http_get...

作用域栈:
  [global_env, func_env, block_env, ...]
  每次进入函数/块 → push (Environment(parent=current))
  每次退出 → pop
```

### 4.2 信号体系

- `ReturnSignal(value)` — 函数返回值
- `BreakSignal()` — 跳出循环/SWITCH
- `NextSignal()` — 跳过本次循环迭代
- `DKError(type, msg, line, col)` — 统一错误

### 4.3 内置函数注册表 (v1.4)

| 函数名 | 用途 | 版本 |
|--------|------|------|
| `print` | 标准输出 | v1.0 |
| `_str_join` | 字符串拼接 | v1.0 |
| `_str_cut` | 字符串截取 | v1.0 |
| `_str_len` | 字符串长度 | v1.0 |
| `_str_find` | 字符串查找 | v1.0 |
| `_str_repl` | 字符串替换 | v1.0 |
| `_arr_len` | 数组长度 | v1.1 |
| `_set_add` | 集合添加 | v1.2 |
| `_db_connect` | 数据库连接 | v1.2 |
| `_db_execute` | SQL 执行 | v1.2 |
| `_db_insert` | 数据插入 | v1.2 |
| `_db_select` | 数据查询 | v1.2 |
| `_db_table` | 查询构造器 | v1.2 |
| `_http_get` | HTTP GET | v1.2 |
| `_http_post` | HTTP POST | v1.2 |

### 4.4 SERVER 执行流程 (v1.3)

```
_ev_server(ServerNode):
  1. 创建 HttpServer(host, port)
  2. 注册 MIDDLEWARE 处理器链
  3. 注册 STATIC 静态文件路由
  4. 注册 ROUTE 处理器（每个 route 调用对应的 DK-Lang 函数）
  5. server.start(blocking=True)
  
  Route handler 流程:
    请求到达 → 构造 req_data JSON → interp._call_dk_func(handler, req_data)
    → DK 函数返回字符串 → 自动检测 Content-Type → 返回 HTTP Response
```

### 4.5 v1.4 解释器修复

| Bug ID | 问题 | 修复 |
|--------|------|------|
| INT-01 | 整数除法总是返回 float | 整数除尽时返回 int |
| INT-02 | 取模运算截断浮点数 | 使用 Python 原生 `%`，支持 float % float |
| INT-03 | 函数调用无参数数量校验 | 添加 `len(args) != len(params)` 检查 |
| INT-04 | 内置函数同名遮蔽用户函数 | 用户函数优先检查，内置作为 fallback |
| INT-05 | LOOP 循环变量未自动定义 | `_ev_loop` 自动 define 循环变量 |

---

## 第五章：扩展模块规范

### 5.1 扩展注册

```python
# dklang/extensions.py
def register_all(interpreter):
    register_database_extensions(interpreter)
    register_http_extensions(interpreter)
```

在 `Interpreter.__init__()` 中自动调用 `_register_extensions()`。

### 5.2 数据库模块

```python
# dklang/database.py
Database.connect(name, db_type, conn_str)  # 连接池
db.execute(sql, params)                     # 原始 SQL
db.insert(table, data)                      # 插入
db.select(table, **filters)                 # 查询
db.table(name).where(...).build_select()    # 查询构造器
```

支持 SQLite、MySQL、PostgreSQL。

### 5.3 HTTP 模块

```python
# dklang/httpd.py
HttpServer(host, port)           # HTTP 服务端
server.router.get/post/put/delete(pattern)  # 路由注册
server.use(middleware)           # 中间件
server.static(prefix, dir)       # 静态文件
server.start(blocking=True)      # 启动

HttpClient(base_url)             # HTTP 客户端
client.get/post/put/delete(path) # 请求方法

WebSocketServer(host, port)      # WebSocket 服务端
GraphQLResolver()                # GraphQL 端点
```

---

## 第六章：测试体系

### 6.1 测试套件（v1.4）

| 测试文件 | 类型 | 用例数 |
|---------|------|--------|
| `tests/test_improvements.dk` | 功能回归 | 6 |
| `tests/test_nested_call2.dk` | 嵌套调用 | 2 |
| `tests/test_server_syntax.dk` | SERVER 语法 | 3 |
| `tests/industrial_core.dk` | 核心语言特性 | 35 |
| `tests/industrial_edge.dk` | 边界+压力 | 9 |
| `tests/deep_audit.py` | Python 单元测试 | 93 |
| `student_system/main.dk` | 集成测试 | ~50 |
| `tests/library_system.dk` | 集成测试 | ~80 |
| `projects/taskflow/server_v2.dk` | 全栈集成 | ~60 |

### 6.2 测试命令

```bash
# 运行所有 DK 测试
python dk_cli.py run tests/industrial_core.dk
python dk_cli.py run tests/industrial_edge.dk
python dk_cli.py run tests/test_improvements.dk

# Python 单元测试
python -m pytest tests/deep_audit.py -v

# 集成测试
python dk_cli.py run student_system/main.dk
python dk_cli.py run tests/library_system.dk
```

---

## 第七章：版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2024-04-02 | 初始发布：完整词法/语法/解释器 |
| v1.1 | 2026-05-28 | STR 表达式化 + ARR_LEN + TRY/CATCH 修复 + TIME 格式化 |
| v1.2 | 2026-05-28 | 两遍解析 + 嵌套 CALL 修复 + SET_ADD/SET_HAS/MAP_HAS + DB 扩展 |
| v1.3 | 2026-05-28 | SERVER/ROUTE/MIDDLEWARE/STATIC + 多行字符串 + 中间件链 |
| v1.4 | 2026-05-29 | 裸运算符 + 深度审计 10 Bug 修复 + Arity 检查 + LOOP 变量 |

---

> **再次强调：本文档是 DK-Lang 实现的唯一技术规范。任何开发行为必须以本文档为依据。**
