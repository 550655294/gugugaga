#!/usr/bin/env python3
"""
即梦 AI 视频生成脚本 — 基于火山引擎视觉智能 API
支持：文生视频 / 图生视频（首帧参考图）

用法:
  python jimeng_video.py i2v --image "角色素材/正面.png" --prompt "企鹅挥手打招呼"
  python jimeng_video.py t2v --prompt "一只可爱的小猫在花园里奔跑"
  python jimeng_video.py i2v --image-url "https://example.com/img.png" --prompt "企鹅走路"

环境变量:
  JIMENG_ACCESS_KEY  — 火山引擎 AccessKey
  JIMENG_SECRET_KEY  — 火山引擎 SecretKey
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# Windows 终端 UTF-8 兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── 配置 ────────────────────────────────────────────────────────────────────

ENDPOINT = "https://visual.volcengineapi.com"
HOST = "visual.volcengineapi.com"
REGION = "cn-north-1"
SERVICE = "cv"
VERSION = "2022-08-31"

# 即梦视频 req_key
REQ_KEY_T2V = "jimeng_t2v_v30"       # 文生视频（720p/1080p）
REQ_KEY_I2V = "jimeng_i2v_first_v30"  # 图生视频（首帧）

ACCESS_KEY = os.environ.get("JIMENG_ACCESS_KEY", "")
SECRET_KEY = os.environ.get("JIMENG_SECRET_KEY", "")

POLL_INTERVAL = 5   # 秒
POLL_TIMEOUT = 600  # 秒（10 分钟）

# ─── BuddyCloud 上传配置（用来把本地图片转成公网 URL） ────────────────────────

BUDDY_CLOUD_TOKEN = os.environ.get("BUDDY_CLOUD_TOKEN", "")
BUDDY_CLOUD_ENDPOINT = "https://api.codebuddy.cn"


# ─── AWS V4 签名 ──────────────────────────────────────────────────────────────

def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def sign_v4(action: str, body: dict) -> tuple:
    """返回 (url, headers, body_str)"""
    body_str = json.dumps(body, ensure_ascii=False)
    payload_hash = sha256_hex(body_str)

    t = datetime.now(timezone.utc)
    x_date = t.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = t.strftime("%Y%m%d")

    qs = f"Action={action}&Version={VERSION}"

    canonical_headers = (
        f"content-type:application/json\n"
        f"host:{HOST}\n"
        f"x-content-sha256:{payload_hash}\n"
        f"x-date:{x_date}\n"
    )
    signed_headers = "content-type;host;x-content-sha256;x-date"

    canonical_request = "\n".join([
        "POST", "/", qs,
        canonical_headers, signed_headers, payload_hash,
    ])

    credential_scope = f"{date_stamp}/{REGION}/{SERVICE}/request"
    string_to_sign = "\n".join([
        "HMAC-SHA256", x_date, credential_scope, sha256_hex(canonical_request),
    ])

    def _hmac(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = _hmac(SECRET_KEY.encode("utf-8"), date_stamp)
    k_region = _hmac(k_date, REGION)
    k_service = _hmac(k_region, SERVICE)
    k_signing = _hmac(k_service, "request")

    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    url = f"{ENDPOINT}?{qs}"
    headers = {
        "Content-Type": "application/json",
        "X-Date": x_date,
        "X-Content-Sha256": payload_hash,
        "Authorization": (
            f"HMAC-SHA256 Credential={ACCESS_KEY}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        ),
    }
    return url, headers, body_str


def api_submit(req_key: str, extra: dict) -> str:
    """提交异步任务，返回 task_id"""
    body = {"req_key": req_key}
    body.update(extra)
    url, headers, body_str = sign_v4("CVSync2AsyncSubmitTask", body)

    print(f"  [SEND] 提交 {req_key}...")
    resp = requests.post(url, headers=headers, data=body_str.encode("utf-8"), timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    if data.get("code") != 10000:
        raise RuntimeError(f"API 错误 [{data.get('code')}]: {data.get('message')}  request_id={data.get('request_id')}")

    task_id = data["data"]["task_id"]
    print(f"     task_id: {task_id}")
    return task_id


def api_query(req_key: str, task_id: str) -> dict:
    """查询任务状态，返回 data 字段"""
    body = {
        "req_key": req_key,
        "task_id": task_id,
        "req_json": json.dumps({"return_url": True, "logo_info": {"add_logo": False}}),
    }
    url, headers, body_str = sign_v4("CVSync2AsyncGetResult", body)

    resp = requests.post(url, headers=headers, data=body_str.encode("utf-8"), timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    if data.get("code") != 10000:
        raise RuntimeError(f"API 错误 [{data.get('code')}]: {data.get('message')}")

    return data["data"]


def wait_for_result(req_key: str, task_id: str) -> dict:
    """轮询直到任务完成"""
    deadline = time.time() + POLL_TIMEOUT
    dots = 0

    while time.time() < deadline:
        data = api_query(req_key, task_id)
        status = data.get("status", "").lower()

        if status in ("done", "success"):
            print()
            return data

        if status == "failed":
            raise RuntimeError(f"任务失败: {json.dumps(data, ensure_ascii=False)}")

        if status in ("not_found", "expired"):
            raise RuntimeError(f"任务 {status}: 可能已过期（12h）")

        dots = (dots + 1) % 4
        sys.stdout.write(f"\r    等待中{'.' * (dots + 1)}    ")
        sys.stdout.flush()
        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"查询超时（{POLL_TIMEOUT}s），task_id: {task_id}")


# ─── 本地图片 → Base64 数据 ───────────────────────────────────────────────────

def image_to_data_uri(filepath: str) -> tuple:
    """读取本地图片，返回 (data_uri, ext, size)"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {filepath}")

    ext = path.suffix.lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"

    with open(path, "rb") as f:
        img_data = f.read()

    b64 = base64.b64encode(img_data).decode("ascii")
    data_uri = f"data:image/{ext};base64,{b64}"
    return data_uri, ext, len(img_data)


# ─── BuddyCloud 上传（获取公网 URL）──────────────────────────────────────────

def buddy_cloud_upload(filepath: str) -> str:
    """
    通过 BuddyCloud 上传图片获取临时公网 URL。
    返回 URL 字符串。
    """
    if not BUDDY_CLOUD_TOKEN:
        raise RuntimeError("未设置 BUDDY_CLOUD_TOKEN 环境变量，无法上传图片")

    data_uri, _, size = image_to_data_uri(filepath)
    print(f"  [CLOUD]  上传图片到 BuddyCloud ({size / 1024:.0f} KB)...")

    # 用 sync-submit 把图片上传（利用 video-fx 或 image 模式）
    # 实际上我们需要一个纯粹的图片上传接口，这里试试用 sync-submit 的处理机制
    # 作为 fallback，直接用 base64 data URI 方式传给即梦

    raise NotImplementedError("BuddyCloud 直接上传待实现，请使用 --image-url")


# ─── 主命令 ──────────────────────────────────────────────────────────────────

def cmd_t2v(args: list):
    """文生视频"""
    prompt = None
    seed = -1
    frames = 121
    aspect_ratio = "16:9"

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--prompt":
            i += 1; prompt = args[i]
        elif a == "--seed":
            i += 1; seed = int(args[i])
        elif a == "--frames":
            i += 1; frames = int(args[i])
        elif a == "--ratio":
            i += 1; aspect_ratio = args[i]
        else:
            print(f"未知参数: {a}")
        i += 1

    if not prompt:
        raise ValueError("请提供 --prompt")

    print(f"[VIDEO] 即梦文生视频")
    print(f"   prompt: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")
    print(f"   比例: {aspect_ratio}, 帧数: {frames}, 种子: {seed}")
    print()

    task_id = api_submit(REQ_KEY_T2V, {
        "prompt": prompt,
        "seed": seed,
        "frames": frames,
        "aspect_ratio": aspect_ratio,
    })

    result = wait_for_result(REQ_KEY_T2V, task_id)
    print_result(result)


def cmd_i2v(args: list):
    """图生视频（首帧参考图）"""
    prompt = None
    image_url = None
    image_file = None
    seed = -1
    frames = 121

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--prompt":
            i += 1; prompt = args[i]
        elif a == "--image":
            i += 1; image_file = args[i]
        elif a == "--image-url":
            i += 1; image_url = args[i]
        elif a == "--seed":
            i += 1; seed = int(args[i])
        elif a == "--frames":
            i += 1; frames = int(args[i])
        else:
            print(f"未知参数: {a}")
        i += 1

    if not prompt:
        raise ValueError("请提供 --prompt")
    if not image_url and not image_file:
        raise ValueError("请提供 --image（本地文件）或 --image-url（公网 URL）")

    # 处理本地图片：尝试多种方式传给 API
    if image_file and not image_url:
        image_file = str(Path(image_file).resolve())
        if not os.path.exists(image_file):
            raise FileNotFoundError(f"图片不存在: {image_file}")

        print(f"[IMG] 本地图片: {image_file}")

        # 方式1：先试试用 buddy-cloud 上传获取 URL
        try:
            image_url = buddy_cloud_upload(image_file)
        except (NotImplementedError, RuntimeError):
            pass

        # 方式2：如果没有 buddy-cloud，尝试 base64 data URI
        if not image_url:
            data_uri, ext, size = image_to_data_uri(image_file)
            print(f"  [FILE] 使用 Base64 Data URI ({ext}, {size / 1024:.0f} KB)")
            # 即梦 API 的 image_urls 参数可能支持 data URI
            image_url = data_uri

    print(f"[VIDEO] 即梦图生视频（首帧）")
    print(f"   prompt: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")
    print(f"   图片: {image_url[:80]}{'...' if len(image_url) > 80 else ''}")
    print(f"   帧数: {frames}, 种子: {seed}")
    print()

    # 判断是 URL 还是 base64 data URI
    extra = {
        "prompt": prompt,
        "seed": seed,
        "frames": frames,
    }
    if image_url.startswith("data:"):
        # base64 data URI → 用 binary_data_base64 传（去掉前缀）
        b64_payload = image_url.split(",", 1)[1]
        extra["binary_data_base64"] = [b64_payload]
        print(f"  [FILE] 使用 binary_data_base64 ({len(b64_payload)} chars)")
    else:
        extra["image_urls"] = [image_url]

    task_id = api_submit(REQ_KEY_I2V, extra)

    result = wait_for_result(REQ_KEY_I2V, task_id)
    print_result(result)


def print_result(data: dict):
    """打印/下载结果"""
    print(f"\n{'='*60}")
    print(f"[OK] 视频生成完成！")

    video_url = data.get("video_url") or data.get("video_urls", [None])[0]
    image_urls = data.get("image_urls", [])

    if video_url:
        print(f"\n[MOVIE] 视频链接: {video_url}")
        # 尝试下载
        try:
            print("[DL]  下载中...")
            resp = requests.get(video_url, timeout=300, stream=True)
            if resp.status_code == 200:
                out_path = Path("e:/咕咕嘎嘎/即梦生成视频.mp4")
                total = int(resp.headers.get("content-length", 0))
                with open(out_path, "wb") as f:
                    downloaded = 0
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = downloaded * 100 // total
                            sys.stdout.write(f"\r    进度: {pct}%")
                            sys.stdout.flush()
                print(f"\n[SAVE] 已保存: {out_path}")
                print(f"   大小: {out_path.stat().st_size / 1024 / 1024:.1f} MB")
        except Exception as e:
            print(f"[WARN]  下载失败: {e}")

    elif image_urls:
        print(f"\n[MOVIE] 结果链接 (共 {len(image_urls)} 个):")
        for i, u in enumerate(image_urls):
            print(f"   [{i+1}] {u}")

    else:
        print(f"\n[LIST] 原始响应:")
        print(json.dumps(data, ensure_ascii=False, indent=2))


# ─── 主入口 ──────────────────────────────────────────────────────────────────

def main():
    if not ACCESS_KEY or not SECRET_KEY:
        print("[ERR] 请设置环境变量：")
        print("   setx JIMENG_ACCESS_KEY \"你的AccessKey\"")
        print("   setx JIMENG_SECRET_KEY \"你的SecretKey\"")
        sys.exit(1)

    args = sys.argv[1:]
    if not args or args[0] in ("help", "h", "--help", "-h"):
        print(__doc__)
        return

    cmd = args[0].lower()
    rest = args[1:]

    try:
        if cmd == "t2v":
            cmd_t2v(rest)
        elif cmd == "i2v":
            cmd_i2v(rest)
        else:
            print(f"未知命令: {cmd}")
            print(__doc__)
            sys.exit(1)
    except Exception as e:
        print(f"\n[ERR] 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
