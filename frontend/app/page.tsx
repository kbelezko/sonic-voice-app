'use client';

import { useRef, useCallback } from 'react';
import ConversationWindow from '@/components/ConversationWindow';
import VoiceButton from '@/components/VoiceButton';
import SonicEventsPanel from '@/components/SonicEventsPanel';
import AvatarPanel from '@/components/AvatarPanel';
import { useVoiceChat } from '@/lib/useVoiceChat';
import ErrorBoundary from '@/components/ErrorBoundary';

export default function Home() {
  const avatarRef = useRef<HTMLIFrameElement>(null);

  // Decode the base64 WAV, strip the 44-byte PCM WAV header, and transfer the
  // raw Int16 PCM buffer to the avatar iframe as a transferable (zero-copy).
  // TalkingHead's streaming AudioWorklet plays it gaplessly; HeadAudio drives
  // the lip animation from the same audio node — no double-play, no choppiness.
  const postToAvatar = useCallback((audioBase64: string) => {
    const iframeWindow = avatarRef.current?.contentWindow;
    if (!iframeWindow) return;

    const binary = atob(audioBase64);
    const bytes  = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

    // Nova Sonic outputs standard PCM WAV (16kHz, 16-bit, mono) with a
    // fixed 44-byte header. Slice it off to get the raw PCM samples.
    const WAV_HEADER = 44;
    if (bytes.byteLength <= WAV_HEADER) return;
    const pcmBuffer = bytes.buffer.slice(WAV_HEADER);

    // Transfer (zero-copy) to the iframe
    iframeWindow.postMessage({ type: 'pcmChunk', buffer: pcmBuffer }, '*', [pcmBuffer]);
  }, []);

  const {
    messages,
    sonicEvents,
    connectionStatus,
    voiceButtonState,
    startVoiceSession,
    stopVoiceSession,
  } = useVoiceChat({ onAudio: postToAvatar });

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-screen bg-gray-50">

        {/* ── Status bar (only when not idle/connected) ── */}
        {connectionStatus !== 'connected' && connectionStatus !== 'disconnected' && (
          <div className="shrink-0 w-full bg-yellow-100 border-b border-yellow-300 px-4 py-2 text-center text-sm">
            {connectionStatus === 'connecting'   && 'Connecting…'}
            {connectionStatus === 'reconnecting' && 'Connection lost. Reconnecting…'}
            {connectionStatus === 'error'        && 'Connection error. Please refresh the page.'}
          </div>
        )}

        {/* ── Main area: avatar (left) + transcript (centre) + events (right) ── */}
        <div className="flex flex-1 min-h-0">

          {/* Left — 3D talking avatar with audio-driven lip-sync */}
          <AvatarPanel ref={avatarRef} />

          {/* Centre — conversation transcript */}
          <main className="flex flex-col flex-1 min-w-0">
            <ConversationWindow messages={messages} />

            <div className="shrink-0 flex flex-col items-center py-5 bg-white border-t border-gray-200 shadow-[0_-1px_4px_rgba(0,0,0,0.06)]">
              <VoiceButton
                state={voiceButtonState}
                onStart={startVoiceSession}
                onStop={stopVoiceSession}
              />
            </div>
          </main>

          {/* Right — Nova Sonic technical events */}
          <aside className="hidden lg:flex flex-col w-80 xl:w-96 shrink-0 border-l border-gray-800">
            <SonicEventsPanel events={sonicEvents} />
          </aside>

        </div>
      </div>
    </ErrorBoundary>
  );
}
