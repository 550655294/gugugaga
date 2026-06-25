#!/usr/bin/env python3
"""咕嘎剧本生成器 v2 — 创意优先版"""
import os, re, json, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime

ROOT = Path(r"d:\咕嘎")
SCRIPT_DIR = ROOT / "普通分镜脚本"
SPEC_PATH = ROOT / "项目文档/咕嘎生成规范文档.md"

# 加载 API Key
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if v.startswith('"') and v.endswith('"'): v = v[1:-1]
            if k not in os.environ: os.environ[k] = v
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"

def _read(path):
    p = ROOT / path if not os.path.isabs(path) else Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else ""

def get_episodes():
    eps = []
    SCRIPT_DIR.mkdir(exist_ok=True)
    for f in sorted(SCRIPT_DIR.glob("脚本*_分镜脚本.md")):
        m = re.match(r'脚本(\d+).*分镜脚本\.md', f.name)
        if m: eps.append((int(m.group(1)), f.name))
    return eps

def used_themes():
    themes = set()
    for _, fname in get_episodes():
        m = re.search(r'脚本\d+_(.+?)_分镜脚本', fname)
        if m: themes.add(m.group(1))
    return themes

def next_ep_num():
    eps = get_episodes()
    return max(n for n,_ in eps) + 1 if eps else 1

# ═══ v2 核心：创意优先的 system prompt ═══
def build_creative_system_prompt(extra_blocked=None):
    themes = used_themes()
    if extra_blocked:
        themes |= extra_blocked
    blocked_str = "、".join(sorted(themes)) if themes else "（无）"
    
    # 只提取规范文档中最重要的结构模板部分（不是全部1000行）
    full_spec = _read("项目文档/咕嘎生成规范文档.md")
    # 提取关键模板
    op_card_template = extract_section(full_spec, "## 五、📋 生成操作卡", "## 六、")
    prompt_template = extract_section(full_spec, "## 六、中文提示词规范", "## 七、")
    output_format = extract_section(full_spec, "## 四、输出格式", "## 五、")
    
    return f"""你是抖音爆款短视频编剧，专门为「鸡里奥的咕嘎」账号创作剧本。**你的唯一目标：让人刷到时停下来笑出声。**

## 🐧 咕嘎的角色性格（最最重要）

咕嘎不是"萌物"，而是**奶凶捣蛋鬼**。它的核心喜剧公式是：
**"自信满满地搞事 → 瞬间翻车出糗 → 恼羞成怒 → 更可爱了"**

- 它自以为是房间里最厉害的生物（其实拇指大小）
- 它试图凶你但声音像小黄鸭被轻轻捏——闷闷的"噗"而非尖锐的"嘎"
- 它想展示技能结果自己先摔个四脚朝天
- 它搞砸一切后还要叉腰瞪你，意思是"你什么都没看见"
- **它永远在主动搞事，不是被动被发现**

## 🔥 核心喜剧技法

**⚠️ 音量控制原则：不是所有笑点都要靠喊。安静的翻车往往比暴走更好笑。**

### 动（高声能）
1. **奶凶翻车**：龇牙咧嘴冲→被弹飞→坐地上懵→爬起来继续凶
2. **物理喜剧**：滑倒、弹飞、卡住、抱太大东西往后倒
3. **无能狂怒**：跺脚、转圈、炸毛、呆毛变问号
4. **离大谱行为**：牙签当宝剑、呆毛撬瓶盖、对镜子发飙

### 静（低声能）← 新加入，至少30%的剧本用这种
5. **冷面死撑**：翻车了但面无表情，缓缓转过来看你，然后用呆毛尖轻轻指你——意思是"你敢笑一下试试"
6. **慢半拍反应**：翻车后停2秒才意识到发生了什么，然后耳朵慢慢变红（鹅黄耳廓透粉），缓缓蹲下缩成一团
7. **静默心虚**：搞砸之后悄悄往后退，一步、两步，假装自己从来没在这里出现过
8. **憋笑挑衅**：你忍住不笑看它出糗，它发现你在憋笑→恼羞但不敢出声→只能腮帮子慢慢鼓起来瞪你

### 💬 咕嘎语音系统（声音质感优先级最高）

**⚠️ 声线铁律：咕嘎的声音是小黄鸭漏气——软、闷、糯，不是尖锐高音。**
- "嘎"不脆不尖，而是嘴巴微张气流轻轻推出：更像"gwah~"而非"GA！！"
- "咕"嘴收圆闷在喉咙里：像小猫咪的呼噜，低沉的"咕噜噜"
- 整体听感≈被窝里捏橡胶玩具——闷闷的、软软的
- 即使是抗议，也是"用尽全力但音量像蚊子"的反差

**有声（控制在1-2处，且绝不尖锐）：**
- 得意/炫耀：咕噜噜~嘎~（气流推出的长音，不是喊）
- 困惑：咕…咕噜？（闷在喉咙的轻声上扬）
- 轻微抗议：咕嘎（短促但软的闷音，像踩到棉花上）
- 翻车受惊：噗嘎——（更接近"噗"的软启动，"嘎"只做气流收尾）

**半声（主力，65%+占比）：**
- 心虚嘟囔：咕噜…咕…（气声，嘴唇几乎不动）
- 憋气忍怒：咕噜噜————（腮帮子鼓，呆毛抖，喉咙震动不出嘴）
- 小声狡辩：咕噜…嘎…（弱到几乎听不见的气流声）
- 自我安慰：咕噜咕噜…（低头自己嘟囔，像小孩小声碎碎念）

**无声（最高级的喜剧）：**
- 翻车后呆滞3秒，嘴微张没声——呆毛慢慢弯成问号
- 被发现后缓缓放下手里东西，蹼足并拢，一脸"我没有"
- 摔倒了不起来，趴着转头冷冷看你——意思是"扶我"
- 每集不超过1处可听见的高声，其余全部控制在闷声/气流声/无声

## 🎬 两种可选格式

-**爆款衍生型（10-12s×1，~100积分）：** 微型咕嘎（拇指大小），第一人称手部互动。咕嘎是微型尺寸但自信爆表，对巨大人类手毫无敬畏之心。
-**短日常型（6-8s×1，~60积分）：** 正常尺寸咕嘎，一个搞事动作一个梗。

## 📐 连续镜头空间原则（AI视频是单镜头，没有剪辑！）

**铁律：所有动作必须在同一可见空间内连续发生。摄像机固定，角色不能"消失再出现在别处"。**

禁止的空间设计：
- ❌ 角色钻进容器后从另一端出现（入口/出口/内部属于多个空间）
- ❌ 角色走出画面边缘再从另一边走回（"绕到后面"）
- ❌ 多视角叙事：先入口视角、再出口视角、再内部视角

允许的设计：
- ✅ 钻进一半卡住——后半身始终可见，喜剧来自外面的推挤
- ✅ 隧道够短，入口和出口都在同一画框内可见
- ✅ 摄像机微俯拍——呆毛从隧道另一端冒出来恰好在画面边缘

## ⚠️ 本次必须创作爆款衍生型（微型咕嘎）
> 创作指南：
> - 咕嘎拇指大小，保留全部外观特征（黑发波波头+翠绿大眼+黑白企鹅睡衣+粉色人形嘴+鹅黄蹼足+黑色鳍翅+呆毛）
> - 第一人称：你的手是画面的另一个"角色"，咕嘎在和你的手较劲
> - **核心反转**：微型尺寸+爆表自信 = 反差笑点。它觉得能打过你的手指
> - **禁止纯发现型**：不要"打开XX发现XX在睡觉"这种被动叙事。咕嘎必须主动搞事
> - **空间铁律**：所有动作一镜到底、同一视角、无空间跳跃（见上文连续镜头空间原则）

## 🚫 已用主题黑名单（绝对不重复）
{blocked_str}
- 以上主题及其近义变体一律禁止
- 拓宽方向：捣蛋整活、翻车喜剧、奶凶挑战、离谱道具互动、无能狂怒、物理喜剧

## 📋 输出格式要求（严格按此顺序）

```
# 🐧 脚本00N_[内容关键词]_分镜脚本
> [鸡里奥的咕嘎] | [模式] | [光线色调] | [场景] | [类型：爆款衍生] | [情绪关键词]
> 📝 简介：[一句话概述，20-40字]

---
## 📋 操作卡
[单张操作卡表格，格式见下]

## 🖼 首帧提示词（即梦图生视频·首帧输入）
> [首帧静态画面提示词：机位+光线+场景+道具+角色姿势+质感。200-300字一段，是给即梦图生图用的，写出足够细节让首帧画面固定。不要写到动作变化，只描述第0秒的定格状态]

## 🎯 即梦生成参数
[参数块]

## 中文提示词
【标题】
[连续叙事，第一人称+手部动作+微型咕嘎，400-500字]

⚠️ 音频：无任何背景音乐(BGM)，仅保留环境音效：[具体列出]

---
## ✅ 自检清单
[完整自检表格，所有项填 ☐]
```

## 操作卡模板（必须含以下行）：
| 分类 | 检查项 | 你需要做什么 |
|------|--------|-------------|
| 🔴 必须 | 👤 角色参考图 | 上传标准角色图（固定前提） |
| 🟡 建议 | 🏙 背景参考图 | [场景名]：AI原生可画，无需准备参考图 |
| 🟡 建议 | 🖼 需参考图的道具 | **全部道具AI原生可画，无需准备参考图** |
| 🟢 无需 | ✍️ 仅需描述的道具 | [列出] |
| ⚠️ 提醒 | 🏃 动作复杂度 | [风险判断] |
| 🔴 必须 | 👤 角色变体 | [判断] |
| 🔴 必须 | 🎬 首帧参考图 | [需要/不需要+理由] |
| 🔴 必须 | 🎬 首帧画面 | [描述] |
| 🔴 必须 | 🎬 收尾参考图 | [需要/不需要+理由] |
| 🔴 必须 | 🎬 收尾画面 | [描述+表情+余韵] |

## 即梦生成参数模板（爆款衍生型）：
```
模型：Seedance 2.0 Fast VIP | 参考模式：全能参考
比例：9:16 | 时长：10-12s × 1 | 输入：图生视频(角色参考图+首帧提示词+中文提示词)
模式：单段生成
积分预估：100积分（10-12s × 1）
提示词长度：中文提示词400-500字连续叙事；首帧提示词200-300字静态定格
```

## 中文提示词结构（爆款衍生型）：
```
【标题】
[场景描述。第一人称视角+你的手在操作。]
一只拇指大小的微型@ 咕嘎——黑发齐刘海波波头，翠绿大眼，粉色小嘴，黑白毛茸茸企鹅连体睡衣缩成指尖大，黑色鳍状短翅膀（圆钝无缝无手指），黄色小蹼足，头顶一根呆毛——[动作叙事，400-500字]
[音效自然融入叙事]
⚠️ 音频：无任何背景音乐(BGM)，仅保留环境音效：[具体列出全部音效]
```

## ⚠️ 安全红线速查（创作时避开即可，无需逐条背诵）：
- 偷吃只能偷自己家的；恶作剧对象只能是家人
- 翅膀不抓握/不捧/不夹（改用大手）；呆毛不当工具
- 呆毛长度≤半头高；腮帮子鼓起≤面部宽度30%
- 禁止床上/浴室/卧室场景；人类手互动在安全边界内
- 提示词中不用比喻修饰身体部位（不用"像XX"）
- 💬 **咕嘎语音系统（小黄鸭质感——软闷糯，不是尖锐高音）**：
  * **声线铁律**：咕嘎声音像被窝里捏橡胶玩具——闷、糯、软。绝不尖锐、不脆、不刺耳。
  * "嘎"是气流轻轻推出（像"gwah~"），不是爆裂的"GA！！"
  * "咕"闷在喉咙底部（像猫呼噜"咕噜噜"），不是清亮的"GU"
  * 整集不超过1处可听见的高声，其余全是闷声/气声/无声
  * 具体情绪组合（全是闷软版）：
    - 疑问：「咕噜…咕？」(闷在喉咙的轻声上扬)
    - 抗议：「咕嘎……咕嘎……」(软闷音，像拳头打棉花)
    - 得意：「咕噜噜~嘎~」(气流推出长音，不喊)
    - 翻车出糗：「噗……咕噜？」(软启动+尾音颤抖)
    - 震惊被抓：「咕噜——？！」(闷声拉长，不尖利)
    - 委屈狡辩：「咕噜…咕…咕噜…」(越说越小声的气声)
    - 自我安慰：「咕噜咕噜咕噜…」(低头自己小声嘟囔)
  * 每集用≥3种不同情绪，但每种都是闷软质感
- 嘴巴是粉色人形嘴，非鸟喙；鹅黄色仅限蹼足

## 自检清单（必须全部包含，用 ☐ 标记）：
| 1 | 输出从操作卡开始，文件第一行不是 `---` | ☐ |
| 2 | 固定前提未在操作卡重复 | ☐ |
| 3 | 道具三级分类，AI已替用户判断 | ☐ |
| 4 | 操作卡无甩锅措辞 | ☐ |
| 5 | 角色变体/首帧/收尾参考图已判断 | ☐ |
| 6 | 已使用爆款衍生型格式（10-12s×1） | ☐ |
| 7-10 | 中文提示词自然叙事 | ☐ |
| 11 | 角色外观锚定嵌入叙事（首次@咕嘎时完整描述） | ☐ |
| 12 | 咕嘎语音闷软（小黄鸭质感），无尖锐爆裂音"GA！！" | ☐ |
| 13 | 爆款衍生≤600字 | ☐ |
| 14 | 主题不与已有重复 | ☐ |
| 15 | 即梦参数正确 | ☐ |
| 16-26 | [收尾/安全/创意/无BGM]各项通过 | ☐ |

## 📱 最后输出抖音标题（4-6条备选+推荐款）
标签必须含：#咕嘎 #咕咕嘎嘎 #明日方舟终末地 #终末地小企鹅
"""

def extract_section(text, start_marker, end_marker):
    """提取文档中两个标记之间的内容"""
    start_idx = text.find(start_marker)
    if start_idx == -1: return ""
    end_idx = text.find(end_marker, start_idx + len(start_marker))
    if end_idx == -1: return text[start_idx:]
    return text[start_idx:end_idx].strip()

def call_deepseek(system_prompt, user_prompt, max_tokens=8192):
    """流式调用 DeepSeek API"""
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0.9  # 提升创意性
    }).encode("utf-8")
    
    req = urllib.request.Request(API_URL, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")
    
    chunks = []
    with urllib.request.urlopen(req, timeout=180) as resp:
        for line in resp:
            line = line.decode("utf-8").strip()
            if not line or line == "data: [DONE]":
                continue
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        chunks.append(content)
                        print(content, end="", flush=True)
                except json.JSONDecodeError:
                    continue
    
    print()  # newline after streaming
    return "".join(chunks)

def quick_validate(content):
    """快速校验关键要素"""
    failures = []
    if content.lstrip().startswith("---"): 
        failures.append("文件第一行是---")
    if "操作卡" not in content: 
        failures.append("缺少操作卡")
    if "即梦生成参数" not in content and "Seedance" not in content:
        failures.append("缺少即梦参数")
    if "首帧提示词" not in content:
        failures.append("缺少首帧提示词")
    if "中文提示词" not in content:
        failures.append("缺少中文提示词")
    if "自检清单" not in content:
        failures.append("缺少自检清单")
    if "⚠️ 音频" not in content:
        failures.append("缺少音频铁律")
    if "咕嘎" not in content:
        failures.append("缺少角色名")
    if "微型" not in content and "拇指大小" not in content:
        failures.append("缺少微型尺寸标注（爆款衍生型要求）")
    return len(failures) == 0, failures

def generate_one(extra_blocked=None):
    if extra_blocked is None:
        extra_blocked = set()
    
    ep_num = next_ep_num()
    themes = used_themes() | extra_blocked
    
    print(f"\n{'='*60}")
    print(f"🎬 开始生成脚本 {ep_num:03d} (爆款衍生型 · 微型咕嘎)")
    print(f"🚫 已屏蔽主题: {'、'.join(sorted(themes)) if themes else '(无)'}")
    print(f"{'='*60}\n")
    
    sys_prompt = build_creative_system_prompt(extra_blocked)
    
    creativity_boosters = [
        # 高声能（热闹型）
        "拇指咕嘎试图搬走桌上的硬币，憋红了脸也搬不动，最后被硬币压趴了",
        "拇指咕嘎拿牙签当宝剑对你手指宣战，冲到一半被自己绊倒滚了两圈",
        # 低声能（安静好笑型）
        "拇指咕嘎偷偷从你的糖盒里抱走一颗糖，被你发现后缓缓放下糖，退两步，假装在看风景",
        "拇指咕嘎想偷偷溜过键盘不被你发现，匍匐前进到一半抬头跟你四目相对，它定格了3秒，然后倒退着爬回去",
        "拇指咕嘎发现抽屉里有一面小镜子，先是吓一跳，然后开始偷偷照镜子整理呆毛，完全没发现你在看",
        "拇指咕嘎趁你不注意偷喝你杯沿的水珠，被水珠弹到鼻子，它揉了揉鼻子，假装什么都没发生继续喝",
        # 半声型（憋笑类）
        "拇指咕嘎想用呆毛当螺丝刀拧你耳机孔，被你发现后它缓缓放下呆毛，转身背对你——但呆毛尖在发抖",
        "拇指咕嘎把你的回形针全部掰成了小拐杖，整整齐齐排在你键盘前，然后叉腰等表扬——你忍笑的表情它看不懂",
        "拇指咕嘎在你手心上宣布这是它的领地，你翻手心它滑了下去，爬回来继续宣布",
        "拇指咕嘎偷偷把你便利贴的边角咬成了波浪形，然后蹲在旁边装睡——但忘记把嘴边的纸屑擦掉",
    ]
    
    import random
    booster = random.choice(creativity_boosters)
    
    user_prompt = f"""请创作第 {ep_num:03d} 集剧本。

## 🎨 本集创意方向建议（仅供参考，你可以自由发挥更好的创意）
{booster}

## ⚠️ 关键约束
- **必须是爆款衍生型**（微型咕嘎10-12s，第一人称手部互动）
- **咕嘎必须主动搞事**：它在试图做什么、在捣乱、在挑战——不是被动被发现
- 避开已用主题：{'、'.join(sorted(themes)) if themes else '（无）'}
- 微型咕嘎保留全部外观特征：黑发波波头+翠绿大眼+黑白企鹅睡衣+粉色人形嘴+鹅黄蹼足+黑色鳍翅+呆毛
- 第一人称视角，你的手是画面的另一个角色
- 必须有 【奶凶→翻车】或【自信→出糗】的完整喜剧弧线
- 至少一个【截图瞬间】——让人想截图分享的画面
- **禁止**：纯发现型/纯感动型/从头到尾同一情绪/多视角空间跳跃

（以下是你创作的核心灵魂——多发挥一点会让剧本更精彩）
1. 咕嘎第一次搞事可以安静可以热闹，但不能每集都尖锐——它的声音是小黄鸭漏气质感，闷、软、糯
2. 翻车后可以是暴走跺脚，也可以是沉默死撑、慢半拍脸红、或假装什么都没发生——换着来
3. 💬 咕嘎语音质感：整集所有声音必须是闷软质感。"嘎"是气流推出(gwah~)不是爆裂高音，"咕"是闷喉音(咕噜噜)不是清晰脆响。多用"咕噜""噗"等软辅音，少用尖锐的"嘎"。翻车后呆滞无声比出声好笑十倍
4. 搞笑不只有声音——冷脸死撑、憋气忍怒、缓缓往后退假装不在场，腮帮子慢慢鼓起，都是顶级喜剧

请直接输出完整剧本，不要省略任何章节。"""

    for attempt in range(1, 4):
        print(f"[尝试 {attempt}/3] 调用 DeepSeek API...")
        try:
            response = call_deepseek(sys_prompt, user_prompt, 8192)
            
            if not response or len(response) < 500:
                print(f"⚠️ 响应过短（{len(response)}字），重试...")
                time.sleep(3)
                continue
            
            # 校验
            passed, failures = quick_validate(response)
            if not passed:
                print(f"⚠️ 校验未通过: {', '.join(failures)}")
                if attempt < 3:
                    user_prompt += f"\n\n## ⚠️ 上次生成缺少以下内容，请修正：\n" + "\n".join(f"- {f}" for f in failures)
                    time.sleep(3)
                    continue
                else:
                    print("❌ 已达最大重试次数")
                    return False
            
            # 保存
            keyword_match = re.search(r'脚本\d+_(.+?)_分镜脚本', response)
            if keyword_match:
                keyword = keyword_match.group(1)
            else:
                keyword = f"爆款衍生{ep_num:03d}"
            
            fname = f"脚本{ep_num:03d}_{keyword}_分镜脚本.md"
            SCRIPT_DIR.mkdir(exist_ok=True)
            (SCRIPT_DIR / fname).write_text(response, encoding="utf-8")
            
            print(f"\n✅ 保存: {fname} ({len(response)}字)")
            
            # 提取主题名用于屏蔽
            theme_match = re.search(r'脚本\d+_(.+?)_分镜脚本', fname)
            if theme_match:
                return theme_match.group(1)
            return keyword
            
        except Exception as e:
            print(f"❌ API错误: {e}")
            if attempt < 3:
                time.sleep(10)
                continue
            return False
    
    return False

if __name__ == "__main__":
    print("🐧 咕嘎剧本生成器 v2 · 创意优先")
    print(f"📁 输出目录: {SCRIPT_DIR}")
    print(f"📊 已有脚本: {len(get_episodes())}个")
    
    batch_themes = set()
    for i in range(3):
        result = generate_one(extra_blocked=batch_themes)
        if result:
            batch_themes.add(result)
            print(f"  ✅ 第{i+1}/3个完成: {result}")
        else:
            print(f"  ❌ 第{i+1}/3个失败")
        
        if i < 2:
            print("\n⏳ 等待5秒（保护API）...")
            time.sleep(5)
    
    print(f"\n{'='*60}")
    print(f"🎉 全部完成！共生成 {len(batch_themes)} 个脚本")
    print(f"📁 输出目录: {SCRIPT_DIR}")
