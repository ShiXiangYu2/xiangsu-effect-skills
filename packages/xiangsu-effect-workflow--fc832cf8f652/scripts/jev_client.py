#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JEV 决策门客户端 —— TypeSafe System One (jev-latest) 首选，推理模型降级，最后由主理人自行裁决。

设计目标（双模式）：
- 【本地模式 / 作者开发机】默认优先使用真 JEV：从本地 .env 读取 TYPESAFE_API_KEY，
  并通过本地代理（默认 http://127.0.0.1:7890）绕过区域拦截。设置环境变量 JEV_LOCAL=1 可
  强制启用作者本地路径（D:\\dishu\\服务器\\.env）与默认代理。
- 【公开版 / 其他用户】不要求任何私有密钥或私有路径。无 key 时自动降级：
  Tier1 真 JEV → Tier2 推理模型（需 OPC_API_KEY）→ Tier3 主理人自行裁决（返回 agent_self 信号，
  由编排层依据 criteria 现场判断）。整套管线不会因缺少密钥而中断。

密钥来源优先级（TYPESAFE_API_KEY）：
  环境变量 TYPESAFE_API_KEY > 技能 .env 的 TYPESAFE_API_KEY >
  JEV_LOCAL=1 时的作者本地路径 D:\\dishu\\服务器\\.env > 空（进入降级）

代理来源优先级（JEV_PROXY）：
  环境变量 JEV_PROXY > 技能 .env 的 JEV_PROXY > JEV_LOCAL=1 时默认 http://127.0.0.1:7890 >
  系统代理 > 直连（无代理）

输入: state(上下文) + questions(带 criteria 的选择/打分问题)
输出: 与 TypeSafe 同构的 { backend, jev_available, answers:{ 问题名:{choice/value, probability, confidence, rationale} } }
      Tier3 额外字段 decision_source="agent_self"，提示编排层现场裁决。
"""
import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request

TYPESAFE_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
# 作者本地开发路径：仅在 JEV_LOCAL=1 时启用，避免公开版依赖私有文件
AUTHOR_LOCAL_ENV = r"D:\dishu\服务器\.env"
OPC_BASE = "https://opc.fiime.cn/api/model-service/v1"
FALLBACK_MODEL = "nemotron-3-nano-omni-30b-a3b-reasoning"
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ENV = os.path.join(HERE, "..", ".env")
LOCAL_DEFAULT_PROXY = "http://127.0.0.1:7890"


# ----------------------------------------------------------------------------
# Key loading
# ----------------------------------------------------------------------------
def _read_env_val(path, key):
    try:
        for line in io.open(path, encoding="utf-8"):
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def load_typesafe_key():
    """TYPESAFE_API_KEY：环境变量 > 技能 .env > (JEV_LOCAL) 作者本地路径。"""
    k = os.environ.get("TYPESAFE_API_KEY")
    if k:
        return k
    k = _read_env_val(SKILL_ENV, "TYPESAFE_API_KEY")
    if k:
        return k
    if os.environ.get("JEV_LOCAL") == "1":
        return _read_env_val(AUTHOR_LOCAL_ENV, "TYPESAFE_API_KEY")
    return ""


def load_opc_key():
    """OPC_API_KEY：环境变量 > 技能 .env。"""
    k = os.environ.get("OPC_API_KEY")
    if k:
        return k
    return _read_env_val(SKILL_ENV, "OPC_API_KEY")


def load_jev_proxy():
    """JEV_PROXY：环境变量 > 技能 .env > (JEV_LOCAL) 直连（依赖系统 VPN/TUN）> 系统代理 > 空。

    注意：历史上 JEV_LOCAL 模式默认走 127.0.0.1:7890 本地代理绕过区域拦截；但部分代理
    端口（如 iKuuu 7890）仅支持 HTTP 明文、不支持 HTTPS 的 CONNECT 隧道（实测返回 501）。
    因此改为【直连优先】，由系统全局 VPN/TUN 接管 HTTPS 出站。若用户确想走本地代理，
    显式设置 JEV_PROXY=http://127.0.0.1:7890 即可。
    """
    p = os.environ.get("JEV_PROXY")
    if p:
        return p
    p = _read_env_val(SKILL_ENV, "JEV_PROXY")
    if p:
        return p
    if os.environ.get("JEV_LOCAL") == "1":
        # 直连（依赖已开启的 TUN/全局 VPN），不再强制 7890
        return os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or ""
    return os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or ""


# ----------------------------------------------------------------------------
# Backend 1: TypeSafe System One (real JEV)
# ----------------------------------------------------------------------------
def call_typesafe(state, questions, key, proxy=None):
    payload = json.dumps(
        {"state": state, "model": "jev-latest", "questions": questions},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        TYPESAFE_ENDPOINT,
        data=payload,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
    opener = urllib.request.build_opener(*handlers) if handlers else urllib.request.build_opener()
    try:
        with opener.open(req, timeout=25) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        if e.code == 451:
            raise RuntimeError(
                "Typesafe HTTP 451: 区域受限。请切换 iKuuu 全局模式到允许区域节点"
                "（如美国/日本）后重试；或自备 TypeSafe 账号时确保出口不在受限区域。"
            )
        raise RuntimeError(f"Typesafe HTTP {e.code}: {body[:200]}")
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Typesafe error: {e}")
    # 归一化：TypeSafe 原生返回已含 answers / choice / probabilities，尽量保留
    data["backend"] = "typesafe"
    data["jev_available"] = True
    data.setdefault("decision_source", "jev")
    return data


# ----------------------------------------------------------------------------
# Backend 2: LLM fallback (same output contract)
# ----------------------------------------------------------------------------
def _strip_fences(text):
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
    return t.strip()


def call_llm_fallback(state, questions, key, model):
    sys_prompt = (
        "你是决策判断引擎 JEV。给定上下文 state 与若干问题 questions"
        "（每题有 type 与 criteria），对每题返回一个 JSON 对象："
        "choice 从 criteria 的键中选一个、probability(0-1)、confidence(0-1)、rationale(简短)。"
        "只输出 JSON，不要解释。整体结构：{\"answers\":{<问题名>:{...}}}。"
    )
    user = (
        "state:\n"
        + json.dumps(state, ensure_ascii=False)
        + "\n\nquestions:\n"
        + json.dumps(questions, ensure_ascii=False)
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        OPC_BASE + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        content = data["choices"][0]["message"]["content"]
        out = json.loads(_strip_fences(content))
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"LLM fallback error: {e}")
    out["backend"] = "llm_fallback"
    out["jev_available"] = False
    out["decision_source"] = "llm_fallback"
    return out


# ----------------------------------------------------------------------------
# Backend 3: agent_self —— 无密钥时由主理人现场裁决（保证管线不中断）
# ----------------------------------------------------------------------------
def agent_self_decision(state, questions):
    """Tier3：JEV 与 OPC 均不可用。返回结构化信号，请编排层依据 criteria 自行裁决。"""
    echoed = {}
    for qname, q in questions.items():
        echoed[qname] = {
            "criteria": q.get("criteria", q.get("options", [])),
            "type": q.get("type", "choice"),
            "pending": True,
        }
    return {
        "backend": "agent_self",
        "jev_available": False,
        "decision_source": "agent_self",
        "note": "JEV 与推理模型后端均不可用（缺少 TYPESAFE_API_KEY / OPC_API_KEY）。"
                "请主理人依据下方 criteria 自行裁决，并将结论回填到 answers。",
        "answers_required": echoed,
    }


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------
def ask(state, questions, fallback_model=FALLBACK_MODEL, force_fallback=False,
        proxy=None, allow_agent_self=True):
    """返回决策结果 dict，按 Tier1→Tier2→Tier3 逐级降级，绝不抛错中断管线。"""
    # 兼容旧 list 格式：[{"name":..., ...}] → {"name": {...}}
    if isinstance(questions, list):
        questions = {q.get("name") or q.get("id") or f"q{i}": q for i, q in enumerate(questions)}
    if proxy is None:
        proxy = load_jev_proxy()
    key = load_typesafe_key()
    if key and not force_fallback:
        try:
            return call_typesafe(state, questions, key, proxy)
        except Exception as e:  # noqa: BLE001
            print(f"[jev] TypeSafe 不可用（{e}），降级到推理模型 {fallback_model}", file=sys.stderr)
    opc = load_opc_key()
    if opc:
        try:
            return call_llm_fallback(state, questions, opc, fallback_model)
        except Exception as e:  # noqa: BLE001
            print(f"[jev] 推理模型降级失败（{e}），转交主理人自行裁决", file=sys.stderr)
    if allow_agent_self:
        return agent_self_decision(state, questions)
    raise RuntimeError("无可用决策后端：TypeSafe 失败且缺少 OPC_API_KEY，且已禁用 agent_self")


def main():
    ap = argparse.ArgumentParser(description="JEV 决策门：TypeSafe 首选，推理模型降级，最后主理人裁决")
    ap.add_argument("--state", required=True, help="JSON 字符串，决策上下文")
    ap.add_argument("--questions", required=True, help="JSON 字符串，带 criteria 的问题")
    ap.add_argument("--fallback-model", default=FALLBACK_MODEL)
    ap.add_argument("--proxy", default=None, help="可选：让 TypeSafe 走代理绕过区域限制，如 http://127.0.0.1:7890")
    ap.add_argument("--force-fallback", action="store_true", help="强制走推理模型降级")
    ap.add_argument("--no-agent-self", action="store_true", help="禁止 Tier3 主理人裁决（不可用则直接报错）")
    args = ap.parse_args()
    state = json.loads(args.state)
    questions = json.loads(args.questions)
    # 兼容旧 list 格式：[{"name":..., ...}] → {"name": {...}}
    if isinstance(questions, list):
        questions = {q.get("name") or q.get("id") or f"q{i}": q for i, q in enumerate(questions)}
    out = ask(state, questions, args.fallback_model, args.force_fallback,
              args.proxy, allow_agent_self=not args.no_agent_self)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
