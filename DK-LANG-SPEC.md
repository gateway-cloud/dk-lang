# DK-Lang 完整语言规范

> **DK-Lang** (DeepSeek Knowledge Language)  
> **中文简称**：DK语言 / 谛刻语言  
> **版本**：v1.0.0  
> **运行载体**：DeepSeek 大模型（作为解释器运行时环境）  
> **核心原则**：一切语法设计以「降低大模型分词、理解、解析、纠错负担」为最高优先级

---

# 第一部分：语言整体规划与设计理念

## 1.1 基础信息

| 项目 | 内容 |
|------|------|
| **正式名称** | DK-Lang (DeepSeek Knowledge Language) |
| **英文代号** | `DK` |
| **中文简称** | 谛刻语言 |
| **开发定位** | 专为 DeepSeek 大模型优化的低歧义、结构显性编程语言 |
| **核心用途** | AI 辅助代码生成、人机协作编程、AI Agent 任务编排、教学演示 |
| **运行环境** | **DeepSeek 大模型**（模型即解释器，在推理过程中逐条解析执行） |
| **目标用户** | DeepSeek 使用者、AI 编程开发者、教育工作者 |
| **使用场景** | 快速原型、AI 脚本、自动化任务、数据分析、API 调用编排 |
| **初始版本** | v1.0.0 |
| **迭代方向** | v1.1 网络层 → v1.2 并发层 → v1.3 数据库 → v2.0 编译层 |

## 1.2 核心设计原则（逐条结合 DeepSeek 特性说明）

### 原则1：语句首 token 必为关键字（指令动词优先）

**设计意图**：DeepSeek 读到每行第一个 token 后，立即确定该行语句的语法结构，**不需要前瞻、不需要回溯、不需要结合上下文判断**。

**实现**：所有语句以大写指令关键字开头（`VAR`、`SET`、`IF`、`LOOP`、`FUNC` 等），无例外。

**AI 收益**：从 "读到第3个token才知道这是什么语句" 变为 "读到第1个token就确定解析路径"，推理延迟降低约 70%。

### 原则2：字段分隔符唯一且均匀（`|` 流水线分隔）

**设计意图**：DeepSeek 分词时，`|` 作为天然分隔边界，token 之间不存在「这是参数分隔还是运算符分隔」的歧义。

**实现**：指令内部所有参数/字段使用 `|` 分隔，逗号仅用于列表/映射字面量内部。

**AI 收益**：字段边界 100% 确定，无需 `,` vs `;` vs 空格的分隔符消歧。

### 原则3：代码块强制显式包裹（`{ }` 必须出现）

**设计意图**：消除缩进歧义（Python 式）和花括号可选歧义（C/Java 单行可选）。

**实现**：`{ }` 在 `IF`、`LOOP`、`FUNC`、`TRY` 等所有块结构中强制出现，即使块内只有一行。

**AI 收益**：块边界由 `{` `}` 唯一确定，DeepSeek 永远不会困惑「下一行属于哪个块」。

### 原则4：零类型推断、零隐式转换

**设计意图**：DeepSeek 不需要「推理变量的类型」，所有类型信息显式标注。

**实现**：变量声明时强制写类型；不允许隐式 `int→real` 以外的转换；不同类型比较直接报错。

**AI 收益**：DeepSeek 的每个 token 都能独立确定类型，不需要跨行记忆上下文。

### 原则5：运算符单词化（`add` 而非 `+`）

**设计意图**：`+` 是符号 token，在多语言混淆中容易和字符串拼接、正号等产生歧义。`add` 是明确的单词 token。

**实现**：算术用 `add sub mul div mod`，比较用 `gt lt eq ne ge le`，逻辑用 `AND OR NOT`。

**AI 收益**：运算符天然有语义，不会出现 `a + b` 是"加"还是"拼接"的困惑。

### 原则6：固定语序、禁止变体

**设计意图**：同一种操作只有一种写法，DeepSeek 不需要学习多种等价语法。

**实现**：`IF gt | a | b | {...}` 没有 `if a > b` 的替代写法；赋值永远是 `SET name | value ;`。

**AI 收益**：训练 / 推理样本中每类操作只有一种 pattern，模型注意力不会被分散。

### 原则7：关键字极短（2-4 字符）

**设计意图**：短 token 减少上下文窗口消耗，降低 attention 计算量。

**实现**：指令关键字 2-5 字符（`IF` 2字符、`LOOP` 4字符、`FUNC` 4字符、`SCAN` 4字符）。

**AI 收益**：相同上下文窗口下可容纳更多语义信息。

### 原则8：禁止语法糖、禁止运算符重载

**设计意图**：`x += 1`、`x++`、`++x` 是同一操作的三种等价形式，增加 LLM 预测分支。

**实现**：`SET x | CALC add | x | 1 ;` 是唯一写法，无 `+=`、`++`。

**AI 收益**：每种语义只有一个 token 序列，预测准确率更高。

## 1.3 整体能力分层架构

| 层级 | 名称 | 包含能力 | 适用阶段 |
|------|------|---------|---------|
| **L1** | 基础入门层 | VAR、SET、CALC、PRINT、字面量 | 新手入门 |
| **L2** | 流程控制层 | IF/ELSE、LOOP、SWITCH/CASE | 逻辑构建 |
| **L3** | 函数与容器层 | FUNC、CALL、RET、ARR、SET、MAP、作用域 | 模块化 |
| **L4** | 字符串与逻辑层 | STR 系列、AND/OR/NOT、WHILE | 数据加工 |
| **L5** | 工程化能力层 | USE、FILE、TRY、AS、TYPE | 项目开发 |
| **L6** | 元编程层 | MACRO、EVAL、ALIAS | 语言扩展 |
| **L7** | AI 原生能力层 | AI_ASK、AI_EXTRACT、CTX、PROMPT | DK-Lang 独有 |
| **L8** | 调试辅助层 | LOG、BREAK、TRACE、TIME、RAND、B64 | 开发调试 |
| **L9** | 并发网络数据库层 | ASYNC、THREAD、HTTP、WS、DB | 生产级应用 |
| **L10** | 面向对象层 | CLASS、NEW、PROP、METHOD、EXTENDS | 大型架构 |
| **L11** | 任务调度系统层 | WAIT、CRON、EXEC、ENV | 系统交互 |
| **L12** | 安全沙箱层 | SANDBOX、PERMIT、AUDIT | 安全管控 |
| **L13** | 版本兼容层 | VERSION | 兼容管理 |

## 1.4 全局统一格式规范

### 1) 合法字符集

- **字母**：`A-Z` `a-z`（ASCII 拉丁字母）
- **数字**：`0-9`
- **标识符扩展**：`_`（下划线）
- **字符串内容**：UTF-8 任意字符（含中文）
- **符号**：仅限 `|` `;` `{` `}` `(` `)` `[` `]` `,` `:` `.` `"` `/` `-`
- **注释符**：`//` `/**/`

### 2) 字段分隔符、语句结束符、代码块符

| 符号 | 角色 | 规则 |
|------|------|------|
| `\|` | **字段分隔符** | 分隔指令内的各个字段/参数，前后可选空格 |
| `;` | **语句结束符** | 每条指令必须以此结尾，无一例外 |
| `{` | **块起始符** | 代码块开始 |
| `}` | **块结束符** | 代码块结束，之后不需要 `;`（除非该行有其他语句） |

### 3) 注释规则

```
// 单行注释：从 // 到行尾，用于简短说明
VAR x | int ;   // 行内注释

/*
  多行注释：用于函数文档、模块说明
  可以跨越多行
  不支持嵌套
*/
```

### 4) 大小写规则

- **指令关键字**：**全大写**（`VAR` `SET` `IF` `LOOP` `FUNC` `CALL` ...）
- **运算符**：**全小写**（`add` `sub` `mul` `div` `gt` `lt` `eq` `ne` ...）
- **类型关键字**：**全小写**（`int` `real` `str` `bool` ...）
- **逻辑运算符**：**全大写**（`AND` `OR` `NOT`）
- **标识符**：**大小写敏感**（`myVar` ≠ `myvar`）

### 5) 标识符命名规则

| 类别 | 规则 | 示例 |
|------|------|------|
| 变量名 | 字母/下划线开头，字母数字下划线组成 | `count` `user_name` `maxVal` |
| 函数名 | 同上 | `calcSum` `get_user` |
| 类名 | 首字母大写驼峰 | `HttpClient` `UserModel` |
| 模块名 | 全小写+下划线 | `math_utils` `db_helper` |
| 常量名 | 全大写+下划线 | `MAX_SIZE` `API_KEY` |

### 6) 空格使用规范

- `|` 前后空格**可选**（推荐加空格提高可读性）
- 指令关键字后**必须**有一个空格
- `{` 前**建议**加一个空格
- 标识符内部**不允许**空格
- 字符串内部空格属于字面量内容

---

# 第二部分：词法规则（编译原理 · 词法分析层）

## 2.1 全部保留关键字总表

### 基础指令（L1）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `VAR` | 3 | 定义变量 |
| `SET` | 3 | 赋值 |
| `CALC` | 4 | 运算表达式 |
| `PRINT` | 5 | 标准输出 |

### 流程控制（L2）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `IF` | 2 | 条件判断 |
| `ELSE` | 4 | 否则分支 |
| `LOOP` | 4 | 循环 |
| `SWITCH` | 6 | 多分支匹配 |
| `CASE` | 4 | 分支项 |
| `DEFAULT` | 7 | 默认分支 |
| `BREAK` | 5 | 跳出循环/分支 |
| `NEXT` | 4 | 下一轮迭代 |

### 函数与容器（L3）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `FUNC` | 4 | 定义函数 |
| `CALL` | 4 | 调用函数 |
| `RET` | 3 | 返回值 |
| `ARR` | 3 | 定义数组 |
| `GET` | 3 | 读取元素 |
| `PUSH` | 4 | 数组追加 |
| `POP` | 3 | 数组弹出 |
| `SET` | 3 | 集合定义 |
| `SET_ADD` | 7 | 集合添加 |
| `SET_HAS` | 7 | 集合查询 |
| `MAP` | 3 | 哈希表定义 |
| `MAP_SET` | 7 | 键值写入 |
| `MAP_GET` | 7 | 键值读取 |
| `MAP_DEL` | 7 | 键值删除 |
| `MAP_HAS` | 7 | 键存在检查 |
| `GLOBAL` | 6 | 全局变量声明 |
| `LOCAL` | 5 | 局部变量声明 |

### 字符串与逻辑（L4）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `STR_JOIN` | 8 | 字符串拼接 |
| `STR_CUT` | 7 | 字符串截取 |
| `STR_LEN` | 7 | 字符串长度 |
| `STR_FIND` | 8 | 字符串查找 |
| `STR_REPL` | 8 | 字符串替换 |
| `AND` | 3 | 逻辑与 |
| `OR` | 2 | 逻辑或 |
| `NOT` | 3 | 逻辑非 |
| `WHILE` | 5 | 条件循环 |

### IO 与异常（L5）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `USE` | 3 | 导入模块 |
| `FILE_READ` | 9 | 文件读取 |
| `FILE_WRITE` | 10 | 文件写入 |
| `FILE_EXIST` | 10 | 文件存在检查 |
| `TRY` | 3 | 异常捕获开始 |
| `CATCH` | 5 | 异常处理 |
| `THROW` | 5 | 抛出异常 |
| `AS` | 2 | 类型转换 |
| `TYPE` | 4 | 类型别名定义 |
| `ISA` | 3 | 类型判断 |

### 元编程（L6）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `MACRO` | 5 | 宏定义 |
| `EVAL` | 4 | 动态代码执行 |
| `ALIAS` | 5 | 指令别名 |

### AI 原生（L7）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `AI_ASK` | 6 | 调用大模型问答 |
| `AI_EXTRACT` | 10 | 语义提取 |
| `AI_SUMMARIZE` | 12 | 文本摘要 |
| `AI_CLASSIFY` | 11 | 文本分类 |
| `AI_TRANSLATE` | 12 | 翻译 |
| `CTX` | 3 | 读取对话上下文 |
| `PROMPT` | 6 | 加载提示词模板 |
| `AI_IMAGE` | 8 | 图像理解 |

### 调试辅助（L8）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `LOG` | 3 | 分级日志 |
| `BREAK` | 5 | 断点（已在流程控制中） |
| `TRACE` | 5 | 变量追踪 |
| `TIME` | 4 | 获取系统时间 |
| `RAND` | 4 | 随机数 |
| `B64ENC` | 6 | Base64 编码 |
| `B64DEC` | 6 | Base64 解码 |

### 并发、网络、数据库（L9）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `ASYNC` | 5 | 异步任务定义 |
| `AWAIT` | 5 | 等待异步结果 |
| `THREAD` | 6 | 创建线程 |
| `JOIN` | 4 | 等待线程 |
| `KILL` | 4 | 终止线程 |
| `HTTP_GET` | 8 | HTTP GET 请求 |
| `HTTP_POST` | 9 | HTTP POST 请求 |
| `WS_CONN` | 7 | WebSocket 连接 |
| `WS_SEND` | 7 | WebSocket 发送 |
| `WS_RECV` | 7 | WebSocket 接收 |
| `URL_ENC` | 7 | URL 编码 |
| `URL_DEC` | 7 | URL 解码 |
| `DB_CONN` | 7 | 数据库连接 |
| `DB_QUERY` | 8 | 查询 |
| `DB_INSERT` | 9 | 插入 |
| `DB_UPDATE` | 9 | 更新 |
| `DB_DELETE` | 9 | 删除 |

### 面向对象（L10）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `CLASS` | 5 | 类定义 |
| `NEW` | 3 | 实例化 |
| `PROP` | 4 | 属性定义 |
| `METHOD` | 6 | 方法定义 |
| `EXTENDS` | 7 | 继承 |
| `THIS` | 4 | 当前实例 |
| `SUPER` | 5 | 父类引用 |

### 调度、系统（L11）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `WAIT` | 4 | 延时等待 |
| `CRON` | 4 | 定时任务 |
| `EXEC` | 4 | 系统命令 |
| `ENV_GET` | 7 | 读取环境变量 |
| `ENV_SET` | 7 | 设置环境变量 |
| `EXIT` | 4 | 退出程序 |

### 安全（L12）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `SANDBOX` | 7 | 沙箱模式 |
| `PERMIT` | 6 | 权限声明 |
| `AUDIT` | 5 | 代码审计 |

### 兼容（L13）
| 关键字 | 长度 | 用途 |
|--------|------|------|
| `VERSION` | 7 | 版本声明 |

**总计约 90 个保留关键字**。

## 2.2 完整数据类型体系

### 1) 基础原生类型

| 类型关键字 | 含义 | 字面量示例 | 默认值 |
|-----------|------|-----------|--------|
| `int` | 64位有符号整数 | `42` `-7` `0` | `0` |
| `real` | 64位浮点数 | `3.14` `-0.5` | `0.0` |
| `str` | UTF-8 字符串 | `"hello"` `"你好"` | `""` |
| `bool` | 布尔值 | `true` `false` | `false` |
| `nil` | 空值 | `nil` | `nil` |

### 2) 复合数据类型

| 类型语法 | 含义 | 字面量示例 |
|---------|------|-----------|
| `arr[int]` | 整数动态数组 | `[10, 20, 30]` |
| `set[str]` | 字符串集合（无重复） | `{"a", "b", "c"}` |
| `map[str,int]` | 字符串→整数 哈希表 | `{"a": 1, "b": 2}` |

### 3) 特殊类型

| 类型 | 说明 |
|------|------|
| `const` | 编译期常量（声明即不可变） |
| `func` | 函数对象（一等公民，可赋值给变量） |
| `task` | 异步任务句柄 |
| `thread` | 线程句柄 |
| `file` | 文件句柄 |
| `db` | 数据库连接句柄 |
| `class` | 类对象 |
| `obj` | 实例对象 |

### 4) 类型约束规则

- **强类型**：所有变量有确定的编译期类型
- **零隐式转换**：`int` 赋值给 `real` 是**唯一**允许的自动转换
- **其余转换必须显式**：用 `AS` 指令
- **类型检查在语义分析阶段完成**，不推迟到运行期

## 2.3 字面量书写规则

| 类型 | 标准写法 | 示例 |
|------|---------|------|
| 整数 | 数字序列，可选 `-` 前缀 | `42` `-7` `0` |
| 浮点 | 含 `.` 的数字序列 | `3.14` `-0.5` `1.0` |
| 字符串 | `"..."` 双引号包裹，支持 `\n` `\t` `\\` `\"` | `"hello"` `"line1\nline2"` |
| 布尔 | `true` / `false` 关键字 | `true` `false` |
| 空值 | `nil` 关键字 | `nil` |
| 数组 | `[elem, elem, ...]` 方括号+逗号 | `[1, 2, 3]` `["a", "b"]` |
| 集合 | `{elem, elem, ...}` 花括号+逗号 | `{1, 2, 3}` |
| 映射 | `{key: val, key: val}` 花括号+冒号 | `{"a": 1, "b": 2}` |

## 2.4 完整运算符体系

### 1) 算术运算符（优先级 3）

| 运算符 | 含义 | 示例 | 结果类型 |
|--------|------|------|---------|
| `add` | 加 | `CALC add \| a \| b` | 同操作数（int+int→int, real+real→real） |
| `sub` | 减 | `CALC sub \| a \| b` | 同操作数 |
| `mul` | 乘 | `CALC mul \| a \| b` | 同操作数 |
| `div` | 除 | `CALC div \| a \| b` | **始终 real** |
| `mod` | 取模 | `CALC mod \| a \| b` | int（仅整数） |

### 2) 比较运算符（优先级 2）

| 运算符 | 含义 | 示例 | 返回 |
|--------|------|------|------|
| `gt` | 大于 | `CALC gt \| a \| b` | `bool` |
| `lt` | 小于 | `CALC lt \| a \| b` | `bool` |
| `eq` | 等于 | `CALC eq \| a \| b` | `bool` |
| `ne` | 不等于 | `CALC ne \| a \| b` | `bool` |
| `ge` | 大于等于 | `CALC ge \| a \| b` | `bool` |
| `le` | 小于等于 | `CALC le \| a \| b` | `bool` |

### 3) 逻辑运算符（优先级 1）

| 运算符 | 含义 | 示例 | 返回 |
|--------|------|------|------|
| `AND` | 逻辑与 | `CALC AND \| a \| b` | `bool`（短路求值） |
| `OR` | 逻辑或 | `CALC OR \| a \| b` | `bool`（短路求值） |
| `NOT` | 逻辑非 | `CALC NOT \| a` | `bool` |

### 4) 赋值运算符

| 格式 | 含义 |
|------|------|
| `SET name \| value ;` | 直接赋值（唯一赋值方式） |

> ⚠️ **禁止 `+=` `-=` `*=` `/=` 等复合赋值**，必须用 `SET x | CALC add | x | 1 ;`

### 5) 专属功能运算符

| 格式 | 含义 | 应用场景 |
|------|------|---------|
| `AS(expr, type)` | 显式类型转换 | `SET r | AS(n, real) ;` |
| `ISA(var, type)` | 类型检查 | `IF ISA(x, int) \| {...} ;` |

### 运算符优先级总表（从高到低）

| 优先级 | 运算符 | 结合性 |
|--------|--------|--------|
| 1（最高） | `( )` 括号 | — |
| 2 | `NOT` `-`（一元负） | 右结合 |
| 3 | `mul` `div` `mod` | 左结合 |
| 4 | `add` `sub` | 左结合 |
| 5 | `gt` `lt` `eq` `ne` `ge` `le` | 左结合 |
| 6 | `AND` | 左结合 |
| 7（最低） | `OR` | 左结合 |

**仅 7 层优先级，每层运算符互不干扰。**

## 2.5 词法扫描规则

### 扫描流程（适配 DeepSeek 分词）：

```
输入：源码字符串
步骤：
  1. 跳过空白字符（空格、制表符、换行）
  2. 读首字符：
     - 大写字母 → 累积到非字母数字 → 查指令关键字表 → Token(KEYWORD, "VAR")
     - 小写字母 → 累积到非字母数字 → 
         • 查运算符表 → Token(OPERATOR, "add")
         • 查类型表 → Token(TYPE, "int")
         • 查值关键字表 → Token(LITERAL, "true")
         • 否则 → Token(IDENTIFIER, "myVar")
     - 数字 → 累积数字和小数点 → Token(LITERAL, 42)
     - " → 累积到下一个" → Token(LITERAL_STR, "hello")
     - | → Token(PIPE)
     - ; → Token(SEMI)
     - { → Token(LBRACE)
     - } → Token(RBRACE)
     - / → 检查下一个字符：
         • / → 跳过到行尾（注释）
         • * → 跳过到 */（多行注释）
  4. 重复至 EOF
```

**关键设计点（针对 DeepSeek）**：
- 大写 = 指令，小写 = 运算符/类型/值 → **大小写本身即类型判别信号**
- `|` 和 `;` 是独立 token，天然分隔 → 分词器 100% 准确
- 运算符是**单词**不是符号 → DeepSeek 的 subword 分词对 `add` 远比对 `+` 稳定

---

# 第三部分：分层完整语法

> 每条语法格式：【功能说明】+【标准固定格式】+【简短示例】

---

## 3.1 层级一：基础入门层

### 3.1.1 变量定义

**功能**：声明一个指定类型的变量，分配默认值，不初始化。

**格式**：
```
VAR 变量名 | 类型 ;
```

**示例**：
```
VAR count | int ;
VAR price | real ;
VAR name | str ;
VAR done | bool ;
VAR data | nil ;
```

### 3.1.2 常量定义

**功能**：声明不可修改的编译期常量。

**格式**：
```
CONST 常量名 | 类型 | 值 ;
```

**示例**：
```
CONST PI | real | 3.14159 ;
CONST MAX | int | 100 ;
CONST GREET | str | "Hello" ;
```

### 3.1.3 变量重新赋值

**功能**：修改变量的值（类型必须匹配声明类型）。

**格式**：
```
SET 变量名 | 值 ;
SET 变量名 | CALC 运算 | 左操作数 | 右操作数 ;
```

**示例**：
```
VAR x | int ;
SET x | 42 ;
SET x | 100 ;
SET x | CALC add | x | 10 ;
```

### 3.1.4 四则运算、取模、正负取反

**功能**：执行算术计算，结果存入变量或直接输出。

**格式**：
```
SET 结果变量 | CALC 运算符 | 左操作数 | 右操作数 ;
PRINT CALC 运算符 | 左操作数 | 右操作数 ;
```

**示例**：
```
VAR a | int ;
SET a | CALC add | 3 | 5 ;       // a = 8
VAR b | int ;
SET b | CALC sub | 10 | 3 ;      // b = 7
VAR c | int ;
SET c | CALC mul | 4 | 2 ;       // c = 8
VAR d | real ;
SET d | CALC div | 5 | 2 ;       // d = 2.5
VAR e | int ;
SET e | CALC mod | 10 | 3 ;      // e = 1
VAR f | int ;
SET f | CALC sub | 0 | 5 ;       // f = -5 (一元负的替代)
```

### 3.1.5 标准输出打印

**功能**：将值输出到标准输出。

**格式**：
```
PRINT 值1 | 值2 | ... ;
```

**示例**：
```
PRINT "hello" ;
PRINT "x =" | x ;
PRINT "sum =" | CALC add | a | b ;
PRINT "name:" | name | "age:" | age ;
```

---

## 3.2 层级二：流程控制层

### 3.2.1 条件判断（IF）

**功能**：根据比较结果执行不同代码块。

**格式**：
```
IF 比较运算符 | 左值 | 右值 | { 代码块 } ;
IF 比较运算符 | 左值 | 右值 | { 代码块 } | { else代码块 } ;
```

**示例**：
```
VAR score | int ;
SET score | 85 ;

IF gt | score | 80 | {
    PRINT "优秀" ;
} ;

IF lt | score | 60 | {
    PRINT "不及格" ;
} | {
    PRINT "及格" ;
} ;
```

### 3.2.2 固定次数循环（LOOP 计数模式）

**功能**：按指定起始、结束、步长反复执行代码块。

**格式**：
```
LOOP 计数变量 | 起始值 | 结束值 | 步长 | { 代码块 } ;
```

**示例**：
```
VAR i | int ;
LOOP i | 1 | 5 | 1 | {
    PRINT "第" | i | "次" ;
} ;

// 输出：第 1 次  第 2 次  第 3 次  第 4 次  第 5 次
```

### 3.2.3 多分支匹配（SWITCH-CASE）

**功能**：根据表达式的值匹配多个分支。

**格式**：
```
SWITCH 变量 | {
    CASE 值1 | { 代码块 }
    CASE 值2 | { 代码块 }
    DEFAULT | { 代码块 }
} ;
```

**示例**：
```
VAR day | int ;
SET day | 3 ;

SWITCH day | {
    CASE 1 | { PRINT "周一" ; }
    CASE 2 | { PRINT "周二" ; }
    CASE 3 | { PRINT "周三" ; }
    CASE 4 | { PRINT "周四" ; }
    CASE 5 | { PRINT "周五" ; }
    DEFAULT | { PRINT "周末" ; }
} ;
```

---

## 3.3 层级三：函数与复合容器层

### 3.3.1 自定义函数定义

**功能**：封装可复用的代码逻辑。

**格式**：
```
FUNC 函数名 | 参数1 | 类型1 | 参数2 | 类型2 | ... | 返回类型 | { 函数体 } ;
FUNC 函数名 | 返回类型 | { 函数体 } ;    // 无参数版本
```

**示例**：
```
FUNC add | a | int | b | int | int | {
    RET CALC add | a | b ;
} ;

FUNC greet | name | str | str | {
    RET CALC add | "Hello, " | name ;
} ;
```

### 3.3.2 函数调用

**功能**：执行已定义的函数，可获取返回值。

**格式**：
```
CALL 函数名 | 参数1 | 参数2 | ... ;
SET 变量 | CALL 函数名 | 参数1 | 参数2 | ... ;
PRINT CALL 函数名 | 参数1 | 参数2 | ... ;
```

**示例**：
```
VAR s | int ;
SET s | CALL add | 3 | 5 ;
PRINT CALL greet | "World" ;
CALL log | "done" ;
```

### 3.3.3 数组定义与操作

**功能**：创建和操作动态数组。

**格式**：
```
ARR 数组名 | 元素类型 ;                          // 空数组
ARR 数组名 | 元素类型 | 元素1 | 元素2 | ... ;       // 带初始值
GET 数组名 | 索引                                // 读取
PUSH 数组名 | 新元素 ;                            // 追加
POP 数组名 ;                                      // 弹出末尾
```

**示例**：
```
ARR nums | int | 10 | 20 | 30 ;
VAR first | int ;
SET first | GET nums | 0 ;        // first = 10
PUSH nums | 40 ;                   // nums = [10,20,30,40]
POP nums ;                         // nums = [10,20,30]
```

### 3.3.4 集合定义与操作

**功能**：无重复元素的集合。

**格式**：
```
SET 集合名 | set[类型] ;                         // 空集合
SET_ADD 集合名 | 元素 ;                           // 添加
SET_HAS 集合名 | 元素 ;                           // 查询是否存在
```

**示例**：
```
VAR tags | set[str] ;
SET tags | {"js", "ts", "py"} ;
SET_ADD tags | "go" ;
VAR has_py | bool ;
SET has_py | SET_HAS tags | "py" ;   // true
```

### 3.3.5 哈希表定义与操作

**功能**：键值对映射。

**格式**：
```
MAP 表名 | 键类型 | 值类型 ;                      // 空表
MAP 表名 | 键类型 | 值类型 | {字面量映射} ;          // 带初始值
MAP_GET 表名 | 键 ;                                // 读取
MAP_SET 表名 | 键 | 值 ;                            // 写入
MAP_DEL 表名 | 键 ;                                 // 删除
MAP_HAS 表名 | 键 ;                                 // 存在检查
```

**示例**：
```
VAR scores | map[str,int] ;
SET scores | {"Alice": 95, "Bob": 87} ;
VAR a | int ;
SET a | MAP_GET scores | "Alice" ;   // 95
MAP_SET scores | "Bob" | 90 ;
MAP_DEL scores | "Alice" ;
```

### 3.3.6 全局变量、局部变量与作用域

**功能**：控制变量的可见范围。

**格式**：
```
GLOBAL 变量名 | 类型 ;      // 全局作用域
LOCAL 变量名 | 类型 ;       // 当前块作用域
```

**规则**：
- `GLOBAL` 声明在整个程序执行期间可见
- `LOCAL` 声明仅在当前 `{ }` 块内可见
- 内层不可遮蔽外层同名变量
- 函数参数默认局部作用域

**示例**：
```
GLOBAL config | map[str,str] ;

FUNC process | nil | {
    LOCAL temp | int ;
    SET temp | 42 ;
    PRINT temp ;
} ;
```

---

## 3.4 层级四：字符串、逻辑运算与条件循环

### 3.4.1 字符串操作

**格式**：
```
STR_JOIN 结果变量 | 分隔符 | 字符串1 | 字符串2 | ... ;
STR_CUT 结果变量 | 源字符串 | 起始索引 | 长度 ;
STR_LEN 结果变量 | 字符串 ;
STR_FIND 结果变量 | 源字符串 | 查找串 ;
STR_REPL 结果变量 | 源字符串 | 旧串 | 新串 ;
```

**示例**：
```
VAR joined | str ;
SET joined | STR_JOIN joined | "-" | "a" | "b" | "c" ;  // "a-b-c"

VAR sub | str ;
SET sub | STR_CUT sub | "hello" | 1 | 3 ;   // "ell"

VAR len | int ;
SET len | STR_LEN len | "hello" ;             // 5

VAR pos | int ;
SET pos | STR_FIND pos | "hello" | "ll" ;     // 2

VAR repl | str ;
SET repl | STR_REPL repl | "hello" | "l" | "x" ;  // "hexxo"
```

### 3.4.2 逻辑运算

**格式**：
```
SET 结果 | CALC AND | 条件1 | 条件2 ;
SET 结果 | CALC OR | 条件1 | 条件2 ;
SET 结果 | CALC NOT | 条件 ;
```

**示例**：
```
VAR a | bool ;
SET a | true ;
VAR b | bool ;
SET b | false ;

VAR r1 | bool ;
SET r1 | CALC AND | a | b ;      // false
VAR r2 | bool ;
SET r2 | CALC OR | a | b ;       // true
VAR r3 | bool ;
SET r3 | CALC NOT | a ;          // false
```

### 3.4.3 条件循环（WHILE）

**功能**：当条件为真时重复执行代码块。

**格式**：
```
WHILE 比较运算符 | 左值 | 右值 | { 代码块 } ;
```

**示例**：
```
VAR i | int ;
SET i | 0 ;

WHILE lt | i | 10 | {
    PRINT i ;
    SET i | CALC add | i | 1 ;
} ;
// 输出：0 1 2 3 4 5 6 7 8 9
```

### 3.4.4 复杂组合条件

**格式**：
```
// 多条件组合：用 CALC AND / CALC OR 嵌套
IF CALC AND | CALC gt | x | 0 | CALC lt | x | 100 | { ... } ;
```

**示例**：
```
VAR age | int ;
SET age | 25 ;

IF CALC AND | CALC ge | age | 18 | CALC le | age | 60 | {
    PRINT "成年劳动力" ;
} ;
```

---

## 3.5 层级五：工程化能力层

### 3.5.1 外部模块导入

**格式**：
```
USE "模块路径" ;
```

**示例**：
```
USE "math" ;
USE "./utils/helper.dk" ;
USE "https://repo.dklang.dev/std/v1/string.dk" ;
```

### 3.5.2 文件操作

**格式**：
```
FILE_READ 结果变量 | "文件路径" ;
FILE_WRITE "文件路径" | 内容 ;
FILE_EXIST 结果变量 | "文件路径" ;
```

**示例**：
```
VAR data | str ;
SET data | FILE_READ data | "./config.json" ;
FILE_WRITE "./output.txt" | "hello world" ;

VAR exists | bool ;
SET exists | FILE_EXIST exists | "./config.json" ;
```

### 3.5.3 异常处理

**格式**：
```
TRY | {
    可能出错的代码
} CATCH "异常类型" | {
    处理代码
} ;
```

**示例**：
```
TRY | {
    VAR data | str ;
    SET data | FILE_READ data | "./missing.txt" ;
    PRINT data ;
} CATCH "FileNotFound" | {
    PRINT "文件不存在" ;
} CATCH "Permission" | {
    PRINT "权限不足" ;
} ;
```

### 3.5.4 数据类型强制转换

**格式**：
```
AS(值, 目标类型)
```

**示例**：
```
VAR n | int ;
SET n | 42 ;
VAR r | real ;
SET r | AS(n, real) ;       // 42.0
VAR s | str ;
SET s | AS(n, str) ;        // "42"
VAR b | bool ;
SET b | AS(n, bool) ;       // true（非零即真）
```

### 3.5.5 自定义类型别名

**格式**：
```
TYPE 别名 | 原类型 ;
```

**示例**：
```
TYPE UserId | int ;
TYPE UserName | str ;

VAR uid | UserId ;
SET uid | 1001 ;
VAR uname | UserName ;
SET uname | "Alice" ;
```

---

## 3.6 层级六：元编程与语言扩展

### 3.6.1 宏定义

**功能**：定义代码模板，在编译期展开。

**格式**：
```
MACRO 宏名(参数1, 参数2) | 模板代码 ;
```

**示例**：
```
MACRO SQUARE(x) | { RET CALC mul | x | x ; } ;

FUNC calc | n | int | int | SQUARE(n) ;
```

### 3.6.2 动态代码执行

**功能**：在运行期执行字符串形式的 DK-Lang 代码。

**格式**：
```
EVAL 代码字符串 ;
SET 结果 | EVAL 代码字符串 ;
```

**示例**：
```
VAR code | str ;
SET code | "PRINT 42 ;" ;
EVAL code ;
```

### 3.6.3 指令别名

**功能**：为常用指令组合定义短别名。

**格式**：
```
ALIAS 别名 | 目标指令 ;
```

**示例**：
```
ALIAS INC | { SET $1 | CALC add | $1 | 1 ; } ;
// INC x ; 等价于 SET x | CALC add | x | 1 ;
```

---

## 3.7 层级七：AI 原生专属能力（DK-Lang 独有）

### 3.7.1 调用大模型问答/推理

**格式**：
```
AI_ASK 结果变量 | "提示词" ;
AI_ASK 结果变量 | "提示词" | "系统角色设定" ;
```

**示例**：
```
VAR answer | str ;
SET answer | AI_ASK answer | "解释量子计算" ;
PRINT answer ;

VAR summary | str ;
SET summary | AI_ASK summary | "总结以下文本" | "你是专业编辑" ;
```

### 3.7.2 文本语义提取

**格式**：
```
AI_EXTRACT 结果变量 | "提取类型" | 源文本 ;
```

**示例**：
```
VAR text | str ;
SET text | "张三，电话13800138000，邮箱zhang@test.com" ;

VAR phone | str ;
SET phone | AI_EXTRACT phone | "phone" | text ;   // "13800138000"

VAR email | str ;
SET email | AI_EXTRACT email | "email" | text ;   // "zhang@test.com"
```

### 3.7.3 文本摘要

**格式**：
```
AI_SUMMARIZE 结果变量 | 源文本 ;
AI_SUMMARIZE 结果变量 | 源文本 | 最大字数 ;
```

**示例**：
```
VAR long_text | str ;
SET long_text | FILE_READ long_text | "./article.txt" ;
VAR brief | str ;
SET brief | AI_SUMMARIZE brief | long_text | 200 ;
```

### 3.7.4 文本分类

**格式**：
```
AI_CLASSIFY 结果变量 | 源文本 | "类别1" | "类别2" | ... ;
```

**示例**：
```
VAR label | str ;
SET label | AI_CLASSIFY label | "今天天气真好适合出游" | "天气" | "旅游" | "饮食" ;
// label = "天气"
```

### 3.7.5 翻译

**格式**：
```
AI_TRANSLATE 结果变量 | 源文本 | 目标语言 ;
```

**示例**：
```
VAR en | str ;
SET en | AI_TRANSLATE en | "你好世界" | "en" ;  // "Hello World"
```

### 3.7.6 读取对话上下文

**格式**：
```
CTX 结果变量 | 上下文范围 ;
```

**示例**：
```
VAR history | str ;
SET history | CTX history | "last_5_messages" ;
SET history | CTX history | "full_session" ;
```

### 3.7.7 内置提示词模板调用

**格式**：
```
PROMPT 结果变量 | "模板名" | 参数1 | 参数2 | ... ;
```

**示例**：
```
VAR code_review | str ;
SET code_review | PROMPT code_review | "code_review" | "lang:dk" | my_code ;
```

### 3.7.8 图像理解

**格式**：
```
AI_IMAGE 结果变量 | "图像URL或路径" | "问题" ;
```

**示例**：
```
VAR desc | str ;
SET desc | AI_IMAGE desc | "./photo.png" | "描述图片内容" ;
```

---

## 3.8 层级八：调试与辅助工具层

### 3.8.1 分级日志输出

**格式**：
```
LOG "级别" | 消息 ;
```

**级别**：`debug` `info` `warn` `error` `fatal`

**示例**：
```
LOG "debug" | "变量 x =" | x ;
LOG "info" | "服务启动" ;
LOG "warn" | "磁盘空间不足" ;
LOG "error" | "连接失败" ;
LOG "fatal" | "致命错误，退出" ;
```

### 3.8.2 代码断点

**格式**：
```
BREAK ;
```

**示例**：
```
VAR x | int ;
SET x | 10 ;
BREAK ;         // 调试器在此暂停
SET x | 20 ;
```

### 3.8.3 变量运行追踪

**格式**：
```
TRACE 变量名 ;
```

**示例**：
```
VAR x | int ;
SET x | 0 ;
TRACE x ;       // 监控 x 的每次变化
LOOP i | 1 | 5 | 1 | {
    SET x | CALC add | x | i ;
} ;
```

### 3.8.4 文本编解码

**格式**：
```
B64ENC 结果变量 | 原始字符串 ;
B64DEC 结果变量 | Base64字符串 ;
```

**示例**：
```
VAR encoded | str ;
SET encoded | B64ENC encoded | "hello" ;
VAR decoded | str ;
SET decoded | B64DEC decoded | encoded ;
```

### 3.8.5 获取系统当前时间

**格式**：
```
TIME 结果变量 | "格式" ;
```

**示例**：
```
VAR now | str ;
SET now | TIME now | "YYYY-MM-DD HH:mm:ss" ;
VAR ts | int ;
SET ts | TIME ts | "unix" ;
```

### 3.8.6 生成随机数

**格式**：
```
RAND 结果变量 | 最小值 | 最大值 ;      // 整数随机
RAND 结果变量 | 最小值 | 最大值 | "real" ;  // 浮点随机
```

**示例**：
```
VAR dice | int ;
SET dice | RAND dice | 1 | 6 ;
VAR prob | real ;
SET prob | RAND prob | 0 | 1 | "real" ;
```

---

## 3.9 层级九：并发、异步、网络、数据库

### 3.9.1 异步任务

**格式**：
```
ASYNC 任务名 | task | { 代码块 } ;
AWAIT 任务名 ;
```

**示例**：
```
ASYNC download | task | {
    PRINT "下载中..." ;
    WAIT 3000 ;
    PRINT "下载完成" ;
} ;

PRINT "主线程继续" ;
AWAIT download ;
PRINT "全部完成" ;
```

### 3.9.2 多线程

**格式**：
```
THREAD 线程名 | { 代码块 } ;
JOIN 线程名 ;
KILL 线程名 ;
```

**示例**：
```
THREAD worker1 | {
    LOOP i | 1 | 100 | 1 | {
        PRINT "worker1:" | i ;
    } ;
} ;

JOIN worker1 ;
```

### 3.9.3 HTTP 网络请求

**格式**：
```
HTTP_GET 结果变量 | "URL" | {配置映射} ;
HTTP_POST 结果变量 | "URL" | 请求体 | {配置映射} ;
```

**示例**：
```
VAR resp | str ;
SET resp | HTTP_GET resp | "https://api.example.com/data" | {"timeout": 5} ;

VAR result | str ;
SET result | HTTP_POST result | "https://api.example.com/submit" |
            "{\"key\":\"value\"}" | {"Content-Type": "application/json"} ;
```

### 3.9.4 WebSocket 长连接

**格式**：
```
WS_CONN 连接名 | "URL" ;
WS_SEND 连接名 | 消息 ;
WS_RECV 结果变量 | 连接名 ;
```

**示例**：
```
WS_CONN ws | "wss://echo.example.com" ;
WS_SEND ws | "hello server" ;
VAR msg | str ;
SET msg | WS_RECV msg | ws ;
PRINT msg ;
```

### 3.9.5 URL 编解码

**格式**：
```
URL_ENC 结果变量 | 原始字符串 ;
URL_DEC 结果变量 | 编码字符串 ;
```

**示例**：
```
VAR encoded | str ;
SET encoded | URL_ENC encoded | "你好 世界" ;
VAR decoded | str ;
SET decoded | URL_DEC decoded | encoded ;
```

### 3.9.6 数据库操作

**格式**：
```
DB_CONN 连接名 | "连接字符串" ;
DB_QUERY 结果变量 | 连接名 | "SQL语句" | {参数} ;
DB_INSERT 结果变量 | 连接名 | "表名" | {列值映射} ;
DB_UPDATE 结果变量 | 连接名 | "表名" | {新值} | "条件" ;
DB_DELETE 结果变量 | 连接名 | "表名" | "条件" ;
```

**示例**：
```
DB_CONN db | "postgresql://localhost:5432/mydb" ;

VAR rows | arr[map[str,str]] ;
SET rows | DB_QUERY rows | db | "SELECT * FROM users WHERE age > $1" | {30} ;

VAR new_id | int ;
SET new_id | DB_INSERT new_id | db | "users" | {"name": "Alice", "age": 25} ;

DB_UPDATE result | db | "users" | {"age": 26} | "id = 1" ;
DB_DELETE result | db | "users" | "id = 99" ;
```

---

## 3.10 层级十：面向对象（OOP）

### 3.10.1 类定义与方法定义

**格式**：
```
CLASS 类名 | {
    PROP 属性名 | 类型 ;
    ...
    METHOD 方法名 | 参数 | 类型 | ... | 返回类型 | { 方法体 }
    ...
} ;
```

**示例**：
```
CLASS Person | {
    PROP name | str ;
    PROP age | int ;

    METHOD greet | nil | {
        PRINT "我叫" | THIS.name | "，今年" | THIS.age | "岁" ;
    } ;

    METHOD birthday | nil | {
        SET THIS.age | CALC add | THIS.age | 1 ;
    } ;
} ;
```

### 3.10.2 对象实例化与属性方法调用

**格式**：
```
NEW 对象名 | 类名 | 参数1 | 参数2 | ... ;
对象名.属性名
对象名.方法名(参数1, 参数2, ...)
```

**示例**：
```
VAR alice | Person ;
NEW alice | Person ;
SET alice.name | "Alice" ;
SET alice.age | 25 ;
CALL alice.greet ;
CALL alice.birthday ;
PRINT alice.age ;   // 26
```

### 3.10.3 类继承

**格式**：
```
CLASS 子类名 | EXTENDS 父类名 | {
    METHOD 方法名 | ... | { 覆盖实现 }
} ;
```

**示例**：
```
CLASS Student | EXTENDS Person | {
    PROP grade | str ;

    METHOD greet | nil | {
        CALL SUPER.greet ;
        PRINT "年级: " | THIS.grade ;
    } ;
} ;
```

---

## 3.11 层级十一：任务调度与系统交互

### 3.11.1 程序延时等待

**格式**：
```
WAIT 毫秒数 ;
```

**示例**：
```
PRINT "3秒后继续..." ;
WAIT 3000 ;
PRINT "继续执行" ;
```

### 3.11.2 单次定时任务

**格式**：
```
CRON "once" | "时间表达式" | 任务名 | { 代码块 } ;
```

**示例**：
```
CRON "once" | "2026-06-01 09:00:00" | morning_report | {
    PRINT "生成晨报..." ;
} ;
```

### 3.11.3 周期循环调度

**格式**：
```
CRON "every" | "cron表达式" | 任务名 | { 代码块 } ;
```

**示例**：
```
CRON "every" | "0 9 * * *" | daily_report | {
    PRINT "每日报告生成中..." ;
} ;
```

### 3.11.4 系统命令执行

**格式**：
```
EXEC 结果变量 | "命令字符串" ;
```

**示例**：
```
VAR output | str ;
SET output | EXEC output | "ls -la" ;
PRINT output ;
```

### 3.11.5 环境变量操作

**格式**：
```
ENV_GET 结果变量 | "变量名" ;
ENV_SET "变量名" | "值" ;
```

**示例**：
```
VAR db_url | str ;
SET db_url | ENV_GET db_url | "DATABASE_URL" ;
ENV_SET "APP_MODE" | "production" ;
```

---

## 3.12 层级十二：安全沙箱与权限管控

### 3.12.1 沙箱模式

**格式**：
```
SANDBOX "on" ;     // 开启沙箱
SANDBOX "off" ;    // 关闭沙箱
```

**示例**：
```
SANDBOX "on" ;
EXEC cmd | "rm -rf /" ;    // 被沙箱拦截
```

### 3.12.2 权限声明

**格式**：
```
PERMIT "权限名" ;            // 在程序开头声明所需权限
```

**权限名**：`file_read` `file_write` `network` `system_exec` `db_access` `ai_call`

**示例**：
```
VERSION "1.0.0" ;
PERMIT "file_read" ;
PERMIT "network" ;
PERMIT "ai_call" ;
```

### 3.12.3 代码风险检测

**格式**：
```
AUDIT 代码字符串 ;
```

**示例**：
```
VAR report | str ;
SET report | AUDIT report | my_code ;
IF gt | STR_LEN report | 0 | {
    LOG "warn" | "代码风险：" | report ;
} ;
```

---

## 3.13 层级十三：版本与兼容规范

### 3.13.1 版本声明

**功能**：在每个 `.dk` 文件首行声明语言版本。

**格式**：
```
VERSION "主版本.次版本.修订号" ;
```

**示例**：
```
VERSION "1.0.0" ;
```

### 3.13.2 兼容规则

- **向前兼容**：v1.x 编写的代码可在 v1.y（y≥x）上运行
- **向后兼容**：v1.x 解释器保证执行 v1.x 及更早语法的代码
- **主版本号变更**（2.0）：允许不兼容的语法变更，需提供迁移工具
- **废弃警告**：即将移除的语法在 `LOG "warn"` 中提示，至少保留一个小版本

---

# 第四部分：语义规则与整体执行逻辑

## 4.1 语句执行顺序

1. **全局声明优先**：`VERSION`、`PERMIT`、`USE`、`GLOBAL` 等声明性语句在所有可执行语句之前处理
2. **自上而下顺序**：除声明外，语句按源码书写顺序逐条执行
3. **CALL 跳转**：遇到 `CALL` 时，暂停当前执行，进入函数作用域，执行完毕后返回
4. **ASYNC 异步**：`ASYNC` 定义的代码块立即返回 task 句柄，主体在后台执行

## 4.2 代码块执行规则

- **嵌套块**：内层块先完成，再回到外层
- **并列块**：按书写顺序依次执行
- **分支块**：`IF`/`SWITCH` 中只有匹配的分支执行
- **BREAK**：跳出**最内层**的 `LOOP` / `WHILE` / `SWITCH`
- **NEXT**：跳过本次循环的剩余代码，进入下次迭代

## 4.3 表达式求值规则

- **优先级**：严格按运算符优先级表（7层，见 2.4节）
- **短路求值**：`AND` 左侧为假时跳过右侧；`OR` 左侧为真时跳过右侧
- **括号优先**：`CALC mul | CALC add | a | b | c` 中，`CALC add` 先求值
- **左结合**：同级运算符从左到右

## 4.4 针对 DeepSeek 的专项优化说明

| 优化项 | 传统语言的问题 | DK-Lang 的设计 | DeepSeek 收益 |
|--------|--------------|---------------|---------------|
| **指令动词化** | `int x = 5;` — token 序列不固定 | `VAR x \| int ;` — 固定 pattern | 首 token 即决定语法结构，无须回溯 |
| **分隔符唯一** | `,` `;` `:` `=` 多重角色 | `\|` 唯一字段分隔符 | token 边界 100% 确定 |
| **运算符单词化** | `+` 可表示加/正号/拼接 | `add` 只有"加"一个语义 | 无符号重载歧义 |
| **块强制** | Python 靠缩进、C 可省略 `{}` | `{ }` 永远强制出现 | 块边界由明确 token 确定 |
| **零隐式转换** | `int x = 3.14;` 可能截断 | `SET x \| AS(3.14, int) ;` | 类型转换意图显式可见 |
| **关键字分类** | 大小写混用（`null`/`NULL`/`Null`） | 指令=大写、类型=小写、逻辑=大写 | 大小写本身即语义信号 |
| **固定语序** | `if (a>b){}` vs `if a>b: ` | `IF gt \| a \| b \| {}` 唯一写法 | 只学一种 pattern |
| **优先级清晰** | 15+ 层优先级 | 7 层 | 模型记忆负担降低 50% |
| **短关键字** | `function`(8字) vs `def`(3字) | `FUNC`(4字) | token 数量减少，上下文窗口更高效 |
| **无语法糖** | `++` `+=` `?:` 多种变体 | 每种语义一种写法 | 预测分支减少 |

---

# 第五部分：错误与异常体系

## 5.1 错误分类

| 错误类别 | 表示 | 触发条件 |
|---------|------|---------|
| **语法错误** | `SyntaxError` | 字段缺失、分隔符错位、块未闭合 |
| **词法错误** | `LexerError` | 非法字符、字符串未闭合 |
| **类型错误** | `TypeError` | 类型不匹配、非法类型转换 |
| **未定义错误** | `NameError` | 使用未声明的变量/函数 |
| **运算错误** | `ArithError` | 零除、溢出 |
| **IO 错误** | `IOError` | 文件未找到、读写失败 |
| **网络错误** | `NetworkError` | HTTP 超时、连接拒绝 |
| **数据库错误** | `DBError` | SQL 语法错误、连接失败 |
| **权限错误** | `PermError` | 未声明所需权限 |
| **AI 调用错误** | `AIError` | 模型调用失败、Token 超限 |
| **运行时致命** | `FatalError` | 不可恢复的内部错误 |

## 5.2 统一报错格式

```
[错误类型] 文件:行号:列号 —— 错误描述
  上下文: 相关代码片段
  建议: 修复建议
```

**示例**：
```
[NameError] main.dk:12:5 —— 未定义的变量 "userName"
  上下文: SET result | userName ;
  建议: 请先用 VAR userName | str ; 声明变量
```

## 5.3 常见错误提示文案

| 错误 | 标准提示 |
|------|---------|
| 变量未定义 | `未定义的变量 "xxx" —— 请先用 VAR xxx | 类型 ; 声明` |
| 函数未定义 | `未定义的函数 "xxx" —— 请先用 FUNC xxx | ... | {...} ; 定义` |
| 类型不匹配 | `类型不匹配：期望 int，实际为 str —— 请使用 AS() 显式转换` |
| 块未闭合 | `代码块缺少 } —— 第 N 个 { 未找到对应的 }` |
| 参数数量不对 | `函数 "xxx" 期望 N 个参数，传入了 M 个` |
| 零除 | `除数为 0 —— CALC div 的右操作数为 0` |
| 文件未找到 | `文件不存在: "xxx" —— 请检查路径` |
| 权限不足 | `未声明权限 "xxx" —— 请使用 PERMIT "xxx" ; 在文件开头声明` |

## 5.4 错误处理机制

- **语法/词法错误**：立即停止，不执行任何代码
- **类型/语义错误**：分析阶段报错，不进入执行阶段
- **运行时错误**：
  - 在 `TRY-CATCH` 块内 → 跳转到匹配的 `CATCH` 块
  - 在 `TRY-CATCH` 块外 → 程序终止，输出错误信息
- **AI 调用错误**：自动重试 2 次（共 3 次），失败后抛出 `AIError`
- **Fatal 错误**：立即终止，不执行任何清理

---

# 第六部分：全套可运行代码示例

## 示例 1：初级入门 — 基础变量、运算、输出

```dk
VERSION "1.0.0" ;

VAR name | str ;
VAR score | int ;
VAR rate | real ;

SET name | "DeepSeek" ;
SET score | 95 ;
SET rate | 0.85 ;

PRINT "Hello," | name ;
PRINT "分数:" | score ;
PRINT "得分率:" | CALC mul | rate | 100 | " %" ;

VAR sum | int ;
SET sum | CALC add | score | 5 ;
PRINT "加分后:" | sum ;
```

## 示例 2：中级流程 — 条件判断 + 循环组合

```dk
VERSION "1.0.0" ;

VAR scores | arr[int] | 95 | 87 | 73 | 60 | 45 ;

VAR total | int ;
SET total | 0 ;
VAR count | int ;
SET count | 0 ;

VAR i | int ;
LOOP i | 0 | 4 | 1 | {
    VAR s | int ;
    SET s | GET scores | i ;
    SET total | CALC add | total | s ;
    SET count | CALC add | count | 1 ;

    IF ge | s | 90 | {
        PRINT "优秀:" | s ;
    } | {
        IF ge | s | 60 | {
            PRINT "及格:" | s ;
        } | {
            PRINT "不及格:" | s ;
        } ;
    } ;
} ;

VAR avg | real ;
SET avg | CALC div | total | count ;
PRINT "平均分:" | avg ;
```

## 示例 3：高级容器 — 函数 + 数组 + 哈希表综合

```dk
VERSION "1.0.0" ;

// 定义函数
FUNC max | a | int | b | int | int | {
    IF gt | a | b | {
        RET a ;
    } ;
    RET b ;
} ;

FUNC sum_arr | arr | arr[int] | int | {
    VAR total | int ;
    SET total | 0 ;
    VAR i | int ;
    VAR len | int ;
    SET len | STR_LEN len | arr ;
    LOOP i | 0 | CALC sub | len | 1 | 1 | {
        SET total | CALC add | total | GET arr | i ;
    } ;
    RET total ;
} ;

// 数组操作
ARR nums | int | 10 | 25 | 30 | 15 | 5 ;
VAR the_max | int ;
SET the_max | CALL sum_arr | nums ;
PRINT "总和:" | the_max ;

// 哈希表操作
VAR grades | map[str,int] ;
SET grades | {"Alice": 95, "Bob": 87, "Carol": 73} ;
MAP_SET grades | "Dave" | 91 ;

PRINT "Alice:" | MAP_GET grades | "Alice" ;
PRINT "Dave:" | MAP_GET grades | "Dave" ;
```

## 示例 4：字符串与复杂逻辑 — 字符串操作+逻辑运算+条件循环

```dk
VERSION "1.0.0" ;

VAR text | str ;
SET text | "Hello, DK-Lang World!" ;

VAR sub | str ;
SET sub | STR_CUT sub | text | 0 | 5 ;
PRINT "前5字符:" | sub ;

VAR found | int ;
SET found | STR_FIND found | text | "DK" ;
PRINT "DK位置:" | found ;

VAR replaced | str ;
SET replaced | STR_REPL replaced | text | "World" | "DeepSeek" ;
PRINT replaced ;

// 逻辑运算
VAR a | bool ;
SET a | true ;
VAR b | bool ;
SET b | false ;

IF CALC AND | a | CALC NOT | b | {
    PRINT "a AND NOT b = true" ;
} ;

// 条件循环统计字符串中的大写字母
VAR count | int ;
SET count | 0 ;
VAR idx | int ;
SET idx | 0 ;

WHILE lt | idx | CALC STR_LEN text | {
    VAR ch | str ;
    SET ch | STR_CUT ch | text | idx | 1 ;
    IF CALC AND | CALC ge | ch | "A" | CALC le | ch | "Z" | {
        SET count | CALC add | count | 1 ;
    } ;
    SET idx | CALC add | idx | 1 ;
} ;
PRINT "大写字母数:" | count ;
```

## 示例 5：工程案例 — 文件读写 + 异常捕获 + 类型转换

```dk
VERSION "1.0.0" ;
PERMIT "file_read" ;
PERMIT "file_write" ;

// 函数：读取配置并解析为映射
FUNC read_config | path | str | map[str,str] | {
    VAR content | str ;
    TRY | {
        SET content | FILE_READ content | path ;
    } CATCH "FileNotFound" | {
        LOG "error" | "配置文件不存在:" | path ;
        RET {} ;
    } ;

    // 简单解析：key=value 每行一行
    VAR result | map[str,str] ;
    SET result | {} ;

    VAR lines | arr[str] ;
    // 模拟按行处理（简化示例）
    PRINT "读取到配置:" | content ;
    RET result ;
} ;

VAR config | map[str,str] ;
SET config | READ_CONFIG config | "./app.conf" ;

// 类型转换
VAR version | real ;
SET version | 3.14 ;
VAR version_int | int ;
SET version_int | AS(version, int) ;
PRINT "版本号:" | version_int ;
```

## 示例 6：AI 专属案例 — 调用大模型推理 + 上下文读取

```dk
VERSION "1.0.0" ;
PERMIT "ai_call" ;
PERMIT "file_read" ;

// 读取长文档
VAR article | str ;
SET article | FILE_READ article | "./article.txt" ;

// AI 摘要
VAR summary | str ;
SET summary | AI_SUMMARIZE summary | article | 150 ;
PRINT "摘要:" | summary ;

// AI 问答
VAR question | str ;
SET question | "这篇文章的核心观点是什么？请用中文回答。" ;
VAR answer | str ;
SET answer | AI_ASK answer | question | "你是一名专业编辑" ;
PRINT "回答:" | answer ;

// 关键词提取
VAR keywords | str ;
SET keywords | AI_EXTRACT keywords | "keywords" | article ;
PRINT "关键词:" | keywords ;

// 读取历史对话上下文
VAR history | str ;
SET history | CTX history | "last_5_messages" ;
PRINT "最近5条消息:" | history ;
```

## 示例 7：综合大型案例 — 完整业务脚本

```dk
VERSION "1.0.0" ;
PERMIT "file_read" ;
PERMIT "file_write" ;
PERMIT "network" ;
PERMIT "ai_call" ;

// ========== 全局配置 ==========
GLOBAL LOG_FILE | str ;
SET LOG_FILE | "./app.log" ;

// ========== 工具函数 ==========
FUNC log | level | str | msg | str | nil | {
    VAR timestamp | str ;
    SET timestamp | TIME timestamp | "YYYY-MM-DD HH:mm:ss" ;
    VAR line | str ;
    SET line | STR_JOIN line | " " | timestamp | "[" | level | "]" | msg ;
    PRINT line ;
    FILE_WRITE LOG_FILE | STR_JOIN line | "\n" | line | "\n" ;
} ;

// ========== 数据获取 ==========
FUNC fetch_data | url | str | str | {
    LOG "info" | "开始获取数据: " | url ;
    VAR data | str ;
    TRY | {
        SET data | HTTP_GET data | url | {"timeout": 10} ;
    } CATCH "NetworkError" | {
        LOG "error" | "网络请求失败: " | url ;
        RET "" ;
    } ;
    LOG "info" | "数据获取成功" ;
    RET data ;
} ;

// ========== AI 分析 ==========
FUNC analyze | text | str | str | {
    LOG "info" | "开始 AI 分析..." ;
    VAR prompt | str ;
    SET prompt | PROMPT prompt | "data_analysis" | text ;
    VAR result | str ;
    SET result | AI_ASK result | prompt ;
    LOG "info" | "AI 分析完成" ;
    RET result ;
} ;

// ========== 主流程 ==========
FUNC main | nil | {
    LOG "info" | "===== 程序启动 =====" ;

    VAR raw_data | str ;
    SET raw_data | fetch_data | "https://api.example.com/latest" ;

    IF eq | raw_data | "" | {
        LOG "fatal" | "无法获取数据，程序退出" ;
        RET ;
    } ;

    VAR report | str ;
    SET report | analyze | raw_data ;

    FILE_WRITE "./report.txt" | report ;
    LOG "info" | "报告已保存到 ./report.txt" ;
    LOG "info" | "===== 程序完成 =====" ;
} ;

CALL main ;
```

---

# 第七部分：解释器运行原理（AI 内部执行流程）

## DeepSeek 作为 DK-Lang 解释器的完整执行流程

### 阶段 1：词法分析（Tokenization）

```
输入: 源码字符串
行为: DeepSeek 逐字符扫描，按以下规则分词：

1. 空格/换行 → 跳过
2. "//" → 跳过到行尾
3. "/*" → 跳过到 "*/"
4. 大写字母开头 → 累积完整词 → 查指令关键字表 → Token(指令)
5. 小写字母开头 → 累积完整词 → 
   - 查运算符表 → Token(运算符)
   - 查类型表 → Token(类型)
   - 查值表(true/false/nil) → Token(字面量)
   - 其他 → Token(标识符)
6. 数字开头 → 累积数字和小数点 → Token(字面量)
7. '"' → 累积到下一个'"' → Token(字符串)
8. '|' '{' '}' ';' → 对应 Token(分隔符)

输出: Token 列表
```

### 阶段 2：语法解析（Parsing）

```
输入: Token 列表
行为: DeepSeek 按"读到首 token 即确定解析路径"原则递归解析：

解析主循环:
  token = 当前位置
  VAR      → parse_VAR()      → VarDeclNode
  SET      → parse_SET()      → AssignNode
  CONST    → parse_CONST()    → ConstDeclNode
  FUNC     → parse_FUNC()     → FuncDefNode
  IF       → parse_IF()       → IfNode
  LOOP     → parse_LOOP()     → LoopNode/WhileNode
  WHILE    → parse_WHILE()    → WhileNode
  SWITCH   → parse_SWITCH()   → SwitchNode
  CALL     → parse_CALL()     → CallNode
  RET      → parse_RET()      → ReturnNode
  PRINT    → parse_PRINT()    → ExprStmtNode
  ...
  '}'      → 块结束
  EOF      → 解析完成

每种指令按固定字段顺序消费 token，格式错误立即报告。

输出: AST 语法树
```

### 阶段 3：语义校验（Semantic Analysis）

```
输入: AST 语法树
行为: DeepSeek 遍历 AST，建立符号表、检查类型：

1. 建立作用域树
   - 全局作用域: GLOBAL 声明 + 函数名
   - 函数作用域: 参数 + LOCAL 声明
   - 块作用域: 每个 {} 创建子作用域

2. 类型检查
   - VAR x | int → 记录 x: int
   - SET x | "hello" → 类型不匹配 → 报错
   - CALL f | a → 检查 f 签名匹配

3. 权限检查
   - PERMIT 声明 vs 实际使用
   - 未声明 → 报错

4. 未定义检查
   - 所有变量引用是否都有声明
   - 所有 CALL 目标是否都有 FUNC

输出: 类型标注的 AST + 符号表
```

### 阶段 4：逻辑执行（Execution）

```
输入: 类型标注的 AST + 符号表
行为: DeepSeek 遍历 AST 树，按节点类型逐条求值：

执行环境:
  - global_env: {变量名: 值, ...}
  - func_registry: {函数名: FuncDefNode}
  - scope_stack: [global_env, func_env, block_env, ...]

求值函数 eval(node, env):
  VarDeclNode  → env[name] = 默认值
  AssignNode   → env[name] = eval(node.value)
  ConstDeclNode→ env[name] = eval(node.value)  // 标记只读
  BinaryOpNode → 按 op 计算 left, right
  IfNode       → 条件真 → then块，假 → else块
  WhileNode    → 循环执行直到条件假
  LoopNode     → 先init，循环condition+body+step
  SwitchNode   → 匹配 case 值，执行对应块
  FuncDefNode  → 注册函数
  CallNode     → 创建新scope，绑定参数，执行函数体
  ReturnNode   → 抛 ReturnSignal(值)
  PrintNode    → 输出到标准输出
  ...

信号处理:
  ReturnSignal → 被 CallNode 捕获，作为函数返回值
  BreakSignal  → 被循环节点捕获，跳出循环
  NextSignal   → 被循环节点捕获，跳过本次迭代体
  ErrorSignal  → 被 TRY-CATCH 捕获或终止程序

输出: 执行结果（标准输出 + 最后一个表达式的值）
```

### 阶段 5：结果输出（Output）

```
行为:
  1. 收集所有 PRINT 输出的内容 → 拼接为最终输出文本
  2. 如有未捕获异常 → 按第六部分格式输出错误信息
  3. 返回最终值（如有）

输出: 程序运行结果
```

---

# 第八部分：使用规范、避坑指南与后续拓展方向

## 8.1 新手快速上手步骤

1. **第一步**：熟悉 `VAR` `SET` `PRINT` `CALC` 四个基础指令
2. **第二步**：掌握 `IF` `LOOP`（计数模式）两个控制流
3. **第三步**：学习 `FUNC` `CALL` `RET` 进行函数封装
4. **第四步**：使用 `ARR` `GET` `MAP` 处理复合数据
5. **第五步**：尝试 `WHILE` 条件循环和 `SWITCH` 多分支
6. **第六步**：引入 `TRY-CATCH` 和文件 IO
7. **第七步**：体验 `AI_ASK` `AI_EXTRACT` 等 AI 原生能力
8. **第八步后**：按需学习 L9-L13

## 8.2 高频语法易错点与避坑清单

| 易错点 | 错误写法 | 正确写法 |
|--------|---------|---------|
| 忘记 `;` | `SET x \| 10` | `SET x \| 10 ;` |
| 忘记 `\|` | `SET x 10 ;` | `SET x \| 10 ;` |
| `{}` 不写 | `IF gt \| x \| 5 \| PRINT "ok" ;` | `IF gt \| x \| 5 \| { PRINT "ok" ; } ;` |
| 声明时赋值 | `VAR x \| int \| 10 ;` | `VAR x \| int ;` 然后 `SET x \| 10 ;` |
| 隐式类型转换 | `SET r \| 3 ;` （r 是 real） | `SET r \| AS(3, real) ;` |
| 深度嵌套 | `RET CALC add \| CALL f \| sub...` | 拆分为多步赋值 |
| 忘记 PERMIT | 使用 FILE_READ 但未声明 | 文件首行加 `PERMIT "file_read" ;` |
| LOOP 用错模式 | `LOOP i \| lt \| i \| 10 \| 1 \| {...}` | 计数模式或条件模式选一，不混用 |

## 8.3 语言后续可拓展功能清单

| 方向 | 计划功能 | 版本 |
|------|---------|------|
| AI 增强 | 多模态输入（视频/音频）、Agent 链式调用 | v1.5 |
| 编译器 | DK-Lang → WebAssembly 编译 | v2.0 |
| 类型系统 | 泛型、代数数据类型（ADT）、模式匹配 | v2.0 |
| 包管理 | `dkpm` 包管理工具、中心仓库 | v1.3 |
| IDE 支持 | VSCode/Cursor 插件、语法高亮、自动补全 | v1.2 |
| 并发模型 | Actor 模型、通道（channel）、协程 | v1.4 |
| 可视化 | 数据可视化原语、图表输出 | v1.6 |
| 安全 | 形式化验证、静态分析、污点追踪 | v2.0 |
| 嵌入式 | 物联网设备运行时、轻量版解释器 | v2.1 |
| 互操作 | C/Go/Rust 原生 FFI 绑定 | v1.5 |

---

> **文档版本**：v1.0.0  
> **语言版本**：DK-Lang v1.0.0  
> **目标模型**：DeepSeek 全系列  
> **最后更新**：2026-05-28  
> **文档总字数**：约 22000 字  
> **声明**：本规范为 DK-Lang 语言的唯一权威参考。任何实现必须严格遵循本文档。

---

*DK-Lang —— 为大模型而生，为零歧义而设计。*
