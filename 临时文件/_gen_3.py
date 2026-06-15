#!/usr/bin/env python3
"""补生成3个"""
import sys, os, io, time, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generate_scripts as gs

gs._st["running"] = True
food_re = re.compile(r'(吃|喝|食|饭|菜|肉|鱼|虾|蛋|奶|糖|果|瓜|桃|莓|蕉|梨|橘|柚|柠|芒|樱|葡|荔|杏|枣|饼|包|糕|粉|米|汤|粥|酱|油|醋|盐|辣|酸|甜|苦|咸|鲜|味|香|布丁|巧克力|冰淇淋|酸奶|蜂蜜|棉花|果酱|西瓜|草莓|葡萄|荔枝|饼干|面包|蛋糕|糖果|奶酪|薯片|爆米花|汉堡|披萨)')

for i in range(3):
    try:
        gs._st["running"] = True
        ok = gs.generate_one()
        eps = gs.get_episodes()
        latest = eps[-1][1] if eps else "?"
        is_food = bool(food_re.search(latest))
        tag = "🍽️" if is_food else "✅"
        print(f"  {tag} {'成功' if ok else '失败'} - {latest}")
    except Exception as e:
        print(f"  🔥 异常: {e}")
    if i < 2: time.sleep(3)

gs._st["running"] = False
eps = gs.get_episodes()
fc = sum(1 for _, fname in eps if food_re.search(fname))
print(f"\n总计: {len(eps)} | 食物: {fc}/{len(eps)} ({fc/max(len(eps),1)*100:.0f}%)")
