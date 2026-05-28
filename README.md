# DK-Lang (谛刻语言) — DeepSeek Knowledge Language

[![Version](https://img.shields.io/badge/version-1.4.0-blue)](https://github.com/dk-lang/dk-lang/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-green)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)

> **AI-Optimized Programming Language** — 专为大模型优化的低歧义、结构显性编程语言

DK-Lang 是一种专为 AI（特别是 DeepSeek 大模型）设计的编程语言。核心原则：**一切语法设计以「降低大模型分词、理解、解析、纠错负担」为最高优先级**。

---

## 🚀 快速开始

### 安装

**Windows (推荐)**: 下载 [DK-Lang-1.4.0-win64.msi](https://github.com/dk-lang/dk-lang/releases/latest) 双击安装。
- ✅ 自动配置 PATH 环境变量
- ✅ 自定义安装路径
- ✅ 安装进度条 + 已安装检测
- ✅ 含完整文档 (DK-LANG-SPEC.md + DEVELOPER.md)

**从源码运行**:
```bash
git clone https://github.com/dk-lang/dk-lang.git
cd dk-lang
python dk_cli.py run examples/e01_basic.dk
```

### 第一个程序

```dk
VERSION "1.0.0" ;

FUNC greet | name | str | str | {
    RET STR_JOIN "" | "Hello, " | name | "!" ;
} ;

FUNC main | str | {
    PRINT CALL greet | "DK-Lang" ;
    RET "OK" ;
} ;

CALL main ;
```

```bash
python dk_cli.py run hello.dk
# 输出: Hello, DK-Lang!
```

---

## ✨ 核心特性

### 🎯 零歧义语法

所有语句以大写关键字开头，`|` 唯一分隔符，运算符单词化：

```dk
// 变量定义 —— 类型显式标注
VAR count | int ;
SET count | 42 ;

// 条件判断 —— 只有一种写法
IF gt | count | 40 | {
    PRINT "大于40" ;
} | {
    PRINT "小于等于40" ;
} ;

// 循环 —— 固定语序，禁止变体
LOOP i | 1 | 5 | 1 | {
    PRINT "第" | i | "次" ;
} ;
```

### 🧵 字符串操作（v1.1 支持表达式）

```dk
// 内联字符串拼接
SET msg | STR_JOIN "-" | "hello" | "world" ;
// msg = "hello-world"

// 多行字符串（v1.3）
VAR html | str ;
SET html | `
<html>
  <body><h1>DK-Lang</h1></body>
</html>
` ;
```

### 📡 纯 DK-Lang HTTP 服务器（v1.3）

零 Python 胶水代码启动 Web 服务：

```dk
FUNC health | req | str | str | {
    RET `{"status":"ok","service":"DK-Lang"}` ;
} ;

FUNC main | str | {
    SERVER "0.0.0.0" | 8080 | {
        MIDDLEWARE auth_mw ;
        STATIC "/static" | "./static" ;
        ROUTE "GET" | "/api/health" | health ;
    } ;
} ;
```

### 🗄️ 数据库支持（v1.2）

```dk
CALL _db_connect | "mydb" | "sqlite" | "sqlite://./data.db" ;
CALL _db_execute | "mydb" | "CREATE TABLE users (id INTEGER, name TEXT)" | "{}" ;
```

---

## 📖 语言特性全览

| 层级 | 特性 | 关键字 |
|------|------|--------|
| L1 基础 | 变量、赋值、运算、输出 | VAR, SET, CONST, CALC, PRINT |
| L2 控制 | 条件、循环、分支 | IF/ELSE, LOOP, WHILE, SWITCH/CASE |
| L3 函数/容器 | 函数、数组、Map、Set | FUNC, CALL, RET, ARR, MAP, PUSH, POP |
| L4 字符串 | 拼接、截取、查找、替换 | STR_JOIN, STR_CUT, STR_LEN, STR_FIND, STR_REPL |
| L5 工程 | 模块、文件、异常、类型 | USE, FILE_READ/WRITE, TRY/CATCH, AS, TYPE |
| L6 元编程 | 宏、动态执行、别名 | MACRO, EVAL, ALIAS |
| L7 AI | 大模型问答、摘要、翻译 | AI_ASK, AI_SUMMARIZE, AI_CLASSIFY |
| L8 调试 | 日志、断点、追踪、时间 | LOG, TRACE, TIME, RAND |
| L9 并发/网络/DB | 异步、HTTP、WebSocket、SQL | ASYNC, HTTP_GET/POST, DB_QUERY |
| L10 OOP | 类、实例、继承 | CLASS, NEW, EXTENDS |
| L11 系统 | 命令、环境、定时 | EXEC, ENV_GET, CRON |
| **v1.3 新增** | **HTTP 服务器** | **SERVER, ROUTE, MIDDLEWARE, STATIC** |
| **v1.1 新增** | **数组工具** | **ARR_LEN** |

---

## 🏗️ 项目结构

```
dk-lang/
├── dk_cli.py                 # CLI 入口 (run/repl/debug)
├── setup.py                  # MSI 打包配置
├── dklang/                   # 解释器核心
│   ├── __init__.py            #   run_dk / run_dk_string
│   ├── lexer.py               #   词法分析器 (~100 关键字)
│   ├── parser.py              #   两遍解析器 + 函数签名预扫描
│   ├── ast_nodes.py           #   AST 节点 + 类型系统 + 错误体系
│   ├── interpreter.py         #   树遍历执行器 + 栈式作用域
│   ├── extensions.py          #   数据库 + HTTP 内置函数注册
│   ├── httpd.py               #   HTTP 客户端/服务端 + WebSocket
│   ├── database.py            #   SQLite/MySQL/PostgreSQL + ORM
│   └── ffi/__init__.py        #   Python/C++/Java FFI 加载器
├── examples/                  # 9 个渐进式示例
│   ├── e01_basic.dk           #   基础语法
│   ├── e02_control.dk         #   流程控制
│   ├── e05_engineering.dk     #   文件+异常+类型转换
│   ├── e07_comprehensive.dk   #   综合案例
│   └── e09_backend.dk         #   后端 REST API 示例
├── projects/taskflow/         # 全栈 Web 示例
│   ├── server_v2.dk           #   纯 DK-Lang API 服务器
│   └── run_v2.py              #   启动脚本
├── tests/                     # 测试套件 (~280 用例)
│   ├── industrial_core.dk     #   35 核心测试
│   ├── industrial_edge.dk     #   9 边界/压力测试
│   └── deep_audit.py          #   93 Python 单元测试
├── DK-LANG-SPEC.md           # 完整语言规范 (~30K 字)
├── DEVELOPER.md              # AI 开发者强制读取文档
└── README.md                 # 本文件
```

---

## 🔧 命令行

```bash
# 运行 .dk 文件
python dk_cli.py run path/to/file.dk

# 交互式 REPL
python dk_cli.py repl

# 调试模式（显示 Token + AST）
python dk_cli.py run path/to/file.dk --debug

# 查看版本
python dk_cli.py version
```

---

## 📊 实战项目

### 学生管理系统 (student_system/)
```bash
python dk_cli.py run ../student_system/main.dk
```
700+ 行，CRUD + 成绩统计 + 排名 + 文件持久化。

### 图书借阅管理系统 (tests/library_system.dk)
```bash
python dk_cli.py run tests/library_system.dk
```
600+ 行，借阅/归还/逾期罚款/预约/统计分析。

### TaskFlow Web 应用 (projects/taskflow/)
```bash
cd projects/taskflow && python run_v2.py
```
纯 DK-Lang 全栈 Web 应用，HTTP 服务器 + SQLite + 前端生成，零 Python 胶水。

---

## 🧪 测试

```bash
# 核心语言特性 (35 测试)
python dk_cli.py run tests/industrial_core.dk

# 边界条件 + 压力 (9 测试)
python dk_cli.py run tests/industrial_edge.dk

# Python 单元测试 (93 测试)
python -m pytest tests/deep_audit.py -v
```

---

## 🧩 VS Code 扩展

安装 [dk-lang-1.4.0.vsix](https://github.com/gateway-cloud/dk-lang-ide/releases/latest) 获得：

- **语法高亮** (8色): 关键字/类型/字符串/数字/注释/函数/运算符/内置
- **23 个代码片段**: `main` `func` `if` `loop` `server` `try`...
- **F5 运行**: 一键执行当前 .dk 文件
- **自动闭合/折叠/缩进**

安装方式: VS Code → `Ctrl+Shift+P` → "Install from VSIX..."

---

## 📐 设计原则

1. **语句首 token 必为关键字** — 读到第 1 个 token 就确定解析路径
2. **`|` 唯一字段分隔符** — 零分隔符歧义
3. **`{ }` 块强制显式** — block 边界 100% 确定
4. **零类型推断** — 变量声明必须写类型
5. **运算符单词化** — `add` 而非 `+`
6. **禁止语法糖** — 每种操作只有一种写法
7. **禁止运算符重载** — 语义唯一
8. **关键字极短 (2-5 字符)** — 降低上下文窗口消耗

---

## 🔄 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2024-04 | 初始发布 |
| v1.1.0 | 2026-05 | STR 表达式化 + ARR_LEN + TRY/CATCH 修复 |
| v1.2.0 | 2026-05 | 两遍解析 + 嵌套 CALL + DB/HTTP 扩展 |
| v1.3.0 | 2026-05 | SERVER/ROUTE + 多行字符串 + 中间件链 |
| v1.4.0 | 2026-05 | 裸运算符 + 10 Bug 修复 + Arity 检查 |

[完整 Changelog →](CHANGELOG.md)

---

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request。开发前请先阅读 [DEVELOPER.md](DEVELOPER.md)（AI 强制）。

