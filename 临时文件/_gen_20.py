#!/usr/bin/env python3
"""批量生成20个分镜脚本，v4.19 含类别多样性监控"""
import sys, os, io, time, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generate_scripts as gs

TARGET = 20
gs._st["running"] = True
success = 0
fail = 0
food_re = re.compile(r'(吃|喝|食|饭|菜|肉|鱼|虾|蛋|奶|糖|果|瓜|桃|莓|蕉|梨|橘|柚|柠|芒|樱|葡|荔|杏|枣|饼|包|糕|粉|米|汤|粥|酱|油|醋|盐|辣|酸|甜|苦|咸|鲜|味|香|布丁|巧克力|冰淇淋|酸奶|蜂蜜|棉花|果酱|西瓜|草莓|葡萄|荔枝|饼干|面包|蛋糕|糖果|奶酪|薯片|爆米花|汉堡|披萨)')

print(f"🎬 批量生成 {TARGET} 个分镜脚本 (v4.19 类别封锁)")
print(f"   启动时已有: {len(gs.get_episodes())} 个")
print("=" * 55)

for i in range(TARGET):
    try:
        gs._st["running"] = True
        ok = gs.generate_one()
        if ok:
            success += 1
            # 检查最新脚本是否是食物类
            eps = gs.get_episodes()
            if eps:
                latest = eps[-1]
                fname = latest[1]
                is_food = bool(food_re.search(fname))
                tag = "🍽️食物" if is_food else "✅正常"
                print(f"  [{success}/{TARGET}] {tag} {fname}")
                if is_food and success > 3:
                    # 食物类超过3个时发出警告（引擎应该已封锁）
                    cats = gs.theme_categories()
                    fc = len(cats["food"])
                    if fc > 3:
                        print(f"  ⚠️ 食物类已达{fc}个，引擎已封锁（后续不应再出现食物主题）")
        else:
            fail += 1
            print(f"  [{success}/{TARGET}] ❌ 失败 (已重试3次)")
    except Exception as e:
        fail += 1
        print(f"  [{success}/{TARGET}] 🔥 异常: {e}")
        import traceback
        traceback.print_exc()
    
    if i < TARGET - 1:
        time.sleep(3)

gs._st["running"] = False

# 最终统计
print()
print("=" * 55)
print(f"🏁 完成！成功: {success}, 失败: {fail}")
eps = gs.get_episodes()
food_count = sum(1 for _, fname in eps if food_re.search(fname))
print(f"   总脚本: {len(eps)} | 食物类: {food_count} | 非食物: {len(eps) - food_count}")
food_pct = food_count / max(len(eps), 1) * 100
if food_pct > 25:
    print(f"   ⚠️ 警告：食物类占比 {food_pct:.0f}%，仍偏高")
else:
    print(f"   ✅ 食物类占比 {food_pct:.0f}%，在合理范围")
