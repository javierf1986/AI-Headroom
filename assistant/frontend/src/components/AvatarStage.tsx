import React, { useEffect, useState, useRef, useLayoutEffect } from 'react';
import { API_BASE } from '../api';

interface SpriteFrame {
  frame_index: number;
  start_time_ms: number;
  duration_ms: number;
  viseme: string;
}

interface SpriteInfo {
  name: string;
  display_name: string;
  image_path: string;
  frame_width: number;
  frame_height: number;
  frames_per_row: number;
  total_frames: number;
}

interface AnimationPayload {
  mode: 'viseme' | 'amplitude';
  fallback_mode: string;
  sprite: SpriteInfo;
  animation: {
    audio_duration_ms: number;
    frames: SpriteFrame[];
    idle_frame: number;
    options: {
      blink_probability_per_ms: number;
      auto_blink: boolean;
    };
  };
  status: string;
}

interface AvatarStageProps {
  animation?: AnimationPayload;
  audioStartTime?: number;
  isPlaying?: boolean;
  isLoadingAvatar?: boolean;
  audioRef?: React.RefObject<HTMLAudioElement>;
  audioDurationSeconds?: number;
}

export const AvatarStage: React.FC<AvatarStageProps> = ({
  animation,
  audioStartTime = 0,
  isPlaying = false,
  isLoadingAvatar = false,
  audioRef,
  audioDurationSeconds,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [spriteImage, setSpriteImage] = useState<HTMLImageElement | null>(null);
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [canvasSize, setCanvasSize] = useState({ width: 400, height: 400 });
  const animationFrameRef = useRef<number>();

  // Dynamically size canvas based on container width
  useLayoutEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    let resizeTimeoutId: ReturnType<typeof setTimeout>;

    const updateCanvasSize = () => {
      if (!container) return;

      // Get the actual available width
      const containerWidth = container.clientWidth;
      
      console.log('[AvatarStage] Container width:', containerWidth);

      if (containerWidth <= 0) {
        console.log('[AvatarStage] Container width is 0, skipping size update');
        return;
      }

      // Canvas should be square and fill the width
      // Leave room for padding and gaps
      const size = Math.max(200, Math.min(containerWidth - 32, 600)); // Min 200px, max 600px, account for padding

      console.log('[AvatarStage] Calculated canvas size:', size);

      setCanvasSize({ width: size, height: size });
    };

    // Debounced version for resize events
    const handleResize = () => {
      clearTimeout(resizeTimeoutId);
      resizeTimeoutId = setTimeout(updateCanvasSize, 100);
    };

    // Use ResizeObserver for container changes
    const resizeObserver = new ResizeObserver(() => {
      updateCanvasSize();
    });

    resizeObserver.observe(container);
    
    // Also listen to window resize events
    window.addEventListener('resize', handleResize);
    
    // Initial call
    updateCanvasSize();

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', handleResize);
      clearTimeout(resizeTimeoutId);
    };
  }, []);

  // Load sprite image when animation changes
  useEffect(() => {
    if (!animation) return;

    const img = new Image();
    const imagePath = animation.sprite.image_path;
    const baseUrl = imagePath.startsWith('/') ? `${API_BASE}${imagePath}` : imagePath;
    // Cache-bust based on sprite grid metadata so re-uploads load the new file
    const cacheKey = `${animation.sprite.frame_width}x${animation.sprite.frame_height}_${animation.sprite.total_frames}`;
    const fullUrl = `${baseUrl}?v=${encodeURIComponent(cacheKey)}`;
    img.src = fullUrl;
    img.onload = () => setSpriteImage(img);
    img.onerror = () => {
      console.error(`[AvatarStage] Failed to load sprite: ${fullUrl}`);
    };
  }, [animation]);

  // Animation loop
  useEffect(() => {
    if (!isPlaying || !animation || !spriteImage) return;

    const startTime = audioStartTime || Date.now();
    let lastLoggedFrame = -1;
    let animationStartLogged = false;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const timeline = animation.animation;

      // Calculate duration and scale factor
      let durationMs = timeline.audio_duration_ms;
      let scaleFactor = 1;
      
      if (audioDurationSeconds && audioDurationSeconds > 0) {
        durationMs = audioDurationSeconds * 1000;
        scaleFactor = durationMs / timeline.audio_duration_ms;
      } else if (audioRef?.current && audioRef.current.duration > 0) {
        durationMs = audioRef.current.duration * 1000;
        scaleFactor = durationMs / timeline.audio_duration_ms;
      }

      // Log once at start
      if (!animationStartLogged) {
        animationStartLogged = true;
        const lastFrame = timeline.frames[timeline.frames.length - 1];
        const lastFrameEndTime = lastFrame ? (lastFrame.start_time_ms + lastFrame.duration_ms) * scaleFactor : 0;
        console.log('[AvatarStage] ANIMATION START - SCALED', {
          timelineAudioDurationMs: timeline.audio_duration_ms,
          actualAudioDurationMs: durationMs,
          scaleFactor,
          totalFrames: timeline.frames.length,
          lastFrameEndTime,
          mismatchMs: durationMs - timeline.audio_duration_ms,
        });
      }

      // Find current frame based on elapsed time, using scaled frame timings
      let frameIndex = animation.animation.idle_frame;
      for (const frame of timeline.frames) {
        const scaledStartTime = frame.start_time_ms * scaleFactor;
        const scaledDuration = frame.duration_ms * scaleFactor;
        
        if (elapsed >= scaledStartTime && elapsed < scaledStartTime + scaledDuration) {
          frameIndex = frame.frame_index;
          break;
        }
      }

      // Log frame changes
      if (frameIndex !== lastLoggedFrame) {
        lastLoggedFrame = frameIndex;
        console.log(`[AvatarStage] Frame ${frameIndex} at elapsed ${elapsed}ms (scale: ${scaleFactor.toFixed(2)}x)`);
      }

      setCurrentFrameIndex(frameIndex);

      const shouldContinue = elapsed < durationMs && isPlaying;

      if (!shouldContinue && elapsed > 100) {
        console.log('[AvatarStage] ANIMATION STOPPING', {
          elapsed,
          durationMs,
          scaleFactor,
          reason: elapsed >= durationMs ? 'elapsed >= durationMs' : 'isPlaying is false',
        });
      }

      if (shouldContinue) {
        animationFrameRef.current = requestAnimationFrame(animate);
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying, animation, spriteImage, audioStartTime, audioRef, audioDurationSeconds]);

  // Render sprite frame
  useEffect(() => {
    if (!canvasRef.current || !spriteImage || !animation) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const sprite = animation.sprite;
    const frameWidth = sprite.frame_width;
    const frameHeight = sprite.frame_height;
    const framesPerRow = sprite.frames_per_row;

    // Calculate source position in sprite sheet
    const frameCol = currentFrameIndex % framesPerRow;
    const frameRow = Math.floor(currentFrameIndex / framesPerRow);
    const srcX = frameCol * frameWidth;
    const srcY = frameRow * frameHeight;

    // Scale to fit canvas
    const scale = Math.min(canvas.width / frameWidth, canvas.height / frameHeight);
    const drawWidth = frameWidth * scale;
    const drawHeight = frameHeight * scale;
    const drawX = (canvas.width - drawWidth) / 2;
    const drawY = (canvas.height - drawHeight) / 2;

    // Clear canvas
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw sprite frame
    ctx.drawImage(
      spriteImage,
      srcX,
      srcY,
      frameWidth,
      frameHeight,
      drawX,
      drawY,
      drawWidth,
      drawHeight
    );

    // Optional: Show frame info in development
    if (import.meta.env.DEV) {
      ctx.fillStyle = '#333';
      ctx.font = '12px monospace';
      ctx.fillText(`Frame: ${currentFrameIndex}`, 10, 20);
    }
  }, [spriteImage, currentFrameIndex, animation]);

  if (isLoadingAvatar) {
    return (
      <div className="avatar-stage avatar-stage--placeholder" ref={containerRef}>
        <p className="avatar-status-text">Loading avatar...</p>
      </div>
    );
  }

  if (!animation) {
    return (
      <div className="avatar-stage avatar-stage--placeholder" ref={containerRef}>
        <p className="avatar-status-text">No avatar loaded</p>
      </div>
    );
  }

  return (
    <div className="avatar-stage" ref={containerRef}>
      <canvas
        ref={canvasRef}
        width={canvasSize.width}
        height={canvasSize.height}
        style={{
          width: `${canvasSize.width}px`,
          height: `${canvasSize.height}px`,
          maxWidth: '100%',
          display: 'block',
        }}
      />
    </div>
  );
};
