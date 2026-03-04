from __future__ import annotations

import json
import logging
import os
import re
import inspect
import sys
from asyncio import Queue
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from backend.audio.tts_worker import TTSWorker
from backend.avatar.service import AvatarService
from backend.avatar.sprite_metadata import SpriteLibrary, SpriteMetadata
from backend.core.event_bus import EventBus
from backend.core.orchestrator import Orchestrator
from backend.core.permissions import PermissionManager
from backend.core.repositories.preferences_repo import PreferencesRepository
from backend.core.schemas import ChatRequest
from backend.core.settings import settings
from backend.core.session_store import SessionStore
from backend.core.text_encoding import normalize_text_encoding
from backend.llm.llama_cpp_client import LLMClientAdapter
from backend.tools.mock_datetime_tool import DateTimeTool
from backend.tools.mock_echo_tool import EchoTool
from backend.tools.registry import ToolRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _read_png_dimensions(contents: bytes) -> tuple[int, int]:
    signature = b"\x89PNG\r\n\x1a\n"
    if len(contents) < 24 or not contents.startswith(signature):
        raise ValueError("Uploaded file is not a valid PNG")
    if contents[12:16] != b"IHDR":
        raise ValueError("PNG missing IHDR header")

    width = int.from_bytes(contents[16:20], "big")
    height = int.from_bytes(contents[20:24], "big")
    return width, height


def _build_viseme_map(total_frames: int) -> dict[str, int]:
    last_index = max(0, total_frames - 1)
    return {
        "A": min(2, last_index),
        "E": min(3, last_index),
        "I": min(4, last_index),
        "O": min(5, last_index),
        "U": min(6, last_index),
        "neutral": 0,
        "closed": min(1, last_index),
        "silence": 0,
    }


def _build_idle_frames(total_frames: int) -> list[int]:
    count = max(1, min(3, total_frames))
    return list(range(count))


def _build_blink_frames(total_frames: int) -> list[int]:
    if total_frames < 2:
        return []
    return [max(0, total_frames - 2), total_frames - 1]


def _normalize_sprite_grid(
    image_width: int,
    image_height: int,
    frame_width: int,
    frame_height: int,
    frames_per_row: int,
    total_frames: int,
) -> tuple[int, int]:
    max_cols = max(1, image_width // frame_width)
    max_rows = max(1, image_height // frame_height)
    max_frames = max_cols * max_rows

    normalized_frames_per_row = min(max(1, frames_per_row), max_cols)
    normalized_total_frames = min(max(1, total_frames), max_frames)
    return normalized_frames_per_row, normalized_total_frames


def _load_persisted_sprites(sprite_library: SpriteLibrary, sprites_dir: Path) -> None:
    if not sprites_dir.exists():
        return

    for metadata_file in sprites_dir.glob("*.json"):
        try:
            payload = json.loads(metadata_file.read_text(encoding="utf-8"))
            sprite = SpriteMetadata(
                name=payload["name"],
                display_name=payload["display_name"],
                image_path=payload["image_path"],
                frame_width=int(payload["frame_width"]),
                frame_height=int(payload["frame_height"]),
                frames_per_row=int(payload["frames_per_row"]),
                total_frames=int(payload["total_frames"]),
                viseme_map=payload.get("viseme_map") or _build_viseme_map(int(payload["total_frames"])),
                blink_frames=payload.get("blink_frames") or _build_blink_frames(int(payload["total_frames"])),
                idle_frames=payload.get("idle_frames") or _build_idle_frames(int(payload["total_frames"])),
                error_frame=int(payload.get("error_frame", 0)),
                frame_duration_ms=int(payload.get("frame_duration_ms", 100)),
                persona=payload.get("persona") or None,
                glitch_enabled=bool(payload.get("glitch_enabled", False)),
                glitch_intensity=float(payload.get("glitch_intensity", 0.5)),
                glitch_effects=payload.get("glitch_effects") or [],
                preferred_voice_en=payload.get("preferred_voice_en", "en-US-AriaNeural"),
                preferred_voice_es=payload.get("preferred_voice_es", "es-MX-DaliaNeural"),
            )
            sprite_library.register_sprite(sprite)
            logger.info("Loaded persisted sprite metadata: %s", sprite.name)
        except Exception as exc:
            logger.warning("Failed to load sprite metadata from %s: %s", metadata_file, exc)

    for png_file in sprites_dir.glob("*.png"):
        stem = png_file.stem
        if stem == "retro-character-v1":
            continue
        if (sprites_dir / f"{stem}.json").exists():
            continue

        try:
            contents = png_file.read_bytes()
            image_width, image_height = _read_png_dimensions(contents)
            total_frames = 1
            payload = {
                "name": stem,
                "display_name": stem.replace("-", " ").title(),
                "image_path": f"/artifacts/sprites/{stem}.png",
                "frame_width": image_width,
                "frame_height": image_height,
                "frames_per_row": 1,
                "total_frames": total_frames,
                "viseme_map": _build_viseme_map(total_frames),
                "blink_frames": _build_blink_frames(total_frames),
                "idle_frames": _build_idle_frames(total_frames),
                "error_frame": 0,
                "frame_duration_ms": 100,
                "persona": None,
                "preferred_voice_en": "en-US-AriaNeural",
                "preferred_voice_es": "es-MX-DaliaNeural",
            }

            metadata_file = sprites_dir / f"{stem}.json"
            metadata_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            sprite_library.register_sprite(SpriteMetadata(**payload))
            logger.info("Recovered legacy sprite without metadata: %s", stem)
        except Exception as exc:
            logger.warning("Failed to recover legacy sprite %s: %s", png_file, exc)


def create_app() -> FastAPI:
    app = FastAPI(title="Local AI Assistant Backend")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    event_bus = EventBus()
    session_store = SessionStore()
    permission_manager = PermissionManager()
    ollama_url = settings.ollama_api_url
    llm_client = LLMClientAdapter(
        llama_cpp_url=ollama_url,
        preferred_model_keyword=settings.preferred_model_keyword,
    )
    tts_worker = TTSWorker(
        piper_models_dir="./piper/models",
        artifact_dir=settings.artifact_dir,
    )
    
    sprite_library = SpriteLibrary()
    sprites_dir = Path(settings.artifact_dir).resolve().parent / "sprites"
    _load_persisted_sprites(sprite_library, sprites_dir)
    avatar_service = AvatarService(sprite_library)
    preferences_repo = PreferencesRepository()

    tool_registry = ToolRegistry(permission_manager=permission_manager)
    tool_registry.register(EchoTool())
    tool_registry.register(DateTimeTool())

    orchestrator = Orchestrator(
        event_bus=event_bus,
        session_store=session_store,
        llm_client=llm_client,
        tool_registry=tool_registry,
        tts_worker=tts_worker,
        avatar_service=avatar_service,
        sprite_library=sprite_library,
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/debug/runtime")
    def debug_runtime() -> dict:
        orchestrator_src = inspect.getsource(orchestrator.__class__.process_text)
        tts_synthesize_src = inspect.getsource(tts_worker.__class__.synthesize)

        return {
            "status": "ok",
            "python_executable": sys.executable,
            "cwd": os.getcwd(),
            "artifact_dir": settings.artifact_dir,
            "orchestrator_module": inspect.getsourcefile(orchestrator.__class__),
            "tts_worker_module": inspect.getsourcefile(tts_worker.__class__),
            "orchestrator_has_audio_debug": '"debug": tts_result.debug' in orchestrator_src,
            "tts_worker_has_debug_payload": "debug_info" in tts_synthesize_src,
        }

    @app.get("/tools")
    def list_tools() -> dict:
        return {"tools": tool_registry.list_tools()}

    @app.get("/config/voices")
    def list_voices() -> dict:
        return {
            "provider": settings.tts_provider,
            "voices": tts_worker.list_voices(),
        }

    @app.get("/tts/demo")
    async def tts_voice_demo(voice_id: str) -> Response:
        """Synthesize a short preview sample for the given voice ID and return as MP3."""
        try:
            audio_bytes, _ = tts_worker.synthesize_demo(voice_id)
            return Response(content=audio_bytes, media_type="audio/mpeg")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Voice preview failed: {exc}") from exc

    @app.get("/config/preferences")
    def get_preferences(client_id: str = settings.default_client_id) -> dict:
        prefs = preferences_repo.get(client_id)
        return {"preferences": PreferencesRepository.to_dict(prefs)}

    @app.put("/config/preferences")
    async def update_preferences(raw_request: Request) -> dict:
        try:
            payload = await raw_request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Body must be valid JSON") from exc

        client_id = payload.get("client_id") or settings.default_client_id
        updates = {
            key: payload.get(key)
            for key in ("default_avatar", "preferred_voice_en", "preferred_voice_es")
            if key in payload
        }
        prefs = preferences_repo.update(client_id=client_id, updates=updates)
        return {"preferences": PreferencesRepository.to_dict(prefs)}

    @app.post("/chat")
    async def chat(raw_request: Request) -> Response:
        try:
            raw_body = await raw_request.body()
            decoded_body = raw_body.decode("utf-8")
            payload = json.loads(decoded_body)
            request = ChatRequest(**payload)
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="Request body must be UTF-8 encoded JSON") from exc
        except (json.JSONDecodeError, TypeError) as exc:
            raise HTTPException(status_code=400, detail="There was an error parsing the body") from exc

        request.text = normalize_text_encoding(request.text)
        request.language = normalize_text_encoding(request.language or "en")
        if request.preferred_voice_id:
            request.preferred_voice_id = normalize_text_encoding(request.preferred_voice_id)
        if request.preferred_sprite:
            request.preferred_sprite = normalize_text_encoding(request.preferred_sprite)

        resolved_client_id = normalize_text_encoding(request.client_id or request.session_id or settings.default_client_id)
        request.client_id = resolved_client_id

        preferences = preferences_repo.get(resolved_client_id)
        if not request.preferred_sprite and preferences.default_avatar:
            request.preferred_sprite = preferences.default_avatar

        try:
            response = orchestrator.process_text(request)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        payload = {
            "session_id": response.session_id,
            "text": normalize_text_encoding(response.text),
            "tool_results": response.tool_results,
            "audio": response.audio,
            "avatar": response.avatar,
        }

        if isinstance(payload.get("audio"), dict):
            audio_payload = payload["audio"]
            if "debug" not in audio_payload:
                audio_payload["debug"] = {
                    "runtime_missing_debug_payload": True,
                }
        return Response(
            content=json.dumps(payload, ensure_ascii=False),
            media_type="application/json; charset=utf-8",
        )

    @app.websocket("/ws/events")
    async def websocket_events(websocket: WebSocket) -> None:
        await websocket.accept()
        
        def event_callback(event):
            try:
                payload = json.dumps(
                    {
                        "name": event.name,
                        "timestamp": event.timestamp.isoformat(),
                        "payload": event.payload,
                    }
                )
                # Note: This is sync-in-async; in production, use proper async event bus
                import asyncio
                asyncio.create_task(websocket.send_text(payload))
            except Exception as e:
                logger.error(f"Failed to send event: {e}")

        for event_name in [
            "tool_invocation_requested",
            "tool_invocation_completed",
            "assistant_response_text",
            "assistant_audio_ready",
            "avatar_speak_start",
            "avatar_speak_end",
        ]:
            event_bus.subscribe(event_name, event_callback)

        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            logger.info("Client disconnected")

    @app.get("/audit")
    def audit() -> dict:
        return {
            "entries": [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "actor": entry.actor,
                    "action": entry.action,
                    "permitted": entry.permitted,
                    "reason": entry.reason,
                    "metadata": entry.metadata,
                }
                for entry in permission_manager.audit_log
            ]
        }

    @app.get("/events")
    def events() -> dict:
        return {
            "events": [
                {
                    "name": event.name,
                    "timestamp": event.timestamp.isoformat(),
                    "payload": event.payload,
                }
                for event in event_bus.history
            ]
        }

    @app.get("/avatar/sprites")
    def list_avatar_sprites() -> dict:
        return {"sprites": avatar_service.list_sprites()}

    @app.post("/avatar/sprite/{sprite_name}")
    def set_avatar_sprite(sprite_name: str) -> dict:
        try:
            avatar_service.set_active_sprite(sprite_name)
            # Return animation payload with idle frame so avatar displays immediately
            animation = avatar_service.create_idle_animation(sprite_name)
            return {"avatar": animation}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete("/avatar/sprite/{sprite_name}")
    def delete_avatar_sprite(sprite_name: str) -> dict:
        try:
            sprite_library.unregister_sprite(sprite_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        sprites_dir = Path(settings.artifact_dir).resolve().parent / "sprites"
        for ext in (".png", ".json"):
            candidate = sprites_dir / f"{sprite_name}{ext}"
            if candidate.exists():
                candidate.unlink()

        return {"status": "deleted", "sprite": sprite_name}

    @app.put("/avatar/sprite/{sprite_name}")
    async def update_avatar_sprite(sprite_name: str, request: Request) -> dict:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

        allowed = {"display_name", "frame_width", "frame_height", "frames_per_row", "total_frames", "persona", "glitch_enabled", "glitch_intensity", "glitch_effects", "preferred_voice_en", "preferred_voice_es"}
        updates = {k: v for k, v in body.items() if k in allowed}
        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Rebuild animation metadata when grid changes
        total = int(updates.get("total_frames", None) or sprite_library.get_sprite(sprite_name).total_frames)
        updates["viseme_map"] = _build_viseme_map(total)
        updates["idle_frames"] = _build_idle_frames(total)
        updates["blink_frames"] = _build_blink_frames(total)

        try:
            updated = sprite_library.update_sprite(sprite_name, updates)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        # Persist back to JSON
        sprites_dir = Path(settings.artifact_dir).resolve().parent / "sprites"
        metadata_file = sprites_dir / f"{sprite_name}.json"
        if metadata_file.exists():
            payload = json.loads(metadata_file.read_text(encoding="utf-8"))
            payload.update({k: getattr(updated, k) for k in allowed if hasattr(updated, k)})
            payload["viseme_map"] = updated.viseme_map
            payload["idle_frames"] = updated.idle_frames
            payload["blink_frames"] = updated.blink_frames
            if updated.persona:
                payload["persona"] = updated.persona
            elif "persona" in payload:
                del payload["persona"]
            # Update glitch settings
            payload["glitch_enabled"] = updated.glitch_enabled
            payload["glitch_intensity"] = updated.glitch_intensity
            payload["glitch_effects"] = updated.glitch_effects or []
            # Update voice preferences
            payload["preferred_voice_en"] = updated.preferred_voice_en
            payload["preferred_voice_es"] = updated.preferred_voice_es
            metadata_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "status": "updated",
            "sprite": {
                "name": updated.name,
                "display_name": updated.display_name,
                "frame_width": updated.frame_width,
                "frame_height": updated.frame_height,
                "frames_per_row": updated.frames_per_row,
                "total_frames": updated.total_frames,
            },
        }

    @app.post("/avatar/upload")
    async def upload_avatar_sprite(
        sprite_name: str = Form(...),
        display_name: str = Form(...),
        file: UploadFile = File(...),
        frame_width: int = Form(64),
        frame_height: int = Form(64),
        frames_per_row: int = Form(4),
        total_frames: int = Form(16),
        persona: str | None = Form(None),
        glitch_enabled: bool = Form(False),
        glitch_intensity: float = Form(0.5),
        glitch_effects: list[str] | None = Form(None),
    ) -> dict:
        if not file.filename or not file.filename.lower().endswith(".png"):
            raise HTTPException(status_code=400, detail="Sprite file must be a PNG")

        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "-", sprite_name).strip("-").lower()
        if not safe_name:
            raise HTTPException(status_code=400, detail="Invalid sprite name")

        sprites_dir = Path(settings.artifact_dir).resolve().parent / "sprites"
        sprites_dir.mkdir(parents=True, exist_ok=True)

        target_file = sprites_dir / f"{safe_name}.png"
        contents = await file.read()
        image_width, image_height = _read_png_dimensions(contents)

        if frames_per_row == 1 and total_frames == 1:
            frame_width = image_width
            frame_height = image_height

        if frame_width <= 0 or frame_height <= 0:
            raise HTTPException(status_code=400, detail="Frame width/height must be positive integers")

        if frame_width > image_width or frame_height > image_height:
            raise HTTPException(
                status_code=400,
                detail=f"Frame size {frame_width}x{frame_height} exceeds image size {image_width}x{image_height}",
            )

        normalized_frames_per_row, normalized_total_frames = _normalize_sprite_grid(
            image_width=image_width,
            image_height=image_height,
            frame_width=frame_width,
            frame_height=frame_height,
            frames_per_row=frames_per_row,
            total_frames=total_frames,
        )

        viseme_map = _build_viseme_map(normalized_total_frames)
        blink_frames = _build_blink_frames(normalized_total_frames)
        idle_frames = _build_idle_frames(normalized_total_frames)

        normalized_persona = normalize_text_encoding(persona.strip()) if persona and persona.strip() else None
        normalized_glitch_intensity = max(0.0, min(1.0, glitch_intensity))
        allowed_glitch_effects = {"stutter", "pitch", "static", "volume"}
        normalized_glitch_effects = [
            effect for effect in (glitch_effects or []) if effect in allowed_glitch_effects
        ]

        target_file.write_bytes(contents)

        metadata_payload = {
            "name": safe_name,
            "display_name": display_name,
            "image_path": f"/artifacts/sprites/{safe_name}.png",
            "frame_width": frame_width,
            "frame_height": frame_height,
            "frames_per_row": normalized_frames_per_row,
            "total_frames": normalized_total_frames,
            "viseme_map": viseme_map,
            "blink_frames": blink_frames,
            "idle_frames": idle_frames,
            "error_frame": 0,
            "frame_duration_ms": 100,
            "persona": normalized_persona,
            "glitch_enabled": glitch_enabled,
            "glitch_intensity": normalized_glitch_intensity,
            "glitch_effects": normalized_glitch_effects,
            "preferred_voice_en": "en-US-AriaNeural",
            "preferred_voice_es": "es-MX-DaliaNeural",
        }

        metadata_file = sprites_dir / f"{safe_name}.json"
        metadata_file.write_text(json.dumps(metadata_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        sprite_library.register_sprite(SpriteMetadata(**metadata_payload))

        return {
            "status": "ok",
            "sprite": safe_name,
            "display_name": display_name,
            "image_path": f"/artifacts/sprites/{safe_name}.png",
            "frame_width": frame_width,
            "frame_height": frame_height,
            "frames_per_row": normalized_frames_per_row,
            "total_frames": normalized_total_frames,
            "image_width": image_width,
            "image_height": image_height,
            "persona": normalized_persona,
            "glitch_enabled": glitch_enabled,
            "glitch_intensity": normalized_glitch_intensity,
            "glitch_effects": normalized_glitch_effects,
        }

    # Mount static file directories for artifacts
    artifact_root = Path(settings.artifact_dir).resolve().parent
    if artifact_root.exists():
        app.mount("/artifacts", StaticFiles(directory=str(artifact_root)), name="artifacts")

    return app


app = create_app()
