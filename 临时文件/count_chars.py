import re

with open('../脚本011_照镜子做鬼脸_分镜脚本.md', 'r', encoding='utf-8') as f:
    text = f.read()

blocks = re.findall(r'```\n(⚠️ 角色铁律.*?)\n```', text, re.DOTALL)
for i, b in enumerate(blocks):
    stripped = re.sub(r'\s', '', b)
    print(f'块{i+1} ({len(stripped)}字)')
