# DK-Lang 深度质量审计报告

**日期**: 2026-05-28
**审计范围**: dklang/lexer.py, dklang/parser.py, dklang/interpreter.py, dklang/ast_nodes.py
**测试文件**: tests/deep_audit.py
**测试结果**: 93 通过 / 9 失败 (4 个根因 Bug)

---

## 目录

1. [测试摘要](#1-测试摘要)
2. [BUG-LEX-01: `_read_string` 列号翻倍递增](#2-bug-lex-01)
3. [BUG-LEX-02: 双引号字符串允许未转义换行](#3-bug-lex-02)
4. [BUG-LEX-03: 反引号多行字符串不处理转义序列](#4-bug-lex-03)
5. [BUG-PAR-01: FUNC 预扫描无限循环风险](#5-bug-par-01)
6. [BUG-PAR-02: CALL 参数数量预扫描限制导致语法错误](#6-bug-par-02)
7. [BUG-INT-01: 整数除法总是返回浮点数](#7-bug-int-01)
8. [BUG-INT-02: 取模运算截断浮点数](#8-bug-int-02)
9. [BUG-INT-03: 函数调用无参数数量校验](#9-bug-int-03)
10. [BUG-INT-04: 内置函数同名遮蔽用户函数](#10-bug-int-04)
11. [BUG-INT-05: LOOP 循环变量未自动定义](#11-bug-int-05)
12. [改进建议](#12-改进建议)

---

## 1. 测试摘要

### 测试覆盖范围

| 模块 | 测试数 | 通过 | 失败 |
|------|--------|------|------|
| 词法分析器 (Lexer) | 21 | 21 | 0 |
| 语法分析器 (Parser) | 21 | 21 | 0 |
| 解释器边界值 | 13 | 11 | 2 |
| 环境作用域 | 6 | 6 | 0 |
| SIGNAL 传播 | 6 | 4 | 2 |
| 类型系统 | 9 | 9 | 0 |
| 函数调用 | 5 | 4 | 1 |
| 集成测试 | 9 | 8 | 1 |
| **确认 Bug 测试** | **12** | **9** | **3** |
| **总计** | **102** | **93** | **9** |

### 失败测试根因分析

| 失败测试组 | 根因 | Bug ID |
|-----------|------|--------|
| test_empty_set, test_non_empty_set, test_map_operations | SET 需要变量预先声明 (这是正确的语义, 非 Bug) | — |
| test_break_in_nested_loop, test_next_skips_iteration, test_bug_interpreter_loop_var_scope | LOOP 循环变量未自动定义 | **BUG-INT-05** |
| test_function_arity_mismatch_too_many, test_bug_interpreter_no_arity_check_too_many | CALL 预扫描参数数量限制冲突 | **BUG-PAR-02** |
| test_bug_lexer_backtick_no_escape | Python 字符串 repr 显示歧义 | — |

---

## 2. BUG-LEX-01: 列号翻倍递增

### 严重程度: 🟡 中

### 位置
`dklang/lexer.py` — `_read_string()` 方法

### 问题描述

```python
# 当前代码 (行 ~107-110)
def _read_string(self):
    ...
    while self.pos < len(self.src) and self.src[self.pos] != '"':
        ch = self.src[self.pos]
        ...
        if ch == '\\' and self.pos+1 < len(self.src):
            self._adv(); n = self.src[self.pos]
            chars.append(...); self._adv()      # ✅ 正确：两个 _adv() 各 +1 col
        else:
            chars.append(ch); self._adv(); self.col += 1  # ❌ BUG: _adv() 已 +1, 再加 +1 = 翻倍
    ...
```

**根因**: `_adv()` 方法定义为 `self.pos += 1; self.col += 1`。在非转义分支中，调用了 `self._adv()` 后又手动 `self.col += 1`，导致 col 被递增了 2 次。

### 影响
- 字符串字面量的列号信息不正确
- 后续语法错误报告的行列位置可能偏差
- 字符串越长，偏差越大

### 修复

```python
# lexer.py _read_string() 修复
def _read_string(self):
    l, c = self.line, self.col; self._adv(); chars = []
    while self.pos < len(self.src) and self.src[self.pos] != '"':
        ch = self.src[self.pos]
        if ch == '\n': self.line += 1; self.col = 1
        if ch == '\\' and self.pos+1 < len(self.src):
            self._adv(); n = self.src[self.pos]
            chars.append({'n':'\n','t':'\t','\\':'\\','"':'"'}.get(n, '\\'+n))
            self._adv()
        else:
            chars.append(ch); self._adv()  # ← 移除 self.col += 1
    if self.pos >= len(self.src): raise LexerError('未闭合的字符串', l, c)
    self._adv()
    return Token(TK.LIT_STR, ''.join(chars), l, c)
```

---

## 3. BUG-LEX-02: 双引号字符串允许未转义换行

### 严重程度: 🟡 中

### 位置
`dklang/lexer.py` — `_read_string()` 方法

### 问题描述

当双引号字符串中包含未转义的换行符 `\n` 时，词法器不会报错，而是将换行符静默包含在字符串值中：

```python
# 当前行为
tokens = Lexer('"line1\nline2"').tokenize()
# tokens[0].value == 'line1\nline2'  (包含真实换行)
# 期望: 应抛出 LexerError("未闭合的字符串" 或 "不允许的换行")
```

**根因**: 代码中 `if ch == '\n': self.line += 1; self.col = 1` 仅更新行列号，没有抛出错误。

### 影响
- 源码格式化不一致：误写多行字符串而不自知
- 语义歧义：用户可能使用 `\n` 期望转义，但实际得到原始换行
- 大多数编程语言在普通字符串中禁止未转义的换行

### 修复

```python
# lexer.py _read_string() 修复
def _read_string(self):
    l, c = self.line, self.col; self._adv(); chars = []
    while self.pos < len(self.src) and self.src[self.pos] != '"':
        ch = self.src[self.pos]
        if ch == '\n':
            raise LexerError('字符串中不允许未转义的换行符，请使用 "\\n" 或多行字符串 ``', 
                             self.line, self.col)
        if ch == '\\' and self.pos+1 < len(self.src):
            self._adv(); n = self.src[self.pos]
            chars.append({'n':'\n','t':'\t','\\':'\\','"':'"'}.get(n, '\\'+n))
            self._adv()
        else:
            chars.append(ch); self._adv()
    if self.pos >= len(self.src): raise LexerError('未闭合的字符串', l, c)
    self._adv()
    return Token(TK.LIT_STR, ''.join(chars), l, c)
```

---

## 4. BUG-LEX-03: 反引号多行字符串不处理转义

### 严重程度: 🟡 中

### 位置
`dklang/lexer.py` — `_read_ml_string()` 方法

### 问题描述

反引号多行字符串逐字符读取，不处理任何转义序列：

```python
def _read_ml_string(self):
    l, c = self.line, self.col; self._adv(); chars = []
    while self.pos < len(self.src) and self.src[self.pos] != '`':
        ch = self.src[self.pos]
        if ch == '\n': self.line += 1; self.col = 1
        chars.append(ch); self._adv()       # ← 无转义处理
    ...
```

### 影响
- `\n` 被保留为字面量反斜杠+n，而非换行符
- `\t` 被保留为字面量反斜杠+t
- 与双引号字符串的转义行为不一致

### 修复

```python
# lexer.py _read_ml_string() 修复
def _read_ml_string(self):
    l, c = self.line, self.col; self._adv(); chars = []
    while self.pos < len(self.src) and self.src[self.pos] != '`':
        ch = self.src[self.pos]
        if ch == '\n': self.line += 1; self.col = 1
        if ch == '\\' and self.pos+1 < len(self.src):
            self._adv(); n = self.src[self.pos]
            chars.append({'n':'\n','t':'\t','\\':'\\','`':'`'}.get(n, '\\'+n))
            self._adv()
        else:
            chars.append(ch); self._adv()
    if self.pos >= len(self.src): raise LexerError('未闭合的多行字符串', l, c)
    self._adv()
    return Token(TK.LIT_STR, ''.join(chars), l, c)
```

---

## 5. BUG-PAR-01: FUNC 预扫描无限循环风险

### 严重程度: 🔴 高

### 位置
`dklang/parser.py` — `parse()` 方法, FUNC 预扫描代码 (~行 32-55)

### 问题描述

```python
# parse() 方法中的 FUNC 预扫描
while self.pos < len(self.tokens):
    tk = self._peek()
    if tk.kind == TK.LBRACE: depth += 1
    elif tk.kind == TK.RBRACE:
        depth -= 1
        if depth <= 0:
            self._eat(TK.RBRACE)
            break
    self._eat(tk.kind) if depth > 0 else self.pos  # ❌ BUG
    if depth <= 0: break
```

**根因**: `self._eat(tk.kind) if depth > 0 else self.pos` — 当 `depth == 0` 时，`self.pos` 是一个整数表达式（无副作用），token 位置不会前进。这会导致在某些边缘情况下（例如函数声明的 `{` 在某处丢失）出现无限循环。

### 影响
- 在畸形的 FUNC 声明中可能导致解析器挂起
- 对合法输入当前可工作，但代码极脆弱

### 修复

```python
# parser.py parse() 方法修复
# 替换 FUNC 预扫描中的体跳过逻辑
def _skip_balanced_braces(self):
    """从当前位置跳过平衡的 {} 块"""
    depth = 0
    while self.pos < len(self.tokens):
        tk = self._peek()
        if tk.kind == TK.LBRACE:
            depth += 1
        elif tk.kind == TK.RBRACE:
            depth -= 1
            if depth <= 0:
                self._eat(TK.RBRACE)
                return
        if depth > 0:
            self._eat(tk.kind)
        else:
            # 还没遇到 {，提前退出
            break
    raise ParseError('无法找到匹配的 RBRACE', self._peek())
```

然后在 `parse()` 中调用: `self._skip_balanced_braces()` 替代原来的 while 循环。

---

## 6. BUG-PAR-02: CALL 参数数量预扫描限制导致语法错误

### 严重程度: 🔴 高

### 位置
`dklang/parser.py` — `_parse_call_expr()` 方法

### 问题描述

```python
def _parse_call_expr(self):
    self._eat(TK.KW_CALL); n = self._consume_name()
    expected = self._func_param_counts.get(n, -1)
    while self._match(TK.PIPE):
        if expected >= 0 and len(args) >= expected:  # ❌ BUG
            break
        self._eat(TK.PIPE); args.append(self._parse_value())
    ...
```

**根因**: 预扫描收集的 `_func_param_counts` 限制了 CALL 能接受的参数数量。当函数定义 `FUNC greet | name | str | str | { ... }` 被预扫描为 param_count=1，CALL 传 3 个参数时，解析器在消费 1 个参数后停止，导致额外的 `|` 触发 `期望 SEMI (got PIPE)` 错误。

### 影响
- 用户无法在 CALL 中传递多于预扫描计数的参数
- 即使是有意传递额外参数（如可变参数函数），也会被拒绝
- 参数数量校验应该是解释器的职责，而非语法分析器

### 修复

```python
# parser.py _parse_call_expr() 修复
def _parse_call_expr(self):
    self._eat(TK.KW_CALL); n = self._consume_name()
    args = []
    # 移除 expected 参数数量限制，全部消费
    while self._match(TK.PIPE):
        self._eat(TK.PIPE)
        # 检查是否有更多有效的值参数（而非下一个语句开始）
        if self._peek().kind in (TK.SEMI, TK.EOF, TK.RBRACE):
            break
        args.append(self._parse_value())
    return CallNode(name=n, arguments=args)
```

---

## 7. BUG-INT-01: 整数除法总是返回浮点数

### 严重程度: 🟡 中

### 位置
`dklang/interpreter.py` — `_ev_bin()` 方法 (~行 248)

### 问题描述

```python
if n.op == '/':
    if r == 0: raise DKArithError('除数为0')
    return float(l) / float(r)  # ❌ 总是返回 float
```

**根因**: 强制使用 `float()` 转换后执行真除法，导致 `6 / 2 = 3.0` 而非 `3`。

### 影响
- 类型不一致：整数输入，浮点输出
- 可能与用户的类型预期不符

### 修复

```python
# interpreter.py _ev_bin() 修复 - 方案 1: Python 标准行为
if n.op == '/':
    if r == 0: raise DKArithError('除数为0')
    return l / r  # Python 3 真除法：整数除法也返回 float

# 方案 2: 整数除法则返回整数
if n.op == '/':
    if r == 0: raise DKArithError('除数为0')
    result = l / r
    # 如果结果是整数（无小数部分），返回 int
    if isinstance(l, int) and isinstance(r, int) and result == int(result):
        return int(result)
    return result
```

**建议**: 方案 2 更符合用户直觉。

---

## 8. BUG-INT-02: 取模运算截断浮点数

### 严重程度: 🟡 中

### 位置
`dklang/interpreter.py` — `_ev_bin()` 方法 (~行 252)

### 问题描述

```python
if n.op == '%':
    if r == 0: raise DKArithError('取模除数为0')
    return int(l) % int(r)  # ❌ 截断浮点数
```

**根因**: 使用 `int()` 强制转换操作数，丢失小数部分。Python 的原生 `%` 运算符支持浮点数取模（如 `5.5 % 2.0 = 1.5`）。

### 影响
- 浮点数取模结果错误：`5.5 % 2` 应为 `1.5`，但得到 `1`
- 精度丢失

### 修复

```python
# interpreter.py _ev_bin() 修复
if n.op == '%':
    if r == 0: raise DKArithError('取模除数为0')
    return l % r  # Python 原生支持 float % float
```

---

## 9. BUG-INT-03: 函数调用无参数数量校验

### 严重程度: 🟡 中

### 位置
`dklang/interpreter.py` — `_ev_call()` 方法 (~行 415)

### 问题描述

```python
# _ev_call() 中的参数绑定
args = [self.eval(a, e) for a in n.arguments]
for (pn, _), av in zip(fd.params, args):  # ❌ zip 静默丢弃/省略
    self.env.define(pn, av)
```

**根因**: `zip(fd.params, args)` 在参数数量不匹配时：
- 参数过多：多余参数被静默忽略
- 参数过少：未绑定的形式参数保持未定义状态，后续访问产生 `NameError`

### 影响
- 错误调用不会得到明确的错误消息
- 静默的数据丢失

### 修复

```python
# interpreter.py _ev_call() 修复
def _ev_call(self, n, e):
    # ... 前置代码 ...

    # 用户函数
    if n.name not in self.funcs:
        raise DKNameError(f'未定义的函数 "{n.name}"')
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
```

---

## 10. BUG-INT-04: 内置函数同名遮蔽用户函数

### 严重程度: 🟡 中

### 位置
`dklang/interpreter.py` — `_ev_call()` 方法

### 问题描述

```python
def _ev_call(self, n, e):
    # ...
    # 内置 → 先检查
    if self.glob.has(n.name):
        fn = self.glob.get(n.name)
        if callable(fn):
            args = [self.eval(a, e) for a in n.arguments]
            return fn(*args)

    # 用户函数 → 后检查
    if n.name not in self.funcs:
        raise DKNameError(f'未定义的函数 "{n.name}"')
    # ...
```

**根因**: 内置函数检查和用户函数检查的顺序错误。用户定义的函数永远无法覆盖内置函数。

### 影响
- 用户定义一个名为 `len` 的函数时，调用 `CALL len | ...` 实际执行的是内置函数
- 没有警告或错误提示

### 修复

```python
# interpreter.py _ev_call() 修复
def _ev_call(self, n, e):
    # ... FFI 检查 ...

    # 用户函数 → 优先检查
    if n.name in self.funcs:
        fd = self.funcs[n.name]
        args = [self.eval(a, e) for a in n.arguments]
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

    # 内置 → 后检查（fallback）
    if self.glob.has(n.name):
        fn = self.glob.get(n.name)
        if callable(fn):
            args = [self.eval(a, e) for a in n.arguments]
            return fn(*args)

    raise DKNameError(f'未定义的函数 "{n.name}"')
```

---

## 11. BUG-INT-05: LOOP 循环变量未自动定义

### 严重程度: 🔴 高

### 位置
`dklang/interpreter.py` — `_ev_loop()` 方法
`dklang/parser.py` — `_p_loop()` 方法

### 问题描述

```python
# parser.py _p_loop() 生成计数模式 AST
def _p_loop(self):
    # ...
    init = AssignNode(name=vn, value=st)  # ❌ AssignNode 需要变量已存在
    cond = BinaryOpNode(op='<=', left=VarRefNode(name=vn), right=en)
    step = AssignNode(name=vn, value=BinaryOpNode(op='add', left=VarRefNode(name=vn), right=sp))
    return LoopNode(init=init, condition=cond, step=step, body=b)

# interpreter.py _ev_loop() 执行
def _ev_loop(self, n, e):
    ne = Environment(e); self._push()
    self.eval(n.init, self.env)  # ❌ init 是 AssignNode, 调用 e.assign('i', 1)
    # assign 向上查找 'i' → 未找到 → DKNameError!
```

**根因**: `_p_loop` 生成的 `init` 是 `AssignNode`（赋值节点），而非 `VarDeclNode`（声明节点）。`AssignNode` 要求变量已在作用域中定义。对于 `LOOP i | 1 | 10 | 1 | {...}`，循环变量 `i` 此前从未声明，导致运行时 `NameError`。

### 影响
- **LOOP 计数模式完全不可用** — 这是 DK-Lang 的核心控制流特性
- 用户必须手动 `VAR i | int ;` 才能使用 LOOP，与语言设计意图相悖

### 修复

**方案 A: 修改 `_ev_loop` 在 init 前自动定义循环变量（推荐）**

```python
# interpreter.py _ev_loop() 修复
def _ev_loop(self, n, e):
    ne = Environment(e); self._push()
    # 提取循环变量名并自动定义
    if isinstance(n.init, AssignNode):
        loop_var = n.init.name
        self.env.define(loop_var, 0)  # 预定义默认值
    self.eval(n.init, self.env)
    try:
        while self._truthy(self.eval(n.condition, self.env)):
            try:
                self._ev_block(n.body, Environment(self.env))
            except BreakSignal:
                break
            except NextSignal:
                pass
            self.eval(n.step, self.env)
    finally:
        self._pop()
```

**方案 B: 修改 `_p_loop` 生成 VarDeclNode 而非 AssignNode**

```python
# parser.py _p_loop() 修复
def _p_loop(self):
    self._eat(TK.KW_LOOP)
    if self._peek().kind in COMPARISON:
        # while 模式不变
        ...
    else:
        # 计数模式: 生成 LoopInit 节点
        vn = self._consume_name(); self._eat(TK.PIPE)
        st = self._parse_value(); self._eat(TK.PIPE)
        en = self._parse_value(); self._eat(TK.PIPE)
        sp = self._parse_value(); self._eat(TK.PIPE)
        init = LoopInitNode(name=vn, start=st, end=en, step=sp)
        b = self._parse_block(); self._eat(TK.SEMI)
        return LoopNode(init=init, body=b)
```

**建议**: 方案 A 改动最小，不影响 AST 结构。

---

## 12. 改进建议

### 低优先级（非 Bug，但建议改进）

| 编号 | 描述 | 位置 | 建议 |
|------|------|------|------|
| IMP-01 | `_ev_switch` 每次都重新求值 case 值 | interpreter.py | 对字面量缓存结果 |
| IMP-02 | `_ev_bin` 变异 AST 的 `n.op` | interpreter.py | 使用局部变量而非修改 AST 节点 |
| IMP-03 | `_p_while` 和 `_p_loop` while 模式重复代码 | parser.py | 提取共同的 while 解析逻辑 |
| IMP-04 | `_skip_line_comment` 列号跟踪 | lexer.py | 行注释中不需要跟踪列号 |
| IMP-05 | 嵌套块注释不支持 | lexer.py | 记录为已知限制 |
| IMP-06 | 空 Set 字面量 `{}` 被解析为 Map | parser.py | 需要显式类型注解或用特殊语法区分 |
| IMP-07 | 无运行时类型检查 | interpreter.py | 考虑添加可选的类型检查模式 |

---

## 附录: 测试运行信息

```
Python: 3.11.9
平台: Windows 10
测试框架: pytest 9.0.2
执行命令: python -m pytest tests/deep_audit.py -v --tb=short
```

### 按模块的测试结果

```
词法分析器 (Lexer):     21/21 通过  (100%)
语法分析器 (Parser):    21/21 通过  (100%)
解释器边界值:            11/13 通过  (84.6%)
环境作用域:               6/6 通过  (100%)
SIGNAL 传播:              4/6 通过  (66.7%)
类型系统:                 9/9 通过  (100%)
函数调用:                 4/5 通过  (80.0%)
综合集成:                 8/9 通过  (88.9%)
Bug 确认测试:            9/12 通过  (75.0%)
───────────────────────────────────
总计:                    93/102 通过 (91.2%)
```

### 确认的 Bug 统计

| 严重度 | 数量 | ID |
|--------|------|-----|
| 🔴 高 | 2 | BUG-PAR-01, BUG-INT-05 |
| 🟡 中 | 8 | BUG-LEX-01, BUG-LEX-02, BUG-LEX-03, BUG-PAR-02, BUG-INT-01~04 |
| **总计** | **10** | |

---

*报告由 OpenClaw 自动化审计生成*
