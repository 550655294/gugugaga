"""
🎬 视频尾帧提取工具
拖拽/选择视频 → 一键提取最后一帧 → 预览下载
访问 http://localhost:8766
"""

import os, sys, json, time, subprocess, tempfile, shutil, io, re
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, parse_qs

# 强制 UTF-8 输出，避免 Windows GBK emoji 报错
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

WORK_DIR = Path(__file__).parent.parent.resolve()
PORT = 8766
OUTPUT_DIR = WORK_DIR / "尾帧截图"
OUTPUT_DIR.mkdir(exist_ok=True)

# ═══ 找到 ffmpeg ═══
def find_ffmpeg():
    paths = [
        "ffmpeg",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        os.path.expandvars(r"%ProgramFiles%\ffmpeg\bin\ffmpeg.exe"),
    ]
    for p in paths:
        if p == "ffmpeg":
            try:
                subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
                return "ffmpeg", "ffprobe"
            except Exception:
                continue
        elif os.path.exists(p):
            d = os.path.dirname(p)
            return p, os.path.join(d, "ffprobe.exe")
    return None, None

FFMPEG, FFPROBE = find_ffmpeg()

def get_video_duration(video_path):
    """获取视频时长（秒）"""
    if not FFPROBE:
        return None
    try:
        r = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30
        )
        return float(r.stdout.strip())
    except Exception:
        return None

def extract_last_frame(video_path, output_path):
    """提取视频最后一帧"""
    if not FFMPEG:
        raise RuntimeError("未找到 ffmpeg，请安装后重试")

    # 获取时长
    duration = get_video_duration(video_path)
    if duration is None or duration <= 0:
        # 降级：用 -sseof 方式
        cmd = [FFMPEG, "-y", "-sseof", "-2", "-i", video_path,
               "-update", "1", "-vframes", "1", "-q:v", "2", output_path]
    else:
        # 精确 seek 到视频末尾前 0.1 秒
        seek_time = max(0, duration - 0.1)
        cmd = [FFMPEG, "-y", "-ss", str(seek_time), "-i", video_path,
               "-vframes", "1", "-q:v", "2", output_path]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[:500]}")
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
        raise RuntimeError("提取的图片无效或为空")
    return True

# ═══ HTTP 服务 ═══
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        with open(path, "rb") as f:
            self.wfile.write(f.read())

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/" or path == "/index.html":
            html = UI_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html)
        elif path.startswith("/output/"):
            # 提供提取的图片
            fname = unquote(path.split("/output/", 1)[1])
            fp = OUTPUT_DIR / fname
            if fp.exists() and fp.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                self._send_file(fp, f"image/{fp.suffix[1:]}")
            else:
                self._json({"error": "文件不存在"}, 404)
        elif path == "/api/status":
            self._json({
                "ffmpeg": bool(FFMPEG),
                "output_dir": str(OUTPUT_DIR)
            })
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/extract":
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len == 0:
                self._json({"error": "no file"}, 400)
                return

            # 读取上传文件
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" in content_type:
                # 解析 multipart
                boundary = content_type.split("boundary=", 1)[1].strip()
                if boundary.startswith('"') and boundary.endswith('"'):
                    boundary = boundary[1:-1]

                body = self.rfile.read(content_len)
                parts = body.split(b"--" + boundary.encode())
                file_data = None
                original_name = "video.mp4"
                for part in parts:
                    if b"Content-Disposition" not in part:
                        continue
                    if b"filename=" in part:
                        # 提取文件名和内容
                        header_end = part.find(b"\r\n\r\n")
                        if header_end == -1:
                            continue
                        headers = part[:header_end].decode("utf-8", errors="replace")
                        content = part[header_end + 4:]
                        # 去掉末尾的 \r\n
                        if content.endswith(b"\r\n"):
                            content = content[:-2]
                        # 提取文件名
                        fn_match = re.search(r'filename="([^"]*)"', headers)
                        if fn_match:
                            original_name = fn_match.group(1)
                        file_data = content
                        break

                if not file_data:
                    self._json({"error": "未找到文件数据"}, 400)
                    return
            else:
                # 原始二进制上传
                file_data = self.rfile.read(content_len)
                original_name = self.headers.get("X-Filename", "video.mp4")

            if len(file_data) < 1024:
                self._json({"error": "文件太小"}, 400)
                return

            # 保存临时文件
            tmp_dir = tempfile.mkdtemp(prefix="vframe_")
            tmp_in = os.path.join(tmp_dir, "input" + os.path.splitext(original_name)[1])
            with open(tmp_in, "wb") as f:
                f.write(file_data)

            # 提取尾帧
            ts = time.strftime("%m%d_%H%M%S")
            out_name = f"尾帧_{Path(original_name).stem}_{ts}.jpg"
            out_path = str(OUTPUT_DIR / out_name)

            try:
                extract_last_frame(tmp_in, out_path)
                self._json({
                    "ok": True,
                    "filename": out_name,
                    "url": f"/output/{out_name}",
                    "input_name": original_name
                })
            except Exception as e:
                self._json({"error": str(e)}, 500)
            finally:
                # 清理临时文件
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass
        else:
            self._json({"error": "not found"}, 404)

# ═══ UI ═══
UI_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎬 视频尾帧提取器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;min-height:100vh}
header{background:#161b22;border-bottom:1px solid #30363d;padding:12px 24px;display:flex;align-items:center;gap:12px}
header h1{font-size:16px;color:#58a6ff;white-space:nowrap}
header .sub{font-size:12px;color:#8b949e}
.main{padding:20px;max-width:720px;margin:0 auto}
/* 拖拽区 */
.dropzone{border:2px dashed #30363d;border-radius:12px;padding:40px 20px;text-align:center;cursor:pointer;transition:.2s;margin-bottom:16px}
.dropzone:hover,.dropzone.drag{border-color:#58a6ff;background:#1c2333}
.dropzone .icon{font-size:48px;margin-bottom:8px}
.dropzone p{color:#8b949e;font-size:14px}
.dropzone .hint{color:#484f58;font-size:12px;margin-top:4px}
/* 状态区 */
.status{display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:13px;color:#8b949e}
.status .ready{color:#3fb950}
.status .warn{color:#d29922}
/* 预览 */
.preview{border-radius:12px;overflow:hidden;border:1px solid #30363d;display:none;margin-bottom:12px}
.preview.show{display:block}
.preview img{width:100%;display:block}
.preview-bar{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;background:#161b22;border-top:1px solid #30363d}
.preview-name{font-size:13px;color:#c9d1d9}
/* 按钮 */
.btn{padding:8px 20px;border-radius:8px;border:none;cursor:pointer;font-size:14px;font-weight:500;transition:.15s}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-primary{background:#238636;color:#fff}
.btn-primary:hover:not(:disabled){background:#2ea043}
.btn-outline{background:transparent;border:1px solid #30363d;color:#c9d1d9}
.btn-outline:hover:not(:disabled){background:#21262d}
.btn-row{display:flex;gap:10px;margin-bottom:12px}
/* 进度 */
.progress{display:none;margin:12px 0}
.progress.show{display:block}
.progress-bar{height:4px;background:#21262d;border-radius:2px;overflow:hidden}
.progress-fill{height:100%;background:#238636;width:0%;transition:.3s;border-radius:2px}
.progress-text{font-size:12px;color:#8b949e;margin-top:4px}
/* 视频预览 */
.video-preview{display:none;margin-bottom:12px;border-radius:12px;overflow:hidden;border:1px solid #30363d}
.video-preview.show{display:block}
.video-preview video{width:100%;display:block;max-height:360px}
/* 隐藏input */
.hidden-input{display:none}
/* 对话 */
.toast{position:fixed;top:20px;left:50%;transform:translateX(-50%);padding:10px 24px;border-radius:8px;font-size:14px;z-index:999;animation:in .3s}
.toast.success{background:#238636;color:#fff}
.toast.error{background:#da3633;color:#fff}
@keyframes in{from{opacity:0;transform:translateX(-50%) translateY(-10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
</style>
</head>
<body>

<header>
  <h1>🎬 视频尾帧提取器</h1>
  <span class="sub">提取视频最后一帧 · 自动裁剪 · 即梦操作卡用</span>
</header>

<div class="main">

  <div id="dropZone" class="dropzone">
    <div class="icon">📁</div>
    <p>拖拽视频到此处，或点击选择</p>
    <p class="hint">支持 MP4 / MOV / AVI / WEBM / MKV</p>
    <input id="fileInput" type="file" class="hidden-input" accept="video/*">
  </div>

  <div class="status">
    <span id="statusIcon">⏳</span>
    <span id="statusText">检测 ffmpeg...</span>
  </div>

  <!-- 视频预览 -->
  <div id="videoPreview" class="video-preview">
    <video id="videoEl" controls></video>
  </div>

  <div class="btn-row">
    <button id="extractBtn" class="btn btn-primary" disabled>🎞 提取尾帧</button>
    <button id="clearBtn" class="btn btn-outline" disabled>✕ 清除</button>
    <button id="downloadBtn" class="btn btn-outline" disabled style="display:none">💾 下载尾帧</button>
  </div>

  <div id="progress" class="progress">
    <div class="progress-bar"><div id="progressFill" class="progress-fill"></div></div>
    <div id="progressText" class="progress-text">提取中...</div>
  </div>

  <!-- 结果预览 -->
  <div id="resultPreview" class="preview">
    <img id="resultImg" alt="尾帧截图">
    <div class="preview-bar">
      <span id="resultName" class="preview-name"></span>
      <button id="copyBtn" class="btn btn-outline" onclick="copyPath()">📋 复制路径</button>
    </div>
  </div>

</div>

<script>
let selectedFile = null;
let lastResult = null;

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const videoEl = document.getElementById('videoEl');
const videoPreview = document.getElementById('videoPreview');
const extractBtn = document.getElementById('extractBtn');
const clearBtn = document.getElementById('clearBtn');
const downloadBtn = document.getElementById('downloadBtn');
const progress = document.getElementById('progress');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultPreview = document.getElementById('resultPreview');
const resultImg = document.getElementById('resultImg');
const resultName = document.getElementById('resultName');
const statusIcon = document.getElementById('statusIcon');
const statusText = document.getElementById('statusText');

// --- 拖拽 & 选择 ---
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => { if(e.target.files[0]) loadFile(e.target.files[0]); });

dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag');
  if(e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0]);
});

function loadFile(file){
  if(!file.type.startsWith('video/')){
    toast('请选择视频文件', 'error');
    return;
  }
  selectedFile = file;
  extractBtn.disabled = false;
  clearBtn.disabled = false;
  resultPreview.classList.remove('show');
  downloadBtn.style.display = 'none';
  lastResult = null;

  // 预览
  const url = URL.createObjectURL(file);
  videoEl.src = url;
  videoPreview.classList.add('show');
  dropZone.querySelector('.icon').textContent = '✅';
  dropZone.querySelector('p').textContent = file.name;
  dropZone.querySelector('.hint').textContent = (file.size/1024/1024).toFixed(1)+' MB';
}

clearBtn.addEventListener('click', () => {
  selectedFile = null;
  extractBtn.disabled = true;
  clearBtn.disabled = true;
  downloadBtn.style.display = 'none';
  lastResult = null;
  videoEl.src = '';
  videoPreview.classList.remove('show');
  resultPreview.classList.remove('show');
  progress.classList.remove('show');
  URL.revokeObjectURL(videoEl.src);
  dropZone.querySelector('.icon').textContent = '📁';
  dropZone.querySelector('p').textContent = '拖拽视频到此处，或点击选择';
  dropZone.querySelector('.hint').textContent = '支持 MP4 / MOV / AVI / WEBM / MKV';
});

// --- 提取 ---
extractBtn.addEventListener('click', async () => {
  if(!selectedFile) return;
  extractBtn.disabled = true;
  progress.classList.add('show');
  progressFill.style.width = '30%';
  progressText.textContent = '上传中...';

  try{
    const form = new FormData();
    form.append('video', selectedFile, selectedFile.name);

    const resp = await fetch('/api/extract', {
      method: 'POST',
      body: form
    });

    progressFill.style.width = '90%';
    progressText.textContent = '处理中...';

    const data = await resp.json();

    if(data.ok){
      progressFill.style.width = '100%';
      progressText.textContent = '完成！';
      lastResult = data;
      resultImg.src = data.url + '?t=' + Date.now();
      resultName.textContent = data.filename;
      resultPreview.classList.add('show');
      downloadBtn.style.display = 'inline-flex';
      downloadBtn.disabled = false;
      downloadBtn.onclick = () => {
        const a = document.createElement('a');
        a.href = data.url;
        a.download = data.filename;
        a.click();
      };
      toast('✅ 尾帧提取成功！', 'success');
    }else{
      toast('❌ ' + (data.error||'未知错误'), 'error');
    }
  }catch(e){
    toast('❌ 请求失败: ' + e.message, 'error');
  }finally{
    extractBtn.disabled = false;
    setTimeout(() => {
      progress.classList.remove('show');
      progressFill.style.width = '0%';
    }, 800);
  }
});

function copyPath(){
  if(!lastResult) return;
  navigator.clipboard.writeText(lastResult.filename).then(
    () => toast('📋 已复制文件名', 'success'),
    () => toast('复制失败，请手动复制', 'error')
  );
}

// --- toast ---
function toast(msg, type){
  const t = document.createElement('div');
  t.className = 'toast ' + (type||'success');
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2000);
}

// --- 检查 ffmpeg ---
(async function check(){
  try{
    const r = await fetch('/api/status');
    const s = await r.json();
    if(s.ffmpeg){
      statusIcon.textContent = '✅';
      statusText.textContent = 'ffmpeg 就绪 · 可提取尾帧';
    }else{
      statusIcon.textContent = '⚠️';
      statusText.textContent = '未检测到 ffmpeg，请安装后使用';
    }
  }catch(e){
    statusIcon.textContent = '❌';
    statusText.textContent = '后端未连接';
  }
})();
</script>
</body>
</html>
"""

# ═══ 主函数 ═══
def main():
    if not FFMPEG:
        print("⚠️  未找到 ffmpeg！")
        print("   请安装 ffmpeg 并添加到 PATH:")
        print("   1. 下载: https://ffmpeg.org/download.html")
        print("   2. 解压后将 bin 目录加入系统 PATH")
        print()
        print("   或者直接下载 Windows 构建版:")
        print("   https://www.gyan.dev/ffmpeg/builds/")
        print()
        input("按回车退出...")
        sys.exit(1)

    print(f"🎬 视频尾帧提取器已启动")
    print(f"🌐 浏览器即将打开: http://localhost:{PORT}")
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print(f"按下 Ctrl+C 停止")
    print("-" * 50)

    import threading
    def open_browser():
        # 等待服务器就绪
        for _ in range(20):
            time.sleep(0.3)
            try:
                import urllib.request
                urllib.request.urlopen(f"http://localhost:{PORT}/api/status", timeout=2)
                break
            except Exception:
                pass

        url = f"http://localhost:{PORT}"
        # 方案1：os.startfile（Windows ShellExecute，最直接）
        try:
            os.startfile(url)
            print(f"✅ 浏览器已打开: {url}")
            return
        except Exception:
            pass

        # 方案2：cmd /c start（独立进程，不依赖 Python 环境）
        try:
            subprocess.run(f'cmd /c start "" "{url}"', shell=True, timeout=5)
            print(f"✅ 浏览器已打开: {url}")
            return
        except Exception:
            pass

        # 方案3：webbrowser 模块（跨平台通用）
        try:
            import webbrowser
            webbrowser.open(url, new=2, autoraise=True)
            print(f"✅ 浏览器已打开: {url}")
            return
        except Exception:
            pass

        # 兜底：手动提示
        print(f"\n❌ 自动打开浏览器失败，请手动打开: {url}")

    threading.Thread(target=open_browser, daemon=True).start()

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 已停止")
        server.server_close()

if __name__ == "__main__":
    main()
