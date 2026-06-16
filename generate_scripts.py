#!/usr/bin/env python3
"""
🐧 咕咕嘎嘎 剧本自动生成器 v1.7
DeepSeek AI 驱动 · 纯引擎模式 · 剧情规则全部走规范文档
📋 支持模式：普通分镜 / 战斗分镜
访问 http://localhost:8765 查看控制面板
"""

import json, os, re, sys, time, threading, subprocess, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

# ═══ 配置 ═══
ROOT_DIR = Path(__file__).parent.resolve()
WORK_DIR = ROOT_DIR  # .env、项目文档等
SCRIPT_DIR = ROOT_DIR / "普通分镜脚本"  # 普通日常分镜脚本存放处
BATTLE_SCRIPT_DIR = ROOT_DIR / "战斗分镜脚本"  # 战斗分镜脚本存放处
X_STYLE_SCRIPT_DIR = ROOT_DIR / "X风格脚本"  # X/Twitter风格AI视频脚本
TOOL_DIR = ROOT_DIR / "工具脚本"
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

HTML_PATH = TOOL_DIR / "generate_scripts_ui.html"

# ═══ 全局状态 ═══
_lock = threading.Lock()
_st = {"running":False,"total":0,"current":"等待启动...","step":"点击按钮开始","logs":[],
       "remaining":DURATION_MIN*60,"completed":False,"errors":0,"start_time":None,
       "streaming":False,"stream_content":"","stream_ep":0,
       "validation_errors":[], "failed_count":0}
_gen_thread = None

# ═══ 战斗模式全局状态 ═══
_battle_lock = threading.Lock()
_st_battle = {"running":False,"total":0,"current":"等待启动...","step":"点击按钮开始","logs":[],
              "remaining":DURATION_MIN*60,"completed":False,"errors":0,"start_time":None,
              "streaming":False,"stream_content":"","stream_ep":0,
              "validation_errors":[], "failed_count":0}
_battle_gen_thread = None

# ═══ X风格模式全局状态 ═══
_xstyle_lock = threading.Lock()
_st_xstyle = {"running":False,"total":0,"current":"等待启动...","step":"点击按钮开始","logs":[],
              "remaining":DURATION_MIN*60,"completed":False,"errors":0,"start_time":None,
              "streaming":False,"stream_content":"","stream_ep":0,
              "validation_errors":[], "failed_count":0}
_xstyle_gen_thread = None

def _add_log_to(state_dict, state_lock, msg):
    with state_lock:
        ts = datetime.now().strftime("%H:%M:%S")
        state_dict["logs"].append(f"[{ts}] {msg}")
        if len(state_dict["logs"]) > 200:
            state_dict["logs"] = state_dict["logs"][-200:]

def _add_log(msg):
    _add_log_to(_st, _lock, msg)

def _get_status(state_dict, state_lock, script_dir, glob_pattern):
    with state_lock:
        d = dict(state_dict)
    with DURATION_MIN_LOCK:
        d["duration_min"] = DURATION_MIN
    script_dir.mkdir(exist_ok=True)
    try:
        eps = []
        for f in sorted(script_dir.glob(glob_pattern), reverse=True):
            eps.append({"name": f.name, "size": f.stat().st_size})
        d["files"] = eps[:20]
    except Exception:
        d["files"] = []
    return d

def get_status():
    return _get_status(_st, _lock, SCRIPT_DIR, "脚本*_分镜脚本.md")

def get_battle_status():
    return _get_status(_st_battle, _battle_lock, BATTLE_SCRIPT_DIR, "战斗*_分镜脚本.md")

def get_xstyle_status():
    return _get_status(_st_xstyle, _xstyle_lock, X_STYLE_SCRIPT_DIR, "X风格*_分镜脚本.md")

def _battle_add_log(msg):
    _add_log_to(_st_battle, _battle_lock, msg)

def _xstyle_add_log(msg):
    _add_log_to(_st_xstyle, _xstyle_lock, msg)

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
    SCRIPT_DIR.mkdir(exist_ok=True)
    for f in sorted(SCRIPT_DIR.glob("脚本*_分镜脚本.md")):
        m = re.match(r'脚本(\d+)_.*分镜脚本\.md', f.name)
        if m: eps.append((int(m.group(1)), f.name))
    return eps

def next_ep_num():
    eps = get_episodes()
    return max(n for n,_ in eps) + 1 if eps else 1

def _used_themes(script_dir, name_pattern, suffix_pattern, fallback_pattern=None):
    """统一提取主题关键词，AI 必须严格避开"""
    raw = set()
    noise = {"校验失败","分镜脚本","即梦生成","抖音","标题","简介","X风格"}
    script_dir.mkdir(exist_ok=True)
    for f in sorted(script_dir.glob("*.md")):
        name = f.stem
        m = re.search(name_pattern, name)
        if m:
            kw = m.group(1).strip().rstrip("_")
            skip = any(n in kw for n in noise)
            if not skip and len(kw) >= 2 and not kw.isdigit():
                kw = re.sub(r'_(?:长视频|抖音标题简介)$', '', kw)
                raw.add(kw)
    themes = set()
    for t in raw:
        base = re.sub(suffix_pattern, '', t)
        themes.add(base.strip().rstrip("_")[:30])
    if fallback_pattern:
        for f in sorted(script_dir.glob(fallback_pattern)):
            try:
                first = f.read_text(encoding="utf-8")[:200]
                tm = re.search(r'脚本\d+_(.+?)_分镜脚本', first)
                if tm:
                    kw = tm.group(1).strip()
                    if len(kw) >= 2:
                        themes.add(kw[:30])
            except:
                pass
    return themes

def used_themes():
    return _used_themes(SCRIPT_DIR, r'[第脚本]\d+[套话集]?_?(.+?)(?:_分镜脚本)?$',
                        r'(大作战|大战|大冒险|风波|失踪事件|争夺战|堡垒|太空船)$',
                        "脚本*_分镜脚本.md")

def theme_similarity_warnings(blocked_themes):
    """纯数据驱动：从已用主题中检测高频动宾模式，0硬编码
    
    返回 (oversaturated_verbs: {verb: count}, warnings: [str])
    例如 已用[偷吃布丁,偷吃饼干,偷喝牛奶] → oversaturated={'偷吃':2,'偷喝':1}
    """
    from collections import Counter
    
    # 动作动词字（中文常见动宾结构中的动词）
    _V = set('吃喝玩追踩吹滚转投篮躲藏钻照拍踢扔打滑摔蹦跳扒蹭躺趴舔尝咬抓够顶偷贪')
    
    verbs = Counter()
    for t in blocked_themes:
        if len(t) < 1:
            continue
        # 智能识别动词长度：检查前2字是否都是动作字 → 复合动词（如"偷吃""贪吃"）
        v2 = t[:2] if len(t) >= 2 else ""
        v1 = t[0]
        
        if v2 and all(c in _V for c in v2):
            verb = v2  # 2字复合动词
        elif v1 in _V:
            verb = v1  # 单字动词
        else:
            continue  # 非动宾结构（如"冬天静电"）
        
        verbs[verb] += 1
    
    saturated = {v: c for v, c in verbs.items() if c >= 2}
    warnings = []
    if saturated:
        items = [f"{v}X（{c}次）" for v, c in sorted(saturated.items(), key=lambda x: -x[1])]
        warnings.append(f"以下动词模式已高频：{', '.join(items)}。请勿再用这些动词搭配不同对象（如偷吃布丁→偷吃饼干），会被判为重复。")
    
    return saturated, warnings

def analyze_usage_stats():
    """分析已生成脚本的模式/角色使用统计，智能均衡轮换"""
    mode_counts = {"A_大手": 0, "B_第二角色": 0, "C_独角戏": 0}
    char_counts = {"Doro": 0, "菲比": 0}
    char_episodes = {"Doro": [], "菲比": []}
    
    for f in sorted(SCRIPT_DIR.glob("脚本*_分镜脚本.md")):
        try:
            c = f.read_text(encoding="utf-8")
            ep_m = re.match(r'脚本(\d+)', f.name)
            ep_num = int(ep_m.group(1)) if ep_m else 0
            
            # 检测模式
            has_hand = bool(re.search(r'(人手|人的手|手指|\bhand\b|五指|大手)', c))
            has_doro = bool(re.search(r'(Doro|doro|粉狗|粉色短发|X形面纹)', c))
            has_phoebe = bool(re.search(r'(菲比|Phoebe|phoebe|金发修女|隐海修会|蓝色大眼修女)', c))
            
            if has_doro:
                mode_counts["B_第二角色"] += 1
                char_counts["Doro"] += 1
                char_episodes["Doro"].append(ep_num)
            elif has_phoebe:
                mode_counts["B_第二角色"] += 1
                char_counts["菲比"] += 1
                char_episodes["菲比"].append(ep_num)
            elif has_hand:
                mode_counts["A_大手"] += 1
            else:
                mode_counts["C_独角戏"] += 1
        except Exception:
            pass
    
    total = max(sum(mode_counts.values()), 1)
    return mode_counts, char_counts, char_episodes, total

def analyze_format_stats():
    """分析已生成脚本的场景格式使用统计（v4.18 统一双段独立）"""
    double_count = 0  # 双段独立 12-15s×2
    last_formats = []  # 最近格式序列
    
    for f in sorted(SCRIPT_DIR.glob("脚本*_分镜脚本.md")):
        try:
            c = f.read_text(encoding="utf-8")
            has_double = "📋 场景一操作卡" in c
            if has_double:
                double_count += 1
                last_formats.append("双段独立")
        except Exception:
            pass
    
    total = max(double_count, 1)
    recent_2 = last_formats[-2:] if len(last_formats) >= 2 else last_formats
    recent_3 = last_formats[-3:] if len(last_formats) >= 3 else last_formats
    
    return double_count, total, recent_2, recent_3

def validate_script(content, ep_num):
    """校验生成内容是否通过自检清单，返回 (passed, failures)"""
    failures = []
    checks = [
        # (编号, 描述, 检查函数)
        ("1", "文件第一行不能是『---』", lambda c: not c.lstrip().startswith("---")),
        ("2", "包含📋 生成操作卡", lambda c: "生成操作卡" in _before_checklist(c) or "操作卡" in _before_checklist(c)),
        ("3", "(v4.18) 操作卡数量正确：双段独立必须有场景一+场景二操作卡（2张）", lambda c: _check_op_card_count(c)),
        ("4", "包含🎯 即梦生成参数", lambda c: "即梦生成参数" in c or "Seedance" in c),
        ("5", "包含中文提示词", lambda c: "中文提示词" in c),
        ("6", "包含⚠️ 角色铁律", lambda c: "角色铁律" in _before_checklist(c)),
        ("7", "包含自检清单", lambda c: "自检清单" in c and ("✅" in c or "☐" in c or "逐项确认" in c)),
        ("8", "操作卡无甩锅措辞", lambda c: _no_buck_passing_in_ops(c)),
        ("9", "角色铁律在提示词前", lambda c: _iron_law_before_prompts(c)),
        ("10", "(v4.18) 中文段数：双段独立=【场景一】【场景二】各一段连续叙事", lambda c: _check_segment_count(c)),
        ("11", "包含『自检清单（输出前逐项确认）』", lambda c: "自检清单" in c and "逐项确认" in c),
        ("12", "(v4.18) 场景标记正确：必须有【场景一】【场景二】", lambda c: _check_scene_markers(c)),
        ("13", "(v4.5) @引用融入正文：含『主体严格参考@图片1』", lambda c: "主体严格参考@图片1" in c),
        ("14", "(v4.5) 废除独立@行：不含『📎 @图1』残留", lambda c: "📎 @图1" not in c),
        ("15", "(v4.18) 格式一致性：【场景一】和【场景二】必须成对出现", lambda c: _v418_format_consistency(c)),
        ("17", "(v4.9) 身体部位安全：提示词中无翅膀抓握/捧/舀/呆毛勾取/拖拽等工具化描述", lambda c: _v49_body_safety(c)),
        ("18", "(v4.9) 比喻安全：提示词中无'像XX钩子/精密机械/气球/着火/星星眼✨/开出小花'等危险比喻", lambda c: _v49_metaphor_safety(c)),
        ("23", "(v4.18) 🔗 场景二操作卡含跨场景衔接判断（有衔接→给出方案 / 无衔接→标注「无衔接」）", lambda c: _check_cross_scene_continuity(c)),
    ]
    
    for num, desc, check_fn in checks:
        if not check_fn(content):
            failures.append(f"#{num} {desc}")
    
    # 非致命警告：不一定失败但提示
    warnings = []
    if len(content) < 2000:
        warnings.append("⚠️ 内容过短（<2000字），可能不完整")
    
    passed = len(failures) == 0
    return passed, failures, warnings

def _validate_battle_script(content, ep_num):
    """战斗模式校验：放宽身体部位安全检查（战斗必然涉及肢体动作）"""
    failures = []
    checks = [
        ("1", "文件第一行不能是『---』", lambda c: not c.lstrip().startswith("---")),
        ("2", "包含📋 生成操作卡", lambda c: "生成操作卡" in _before_checklist(c) or "操作卡" in _before_checklist(c)),
        ("3", "(v4.18) 操作卡数量正确：必须有场景一+场景二操作卡（2张）", lambda c: _check_op_card_count(c)),
        ("4", "包含🎯 即梦生成参数", lambda c: "即梦生成参数" in c or "Seedance" in c),
        ("5", "包含中文提示词", lambda c: "中文提示词" in c),
        ("6", "包含⚠️ 角色铁律", lambda c: "角色铁律" in _before_checklist(c)),
        ("7", "包含自检清单", lambda c: "自检清单" in c and ("✅" in c or "☐" in c or "逐项确认" in c)),
        ("8", "操作卡无甩锅措辞", lambda c: _no_buck_passing_in_ops(c)),
        ("9", "角色铁律在提示词前", lambda c: _iron_law_before_prompts(c)),
        ("10", "段数正确：必须有【场景一】【场景二】", lambda c: _check_segment_count(c)),
        ("11", "包含『自检清单（输出前逐项确认）』", lambda c: "自检清单" in c and "逐项确认" in c),
        ("12", "场景标记正确：必须有【场景一】【场景二】", lambda c: _check_scene_markers(c)),
        ("13", "@引用融入正文：含『主体严格参考@图片1』", lambda c: "主体严格参考@图片1" in c),
        ("14", "废除独立@行：不含『📎 @图1』残留", lambda c: "📎 @图1" not in c),
        ("15", "格式一致性：【场景一】和【场景二】必须成对出现", lambda c: _v418_format_consistency(c)),
        # 战斗模式放宽 #17 #18：只拦截最危险的身体部位描述
        ("17-judge", "战斗身体安全：无呆毛勾取/拖拽/缠绕/工具化、无嘴张成O形/伸长、无腮帮像气球", lambda c: _battle_body_safety(c)),
        ("23", "🔗 场景二操作卡含跨场景衔接判断", lambda c: _check_cross_scene_continuity(c)),
    ]
    
    for num, desc, check_fn in checks:
        if not check_fn(content):
            failures.append(f"#{num} {desc}")
    
    warnings = []
    if len(content) < 2000:
        warnings.append("⚠️ 内容过短（<2000字），可能不完整")
    
    passed = len(failures) == 0
    return passed, failures, warnings

def _battle_body_safety(content):
    """战斗模式身体安全：允许鳍翅拍打/呆毛戳/蹼足踢等合理战斗动作，只拦截过度工具化"""
    prompt_section = ""
    cn_match = re.search(r'##\s*中文提示词.*?(?=## 自检清单|---\s*\n##)', content, re.DOTALL)
    if cn_match:
        prompt_section = cn_match.group()
    else:
        prompt_section = _before_checklist(content)
    
    # 只拦截最危险的描述（工具化/变形）
    dangerous = [
        r'呆毛.{0,15}(勾取|拖拽|缠绕|开出小花|像.*钩子|像.*机械)',
        r'翅膀.{0,10}(抓握|五指|握拳|舀|手指)',
        r'嘴.{0,5}(张成.{0,3}O形|伸长|无底洞)',
        r'腮帮子.{0,5}(像气球|气球)',
        r'星星眼',
        r'舌头.{0,5}像.{0,5}着火',
        r'头发.{0,5}(炸成蒲公英|球形闪电|膨胀炸)',
        r'身体.{0,5}(像泄气皮球|皮球.{0,3}泄气)',
    ]
    for pattern in dangerous:
        if re.search(pattern, prompt_section):
            return False
    return True

def _iron_law_before_prompts(content):
    """检查角色铁律是否出现在中文提示词标题之后、分段开始之前"""
    cn_section = re.search(r'##\s*中文提示词.*?(?=## 自检清单|---\s*\n##)', content, re.DOTALL)
    if cn_section:
        cn_text = cn_section.group()
        return "角色铁律" in cn_text
    # 找不到中文提示词区域，回退到自检清单前的内容（避免自检清单#11「角色铁律在提示词顶部」触发假阳性）
    return "角色铁律" in _before_checklist(content)

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

def _before_checklist(content):
    """返回自检清单之前的内容，避免自检清单中的元描述（如『已输出场景一操作卡+场景二操作卡』或『中文只有【场景一】【场景二】』）污染格式检测"""
    idx = content.find("自检清单")
    if idx > 0:
        return content[:idx]
    return content

def _check_op_card_count(content):
    """检查操作卡数量正确：双段独立=场景一+场景二（2张）"""
    body = _before_checklist(content)
    has_card1 = "场景一操作卡" in body
    has_card2 = "场景二操作卡" in body
    return has_card1 and has_card2

def _check_scene_markers(content):
    """检查场景标记正确：必须有【场景一】【场景二】"""
    body = _before_checklist(content)
    has_scene1 = "【场景一" in body
    has_scene2 = "【场景二" in body
    return has_scene1 and has_scene2

def _check_segment_count(content):
    """检查段数：双段独立=【场景一】【场景二】各一段连续叙事"""
    body = _before_checklist(content)
    scene_markers = len(re.findall(r'【场景[一二]', body))
    return scene_markers >= 2

def _v418_format_consistency(content):
    """(v4.18) 双段独立格式必须【场景一】和【场景二】成对出现"""
    body = _before_checklist(content)
    has_scene1 = "【场景一" in body
    has_scene2 = "【场景二" in body
    return has_scene1 and has_scene2

def _v49_body_safety(content):
    """(v4.9) 检查提示词中是否包含身体部位工具化的危险描述"""
    # 只在提示词段落中检查（操作卡和自检清单区域可以包含元描述）
    # 提取中文提示词区域（锚定到 ## 标题，防止误匹配即梦参数中的"图生视频(角色参考图+中文提示词)"）
    prompt_section = ""
    cn_match = re.search(r'##\s*中文提示词.*?(?=## 自检清单|---\s*\n##)', content, re.DOTALL)
    if cn_match:
        prompt_section = cn_match.group()
    else:
        prompt_section = _before_checklist(content)  # 兜底：至少排除自检清单，避免「星星眼」等危险示例触发误判
    
    # 危险模式：(翅膀/鳍翅/呆毛/蹼足) + (工具化动作)
    dangerous = [
        r'翅[膀尖].{0,10}(抓|握|捧|舀|掀开|夹|扇风|拍)',
        r'鳍翅.{0,10}(抓|握|捧|舀|掀开|夹|扇风|拍)',
        r'呆毛.{0,15}(勾|拖|缠绕|触碰.{0,5}碗|触碰.{0,5}物体)',
        r'呆毛.{0,10}(像.{0,5}钩子|像.{0,5}机械|开出小花)',
        r'蹼足.{0,10}(抓|踢飞|踢开|勾)',
        r'嘴.{0,5}(张成.{0,3}O形|伸长|无底洞)',
        r'腮帮子.{0,5}(像气球|气球)',
        r'星星眼',
        r'眼睛.{0,5}瞪到.{0,5}前所未有',
        r'舌头.{0,5}像.{0,5}着火',
        r'头发.{0,5}(炸成蒲公英|球形闪电|膨胀炸)',
        r'身体.{0,5}(像泄气皮球|皮球.{0,3}泄气)',
    ]
    for pattern in dangerous:
        if re.search(pattern, prompt_section):
            return False
    return True

def _v49_metaphor_safety(content):
    """(v4.9) 检查提示词中是否包含危险比喻性描述"""
    prompt_section = ""
    cn_match = re.search(r'##\s*中文提示词.*?(?=## 自检清单|---\s*\n##)', content, re.DOTALL)
    if cn_match:
        prompt_section = cn_match.group()
    else:
        prompt_section = _before_checklist(content)  # 兜底：至少排除自检清单，避免「像钩子」「像气球」等危险示例触发误判
    
    # 这些比喻在操作卡/自检清单的说明中出现可以接受，但提示词正文中不能有
    # 检查"像XX"修饰身体部位的模式
    body_metaphor = [
        r'像.{0,4}(钩子|弹簧|天线|雷达)',
        r'像.{0,4}精密机械',
        r'(?:像|如).{0,2}(气球|皮球)',
        r'像.{0,4}着火',
    ]
    for pattern in body_metaphor:
        if re.search(pattern, prompt_section):
            return False
    return True

def _check_cross_scene_continuity(content):
    """(v4.18) 检查场景二操作卡是否包含跨场景衔接判断"""
    body = _before_checklist(content)
    return "跨场景衔接" in body

def recent_scripts(n=2):
    eps = sorted(get_episodes(), key=lambda x: x[0], reverse=True)[:n]
    texts = []
    for num, fname in eps:
        fp = SCRIPT_DIR / fname
        if fp.exists():
            c = fp.read_text(encoding="utf-8")
            if len(c) > 15000: c = c[:4000] + "\n\n...(中间省略)...\n\n" + c[-4000:]
            texts.append(f"=== 参考脚本{num:03d} ===\n{c}")
    return "\n\n".join(texts)

# ═══ 生成逻辑 ═══
def build_system_prompt():
    full_spec = _read("项目文档/咕嘎生成规范文档.md")
    themes = "、".join(sorted(used_themes()))
    refs = recent_scripts(2)
    mode_counts, char_counts, char_episodes, total = analyze_usage_stats()
    double_count, fmt_total, recent_fmts_2, recent_fmts_3 = analyze_format_stats()
    
    # 规范文档存在且有内容时才插入，否则跳过
    spec_section = ""
    if full_spec and full_spec.strip():
        spec_section = f"\n## ⭐⭐⭐ 完整生成规范（最高优先级，逐项对照执行）⭐⭐⭐\n{full_spec}\n"
    
    # 智能模式推荐：计算各模式缺口，引导 AI 均衡
    a_ratio = mode_counts["A_大手"] / max(total, 1)
    b_ratio = mode_counts["B_第二角色"] / max(total, 1)
    c_ratio = mode_counts["C_独角戏"] / max(total, 1)
    
    # 选最缺的模式（v4.18: B模式「第二角色」已停用，仅统计不推荐）
    mode_suggestions = []
    if a_ratio < 0.4: mode_suggestions.append(f"「大手入镜」(已用{mode_counts['A_大手']}/{total}集，偏少→优先)")
    if c_ratio < 0.15: mode_suggestions.append(f"「独角戏」(已用{mode_counts['C_独角戏']}/{total}集，偏少→优先)")
    if not mode_suggestions: mode_suggestions.append("随机选择A/C，保持多样性")
    
    # ═══ v4.21 纯数据驱动去重：AI 自主创意 ═══
    blocked = used_themes()
    _, sim_warnings = theme_similarity_warnings(blocked)
    
    category_block = ""
    if sim_warnings:
        for w in sim_warnings:
            category_block += f"## ⚠️ {w}\n"
    
    blocked_list = "、".join(sorted(blocked)) if blocked else "（无）"
    category_block += f"""## 🎯 主题自主创意指令（v4.21）
已用主题黑名单：{blocked_list}

**AI 自主创意规则：**
- 以上主题及其近义变体一律禁止（换宾语不算新主题，如「偷吃布丁→偷吃饼干」）
- 从企鹅妹妹的日常/探索/玩耍/意外/情绪中**自由原创**一个全新主题，不要从任何预设列表挑
- 主题名简洁3-8字，一眼看出核心剧情

"""
    
    return f"""你是专业 AI 短剧编剧，创作"咕咕嘎嘎"企鹅妹妹系列短视频剧本。

⭐⭐⭐ 以下规范文档是你必须逐项对照的唯一规则源。所有剧情规则、格式模板、
安全铁律、自检清单均在此文档中，不得自行添加或修改规则。⭐⭐⭐
{spec_section}

{category_block}
## 📊 智能均衡统计（Python 自动计算，供参考）

当前已生成 {total} 集，各模式使用统计：
- 🖐 大手入镜：{mode_counts['A_大手']} 集（{a_ratio:.0%}）
- 👫 第二角色：{mode_counts['B_第二角色']} 集（{b_ratio:.0%}）
- 🐧 独角戏：{mode_counts['C_独角戏']} 集（{c_ratio:.0%}）
- 🐶 Doro 已出场 {char_counts.get('Doro', 0)} 次 | ✨ 菲比已出场 {char_counts.get('菲比', 0)} 次（⚠️ B模式「第二角色」已按 v4.18规范停用，历史统计仅供参考）

👉 本集建议：{', '.join(mode_suggestions)}

## 补充材料（动态数据）

### 已用主题(请避开): {themes}

### 参考资料（已生成剧本的格式参考）
{refs if refs else '暂无已生成剧本，请按规范文档中的模板输出。'}"""

def _generate_one(pipe):
    """统一生成函数。pipe = {state, lock, log_fn, next_ep, build_prompt,
       validate, script_dir, ep_prefix, used_themes, title_icon, user_prompt_prefix}"""
    state = pipe["state"]
    lock = pipe["lock"]
    log_fn = pipe["log_fn"]
    next_ep = pipe["next_ep"]
    build_prompt = pipe["build_prompt"]
    validate = pipe["validate"]
    script_dir = pipe["script_dir"]
    ep_prefix = pipe["ep_prefix"]
    used_themes_fn = pipe["used_themes"]
    title_icon = pipe.get("title_icon", "🐧")
    user_prompt_prefix = pipe.get("user_prompt_prefix", "请生成脚本")

    MAX_RETRIES = 3
    prev_failures = []

    for attempt in range(1, MAX_RETRIES + 1):
        with lock:
            if not state["running"]:
                return False

        ep_num = next_ep()
        with lock:
            state["current"] = f"{ep_prefix}{ep_num:03d}生成中..."
            state["streaming"] = True
            state["stream_content"] = ""
            state["stream_ep"] = ep_num
            state["validation_errors"] = []

        if attempt == 1:
            log_fn(f"📝 开始生成{ep_prefix}{ep_num:03d}...")
        else:
            log_fn(f"🔄 重试第{attempt}次 生成{ep_prefix}{ep_num:03d}...")

        full_content_chunks = []

        try:
            with lock: state["step"] = "调用 DeepSeek API（流式）..."
            log_fn("🤖 请求 DeepSeek API（实时流式输出）...")

            sys_prompt = build_prompt()

            retry_feedback = ""
            if prev_failures:
                fix_instructions = []
                for f in prev_failures:
                    if "自检清单" in f:
                        fix_instructions.append(f'- {f} → **必须在中文提示词之后、全文末尾插入「## 自检清单（输出前逐项确认）」段落**，包含 | # | 检查项 | ✅ | 格式的表格，最后一列全填 ✅')
                    elif "角色铁律" in f:
                        fix_instructions.append(f'- {f} → **中文提示词中必须写「⚠️ 角色铁律」四个字，不是「⚠️ 铁律」**。在提示词标题下紧跟此行')
                    else:
                        fix_instructions.append(f'- {f} → 请修正')
                retry_feedback = f"""
## ⚠️ 上次生成校验失败，本次必须修正以下问题：
{chr(10).join(fix_instructions)}

这些是自动化校验规则，必须逐字满足。"""

            blocked = used_themes_fn()
            sim_saturated, sim_warnings = theme_similarity_warnings(blocked)
            blocked_str = "\n".join(f"  - ❌ {t}" for t in sorted(blocked)) if blocked else "  （暂无）"

            user_prompt = f"{user_prompt_prefix}{ep_num:03d}。\n\n"
            if sim_warnings:
                for w in sim_warnings:
                    user_prompt += f"## ⚠️ {w}\n\n"
            user_prompt += f"## 🚫 已用主题黑名单：\n{blocked_str}\n\n"
            user_prompt += f"⚠️ 严格遵守系统提示中的规范文档全部规则，逐项对照执行，不得跳过。{retry_feedback}\n\n直接输出，不要省略。"

            def on_chunk(text):
                full_content_chunks.append(text)
                with lock:
                    state["stream_content"] = ''.join(full_content_chunks)

            call_api_streaming(sys_prompt, user_prompt, on_chunk, 8192)
            response = ''.join(full_content_chunks)

            with lock: state["streaming"] = False
            log_fn(f"✅ 流式响应完成（{len(response)}字）")

            # ═══ 校验 ═══
            passed, failures, warnings = validate(response, ep_num)

            if not passed:
                fail_detail = "、".join(failures[:5])
                with lock:
                    state["validation_errors"] = failures
                    state["failed_count"] += 1
                log_fn(f"⚠️ 校验未通过（{len(failures)}项）: {fail_detail}，内容已丢弃")
                if warnings:
                    for w in warnings:
                        log_fn(w)
                prev_failures = failures[:]
                if attempt < MAX_RETRIES:
                    log_fn(f"🔄 5秒后重试（{attempt}/{MAX_RETRIES}，将反馈失败原因给AI）...")
                    time.sleep(5)
                    continue
                else:
                    log_fn(f"❌ 已达最大重试次数，放弃{ep_prefix}{ep_num:03d}")
                    with lock: state["errors"] += 1
                    return False

            if warnings:
                for w in warnings:
                    log_fn(w)

            # 从生成标题动态提取关键词
            safe_chars = r'[\\/*?:"<>|🐧⚔️]'
            title_regex = rf'#\s*{re.escape(title_icon)}\s*{re.escape(ep_prefix)}\d+_(.+?)_分镜脚本'
            title_match = re.search(title_regex, response)
            if title_match:
                keyword = title_match.group(1)
                fname = f"{ep_prefix}{ep_num:03d}_{keyword}_分镜脚本.md"
            else:
                h1_match = re.search(r'#\s*(.+)', response)
                if h1_match:
                    safe = re.sub(safe_chars, '', h1_match.group(1)).strip()[:30]
                    fname = f"{ep_prefix}{ep_num:03d}_{safe}_分镜脚本.md" if safe else f"{ep_prefix}{ep_num:03d}_分镜脚本.md"
                else:
                    fname = f"{ep_prefix}{ep_num:03d}_分镜脚本.md"

            script_dir.mkdir(exist_ok=True)
            (script_dir / fname).write_text(response, encoding="utf-8")

            with lock:
                state["total"] += 1
                state["step"] = f"已保存: {fname}"
                state["current"] = f"{ep_prefix}{ep_num:03d}"
                state["validation_errors"] = []
            log_fn(f"💾 保存: {fname} ✅ 校验通过")
            return True

        except Exception as e:
            with lock:
                state["streaming"] = False
            log_fn(f"❌ 失败: {e}")
            with lock: state["step"] = f"错误: {str(e)[:80]}"
            if attempt < MAX_RETRIES:
                log_fn(f"🔄 10秒后重试（{attempt}/{MAX_RETRIES}）...")
                time.sleep(10)
                continue
            else:
                with lock: state["errors"] += 1
                return False

    return False

def generate_one():
    return _generate_one({
        "state": _st, "lock": _lock, "log_fn": _add_log,
        "next_ep": next_ep_num, "build_prompt": build_system_prompt,
        "validate": validate_script, "script_dir": SCRIPT_DIR,
        "ep_prefix": "脚本", "used_themes": used_themes,
        "title_icon": "🐧", "user_prompt_prefix": "请生成脚本"
    })

# ═══ 战斗分镜脚本生成 ═══
def get_battle_episodes():
    eps = []
    BATTLE_SCRIPT_DIR.mkdir(exist_ok=True)
    for f in sorted(BATTLE_SCRIPT_DIR.glob("战斗*_分镜脚本.md")):
        m = re.match(r'战斗(\d+)_.*分镜脚本\.md', f.name)
        if m: eps.append((int(m.group(1)), f.name))
    return eps

def next_battle_ep_num():
    eps = get_battle_episodes()
    return max(n for n,_ in eps) + 1 if eps else 1

def battle_used_themes():
    return _used_themes(BATTLE_SCRIPT_DIR, r'战斗\d+_?(.+?)(?:_分镜脚本)?$',
                        r'(大作战|大战|对决|决斗|激战|死斗)$')

def build_battle_system_prompt():
    battle_spec = _read("项目文档/咕嘎战斗生成规范文档.md")
    blocked = battle_used_themes()
    _, sim_warnings = theme_similarity_warnings(blocked)
    
    # 战斗规范文档（唯一权威战斗规范源——v2.4不再加载普通规范避免AI迷惑）
    battle_section = ""
    if battle_spec and battle_spec.strip():
        battle_section = f"\n## ⭐⭐⭐ 战斗生成规范（最高优先级，逐项对照执行）⭐⭐⭐\n{battle_spec}\n"
    
    category_block = ""
    if sim_warnings:
        for w in sim_warnings:
            category_block += f"## ⚠️ {w}\n"
    
    blocked_list = "、".join(sorted(blocked)) if blocked else "（无）"
    category_block += f"""## 🎯 战斗主题创意指令（v1.0）
已用战斗主题黑名单：{blocked_list}

**战斗创意规则：**
- 以上主题一律禁止
- 创作企鹅妹妹的战斗/对决/切磋场景，萌系风格，有趣不严肃
- 主题名简洁3-8字，前缀为「战斗」而非「脚本」
"""
    
    return f"""你是专业 AI 短剧编剧，创作"咕咕嘎嘎"企鹅妹妹系列**战斗短视频**剧本。

{battle_section}
{category_block}

## 补充材料
### 已用战斗主题(请避开): {blocked_list}

**⚠️ 输出时不要省略任何部分，严格按照规范文档逐项输出。**"""

def generate_battle_one():
    return _generate_one({
        "state": _st_battle, "lock": _battle_lock, "log_fn": _battle_add_log,
        "next_ep": next_battle_ep_num, "build_prompt": build_battle_system_prompt,
        "validate": _validate_battle_script, "script_dir": BATTLE_SCRIPT_DIR,
        "ep_prefix": "战斗", "used_themes": battle_used_themes,
        "title_icon": "⚔️", "user_prompt_prefix": "请生成战斗分镜脚本 战斗"
    })

# ═══ X风格分镜脚本生成 ═══
def get_xstyle_episodes():
    eps = []
    X_STYLE_SCRIPT_DIR.mkdir(exist_ok=True)
    for f in sorted(X_STYLE_SCRIPT_DIR.glob("X风格*_分镜脚本.md")):
        m = re.match(r'X风格(\d+)_.*分镜脚本\.md', f.name)
        if m: eps.append((int(m.group(1)), f.name))
    return eps

def next_xstyle_ep_num():
    eps = get_xstyle_episodes()
    return max(n for n,_ in eps) + 1 if eps else 1

def xstyle_used_themes():
    return _used_themes(X_STYLE_SCRIPT_DIR, r'X风格\d+_?(.+?)(?:_分镜脚本)?$',
                        r'(大作战|大战|对决|决斗|激战)$')

def _validate_xstyle_script(content, ep_num):
    """X风格校验：允许氛围叙事，放宽部分格式约束"""
    failures = []
    checks = [
        ("1", "文件第一行不能是『---』", lambda c: not c.lstrip().startswith("---")),
        ("2", "包含📋 生成操作卡", lambda c: "生成操作卡" in _before_checklist(c) or "操作卡" in _before_checklist(c)),
        ("3", "包含🎯 即梦生成参数", lambda c: "即梦生成参数" in c or "Seedance" in c),
        ("4", "包含中文提示词", lambda c: "中文提示词" in c),
        ("5", "包含⚠️ 角色铁律", lambda c: "角色铁律" in _before_checklist(c)),
        ("6", "包含自检清单", lambda c: "自检清单" in c and ("✅" in c or "☐" in c or "逐项确认" in c)),
        ("7", "操作卡无甩锅措辞", lambda c: _no_buck_passing_in_ops(c)),
        ("8", "角色铁律在提示词前", lambda c: _iron_law_before_prompts(c)),
        ("9", "包含电影级场景描述", lambda c: "电影级场景描述" in c or "场景描述" in c),
        ("10", "包含5段关键帧结构", lambda c: "关键帧1" in c and "关键帧5" in c),
        ("11", "氛围描述占比充足（提示词长度>300字）", lambda c: _xstyle_atmosphere_check(c)),
        ("12", "@引用融入正文：含『主体严格参考@图片1』", lambda c: "主体严格参考@图片1" in c),
        ("13", "X风格身体安全", lambda c: _battle_body_safety(c)),
    ]
    for num, desc, check_fn in checks:
        if not check_fn(content):
            failures.append(f"#{num} {desc}")
    warnings = []
    if len(content) < 2000:
        warnings.append("⚠️ 内容过短（<2000字），可能不完整")
    passed = len(failures) == 0
    return passed, failures, warnings

def _xstyle_atmosphere_check(content):
    """检查中文提示词段落是否有足够的氛围描述"""
    cn_match = re.search(r'##\s*中文提示词.*?(?=## 自检清单|---\s*\n##)', content, re.DOTALL)
    if cn_match:
        cn_text = cn_match.group()
        return len(cn_text) > 300
    return False

def build_x_style_system_prompt():
    xstyle_spec = _read("项目文档/咕嘎X风格生成规范文档.md")
    blocked = xstyle_used_themes()
    
    xstyle_section = ""
    if xstyle_spec and xstyle_spec.strip():
        xstyle_section = f"\n## ⭐⭐⭐ X风格生成规范（最高优先级，逐项对照执行）⭐⭐⭐\n{xstyle_spec}\n"
    
    blocked_list = "、".join(sorted(blocked)) if blocked else "（无）"
    
    return f"""你是专业的 AI 视频导演兼视觉设计师，创作"咕咕嘎嘎"企鹅妹妹系列**X/Twitter风格电影级短视频**。

你的风格参考 X 平台（原Twitter）上顶级 AI 视频创作者的叙事流：
- 氛围驱动而非动作驱动
- 场景描述先行，角色融入环境
- 电影级运镜与光影
- 每一帧都像电影截图

{xstyle_section}

## 🎯 X风格主题创意指令
已用X风格主题黑名单：{blocked_list}

**创意规则：**
- 以上主题一律禁止
- 创作电影感意境片段：黄昏车站、霓虹雨夜、星海漂流、旧教室阳光、樱花坡道等
- 主题具有「电影感标题」气质，3-8字
- 区别于日常萌系（普通分镜）和动作设计（战斗分镜）

## 补充材料
### 已用X风格主题(请避开): {blocked_list}

**⚠️ 输出时不要省略任何部分，严格按照规范文档逐项输出。**
**⚠️ 氛围描述必须占提示词50%以上篇幅。**
**⚠️ 必须包含5段关键帧（开场大景→氛围铺垫→角色入画→情绪高点→意境收尾）。**"""

def generate_x_style_one():
    return _generate_one({
        "state": _st_xstyle, "lock": _xstyle_lock, "log_fn": _xstyle_add_log,
        "next_ep": next_xstyle_ep_num, "build_prompt": build_x_style_system_prompt,
        "validate": _validate_xstyle_script, "script_dir": X_STYLE_SCRIPT_DIR,
        "ep_prefix": "X风格", "used_themes": xstyle_used_themes,
        "title_icon": "🅧", "user_prompt_prefix": "请生成X风格电影级分镜脚本 X风格"
    })

def _gen_loop(state_dict, state_lock, log_fn, generate_fn, icon="🐧"):
    log_fn(f"{icon} 启动！{DURATION_MIN}分钟持续生成...")
    log_fn(f"⏰ 预计结束: {(datetime.now()+timedelta(minutes=DURATION_MIN)).strftime('%H:%M:%S')}")
    start = time.time()
    try:
        while True:
            with state_lock:
                if not state_dict["running"]: break
            elapsed = time.time() - start
            remaining = DURATION_MIN * 60 - elapsed
            if remaining <= 0: break
            with state_lock: state_dict["remaining"] = int(remaining)
            if remaining < 180:
                log_fn("⏰ 不足3分钟，停止生成")
                break
            success = generate_fn()
            if not success:
                log_fn("⚠️ 失败，10秒后重试")
                time.sleep(10)
                continue
            elapsed = time.time() - start
            remaining = DURATION_MIN * 60 - elapsed
            with state_lock: state_dict["remaining"] = int(remaining)
            if remaining <= 0: break
            time.sleep(5)
    except Exception as e:
        log_fn(f"💥 异常: {e}")
    finally:
        with state_lock:
            state_dict["running"] = False
            state_dict["completed"] = True
            state_dict["remaining"] = 0
            state_dict["step"] = "完成!"
        log_fn("=" * 40)
        log_fn(f"🏁 完成！共生成了 {state_dict['total']} 集")
        if state_dict["errors"]: log_fn(f"⚠️ {state_dict['errors']} 次错误")
        log_fn("=" * 40)

def battle_gen_loop():
    _gen_loop(_st_battle, _battle_lock, _battle_add_log, generate_battle_one, icon="⚔️")

def start_battle_gen():
    global _st_battle, _battle_gen_thread
    with _battle_lock:
        if _st_battle["running"]: return
        _st_battle.update(running=True,completed=False,total=0,errors=0,logs=[],
                          remaining=DURATION_MIN*60,step="启动中...",current="初始化...",
                          start_time=time.time(),streaming=False,stream_content="",stream_ep=0,
                          validation_errors=[], failed_count=0)
    _battle_gen_thread = threading.Thread(target=battle_gen_loop, daemon=True)
    _battle_gen_thread.start()

def stop_battle_gen():
    global _st_battle
    with _battle_lock:
        _st_battle["running"] = False
        _st_battle["step"] = "已手动停止"
    _battle_add_log("⏹ 用户手动停止")

# ═══ X风格 循环与启动/停止 ═══
def xstyle_gen_loop():
    _gen_loop(_st_xstyle, _xstyle_lock, _xstyle_add_log, generate_x_style_one, icon="🅧")

def start_xstyle_gen():
    global _st_xstyle, _xstyle_gen_thread
    with _xstyle_lock:
        if _st_xstyle["running"]: return
        _st_xstyle.update(running=True,completed=False,total=0,errors=0,logs=[],
                          remaining=DURATION_MIN*60,step="启动中...",current="初始化...",
                          start_time=time.time(),streaming=False,stream_content="",stream_ep=0,
                          validation_errors=[], failed_count=0)
    _xstyle_gen_thread = threading.Thread(target=xstyle_gen_loop, daemon=True)
    _xstyle_gen_thread.start()

def stop_xstyle_gen():
    global _st_xstyle
    with _xstyle_lock:
        _st_xstyle["running"] = False
        _st_xstyle["step"] = "已手动停止"
    _xstyle_add_log("⏹ 用户手动停止")

# ═══ 主循环 ═══
def gen_loop():
    _gen_loop(_st, _lock, _add_log, generate_one)

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
    
    def _serve_md_file(self, script_dir):
        from urllib.parse import unquote
        raw = self.path.split("?name=", 1)[1]
        fname = unquote(raw)
        fp = (script_dir / fname).resolve()
        if not str(fp).startswith(str(WORK_DIR.resolve())):
            self._json({"error": "非法文件路径"}, 403)
            return
        if fp.exists() and fp.suffix.lower() in (".md", ".txt"):
            try:
                content = fp.read_text(encoding="utf-8")
                self._json({"name": fname, "content": content, "size": len(content)})
            except Exception as e:
                self._json({"error": f"读取失败: {e}"}, 500)
        else:
            self._json({"error": "文件不存在或类型不支持"}, 404)
    
    def do_GET(self):
        if self.path == "/api/status":
            self._json(get_status())
        elif self.path == "/api/battle/status":
            self._json(get_battle_status())
        elif self.path == "/api/xstyle/status":
            self._json(get_xstyle_status())
        elif self.path.startswith("/api/file?name="):
            self._serve_md_file(SCRIPT_DIR)
        elif self.path.startswith("/api/battle/file?name="):
            self._serve_md_file(BATTLE_SCRIPT_DIR)
        elif self.path.startswith("/api/xstyle/file?name="):
            self._serve_md_file(X_STYLE_SCRIPT_DIR)
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
        elif self.path == "/api/battle/start":
            start_battle_gen()
            self._json({"ok":True, "mode":"battle"})
        elif self.path == "/api/battle/stop":
            stop_battle_gen()
            self._json({"ok":True, "mode":"battle"})
        elif self.path == "/api/xstyle/start":
            start_xstyle_gen()
            self._json({"ok":True, "mode":"xstyle"})
        elif self.path == "/api/xstyle/stop":
            stop_xstyle_gen()
            self._json({"ok":True, "mode":"xstyle"})
        elif self.path == "/api/config":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
            except (ValueError, TypeError):
                self._json({"error": "invalid Content-Length"}, 400)
                return
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
        print("  🔁 或者直接双击「启动.bat」重试")
        print()
        print("  📖 详细说明见 项目文档/README_脚本说明.md")
        print("=" * 60)
        sys.exit(1)
    
    if not HTML_PATH.exists():
        print(f"[ERR] UI文件不存在: {HTML_PATH}")
        print("请确保 generate_scripts_ui.html 在同一个目录")
        sys.exit(1)
    
    HTTPServer.allow_reuse_address = True  # 必须在实例化前设置，防止端口残留占用
    server = HTTPServer(("0.0.0.0", PORT), Handler)
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
