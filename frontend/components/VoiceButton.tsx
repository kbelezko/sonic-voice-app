'use client';

import { VoiceButtonState } from '@/types';
import { Mic, MicOff, Loader2 } from 'lucide-react';

interface VoiceButtonProps {
  state: VoiceButtonState;
  onStart: () => void;
  onStop: () => void;
}

export default function VoiceButton({ state, onStart, onStop }: VoiceButtonProps) {
  const isListening = state === 'listening';
  const isProcessing = state === 'processing';
  const isInactive = state === 'inactive';

  const handleClick = () => {
    if (isListening || isProcessing) {
      onStop();
    } else {
      onStart();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <div className="flex flex-col items-center">
      <button
        onClick={handleClick}
        onKeyDown={handleKeyPress}
        disabled={isProcessing}
        className={`
          group relative flex items-center justify-center
          w-20 h-20 rounded-full
          transition-all duration-300 ease-in-out
          focus:outline-none focus:ring-4 focus:ring-offset-2
          ${
            isListening
              ? 'bg-red-500 hover:bg-red-600 focus:ring-red-300 animate-pulse'
              : isProcessing
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-300 shadow-lg hover:shadow-xl'
          }
        `}
        aria-label={
          isListening
            ? 'Stop voice session'
            : isProcessing
            ? 'Processing...'
            : 'Start voice session'
        }
        aria-pressed={isListening}
        tabIndex={0}
      >
        {isProcessing ? (
          <Loader2 className="w-8 h-8 text-white animate-spin" />
        ) : isListening ? (
          <MicOff className="w-8 h-8 text-white" />
        ) : (
          <Mic className="w-8 h-8 text-white" />
        )}

        {/* Pulsing ring effect when listening */}
        {isListening && (
          <span className="absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75 animate-ping" />
        )}
      </button>

      {/* Button label */}
      <div className="mt-3 text-center">
        <p className="text-sm font-medium text-gray-700">
          {isListening
            ? 'Listening...'
            : isProcessing
            ? 'Processing...'
            : 'Start Voice Session'}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          {isInactive && 'Press to begin'}
        </p>
      </div>
    </div>
  );
}
