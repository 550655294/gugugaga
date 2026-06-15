#!/usr/bin/env python3
"""测试：生成1个战斗分镜脚本（带日志）"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_scripts as g

g._st_battle["running"] = True

success = g.generate_battle_one()

print(f"\nSuccess: {success}")
print(f"Total: {g._st_battle['total']}")
print(f"Errors: {g._st_battle['errors']}")
print(f"Step: {g._st_battle['step']}")
print(f"Validation errors: {g._st_battle['validation_errors']}")
print(f"\n--- LOGS ---")
for log in g._st_battle["logs"]:
    print(log)
