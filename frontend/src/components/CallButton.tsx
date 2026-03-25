'use client';
import { motion, AnimatePresence } from 'framer-motion';
import { initiateCall } from '@/lib/api';
import toast from 'react-hot-toast';

export type CallState = 'idle' | 'initiating' | 'ringing' | 'connected';

interface Props {
  sessionId: string | null;
  patientPhone: string | null;
  callState: CallState;
  setCallState: (s: CallState) => void;
}

export function CallButton({ sessionId, patientPhone, callState, setCallState }: Props) {

  const handleCall = async () => {
    if (!sessionId || !patientPhone) {
      toast.error("Please complete the intake form first so we have your phone number.");
      return;
    }
    setCallState('initiating');
    try {
      await initiateCall(patientPhone, sessionId);
      setCallState('ringing');
      toast.success('Calling your phone now…');
      // After 10s assume connected (could be replaced by Vapi webhook)
      setTimeout(() => setCallState('connected'), 10000);
    } catch {
      toast.error('Could not initiate call. Please try again.');
      setCallState('idle');
    }
  };

  const handleEndCall = () => {
    setCallState('idle');
    toast('Call ended. You can continue chatting here anytime.', { icon: '💬' });
  };

  if (callState === 'idle') {
    return (
      <motion.button
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        onClick={handleCall}
        className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold
                   glass border-kyron-teal/40 text-kyron-teal
                   hover:bg-kyron-teal/10 transition-colors cursor-pointer"
      >
        <PhoneIcon />
        <span>Call Me to Continue</span>
      </motion.button>
    );
  }

  if (callState === 'initiating') {
    return (
      <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold
                      glass border-kyron-teal/30 text-kyron-teal/70">
        <SpinnerIcon />
        <span>Connecting…</span>
      </div>
    );
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex items-center gap-3"
      >
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold
                        bg-emerald-500/15 border border-emerald-500/40 text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>{callState === 'ringing' ? 'Phone ringing…' : 'On call'}</span>
        </div>
        <button
          onClick={handleEndCall}
          className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold
                     bg-red-500/15 border border-red-500/40 text-red-400
                     hover:bg-red-500/25 transition-colors"
        >
          End
        </button>
      </motion.div>
    </AnimatePresence>
  );
}

function PhoneIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.09 11 19.79 19.79 0 01.13 2.36 2 2 0 012.11.18h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.36a16 16 0 006.72 6.72l1.43-.47.44.44a2 2 0 002.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/>
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 12a9 9 0 11-6.219-8.56"/>
    </svg>
  );
}
