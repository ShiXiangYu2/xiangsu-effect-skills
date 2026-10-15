#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
opc.fiime.cn 统一客户端：文本 / 生图 / 生视频。
密钥从环境变量 OPC_API_KEY 或本技能 .env 读取。
"""
import argparse
import io
import json
import os
import urllib.error
import urllib.request

OPC_BASE = "https://opc.fiime.cn/api/model-service/v1"


def load_key():
    k = os.environ.get("OPC_API_KEY")
    if k:
        return k
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    try:
        for line in io.open(p, encoding="utf-8"):
            if line.startswith("OPC_API_KEY="):
                return line.strip().split("=", 1)[1]
    except Exception:
        pass
    return ""


def _post(endpoint, payload, key):
    payload = dict(payload)
    req = urllib.request.Request(
        OPC_BASE + "/" + endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode(errors="ignore"))
        except Exception:  # noqa: BLE001
            return e.code, {"error": e.read().decode(errors="ignore")[:300]}
    except Exception as e:  # noqa: BLE001
        return -1, {"error": str(e)}


def text(model, messages, **kw):
    key = load_key()
    p = {"model": model, "messages": messages}
    p.update(kw)
    s, d = _post("chat/completions", p, key)
    return d


def image(model, prompt, size="512x512", n=1, **kw):
    key = load_key()
    p = {"model": model, "prompt": prompt, "size": size, "n": n}
    p.update(kw)
    s, d = _post("images/generations", p, key)
    return d


def video(model, prompt, **kw):
    key = load_key()
    p = {"model": model, "prompt": prompt}
    p.update(kw)
    s, d = _post("videos", p, key)
    return d


def main():
    ap = argparse.ArgumentParser(description="opc 统一客户端")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("text")
    t.add_argument("--model", default="opc-txt-v2")
    t.add_argument("--prompt", required=True)

    i = sub.add_parser("image")
    i.add_argument("--model", default="opc-image-v1")
    i.add_argument("--prompt", required=True)
    i.add_argument("--size", default="512x512")
    i.add_argument("--n", type=int, default=1)

    v = sub.add_parser("video")
    v.add_argument("--model", default="opc-video-v1")
    v.add_argument("--prompt", required=True)

    args = ap.parse_args()
    if args.cmd == "text":
        d = text(args.model, [{"role": "user", "content": args.prompt}])
    elif args.cmd == "image":
        d = image(args.model, args.prompt, args.size, args.n)
    else:
        d = video(args.model, args.prompt)
    print(json.dumps(d, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
