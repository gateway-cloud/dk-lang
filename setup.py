"""
DK-Lang MSI 安装程序 v1.4.0
功能: 自定义安装路径 | PATH环境变量 | 已安装检测 | 进度条
"""
import sys, os
from cx_Freeze import setup, Executable

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(PROJECT_ROOT, 'build', 'msi')

executables = [
    Executable(
        script=os.path.join(PROJECT_ROOT, 'dk_cli.py'),
        target_name='dk.exe',
        base='Console',
        icon=os.path.join(PROJECT_ROOT, 'dk.ico') if os.path.exists(os.path.join(PROJECT_ROOT, 'dk.ico')) else None,
    ),
]

build_exe_options = {
    'packages': ['dklang', 'dklang.ffi'],
    'includes': ['dklang.database', 'dklang.httpd', 'dklang.extensions',
                 'json', 'os', 'sys', 're', 'time', 'math', 'random',
                 'threading', 'base64', 'urllib.request', 'urllib.parse',
                 'sqlite3', 'socket', 'traceback', 'importlib.util',
                 'pathlib', 'ctypes', 'enum', 'dataclasses', 'typing',
                 'http.server', 'subprocess', 'hashlib', 'struct'],
    'excludes': ['tkinter', 'unittest', 'distutils', 'setuptools',
                 'numpy', 'pandas', 'PIL', 'matplotlib', 'test'],
    # 仅包含文档，不包含示例和测试文件
    'include_files': [
        (os.path.join(PROJECT_ROOT, 'DK-LANG-SPEC.md'), 'doc/DK-LANG-SPEC.md'),
        (os.path.join(PROJECT_ROOT, 'DEVELOPER.md'), 'doc/DEVELOPER.md'),
    ],
    'optimize': 2,
    'build_exe': BUILD_DIR,
}

# 升级后的 MSI 选项
bdist_msi_options = {
    'add_to_path': True,          # 添加 PATH 环境变量（安装时可选择）
    'all_users': False,           # 每用户安装（也可选所有用户）
    'upgrade_code': '{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}',
    'initial_target_dir': os.path.join(
        os.environ.get('ProgramFiles', 'C:\\Program Files'), 'DK-Lang'
    ),
    'install_icon': os.path.join(PROJECT_ROOT, 'dk.ico') if os.path.exists(os.path.join(PROJECT_ROOT, 'dk.ico')) else None,
}

setup(
    name='DK-Lang',
    version='1.4.0',
    description='DK-Lang (DeepSeek Knowledge Language) — AI-Optimized Programming Language v1.4',
    long_description=(
        'DK-Lang (谛刻语言) is a programming language optimized for DeepSeek AI models.\n'
        'Features: Low-ambiguity syntax, explicit structure, AI-native operations.\n'
        'v1.4: SERVER/ROUTE/MIDDLEWARE for HTTP servers, multi-line strings,\n'
        '      ARR_LEN, bare operators, nested CALL fix, 10+ bug fixes from industrial audit.'
    ),
    author='DK-Lang Foundation',
    options={
        'build_exe': build_exe_options,
        'bdist_msi': bdist_msi_options,
    },
    executables=executables,
)
