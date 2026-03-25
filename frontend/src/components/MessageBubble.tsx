'use client';
import { motion } from 'framer-motion';
import { Message } from '@/hooks/useChat';
import { clsx } from 'clsx';

interface Props {
  message: Message;
  index: number;
}

export function MessageBubble({ message, index }: Props) {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 380, damping: 28, delay: 0 }}
      className={clsx('flex items-end gap-3 px-1', isUser ? 'justify-end' : 'justify-start')}
    >
      {/* Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold
                        bg-gradient-to-br from-kyron-teal to-kyron-teal2 text-white shadow-lg
                        shadow-kyron-teal/30">
          K
        </div>
      )}

      {/* Bubble */}
      <div
        className={clsx(
          'max-w-[78%] px-4 py-3 rounded-2xl text-sm leading-relaxed',
          isUser
            ? 'glass-blue text-slate-100 rounded-br-sm'
            : 'glass-teal text-slate-100 rounded-bl-sm',
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        <p suppressHydrationWarning className={clsx(
          'text-[10px] mt-1.5 opacity-50',
          isUser ? 'text-right' : 'text-left',
        )}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold
                        bg-gradient-to-br from-kyron-blue to-violet-500 text-white shadow-lg shadow-blue-500/30">
          Y
        </div>
      )}
    </motion.div>
  );
}
