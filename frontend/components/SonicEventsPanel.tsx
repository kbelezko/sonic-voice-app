'use client';

import { useEffect, useRef } from 'react';
import { SonicEvent } from '@/types';

interface SonicEventsPanelProps {
  events: SonicEvent[];
}

// Colour badge per event family
const EVENT_COLORS: Record<string, string> = {
  sessionStart:     'bg-purple-100 text-purple-700',
  sessionEnd:       'bg-purple-100 text-purple-700',
  promptStart:      'bg-indigo-100 text-indigo-700',
  promptEnd:        'bg-indigo-100 text-indigo-700',
  contentStart:     'bg-blue-100   text-blue-700',
  contentEnd:       'bg-blue-100   text-blue-700',
  textInput:        'bg-sky-100    text-sky-700',
  textOutput:       'bg-green-100  text-green-700',
  audioInput:       'bg-amber-100  text-amber-700',
  audioOutput:      'bg-orange-100 text-orange-700',
  toolUse:          'bg-rose-100   text-rose-700',
  toolResult:       'bg-pink-100   text-pink-700',
  completionStart:  'bg-teal-100   text-teal-700',
  completionEnd:    'bg-teal-100   text-teal-700',
  usageEvent:       'bg-gray-100   text-gray-600',
};

function badgeClass(eventType: string): string {
  return EVENT_COLORS[eventType] ?? 'bg-gray-100 text-gray-500';
}

/** Pull a short human-readable summary from the event payload */
function summarise(eventType: string, data: Record<string, unknown>): string {
  switch (eventType) {
    case 'contentStart': {
      const role = data.role ?? '';
      const type = data.type ?? '';
      return `${role} · ${type}`;
    }
    case 'contentEnd':
      return data.contentName ? String(data.contentName).slice(0, 8) + '…' : '';
    case 'textOutput': {
      const text = String(data.content ?? '');
      return text.length > 60 ? text.slice(0, 60) + '…' : text;
    }
    case 'audioOutput':
      return String(data.content ?? '');
    case 'toolUse':
      return String(data.toolName ?? data.toolUseId ?? '');
    case 'completionEnd':
      return data.stopReason ? `stopReason: ${data.stopReason}` : '';
    case 'usageEvent': {
      const u = data.usage as Record<string, unknown> | undefined;
      if (u) return `in:${u.inputTokens ?? '?'} out:${u.outputTokens ?? '?'}`;
      return '';
    }
    default:
      return '';
  }
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  const ms = String(d.getMilliseconds()).padStart(3, '0');
  return `${hh}:${mm}:${ss}.${ms}`;
}

export default function SonicEventsPanel({ events }: SonicEventsPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom as events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="flex flex-col h-full bg-gray-950 text-gray-300 font-mono text-xs">
      {/* Header */}
      <div className="shrink-0 px-3 py-2 bg-gray-900 border-b border-gray-800 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-gray-400 font-semibold tracking-wide uppercase text-[10px]">
          Nova Sonic Events
        </span>
        <span className="ml-auto text-gray-600">{events.length}</span>
      </div>

      {/* Event log */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-2 py-2 space-y-1"
      >
        {events.length === 0 && (
          <p className="text-gray-600 text-center mt-8">
            No events yet
          </p>
        )}

        {events.map((ev, i) => {
          const summary = summarise(ev.event_type, ev.data);
          return (
            <div
              key={i}
              className="flex items-start gap-2 leading-tight group"
            >
              {/* Timestamp */}
              <span className="shrink-0 text-gray-600 pt-px">
                {formatTime(ev.ts)}
              </span>

              {/* Badge */}
              <span
                className={`shrink-0 px-1.5 py-px rounded text-[10px] font-semibold ${badgeClass(ev.event_type)}`}
              >
                {ev.event_type}
              </span>

              {/* Summary */}
              {summary && (
                <span className="text-gray-400 truncate">{summary}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
