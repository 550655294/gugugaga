import os, sys, glob
os.chdir(r"e:\咕咕嘎嘎")

# Check env
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "KEY" in line.upper():
                k, _, v = line.partition("=")
                print(f"Key config: {k.strip()}={v.strip()[:10]}...")
                break
print(f"Has env KEY: {bool(os.environ.get('DEEPSEEK_API_KEY'))}")

fails = sorted(glob.glob("失败脚本/*.md"), reverse=True)
print(f"Failure count: {len(fails)}")
if fails:
    with open(fails[0], "r", encoding="utf-8") as f:
        c = f.read()
    print(f"Latest failure file: {fails[0]}")
    print(f"Size: {len(c)} chars")
    # Write to temp file for full read
    with open("_debug_fail.txt", "w", encoding="utf-8") as f:
        f.write(c[:2000])
    print("First 500 chars:")
    print(c[:500])
