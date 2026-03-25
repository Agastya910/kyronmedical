'use client';
import { useState, useCallback, useRef } from 'react';
import { sendMessage, ChatResponse, BookedAppointment } from '@/lib/api';
import toast from 'react-hot-toast';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "Hi there! I'm Kyron Care, your scheduling assistant for Kyron Medical Group. " +
        "I can help you schedule an appointment, check on a prescription refill, or answer questions about our offices. What can I help you with today?",
      timestamp: new Date(),
    },
  ]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [beliefState, setBeliefState] = useState<Record<string, unknown>>({});
  const [bookedAppointment, setBookedAppointment] = useState<BookedAppointment | null>(null);
  const latestSessionId = useRef<string | null>(null);

  const sendUserMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    // Small artificial delay for humanization (600ms min)
    const [response] = await Promise.all([
      sendMessage(text.trim(), latestSessionId.current).catch((err) => {
        toast.error('Connection error. Please try again.');
        throw err;
      }),
      new Promise((r) => setTimeout(r, 650)),
    ]);

    const data = response as ChatResponse;

    latestSessionId.current = data.session_id;
    setSessionId(data.session_id);
    setBeliefState(data.belief_state);

    if (data.booked_appointment) {
      setBookedAppointment(data.booked_appointment as BookedAppointment);
    }

    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: data.reply,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, assistantMsg]);
    setIsLoading(false);
  }, [isLoading]);

  return {
    messages,
    sessionId,
    isLoading,
    beliefState,
    bookedAppointment,
    sendUserMessage,
  };
}
