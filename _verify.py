import os, sys, io, re, glob
os.chdir(r"e:\咕咕嘎嘎")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

fails = sorted(glob.glob("失败脚本/*.md"), key=lambda f: os.path.getmtime(f), reverse=True)
with open(fails[0], "r", encoding="utf-8") as f:
    content = f.read()

# Test FIXED regex
cn_section = re.search(r'##\s*中文提示词.*?(?=## 自检清单|---\s*\n##)', content, re.DOTALL)
if cn_section:
    cn_text = cn_section.group()
    print(f"FIXED regex matched! Length: {len(cn_text)}")
    print(f"Has role iron law: {'角色铁律' in cn_text}")
    print(f"First 120 chars: {cn_text[:120]}")
else:
    print("FIXED regex did NOT match")
