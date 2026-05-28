"""DK-Lang AST 节点 + 类型系统 + 错误体系。读取 DEVELOPER.md 获取完整规范。"""
from dataclasses import dataclass, field
from typing import Optional, Any, List, Dict


# ── 类型系统 ──────────────────────────────────────────────

class DKType:
    def __str__(self): return self.__class__.__name__.replace('Type','').lower()
class IntType(DKType): pass
class RealType(DKType): pass
class StrType(DKType): pass
class BoolType(DKType): pass
class NilType(DKType): pass

class ListType(DKType):
    def __init__(self, elem: DKType): self.elem = elem
    def __str__(self): return f'arr[{self.elem}]'
    def __eq__(self, o): return isinstance(o, ListType) and str(self.elem)==str(o.elem)

class MapType(DKType):
    def __init__(self, k: DKType, v: DKType): self.key, self.val = k, v
    def __str__(self): return f'map[{self.key},{self.val}]'

class SetType(DKType):
    def __init__(self, e: DKType): self.elem = e
    def __str__(self): return f'set[{self.elem}]'

class FuncType(DKType):
    def __init__(self, pts: List[DKType], rt: DKType): self.param_types, self.ret = pts, rt

class TaskType(DKType): pass
class ThreadType(DKType): pass
class FileType(DKType): pass
class DbType(DKType): pass
class ClassType(DKType):
    def __init__(self, n: str): self.name = n
class ObjType(DKType):
    def __init__(self, n: str): self.cls_name = n

TYPE_MAP = {'int': IntType, 'real': RealType, 'str': StrType, 'bool': BoolType, 'nil': NilType}
DEFAULT_VALUES = {IntType: 0, RealType: 0.0, StrType: '', BoolType: False, NilType: None}


# ── AST 节点 ─────────────────────────────────────────────

class ASTNode: pass

@dataclass
class LiteralNode(ASTNode):
    value: Any; dk_type: DKType

@dataclass
class VarRefNode(ASTNode):
    name: str

@dataclass
class BinaryOpNode(ASTNode):
    op: str; left: 'ExprNode'; right: 'ExprNode'

@dataclass
class UnaryOpNode(ASTNode):
    op: str; operand: 'ExprNode'

@dataclass
class CallNode(ASTNode):
    name: str; arguments: List['ExprNode'] = field(default_factory=list)

@dataclass
class IndexNode(ASTNode):
    target: 'ExprNode'; index: 'ExprNode'

@dataclass
class AsNode(ASTNode):
    expr: 'ExprNode'; target_type: DKType

@dataclass
class IsaNode(ASTNode):
    expr: 'ExprNode'; check_type: DKType

@dataclass
class ListLiteralNode(ASTNode):
    elements: List['ExprNode'] = field(default_factory=list)

@dataclass
class MapLiteralNode(ASTNode):
    pairs: List = field(default_factory=list)  # [(key, val)]

@dataclass
class SetLiteralNode(ASTNode):
    elements: List['ExprNode'] = field(default_factory=list)

@dataclass
class MemberAccessNode(ASTNode):
    target: 'ExprNode'; member: str

@dataclass
class VarDeclNode(ASTNode):
    name: str; var_type: DKType; init_expr: Optional['ExprNode'] = None

@dataclass
class ConstDeclNode(ASTNode):
    name: str; const_type: DKType; value: 'ExprNode'

@dataclass
class AssignNode(ASTNode):
    name: str; value: 'ExprNode'

@dataclass
class IfNode(ASTNode):
    condition: 'ExprNode'; then_block: 'BlockNode'
    elifs: List = field(default_factory=list); else_block: Optional['BlockNode'] = None

@dataclass
class WhileNode(ASTNode):
    condition: 'ExprNode'; body: 'BlockNode'

@dataclass
class LoopNode(ASTNode):
    init: 'StmtNode'; condition: 'ExprNode'; step: 'StmtNode'; body: 'BlockNode'

@dataclass
class SwitchNode(ASTNode):
    expr: 'ExprNode'; cases: List = field(default_factory=list)
    default: Optional['BlockNode'] = None

@dataclass
class ReturnNode(ASTNode):
    expr: Optional['ExprNode'] = None

@dataclass
class BreakNode(ASTNode): pass

@dataclass
class NextNode(ASTNode): pass

@dataclass
class FuncDefNode(ASTNode):
    name: str; params: List = field(default_factory=list)
    return_type: DKType = None; body: 'BlockNode' = None

@dataclass
class BlockNode(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)

@dataclass
class ExprStmtNode(ASTNode):
    expr: 'ExprNode'

@dataclass
class ProgramNode(ASTNode):
    declarations: List[ASTNode] = field(default_factory=list)

@dataclass
class ImportNode(ASTNode):
    module_path: str

@dataclass
class FfiImportNode(ASTNode):
    lang: str; lib_name: str; alias: Optional[str] = None

@dataclass
class TryNode(ASTNode):
    try_block: BlockNode; catches: List = field(default_factory=list)
    # catches: [(error_type_str, BlockNode)]

@dataclass
class ThrowNode(ASTNode):
    error_type: str; message: 'ExprNode'

@dataclass
class TypeAliasNode(ASTNode):
    alias: str; original: DKType

@dataclass
class MacroNode(ASTNode):
    name: str; params: List[str]; body: str

@dataclass
class EvalNode(ASTNode):
    code_expr: 'ExprNode'

@dataclass
class AliasNode(ASTNode):
    alias_name: str; target_block: str

@dataclass
class VersionNode(ASTNode):
    version_str: str

@dataclass
class PermitNode(ASTNode):
    permission: str

@dataclass
class AiAskNode(ASTNode):
    result_var: str; prompt: 'ExprNode'; system: Optional['ExprNode'] = None

@dataclass
class AiExtractNode(ASTNode):
    result_var: str; extract_type: str; source: 'ExprNode'

@dataclass
class AiSummarizeNode(ASTNode):
    result_var: str; source: 'ExprNode'; max_words: Optional[int] = None

@dataclass
class AiClassifyNode(ASTNode):
    result_var: str; source: 'ExprNode'; categories: List[str] = field(default_factory=list)

@dataclass
class AiTranslateNode(ASTNode):
    result_var: str; source: 'ExprNode'; target_lang: str

@dataclass
class CtxNode(ASTNode):
    result_var: str; scope: str

@dataclass
class PromptNode(ASTNode):
    result_var: str; template_name: str; args: List['ExprNode'] = field(default_factory=list)

@dataclass
class AiImageNode(ASTNode):
    result_var: str; image_path: 'ExprNode'; question: 'ExprNode'

@dataclass
class LogNode(ASTNode):
    level: str; message_parts: List['ExprNode'] = field(default_factory=list)

@dataclass
class TraceNode(ASTNode):
    var_name: str

@dataclass
class TimeNode(ASTNode):
    result_var: str; fmt: str

@dataclass
class RandNode(ASTNode):
    result_var: str; min_expr: 'ExprNode'; max_expr: 'ExprNode'; as_real: bool = False

@dataclass
class Base64Node(ASTNode):
    result_var: str; source: 'ExprNode'; mode: str = 'enc'  # enc|dec

@dataclass
class FileReadNode(ASTNode):
    result_var: str; path: 'ExprNode'

@dataclass
class FileWriteNode(ASTNode):
    path: 'ExprNode'; content: 'ExprNode'

@dataclass
class FileExistNode(ASTNode):
    result_var: str; path: 'ExprNode'

@dataclass
class WaitNode(ASTNode):
    ms_expr: 'ExprNode'

@dataclass
class HttpGetNode(ASTNode):
    result_var: str; url: 'ExprNode'; headers: Optional[MapLiteralNode] = None

@dataclass
class HttpPostNode(ASTNode):
    result_var: str; url: 'ExprNode'; body: 'ExprNode'; headers: Optional[MapLiteralNode] = None

@dataclass
class ExecNode(ASTNode):
    result_var: str; cmd: 'ExprNode'

@dataclass
class EnvGetNode(ASTNode):
    result_var: str; name: 'ExprNode'

@dataclass
class EnvSetNode(ASTNode):
    name: str; value: 'ExprNode'

@dataclass
class ArrayPushNode(ASTNode):
    arr_name: str; value: 'ExprNode'

@dataclass
class ArrayPopNode(ASTNode):
    arr_name: str; result_var: Optional[str] = None

@dataclass
class MapSetNode(ASTNode):
    map_name: str; key: 'ExprNode'; value: 'ExprNode'

@dataclass
class MapGetNode(ASTNode):
    map_name: str; key: 'ExprNode'

@dataclass
class MapDelNode(ASTNode):
    map_name: str; key: 'ExprNode'

@dataclass
class MapHasNode(ASTNode):
    map_name: str; key: 'ExprNode'; result_var: str

@dataclass
class ClassDefNode(ASTNode):
    name: str; parent: Optional[str]; props: List; methods: List

@dataclass
class NewNode(ASTNode):
    obj_name: str; class_name: str; args: List['ExprNode'] = field(default_factory=list)

@dataclass
class AsyncNode(ASTNode):
    task_name: str; body: BlockNode

@dataclass
class AwaitNode(ASTNode):
    task_name: str

@dataclass
class SandboxNode(ASTNode):
    mode: str  # on|off

@dataclass
class AuditNode(ASTNode):
    result_var: str; code: 'ExprNode'

@dataclass
class ArrLenNode(ASTNode):
    result_var: str; arr_name: str

@dataclass
class ServerNode(ASTNode):
    host: 'ExprNode'; port: 'ExprNode'
    routes: List['RouteNode'] = field(default_factory=list)
    middlewares: List['MiddlewareNode'] = field(default_factory=list)
    statics: List['StaticNode'] = field(default_factory=list)

@dataclass
class RouteNode(ASTNode):
    method: str; path: str; handler_name: str

@dataclass
class MiddlewareNode(ASTNode):
    handler_name: str

@dataclass
class StaticNode(ASTNode):
    url_prefix: str; directory: str

# 类型别名
ExprNode = ASTNode
StmtNode = ASTNode


# ── 错误体系 ─────────────────────────────────────────────

class DKError(Exception):
    """DK-Lang 统一异常基类"""
    def __init__(self, error_type: str, message: str, line: int = 0, col: int = 0):
        self.error_type = error_type
        self.message = message
        self.line = line
        self.col = col
        loc = f'{line}:{col}' if line else '?'
        super().__init__(f'[{error_type}] {loc} —— {message}')

class DKSyntaxError(DKError):
    def __init__(self, msg, line=0, col=0): super().__init__('SyntaxError', msg, line, col)

class DKNameError(DKError):
    def __init__(self, msg, line=0, col=0): super().__init__('NameError', msg, line, col)

class DKTypeError(DKError):
    def __init__(self, msg, line=0, col=0): super().__init__('TypeError', msg, line, col)

class DKArithError(DKError):
    def __init__(self, msg, line=0, col=0): super().__init__('ArithError', msg, line, col)

class DKIOError(DKError):
    def __init__(self, msg, line=0, col=0): super().__init__('IOError', msg, line, col)

class DKPermError(DKError):
    def __init__(self, msg, line=0, col=0): super().__init__('PermError', msg, line, col)

class DKAIError(DKError):
    def __init__(self, msg, line=0, col=0): super().__init__('AIError', msg, line, col)

class DKNetworkError(DKError):
    def __init__(self, msg, line=0, col=0): super().__init__('NetworkError', msg, line, col)

class DKDBError(DKError):
    def __init__(self, msg, line=0, col=0): super().__init__('DBError', msg, line, col)

# 运行时信号
class ReturnSignal(Exception):
    def __init__(self, value): self.value = value
class BreakSignal(Exception): pass
class NextSignal(Exception): pass
