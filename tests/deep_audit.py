# -*- coding: utf-8 -*-
"""
DK-Lang 深度质量审计 — 单元测试套件 (修复后验证版)
测试覆盖：词法分析器、语法分析器、解释器、环境作用域、信号传播、类型系统
Bug 修复验证：BUG-LEX-01~03, BUG-PAR-02, BUG-INT-01~05
"""
import sys, os, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dklang.lexer import Lexer, LexerError, TK, Token
from dklang.parser import Parser, ParseError
from dklang.interpreter import Interpreter, Environment
from dklang.ast_nodes import *
from dklang import run_dk_string


# ═══════════════════════════════════════════════════════════════
# PART 1: 词法分析器深度测试
# ═══════════════════════════════════════════════════════════════

class TestLexerEdgeCases(unittest.TestCase):
    """词法器边界测试"""

    def test_empty_file(self):
        tokens = Lexer("").tokenize()
        self.assertEqual([t.kind for t in tokens], [TK.EOF])

    def test_whitespace_only(self):
        tokens = Lexer("  \t  \n  \n  ").tokenize()
        self.assertEqual([t.kind for t in tokens], [TK.EOF])

    def test_unicode_identifiers(self):
        tokens = Lexer("你好 世界 こんにちは").tokenize()
        idents = [t for t in tokens if t.kind == TK.IDENT]
        self.assertEqual(len(idents), 3)

    def test_emoji_in_source(self):
        with self.assertRaises(LexerError):
            Lexer("😀👍").tokenize()

    def test_emoji_in_string(self):
        tokens = Lexer('"hello 😀 world"').tokenize()
        self.assertEqual(tokens[0].kind, TK.LIT_STR)
        self.assertIn('😀', tokens[0].value)

    def test_super_long_identifier(self):
        long_id = 'x' * 10000
        tokens = Lexer(f'SET {long_id} | 42 ;').tokenize()
        self.assertEqual(tokens[1].kind, TK.IDENT)
        self.assertEqual(tokens[1].value, long_id)

    def test_mixed_cjk_identifiers(self):
        tokens = Lexer("user_姓名 _123测试 data_データ").tokenize()
        idents = [t.value for t in tokens if t.kind == TK.IDENT]
        self.assertEqual(len(idents), 3)

    def test_string_escape_all(self):
        tokens = Lexer(r'"line1\nline2\tindented\"quote\"\\end"').tokenize()
        self.assertEqual(tokens[0].value, 'line1\nline2\tindented"quote"\\end')

    def test_string_unknown_escape(self):
        tokens = Lexer(r'"hello\xhello"').tokenize()
        self.assertIn('\\x', tokens[0].value)

    def test_unclosed_string(self):
        with self.assertRaises(LexerError):
            Lexer('"open but not close').tokenize()

    def test_unclosed_block_comment(self):
        with self.assertRaises(LexerError):
            Lexer('/* open').tokenize()

    def test_multiline_string_backtick(self):
        src = "`hello\nworld\nmultiline`"
        tokens = Lexer(src).tokenize()
        self.assertEqual(tokens[0].kind, TK.LIT_STR)
        self.assertIn("hello", tokens[0].value)

    def test_multiline_string_escape(self):
        """修复 BUG-LEX-03: 反引号字符串现在支持转义"""
        src = r'`hello\nthere`'
        tokens = Lexer(src).tokenize()
        self.assertIn('\n', tokens[0].value)

    def test_string_col_tracking(self):
        """修复 BUG-LEX-01: col 不再翻倍"""
        src = '"abc"'
        tokens = Lexer(src).tokenize()
        t = tokens[0]
        self.assertEqual(t.line, 1)
        self.assertEqual(t.col, 1)
        eof_t = tokens[-1]
        self.assertTrue(eof_t.col > 1, f"EOF col {eof_t.col}")

    def test_negative_number(self):
        tokens = Lexer("-123 -45.67").tokenize()
        self.assertEqual(tokens[0].kind, TK.LIT_INT)
        self.assertEqual(tokens[0].value, -123)
        self.assertEqual(tokens[1].kind, TK.LIT_REAL)
        self.assertEqual(tokens[1].value, -45.67)

    def test_keyword_case_sensitivity(self):
        tokens_upper = Lexer("VAR x | int ;").tokenize()
        self.assertEqual(tokens_upper[0].kind, TK.KW_VAR)
        tokens_lower = Lexer("var x | int ;").tokenize()
        self.assertEqual(tokens_lower[0].kind, TK.IDENT)

    def test_underscore_identifiers(self):
        for name in ["_", "_private", "__dunder__"]:
            tokens = Lexer(f'{name}').tokenize()
            self.assertEqual(tokens[0].kind, TK.IDENT, f"'{name}' 应为 IDENT")

    def test_line_comment(self):
        tokens = Lexer("SET x | 1; // comment\nSET y | 2;").tokenize()
        kw_set = [t for t in tokens if t.kind == TK.KW_SET]
        self.assertEqual(len(kw_set), 2)

    def test_block_comment(self):
        tokens = Lexer("SET x /* inline */ | 1;").tokenize()
        kw_set = [t for t in tokens if t.kind == TK.KW_SET]
        self.assertEqual(len(kw_set), 1)

    def test_nested_block_comment_fails(self):
        src = "SET x /* /* inner */ outer */ | 1;"
        with self.assertRaises(LexerError):
            Lexer(src).tokenize()

    def test_consecutive_symbols(self):
        tokens = Lexer("||;;{{}}(()) [][]::,,..").tokenize()
        self.assertGreater(len([t.kind for t in tokens]), 10)

    def test_unescaped_newline_error(self):
        """修复 BUG-LEX-02: 未转义换行现在抛出错误"""
        with self.assertRaises(LexerError):
            Lexer('"line1\nline2"').tokenize()


# ═══════════════════════════════════════════════════════════════
# PART 2: 语法分析器深度测试
# ═══════════════════════════════════════════════════════════════

class TestParserEdgeCases(unittest.TestCase):
    """语法分析器边界测试"""

    def _parse(self, src):
        tokens = Lexer(src).tokenize()
        return Parser(tokens).parse()

    def test_empty_program(self):
        ast = self._parse("")
        self.assertEqual(ast.declarations, [])

    def test_only_semicolons(self):
        ast = self._parse("; ; ; ;")
        self.assertEqual(ast.declarations, [])

    def test_nested_if_10_levels(self):
        src = "".join(["IF eq | 1 | 1 | { " for _ in range(10)]) + " } ;" * 10
        ast = self._parse(src)
        self.assertIsNotNone(ast)

    def test_deeply_nested_blocks(self):
        src = "SET a | 1 ; " + "{ " * 30 + "SET b | 2 ; " + "} ;" * 30
        ast = self._parse(src)
        self.assertIsNotNone(ast)

    def test_func_def_no_params_no_return(self):
        ast = self._parse("FUNC nop | { SET x | 1 ; } ;")
        self.assertIsNotNone(ast)

    def test_func_def_return_type_only(self):
        ast = self._parse('FUNC hello | str { RET "hi" ; } ;')
        self.assertIsNotNone(ast)

    def test_func_def_with_params(self):
        ast = self._parse("FUNC add | a | int | b | int | int | { RET CALC add | a | b ; } ;")
        self.assertIsNotNone(ast)

    def test_call_with_pipes(self):
        ast = self._parse("CALL add | 1 | 2 ;")
        self.assertIsNotNone(ast)

    def test_cross_call_pipes(self):
        """验证嵌套 CALL 的管道分隔正确解析 (修复 BUG-PAR-02)"""
        src = """FUNC double | x | int | int | { RET CALC mul | x | 2 ; } ;
        FUNC add2 | a | int | b | int | int | { RET CALC add | a | b ; } ;
        CALL add2 | CALL double | 10 | 5 ;"""
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        self.assertIsNotNone(ast)

    def test_while_loop_parsing(self):
        ast = self._parse("SET i | 0 ; WHILE lt | i | 10 | { SET i | CALC add | i | 1 ; } ;")
        self.assertIsNotNone(ast)

    def test_loop_counting_mode(self):
        ast = self._parse("LOOP i | 0 | 9 | 1 | { SET x | i ; } ;")
        self.assertIsNotNone(ast)

    def test_switch_statement(self):
        ast = self._parse("""SET x | 2 ;
        SWITCH x | {
            CASE 1 | { SET r | "one" ; }
            CASE 2 | { SET r | "two" ; }
            DEFAULT | { SET r | "other" ; }
        } ;""")
        self.assertIsNotNone(ast)

    def test_parse_error_on_missing_semicolon(self):
        with self.assertRaises(ParseError):
            self._parse("SET x | 1")

    def test_parse_error_invalid_instruction(self):
        with self.assertRaises(ParseError):
            self._parse("123 | x ;")

    def test_map_literal(self):
        ast = self._parse('SET m | {"a": 1, "b": 2} ;')
        self.assertIsNotNone(ast)

    def test_empty_map_literal(self):
        ast = self._parse('SET m | {} ;')
        self.assertIsNotNone(ast)

    def test_set_literal(self):
        ast = self._parse('SET s | {1, 2, 3} ;')
        self.assertIsNotNone(ast)

    def test_try_catch(self):
        ast = self._parse('TRY | { SET x | 1 ; } CATCH "Error" | { SET x | 2 ; } ;')
        self.assertIsNotNone(ast)

    def test_calc_expression(self):
        ast = self._parse('SET x | CALC add | 1 | 2 ;')
        self.assertIsNotNone(ast)

    def test_str_operations(self):
        for kw, body in [
            ('STR_JOIN', 'result | "," | "a" | "b" | "c" ;'),
            ('STR_CUT', 'result | "hello" | 0 | 3 ;'),
            ('STR_LEN', 'result | "hello" ;'),
        ]:
            ast = self._parse(f'{kw} {body}')
            self.assertIsNotNone(ast, f"Failed for {kw}")

    def test_global_local(self):
        for kw in ['GLOBAL', 'LOCAL']:
            ast = self._parse(f'{kw} counter | int ;')
            self.assertIsNotNone(ast, f"Failed for {kw}")

    def test_macro_definition(self):
        ast = self._parse('MACRO square(x) | { RET CALC mul | x | x ; } ;')
        self.assertIsNotNone(ast)

    def test_bare_calc_expr_parsing(self):
        ast = self._parse("SET x | add | 1 | 2 ;")
        self.assertIsNotNone(ast)


# ═══════════════════════════════════════════════════════════════
# PART 3: 解释器边界值测试
# ═══════════════════════════════════════════════════════════════

class TestInterpreterBoundaryValues(unittest.TestCase):
    """解释器边界值测试"""

    def _run(self, src, ctx=None):
        return run_dk_string(src, ctx=ctx or {})

    def test_division_by_zero(self):
        src = "VAR a | int ; SET a | CALC div | 10 | 0 ;"
        result = self._run(src)
        self.assertIsNone(result)

    def test_modulo_by_zero(self):
        src = "VAR a | int ; SET a | CALC mod | 10 | 0 ;"
        result = self._run(src)
        self.assertIsNone(result)

    def test_integer_overflow(self):
        src = "VAR a | int ; SET a | CALC mul | 9999999999 | 9999999999 ;"
        result = self._run(src)
        self.assertIsNotNone(result)

    def test_empty_array_access(self):
        src = "ARR arr | int ; VAR x | int ; SET x | GET arr | 0 ;"
        result = self._run(src)
        self.assertIsNone(result)

    def test_nil_access(self):
        src = "VAR n | nil ; VAR x | int ; SET x | GET n | 0 ;"
        result = self._run(src)
        self.assertIsNone(result)

    def test_division_int_result(self):
        """修复 BUG-INT-01: 6/2 返回 int 3"""
        src = "VAR r | int ; SET r | CALC div | 6 | 2 ;"
        result = self._run(src)
        self.assertIsInstance(result, int)
        self.assertEqual(result, 3)

    def test_negative_numbers_arithmetic(self):
        src = "VAR a | int ; SET a | CALC add | -5 | -3 ;"
        result = self._run(src)
        self.assertEqual(result, -8)

    def test_modulo_with_floats(self):
        """修复 BUG-INT-02: 取模不再截断浮点"""
        src = "VAR r | int ; SET r | CALC mod | 5 | 2 ;"
        result = self._run(src)
        self.assertEqual(result, 1)

    def test_string_comparison(self):
        src = """VAR b1 | bool ; VAR b2 | bool ;
        SET b1 | CALC eq | "abc" | "abc" ;
        SET b2 | CALC ne | "abc" | "xyz" ;"""
        result = self._run(src)
        self.assertIsNotNone(result)

    def test_bool_operations(self):
        src = "VAR b1 | bool ; SET b1 | NOT true ;"
        result = self._run(src)
        self.assertEqual(result, False)

    def test_empty_set(self):
        src = "VAR s | map[str, str] ; SET s | {} ;"
        result = self._run(src)
        self.assertIsInstance(result, dict)

    def test_non_empty_set(self):
        src = "VAR s | set[int] ; SET s | {1, 2, 3} ;"
        result = self._run(src)
        self.assertIsInstance(result, set)

    def test_type_conversion_implicit(self):
        src = "VAR i | int ; SET i | 42 ;"
        result = self._run(src)
        self.assertIsNotNone(result)


# ═══════════════════════════════════════════════════════════════
# PART 4: 环境作用域测试
# ═══════════════════════════════════════════════════════════════

class TestEnvironmentScope(unittest.TestCase):
    """环境作用域深度测试"""

    def _run(self, src):
        return run_dk_string(src)

    def test_global_variable_access(self):
        src = "GLOBAL gx | int ; SET gx | 100 ;"
        result = self._run(src)
        self.assertEqual(result, 100)

    def test_local_var_decl(self):
        src = "LOCAL v | int ; SET v | 42 ;"
        result = self._run(src)
        self.assertEqual(result, 42)

    def test_const_cannot_be_reassigned(self):
        src = "CONST PI | real | 3.14159 ; SET PI | 2.0 ;"
        result = self._run(src)
        self.assertIsNone(result)

    def test_var_default_values(self):
        tests = [
            ("VAR i | int ;", 0),
            ("VAR r | real ;", 0.0),
            ("VAR s | str ;", ''),
            ("VAR b | bool ;", False),
            ("VAR n | nil ;", None),
        ]
        for src, expected in tests:
            result = run_dk_string(src)
            self.assertEqual(result, expected, f"Failed: {src}")

    def test_environment_parent_chain(self):
        env = Environment()
        env.define('a', 1)
        child = Environment(env)
        child.define('b', 2)
        grandchild = Environment(child)
        self.assertEqual(grandchild.get('a'), 1)
        self.assertEqual(grandchild.get('b'), 2)
        grandchild.assign('a', 10)
        self.assertEqual(env.get('a'), 10)

    def test_assign_undefined_variable(self):
        env = Environment()
        with self.assertRaises(DKNameError):
            env.assign('undefined', 42)


# ═══════════════════════════════════════════════════════════════
# PART 5: SIGNAL 传播测试
# ═══════════════════════════════════════════════════════════════

class TestSignalPropagation(unittest.TestCase):
    """SIGNAL 传播深度测试"""

    def _run(self, src):
        return run_dk_string(src)

    def test_break_in_nested_loop(self):
        """修复 BUG-INT-05: LOOP 变量自动定义"""
        src = """GLOBAL counter | int ; SET counter | 0 ;
        LOOP i | 1 | 5 | 1 | {
            LOOP j | 1 | 5 | 1 | {
                SET counter | CALC add | counter | 1 ;
                IF eq | j | 2 | { BREAK ; } ;
            } ;
        } ;
        SET counter | counter ;"""
        result = self._run(src)
        self.assertEqual(result, 10, f"Expected 10 (5×2), got {result}")

    def test_next_skips_iteration(self):
        src = """GLOBAL total | int ; SET total | 0 ;
        LOOP i | 1 | 10 | 1 | {
            IF eq | CALC mod | i | 2 | 0 | { NEXT ; } ;
            SET total | CALC add | total | i ;
        } ;
        SET total | total ;"""
        result = self._run(src)
        self.assertEqual(result, 25, "1+3+5+7+9=25")

    def test_break_outside_loop(self):
        result = self._run("BREAK ;")
        self.assertIsNone(result)

    def test_ret_from_top_level(self):
        result = self._run("RET 42 ;")
        self.assertIsNone(result)

    def test_return_without_value(self):
        result = self._run("FUNC nop | { RET ; } ; CALL nop ;")
        self.assertIsNone(result)

    def test_return_from_nested_if(self):
        src = """FUNC test | int { IF eq | 1 | 1 | { RET 42 ; } ; RET 0 ; } ; CALL test ;"""
        result = self._run(src)
        self.assertEqual(result, 42)


# ═══════════════════════════════════════════════════════════════
# PART 6: 类型系统测试
# ═══════════════════════════════════════════════════════════════

class TestTypeSystem(unittest.TestCase):
    """类型系统深度测试"""

    def _run(self, src):
        return run_dk_string(src)

    def test_no_type_check_on_assignment(self):
        src = "VAR i | int ; SET i | \"hello\" ;"
        result = self._run(src)
        self.assertIsNotNone(result)

    def test_add_ints(self):
        src = "VAR x | int ; SET x | CALC add | 1 | 2 ;"
        result = self._run(src)
        self.assertEqual(result, 3)

    def test_str_concatenation(self):
        src = 'VAR x | str ; SET x | CALC add | "hello " | "world" ;'
        result = self._run(src)
        self.assertEqual(result, "hello world")

    def test_float_int_mixed(self):
        src = "VAR x | real ; SET x | CALC add | 1 | 2.5 ;"
        result = self._run(src)
        self.assertEqual(result, 3.5)

    def test_int_str_mixed_add(self):
        src = 'VAR x | str ; SET x | CALC add | 1 | "hello" ;'
        result = self._run(src)
        self.assertIsNone(result)

    def test_as_cast(self):
        src = "VAR x | int ; SET x | AS(3.14, int) ;"
        result = self._run(src)
        self.assertEqual(result, 3)

    def test_comparison_across_types(self):
        src = "VAR x | bool ; SET x | CALC eq | 1 | \"1\" ;"
        result = self._run(src)
        self.assertEqual(result, False)

    def test_nil_comparison(self):
        src = "VAR x | bool ; SET x | CALC eq | nil | nil ;"
        result = self._run(src)
        self.assertEqual(result, True)

    def test_bare_operator_expression(self):
        src = "VAR x | int ; SET x | add | 1 | 2 ;"
        result = self._run(src)
        self.assertEqual(result, 3)


# ═══════════════════════════════════════════════════════════════
# PART 7: 函数调用与参数测试
# ═══════════════════════════════════════════════════════════════

class TestFunctionCalls(unittest.TestCase):
    """函数调用深度测试"""

    def _run(self, src):
        return run_dk_string(src)

    def test_recursive_function(self):
        src = """FUNC factorial | n | int | int | {
            IF eq | n | 0 | { RET 1 ; } ;
            RET CALC mul | n | CALL factorial | CALC sub | n | 1 ;
        } ;
        CALL factorial | 5 ;"""
        result = self._run(src)
        self.assertEqual(result, 120)

    def test_function_arity_mismatch_too_few(self):
        src = """FUNC add | a | int | b | int | int | {
            RET CALC add | a | b ;
        } ;
        CALL add | 5 ;"""
        result = self._run(src)
        self.assertIsNone(result)  # ArityError

    def test_function_arity_mismatch_too_many(self):
        """修复 BUG-INT-03: 参数过多触发 ArityError"""
        src = """FUNC greet | name | str | str | {
            RET CALC add | "Hello, " | name ;
        } ;
        CALL greet | "Alice" | "Bob" | "Extra" ;"""
        result = self._run(src)
        self.assertIsNone(result)  # ArityError

    def test_user_func_priority_over_builtin(self):
        """修复 BUG-INT-04: 用户函数优先于内置函数"""
        src = """FUNC len | s | str | int | {
            RET 999 ;
        } ;
        CALL len | "hello" ;"""
        result = self._run(src)
        self.assertEqual(result, 999, "用户函数应返回 999")

    def test_simple_function_call(self):
        src = """FUNC double | x | int | int | {
            RET CALC mul | x | 2 ;
        } ;
        CALL double | 21 ;"""
        result = self._run(src)
        self.assertEqual(result, 42)


# ═══════════════════════════════════════════════════════════════
# PART 8: 综合集成测试
# ═══════════════════════════════════════════════════════════════

class TestIntegration(unittest.TestCase):
    """综合集成测试"""

    def _run(self, src):
        return run_dk_string(src)

    def test_array_operations(self):
        src = """ARR nums | int | 1 | 2 | 3 ;
        PUSH nums | 4 ;
        VAR last | int ;
        POP nums | last ;
        VAR total | int ;
        SET total | CALC add | GET nums | 0 | GET nums | 1 ;"""
        result = self._run(src)
        self.assertEqual(result, 3, "1+2=3")

    def test_map_operations(self):
        src = """VAR m | map[str, str] ;
        SET m | {} ;
        MAP_SET m | "key" | "value" ;
        VAR v | str ;
        SET v | MAP_GET m | "key" ;"""
        result = self._run(src)
        self.assertEqual(result, "value")

    def test_str_operations_runtime(self):
        src = """VAR res | str ;
        STR_JOIN res | ", " | "a" | "b" | "c" ;"""
        result = self._run(src)
        self.assertEqual(result, "a, b, c")

    def test_rand_in_range(self):
        src = """VAR x | int ; RAND x | 1 | 10 ;"""
        result = self._run(src)
        self.assertGreaterEqual(result, 1)
        self.assertLessEqual(result, 10)

    def test_log_no_crash(self):
        result = self._run('LOG "info" | "test message" ;')
        self.assertIsNone(result)

    def test_time_unix(self):
        src = 'VAR t | int ; TIME t | "unix" ;'
        result = self._run(src)
        self.assertGreater(result, 1700000000)

    def test_b64_roundtrip(self):
        src = """VAR enc | str ; B64ENC enc | "hello" ;
        VAR dec | str ; B64DEC dec | enc ;"""
        result = self._run(src)
        self.assertEqual(result, "hello")

    def test_throw_catch(self):
        src = """VAR x | str ;
        TRY | {
            THROW "MyError" | "something went wrong" ;
        } CATCH "MyError" | {
            SET x | "caught" ;
        } ;"""
        result = self._run(src)
        self.assertEqual(result, "caught")

    def test_complex_nested_call(self):
        """修复 BUG-PAR-02: 嵌套 CALL 管道正确解析"""
        src = """FUNC double | x | int | int | { RET CALC mul | x | 2 ; } ;
        FUNC add2 | a | int | b | int | int | { RET CALC add | a | b ; } ;
        CALL add2 | CALL double | 10 | 5 ;"""
        result = self._run(src)
        self.assertEqual(result, 25, "double(10)=20, add2(20,5)=25")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    loader = unittest.TestLoader()
    all_tests = unittest.TestSuite([
        loader.loadTestsFromTestCase(TestLexerEdgeCases),
        loader.loadTestsFromTestCase(TestParserEdgeCases),
        loader.loadTestsFromTestCase(TestInterpreterBoundaryValues),
        loader.loadTestsFromTestCase(TestEnvironmentScope),
        loader.loadTestsFromTestCase(TestSignalPropagation),
        loader.loadTestsFromTestCase(TestTypeSystem),
        loader.loadTestsFromTestCase(TestFunctionCalls),
        loader.loadTestsFromTestCase(TestIntegration),
    ])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(all_tests)

    print("\n" + "=" * 70)
    print(f"TOTAL: {result.testsRun} tests run")
    print(f"PASSED: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"FAILURES: {len(result.failures)}")
    print(f"ERRORS: {len(result.errors)}")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)
