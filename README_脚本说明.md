# 🐧 咕咕嘎嘎剧本生成器 — 使用说明

> **一句话：双击「启动剧本生成器.bat」就行。**

---

## 📦 换新电脑只需 3 步

### 1. 装 Python
- 下载：https://python.org （选 3.9 以上版本）
- ⚠️ 安装时务必勾选 **"Add Python to PATH"**

### 2. 搞到 DeepSeek API Key
- 打开：https://platform.deepseek.com/api_keys
- 注册/登录 → 创建 API Key → 复制 `sk-` 开头的那串字符
- 💰 费用超便宜，充值地址：https://platform.deepseek.com/top_up

### 3. 双击运行
```
启动剧本生成器.bat
```
- 首次运行会让你粘贴 API Key，之后自动记住
- 浏览器会自动打开控制面板 `http://localhost:8765`

---

## 🔑 API Key 存在哪？

保存在项目根目录的 `.env` 文件里（不会上传到 git，已加入 .gitignore）。

格式：
```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

换电脑时删掉这个文件，双击 bat 会重新引导你输入。

---

## ❓ 常见问题

| 问题 | 解决 |
|------|------|
| 双击 bat 闪退 | 右键 bat → 编辑，看错误提示。大概率是没装 Python |
| 看到"未找到 Python" | 装 Python 时没勾"Add to PATH"，重装或手动加 PATH |
| API 调用失败 | 检查 API Key 是否过期、余额是否用完 |
| 端口 8765 被占用 | 关掉其他占用的程序，或改 generate_scripts.py 里的 PORT |

---

## 🛠 文件说明

| 文件 | 作用 |
|------|------|
| `启动剧本生成器.bat` | 一键启动，自动检测 Python + 配置 Key |
| `generate_scripts.py` | 核心脚本，DeepSeek API 驱动生成剧本 |
| `generate_scripts_ui.html` | Web 可视化控制面板 |
| `.env` | API Key 存储（不上传 git） |
| `.gitignore` | 防止敏感文件泄露 |
