'use client';

import { useEffect, useRef } from 'react';
import { ConversationMessage } from '@/types';
import MessageBubble from './MessageBubble';

interface ConversationWindowProps {
  messages: ConversationMessage[];
}

export default function ConversationWindow({ messages }: ConversationWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div
      ref={scrollRef}
      className="flex-1 w-full max-w-4xl mx-auto overflow-y-auto px-4 py-6"
      role="log"
      aria-live="polite"
      aria-label="Conversation transcript"
    >
      {messages.length === 0 && (
        <div className="flex items-center justify-center h-full text-gray-400">
          <p className="text-lg">Press the button below to start your conversation</p>
        </div>
      )}

      <div className="space-y-4">
        {messages.map((message, index) => (
          <MessageBubble key={index} message={message} />
        ))}
      </div>
    </div>
  );
}
