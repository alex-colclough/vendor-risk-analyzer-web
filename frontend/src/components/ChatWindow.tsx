'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { MessageSquare, Send, X, Loader2, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useStore } from '@/store';
import { useChatWebSocket } from '@/hooks/useWebSocket';
import type { ChatMessage, ProgressEvent } from '@/types';

export function ChatWindow() {
  const {
    sessionId,
    isChatOpen,
    toggleChat,
    chatMessages,
    addChatMessage,
    progressMessages,
  } = useStore();

  const [input, setInput] = useState('');
  const [streamingMessage, setStreamingMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleWebSocketMessage = useCallback(
    (event: ProgressEvent) => {
      if (event.event_type === 'chat_response_chunk') {
        setStreamingMessage((prev) => prev + (event.data?.chunk || ''));
      } else if (event.event_type === 'chat_response_complete') {
        if (streamingMessage || event.data?.full_response) {
          addChatMessage({
            id: Date.now().toString(),
            role: 'assistant',
            content: event.data?.full_response as string || streamingMessage,
            timestamp: new Date().toISOString(),
          });
          setStreamingMessage('');
        }
      }
    },
    [addChatMessage, streamingMessage]
  );

  const { connect, disconnect, sendMessage, isConnected, isTyping } =
    useChatWebSocket(sessionId, {
      onMessage: handleWebSocketMessage,
    });

  useEffect(() => {
    if (isChatOpen && !isConnected) {
      connect();
    }
  }, [isChatOpen, isConnected, connect]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, streamingMessage]);

  const handleSend = () => {
    if (!input.trim()) return;

    // Add user message
    addChatMessage({
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    });

    // Send via WebSocket
    sendMessage(input);
    setInput('');
    setStreamingMessage('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!isChatOpen) {
    return (
      <Button
        onClick={toggleChat}
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg"
        size="icon"
      >
        <MessageSquare className="h-6 w-6" />
      </Button>
    );
  }

  return (
    <Card className="fixed bottom-0 right-0 w-full md:w-[500px] md:right-6 md:bottom-6 h-[500px] flex flex-col shadow-xl z-50">
      <CardHeader className="flex flex-row items-center justify-between py-3 px-4 border-b">
        <CardTitle className="text-base flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          AI Assistant
          {isConnected && (
            <span className="w-2 h-2 rounded-full bg-green-500" />
          )}
        </CardTitle>
        <Button variant="ghost" size="icon" onClick={toggleChat}>
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
        <div className="flex-1 flex">
          {/* Progress Panel */}
          <div className="w-1/2 border-r flex flex-col">
            <div className="px-3 py-2 border-b bg-muted/50">
              <p className="text-xs font-medium text-muted-foreground">
                Analysis Progress
              </p>
            </div>
            <ScrollArea className="flex-1 p-3">
              <div className="space-y-2">
                {progressMessages.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">
                    Progress updates will appear here
                  </p>
                ) : (
                  progressMessages.slice(-20).map((msg, i) => (
                    <div
                      key={i}
                      className="text-xs p-2 rounded bg-muted animate-slide-up"
                    >
                      <span className="text-muted-foreground">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </span>
                      <p className="mt-1">{msg.message}</p>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>

          {/* Chat Panel */}
          <div className="w-1/2 flex flex-col">
            <div className="px-3 py-2 border-b bg-muted/50">
              <p className="text-xs font-medium text-muted-foreground">
                Chat
              </p>
            </div>
            <ScrollArea className="flex-1 p-3">
              <div className="space-y-3">
                {chatMessages.length === 0 && !streamingMessage && (
                  <p className="text-xs text-muted-foreground text-center py-4">
                    Ask questions about your compliance analysis
                  </p>
                )}
                {chatMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${
                      msg.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    <div
                      className={`max-w-[85%] rounded-lg px-3 py-2 text-sm animate-slide-up ${
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}
                {streamingMessage && (
                  <div className="flex justify-start">
                    <div className="max-w-[85%] rounded-lg px-3 py-2 text-sm bg-muted">
                      {streamingMessage}
                      <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
                    </div>
                  </div>
                )}
                {isTyping && !streamingMessage && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-lg px-3 py-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>
          </div>
        </div>

        {/* Input */}
        <div className="p-3 border-t">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your compliance..."
              className="flex-1 px-3 py-2 text-sm rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              disabled={!isConnected}
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || !isConnected}
              size="icon"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
