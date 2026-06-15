import os, sys, io, re
os.chdir(r"e:\咕咕嘎嘎")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Read the latest failure
import glob
fails = sorted(glob.glob("失败脚本/*.md"), reverse=True)
# Get the actual latest by modification time
fails_by_time = sorted(fails, key=lambda f: os.path.getmtime(f), reverse=True)
latest = fails_by_time[0]
print(f"Latest failure: {latest}")
print(f"Modified: {os.path.getmtime(latest)}")

with open(latest, "r", encoding="utf-8") as f:
    content = f.read()

print(f"Content length: {len(content)} chars")

# Test _iron_law_before_prompts
cn_section = re.search(r'中文提示词.*?(?=## 自检清单|---\s*\n##)', content, re.DOTALL)
if cn_section:
    cn_text = cn_section.group()
    print(f"\nRegex matched! Length: {len(cn_text)}")
    print(f"Has '角色铁律': {'角色铁律' in cn_text}")
    print(f"First 100 chars of match: {cn_text[:100]}")
    print(f"Last 100 chars of match: {cn_text[-100:]}")
else:
    print("\nRegex did NOT match!")
    # Try simpler patterns
    m1 = re.search(r'中文提示词', content)
    print(f"中文提示词 found at: {m1.start() if m1 else 'NOT FOUND'}")
    m2 = re.search(r'## 自检清单', content)
    print(f"## 自检清单 found at: {m2.start() if m2 else 'NOT FOUND'}")

# Check _before_checklist
idx = content.find("自检清单")
print(f"\n自检清单 at index: {idx}")
before = content[:idx] if idx > 0 else content
print(f"Before checklist has '角色铁律': {'角色铁律' in before}")
