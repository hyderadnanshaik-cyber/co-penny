# llm/llm_client.py
import os
import requests
from typing import Optional, Dict, Any, List
import time

class LLMClient:
    def __init__(
        self,
        base_url: str = None,
        timeout: int = 60,
        retries: int = 2,
        backoff_seconds: float = 1.5
    ):
        """
        Lightweight client for multiple LLM providers (FreeLLM-compatible and Gemini).
        Supports multiple response shapes and payload formats commonly seen across providers.
        Environment overrides:
          - LLM_PROVIDER: 'free' | 'gemini' (default: 'free')
          - LLM_BASE_URL: override base URL for 'free'
          - LLM_PAYLOAD_STYLE: 'message' | 'messages' (default: 'message', only for 'free')
          - GEMINI_API_KEY: required when LLM_PROVIDER=gemini
          - GEMINI_MODEL: model name (default: 'gemini-1.5-flash')
        """
        self.provider = (os.getenv("LLM_PROVIDER", "free") or "free").lower()
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://apifreellm.com/api/chat")
        self.timeout = timeout
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.headers = {"Content-Type": "application/json"}  # add auth header here if needed
        self.payload_style = os.getenv("LLM_PAYLOAD_STYLE", "message").lower().strip() or "message"
        # Gemini config
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        # FORCE gemini-flash-latest as default (standard name) and override any accidental 2.0 settings which are causing rate limits
        model_env = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        if "2.0" in str(model_env) or "1.5-flash" == model_env:
            model_env = "gemini-flash-latest"
        self.gemini_model = model_env
        print(f"DEBUG: LLMClient initialized with model: {self.gemini_model}")
        # OpenRouter config
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Send a chat completion request.
        - Provider 'free':
            When payload_style == 'message':  { "message": "<system+prompt or prompt>" }
            When payload_style == 'messages': { "messages": [{role, content}, ...] }
        - Provider 'gemini':
            POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=API_KEY
            Body: { "contents":[{"role":"user","parts":[{"text":"..."}]}], "systemInstruction": {"parts":[{"text":"..."}]}? }
        """
        if self.provider == "gemini":
            return self._complete_gemini(prompt, system)
        if self.provider == "openrouter":
            return self._complete_openrouter(prompt, system)

        # Build payload
        system_text = (system or "").strip()
        if self.payload_style == "messages":
            messages: List[Dict[str, str]] = []
            if system_text:
                messages.append({"role": "system", "content": system_text})
            messages.append({"role": "user", "content": prompt})
            data: Dict[str, Any] = {"messages": messages}
        else:
            # Default: single message
            msg = f"{system_text}\n\n{prompt}" if system_text else prompt
            data = {"message": msg}

        last_err = None
        for attempt in range(self.retries + 1):
            try:
                resp = requests.post(self.base_url, headers=self.headers, json=data, timeout=self.timeout)
                break
            except requests.RequestException as e:
                last_err = e
                if attempt < self.retries:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                raise RuntimeError(f"LLM request failed: {e}") from e

        # Basic HTTP error surface
        if not (200 <= resp.status_code < 300):
            snippet = (resp.text or "")[:300]
            raise RuntimeError(f"LLM HTTP {resp.status_code}: {snippet}")

        try:
            js = resp.json()
        except ValueError:
            raise RuntimeError(f"Non-JSON response from LLM: {resp.text[:300]}")

        # Normalize success detection across common shapes
        # apifreellm typical: { status: "success", response: "..." }
        if js.get("status") == "success":
            if "response" in js and isinstance(js["response"], str):
                return js["response"]
            if "message" in js and isinstance(js["message"], str):
                return js["message"]
            if "output" in js and isinstance(js["output"], str):
                return js["output"]
            # Some providers echo the text at top level
            if "text" in js and isinstance(js["text"], str):
                return js["text"]

        # OpenAI-like: { choices: [{ message: { content } }] }
        choices = js.get("choices")
        if isinstance(choices, list) and choices:
            choice0 = choices[0] or {}
            msg = (choice0.get("message") or {})
            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                return msg["content"]
            if isinstance(choice0.get("text"), str):
                return choice0["text"]

        # Cohere/others: { answer: "..."} or { data: { answer: "..." } }
        for key in ("answer", "response", "message", "output", "text"):
            if isinstance(js.get(key), str):
                return js[key]
        data_block = js.get("data") or {}
        for key in ("answer", "response", "message", "output", "text"):
            if isinstance(data_block.get(key), str):
                return data_block[key]

        # Surface error details for easier debugging
        raise RuntimeError(f"LLM error: status={js.get('status')} error={js.get('error') or js}")

    def _complete_gemini(self, prompt: str, system: Optional[str]) -> str:
        """
        Google Gemini (Generative Language API) text generation via REST.
        """
        if not self.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set. Please export GEMINI_API_KEY or set LLM_PROVIDER=free.")

        # Endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"

        # Build body
        system_text = (system or "").strip()
        body: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ]
        }
        if system_text:
            # Prefer systemInstruction if available in v1beta; otherwise prepend to prompt
            body["systemInstruction"] = {
                "parts": [{"text": system_text}]
            }

        last_err = None
        for attempt in range(self.retries + 1):
            try:
                resp = requests.post(url, headers={"Content-Type": "application/json"}, json=body, timeout=self.timeout)
                break
            except requests.RequestException as e:
                last_err = e
                if attempt < self.retries:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                raise RuntimeError(f"Gemini request failed: {e}") from e

        if not (200 <= resp.status_code < 300):
            snippet = (resp.text or "")[:500]
            raise RuntimeError(f"Gemini HTTP {resp.status_code}: {snippet}")

        try:
            js = resp.json()
        except ValueError:
            raise RuntimeError(f"Non-JSON response from Gemini: {resp.text[:300]}")

        # Parse Gemini response
        # Expected: { "candidates":[ { "content": { "parts":[{"text":"..."}] } } ] }
        candidates = js.get("candidates") or []
        if isinstance(candidates, list) and candidates:
            content = candidates[0].get("content") or {}
            parts = content.get("parts") or []
            if isinstance(parts, list) and parts:
                text = parts[0].get("text")
                if isinstance(text, str):
                    return text
        # Alternative structure
        if isinstance(js.get("text"), str):
            return js["text"]
        raise RuntimeError(f"Gemini error: {js}")

    def _complete_openrouter(self, prompt: str, system: Optional[str]) -> str:
        """
        OpenRouter (OpenAI-compatible) text generation.
        """
        if not self.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set. Please export OPENROUTER_API_KEY.")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "HTTP-Referer": "https://copenny.ai", # Optional
            "X-Title": "Co Penny", # Optional
            "Content-Type": "application/json"
        }

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self.openrouter_model,
            "messages": messages
        }

        last_err = None
        for attempt in range(self.retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=self.timeout)
                break
            except requests.RequestException as e:
                last_err = e
                if attempt < self.retries:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                raise RuntimeError(f"OpenRouter request failed: {e}") from e

        if not (200 <= resp.status_code < 300):
            snippet = (resp.text or "")[:500]
            raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {snippet}")

        try:
            js = resp.json()
        except ValueError:
            raise RuntimeError(f"Non-JSON response from OpenRouter: {resp.text[:300]}")

        choices = js.get("choices") or []
        if choices:
            content = choices[0].get("message", {}).get("content")
            if content:
                return content
        
        raise RuntimeError(f"OpenRouter error: {js}")

