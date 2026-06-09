#!/usr/bin/env python3
"""
🐧 咕咕嘎嘎 剧本自动生成器 v1.2
DeepSeek AI 驱动 · 30分钟持续产出 · Web可视化界面
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
       "remaining":DURATION_MIN*60,"completed":False,"errors":0,"start_time":None}
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
        for f in sorted(WORK_DIR.glob("第*集_*_分镜脚本.md"), reverse=True):
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

# ═══ 上下文加载 ═══
def _read(fname): 
    fp = WORK_DIR / fname
    return fp.read_text(encoding="utf-8") if fp.exists() else ""

def get_episodes():
    eps = []
    for f in sorted(WORK_DIR.glob("第*集_*_分镜脚本.md")):
        m = re.match(r'第(\d+)集_(.+)_分镜脚本\.md', f.name)
        if m: eps.append((int(m.group(1)), m.group(2)))
    return eps

def next_ep_num():
    eps = get_episodes()
    return max(n for n,_ in eps) + 1 if eps else 24

def used_themes():
    return {t for _,t in get_episodes()}

def recent_scripts(n=2):
    eps = sorted(get_episodes(), key=lambda x: x[0], reverse=True)[:n]
    texts = []
    for num, title in sorted(eps):
        fp = WORK_DIR / f"第{num}集_{title}_分镜脚本.md"
        if fp.exists():
            c = fp.read_text(encoding="utf-8")
            if len(c) > 15000: c = c[:4000] + "\n\n...(中间省略)...\n\n" + c[-4000:]
            texts.append(f"=== 参考第{num}集 ===\n{c}")
    return "\n\n".join(texts)

# ═══ 生成逻辑 ═══
def build_system_prompt():
    shared = _read("共享参数模板.md")[:3000]
    spec = _read("Seedance2.0_提示词规范_校验版.txt")
    themes = "、".join(sorted(used_themes()))
    refs = recent_scripts(2)
    
    return f"""你是专业 AI 短剧编剧，创作"咕咕嘎嘎"企鹅妹妹系列短视频剧本。

## 角色设定
{shared}

## 提示词规范
{spec}

## 已用主题(请避开): {themes}

## 参考剧本
{refs}

## 输出格式（严格遵循）
输出完整的 Markdown 分镜脚本，包含以下所有部分：

# 🐧 第 N 集：标题（24秒 · 双章节）
> 共享参数见 `共享参数模板.md`
**一句话：** 一句话故事梗概
| 段 | 秒 | 拟声词 | 语调情绪 | 音效 |
（8段表格）

# 🎯 第一章：章名（0-12s）
## 🎬 段 1（0-3s）：标题
（100-200字详细分镜描述 + 拟声词情绪说明）
...段2(3-6s)、段3(6-9s)、段4(9-12s)...

# 🎯 第二章：章名（12-24s）
## 🎬 段 5（12-15s）：标题
...段6(15-18s)、段7(18-21s)、段8(21-24s)...
**【收尾】** 收尾画面

## 📦 素材需求清单（⚠️ 必须输出，放在提示词之前）
	（根据本集具体内容填写，禁止写占位符）
| 场景 | 必需素材 | 说明 |
|------|---------|------|
| 第一场景（0-12s） | 角色参考图 | 企鹅妹妹标准角色设定图（全身+面部特写） |
| 第一场景（0-12s） | 场景背景参考图 | [填入具体场景，如：温馨客厅沙发区] |
| 第一场景（0-12s） | 额外道具参考 | [关键道具名称，无则写"无需"] |
| 第二场景（12-24s） | 角色参考图 | 与第一场景同一张 |
| 第二场景（12-24s） | 场景背景参考图 | [填入具体场景] |
| 第二场景（12-24s） | ⚠️ 是否需要第一场景尾帧 | 场景连续→"需要，作为首帧参考上传"；切换新场景→"不需要" |
| 第二场景（12-24s） | 额外道具参考 | [有则列出，无则写"无需"] |
| 全局 | 转场方式 | [直接切换/黑场过渡/特效转场/尾帧衔接] |

## 中文提示词（即梦 Seedance 2.0）
```
> ⚠️ 角色铁律：她是企鹅，不是人类。上肢=鹅黄鳍状短翅膀（企鹅鳍），无人类手指/手掌/指关节。所有"握、抓、伸、抱、捂"动作由鳍状翅膀完成，没有五指分开的动作。

（0-3s）：日系萌圆暖柔handheld。...150-250字...natural motion，画面流畅不抖动，面部清晰不变形，人体结构正常，cinematic 4K quality, 电影质感，无模糊无闪烁。
（3-6s）：日系萌圆暖柔handheld。...
（6-9s）：日系萌圆暖柔handheld。...
（9-12s）：日系萌圆暖柔handheld。...
---
（0-3s）：日系萌圆暖柔handheld。...（第二场景重新从0s计数）
（3-6s）：...
（6-9s）：...
（9-12s）：...
【收尾】日系萌圆暖柔handheld。...
```

## 英文提示词（即梦 Seedance 2.0）
```
段1（0-3s）：Japanese cute rounded warm soft handheld slight camera shake sway. kawaii penguin girl (human-like anime face, 1:2 neat bangs ahoge, pink &amp; white onesie, yellow flipper wings, webbed feet, penguin body)...80-150 words..., cinematic 4K quality.
段2（3-6s）：...
...
段8（21-24s）：...
[Closing] ...
```

> ⚠️ 英文提示词中禁止出现 "beak"（鸟喙）这个词——因为角色面部是人形日系动漫脸（大眼睛、小嘴、人类五官），不是动物脸。"webbed feet" 可以保留，因为角色确实是企鹅身体，有黄色蹼足。

## 规则
1. 新主题不能与已用主题重复。故事围绕日常生活展开，有笑点有反转
2. 角色一致性：妹妹是企鹅身体造型（鳍状短翅膀无手指），但面部是人形日系动漫脸（大眼睛、小嘴、人类五官），不是动物脸
3. 每段情绪递进，最后段有暖心反转/笑点
4. 中文提示词开头固定"日系萌圆暖柔handheld"
5. 英文提示词必须包含"kawaii penguin girl (human-like anime face, 1:2 neat bangs ahoge, pink &amp; white onesie, yellow flipper wings, webbed feet, penguin body)"，严格禁止使用 beak（鸟喙）这个词
6. 第二场景秒数从0重新计数，用---分隔两场景
7. 中文提示词开头必须有角色铁律⚠️
8. 直接输出完整Markdown，不要任何省略
9. 素材需求清单必须根据本集剧本的具体内容填写场景/道具/转场，不能写占位符。此清单在输出中必须出现，位置在第二章之后、中文提示词之前"""

def generate_one():
    global _st
    # 检查是否被手动停止
    with _lock:
        if not _st["running"]:
            return False
    ep_num = next_ep_num()
    with _lock: _st["current"] = f"第{ep_num}集生成中..."
    _add_log(f"📝 开始生成第{ep_num}集...")
    
    try:
        with _lock: _st["step"] = "调用 DeepSeek API..."
        _add_log("🤖 请求 DeepSeek API...")
        
        sys_prompt = build_system_prompt()
        user_prompt = f"请创作第{ep_num}集的完整分镜脚本（8段双章节24秒格式）。\n\n⚠️ 严格要求：\n1. 新主题（不能是已有主题）+ 有笑点有反转\n2. 完整中英文提示词（即梦 Seedance 2.0）\n3. 前15秒/后15秒合并提示词\n4. 📦 素材需求清单（位置在第二章之后、中文提示词之前，根据本集剧本填写具体场景/道具/转场，禁止占位符）\n5. 即梦生成参数\n\n直接输出完整 Markdown，不要任何省略。"
        
        response = call_api(sys_prompt, user_prompt, 8192)
        _add_log("✅ API响应完成")
        
        # 提取标题
        m = re.search(r'第\s*\d+\s*集[：:]\s*(.+?)[（\n]', response)
        title = m.group(1).strip() if m else f"待命名{ep_num}"
        title = re.sub(r'[\\/:*?"<>|]', '', title).strip().rstrip('.')
        
        # 保存
        fname = f"第{ep_num}集_{title}_分镜脚本.md"
        (WORK_DIR / fname).write_text(response, encoding="utf-8")
        
        with _lock:
            _st["total"] += 1
            _st["step"] = f"已保存: {fname}"
            _st["current"] = f"第{ep_num}集: {title}"
        _add_log(f"💾 保存: {fname}")
        _add_log(f"🎉 第{ep_num}集《{title}》完成!")
        return True
    except Exception as e:
        with _lock: _st["errors"] += 1
        _add_log(f"❌ 失败: {e}")
        with _lock: _st["step"] = f"错误: {str(e)[:80]}"
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
                   start_time=time.time())
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
    print(f"🌐 打开浏览器访问: {url}")
    try:
        subprocess.Popen(f'start "" "{url}"', shell=True)
    except Exception:
        pass
    print(f"⏱  运行时长: {DURATION_MIN} 分钟")
    print(f"按下 Ctrl+C 停止服务器")
    print("-" * 50)
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
