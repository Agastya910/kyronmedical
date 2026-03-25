'use client';
import { motion } from 'framer-motion';

export function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="flex items-end gap-3 px-1"
    >
      <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold
                      bg-gradient-to-br from-kyron-teal to-kyron-teal2 text-white">
        K
      </div>
      <div className="glass-teal px-4 py-3 rounded-2xl rounded-bl-sm">
        <div className="flex gap-1.5 items-center h-4">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      </div>
    </motion.div>
  );
}
