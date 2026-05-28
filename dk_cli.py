#!/usr/bin/env python3
"""DK-Lang CLI — 为 DeepSeek 优化的编程语言解释器。
用法:
  python dk_cli.py run <file.dk>      执行 .dk 文件
  python dk_cli.py run -c "<code>"    执行内联代码
  python dk_cli.py repl              交互式 REPL
  python dk_cli.py debug <file.dk>   调试模式
  python dk_cli.py version           版本信息
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dklang import run_dk, run_dk_string, __version__

BANNER = fr"""
  ____  _  __     __                         
 |  _ \| |/ /    / /  __ _ _ __   __ _  ___ 
 | | | | ' /    / /  / _` | '_ \ / _` |/ _ \
 | |_| | . \   / /__| (_| | | | | (_| |  __/
 |____/|_|\_\  \____/\__,_|_| |_|\__, |\___|
                                  |___/    v{__version__}
  DeepSeek Knowledge Language
""".strip() + '\n'


def cmd_run(args):
    debug = '--debug' in args or '-d' in args
    if '-c' in args:
        idx = args.index('-c')
        if idx + 1 < len(args):
            return run_dk_string(args[idx + 1], debug=debug)
        print('错误: -c 需要代码参数'); return
    if not args: print('错误: 需要 .dk 文件路径'); return
    fp = args[0]
    if not os.path.exists(fp): print(f'错误: 文件不存在: {fp}'); return
    return run_dk(fp, debug=debug)


def cmd_repl():
    print(BANNER); print('DK-Lang REPL — 指令模式\n输入 :q 退出\n')
    buf = []; depth = 0
    while True:
        try:
            p = '... ' if depth > 0 else '>>> '
            line = input(p).rstrip()
            if not line and not buf: continue
            if line.startswith(':'):
                c = line[1:].strip()
                if c in ('q','quit','exit'): print('再见!'); break
                elif c in ('c','clear'): buf=[]; depth=0; print('已清空'); continue
                elif c in ('h','help'): print(':q 退出 :c 清空 :h 帮助'); continue
            depth += line.count('{') - line.count('}')
            buf.append(line)
            if depth <= 0:
                code = '\n'.join(buf); buf = []; depth = 0
                try:
                    r = run_dk_string(code, debug=False)
                    if r is not None: print(f'=> {r}')
                except Exception as e: print(f'错误: {e}')
                print()
        except KeyboardInterrupt: print('\n输入 :q 退出'); buf=[]; depth=0
        except EOFError: print('\n再见!'); break


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(BANNER)
        print('用法: python dk_cli.py [run|repl|debug|version] [args]')
    else:
        cmd = sys.argv[1].lower()
        if cmd == 'run': cmd_run(sys.argv[2:])
        elif cmd == 'repl': cmd_repl()
        elif cmd in ('version','-v','--version'): print(BANNER)
        elif cmd == 'debug': cmd_run(['--debug'] + sys.argv[2:])
        elif os.path.exists(sys.argv[1]) and sys.argv[1].endswith('.dk'):
            cmd_run(sys.argv[1:])
        else: print(f'未知命令: {cmd}')
