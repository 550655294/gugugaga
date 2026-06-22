import os, sys, io, time, json, urllib.request, urllib.error, re, threading
from pathlib import Path
from datetime import datetime, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

os.chdir(r'd:\咕嘎')
sys.path.insert(0, r'd:\咕嘎')

# Load env
env_path = Path(r'd:\咕嘎\.env')
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = val

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

ROOT_DIR = Path(r'd:\咕嘎')
SCRIPT_DIR = ROOT_DIR / "普通分镜脚本"
WORK_DIR = ROOT_DIR

def _read(fname):
    fp = WORK_DIR / fname
    return fp.read_text(encoding="utf-8") if fp.exists() else ""

def get_episodes():
    eps = []
    SCRIPT_DIR.mkdir(exist_ok=True)
    for f in sorted(SCRIPT_DIR.glob("脚本*_分镜脚本.md")):
        m = re.match(r'脚本(\d+)_.*分镜脚本\.md', f.name)
        if m: eps.append((int(m.group(1)), f.name))
    return eps

def next_ep_num():
    eps = get_episodes()
    return max(n for n,_ in eps) + 1 if eps else 1

# Direct generation without the server loop
def call_api(system_prompt, user_prompt, max_tokens=8192):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    body = {"model": MODEL, "messages": [{"role":"system","content":system_prompt},
            {"role":"user","content":user_prompt}], "max_tokens": max_tokens, "temperature": 0.8, "stream": True}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
    
    full_text = []
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            buffer = b""
            while True:
                chunk = resp.read(1024)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        return ''.join(full_text)
                    try:
                        obj = json.loads(data_str)
                        delta = obj.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_text.append(content)
                            print(content, end='', flush=True)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass
        return ''.join(full_text)
    except Exception as e:
        print(f"\n[API ERROR] {e}")
        return None

# Minimal validate - just basic checks
def quick_validate(content):
    failures = []
    if content.lstrip().startswith("---"): failures.append("#1 first line '---'")
    if "生成操作卡" not in content and "操作卡" not in content: failures.append("#2 missing 操作卡")
    if "即梦生成参数" not in content and "Seedance" not in content: failures.append("#4 missing 即梦参数")
    if "中文提示词" not in content: failures.append("#5 missing 中文提示词")
    # v4.31: 角色铁律已嵌入叙事，不再需要独立块
    if "自检清单" not in content: failures.append("#7 missing 自检清单")
    return len(failures) == 0, failures

def generate_one_direct(extra_blocked=None):
    """Directly generate one script without the full server"""
    if extra_blocked is None:
        extra_blocked = set()
    full_spec = _read("项目文档/咕嘎生成规范文档.md")
    
    themes = set()
    SCRIPT_DIR.mkdir(exist_ok=True)
    for f in sorted(SCRIPT_DIR.glob("脚本*_分镜脚本.md")):
        m = re.search(r'脚本\d+_?(.+?)(?:_分镜脚本)?$', f.stem)
        if m:
            kw = m.group(1).strip()
            if len(kw) >= 2 and not kw.isdigit():
                themes.add(kw[:30])
    
    themes |= extra_blocked  # also block themes from previous runs in this batch
    
    # Load ref scripts
    ref_text = ""
    eps = sorted(get_episodes(), key=lambda x: x[0], reverse=True)[:2]
    for num, fname in eps:
        c = (SCRIPT_DIR / fname).read_text(encoding="utf-8")
        if len(c) > 15000: c = c[:4000] + "\n...(skip)...\n" + c[-4000:]
        ref_text += f"\n=== Ref Script {num:03d} ===\n{c}\n"
    
    ep_num = next_ep_num()
    blocked = "、".join(sorted(themes)) if themes else "（无）"
    
    system_prompt = f"""你是专业 AI 短剧编剧，创作"咕咕嘎嘎"企鹅妹妹系列短视频剧本。

## 完整生成规范（最高优先级，逐项对照执行）
{full_spec}

## 已用主题黑名单：{blocked}

以上主题及其近义变体一律禁止。请自由原创全新主题，3-8字。

## 参考（已生成剧本格式）
{ref_text if ref_text else '暂无已生成剧本'}

输出完整剧本，不要省略任何部分。"""

    user_prompt = f"请生成脚本{ep_num:03d}。严格遵守规范文档全部规则。直接输出，不要省略。"
    
    print(f"\n=== Generating Script {ep_num:03d} ===\n")
    print(f"[SYS] {len(system_prompt)} chars")
    print(f"[USR] {user_prompt}")
    print(f"\n--- API Response ---\n")
    
    content = call_api(system_prompt, user_prompt)
    
    if not content:
        print("\n[FAIL] API returned nothing")
        return False
    
    print(f"\n\n--- Response: {len(content)} chars ---")
    
    passed, failures = quick_validate(content)
    if failures:
        print(f"\n[FAIL] Validation: {', '.join(failures)}")
        # Try to save anyway for debugging
        debug_path = SCRIPT_DIR / f"脚本{ep_num:03d}_DEBUG_FAILED.md"
        debug_path.write_text(content, encoding="utf-8")
        print(f"[DEBUG] Saved to {debug_path.name}")
        return False
    
    # Save
    title_match = re.search(r'#\s*🐧\s*脚本\d+_(.+?)_分镜脚本', content)
    if title_match:
        keyword = title_match.group(1)
        fname = f"脚本{ep_num:03d}_{keyword}_分镜脚本.md"
    else:
        h1 = re.search(r'#\s*(.+)', content)
        if h1:
            safe = re.sub(r'[\\/*?:"<>|🐧⚔️]', '', h1.group(1)).strip()[:30]
            fname = f"脚本{ep_num:03d}_{safe}_分镜脚本.md" if safe else f"脚本{ep_num:03d}_分镜脚本.md"
        else:
            fname = f"脚本{ep_num:03d}_分镜脚本.md"
    
    (SCRIPT_DIR / fname).write_text(content, encoding="utf-8")
    print(f"\n[OK] Saved: {fname}")
    return True

# Generate 3 scripts, tracking themes to avoid duplicates
batch_themes = set()
for i in range(3):
    ok = generate_one_direct(extra_blocked=batch_themes)
    if ok:
        # Extract theme from saved file name
        eps = get_episodes()
        if eps:
            last = sorted(eps, key=lambda x: x[0], reverse=True)[0]
            theme_match = re.search(r'脚本\d+_(.+?)_分镜脚本', last[1])
            if theme_match:
                batch_themes.add(theme_match.group(1))
    print(f"\n{'='*60}")
    print(f"Script #{i+1}/3: {'OK' if ok else 'FAIL'}")
    print(f"{'='*60}\n")
    if i < 2:
        time.sleep(3)

print("\n=== ALL DONE ===")
