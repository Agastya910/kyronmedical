'use client';
import { useState, useRef, KeyboardEvent } from 'react';
import { motion } from 'framer-motion';

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!value.trim() || disabled) return;
    onSend(value.trim());
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  };

  return (
    <div className="flex items-end gap-3">
      <div className="flex-1 glass rounded-2xl px-4 py-3 flex items-end gap-3">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          disabled={disabled}
          placeholder="Type a message…"
          rows={1}
          className="flex-1 bg-transparent text-slate-200 placeholder-slate-500 text-sm
                     resize-none outline-none leading-relaxed max-h-[120px]
                     disabled:opacity-50"
        />
      </div>
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.93 }}
        onClick={handleSend}
        disabled={!value.trim() || disabled}
        className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0
                   bg-gradient-to-br from-kyron-teal to-kyron-teal2
                   text-white shadow-lg shadow-kyron-teal/30
                   disabled:opacity-40 disabled:cursor-not-allowed
                   transition-opacity"
      >
        <SendIcon />
      </motion.button>
    </div>
  );
}

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <line x1="22" y1="2" x2="11" y2="13"/>
      <polygon points="22,2 15,22 11,13 2,9"/>
    </svg>
  );
}
