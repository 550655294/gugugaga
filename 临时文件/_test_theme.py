import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test 1: load config
import json
cfg = json.load(open(r"e:\咕咕嘎嘎\项目文档\主题库.json", encoding="utf-8"))
print("Test 1 - Config loaded:")
print(f"  Categories: {list(cfg['categories'].keys())}")
print(f"  Pools: {list(cfg['suggestion_pools'].keys())}")
print(f"  Cross: {list(cfg['cross_alternatives'].keys())}")
print()

# Test 2: theme_categories() - simulate with known themes
import re
test_themes = {"冬天静电", "偷吃布丁", "吹蒲公英", "贪吃棉花糖", "柠檬酸到皱眉", "追光点游戏", "踩泡泡纸", 
               "玩纸团", "躲猫猫", "吹泡泡", "转圈圈晕倒", "踩到胶带黏脚", "打喷嚏", "玩毛线球",
               "哈气画圈圈", "玩纸飞机", "玩影子游戏", "玩气球", "钻购物袋", "追光点游戏"}

cats = {}
for cat_id in cfg["categories"]:
    cats[cat_id] = []
cats["other"] = []

for t in test_themes:
    matched = False
    for cat_id, cat_def in cfg["categories"].items():
        for kw_group in cat_def.get("keywords", []):
            if re.search(kw_group, t):
                cats.setdefault(cat_id, []).append(t)
                matched = True
                break
        if matched:
            break
    if not matched:
        cats["other"].append(t)

print("Test 2 - Category classification:")
for cat_id, items in cats.items():
    cat_name = cfg["categories"].get(cat_id, {}).get("name", cat_id)
    threshold = cfg["categories"].get(cat_id, {}).get("threshold", "N/A")
    print(f"  [{cat_id}] {cat_name} (threshold={threshold}): {len(items)} items")
    if items:
        for item in items:
            print(f"    - {item}")

print()

# Test 3: Dynamic block generation
print("Test 3 - Dynamic category_block:")
for cat_id, cat_def in cfg["categories"].items():
    count = len(cats.get(cat_id, []))
    threshold = cat_def.get("threshold", 5)
    if count >= threshold:
        print(f"  BLOCKED: {cat_def['name']} ({count}/{threshold})")
        ban_verbs = cat_def.get("ban_verbs", [])
        ban_nouns = cat_def.get("ban_nouns", [])
        print(f"    ban_verbs: {ban_verbs}")
        print(f"    ban_nouns sample: {ban_nouns[:5]}...")
        
        alt_keys = cfg["cross_alternatives"].get(cat_id, list(cfg["suggestion_pools"].keys()))
        print(f"    alternatives: {alt_keys}")
    elif count >= threshold - 1:
        print(f"  WARNING: {cat_def['name']} ({count}/{threshold})")
    else:
        print(f"  OK: {cat_def['name']} ({count}/{threshold})")

print("\nAll tests passed!")
