'use client';
import { motion } from 'framer-motion';
import { BookedAppointment } from '@/lib/api';

interface Props {
  appointment: BookedAppointment;
}

export function AppointmentCard({ appointment }: Props) {
  const { doctor, slot, patient } = appointment;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85, y: 24 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 280, damping: 22, delay: 0.15 }}
      className="mx-1 my-3"
    >
      <div className="relative overflow-hidden rounded-2xl border border-kyron-teal/30
                      bg-gradient-to-br from-kyron-teal/10 via-kyron-navy to-kyron-teal2/10
                      shadow-[0_8px_32px_rgba(20,184,166,0.25)]">
        {/* Specular highlight */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/[0.07] via-transparent to-transparent pointer-events-none" />

        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-white/[0.08]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-kyron-teal to-kyron-teal2
                            flex items-center justify-center text-sm font-bold text-white shadow-lg">
              {doctor.photo_placeholder || doctor.name.split(' ').map((n: string) => n[0]).join('')}
            </div>
            <div>
              <p className="text-white font-semibold text-sm">{doctor.name}</p>
              <p className="text-kyron-teal text-xs">{doctor.specialty}</p>
            </div>
          </div>
          {/* Confirmed badge */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 500, damping: 20, delay: 0.4 }}
            className="flex items-center gap-1.5 bg-emerald-500/20 border border-emerald-500/40
                       rounded-full px-3 py-1"
          >
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse-slow" />
            <span className="text-emerald-400 text-xs font-semibold">Confirmed</span>
          </motion.div>
        </div>

        {/* Details */}
        <div className="px-5 py-4 grid grid-cols-2 gap-3">
          <div>
            <p className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Date</p>
            <p className="text-slate-200 text-sm font-medium">{slot.display_date}</p>
          </div>
          <div>
            <p className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Time</p>
            <p className="text-slate-200 text-sm font-medium">{slot.time}</p>
          </div>
          <div>
            <p className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Patient</p>
            <p className="text-slate-200 text-sm font-medium">{patient.first_name} {patient.last_name}</p>
          </div>
          <div>
            <p className="text-slate-500 text-[10px] uppercase tracking-wider mb-1">Confirmation</p>
            <p className="text-kyron-teal text-xs truncate">{patient.email}</p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 pb-4">
          <p className="text-slate-500 text-xs">
            📍 Kyron Medical Group · 1250 Medical Center Drive, Houston TX
          </p>
        </div>
      </div>
    </motion.div>
  );
}
