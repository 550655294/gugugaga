#!/usr/bin/env python3
"""
🐧 咕咕嘎嘎 剧本自动生成器 v1.6
DeepSeek AI 驱动 · 纯引擎模式 · 剧情规则全部走规范文档
访问 http://localhost:8765 查看控制面板
"""

import json, os, re, sys, time, threading, glob, subprocess, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

# ═══ 配置 ═══
WORK_DIR = Path(__file__).parent.resolve()
DURATION_MIN = 30
PORT = 8765
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

def _load_env():
    """从 .env 文件加载环境变量（零依赖，纯标准库）"""
    env_path = WORK_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                if val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                if key not in os.environ:  # 不覆盖已有环境变量
                    os.environ[key] = val

_load_env()
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DURATION_MIN_LOCK = threading.Lock()

HTML_PATH = WORK_DIR / "generate_scripts_ui.html"

# ═══ 全局状态 ═══
_lock = threading.Lock()
_st = {"running":False,"total":0,"current":"等待启动...","step":"点击按钮开始","logs":[],
       "remaining":DURATION_MIN*60,"completed":False,"errors":0,"start_time":None,
       "streaming":False,"stream_content":"","stream_ep":0,
       "validation_errors":[], "failed_count":0}
_gen_thread = None

def _add_log(msg):
    with _lock:
        ts = datetime.now().strftime("%H:%M:%S")
        _st["logs"].append(f"[{ts}] {msg}")
        if len(_st["logs"]) > 200: _st["logs"] = _st["logs"][-200:]

def get_status():
    with _lock:
        d = dict(_st)
    with DURATION_MIN_LOCK:
        d["duration_min"] = DURATION_MIN
    # 附加文件列表（不用锁读文件系统）
    try:
        eps = []
        for f in sorted(WORK_DIR.glob("脚本*_分镜脚本.md"), reverse=True):
            eps.append({"name": f.name, "size": f.stat().st_size})
        d["files"] = eps[:20]
    except Exception:
        d["files"] = []
    return d

# ═══ DeepSeek API ═══
def call_api(system_prompt, user_prompt, max_tokens=8192):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    body = {"model": MODEL, "messages": [{"role":"system","content":system_prompt},
            {"role":"user","content":user_prompt}], "max_tokens": max_tokens, "temperature": 0.8}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8','replace')
        raise RuntimeError(f"HTTP {e.code}: {err_body}")
    except Exception as e:
        raise RuntimeError(f"API错误: {e}")

def call_api_streaming(system_prompt, user_prompt, on_chunk, max_tokens=8192):
    """流式调用 DeepSeek API，每收到一个 token 就回调 on_chunk(text)"""
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    body = {"model": MODEL, "messages": [{"role":"system","content":system_prompt},
            {"role":"user","content":user_prompt}], "max_tokens": max_tokens,
            "temperature": 0.8, "stream": True}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            buffer = b""
            while True:
                chunk = resp.read(1024)
                if not chunk:
                    break
                buffer += chunk
                # 按行解析 SSE
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        return
                    try:
                        obj = json.loads(data_str)
                        delta = obj.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            on_chunk(content)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8','replace')
        raise RuntimeError(f"HTTP {e.code}: {err_body}")
    except Exception as e:
        raise RuntimeError(f"API错误: {e}")

# ═══ 上下文加载 ═══
def _read(fname): 
    fp = WORK_DIR / fname
    return fp.read_text(encoding="utf-8") if fp.exists() else ""

def get_episodes():
    eps = []
    for f in sorted(WORK_DIR.glob("脚本*_分镜脚本.md")):
        m = re.match(r'脚本(\d+)_分镜脚本\.md', f.name)
        if m: eps.append((int(m.group(1)), m.group(1)))
    return eps

def next_ep_num():
    eps = get_episodes()
    return max(n for n,_ in eps) + 1 if eps else 1

def used_themes():
    """从操作卡/提示词中提取实质主题关键词，避免 AI 重复"""
    themes = set()
    for f in sorted(WORK_DIR.glob("脚本*_分镜脚本.md")):
        try:
            c = f.read_text(encoding="utf-8")
            keyword = ""
            # 优先：开场首帧描述（包含地点+核心道具+场景）
            m = re.search(r'[🎬]\s*开场首帧[^\n]*\n[^\n]*[：:]\s*(.+?)(?:→|$)', c)
            if m:
                keyword = m.group(1).strip()
            # 备选：背景参考图行（包含场景地点）
            if not keyword:
                m = re.search(r'[🏙]\s*背景参考图[^\n]*[：:]\s*(.+?)(?:，|。|$)', c)
                if m:
                    keyword = m.group(1).strip()
            # 兜底：中文提示词第一句（0-3s段首行）
            if not keyword:
                m = re.search(r'（0-3s）：[^\n]{0,200}', c)
                if m:
                    text = m.group().replace('（0-3s）：日系萌圆暖柔handheld。', '').strip()
                    keyword = text[:60]
            if keyword:
                themes.add(keyword[:80])  # 截取前80字作为主题指纹
        except Exception:
            pass
    return themes

def analyze_usage_stats():
    """分析已生成脚本的模式/角色使用统计，智能均衡轮换"""
    mode_counts = {"A_大手": 0, "B_第二角色": 0, "C_独角戏": 0}
    char_counts = {"Doro": 0}
    char_episodes = {"Doro": []}
    
    for f in sorted(WORK_DIR.glob("脚本*_分镜脚本.md")):
        try:
            c = f.read_text(encoding="utf-8")
            ep_m = re.match(r'脚本(\d+)', f.name)
            ep_num = int(ep_m.group(1)) if ep_m else 0
            
            # 检测模式
            has_hand = bool(re.search(r'(人手|人的手|手指|hand|五指|大手)', c))
            has_doro = bool(re.search(r'(Doro|doro|粉狗|粉色短发|X形面纹)', c))
            
            if has_doro:
                mode_counts["B_第二角色"] += 1
                char_counts["Doro"] += 1
                char_episodes["Doro"].append(ep_num)
            elif has_hand:
                mode_counts["A_大手"] += 1
            else:
                mode_counts["C_独角戏"] += 1
        except Exception:
            pass
    
    total = max(sum(mode_counts.values()), 1)
    return mode_counts, char_counts, char_episodes, total

def validate_script(content, ep_num):
    """校验生成内容是否通过18项自检，返回 (passed, failures)"""
    failures = []
    checks = [
        # (编号, 描述, 正则/检查函数, 是正则则预期True)
        ("1", "文件第一行不能是『---』", lambda c: not c.lstrip().startswith("---")),
        ("2", "包含📋 第一场景生成操作卡", lambda c: "第一场景生成操作卡" in c or "第一场景 生成操作卡" in c),
        ("3", "包含📋 第二场景生成操作卡", lambda c: "第二场景生成操作卡" in c or "第二场景 生成操作卡" in c),
        ("4", "包含🎯 即梦生成参数", lambda c: "即梦生成参数" in c or "Seedance" in c),
        ("5", "包含中文提示词", lambda c: "中文提示词" in c),
        ("6", "包含英文提示词", lambda c: "英文提示词" in c),
        ("7", "包含⚠️ 角色铁律", lambda c: "角色铁律" in c),
        ("8", "包含自检清单", lambda c: "自检清单" in c and "✅" in c),
        ("9", "操作卡无甩锅措辞", lambda c: _no_buck_passing_in_ops(c)),
        ("10", "英文无『beak』", lambda c: _no_beak_in_en_section(c)),
        ("11", "角色铁律在提示词前", lambda c: _iron_law_before_prompts(c)),
        ("12", "中文段数≥5段", lambda c: len(re.findall(r'（\d+[–\-]\d+s）', c)) >= 5),
        ("13", "包含『自检清单（输出前逐项确认）』", lambda c: "自检清单" in c and "逐项确认" in c),
    ]
    
    for num, desc, check_fn in checks:
        if not check_fn(content):
            failures.append(f"#{num} {desc}")
    
    # 非致命警告：不一定失败但提示
    warnings = []
    if len(content) < 2000:
        warnings.append("⚠️ 内容过短（<2000字），可能不完整")
    if "gltf" not in content.lower() and "kawaii" not in content:
        warnings.append("⚠️ 英文段可能缺失或格式异常")
    
    passed = len(failures) == 0
    return passed, failures, warnings

def _no_beak_in_en_section(content):
    """检查英文提示词中企鹅是否错误出现了 beak"""
    en_section_match = re.search(r'英文提示词.*?$(.+?)(?:^---|\Z)', content, re.DOTALL | re.MULTILINE)
    if en_section_match:
        en_text = en_section_match.group(1)
        # 只在提到企鹅的上下文中检查 beak
        # 如果 beak 和 chick/bird 一起出现，是合法的
        lines = en_text.split('\n')
        for line in lines:
            line_lower = line.lower()
            if "beak" in line_lower:
                # 如果同一行有 chick 或 bird 字样，允许
                if "chick" in line_lower or "bird" in line_lower:
                    continue
                # 如果同一行有 penguin 字样，报错
                if "penguin" in line_lower:
                    return False
                # 默认：如果出现了 beak，且不在 chick 语境中，报错
                return False
    return True  # 没找到英文段，不算失败

def _iron_law_before_prompts(content):
    """检查角色铁律是否出现在中文提示词标题之后、分段开始之前"""
    # 角色铁律应该在中文提示词部分出现
    cn_section = re.search(r'中文提示词.*?(?=英文提示词)', content, re.DOTALL)
    if cn_section:
        cn_text = cn_section.group()
        return "角色铁律" in cn_text
    return True

def _no_buck_passing_in_ops(content):
    """检查操作卡区域（排除自检清单）是否无甩锅措辞"""
    # 切除自检清单及其后内容，只检查前面的操作卡
    checklist_idx = content.find("自检清单")
    if checklist_idx > 0:
        check_content = content[:checklist_idx]
    else:
        check_content = content
    # 排除「未出现"用户自行判断"」这类表述的假阳性
    # 真正需要拦截的是操作卡正文里真实的甩锅语句
    banned = ["用户自行判断", "根据实际情况", "待定"]
    for phrase in banned:
        idx = check_content.find(phrase)
        if idx >= 0:
            # 检查上下文：如果前后有「未出现」「不写」「没有」等否定词，跳过
            context_before = check_content[max(0, idx-15):idx]
            context_after = check_content[idx+len(phrase):idx+len(phrase)+15]
            negations = ["未出现", "不写", "没有", "不含", "不应", "禁止"]
            if any(n in context_before or n in context_after for n in negations):
                continue
            return False
    return True

def recent_scripts(n=2):
    eps = sorted(get_episodes(), key=lambda x: x[0], reverse=True)[:n]
    texts = []
    for num, _ in sorted(eps):
        fp = WORK_DIR / f"脚本{num:03d}_分镜脚本.md"
        if fp.exists():
            c = fp.read_text(encoding="utf-8")
            if len(c) > 15000: c = c[:4000] + "\n\n...(中间省略)...\n\n" + c[-4000:]
            texts.append(f"=== 参考脚本{num:03d} ===\n{c}")
    return "\n\n".join(texts)

# ═══ 生成逻辑 ═══
def build_system_prompt():
    shared = _read("共享参数模板.md")[:3000]
    spec = _read("Seedance2.0_提示词规范_校验版.txt")
    full_spec = _read("咕嘎生成规范文档.md")
    themes = "、".join(sorted(used_themes()))
    refs = recent_scripts(2)
    mode_counts, char_counts, char_episodes, total = analyze_usage_stats()
    
    # 规范文档存在且有内容时才插入，否则跳过
    spec_section = ""
    if full_spec and full_spec.strip():
        spec_section = f"\n## ⭐⭐⭐ 完整生成规范（最高优先级，逐项对照执行）⭐⭐⭐\n{full_spec}\n"
    
    # 智能模式推荐：计算各模式缺口，引导 AI 均衡
    a_ratio = mode_counts["A_大手"] / max(total, 1)
    b_ratio = mode_counts["B_第二角色"] / max(total, 1)
    c_ratio = mode_counts["C_独角戏"] / max(total, 1)
    
    # 选最缺的模式
    mode_suggestions = []
    if a_ratio < 0.4: mode_suggestions.append(f"「大手入镜」(已用{mode_counts['A_大手']}/{total}集，偏少→优先)")
    if b_ratio < 0.25: mode_suggestions.append(f"「第二角色」(已用{mode_counts['B_第二角色']}/{total}集，偏少→优先)")
    if c_ratio < 0.15: mode_suggestions.append(f"「独角戏」(已用{mode_counts['C_独角戏']}/{total}集，偏少→优先)")
    if not mode_suggestions: mode_suggestions.append("随机选择，保持多样性")
    
    return f"""你是专业 AI 短剧编剧，创作"咕咕嘎嘎"企鹅妹妹系列短视频剧本。{spec_section}
## 📊 智能均衡统计（Python 自动计算，供参考）

当前已生成 {total} 集，各模式使用统计：
- 🖐 大手入镜：{mode_counts['A_大手']} 集（{a_ratio:.0%}）
- 👫 第二角色：{mode_counts['B_第二角色']} 集（{b_ratio:.0%}）
- 🐧 独角戏：{mode_counts['C_独角戏']} 集（{c_ratio:.0%}）
- 角色 Doro 已出场 {char_counts.get('Doro', 0)} 次

👉 本集建议：{', '.join(mode_suggestions)}

## 补充材料（动态数据）

### 角色设定
{shared}

### 提示词规范（Seedance 2.0 官方）
{spec}

### 已用主题(请避开): {themes}

### 参考资料（已生成剧本的格式参考）
{refs}"""

def generate_one():
    global _st
    MAX_RETRIES = 3
    prev_failures = []  # 记住上次校验失败的原因，用于重试反馈
    
    for attempt in range(1, MAX_RETRIES + 1):
        # 检查是否被手动停止
        with _lock:
            if not _st["running"]:
                return False
        
        ep_num = next_ep_num()
        with _lock:
            _st["current"] = f"脚本{ep_num:03d}生成中..."
            _st["streaming"] = True
            _st["stream_content"] = ""
            _st["stream_ep"] = ep_num
            _st["validation_errors"] = []
        
        if attempt == 1:
            _add_log(f"📝 开始生成脚本{ep_num:03d}...")
        else:
            _add_log(f"🔄 重试第{attempt}次 生成脚本{ep_num:03d}...")
        
        full_content_chunks = []  # try 外部初始化，确保 except 可访问
        
        try:
            with _lock: _st["step"] = "调用 DeepSeek API（流式）..."
            _add_log("🤖 请求 DeepSeek API（实时流式输出）...")
            
            sys_prompt = build_system_prompt()
            
            # 构建用户指令：如果有之前失败的原因，明确告知 AI 修正
            retry_feedback = ""
            if prev_failures:
                retry_feedback = f"""
## ⚠️ 上次生成校验失败，本次必须修正以下问题：
{chr(10).join(f'- {f}' for f in prev_failures)}

请特别注意这些项的修正，确保全部通过校验。"""
            
            user_prompt = f"请生成脚本{ep_num:03d}的即梦提交内容。\n\n⚠️ 严格遵守系统提示中的「完整生成规范文档」全部规则，逐项对照执行，不得跳过。{retry_feedback}\n\n直接输出，不要省略。"
            
            def on_chunk(text):
                full_content_chunks.append(text)
                with _lock:
                    _st["stream_content"] = ''.join(full_content_chunks)
            
            call_api_streaming(sys_prompt, user_prompt, on_chunk, 8192)
            response = ''.join(full_content_chunks)
            
            with _lock: _st["streaming"] = False
            _add_log(f"✅ 流式响应完成（{len(response)}字）")
            
            # ═══ 校验 ═══
            passed, failures, warnings = validate_script(response, ep_num)
            
            if not passed:
                # 保存到失败脚本/
                fail_dir = WORK_DIR / "失败脚本"
                fail_dir.mkdir(exist_ok=True)
                ts = datetime.now().strftime("%m%d_%H%M")
                fail_name = f"脚本{ep_num:03d}_校验失败_{ts}_{len(failures)}项.md"
                fail_path = fail_dir / fail_name
                fail_path.write_text(response, encoding="utf-8")
                
                fail_detail = "、".join(failures[:5])
                with _lock:
                    _st["validation_errors"] = failures
                    _st["failed_count"] += 1
                _add_log(f"⚠️ 校验未通过（{len(failures)}项）: {fail_detail}")
                _add_log(f"📁 已保存到 失败脚本/{fail_name}")
                if warnings:
                    for w in warnings:
                        _add_log(w)
                
                # 🔥 记住失败原因，下次重试时反馈给 AI
                prev_failures = failures[:]
                
                if attempt < MAX_RETRIES:
                    _add_log(f"🔄 {5}秒后重试（{attempt}/{MAX_RETRIES}，将反馈失败原因给AI）...")
                    time.sleep(5)
                    continue
                else:
                    _add_log(f"❌ 已达最大重试次数，放弃脚本{ep_num:03d}")
                    with _lock: _st["errors"] += 1
                    return False
            
            # ═══ 通过校验，正常保存 ═══
            if warnings:
                for w in warnings:
                    _add_log(w)
            
            fname = f"脚本{ep_num:03d}_分镜脚本.md"
            (WORK_DIR / fname).write_text(response, encoding="utf-8")
            
            with _lock:
                _st["total"] += 1
                _st["step"] = f"已保存: {fname}"
                _st["current"] = f"脚本{ep_num:03d}"
                _st["validation_errors"] = []
            _add_log(f"💾 保存: {fname} ✅ 校验通过")
            return True
            
        except Exception as e:
            with _lock:
                _st["streaming"] = False
            
            # API调用异常：尝试保存不完整内容到失败脚本
            if full_content_chunks:
                partial = ''.join(full_content_chunks)
                if len(partial) > 200:
                    fail_dir = WORK_DIR / "失败脚本"
                    fail_dir.mkdir(exist_ok=True)
                    ts = datetime.now().strftime("%m%d_%H%M")
                    fail_name = f"脚本{ep_num:03d}_API中断_{ts}.md"
                    (fail_dir / fail_name).write_text(partial, encoding="utf-8")
                    _add_log(f"📁 API中断，已保存片段到 失败脚本/{fail_name}")
            
            _add_log(f"❌ 失败: {e}")
            with _lock: _st["step"] = f"错误: {str(e)[:80]}"
            
            if attempt < MAX_RETRIES:
                _add_log(f"🔄 {10}秒后重试（{attempt}/{MAX_RETRIES}）...")
                time.sleep(10)
                continue
            else:
                with _lock: _st["errors"] += 1
                return False
    
    return False

# ═══ 主循环 ═══
def gen_loop():
    global _st
    _add_log(f"🚀 启动！{DURATION_MIN}分钟持续生成...")
    _add_log(f"⏰ 预计结束: {(datetime.now()+timedelta(minutes=DURATION_MIN)).strftime('%H:%M:%S')}")
    start = time.time()
    
    try:
        while True:
            with _lock:
                if not _st["running"]:
                    break
            elapsed = time.time() - start
            remaining = DURATION_MIN * 60 - elapsed
            if remaining <= 0: break
            with _lock: _st["remaining"] = int(remaining)
            if remaining < 180:
                _add_log("⏰ 不足3分钟，停止生成")
                break
            
            success = generate_one()
            if not success:
                _add_log("⚠️ 失败，10秒后重试")
                time.sleep(10)
                continue
            
            elapsed = time.time() - start
            remaining = DURATION_MIN * 60 - elapsed
            with _lock: _st["remaining"] = int(remaining)
            if remaining <= 0: break
            time.sleep(5)
    except Exception as e:
        _add_log(f"💥 异常: {e}")
    finally:
        with _lock:
            _st["running"] = False
            _st["completed"] = True
            _st["remaining"] = 0
            _st["step"] = "完成!"
        _add_log("=" * 40)
        _add_log(f"🏁 完成！共生成了 {_st['total']} 集")
        if _st["errors"]: _add_log(f"⚠️ {_st['errors']} 次错误")
        _add_log("=" * 40)

def start_gen():
    global _st, _gen_thread
    with _lock:
        if _st["running"]: return
        _st.update(running=True,completed=False,total=0,errors=0,logs=[],
                   remaining=DURATION_MIN*60,step="启动中...",current="初始化...",
                   start_time=time.time(),streaming=False,stream_content="",stream_ep=0,
                   validation_errors=[], failed_count=0)
    _gen_thread = threading.Thread(target=gen_loop, daemon=True)
    _gen_thread.start()

def stop_gen():
    global _st
    with _lock:
        _st["running"] = False
        _st["step"] = "已手动停止"
    _add_log("⏹ 用户手动停止")

# ═══ HTTP 服务 ═══
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass  # 静默
    
    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
    
    def do_GET(self):
        if self.path == "/api/status":
            self._json(get_status())
        elif self.path.startswith("/api/file?name="):
            # 读取指定 md 文件内容
            from urllib.parse import unquote
            raw = self.path.split("?name=", 1)[1]
            fname = unquote(raw)
            fp = WORK_DIR / fname
            if fp.exists() and fp.suffix.lower() in (".md", ".txt"):
                try:
                    content = fp.read_text(encoding="utf-8")
                    self._json({"name": fname, "content": content, "size": len(content)})
                except Exception as e:
                    self._json({"error": f"读取失败: {e}"}, 500)
            else:
                self._json({"error": "文件不存在或类型不支持"}, 404)
        elif self.path in ("/", "/index.html"):
            if HTML_PATH.exists():
                html = HTML_PATH.read_text(encoding="utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            else:
                self._json({"error":"UI文件不存在"}, 500)
        else:
            self._json({"error":"not found"}, 404)
    
    def do_POST(self):
        if self.path == "/api/start":
            start_gen()
            self._json({"ok":True})
        elif self.path == "/api/stop":
            stop_gen()
            self._json({"ok":True})
        elif self.path == "/api/config":
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._json({"error": "empty body"}, 400)
                return
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode("utf-8"))
            except Exception:
                self._json({"error": "invalid json"}, 400)
                return
            if 'duration' in data:
                try:
                    new_dur = int(data['duration'])
                    if new_dur < 1 or new_dur > 120:
                        self._json({"error": "时长需在1-120分钟之间"}, 400)
                        return
                    global DURATION_MIN
                    with DURATION_MIN_LOCK:
                        DURATION_MIN = new_dur
                    with _lock:
                        _st["remaining"] = DURATION_MIN * 60
                    _add_log(f"⚙️ 运行时已更新为 {DURATION_MIN} 分钟")
                    self._json({"ok": True, "duration": DURATION_MIN})
                except (ValueError, TypeError):
                    self._json({"error": "时长必须是整数"}, 400)
            else:
                self._json({"error": "缺少 duration 参数"}, 400)
        else:
            self._json({"error":"not found"}, 404)

# ═══ 入口 ═══
def main():
    if not API_KEY:
        env_path = WORK_DIR / ".env"
        print("=" * 60)
        print("  [错误] 未找到 DeepSeek API Key")
        print("=" * 60)
        print()
        print("  ❓ 这是什么？")
        print("     DeepSeek 是大模型 API，脚本靠它自动写剧本。")
        print("     需要一个 API Key 来调用。")
        print()
        print("  📝 如何获取？（30秒搞定）")
        print("     1. 打开 https://platform.deepseek.com/api_keys")
        print("     2. 注册/登录 DeepSeek 开放平台")
        print("     3. 点击「创建 API Key」→ 复制密钥")
        print("        （格式：sk- 开头的一长串字符）")
        print(f"     4. 粘贴到 {env_path} 文件中：")
        print()
        print(f"           DEEPSEEK_API_KEY=sk-你的密钥")
        print()
        print("  💰 费用：很便宜，几块钱能生成几十集剧本")
        print("  💰 充值：https://platform.deepseek.com/top_up")
        print()
        print("  🔁 或者直接双击「启动剧本生成器.bat」")
        print("     首次运行会交互式引导你输入")
        print()
        print("  📖 详细说明见 README_脚本说明.md")
        print("=" * 60)
        sys.exit(1)
    
    if not HTML_PATH.exists():
        print(f"[ERR] UI文件不存在: {HTML_PATH}")
        print("请确保 generate_scripts_ui.html 在同一个目录")
        sys.exit(1)
    
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.allow_reuse_address = True  # 防止上次残留占用端口
    print(f"🐧 咕咕嘎嘎剧本生成器已启动")
    url = f"http://localhost:{PORT}"
    print(f"🌐 浏览器即将自动打开: {url}")
    print(f"⏱  运行时长: {DURATION_MIN} 分钟")
    print(f"按下 Ctrl+C 停止服务器")
    print("-" * 50)

    # 后台线程开浏览器（等服务器确认就绪后再弹），优先Chrome
    def _open_browser():
        time.sleep(0.5)
        # 方法1: 自动查找 Chrome 浏览器
        chrome_candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for chrome in chrome_candidates:
            if os.path.exists(chrome):
                try:
                    subprocess.Popen([chrome, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"   ✓ 已用 Chrome 打开浏览器")
                    return
                except Exception:
                    continue
        # 方法2: 系统默认浏览器（兜底）
        try:
            os.startfile(url)
            return
        except Exception:
            pass
        # 方法3: cmd /c start（最终兜底）
        try:
            subprocess.Popen(['cmd', '/c', 'start', url])
        except Exception:
            pass

    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        server.server_close()
    except Exception as e:
        print(f"\n❌ 服务器异常: {e}")
        server.server_close()
        input("按回车键退出...")

if __name__ == "__main__":
    main()
