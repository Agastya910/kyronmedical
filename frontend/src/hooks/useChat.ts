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
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [beliefState, setBeliefState] = useState<Record<string, unknown>>({});
  const [bookedAppointment, setBookedAppointment] = useState<BookedAppointment | null>(null);
  const [callState, setCallState] = useState<CallState>('idle');
  const [intakeComplete, setIntakeComplete] = useState(false);
  const latestSessionId = useRef<string | null>(null);
  const callWasActive = useRef(false);

  // Initialize from intake form result
  const initFromIntake = useCallback((data: {
    sessionId: string;
    beliefState: Record<string, unknown>;
    patientName: string;
  }) => {
    latestSessionId.current = data.sessionId;
    setSessionId(data.sessionId);
    setBeliefState(data.beliefState);
    setIntakeComplete(true);

    // Add the welcome message with the patient's name
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content:
          `Welcome, ${data.patientName}! I'm Kyron Care, your scheduling assistant. ` +
          `Your identity has been verified. What brings you in today?`,
        timestamp: new Date(),
      },
    ]);
  }, []);

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
             const visible = res.messages.filter((m: any) => 
                 (m.role === 'user' || m.role === 'assistant') && 
                 typeof m.content === 'string' && 
                 m.content.trim().length > 0
             );
             
             const newMapped = visible.map((m: any, i: number) => ({
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

        // Track whether the call has actually connected via Twilio WebSocket
        if (res.call_active === true) {
          callWasActive.current = true;
          // Transition from ringing → connected
          if (callState === 'ringing' || callState === 'initiating') {
            setCallState('connected');
          }
        }

        // Only trigger disconnect if the call was previously active and is now inactive
        if (callWasActive.current && res.call_active === false) {
          callWasActive.current = false;
          setCallState('idle');
          toast('Call ended.', { icon: '📞' });
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

  const signOut = useCallback(() => {
    setSessionId(null);
    latestSessionId.current = null;
    setBeliefState({});
    setBookedAppointment(null);
    setIntakeComplete(false);
    setMessages([]);
  }, []);

  return {
    messages,
    sessionId,
    isLoading,
    beliefState,
    bookedAppointment,
    callState,
    setCallState,
    sendUserMessage,
    intakeComplete,
    initFromIntake,
    signOut,
  };
}
