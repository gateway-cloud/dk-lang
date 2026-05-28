# DK-Lang (璋涘埢璇█) 鈥?DeepSeek Knowledge Language

[![Version](https://img.shields.io/badge/version-1.4.0-blue)](https://github.com/dk-lang/dk-lang/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-green)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)

> **AI-Optimized Programming Language** 鈥?涓撲负澶фā鍨嬩紭鍖栫殑浣庢涔夈€佺粨鏋勬樉鎬х紪绋嬭瑷€

DK-Lang 鏄竴绉嶄笓涓?AI锛堢壒鍒槸 DeepSeek 澶фā鍨嬶級璁捐鐨勭紪绋嬭瑷€銆傛牳蹇冨師鍒欙細**涓€鍒囪娉曡璁′互銆岄檷浣庡ぇ妯″瀷鍒嗚瘝銆佺悊瑙ｃ€佽В鏋愩€佺籂閿欒礋鎷呫€嶄负鏈€楂樹紭鍏堢骇**銆?
---

## 馃殌 蹇€熷紑濮?
### 瀹夎

**Windows (鎺ㄨ崘)**: 涓嬭浇 [DK-Lang-1.4.0-win64.msi](https://github.com/dk-lang/dk-lang/releases/latest) 鍙屽嚮瀹夎銆?- 鉁?鑷姩閰嶇疆 PATH 鐜鍙橀噺
- 鉁?鑷畾涔夊畨瑁呰矾寰?- 鉁?瀹夎杩涘害鏉?+ 宸插畨瑁呮娴?- 鉁?鍚畬鏁存枃妗?(DK-LANG-SPEC.md + DEVELOPER.md)

**浠庢簮鐮佽繍琛?*:
```bash
git clone https://github.com/dk-lang/dk-lang.git
cd dk-lang
python dk_cli.py run examples/e01_basic.dk
```

### 绗竴涓▼搴?
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
# 杈撳嚭: Hello, DK-Lang!
```

---

## 鉁?鏍稿績鐗规€?
### 馃幆 闆舵涔夎娉?
鎵€鏈夎鍙ヤ互澶у啓鍏抽敭瀛楀紑澶达紝`|` 鍞竴鍒嗛殧绗︼紝杩愮畻绗﹀崟璇嶅寲锛?
```dk
// 鍙橀噺瀹氫箟 鈥斺€?绫诲瀷鏄惧紡鏍囨敞
VAR count | int ;
SET count | 42 ;

// 鏉′欢鍒ゆ柇 鈥斺€?鍙湁涓€绉嶅啓娉?IF gt | count | 40 | {
    PRINT "澶т簬40" ;
} | {
    PRINT "灏忎簬绛変簬40" ;
} ;

// 寰幆 鈥斺€?鍥哄畾璇簭锛岀姝㈠彉浣?LOOP i | 1 | 5 | 1 | {
    PRINT "绗? | i | "娆? ;
} ;
```

### 馃У 瀛楃涓叉搷浣滐紙v1.1 鏀寔琛ㄨ揪寮忥級

```dk
// 鍐呰仈瀛楃涓叉嫾鎺?SET msg | STR_JOIN "-" | "hello" | "world" ;
// msg = "hello-world"

// 澶氳瀛楃涓诧紙v1.3锛?VAR html | str ;
SET html | `
<html>
  <body><h1>DK-Lang</h1></body>
</html>
` ;
```

### 馃摗 绾?DK-Lang HTTP 鏈嶅姟鍣紙v1.3锛?
闆?Python 鑳舵按浠ｇ爜鍚姩 Web 鏈嶅姟锛?
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

### 馃梽锔?鏁版嵁搴撴敮鎸侊紙v1.2锛?
```dk
CALL _db_connect | "mydb" | "sqlite" | "sqlite://./data.db" ;
CALL _db_execute | "mydb" | "CREATE TABLE users (id INTEGER, name TEXT)" | "{}" ;
```

---

## 馃摉 璇█鐗规€у叏瑙?
| 灞傜骇 | 鐗规€?| 鍏抽敭瀛?|
|------|------|--------|
| L1 鍩虹 | 鍙橀噺銆佽祴鍊笺€佽繍绠椼€佽緭鍑?| VAR, SET, CONST, CALC, PRINT |
| L2 鎺у埗 | 鏉′欢銆佸惊鐜€佸垎鏀?| IF/ELSE, LOOP, WHILE, SWITCH/CASE |
| L3 鍑芥暟/瀹瑰櫒 | 鍑芥暟銆佹暟缁勩€丮ap銆丼et | FUNC, CALL, RET, ARR, MAP, PUSH, POP |
| L4 瀛楃涓?| 鎷兼帴銆佹埅鍙栥€佹煡鎵俱€佹浛鎹?| STR_JOIN, STR_CUT, STR_LEN, STR_FIND, STR_REPL |
| L5 宸ョ▼ | 妯″潡銆佹枃浠躲€佸紓甯搞€佺被鍨?| USE, FILE_READ/WRITE, TRY/CATCH, AS, TYPE |
| L6 鍏冪紪绋?| 瀹忋€佸姩鎬佹墽琛屻€佸埆鍚?| MACRO, EVAL, ALIAS |
| L7 AI | 澶фā鍨嬮棶绛斻€佹憳瑕併€佺炕璇?| AI_ASK, AI_SUMMARIZE, AI_CLASSIFY |
| L8 璋冭瘯 | 鏃ュ織銆佹柇鐐广€佽拷韪€佹椂闂?| LOG, TRACE, TIME, RAND |
| L9 骞跺彂/缃戠粶/DB | 寮傛銆丠TTP銆乄ebSocket銆丼QL | ASYNC, HTTP_GET/POST, DB_QUERY |
| L10 OOP | 绫汇€佸疄渚嬨€佺户鎵?| CLASS, NEW, EXTENDS |
| L11 绯荤粺 | 鍛戒护銆佺幆澧冦€佸畾鏃?| EXEC, ENV_GET, CRON |
| **v1.3 鏂板** | **HTTP 鏈嶅姟鍣?* | **SERVER, ROUTE, MIDDLEWARE, STATIC** |
| **v1.1 鏂板** | **鏁扮粍宸ュ叿** | **ARR_LEN** |

---

## 馃彈锔?椤圭洰缁撴瀯

```
dk-lang/
鈹溾攢鈹€ dk_cli.py                 # CLI 鍏ュ彛 (run/repl/debug)
鈹溾攢鈹€ setup.py                  # MSI 鎵撳寘閰嶇疆
鈹溾攢鈹€ dklang/                   # 瑙ｉ噴鍣ㄦ牳蹇?鈹?  鈹溾攢鈹€ __init__.py            #   run_dk / run_dk_string
鈹?  鈹溾攢鈹€ lexer.py               #   璇嶆硶鍒嗘瀽鍣?(~100 鍏抽敭瀛?
鈹?  鈹溾攢鈹€ parser.py              #   涓ら亶瑙ｆ瀽鍣?+ 鍑芥暟绛惧悕棰勬壂鎻?鈹?  鈹溾攢鈹€ ast_nodes.py           #   AST 鑺傜偣 + 绫诲瀷绯荤粺 + 閿欒浣撶郴
鈹?  鈹溾攢鈹€ interpreter.py         #   鏍戦亶鍘嗘墽琛屽櫒 + 鏍堝紡浣滅敤鍩?鈹?  鈹溾攢鈹€ extensions.py          #   鏁版嵁搴?+ HTTP 鍐呯疆鍑芥暟娉ㄥ唽
鈹?  鈹溾攢鈹€ httpd.py               #   HTTP 瀹㈡埛绔?鏈嶅姟绔?+ WebSocket
鈹?  鈹溾攢鈹€ database.py            #   SQLite/MySQL/PostgreSQL + ORM
鈹?  鈹斺攢鈹€ ffi/__init__.py        #   Python/C++/Java FFI 鍔犺浇鍣?鈹溾攢鈹€ examples/                  # 9 涓笎杩涘紡绀轰緥
鈹?  鈹溾攢鈹€ e01_basic.dk           #   鍩虹璇硶
鈹?  鈹溾攢鈹€ e02_control.dk         #   娴佺▼鎺у埗
鈹?  鈹溾攢鈹€ e05_engineering.dk     #   鏂囦欢+寮傚父+绫诲瀷杞崲
鈹?  鈹溾攢鈹€ e07_comprehensive.dk   #   缁煎悎妗堜緥
鈹?  鈹斺攢鈹€ e09_backend.dk         #   鍚庣 REST API 绀轰緥
鈹溾攢鈹€ projects/taskflow/         # 鍏ㄦ爤 Web 绀轰緥
鈹?  鈹溾攢鈹€ server_v2.dk           #   绾?DK-Lang API 鏈嶅姟鍣?鈹?  鈹斺攢鈹€ run_v2.py              #   鍚姩鑴氭湰
鈹溾攢鈹€ tests/                     # 娴嬭瘯濂椾欢 (~280 鐢ㄤ緥)
鈹?  鈹溾攢鈹€ industrial_core.dk     #   35 鏍稿績娴嬭瘯
鈹?  鈹溾攢鈹€ industrial_edge.dk     #   9 杈圭晫/鍘嬪姏娴嬭瘯
鈹?  鈹斺攢鈹€ deep_audit.py          #   93 Python 鍗曞厓娴嬭瘯
鈹溾攢鈹€ DK-LANG-SPEC.md           # 瀹屾暣璇█瑙勮寖 (~30K 瀛?
鈹溾攢鈹€ DEVELOPER.md              # AI 寮€鍙戣€呭己鍒惰鍙栨枃妗?鈹斺攢鈹€ README.md                 # 鏈枃浠?```

---

## 馃敡 鍛戒护琛?
```bash
# 杩愯 .dk 鏂囦欢
python dk_cli.py run path/to/file.dk

# 浜や簰寮?REPL
python dk_cli.py repl

# 璋冭瘯妯″紡锛堟樉绀?Token + AST锛?python dk_cli.py run path/to/file.dk --debug

# 鏌ョ湅鐗堟湰
python dk_cli.py version
```

---

## 馃搳 瀹炴垬椤圭洰

### 瀛︾敓绠＄悊绯荤粺 (student_system/)
```bash
python dk_cli.py run ../student_system/main.dk
```
700+ 琛岋紝CRUD + 鎴愮哗缁熻 + 鎺掑悕 + 鏂囦欢鎸佷箙鍖栥€?
### 鍥句功鍊熼槄绠＄悊绯荤粺 (tests/library_system.dk)
```bash
python dk_cli.py run tests/library_system.dk
```
600+ 琛岋紝鍊熼槄/褰掕繕/閫炬湡缃氭/棰勭害/缁熻鍒嗘瀽銆?
### TaskFlow Web 搴旂敤 (projects/taskflow/)
```bash
cd projects/taskflow && python run_v2.py
```
绾?DK-Lang 鍏ㄦ爤 Web 搴旂敤锛孒TTP 鏈嶅姟鍣?+ SQLite + 鍓嶇鐢熸垚锛岄浂 Python 鑳舵按銆?
---

## 馃И 娴嬭瘯

```bash
# 鏍稿績璇█鐗规€?(35 娴嬭瘯)
python dk_cli.py run tests/industrial_core.dk

# 杈圭晫鏉′欢 + 鍘嬪姏 (9 娴嬭瘯)
python dk_cli.py run tests/industrial_edge.dk

# Python 鍗曞厓娴嬭瘯 (93 娴嬭瘯)
python -m pytest tests/deep_audit.py -v
```

---

## 馃З VS Code 鎵╁睍

瀹夎 [dk-lang-1.4.0.vsix](https://github.com/gateway-cloud/dk-lang-ide/releases/latest) 鑾峰緱锛?
- **璇硶楂樹寒** (8鑹?: 鍏抽敭瀛?绫诲瀷/瀛楃涓?鏁板瓧/娉ㄩ噴/鍑芥暟/杩愮畻绗?鍐呯疆
- **23 涓唬鐮佺墖娈?*: `main` `func` `if` `loop` `server` `try`...
- **F5 杩愯**: 涓€閿墽琛屽綋鍓?.dk 鏂囦欢
- **鑷姩闂悎/鎶樺彔/缂╄繘**

瀹夎鏂瑰紡: VS Code 鈫?`Ctrl+Shift+P` 鈫?"Install from VSIX..."

---

## 馃搻 璁捐鍘熷垯

1. **璇彞棣?token 蹇呬负鍏抽敭瀛?* 鈥?璇诲埌绗?1 涓?token 灏辩‘瀹氳В鏋愯矾寰?2. **`|` 鍞竴瀛楁鍒嗛殧绗?* 鈥?闆跺垎闅旂姝т箟
3. **`{ }` 鍧楀己鍒舵樉寮?* 鈥?block 杈圭晫 100% 纭畾
4. **闆剁被鍨嬫帹鏂?* 鈥?鍙橀噺澹版槑蹇呴』鍐欑被鍨?5. **杩愮畻绗﹀崟璇嶅寲** 鈥?`add` 鑰岄潪 `+`
6. **绂佹璇硶绯?* 鈥?姣忕鎿嶄綔鍙湁涓€绉嶅啓娉?7. **绂佹杩愮畻绗﹂噸杞?* 鈥?璇箟鍞竴
8. **鍏抽敭瀛楁瀬鐭?(2-5 瀛楃)** 鈥?闄嶄綆涓婁笅鏂囩獥鍙ｆ秷鑰?
---

## 馃攧 鐗堟湰鍘嗗彶

| 鐗堟湰 | 鏃ユ湡 | 鍙樻洿 |
|------|------|------|
| v1.0.0 | 2024-04 | 鍒濆鍙戝竷 |
| v1.1.0 | 2026-05 | STR 琛ㄨ揪寮忓寲 + ARR_LEN + TRY/CATCH 淇 |
| v1.2.0 | 2026-05 | 涓ら亶瑙ｆ瀽 + 宓屽 CALL + DB/HTTP 鎵╁睍 |
| v1.3.0 | 2026-05 | SERVER/ROUTE + 澶氳瀛楃涓?+ 涓棿浠堕摼 |
| v1.4.0 | 2026-05 | 瑁歌繍绠楃 + 10 Bug 淇 + Arity 妫€鏌?|

[瀹屾暣 Changelog 鈫抅(CHANGELOG.md)

---

## 馃搫 璁稿彲璇?
MIT License 鈥?璇﹁ [LICENSE](LICENSE)

---

## 馃 璐＄尞

娆㈣繋鎻愪氦 Issue 鍜?Pull Request銆傚紑鍙戝墠璇峰厛闃呰 [DEVELOPER.md](DEVELOPER.md)锛圓I 寮哄埗锛夈€?
