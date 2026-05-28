"""
TaskFlow v2.0 Launcher — 纯 DK-Lang Native Server
"""
import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dklang import run_dk
run_dk('server_v2.dk')
