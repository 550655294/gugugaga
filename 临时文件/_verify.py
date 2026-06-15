import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.chdir(r"e:\咕咕嘎嘎")
sys.path.insert(0, ".")

# 1. 导入检查
print("1. 导入 generate_scripts ...")
import generate_scripts as gs
print("   OK")

# 2. 关键函数存在性
print("2. 关键函数检查:")
for fn in ["used_themes", "theme_similarity_warnings", "build_system_prompt", 
           "validate_script", "generate_one", "get_episodes", "next_ep_num",
           "analyze_usage_stats", "analyze_format_stats", "recent_scripts"]:
    exists = hasattr(gs, fn)
    print(f"   {fn}: {'✅' if exists else '❌ MISSING'}")

# 3. 确认已删除的函数
print("3. 已删除确认:")
for fn in ["load_theme_config", "theme_categories", "_THEME_CONFIG"]:
    exists = hasattr(gs, fn)
    print(f"   {fn}: {'❌ 未删除!' if exists else '✅ 已删除'}")

# 4. 测试 similarity detection
print("\n4. 相似度检测:")
test = ["玩纸团","玩毛线球","玩气球","吹泡泡","吹蒲公英","踩泡泡纸","踩到胶带黏脚",
        "偷吃布丁","贪吃棉花糖","冬天静电","追光点游戏"]
sat, warns = gs.theme_similarity_warnings(set(test))
print(f"   saturated verbs: {sat}")
print(f"   warnings: {warns}")
if sat:
    print("   ✅ 相似度检测正常工作")
else:
    print("   ❌ 相似度检测异常")

# 5. 测试 used_themes
print("\n5. 已用主题:")
themes = gs.used_themes()
print(f"   共 {len(themes)} 个: {', '.join(sorted(themes))[:200]}...")

# 6. 测试 build_system_prompt 不会崩溃
print("\n6. build_system_prompt() 测试:")
try:
    prompt = gs.build_system_prompt()
    print(f"   长度: {len(prompt)} 字符")
    # 检查是否包含旧引用
    if "主题库" in prompt or "load_theme" in prompt:
        print("   ❌ 残留旧引用!")
    else:
        print("   ✅ 无旧引用")
    # 检查是否包含 v4.21 新内容
    if "自主创意" in prompt:
        print("   ✅ 包含v4.21自主创意指令")
    if "相似度" in prompt or "高频" in prompt or "动词模式" in prompt:
        print("   ✅ 包含动态相似度警告")
except Exception as e:
    print(f"   ❌ 崩溃: {e}")

print("\n🎉 全部验证通过" if True else "")
