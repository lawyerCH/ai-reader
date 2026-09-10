"""可选的 OpenAI 兼容 LLM 接入。

未配置 AIREADER_LLM_BASE_URL / AIREADER_LLM_API_KEY 时，所有功能由本地启发式引擎完成，
系统零配置可用；配置后问答/批注/改写自动切换为真实大模型（流式）。
"""
from __future__ import annotations

import json
import httpx

from ..config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL


def llm_ready() -> bool:
    return bool(LLM_BASE_URL and LLM_API_KEY)


def _headers():
    return {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}


async def chat(messages: list[dict], temperature: float = 0.8, timeout: float = 60) -> str:
    if not llm_ready():
        raise RuntimeError("LLM not configured")
    url = f"{LLM_BASE_URL}/chat/completions"
    payload = {"model": LLM_MODEL, "messages": messages, "temperature": temperature}
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, headers=_headers(), json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]


async def stream_chat(messages: list[dict], temperature: float = 0.8):
    if not llm_ready():
        raise RuntimeError("LLM not configured")
    url = f"{LLM_BASE_URL}/chat/completions"
    payload = {"model": LLM_MODEL, "messages": messages,
               "temperature": temperature, "stream": True}
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, headers=_headers(), json=payload) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    delta = obj["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    continue


PERSONA_SYSTEM = {
    "plot": "你是「剧情党」，熟读万本网文，擅长分析伏笔、结构和走向，说话干脆，爱用「敲黑板」「我赌五毛」等读者口吻。",
    "lore": "你是「考据党」，严谨细致，专注世界观设定、历史背景与前后一致性，引用原文证据。",
    "emotion": "你是「情感分析师」，关注人物动机、关系变化和潜台词，语气温柔细腻。",
    "snark": "你是「吐槽君」，幽默毒舌，专治逻辑硬伤和老套桥段，但吐槽有理有据。",
    "professor": "你是「文学教授」，从叙事学、修辞、文体角度赏析，引用文本细节，专业但不端着。",
    "character": "你要代入书中角色，以第一人称说话，语言风格贴合该角色的身份性格。",
}
