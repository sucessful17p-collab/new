"""Provider contract. Demo analysis is deterministic source parsing in main.py."""
from __future__ import annotations
import json
import os
from typing import Any, Protocol
from urllib.request import Request, urlopen

class AIProvider(Protocol):
    name: str
    def complete_json(self, *, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]: ...

class MockProvider:
    name = "mock"
    def complete_json(self, *, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("MockProvider does not invent model output; use deterministic source extraction.")

class OpenAICompatibleProvider:
    name = "openai-compatible"
    def __init__(self, base_url: str | None = None, model: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("OPENAI_MODEL", "")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
    def complete_json(self, *, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        if not self.model or not self.api_key: raise RuntimeError("OpenAI-compatible provider requires OPENAI_MODEL and OPENAI_API_KEY.")
        body = json.dumps({"model": self.model, "messages": [{"role":"system","content":system},{"role":"user","content":prompt}],"response_format":{"type":"json_object"}}).encode()
        req = Request(self.base_url + "/chat/completions", data=body, headers={"Authorization":"Bearer "+self.api_key,"Content-Type":"application/json"})
        with urlopen(req, timeout=60) as response: result = json.loads(response.read())
        parsed = json.loads(result["choices"][0]["message"]["content"])
        if not isinstance(parsed, dict): raise ValueError("Provider response was not a JSON object.")
        return parsed

class OllamaProvider:
    name = "ollama"
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "")
    def complete_json(self, *, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        if not self.model: raise RuntimeError("Ollama provider requires OLLAMA_MODEL.")
        body = json.dumps({"model":self.model,"system":system,"prompt":prompt,"stream":False,"format":schema}).encode()
        req = Request(self.base_url + "/api/generate", data=body, headers={"Content-Type":"application/json"})
        with urlopen(req, timeout=120) as response: result = json.loads(response.read())
        parsed = json.loads(result["response"])
        if not isinstance(parsed, dict): raise ValueError("Provider response was not a JSON object.")
        return parsed

def configured_provider() -> AIProvider:
    choice = os.getenv("AI_PROVIDER", "mock").lower()
    if choice == "ollama": return OllamaProvider()
    if choice in {"openai", "openai-compatible"}: return OpenAICompatibleProvider()
    return MockProvider()
