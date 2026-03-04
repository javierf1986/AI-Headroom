// API service for communicating with the backend

export interface AnimationPayload {
  mode: 'viseme' | 'amplitude';
  fallback_mode: string;
  sprite: {
    name: string;
    display_name: string;
    image_path: string;
    frame_width: number;
    frame_height: number;
    frames_per_row: number;
    total_frames: number;
  };
  animation: {
    audio_duration_ms: number;
    frames: Array<{
      frame_index: number;
      start_time_ms: number;
      duration_ms: number;
      viseme: string;
    }>;
    idle_frame: number;
    options: {
      blink_probability_per_ms: number;
      auto_blink: boolean;
    };
  };
  status: string;
}

export interface ChatResponse {
  session_id: string;
  text: string;
  tool_results: Record<string, unknown> | Array<Record<string, unknown>>;
  audio?: {
    artifact_id: string;
    audio_path?: string;
    wav_path?: string;
    duration_seconds: number;
    voice_id: string;
    language: string;
    debug?: {
      artifact_file?: string;
      glitch_requested?: boolean;
      glitch_applied?: boolean;
      glitch_error?: string | null;
      glitch_effects?: string[];
      glitch_intensity?: number;
      before?: {
        exists?: boolean;
        file_path?: string;
        file_size?: number;
        file_mtime_ns?: number;
      };
      after?: {
        exists?: boolean;
        file_path?: string;
        file_size?: number;
        file_mtime_ns?: number;
      };
    };
  };
  avatar?: AnimationPayload;
}

export interface ChatRequest {
  session_id: string;
  actor: string;
  text: string;
  language: string;
  permissions: string[];
  client_id?: string;
  preferred_voice_id?: string;
  preferred_sprite?: string;
}

export interface UserPreferences {
  client_id: string;
  default_avatar?: string | null;
}

export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  // Send chat message to backend
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        Accept: 'application/json; charset=utf-8',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error(`Chat failed: ${response.statusText}`);
    }
    const responseText = await response.text();
    return JSON.parse(responseText) as ChatResponse;
  },

  // Get list of available tools
  async getTools() {
    const response = await fetch(`${API_BASE}/tools`);
    if (!response.ok) {
      throw new Error(`Failed to fetch tools: ${response.statusText}`);
    }
    return response.json();
  },

  // Get available voices from backend
  async getAvailableVoices() {
    const response = await fetch(`${API_BASE}/config/voices`);
    if (!response.ok) {
      throw new Error(`Failed to fetch voices: ${response.statusText}`);
    }
    return response.json();
  },

  // Synthesize a short voice preview and return audio blob
  async previewVoice(voiceId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE}/tts/demo?voice_id=${encodeURIComponent(voiceId)}`);
    if (!response.ok) {
      throw new Error(`Failed to get voice preview: ${response.statusText}`);
    }
    return response.blob();
  },

  // Get user preferences
  async getPreferences(clientId: string) {
    const response = await fetch(`${API_BASE}/config/preferences?client_id=${encodeURIComponent(clientId)}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch preferences: ${response.statusText}`);
    }
    return response.json() as Promise<{ preferences: UserPreferences }>;
  },

  // Update user preferences
  async updatePreferences(preferences: Partial<UserPreferences> & { client_id: string }) {
    const response = await fetch(`${API_BASE}/config/preferences`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
      },
      body: JSON.stringify(preferences),
    });
    if (!response.ok) {
      throw new Error(`Failed to update preferences: ${response.statusText}`);
    }
    return response.json() as Promise<{ preferences: UserPreferences }>;
  },

  // Upload avatar sprite
  async uploadSprite(formData: FormData) {
    const response = await fetch(`${API_BASE}/avatar/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      throw new Error(`Failed to upload sprite: ${response.statusText}`);
    }
    return response.json();
  },

  // Get available sprites
  async getAvailableSprites() {
    const response = await fetch(`${API_BASE}/avatar/sprites`);
    if (!response.ok) {
      throw new Error(`Failed to fetch sprites: ${response.statusText}`);
    }
    return response.json();
  },

  // Switch active sprite
  async setActiveSprite(spriteName: string) {
    const response = await fetch(`${API_BASE}/avatar/sprite/${spriteName}`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to set sprite: ${response.statusText}`);
    }
    return response.json();
  },

  // Delete a sprite
  async deleteSprite(spriteName: string) {
    const response = await fetch(`${API_BASE}/avatar/sprite/${spriteName}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || response.statusText);
    }
    return response.json();
  },

  // Update sprite metadata
  async updateSprite(
    spriteName: string,
    data: {
      display_name?: string;
      frame_width?: number;
      frame_height?: number;
      frames_per_row?: number;
      total_frames?: number;
      persona?: string;
      glitch_enabled?: boolean;
      glitch_intensity?: number;
      glitch_effects?: string[];
      preferred_voice_en?: string;
      preferred_voice_es?: string;
    }
  ) {
    const response = await fetch(`${API_BASE}/avatar/sprite/${spriteName}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || response.statusText);
    }
    return response.json();
  },

  // Update sprite voice preferences
  async updateAvatarVoices(spriteName: string, voiceEn: string, voiceEs: string) {
    return this.updateSprite(spriteName, {
      preferred_voice_en: voiceEn,
      preferred_voice_es: voiceEs,
    });
  },

  // Connect to WebSocket event stream
  connectToEventStream(onMessage: (data: unknown) => void) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/events`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error('Failed to parse event data:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return ws;
  },
};
