'use client';

import { ConversationMessage } from '@/types';

interface MessageBubbleProps {
  message: ConversationMessage;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      aria-label={`${message.role} message`}
    >
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : isSystem
            ? 'bg-yellow-100 text-gray-800 border border-yellow-300'
            : 'bg-green-100 text-gray-800 shadow-sm border border-green-200'
        }`}
      >
        <div className="text-sm mb-1">
          <span className="font-semibold">
            {isUser ? 'You' : isSystem ? 'System' : 'Assistant'}
          </span>
        </div>
        <div className="text-base whitespace-pre-wrap">{message.content}</div>
        <div className={`text-xs mt-2 ${isUser ? 'text-blue-100' : 'text-gray-400'}`}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
