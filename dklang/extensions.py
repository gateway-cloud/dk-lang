"""
DK-Lang 扩展模块注册 —— 数据库 + HTTP 集成到解释器
"""
import sys, os, json, threading

def register_database_extensions(interpreter):
    """注册数据库相关内置函数"""
    from .database import Database, ConnectionPool, QueryBuilder

    def _db_connect(name: str, db_type: str, conn_str: str):
        db = Database.connect(name, db_type, conn_str)
        interpreter.glob.define(f'_db_{name}', db, True)
        return db

    def _db_execute(name: str, sql: str, params: str = '{}'):
        db = Database.get(name)
        if not db: raise RuntimeError(f'数据库 "{name}" 未连接')
        return db.execute(sql, json.loads(params) if params else None)

    def _db_insert(name: str, table: str, data_json: str):
        db = Database.get(name)
        if not db: raise RuntimeError(f'数据库 "{name}" 未连接')
        return db.insert(table, json.loads(data_json))

    def _db_select(name: str, table: str, filters_json: str = '{}'):
        db = Database.get(name)
        if not db: raise RuntimeError(f'数据库 "{name}" 未连接')
        return db.select(table, **json.loads(filters_json))

    def _db_table(name: str, table: str):
        db = Database.get(name)
        if not db: raise RuntimeError(f'数据库 "{name}" 未连接')
        return db.table(table)

    interpreter.glob.define('_db_connect', _db_connect, True)
    interpreter.glob.define('_db_execute', _db_execute, True)
    interpreter.glob.define('_db_insert', _db_insert, True)
    interpreter.glob.define('_db_select', _db_select, True)
    interpreter.glob.define('_db_table', _db_table, True)


def register_http_extensions(interpreter):
    """注册HTTP相关内置函数"""
    from .httpd import HttpClient, HttpServer, Router

    def _http_get(url: str, headers_json: str = '{}'):
        client = HttpClient()
        return client.get(url, json.loads(headers_json))

    def _http_post(url: str, body: str = '', headers_json: str = '{}'):
        client = HttpClient()
        return client.post(url, body, json.loads(headers_json))

    interpreter.glob.define('_http_get', _http_get, True)
    interpreter.glob.define('_http_post', _http_post, True)


def register_all(interpreter):
    """注册所有扩展"""
    try:
        register_database_extensions(interpreter)
        register_http_extensions(interpreter)
    except Exception as e:
        print(f'[扩展] 注册失败: {e}')
