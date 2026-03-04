from __future__ import annotations

import logging
from typing import Any

from backend.audio.tts_worker import TTSWorker
from backend.avatar.service import AvatarService
from backend.avatar.sprite_metadata import SpriteLibrary
from backend.core.event_bus import EventBus
from backend.core.schemas import ChatRequest, ChatResponse
from backend.core.session_store import SessionStore
from backend.llm.llama_cpp_client import LLMClientAdapter
from backend.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        event_bus: EventBus,
        session_store: SessionStore,
        llm_client: LLMClientAdapter,
        tool_registry: ToolRegistry,
        tts_worker: TTSWorker,
        avatar_service: AvatarService,
        sprite_library: SpriteLibrary,
    ) -> None:
        self._event_bus = event_bus
        self._session_store = session_store
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._tts_worker = tts_worker
        self._avatar_service = avatar_service
        self._sprite_library = sprite_library

    def process_text(self, request: ChatRequest) -> ChatResponse:
        logger.info(f"[ORCHESTRATOR] Received request with language='{request.language}'")
        self._session_store.append(request.session_id, "user", request.text)

        # Extract persona from active sprite (if available)
        persona = None
        if request.preferred_sprite:
            try:
                sprite = self._sprite_library.get_sprite(request.preferred_sprite)
                persona = sprite.persona
                if persona:
                    logger.info(f"[ORCHESTRATOR] Using persona from sprite '{request.preferred_sprite}': {persona[:80]}...")
            except ValueError:
                logger.warning(f"[ORCHESTRATOR] Sprite '{request.preferred_sprite}' not found, no persona applied")

        tools = self._tool_registry.list_tools()
        tool_schemas = [t["schema"] for t in tools]

        llm_reply = self._llm_client.generate(
            prompt=request.text,
            session_messages=self._session_store.get(request.session_id),
            tools=tool_schemas,
            persona=persona,
            response_language=request.language,
        )

        tool_results: list[dict] = []
        for call in llm_reply.tool_calls:
            self._event_bus.publish("tool_invocation_requested", {"session_id": request.session_id, "tool": call["tool_id"]})
            try:
                result = self._tool_registry.run(
                    tool_id=call["tool_id"],
                    input_data=call["input_data"],
                    context={
                        "session_id": request.session_id,
                        "actor": request.actor,
                        "permissions": request.permissions,
                    },
                )
                tool_results.append({"tool_id": call["tool_id"], "result": result})
                self._event_bus.publish(
                    "tool_invocation_completed",
                    {"session_id": request.session_id, "tool": call["tool_id"], "result": result},
                )
            except (ValueError, PermissionError) as e:
                logger.error(f"Tool execution failed for {call['tool_id']}: {e}")
                tool_results.append({"tool_id": call["tool_id"], "error": str(e)})
                self._event_bus.publish(
                    "tool_invocation_completed",
                    {"session_id": request.session_id, "tool": call["tool_id"], "error": str(e)},
                )

        # Use original LLM response if no tools were called, otherwise finalize with tool results
        if tool_results:
            final_text = self._llm_client.finalize(
                request.text,
                tool_results=tool_results,
                persona=persona,
                response_language=request.language,
            )
        else:
            final_text = llm_reply.text
            logger.info(f"No tools called, using LLM response directly: {final_text[:100]}")
        
        self._session_store.append(request.session_id, "assistant", final_text)
        self._event_bus.publish("assistant_response_text", {"session_id": request.session_id, "text": final_text})

        # Extract glitch configuration from sprite
        sprite_glitch_config = None
        voice_id_override = request.preferred_voice_id  # Start with request override
        if request.preferred_sprite:
            try:
                sprite = self._sprite_library.get_sprite(request.preferred_sprite)
                if sprite.glitch_enabled:
                    sprite_glitch_config = {
                        "enabled": True,
                        "intensity": sprite.glitch_intensity,
                        "effects": sprite.glitch_effects or [],
                    }
                    logger.info(f"[ORCHESTRATOR] Glitch effects: {sprite_glitch_config['effects']} (intensity={sprite.glitch_intensity})")
                
                # Use sprite's voice preference if no explicit override provided
                if not voice_id_override:
                    if request.language == "es":
                        voice_id_override = sprite.preferred_voice_es
                        logger.info(f"[ORCHESTRATOR] Using sprite's Spanish voice: {voice_id_override}")
                    else:
                        voice_id_override = sprite.preferred_voice_en
                        logger.info(f"[ORCHESTRATOR] Using sprite's English voice: {voice_id_override}")
            except ValueError:
                logger.warning(f"[ORCHESTRATOR] Sprite '{request.preferred_sprite}' not found for glitch config")

        logger.info(f"[ORCHESTRATOR] Calling TTS with language='{request.language}'")
        tts_result = self._tts_worker.synthesize(
            final_text,
            language=request.language,
            voice_id_override=voice_id_override,
            sprite_glitch_config=sprite_glitch_config,
        )
        logger.info(f"[ORCHESTRATOR] TTS returned voice_id='{tts_result.voice_id}' for language='{tts_result.language}'")
        self._event_bus.publish(
            "assistant_audio_ready",
            {
                "session_id": request.session_id,
                "language": tts_result.language,
                "voice_id": tts_result.voice_id,
                "audio_path": tts_result.audio_path,
                "wav_path": tts_result.audio_path,
                "duration_seconds": tts_result.duration_seconds,
                "artifact_id": tts_result.artifact_id,
                "debug": tts_result.debug,
            },
        )

        avatar_payload = self._avatar_service.create_animation(
            response_text=final_text,
            audio_duration_seconds=tts_result.duration_seconds,
            language=request.language,
            sprite_name=request.preferred_sprite,
        )
        self._event_bus.publish("avatar_speak_start", {"session_id": request.session_id, "avatar": avatar_payload})
        self._event_bus.publish("avatar_speak_end", {"session_id": request.session_id})

        return ChatResponse(
            session_id=request.session_id,
            text=final_text,
            tool_results=tool_results,
            audio={
                "language": tts_result.language,
                "voice_id": tts_result.voice_id,
                "audio_path": tts_result.audio_path,
                "wav_path": tts_result.audio_path,
                "duration_seconds": tts_result.duration_seconds,
                "artifact_id": tts_result.artifact_id,
                "debug": tts_result.debug,
            },
            avatar=avatar_payload,
        )
