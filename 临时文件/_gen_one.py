#!/usr/bin/env python3
"""临时：手动调用 generate_one() 生成一个脚本"""
import sys, os, threading, io
from pathlib import Path
from datetime import datetime

# 修正 Windows 控制台编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 切换到项目根目录
os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 模拟 generate_scripts 需要的全局变量
import generate_scripts as g

g._lock = threading.Lock()
g._st = {"running": True, "total": 0, "current": "等待启动...", "step": "点击按钮开始", "logs": [],
         "remaining": 1800, "completed": False, "errors": 0, "start_time": None,
         "streaming": False, "stream_content": "", "stream_ep": 0,
         "validation_errors": [], "failed_count": 0}

orig_add_log = g._add_log
def _add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    g._st["logs"].append(f"[{ts}] {msg}")
    try:
        print(f"[{ts}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{ts}] {msg.encode('ascii','replace').decode('ascii')}", flush=True)
g._add_log = _add_log

success = g.generate_one()
if success:
    print("\n✅ 生成成功！")
else:
    print("\n❌ 生成失败")
