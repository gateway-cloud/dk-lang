"""DK-Lang 解释器 — 为 DeepSeek 优化的编程语言。读取 DEVELOPER.md。"""
from .lexer import Lexer, LexerError
from .parser import Parser, ParseError
from .interpreter import Interpreter
from .ast_nodes import DKError

__version__ = '1.0.0'


def run_dk_string(source: str, debug: bool = False, ctx: dict = None) -> any:
    lexer = Lexer(source)
    try: tokens = lexer.tokenize()
    except LexerError as e: print(f'[词法错误] {e}'); return None
    if debug:
        print('=== Tokens ===')
        for t in tokens: print(f'  {t}')
    parser = Parser(tokens)
    try: ast = parser.parse()
    except ParseError as e: print(f'[语法错误] {e}'); return None
    if debug:
        print('=== AST ==='); _print_ast(ast)
    try:
        interp = Interpreter(ctx=ctx)
        result = interp.execute(ast)
    except DKError as e: print(f'[{e.error_type}] {e.message}'); return None
    except Exception as e:
        import traceback
        print(f'[运行时错误] {type(e).__name__}: {e}')
        if debug: traceback.print_exc()
        return None
    return result


def run_dk(filepath: str, debug: bool = False, ctx: dict = None) -> any:
    with open(filepath, 'r', encoding='utf-8') as f: source = f.read()
    if debug: print(f'=== 执行文件: {filepath} ===')
    return run_dk_string(source, debug=debug, ctx=ctx)


def _print_ast(node, indent=0):
    p = '  ' * indent
    if node is None: print(f'{p}None'); return
    n = type(node).__name__; print(f'{p}{n}', end='')
    if hasattr(node, 'name'): print(f' ({node.name})', end='')
    if hasattr(node, 'op'): print(f' [{node.op}]', end='')
    if hasattr(node, 'value'): print(f' = {node.value!r}', end='')
    print()
    for a in dir(node):
        if a.startswith('_'): continue
        v = getattr(node, a)
        if a in ('name','op','value','var_type','return_type','dk_type'): continue
        if isinstance(v, list):
            for i in v:
                if hasattr(i, '__dict__'): _print_ast(i, indent+1)
        elif hasattr(v, '__dict__') and not isinstance(v, type):
            _print_ast(v, indent+1)
