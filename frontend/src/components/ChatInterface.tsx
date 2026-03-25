'use client';
import { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Toaster } from 'react-hot-toast';

import { useChat } from '@/hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { AppointmentCard } from './AppointmentCard';
import { CallButton } from './CallButton';
import { ChatInput } from './ChatInput';

export function ChatInterface() {
  const { messages, sessionId, isLoading, beliefState, bookedAppointment, callState, setCallState, sendUserMessage } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const patientPhone = (beliefState?.phone as string) || null;

  return (
    <div className="relative flex flex-col h-screen max-w-2xl mx-auto">
      <Toaster
        position="top-center"
        toastOptions={{
          style: {
            background: 'rgba(15, 23, 42, 0.95)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#e2e8f0',
            borderRadius: '12px',
          },
        }}
      />

      {/* ── Header ── */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass flex items-center justify-between px-5 py-4 z-10
                   border-b border-white/[0.08] rounded-b-none"
        style={{ borderRadius: '0 0 0 0' }}
      >
        <div className="flex items-center gap-3">
          {/* Logo mark */}
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-kyron-teal to-kyron-teal2
                          flex items-center justify-center text-white font-black text-lg shadow-lg
                          shadow-kyron-teal/40">
            ◈
          </div>
          <div>
            <h1 className="text-white font-bold text-base leading-tight">Kyron Care</h1>
            <p className="text-slate-500 text-xs">Kyron Medical Group</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse-slow" />
          <span className="text-emerald-400 text-xs font-medium">Online</span>
        </div>
      </motion.header>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4 z-10">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <MessageBubble key={msg.id} message={msg} index={i} />
          ))}

          {/* Appointment Card — shown once booking is confirmed */}
          {bookedAppointment && (
            <motion.div key="appointment-card">
              <AppointmentCard appointment={bookedAppointment} />
            </motion.div>
          )}

          {/* Typing indicator */}
          {isLoading && <TypingIndicator key="typing" />}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      {/* ── Footer / Input Bar ── */}
      <motion.footer
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass border-t border-white/[0.08] px-4 pt-3 pb-4 z-10 space-y-3"
      >
        {/* Call button row */}
        <div className="flex items-center justify-between">
          <CallButton 
            sessionId={sessionId} 
            patientPhone={patientPhone} 
            callState={callState} 
            setCallState={setCallState} 
          />
          <p className="text-slate-600 text-[11px]">
            {sessionId ? `Session active` : 'Starting session…'}
          </p>
        </div>

        {/* Input */}
        <ChatInput onSend={sendUserMessage} disabled={isLoading} />
      </motion.footer>
    </div>
  );
}
