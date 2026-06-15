import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"e:\咕咕嘎嘎")

# 模拟已用主题列表（当前20个脚本）
test_themes = [
    "冬天静电", "偷吃布丁", "吹蒲公英", "贪吃棉花糖", "柠檬酸到皱眉",
    "追光点游戏", "踩泡泡纸", "玩纸团", "躲猫猫", "吹泡泡",
    "转圈圈晕倒", "踩到胶带黏脚", "打喷嚏", "玩毛线球",
    "哈气画圈圈", "玩纸飞机", "玩影子游戏", "玩气球", "钻购物袋", "追光点游戏"
]

# 测试 similarity detection
from collections import Counter
import re

verbs = Counter()
for t in set(test_themes):
    m = re.match(r'^(.{1,3})(.+)$', t)
    if m:
        verb, obj = m.group(1), m.group(2)
        if re.search(r'[吃喝玩追踩吹滚转投篮躲藏钻照拍踢扔打滑摔蹦跳扒蹭躺趴舔尝咬抓够顶]', verb):
            verbs[verb] += 1

saturated = {v: c for v, c in verbs.items() if c >= 2}
print("saturated verbs (>=2):", saturated)

# Simulate warnings
warnings = []
if saturated:
    items = [f"{v}X（{c}次）" for v, c in sorted(saturated.items(), key=lambda x: -x[1])]
    warnings.append(f"以下动词模式已高频：{', '.join(items)}。请勿再用这些动词搭配不同对象")

print("warnings:", warnings)

# Verify no hardcoded keywords needed
print("\n--- test theme_similarity_warnings() ---")
from generate_scripts import theme_similarity_warnings
sat, warns = theme_similarity_warnings(set(test_themes))
print("saturated:", sat)
print("warnings:", warns)
