#!/usr/bin/env python3
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generate_scripts as gs

gs._st["running"] = True
print("开始生成...")
try:
    ok = gs.generate_one()
    print("✅ 生成成功" if ok else "❌ 生成失败")
except Exception as e:
    print(f"🔥 异常: {e}")
    import traceback
    traceback.print_exc()
finally:
    gs._st["running"] = False
