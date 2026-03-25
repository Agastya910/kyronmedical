'use client';
import { useState, useCallback, useRef, useEffect } from 'react';
import { sendMessage, getSession, ChatResponse, BookedAppointment } from '@/lib/api';
import { CallState } from '@/components/CallButton';
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
  const [callState, setCallState] = useState<CallState>('idle');
  const latestSessionId = useRef<string | null>(null);

  // Background polling for active voice calls
  useEffect(() => {
    if (callState === 'idle' || !sessionId) return;

    const interval = setInterval(async () => {
      try {
        const res = await getSession(sessionId);
        
        if (res.belief_state) setBeliefState(res.belief_state);
        if (res.booked_appointment) setBookedAppointment(res.booked_appointment);
        
        // Sync messages from Redis while protecting local UI state IDs mapping
        if (res.messages && Array.isArray(res.messages)) {
           setMessages((prev) => {
             const newMapped = res.messages.map((m: any, i: number) => ({
                 id: prev[i]?.id || crypto.randomUUID(), 
                 role: m.role,
                 content: m.content,
                 timestamp: prev[i]?.timestamp || new Date()
             }));
             // Only force a render if there are actually new messages from the voice thread
             if (newMapped.length > prev.length) return newMapped;
             return prev;
           });
        }

        // Auto-disconnect handling from Twilio closing the socket
        if (res.call_active === false) {
          setCallState('idle');
          toast('Call ended remotely.', { icon: '📞' });
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [callState, sessionId]);

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
    callState,
    setCallState,
    sendUserMessage,
  };
}
