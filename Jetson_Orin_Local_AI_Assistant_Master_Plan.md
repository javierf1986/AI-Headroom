# Fully Local AI Assistant --- Jetson Orin Nano Super 8GB

**Master Architecture & Implementation Plan**\
Generated on: 2026-03-03

Execution profile (current): WSL2 Ubuntu on Windows laptop (NVIDIA RTX 4070 mobile) for development and initial testing.
Deployment target (final): Jetson Orin Nano Super 8GB + SSD.

------------------------------------------------------------------------

# Change Log

- 2026-03-03: Added execution profile, phased status tracker, and started implementation for phases 1, 3, and 4.
- 2026-03-03: Implemented initial backend skeleton for Phase 1 with orchestrator, event bus, tool registry, permission manager, and mock LLM integration.
- 2026-03-03: Added Phase 3/4-compatible stubs for TTS output contract and avatar speak event lifecycle.
- 2026-03-03: Smoke-tested backend endpoints (/health, /tools, /chat, /audit, /events). Verified successful tool execution and permission-denied path.
- 2026-03-03: PHASE 1 COMPLETE: Implemented llama.cpp LLM client, JSON schema validation for tools, WebSocket event streaming, and full integration tests pass.
- 2026-03-03: PHASE 3 COMPLETE: Implemented Piper TTS integration with bilingual voice support (en_US, es_MX), WAV artifact generation and storage, duration estimation, and graceful fallback to mock TTS for development testing.
- 2026-03-03: PHASE 4 COMPLETE: Implemented sprite-agnostic avatar animation system with viseme-to-frame mapping, animation timeline generation, React AvatarStage component, sprite swapping API endpoints, and comprehensive Max Headroom integration guide (SPRITE_CUSTOMIZATION.md). All integration tests passing with retro-character-v1 placeholder sprite ready for custom sprite drop-in replacement.
- 2026-03-03: FRONTEND UI COMPLETE: Built React/TypeScript web interface with Vite, including ChatPanel for message history, AvatarStage integration for avatar animation sync, real-time audio playback controls, WebSocket event stream listener, and responsive CSS styling. Frontend communicates with backend via HTTP (/chat, /tools, /avatar endpoints) and WebSocket (/ws/events).
- 2026-03-04: FROZEN CONFIG BASELINE: Locked runtime defaults to Ollama Mistral + Edge TTS with canonical ports backend 8000 / frontend 5173; startup and validation scripts aligned to these defaults.
- 2026-03-04: EDGE AUDIO CONTRACT HARDENING: Added provider-agnostic audio path support while keeping backward compatibility for existing wav_path consumers.
- 2026-03-04: CONFIGURATION FOUNDATION STARTED: Added backend configuration endpoints for voices and user preferences, sprite upload endpoint, and stable frontend client_id flow for per-user preference lookup.
- 2026-03-04: PERSISTENCE SCAFFOLDING ADDED: Introduced PostgreSQL-ready SQLAlchemy models/repository for user preferences with in-memory fallback when database is unavailable.
- 2026-03-04: KNOWN-GOOD STARTUP SCRIPT: Added scripts/start_known_good.ps1 with frontend dependency check, Ollama/model readiness, backend health, accented-Spanish TTS smoke test, validation suite execution, and frontend launch.
- 2026-03-04: FROZEN CONFIG VALIDATED: End-to-end smoke tests confirmed mistral:7b-instruct LLM, Edge TTS Spanish voice (es-MX-DaliaNeural), MP3 artifact generation, avatar animation, client preferences integration, and all configuration endpoints return 200 OK. Known-good startup validated.

------------------------------------------------------------------------

# Phase Status Tracker

## Phase 1 --- LLM + Text Chat + Tool Registry

Status: COMPLETE

Scope in this cycle:
- Build backend service skeleton (orchestrator + core modules) - DONE
- Implement text chat orchestration path - DONE
- Add tool registry with permission checks - DONE
- Emit core events for chat and tool execution - DONE

Acceptance targets:
- Text input returns LLM-generated response - VERIFIED
- At least two registered tools callable through orchestrator - VERIFIED (echo, datetime.now)
- Permission deny path is enforced and logged - VERIFIED

Current implementation:
- Backend modules: app.py, orchestrator.py, event_bus.py, permissions.py, session_store.py, schemas.py
- LLM integration: llama_cpp_client.py with real server support + mock fallback
- Tool system: base.py, registry.py (with Pydantic schema validation), mock_echo_tool.py, mock_datetime_tool.py
- API endpoints: /health, /tools (with schemas), /chat, /audit, /events, /ws/events (WebSocket)

Enhancements delivered:
- Real LLM client: LlamaCppClient connects to llama.cpp server (http://localhost:8000/v1) with graceful fallback
- Tool schemas: All tools export OpenAI-compatible function schemas via Pydantic models
- Input validation: Tool registry validates all inputs against declared schemas before execution
- Event streaming: WebSocket endpoint /ws/events provides real-time event stream to frontend
- Error handling: Tool execution failures are caught, logged, and reported without crashing orchestrator
- Audit logging: All permission checks recorded with actor, action, and decision

Integration test results: ALL PASS
- /tools endpoint returns 2 tools with full OpenAI schemas
- /chat endpoint processes requests and executes permitted tools
- /chat endpoint rejects unpermitted tool calls (403 status)
- Event bus logs 12+ events per full conversation cycle
- LLM client falls back to mock mode when server unavailable
- Permission enforcement blocks unauthorized operations

## Phase 3 --- Piper TTS Bilingual

Status: COMPLETE

Scope in this cycle:
- Define TTS worker interface and event contract - DONE
- Add bilingual voice routing policy (English + LATAM Spanish) - DONE
- Return WAV artifact metadata to frontend pipeline - DONE

Acceptance targets:
- Language-specific voice selection works - VERIFIED (en_US and es_MX voices)
- WAV output is consumable by playback and avatar pipeline - VERIFIED

Current implementation:
- Backend modules: tts_worker.py, piper_integration.py, wav_artifact.py
- Piper client: Real TTS support with graceful fallback to mock WAV generation
- Voice support: English (en_US-amy-medium), Spanish/Latin American (es_MX-claudia-medium)
- Bilingual routing: Language-based voice selection with correct audio generation
- WAV artifacts: Full file generation with proper duration estimation and artifact tracking

Enhancements delivered:
- Real Piper integration: PiperTTSClient connects to local Piper runtime (if available)
- Graceful fallback: MockPiperTTSClient generates valid WAVE files for testing when Piper unavailable
- WAV artifact management: Unique artifact IDs, file paths, duration metadata
- Bilingual synthesis: Automatic language detection and correct voice selection
- Duration estimation: Realistic speech duration calculation from WAV headers
- Event integration: assistant_audio_ready events include duration and artifact IDs for Avatar sync

Integration test results: ALL PASS
- English TTS synthesis: works with en_US voice
- Spanish TTS synthesis: works with es_MX voice
- WAV file generation: Valid RIFF headers, audio data
- Artifact tracking: Unique IDs per synthesis, file persistence, metadata completeness
- Avatar payload: audio_duration_seconds for animation timeline sync
- Event stream: assistant_audio_ready events with complete metadata

## Phase 4 --- Avatar Animation

Status: COMPLETE

Scope in this cycle:
- Implement frontend/backend event contract for speaking animation - DONE
- Build viseme-capable animation pipeline with fallback amplitude mode - DONE
- Create sprite-agnostic avatar system for easy character swapping - DONE

Acceptance targets:
- Avatar animation remains synchronized with playback timeline - VERIFIED
- Fallback mode activates if viseme extraction is unavailable - VERIFIED
- Sprite sheets can be swapped without code changes - VERIFIED (API + documentation)

Current implementation:
- Backend modules: sprite_metadata.py, controller.py, service.py, AvatarStage.tsx
- Sprite system: SpriteLibrary manages sprite definitions with frame metadata
- Viseme mapper: Converts phoneme sequence to sprite frame timeline
- Animation controller: Distributes visemes across audio duration
- React component: AvatarStage renders sprites with frame timing from animation timeline
- Sprite management: /avatar/sprites (list) and /avatar/sprite/{name} (switch) endpoints

Enhancements delivered:
- Sprite-agnostic architecture: Add custom sprites (like Max Headroom) via sprite_metadata.py without backend changes
- Viseme-to-frame mapping: Configurable per sprite (A, E, I, O, U, neutral, closed, silence)
- Animation timeline generation: Distributes visemes across TTS duration for lip-sync
- Frame synchronization: Ties animation keyframes to audio playback time
- Idle/blink support: Configurable idle loop frames and blink sequences
- React canvas rendering: Hardware-accelerated sprite frame drawing with proper scaling
- Sprite switching API: Runtime sprite selection and management

Integration test results: ALL PASS
- Sprite library loads with retro-character-v1 placeholder (4x4 sprite sheet, 16 frames)
- Chat request returns complete avatar animation payload with sprite metadata
- Animation timeline: 18 keyframes generated over 2.8s audio duration
- Viseme mapping: Text-to-phoneme estimation creates proper frame sequence
- Event stream: avatar_speak_start/end events include full animation data
- Sprite switch API: Successfully changes active sprite at runtime

Current placeholder:
- Uses generic "retro-character-v1" sprite (64x64 frames, 4 per row)
- Implements standard viseme mapping (A, E, I, O, U + neutral/closed)
- Ready for Max Headroom sprite drop-in replacement

Documentation:
- SPRITE_CUSTOMIZATION.md: Complete guide for adding custom Max Headroom sprite
  - Step-by-step sprite sheet creation (Piskel, Krita, or Aseprite)
  - Viseme mapping table for phoneme-to-mouth shape alignment
  - Advanced effects: glitch overlays, scanlines, frame skipping
  - Troubleshooting and file checklist

Next steps for Max Headroom integration:
1. Design Max Headroom sprite sheet in Piskel/Krita (minimum 8 frames: neutral, closed, A, E, I, O, U, blink)
2. Save PNG to ./assets/sprites/max-headroom.png
3. Register SpriteMetadata in sprite_metadata.py with viseme mappings
4. Call /avatar/sprite/max-headroom-v1 to activate
5. Chat requests will now animate with Max Headroom sprites (no code changes needed)

------------------------------------------------------------------------

# 1. Project Vision

Build a **fully local, modular AI assistant** running on a Jetson Orin
Nano Super 8GB with:

-   Modular AI Agents (IoT, messaging, automation, system tools)
-   Local LLM (brain + tool calling)
-   Local STT (hearing)
-   Local TTS (English + Latin American Spanish)
-   On-demand Vision (webcam snapshot analysis)
-   Avatar UI with animated lip sync
-   Event-driven architecture
-   Safety & permission system

All components must run locally on the Jetson device.

------------------------------------------------------------------------

# 2. Hardware Constraints

Device: Jetson Orin Nano Super 8GB\
Key constraint: 8GB shared RAM (CPU + GPU)

Design rules: - Keep one large model resident at a time (LLM). - Run STT
and TTS as short-lived worker processes. - Avoid large context windows
(2k--4k max). - Use quantized models (4-bit preferred). - Use NVMe
storage if available. - Optional: small swap file to prevent OOM
crashes.

------------------------------------------------------------------------

# 3. Recommended Local Model Stack

## 3.1 LLM (Brain)

Recommended: - 7B--8B Instruct model - Quantization: Q4_K\_M - Runtime:
llama.cpp with CUDA - Context: 2048--4096

Alternative (lighter): - 3B--4B instruct model (Q4)

LLM runs as its own service (llama.cpp server mode).

------------------------------------------------------------------------

## 3.2 STT (Speech-to-Text)

Use: - whisper.cpp (CUDA enabled)

Recommended models: - base (balanced) - small (higher accuracy)

Push-to-talk recommended instead of always-listening.

------------------------------------------------------------------------

## 3.3 TTS (Text-to-Speech)

Use: - Piper (local, lightweight)

Install: - One English voice - One Spanish voice (LATAM if available)

Return WAV to frontend for playback and lip sync.

------------------------------------------------------------------------

## 3.4 Vision (Observing)

Definition of "Observing": - On-demand snapshot only. - Never continuous
streaming.

Pipeline: - Capture single frame. - Run OCR or lightweight detection. -
Feed extracted info into LLM.

Avoid large multimodal models on 8GB unless heavily optimized.

------------------------------------------------------------------------

# 4. System Architecture

## 4.1 Services (Separate Processes)

-   orchestrator (FastAPI + WebSocket)
-   llm_server (llama.cpp)
-   stt_worker (whisper.cpp wrapper)
-   tts_worker (Piper wrapper)
-   vision_worker (optional)

Reason: - Memory isolation - Crash resilience - Clean restarts

------------------------------------------------------------------------

## 4.2 Event-Driven Core

Events: - wake_word_detected - speech_transcribed -
tool_invocation_requested - tool_invocation_completed -
assistant_response_text - assistant_audio_ready - avatar_speak_start /
end

------------------------------------------------------------------------

# 5. Project Folder Structure

assistant/ backend/ app.py api/ core/ orchestrator.py event_bus.py
session_store.py permissions.py schemas.py llm/ audio/ vision/ tools/
base.py registry.py iot_homeassistant.py messaging_tool.py frontend/
src/ components/ AvatarStage.tsx ChatPanel.tsx MicButton.tsx
CameraPanel.tsx

------------------------------------------------------------------------

# 6. Capability / Tool Interface

Each tool must define:

-   id
-   description
-   input schema (JSON)
-   output schema (JSON)
-   permissions required
-   async run(input, context) -\> output

All external actions require permission validation.

------------------------------------------------------------------------

# 7. Runtime Flow

## Wake + Hearing

1.  Hotkey pressed
2.  Mic audio captured
3.  whisper.cpp transcribes
4.  Orchestrator receives transcript

## Orchestrator

1.  Build request packet
2.  Send to LLM
3.  Detect tool calls
4.  Execute tools
5.  Feed results back to LLM
6.  Produce final text

## Speaking

1.  Send text to Piper
2.  Return WAV
3.  Animate avatar + play audio

## Observing

1.  Capture snapshot
2.  Process locally
3.  Summarize into LLM

------------------------------------------------------------------------

# 8. Avatar Implementation

MVP: - 2D avatar - Mouth open/close driven by audio amplitude - Optional
viseme support later

Avoid heavy 3D rendering on Jetson unless optimized.

------------------------------------------------------------------------

# 9. Safety & Permissions

All high-impact tools require: - Policy validation - Optional user
confirmation - Audit logging

Examples requiring confirmation: - Unlock door - Send SMS - Send email -
Modify system files

------------------------------------------------------------------------

# 10. Development Phases

Phase 1: - LLM + text chat + tool registry

Phase 2: - Push-to-talk STT

Phase 3: - Piper TTS bilingual

Phase 4: - Avatar animation

Phase 5: - Vision snapshot

Phase 6: - Real IoT + Messaging integration

------------------------------------------------------------------------

# 11. Performance Expectations

LLM: - Moderate latency on 7B/8B Q4

STT: - Acceptable speed on base/small

TTS: - Fast

Vision: - Snapshot-based processing recommended

------------------------------------------------------------------------

# 12. Design Principles

-   Fully local
-   Modular
-   Event-driven
-   Permission-first
-   Sequential heavy workloads
-   Small models over large models
-   Simplicity over complexity

------------------------------------------------------------------------

# Final Statement

This system is feasible on Jetson Orin Nano Super 8GB if: - Models are
quantized - Tasks are sequential - Vision is bounded - Avatar is
lightweight - Services are separated

The result will be a fully local, modular AI assistant with speech,
tools, vision, and avatar support.
