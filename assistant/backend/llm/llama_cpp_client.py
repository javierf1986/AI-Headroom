from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from backend.core.text_encoding import normalize_text_encoding

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LLMReply:
    text: str
    tool_calls: list[dict[str, Any]]
    stop_reason: str


class LlamaCppClient:
    """Client for llama.cpp HTTP server (OpenAI-compatible API) or Ollama."""

    def __init__(self, base_url: str = "http://localhost:8000/v1", timeout: float = 120, preferred_model_keyword: str = "mistral") -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.preferred_model_keyword = preferred_model_keyword.strip().lower()
        # Configure httpx client with explicit UTF-8 encoding
        self._client = httpx.Client(
            timeout=timeout,
            headers={"Accept": "application/json; charset=utf-8"},
        )
        self._available = False
        self._model_name = None
        self._check_availability()

    def _check_availability(self) -> None:
        try:
            logger.info(f"Checking LLM availability at {self.base_url}/models...")
            resp = self._client.get(f"{self.base_url}/models", timeout=5)
            logger.info(f"LLM check response: status={resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"LLM response data: {data}")
                # Prefer configured model keyword, fallback to first available
                if "data" in data and len(data["data"]) > 0:
                    models = [m.get("id", "") for m in data["data"]]
                    preferred_model = None
                    if self.preferred_model_keyword:
                        preferred_model = next(
                            (m for m in models if self.preferred_model_keyword in m.lower()),
                            None,
                        )
                    self._model_name = preferred_model if preferred_model else models[0]
                    self._available = True
                    logger.info(f"✓ LLM server available at {self.base_url}, using model: {self._model_name}")
                    return
                else:
                    logger.warning(f"LLM response has no models: {data}")
            else:
                logger.warning(f"LLM server returned status {resp.status_code}")
        except Exception as e:
            logger.warning(f"✗ LLM server not available at {self.base_url}: {type(e).__name__}: {e}")
            import traceback
            logger.warning(f"Traceback: {traceback.format_exc()}")
        
        self._available = False
        logger.warning(f"Using fallback mock LLM (real LLM not available)")

    @property
    def available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        session_messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        persona: str | None = None,
        response_language: str | None = None,
    ) -> LLMReply:
        """Generate LLM response with optional tool calling and persona."""
        if not self.available:
            raise RuntimeError("LLM server is not available. Start server or use mock mode.")

        normalized_messages: list[dict[str, Any]] = []
        
        # Inject persona as system message if provided
        if persona and persona.strip():
            normalized_messages.append({
                "role": "system",
                "content": normalize_text_encoding(persona.strip())
            })
            logger.info(f"[LLM] Injecting persona: {persona[:80]}...")

        if response_language and response_language.lower().startswith("es"):
            normalized_messages.append(
                {
                    "role": "system",
                    "content": "Responde siempre en español neutro. No cambies al inglés a menos que el usuario lo pida explícitamente.",
                }
            )
        elif response_language and response_language.lower().startswith("en"):
            normalized_messages.append(
                {
                    "role": "system",
                    "content": "Respond in English unless the user explicitly asks for another language.",
                }
            )
        
        for msg in session_messages:
            content = msg.get("content")
            if isinstance(content, str):
                normalized_messages.append({**msg, "content": normalize_text_encoding(content)})
            else:
                normalized_messages.append(msg)

        normalized_prompt = normalize_text_encoding(prompt)
        messages = normalized_messages + [{"role": "user", "content": normalized_prompt}]

        # Ollama doesn't support tools parameter, so only include it if backend explicitly supports it
        payload = {
            "model": self._model_name or "local-model",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        # Don't include tools - Ollama doesn't support function calling yet

        try:
            logger.debug(f"Sending request to {self.base_url}/chat/completions with model {self._model_name}")
            resp = self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json; charset=utf-8",
                },
            )
            resp.raise_for_status()
            
            # Force UTF-8 decoding by reinterpreting the raw bytes
            if resp.content:
                try:
                    # Decode the raw response bytes as UTF-8 explicitly
                    text_content = resp.content.decode('utf-8')
                    data = json.loads(text_content)
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    logger.warning(f"UTF-8 decode failed, trying with latin-1: {e}")
                    # Fallback to resp.json() which uses httpx's auto-detection
                    data = resp.json()
            else:
                data = resp.json()

            text = ""
            tool_calls = []

            # Extract text response
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice:
                    msg = choice["message"]
                    if "content" in msg and msg["content"]:
                        text = normalize_text_encoding(msg["content"])
                        logger.info(f"[LLMClientAdapter] LLM text response (first 100 chars): {repr(text[:100])}")

                    # Extract tool calls if present
                    if "tool_calls" in msg:
                        tool_calls = [
                            {
                                "tool_id": tc.get("function", {}).get("name", ""),
                                "input_data": json.loads(tc.get("function", {}).get("arguments", "{}")),
                            }
                            for tc in msg.get("tool_calls", [])
                        ]

                stop_reason = choice.get("finish_reason", "stop")
                return LLMReply(text=text, tool_calls=tool_calls, stop_reason=stop_reason)

            return LLMReply(text="No response from LLM.", tool_calls=[], stop_reason="error")

        except httpx.HTTPError as e:
            logger.error(f"LLM request failed: {e}")
            raise RuntimeError(f"LLM generation failed: {e}") from e

    def finalize(
        self,
        original_prompt: str,
        tool_results: list[dict[str, Any]],
        persona: str | None = None,
        response_language: str | None = None,
    ) -> str:
        """Generate a final response based on tool results."""
        if not tool_results:
            return f"Response to: {original_prompt}"

        results_text = "\n".join([f"- {r['tool_id']}: {json.dumps(r['result'])}" for r in tool_results])
        finalize_prompt = f"Based on these tool results:\n{results_text}\n\nProvide a concise response to the user's original request: {original_prompt}"

        repl = self.generate(
            prompt=finalize_prompt,
            session_messages=[],
            persona=persona,
            response_language=response_language,
        )
        return repl.text


class FallbackLLMClient:
    """Mock LLM client for when llama.cpp is not available."""

    def generate(
        self,
        prompt: str,
        session_messages: list[dict[str, Any]],
        persona: str | None = None,
        response_language: str | None = None,
    ) -> LLMReply:
        if response_language and response_language.lower().startswith("es"):
            return LLMReply(text=f"Entiendo tu mensaje: {prompt}", tool_calls=[], stop_reason="stop")

        lower = prompt.lower()
        if "time" in lower or "date" in lower:
            return LLMReply(
                text="I will check the current UTC time.",
                tool_calls=[{"tool_id": "datetime.now", "input_data": {}}],
                stop_reason="tool_call",
            )
        if lower.startswith("echo "):
            return LLMReply(
                text="I will echo that.",
                tool_calls=[{"tool_id": "echo", "input_data": {"message": prompt[5:]}}],
                stop_reason="tool_call",
            )
        return LLMReply(text=f"Mock response: {prompt}", tool_calls=[], stop_reason="stop")

    def finalize(
        self,
        original_prompt: str,
        tool_results: list[dict[str, Any]],
        persona: str | None = None,
        response_language: str | None = None,
    ) -> str:
        """Generate a mock response based on tool results or the original prompt."""
        if not tool_results:
            if response_language and response_language.lower().startswith("es"):
                return f"Entiendo que dijiste '{original_prompt}'. Para mejores respuestas, asegúrate de tener un modelo local activo."

            # Generate a context-aware mock response
            responses = {
                "hello": "Hello! I'm a local AI assistant. How can I help you today?",
                "hi": "Hi there! What would you like to know?",
                "how are you": "I'm doing well, thank you for asking! How can I assist you?",
                "what is your name": "I'm an AI Assistant running locally on your machine.",
                "name": "I'm a local AI Assistant. You can give me any name you'd like!",
                "buenas": "¡Hola! Soy un asistente de IA local. ¿Cómo puedo ayudarte?",
            }
            
            prompt_lower = original_prompt.lower().strip()
            for key, response in responses.items():
                if key in prompt_lower:
                    return response
            
            # Default response with acknowledgment
            return f"I understand you said '{original_prompt}'. Unfortunately, I need a real LLM server to provide a meaningful response. Please install Ollama or LM Studio to get full AI capabilities."
        
        # If we have tool results, provide a response based on them
        result_text = []
        for result in tool_results:
            if "error" in result:
                result_text.append(f"I encountered an error: {result['error']}")
            elif result["tool_id"] == "datetime.now":
                utc_time = result["result"].get("utc", "unknown time")
                return f"The current UTC time is: {utc_time}"
            elif result["tool_id"] == "echo":
                msg = result["result"].get("message", "")
                return f"You said: {msg}"
        
        if result_text:
            return " ".join(result_text)
        
        return "I processed your request. To get a real response, please set up a local LLM server."


class LLMClientAdapter:
    """Adapter that tries real llama.cpp server, falls back to mock."""

    def __init__(self, llama_cpp_url: str = "http://localhost:8000/v1", preferred_model_keyword: str = "mistral") -> None:
        self._primary = LlamaCppClient(
            base_url=llama_cpp_url,
            preferred_model_keyword=preferred_model_keyword,
        )
        self._fallback = FallbackLLMClient()

    def generate(
        self,
        prompt: str,
        session_messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        persona: str | None = None,
        response_language: str | None = None,
    ) -> LLMReply:
        logger.info(f"[LLMClientAdapter.generate] Primary available: {self._primary.available}, prompt: {prompt[:50]}")
        if self._primary.available:
            try:
                logger.info(f"[LLMClientAdapter] Calling primary LLM...")
                result = self._primary.generate(
                    prompt=prompt,
                    session_messages=session_messages,
                    tools=tools,
                    persona=persona,
                    response_language=response_language,
                )
                logger.info(f"[LLMClientAdapter] Primary LLM returned: {result.text[:100]}")
                return result
            except Exception as e:
                logger.error(f"[LLMClientAdapter] Primary LLM failed: {type(e).__name__}: {e}", exc_info=True)
        
        logger.warning(f"[LLMClientAdapter] Using fallback mock LLM")
        return self._fallback.generate(
            prompt=prompt,
            session_messages=session_messages,
            persona=persona,
            response_language=response_language,
        )

    def finalize(
        self,
        original_prompt: str,
        tool_results: list[dict[str, Any]],
        persona: str | None = None,
        response_language: str | None = None,
    ) -> str:
        logger.info(f"[LLMClientAdapter.finalize] Primary available: {self._primary.available}")
        if self._primary.available:
            try:
                logger.info(f"[LLMClientAdapter] Calling primary finalize...")
                result = self._primary.finalize(
                    original_prompt=original_prompt,
                    tool_results=tool_results,
                    persona=persona,
                    response_language=response_language,
                )
                logger.info(f"[LLMClientAdapter] Primary finalize returned: {result[:100]}")
                return result
            except Exception as e:
                logger.error(f"[LLMClientAdapter] Primary finalize failed: {type(e).__name__}: {e}", exc_info=True)
        
        logger.warning(f"[LLMClientAdapter] Using fallback finalize")
        return self._fallback.finalize(
            original_prompt=original_prompt,
            tool_results=tool_results,
            persona=persona,
            response_language=response_language,
        )
