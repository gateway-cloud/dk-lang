"""
TaskFlow Server — Python 胶水层
HTTP 路由 + DK-Lang 业务逻辑调用
"""
import sys
import os
import json

# 添加项目路径 (server.py → taskflow/ → projects/ → dk-lang/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dklang import run_dk_string, run_dk
from dklang.httpd import HttpServer, Response, Request
from dklang.database import Database
from dklang.interpreter import Interpreter, ReturnSignal
from dklang.lexer import Lexer
from dklang.parser import Parser
from dklang.ast_nodes import CallNode, LiteralNode, StrType, IntType, RealType, BoolType

# ── 全局状态 ──────────────────────────────────────
DB_NAME = 'taskflow'
DB_PATH = os.path.join(os.path.dirname(__file__), 'taskflow.db')
INIT_DB_PATH = os.path.join(os.path.dirname(__file__), 'init_db.dk')
API_DK_PATH = os.path.join(os.path.dirname(__file__), 'api.dk')
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8080

# 连接数据库
db = Database.connect(DB_NAME, 'sqlite', f'sqlite://{DB_PATH}')

# 先通过 run_dk 初始化数据库（创建 .db 文件 + 表 + 种子数据）
print("[Server] 初始化数据库...")
run_dk(INIT_DB_PATH)

# 数据库已通过 init_db 连接；连接信息在扩展中持久化
# 后续 API 调用通过 run_dk 创建新解释器即可复用同一 DB
db = Database.connect(DB_NAME, 'sqlite', f'sqlite://{DB_PATH}')

# 创建持久化解释器用于 API 调用
interp = Interpreter()
# 在同一个解释器中加载 API 代码（函数定义）
with open(API_DK_PATH, 'r', encoding='utf-8') as f:
    api_source = f.read()
api_lexer = Lexer(api_source)
api_tokens = api_lexer.tokenize()
api_parser = Parser(api_tokens)
api_ast = api_parser.parse()
interp.execute(api_ast)

# 建立数据库连接（API 函数需要）
# _db_connect 在 extensions 中已注册为全局内置
interp.glob.get('_db_connect')('taskflow', 'sqlite', f'sqlite://{DB_PATH}')

print(f"[Server] DK-Lang API 模块已加载，{len(interp.funcs)} 个函数，DB 已就绪")

# ── 辅助函数：调用 DK-Lang 函数 ──────────────────
def dk_call(func_name, *args):
    """调用 DK-Lang 函数并返回结果"""
    call_args = []
    for a in args:
        if isinstance(a, str):
            call_args.append(LiteralNode(value=a, dk_type=StrType()))
        elif isinstance(a, int):
            call_args.append(LiteralNode(value=a, dk_type=IntType()))
        elif isinstance(a, float):
            call_args.append(LiteralNode(value=a, dk_type=RealType()))
        elif isinstance(a, bool):
            call_args.append(LiteralNode(value=a, dk_type=BoolType()))
        else:
            call_args.append(LiteralNode(value=str(a), dk_type=StrType()))

    call_node = CallNode(name=func_name, arguments=call_args)

    old_env = interp.env
    try:
        return interp.eval(call_node, interp.glob)
    except ReturnSignal as rs:
        return rs.value
    except Exception as e:
        print(f"[DK Error] {func_name}: {e}")
        return None
    finally:
        interp.env = old_env

# ── HTTP 服务器 ───────────────────────────────────
server = HttpServer(SERVER_HOST, SERVER_PORT)

# CORS 中间件
def cors_middleware(req, next_handler):
    if req.method == 'OPTIONS':
        return Response(200, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        })
    resp = next_handler(req)
    if resp.headers is None:
        resp.headers = {}
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

server.use(cors_middleware)

# 静态文件服务
static_dir = os.path.join(os.path.dirname(__file__), 'static')
server.static('/static', static_dir)

# ── API 路由 ──────────────────────────────────────

# 首页
@server.router.get('/')
def index(req):
    html_path = os.path.join(static_dir, 'index.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return Response(200, f.read(), {'Content-Type': 'text/html; charset=utf-8'})
    return Response(200, '<h1>TaskFlow API Server Running</h1>',
                    {'Content-Type': 'text/html; charset=utf-8'})

# 健康检查
@server.router.get('/api/health')
def health(req):
    return Response.ok({'status': 'ok', 'service': 'TaskFlow', 'version': '1.0.0'})

# 仪表盘统计
@server.router.get('/api/dashboard')
def dashboard(req):
    user_id = req.query.get('user_id', '1')
    stats = dk_call('get_dashboard_stats', user_id)
    return Response.ok(stats if stats else {})

# 获取任务列表
@server.router.get('/api/tasks')
def get_tasks(req):
    user_id = req.query.get('user_id', '1')
    status = req.query.get('status', '')
    category = req.query.get('category', '')
    search = req.query.get('search', '')

    tasks_json = dk_call('get_tasks', user_id, status, category, search)
    try:
        tasks = json.loads(tasks_json) if isinstance(tasks_json, str) else tasks_json
    except:
        tasks = []
    return Response.ok(tasks if tasks else [])

# 获取单个任务
@server.router.get('/api/tasks/:task_id')
def get_task(req):
    task_id = req.params['task_id']
    task_json = dk_call('get_task_by_id', task_id)
    try:
        task = json.loads(task_json) if isinstance(task_json, str) else task_json
    except:
        task = None
    if task:
        return Response.ok(task)
    return Response.not_found('任务不存在')

# 创建任务
@server.router.post('/api/tasks')
def create_task(req):
    data = req.json()
    task_id = dk_call('create_task', json.dumps(data, ensure_ascii=False))
    return Response.created({'id': task_id, 'message': 'created'})

# 更新任务
@server.router.put('/api/tasks/:task_id')
def update_task(req):
    task_id = req.params['task_id']
    data = req.json()
    result = dk_call('update_task', task_id, json.dumps(data, ensure_ascii=False))
    return Response.ok({'status': 'updated'})

# 删除任务
@server.router.delete('/api/tasks/:task_id')
def delete_task(req):
    task_id = req.params['task_id']
    dk_call('delete_task', task_id)
    return Response.ok({'status': 'deleted'})

# 获取用户列表
@server.router.get('/api/users')
def get_users(req):
    users_json = dk_call('get_users')
    try:
        users = json.loads(users_json) if isinstance(users_json, str) else users_json
    except:
        users = []
    return Response.ok(users if users else [])

# 获取标签
@server.router.get('/api/tags')
def get_tags(req):
    user_id = req.query.get('user_id', '1')
    tags_json = dk_call('get_tags', user_id)
    try:
        tags = json.loads(tags_json) if isinstance(tags_json, str) else tags_json
    except:
        tags = []
    return Response.ok(tags if tags else [])

# 获取项目
@server.router.get('/api/projects')
def get_projects(req):
    user_id = req.query.get('user_id', '1')
    proj_json = dk_call('get_projects', user_id)
    try:
        proj = json.loads(proj_json) if isinstance(proj_json, str) else proj_json
    except:
        proj = []
    return Response.ok(proj if proj else [])

# ── 启动 ──────────────────────────────────────────
if __name__ == '__main__':
    # 数据库已通过持久解释器加载

    # 生成前端文件
    gen_fe_path = os.path.join(os.path.dirname(__file__), 'generate_frontend.dk')
    if os.path.exists(gen_fe_path):
        print("[Server] 生成前端文件...")
        run_dk(gen_fe_path)

    print(f"\n{'='*60}")
    print(f"  TaskFlow Server 启动")
    print(f"  地址: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"  API:  http://{SERVER_HOST}:{SERVER_PORT}/api/health")
    print(f"{'='*60}\n")
    server.start(blocking=True)
