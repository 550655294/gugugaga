"""临时脚本：生成一个新分镜脚本（非流式）"""
import sys, json, urllib.request, urllib.error, os, re
from pathlib import Path
sys.path.insert(0, '.')
from generate_scripts import _read, build_system_prompt, next_ep_num, validate_script, WORK_DIR

API_URL = "https://api.deepseek.com/v1/chat/completions"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL = "deepseek-chat"

ep_num = next_ep_num()
print(f'生成脚本{ep_num:03d}...', flush=True)

sys_prompt = build_system_prompt()
user_prompt = f'请生成脚本{ep_num:03d}的即梦提交内容。\n\n⚠️ 严格遵守系统提示中的「完整生成规范文档」全部规则，逐项对照执行，不得跳过。\n\n直接输出，不要省略。'

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
body = {"model": MODEL, "messages": [{"role":"system","content":sys_prompt}, {"role":"user","content":user_prompt}], "max_tokens": 8192, "temperature": 0.8}
data = json.dumps(body, ensure_ascii=False).encode("utf-8")
req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")

print('调用 DeepSeek API...', flush=True)
try:
    with urllib.request.urlopen(req, timeout=600) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        response = result["choices"][0]["message"]["content"]
except Exception as e:
    print(f'API错误: {e}', flush=True)
    sys.exit(1)

print(f'响应长度: {len(response)}字', flush=True)

passed, failures, warnings = validate_script(response, ep_num)
fname = f'脚本{ep_num:03d}_分镜脚本.md'
(WORK_DIR / fname).write_text(response, encoding='utf-8')

if passed:
    print(f'✅ 校验通过! 保存: {fname}', flush=True)
    if warnings:
        for w in warnings: print(f'  {w}')
else:
    print(f'⚠️ 校验未通过({len(failures)}项) 但仍保存: {fname}', flush=True)
    for f in failures: print(f'  - {f}', flush=True)

# 打印内容
print('\n' + '='*60)
print(response)
print('='*60)
