#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JEV 决策门一键自检：诊断网络通道 + 跑真 JEV，告诉你当前该用哪种方式。

用法（需非沙箱环境，依赖系统全局 VPN/TUN 出网）：
    python jev_selfcheck.py
或显式指定本地模式（直连优先，读 D:\\dishu\\服务器\\.env 的 TYPESAFE_API_KEY）：
    JEV_LOCAL=1 python jev_selfcheck.py
"""
import os
import sys
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jev_client  # noqa: E402


def probe(label, url, proxy=None, timeout=12):
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
    opener = urllib.request.build_opener(*handlers) if handlers else urllib.request.build_opener()
    try:
        with opener.open(urllib.request.Request(url, method="GET"), timeout=timeout) as r:
            return f"{label}: HTTP {r.status}"
    except urllib.error.HTTPError as e:
        return f"{label}: HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return f"{label}: FAIL ({type(e).__name__})"


def main():
    print("===== 网络通道自检 =====")
    print(probe("① HTTP明文 经7890→百度", "http://www.baidu.com", proxy="http://127.0.0.1:7890"))
    print(probe("② HTTPS 经7890→qq(-k)", "https://www.qq.com", proxy="http://127.0.0.1:7890"))
    print(probe("③ 直连→typesafe (依赖系统 TUN)", "https://api.typesafe.ai/v1/systemone"))
    print(probe("④ HTTPS 经7890→typesafe", "https://api.typesafe.ai/v1/systemone", proxy="http://127.0.0.1:7890"))

    print("\n===== 真 JEV 调用（JEV_LOCAL=1 直连优先）=====")
    os.environ["JEV_LOCAL"] = "1"
    os.environ.setdefault("JEV_PROXY", "http://127.0.0.1:7890")  # 优先走 7890 绕过区域 451
    state = {"effect_goal": "水波纹玻璃折射", "platform": "抖音", "interaction": "点击触发"}
    questions = {
        "shader_type": {
            "type": "choice",
            "criteria": {"weave": "编织着色器", "caustics": "焦散着色器", "glass": "玻璃折射着色器"},
        },
    }
    try:
        out = jev_client.ask(state, questions)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        backend = out.get("backend")
        if backend == "typesafe":
            print("\n✅ 真 JEV 已返回（backend=typesafe），决策门链路完整可用。")
        elif backend == "llm_fallback":
            print("\n⚠️ 真 JEV 被区域拦截(451)或超时，已自动降级到推理模型。"
                  "若需真 JEV：切换 iKuuu 全局模式到允许区域节点（美国/日本）后重跑本脚本。")
        else:
            print("\n⚠️ 进入主理人裁决（agent_self）：缺少密钥或网络不可用，"
                  "请在 .env / 环境变量配置 TYPESAFE_API_KEY 或 OPC_API_KEY。")
    except Exception as e:  # noqa: BLE001
        print("JEV 调用异常:", e)


if __name__ == "__main__":
    main()
