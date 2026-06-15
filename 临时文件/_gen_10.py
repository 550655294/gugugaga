#!/usr/bin/env python3
"""批量生成10个新脚本（不覆盖已有），编号从021开始"""
import sys, os, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_scripts as g

# 初始化全局状态（绕过 HTTP 服务）
g._st["running"] = True

total_success = 0
total_fail = 0

for i in range(10):
    ep = g.next_ep_num()
    print(f"\n{'='*50}")
    print(f"📝 [{i+1}/10] 开始生成脚本{ep:03d}...")
    print(f"{'='*50}")
    
    success = g.generate_one()
    if success:
        total_success += 1
        print(f"✅ 脚本{ep:03d} 生成成功 ({total_success}/10)")
    else:
        total_fail += 1
        print(f"❌ 脚本{ep:03d} 生成失败 ({total_fail}次失败)")
    
    if i < 9:
        print("⏳ 等待3秒后生成下一个...")
        time.sleep(3)

print(f"\n{'='*50}")
print(f"🏁 生成完毕！成功: {total_success}/10, 失败: {total_fail}/10")
print(f"{'='*50}")
