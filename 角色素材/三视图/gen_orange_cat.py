import os, subprocess, json, sys

os.environ["BUDDY_CLOUD_TOKEN"] = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJteWZFenA3ODNLaV9KQ3g4Vm5jM1hfaXg2alpyYjZDZjVPTWtHWk1QSTNzIn0.eyJleHAiOjE4MTEzMzY2OTcsImlhdCI6MTc4MDkxOTQzMywiYXV0aF90aW1lIjoxNzc5ODAwNDM0LCJqdGkiOiI5Nzk5YjQ3NS0yNGQ3LTQ3ZmUtYjI2Yi0zYjBjZmI3MWYyYjAiLCJpc3MiOiJodHRwczovL3d3dy5jb2RlYnVkZHkuY24vYXV0aC9yZWFsbXMvY29waWxvdCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiJkZmI5N2I0NS04MmI0LTRhZDctODA3Ny0zNDcwODdiMWIwNTciLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjb25zb2xlIiwic2lkIjoiMjVlN2U1MzctNGIyYy00ZTYyLThjYjQtODVhMTA3YThiMDVmIiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyIqIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzIiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgb2ZmbGluZV9hY2Nlc3MgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5pY2tuYW1lIjoi5rm-5LuU5p6q56WeIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiMTUwNDI3MDc5NzAifQ.swKq1809H2WiTXQO9_08pzzYoYTYdIj1DUtdC2lCRYXLVQNJUBhWvsKABanKRj4roohZfWzt8EO-48IgNkXgY7BOS76QJb8L2U7ZiHIJqczya7F9SKZbmiENpuLS-mhQ7q-qMbFi0fivXaUXM9TuxQOBm7loGyTiLsiMMk0wBFMJUiQ5lp8rdPyNIzxsmqN5bq41xfGNIAiPzkAoq8XhaTRso6jehKM_JRk9Vk37D5JrvnPcHaPLjW3XglwVnsTUqpeZjZk97TYgU6tw8O05dITfdBibzkwSGPJ9mWPONn-06SHUt88u_POMn43hE9o1W_jJDO0J18xxPUbj6_FnwA"

SCRIPT = r"d:\CodeBuddy CN\resources\app\extensions\genie\out\extension\builtin\buddy-multimodal-generation\scripts\buddy-cloud.py"
PYTHON = sys.executable

# Query previous job status
for i in range(6):
    print(f"--- Attempt {i+1} ---")
    result = subprocess.run(
        [PYTHON, SCRIPT, "image", "Q版卡通橘色肥猫三视图正面侧面背面白色背景圆滚滚胖橘猫"],
        capture_output=True, text=True, timeout=180
    )
    print("Code:", result.returncode)
    print(result.stdout.strip())
    if result.stderr:
        # Filter only relevant info
        for line in result.stderr.split("\n"):
            if "error" in line.lower() or "DONE" in line or "result" in line.lower() or "url" in line.lower():
                print("STDERR:", line.strip())
    if result.returncode == 0 and "concurrent" not in result.stdout.lower():
        break
    if i < 5:
        print("Waiting 20s...")
        import time
        time.sleep(20)
