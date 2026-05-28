"""
DK-Lang 数据库引擎 —— 工业级 SQLite/MySQL/PostgreSQL 统一接口
特性：连接池、查询构造器、ORM、事务、批量操作、迁移、软删除
"""
import sqlite3, threading, time, json, re, os
from contextlib import contextmanager
from typing import Any, List, Dict, Optional, Callable, Union


class ConnectionPool:
    """线程安全连接池"""
    def __init__(self, db_type: str, conn_str: str, pool_size: int = 5, max_overflow: int = 10):
        self.db_type = db_type
        self.conn_str = conn_str
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._pool: List = []
        self._in_use: set = set()
        self._lock = threading.Lock()
        self._sem = threading.Semaphore(pool_size + max_overflow)
        self._created = 0

    def _create_conn(self):
        if self.db_type == 'sqlite':
            path = self.conn_str.replace('sqlite://', '')
            conn = sqlite3.connect(path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        elif self.db_type == 'mysql':
            import pymysql
            # conn_str: mysql://user:pass@host:port/db
            m = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):?(\d+)?/(.+)', self.conn_str)
            if m:
                user, pwd, host, port, db = m.groups()
                port = int(port) if port else 3306
                return pymysql.connect(host=host, port=port, user=user, password=pwd, database=db,
                                       charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
        elif self.db_type == 'postgresql':
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(self.conn_str)
            conn.cursor_factory = psycopg2.extras.RealDictCursor
            return conn
        raise ValueError(f'不支持的数据库类型: {self.db_type}')

    @contextmanager
    def get_conn(self):
        self._sem.acquire()
        with self._lock:
            if self._pool:
                conn = self._pool.pop()
            elif self._created < self.pool_size + self.max_overflow:
                conn = self._create_conn()
                self._created += 1
            else:
                self._sem.release()
                raise RuntimeError('连接池耗尽')
            self._in_use.add(id(conn))
        try:
            yield conn
        finally:
            with self._lock:
                self._in_use.discard(id(conn))
                if len(self._pool) < self.pool_size:
                    self._pool.append(conn)
                else:
                    conn.close()
                    self._created -= 1
            self._sem.release()

    def close_all(self):
        with self._lock:
            for conn in self._pool:
                conn.close()
            self._pool.clear()
            self._created = 0


class QueryBuilder:
    """类型安全的查询构造器"""
    def __init__(self, table: str):
        self._table = table
        self._select = ['*']
        self._where = []
        self._where_params = []
        self._order = []
        self._limit = None
        self._offset = None
        self._join = []
        self._group = []
        self._having = []

    def select(self, *columns):
        self._select = list(columns) if columns else ['*']; return self

    def where(self, column: str, op: str, value):
        param_name = f'__p{len(self._where_params)}'
        self._where.append(f'{column} {op} :{param_name}')
        self._where_params.append((param_name, value))
        return self

    def where_raw(self, condition: str, **params):
        self._where.append(condition)
        for k, v in params.items():
            self._where_params.append((k, v))
        return self

    def order_by(self, column: str, desc: bool = False):
        self._order.append(f'{column} {"DESC" if desc else "ASC"}'); return self

    def limit(self, n: int): self._limit = n; return self
    def offset(self, n: int): self._offset = n; return self

    def join(self, table: str, on: str, jtype: str = 'INNER'):
        self._join.append(f'{jtype} JOIN {table} ON {on}'); return self

    def group_by(self, *columns):
        self._group = list(columns); return self

    def having(self, condition: str, **params):
        self._having.append(condition)
        for k, v in params.items(): self._where_params.append((k, v))
        return self

    def build_select(self) -> tuple:
        sql = f'SELECT {", ".join(self._select)} FROM {self._table}'
        if self._join: sql += ' ' + ' '.join(self._join)
        if self._where: sql += ' WHERE ' + ' AND '.join(self._where)
        if self._group: sql += ' GROUP BY ' + ', '.join(self._group)
        if self._having: sql += ' HAVING ' + ' AND '.join(self._having)
        if self._order: sql += ' ORDER BY ' + ', '.join(self._order)
        if self._limit is not None: sql += f' LIMIT {self._limit}'
        if self._offset is not None: sql += f' OFFSET {self._offset}'
        params = {k: v for k, v in self._where_params}
        return sql, params

    def build_insert(self, data: dict) -> tuple:
        cols = ', '.join(data.keys())
        placeholders = ', '.join(f':{k}' for k in data.keys())
        sql = f'INSERT INTO {self._table} ({cols}) VALUES ({placeholders})'
        return sql, data

    def build_update(self, data: dict) -> tuple:
        sets = ', '.join(f'{k} = :set_{k}' for k in data.keys())
        sql = f'UPDATE {self._table} SET {sets}'
        if self._where: sql += ' WHERE ' + ' AND '.join(self._where)
        params = {f'set_{k}': v for k, v in data.items()}
        params.update({k: v for k, v in self._where_params})
        return sql, params

    def build_delete(self) -> tuple:
        sql = f'DELETE FROM {self._table}'
        if self._where: sql += ' WHERE ' + ' AND '.join(self._where)
        return sql, {k: v for k, v in self._where_params}


class Database:
    """统一数据库访问接口"""
    _instances: Dict[str, 'Database'] = {}

    @classmethod
    def connect(cls, name: str, db_type: str, conn_str: str, **kwargs) -> 'Database':
        if name in cls._instances:
            return cls._instances[name]
        db = Database(db_type, conn_str, **kwargs)
        cls._instances[name] = db
        return db

    @classmethod
    def get(cls, name: str) -> 'Database':
        return cls._instances.get(name)

    def __init__(self, db_type: str, conn_str: str, pool_size: int = 5):
        self.db_type = db_type
        self.conn_str = conn_str
        self.pool = ConnectionPool(db_type, conn_str, pool_size)
        self._orm_registry: Dict[str, type] = {}

    def table(self, name: str) -> QueryBuilder:
        return QueryBuilder(name)

    def execute(self, sql: str, params: dict = None) -> Any:
        """执行原始SQL"""
        with self.pool.get_conn() as conn:
            cur = conn.cursor()
            if params:
                # 转换 :param 风格到 ? 风格 (SQLite)
                if self.db_type == 'sqlite':
                    named_params = re.findall(r':(\w+)', sql)
                    positional = []
                    new_sql = sql
                    for i, np in enumerate(named_params):
                        new_sql = new_sql.replace(f':{np}', '?', 1)
                        positional.append(params.get(np))
                    cur.execute(new_sql, positional)
                else:
                    cur.execute(sql, params)
            else:
                cur.execute(sql)
            if sql.strip().upper().startswith(('SELECT', 'PRAGMA', 'WITH', 'EXPLAIN')):
                rows = cur.fetchall()
                if self.db_type == 'sqlite':
                    return [dict(row) for row in rows]
                return rows
            conn.commit()
            return cur.rowcount if hasattr(cur, 'rowcount') else None

    def execute_many(self, sql: str, params_list: List[dict]) -> int:
        """批量操作"""
        count = 0
        with self.pool.get_conn() as conn:
            cur = conn.cursor()
            for params in params_list:
                if self.db_type == 'sqlite':
                    named = re.findall(r':(\w+)', sql)
                    positional = [params.get(n) for n in named]
                    cur.execute(re.sub(r':\w+', '?', sql), positional)
                else:
                    cur.execute(sql, params)
                count += cur.rowcount
            conn.commit()
        return count

    def insert(self, table: str, data: Union[dict, List[dict]]) -> Any:
        """插入数据"""
        if isinstance(data, list):
            return self.execute_many(*self.table(table).build_insert(data[0])[:1], data)
        sql, params = self.table(table).build_insert(data)
        with self.pool.get_conn() as conn:
            cur = conn.cursor()
            if self.db_type == 'sqlite':
                cols = list(data.keys())
                placeholders = ','.join(['?'] * len(cols))
                sql2 = f'INSERT INTO {table} ({",".join(cols)}) VALUES ({placeholders})'
                cur.execute(sql2, list(data.values()))
            else:
                cur.execute(sql, params)
            conn.commit()
            return cur.lastrowid if hasattr(cur, 'lastrowid') else None

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        with self.pool.get_conn() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def select(self, table: str, **kwargs) -> List[dict]:
        qb = self.table(table)
        for k, v in kwargs.items():
            if '__' in k:
                col, op = k.rsplit('__', 1)
                op_map = {'gt': '>', 'lt': '<', 'gte': '>=', 'lte': '<=', 'eq': '=', 'ne': '!=', 'like': 'LIKE', 'in': 'IN'}
                qb.where(col, op_map.get(op, '='), v)
            else:
                qb.where(k, '=', v)
        sql, params = qb.build_select()
        return self.execute(sql, params)

    # ── ORM 功能 ──
    def register_model(self, model_class):
        self._orm_registry[model_class.__name__] = model_class
        model_class._db = self

    def create_table(self, model_class):
        """自动建表（迁移）"""
        table = model_class._table or model_class.__name__.lower()
        cols = []
        for name, field in model_class._fields.items():
            col_def = f'{name} {field.db_type}'
            if field.primary_key: col_def += ' PRIMARY KEY AUTOINCREMENT'
            if field.unique: col_def += ' UNIQUE'
            if field.nullable is False: col_def += ' NOT NULL'
            if field.default is not None: col_def += f' DEFAULT {field.default!r}'
            cols.append(col_def)
        if model_class._soft_delete:
            cols.append('deleted_at TIMESTAMP NULL')
        sql = f'CREATE TABLE IF NOT EXISTS {table} ({", ".join(cols)})'
        self.execute(sql)

    def drop_table(self, model_class):
        self.execute(f'DROP TABLE IF EXISTS {model_class._table}')


class Field:
    """ORM 字段定义"""
    def __init__(self, db_type: str = 'TEXT', primary_key: bool = False, unique: bool = False,
                 nullable: bool = True, default: Any = None, max_length: int = None,
                 validators: List[Callable] = None):
        self.db_type = db_type
        self.primary_key = primary_key
        self.unique = unique
        self.nullable = nullable
        self.default = default
        self.max_length = max_length
        self.validators = validators or []

    def validate(self, value) -> bool:
        if not self.nullable and value is None:
            raise ValueError('字段不可为空')
        if self.max_length and value and len(str(value)) > self.max_length:
            raise ValueError(f'超出最大长度 {self.max_length}')
        for v in self.validators:
            v(value)
        return True


class IntField(Field):
    def __init__(self, **kwargs): super().__init__(db_type='INTEGER', **kwargs)

class RealField(Field):
    def __init__(self, **kwargs): super().__init__(db_type='REAL', **kwargs)

class StrField(Field):
    def __init__(self, max_length: int = 255, **kwargs): super().__init__(db_type='TEXT', max_length=max_length, **kwargs)

class BoolField(Field):
    def __init__(self, **kwargs): super().__init__(db_type='INTEGER', **kwargs)

class JSONField(Field):
    def __init__(self, **kwargs): super().__init__(db_type='TEXT', **kwargs)


class ModelMeta(type):
    """ORM 元类"""
    def __new__(mcs, name, bases, namespace):
        if name == 'Model':
            return super().__new__(mcs, name, bases, namespace)
        fields = {}
        for key, val in namespace.items():
            if isinstance(val, Field):
                fields[key] = val
        namespace['_fields'] = fields
        namespace['_table'] = namespace.get('_table', name.lower())
        namespace['_soft_delete'] = namespace.get('_soft_delete', False)
        cls = super().__new__(mcs, name, bases, namespace)
        return cls


class Model(metaclass=ModelMeta):
    """ORM 基类"""
    _db: Database = None
    _table: str = None
    _fields: Dict[str, Field] = {}
    _soft_delete: bool = False
    id = IntField(primary_key=True)

    def __init__(self, **kwargs):
        for name, field in self._fields.items():
            val = kwargs.get(name, field.default)
            field.validate(val)
            setattr(self, name, val)

    @classmethod
    def create_table(cls):
        cls._db.create_table(cls)

    @classmethod
    def drop_table(cls):
        cls._db.drop_table(cls)

    def save(self) -> 'Model':
        data = {name: getattr(self, name, None) for name in self._fields if name != 'id'}
        if getattr(self, 'id', None):
            qb = self._db.table(self._table).where('id', '=', self.id)
            sql, params = qb.build_update(data)
            self._db.execute(sql, params)
        else:
            rowid = self._db.insert(self._table, data)
            if rowid: self.id = rowid
        return self

    def delete(self, hard: bool = False):
        if self._soft_delete and not hard:
            self._db.execute(f'UPDATE {self._table} SET deleted_at = ? WHERE id = ?',
                             [time.strftime('%Y-%m-%d %H:%M:%S'), self.id])
        else:
            self._db.execute(f'DELETE FROM {self._table} WHERE id = ?', [self.id])

    @classmethod
    def find(cls, pk) -> Optional['Model']:
        rows = cls._db.select(cls._table, id=pk)
        return cls(**rows[0]) if rows else None

    @classmethod
    def all(cls, **filters) -> List['Model']:
        rows = cls._db.select(cls._table, **filters)
        return [cls(**r) for r in rows]

    @classmethod
    def where(cls, **kwargs) -> List['Model']:
        return cls.all(**kwargs)

    @classmethod
    def count(cls, **filters) -> int:
        rows = cls._db.select(cls._table, **filters)
        return len(rows)


def setup_demo():
    """快速演示：创建内存数据库并返回"""
    db = Database('sqlite', 'sqlite://:memory:')
    Database._instances['default'] = db
    return db
