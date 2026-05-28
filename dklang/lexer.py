"""DK-Lang 词法分析器。读取 DEVELOPER.md 获取完整关键字清单。"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Any


class TK(Enum):
    # 指令关键字(大写)
    KW_VAR=auto(); KW_SET=auto(); KW_CONST=auto(); KW_PRINT=auto(); KW_IF=auto(); KW_ELSE=auto()
    KW_LOOP=auto(); KW_SWITCH=auto(); KW_CASE=auto(); KW_DEFAULT=auto(); KW_BREAK=auto(); KW_NEXT=auto()
    KW_FUNC=auto(); KW_CALL=auto(); KW_RET=auto(); KW_ARR=auto(); KW_GET=auto(); KW_PUSH=auto(); KW_POP=auto()
    KW_SET_ADD=auto(); KW_SET_HAS=auto(); KW_MAP=auto(); KW_MAP_SET=auto(); KW_MAP_GET=auto()
    KW_MAP_DEL=auto(); KW_MAP_HAS=auto(); KW_GLOBAL=auto(); KW_LOCAL=auto()
    KW_STR_JOIN=auto(); KW_STR_CUT=auto(); KW_STR_LEN=auto(); KW_STR_FIND=auto(); KW_STR_REPL=auto()
    KW_ARR_LEN=auto()
    KW_AND=auto(); KW_OR=auto(); KW_NOT=auto(); KW_WHILE=auto()
    KW_USE=auto(); KW_FILE_READ=auto(); KW_FILE_WRITE=auto(); KW_FILE_EXIST=auto()
    KW_TRY=auto(); KW_CATCH=auto(); KW_THROW=auto(); KW_AS=auto(); KW_TYPE=auto(); KW_ISA=auto()
    KW_FROM=auto(); KW_IMPORT=auto()
    KW_MACRO=auto(); KW_EVAL=auto(); KW_ALIAS=auto()
    KW_AI_ASK=auto(); KW_AI_EXTRACT=auto(); KW_AI_SUMMARIZE=auto(); KW_AI_CLASSIFY=auto()
    KW_AI_TRANSLATE=auto(); KW_CTX=auto(); KW_PROMPT=auto(); KW_AI_IMAGE=auto()
    KW_CALC=auto();
    KW_LOG=auto(); KW_TRACE=auto(); KW_TIME=auto(); KW_RAND=auto()
    KW_B64ENC=auto(); KW_B64DEC=auto()
    KW_ASYNC=auto(); KW_AWAIT=auto(); KW_THREAD=auto(); KW_JOIN=auto(); KW_KILL=auto()
    KW_HTTP_GET=auto(); KW_HTTP_POST=auto(); KW_WS_CONN=auto(); KW_WS_SEND=auto(); KW_WS_RECV=auto()
    KW_URL_ENC=auto(); KW_URL_DEC=auto()
    KW_DB_CONN=auto(); KW_DB_QUERY=auto(); KW_DB_INSERT=auto(); KW_DB_UPDATE=auto(); KW_DB_DELETE=auto()
    KW_CLASS=auto(); KW_NEW=auto(); KW_PROP=auto(); KW_METHOD=auto(); KW_EXTENDS=auto()
    KW_THIS=auto(); KW_SUPER=auto()
    KW_WAIT=auto(); KW_CRON=auto(); KW_EXEC=auto(); KW_ENV_GET=auto(); KW_ENV_SET=auto(); KW_EXIT=auto()
    KW_SANDBOX=auto(); KW_PERMIT=auto(); KW_AUDIT=auto(); KW_VERSION=auto()
    KW_SERVER=auto(); KW_ROUTE=auto(); KW_MIDDLEWARE=auto(); KW_STATIC=auto()

    # 运算符(小写)
    OP_ADD=auto(); OP_SUB=auto(); OP_MUL=auto(); OP_DIV=auto(); OP_MOD=auto()
    OP_GT=auto(); OP_LT=auto(); OP_EQ=auto(); OP_NE=auto(); OP_GE=auto(); OP_LE=auto()

    # 类型(小写)
    TYPE_INT=auto(); TYPE_REAL=auto(); TYPE_STR=auto(); TYPE_BOOL=auto(); TYPE_NIL_KW=auto()
    TYPE_ARR=auto(); TYPE_SET=auto(); TYPE_MAP=auto()
    TYPE_TASK=auto(); TYPE_THREAD=auto(); TYPE_FILE=auto(); TYPE_DB=auto(); TYPE_CLASS=auto(); TYPE_OBJ=auto()

    # 字面量
    LIT_INT=auto(); LIT_REAL=auto(); LIT_STR=auto()
    LIT_TRUE=auto(); LIT_FALSE=auto()

    # 分隔符
    PIPE=auto(); SEMI=auto(); LBRACE=auto(); RBRACE=auto()
    LPAREN=auto(); RPAREN=auto(); LBRACKET=auto(); RBRACKET=auto()
    COLON=auto(); COMMA=auto(); DOT=auto()

    IDENT=auto(); EOF=auto()


@dataclass
class Token:
    kind: TK; value: Any = None; line: int = 0; col: int = 0
    def __repr__(self):
        v = f', {self.value!r}' if self.value is not None else ''
        return f'Token({self.kind.name}{v})'


# ──关键字映射表───────────────────────────────────────────

INSTR = {  # 大写指令 → TK
    'VAR':TK.KW_VAR,'SET':TK.KW_SET,'CONST':TK.KW_CONST,'PRINT':TK.KW_PRINT,
    'IF':TK.KW_IF,'ELSE':TK.KW_ELSE,'LOOP':TK.KW_LOOP,'SWITCH':TK.KW_SWITCH,
    'CASE':TK.KW_CASE,'DEFAULT':TK.KW_DEFAULT,'BREAK':TK.KW_BREAK,'NEXT':TK.KW_NEXT,
    'CALC':TK.KW_CALC,'FUNC':TK.KW_FUNC,'CALL':TK.KW_CALL,'RET':TK.KW_RET,'ARR':TK.KW_ARR,
    'GET':TK.KW_GET,'PUSH':TK.KW_PUSH,'POP':TK.KW_POP,
    'SET_ADD':TK.KW_SET_ADD,'SET_HAS':TK.KW_SET_HAS,
    'MAP':TK.KW_MAP,'MAP_SET':TK.KW_MAP_SET,'MAP_GET':TK.KW_MAP_GET,
    'MAP_DEL':TK.KW_MAP_DEL,'MAP_HAS':TK.KW_MAP_HAS,
    'GLOBAL':TK.KW_GLOBAL,'LOCAL':TK.KW_LOCAL,
    'STR_JOIN':TK.KW_STR_JOIN,'STR_CUT':TK.KW_STR_CUT,'STR_LEN':TK.KW_STR_LEN,
    'STR_FIND':TK.KW_STR_FIND,'STR_REPL':TK.KW_STR_REPL,'ARR_LEN':TK.KW_ARR_LEN,
    'AND':TK.KW_AND,'OR':TK.KW_OR,'NOT':TK.KW_NOT,'WHILE':TK.KW_WHILE,
    'FROM':TK.KW_FROM,'from':TK.KW_FROM,'IMPORT':TK.KW_IMPORT,'import':TK.KW_IMPORT,'USE':TK.KW_USE,'FILE_READ':TK.KW_FILE_READ,'FILE_WRITE':TK.KW_FILE_WRITE,
    'FILE_EXIST':TK.KW_FILE_EXIST,'TRY':TK.KW_TRY,'CATCH':TK.KW_CATCH,'THROW':TK.KW_THROW,
    'AS':TK.KW_AS,'as':TK.KW_AS,'TYPE':TK.KW_TYPE,'ISA':TK.KW_ISA,
    'MACRO':TK.KW_MACRO,'EVAL':TK.KW_EVAL,'ALIAS':TK.KW_ALIAS,
    'AI_ASK':TK.KW_AI_ASK,'AI_EXTRACT':TK.KW_AI_EXTRACT,'AI_SUMMARIZE':TK.KW_AI_SUMMARIZE,
    'AI_CLASSIFY':TK.KW_AI_CLASSIFY,'AI_TRANSLATE':TK.KW_AI_TRANSLATE,
    'CTX':TK.KW_CTX,'PROMPT':TK.KW_PROMPT,'AI_IMAGE':TK.KW_AI_IMAGE,
    'LOG':TK.KW_LOG,'TRACE':TK.KW_TRACE,'TIME':TK.KW_TIME,'RAND':TK.KW_RAND,
    'B64ENC':TK.KW_B64ENC,'B64DEC':TK.KW_B64DEC,
    'ASYNC':TK.KW_ASYNC,'AWAIT':TK.KW_AWAIT,'THREAD':TK.KW_THREAD,
    'JOIN':TK.KW_JOIN,'KILL':TK.KW_KILL,
    'HTTP_GET':TK.KW_HTTP_GET,'HTTP_POST':TK.KW_HTTP_POST,
    'WS_CONN':TK.KW_WS_CONN,'WS_SEND':TK.KW_WS_SEND,'WS_RECV':TK.KW_WS_RECV,
    'URL_ENC':TK.KW_URL_ENC,'URL_DEC':TK.KW_URL_DEC,
    'DB_CONN':TK.KW_DB_CONN,'DB_QUERY':TK.KW_DB_QUERY,'DB_INSERT':TK.KW_DB_INSERT,
    'DB_UPDATE':TK.KW_DB_UPDATE,'DB_DELETE':TK.KW_DB_DELETE,
    'CLASS':TK.KW_CLASS,'NEW':TK.KW_NEW,'PROP':TK.KW_PROP,'METHOD':TK.KW_METHOD,
    'EXTENDS':TK.KW_EXTENDS,'THIS':TK.KW_THIS,'SUPER':TK.KW_SUPER,
    'WAIT':TK.KW_WAIT,'CRON':TK.KW_CRON,'EXEC':TK.KW_EXEC,
    'ENV_GET':TK.KW_ENV_GET,'ENV_SET':TK.KW_ENV_SET,'EXIT':TK.KW_EXIT,
    'SANDBOX':TK.KW_SANDBOX,'PERMIT':TK.KW_PERMIT,'AUDIT':TK.KW_AUDIT,'VERSION':TK.KW_VERSION,
    'SERVER':TK.KW_SERVER,'ROUTE':TK.KW_ROUTE,'MIDDLEWARE':TK.KW_MIDDLEWARE,'STATIC':TK.KW_STATIC,
}

OPS = {'add':TK.OP_ADD,'sub':TK.OP_SUB,'mul':TK.OP_MUL,'div':TK.OP_DIV,'mod':TK.OP_MOD,
       'gt':TK.OP_GT,'lt':TK.OP_LT,'eq':TK.OP_EQ,'ne':TK.OP_NE,'ge':TK.OP_GE,'le':TK.OP_LE}

TYPES = {'int':TK.TYPE_INT,'real':TK.TYPE_REAL,'str':TK.TYPE_STR,'bool':TK.TYPE_BOOL,
         'nil':TK.TYPE_NIL_KW,'arr':TK.TYPE_ARR,'set':TK.TYPE_SET,'map':TK.TYPE_MAP}

OP_TO_STR = {TK.OP_ADD:'add',TK.OP_SUB:'sub',TK.OP_MUL:'mul',TK.OP_DIV:'div',TK.OP_MOD:'mod',
             TK.OP_GT:'gt',TK.OP_LT:'lt',TK.OP_EQ:'eq',TK.OP_NE:'ne',TK.OP_GE:'ge',TK.OP_LE:'le'}

COMPARISON = {TK.OP_GT, TK.OP_LT, TK.OP_EQ, TK.OP_NE, TK.OP_GE, TK.OP_LE}


class LexerError(Exception):
    def __init__(self, msg, line, col): super().__init__(f'词法错误({line}:{col}): {msg}')

class Lexer:
    def __init__(self, source: str):
        self.src = source; self.pos = 0; self.line = 1; self.col = 1

    def tokenize(self) -> list:
        tokens = []
        while self.pos < len(self.src):
            ch = self._peek()
            if ch in ' \t\r': self._adv(); continue
            if ch == '\n': self._adv(); self.line += 1; self.col = 1; continue
            if ch == '/' and self.pos+1 < len(self.src):
                if self.src[self.pos+1] == '/': self._skip_line_comment(); continue
                if self.src[self.pos+1] == '*': self._skip_block_comment(); continue
            if ch == '"': tokens.append(self._read_string()); continue
            if ch == '`': tokens.append(self._read_ml_string()); continue
            if ch.isdigit() or (ch == '-' and self.pos+1 < len(self.src) and self.src[self.pos+1].isdigit()):
                tokens.append(self._read_number()); continue
            if ch.isalpha() or ch == '_': tokens.append(self._read_word()); continue
            t = self._read_symbol(ch)
            if t: tokens.append(t); continue
            raise LexerError(f'非法字符 "{ch}"', self.line, self.col)
        tokens.append(Token(TK.EOF, line=self.line, col=self.col))
        return tokens

    def _peek(self): return self.src[self.pos] if self.pos < len(self.src) else '\0'
    def _adv(self): self.pos += 1; self.col += 1

    def _skip_line_comment(self):
        self._adv(); self._adv()
        while self.pos < len(self.src) and self.src[self.pos] != '\n': self.pos += 1; self.col += 1

    def _skip_block_comment(self):
        self._adv(); self._adv()
        while self.pos+1 < len(self.src):
            if self.src[self.pos] == '*' and self.src[self.pos+1] == '/':
                self._adv(); self._adv(); return
            if self.src[self.pos] == '\n': self.line += 1; self.col = 1
            else: self.col += 1
            self.pos += 1
        raise LexerError('未闭合的块注释', self.line, self.col)

    def _read_string(self):
        l, c = self.line, self.col; self._adv(); chars = []
        while self.pos < len(self.src) and self.src[self.pos] != '"':
            ch = self.src[self.pos]
            if ch == '\n':
                raise LexerError('字符串中不允许未转义的换行符，请使用 "\\n" 或多行字符串 ``', self.line, self.col)
            if ch == '\\' and self.pos+1 < len(self.src):
                self._adv(); n = self.src[self.pos]
                chars.append({'n':'\n','t':'\t','\\':'\\','"':'"'}.get(n, '\\'+n)); self._adv()
            else: chars.append(ch); self._adv()
        if self.pos >= len(self.src): raise LexerError('未闭合的字符串', l, c)
        self._adv()
        return Token(TK.LIT_STR, ''.join(chars), l, c)

    def _read_ml_string(self):
        """多行字符串，用反引号界定，支持转义序列"""
        l, c = self.line, self.col; self._adv(); chars = []
        while self.pos < len(self.src) and self.src[self.pos] != '`':
            ch = self.src[self.pos]
            if ch == '\n': self.line += 1; self.col = 1
            if ch == '\\' and self.pos+1 < len(self.src):
                self._adv(); n = self.src[self.pos]
                chars.append({'n':'\n','t':'\t','\\':'\\','`':'`'}.get(n, '\\'+n)); self._adv()
            else: chars.append(ch); self._adv()
        if self.pos >= len(self.src): raise LexerError('未闭合的多行字符串', l, c)
        self._adv()
        return Token(TK.LIT_STR, ''.join(chars), l, c)

    def _read_number(self):
        l, c = self.line, self.col; neg = False; chars = []
        if self.src[self.pos] == '-': neg = True; chars.append('-'); self._adv()
        real = False
        while self.pos < len(self.src):
            ch = self.src[self.pos]
            if ch.isdigit(): chars.append(ch); self._adv(); self.col += 1
            elif ch == '.': real = True; chars.append(ch); self._adv(); self.col += 1
            else: break
        v = ''.join(chars)
        return Token(TK.LIT_REAL if real else TK.LIT_INT, float(v) if real else int(v), l, c)

    def _read_word(self):
        l, c = self.line, self.col; chars = []
        while self.pos < len(self.src):
            ch = self.src[self.pos]
            if ch.isalnum() or ch == '_': chars.append(ch); self._adv(); self.col += 1
            else: break
        w = ''.join(chars)
        if w in INSTR: return Token(INSTR[w], line=l, col=c)
        if w in OPS: return Token(OPS[w], line=l, col=c)
        if w in TYPES: return Token(TYPES[w], line=l, col=c)
        if w == 'true': return Token(TK.LIT_TRUE, True, l, c)
        if w == 'false': return Token(TK.LIT_FALSE, False, l, c)
        return Token(TK.IDENT, w, l, c)

    def _read_symbol(self, ch):
        l, c = self.line, self.col
        m = {'|':TK.PIPE,';':TK.SEMI,'{':TK.LBRACE,'}':TK.RBRACE,
             '(':TK.LPAREN,')':TK.RPAREN,'[':TK.LBRACKET,']':TK.RBRACKET,
             ':':TK.COLON,',':TK.COMMA,'.':TK.DOT}
        if ch in m: self._adv(); self.col += 1; return Token(m[ch], line=l, col=c)
        return None
