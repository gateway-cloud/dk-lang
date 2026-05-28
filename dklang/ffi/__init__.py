"""DK-Lang FFI —— Python / C++ / Java 外部库导入。"""
import sys, os, importlib
from typing import Any

class FFIError(Exception): pass

class FFI:
    def load(self, lang: str, lib_name: str) -> Any:
        lang = lang.lower()
        if lang == 'python': return self._load_py(lib_name)
        if lang == 'cpp': return self._load_cpp(lib_name)
        if lang == 'java': return self._load_java(lib_name)
        raise FFIError(f'不支持的 FFI 语言: "{lang}"。支持: python, cpp, java')

    def _load_py(self, name):
        import importlib
        if name.startswith('.') or name.startswith('/') or ':' in name:
            import importlib.util
            path = os.path.abspath(name)
            if not os.path.exists(path): raise FFIError(f'Python 文件不存在: {path}')
            spec = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(path))[0], path)
            if not spec or not spec.loader: raise FFIError(f'无法加载: {path}')
            mod = importlib.util.module_from_spec(spec); sys.modules[spec.name] = mod; spec.loader.exec_module(mod)
            return mod
        try: return importlib.import_module(name)
        except ImportError as e: raise FFIError(f'无法导入 Python 模块 "{name}": {e}')

    def _load_cpp(self, name):
        import ctypes, ctypes.util
        path = name
        if not any(c in name for c in ('/','\\',':')):
            if sys.platform == 'win32' and not name.endswith('.dll'): path = name + '.dll'
            elif sys.platform == 'darwin' and not name.endswith('.dylib'): path = 'lib' + name + '.dylib'
            elif not name.endswith('.so'): path = 'lib' + name + '.so'
            found = ctypes.util.find_library(name)
            if found: path = found
        try:
            lib = ctypes.CDLL(path) if sys.platform == 'win32' else ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
            return lib
        except OSError as e: raise FFIError(f'无法加载 C++ 库 "{path}": {e}')

    def _load_java(self, name):
        try: import jpype
        except ImportError: raise FFIError('需要安装 JPype: pip install jpype1')
        if not jpype.isJVMStarted():
            java_home = os.environ.get('JAVA_HOME', '')
            jvm_path = None
            if java_home:
                if sys.platform == 'win32':
                    for p in [os.path.join(java_home,'bin','server','jvm.dll'),
                              os.path.join(java_home,'jre','bin','server','jvm.dll')]:
                        if os.path.exists(p): jvm_path = p; break
            try:
                if jvm_path and os.path.exists(jvm_path): jpype.startJVM(jvm_path, classpath=['.'], convertStrings=True)
                else: jpype.startJVM(classpath=['.'], convertStrings=True)
            except Exception as e: raise FFIError(f'无法启动 JVM: {e}\n请确保已安装 Java 并设置 JAVA_HOME')
        try: return jpype.JClass(name)
        except Exception as e: raise FFIError(f'无法加载 Java 类 "{name}": {e}')
