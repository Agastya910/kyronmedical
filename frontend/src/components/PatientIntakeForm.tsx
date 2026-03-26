'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { submitPatientIntake, verifyPatient, sendIdReminder, IntakeResponse } from '@/lib/api';

interface IntakeResult {
  sessionId: string;
  beliefState: Record<string, unknown>;
  patientId: string;
  patientName: string;
}

interface Props {
  onComplete: (result: IntakeResult) => void;
}

type Mode = 'choose' | 'new' | 'returning' | 'forgot-id' | 'success';

export function PatientIntakeForm({ onComplete }: Props) {
  const [mode, setMode] = useState<Mode>('choose');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [pendingResult, setPendingResult] = useState<IntakeResult | null>(null);

  // New patient form
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [dob, setDob] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');

  // Returning patient
  const [patientId, setPatientId] = useState('');

  // Forgot ID
  const [reminderContact, setReminderContact] = useState('');
  const [reminderSent, setReminderSent] = useState(false);
  const [maskedEmail, setMaskedEmail] = useState('');

  const handleNewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res: IntakeResponse = await submitPatientIntake({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        dob: dob.trim(),
        phone: phone.trim(),
        email: email.trim(),
      });
      const result: IntakeResult = {
        sessionId: res.session_id,
        beliefState: res.belief_state,
        patientId: res.patient_id,
        patientName: firstName.trim(),
      };
      setPendingResult(result);
      setMode('success');
    } catch {
      setError('Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await verifyPatient(patientId.trim());
      if (res.verified && res.session_id && res.belief_state) {
        onComplete({
          sessionId: res.session_id,
          beliefState: res.belief_state,
          patientId: res.patient_id || patientId.trim(),
          patientName: (res.belief_state.first_name as string) || '',
        });
      } else {
        setError(res.message || 'Invalid Patient ID. Please try again.');
      }
    } catch {
      setError('Verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSendReminder = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const isEmail = reminderContact.includes('@');
      const res = await sendIdReminder(
        isEmail ? undefined : reminderContact.trim(),
        isEmail ? reminderContact.trim() : undefined,
      );
      if (res.sent) {
        setReminderSent(true);
        setMaskedEmail(res.masked_email || '');
      } else {
        setError(res.message);
      }
    } catch {
      setError('Could not send reminder. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyId = () => {
    if (pendingResult) {
      navigator.clipboard.writeText(pendingResult.patientId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const inputClass =
    'w-full px-4 py-3 rounded-xl bg-white/[0.06] border border-white/[0.1] ' +
    'text-white placeholder-slate-500 outline-none focus:border-kyron-teal/60 ' +
    'focus:ring-1 focus:ring-kyron-teal/30 transition-all text-sm';

  const btnPrimary =
    'w-full py-3 rounded-xl font-semibold text-sm transition-all ' +
    'bg-gradient-to-r from-kyron-teal to-kyron-teal2 text-white ' +
    'hover:shadow-lg hover:shadow-kyron-teal/30 disabled:opacity-40';

  const btnSecondary =
    'w-full py-3 rounded-xl font-semibold text-sm transition-all ' +
    'bg-white/[0.06] border border-white/[0.1] text-slate-300 ' +
    'hover:bg-white/[0.1] hover:text-white';

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6">
      <AnimatePresence mode="wait">

        {/* ── Choose mode ── */}
        {mode === 'choose' && (
          <motion.div
            key="choose"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="w-full max-w-sm space-y-5"
          >
            <div className="text-center space-y-2">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-kyron-teal to-kyron-teal2
                              flex items-center justify-center text-white text-2xl font-black shadow-lg shadow-kyron-teal/40">
                ◈
              </div>
              <h2 className="text-white text-xl font-bold">Welcome to Kyron Care</h2>
              <p className="text-slate-400 text-sm">Let&apos;s get you set up before we chat.</p>
            </div>

            <button onClick={() => setMode('new')} className={btnPrimary}>
              I&apos;m a New Patient
            </button>
            <button onClick={() => setMode('returning')} className={btnSecondary}>
              I&apos;m a Returning Patient
            </button>
          </motion.div>
        )}

        {/* ── New patient form ── */}
        {mode === 'new' && (
          <motion.form
            key="new"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            onSubmit={handleNewSubmit}
            className="w-full max-w-sm space-y-4"
          >
            <h2 className="text-white text-lg font-bold text-center">Patient Registration</h2>
            <p className="text-slate-400 text-xs text-center">All fields are required.</p>

            <div className="grid grid-cols-2 gap-3">
              <input className={inputClass} placeholder="First Name" value={firstName}
                onChange={(e) => setFirstName(e.target.value)} required />
              <input className={inputClass} placeholder="Last Name" value={lastName}
                onChange={(e) => setLastName(e.target.value)} required />
            </div>
            <input className={inputClass} type="date" placeholder="Date of Birth" value={dob}
              onChange={(e) => setDob(e.target.value)} required />
            <input className={inputClass} type="tel" placeholder="Phone Number" value={phone}
              onChange={(e) => setPhone(e.target.value)} required />
            <input className={inputClass} type="email" placeholder="Email Address" value={email}
              onChange={(e) => setEmail(e.target.value)} required />

            {error && <p className="text-red-400 text-xs text-center">{error}</p>}

            <button type="submit" className={btnPrimary} disabled={loading}>
              {loading ? 'Registering…' : 'Register & Continue'}
            </button>
            <button type="button" onClick={() => setMode('choose')} className="w-full text-slate-500 text-xs hover:text-slate-300 transition">
              ← Back
            </button>
          </motion.form>
        )}

        {/* ── Returning patient ── */}
        {mode === 'returning' && (
          <motion.form
            key="returning"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            onSubmit={handleVerify}
            className="w-full max-w-sm space-y-4"
          >
            <h2 className="text-white text-lg font-bold text-center">Welcome Back</h2>
            <p className="text-slate-400 text-xs text-center">Enter your Patient ID to continue.</p>

            <input className={inputClass} placeholder="Patient ID (e.g. KMG-A1B2C3)" value={patientId}
              onChange={(e) => setPatientId(e.target.value)} required />

            {error && <p className="text-red-400 text-xs text-center">{error}</p>}

            <button type="submit" className={btnPrimary} disabled={loading}>
              {loading ? 'Verifying…' : 'Verify Identity'}
            </button>
            <button type="button" onClick={() => { setMode('forgot-id'); setError(''); }}
              className="w-full text-kyron-teal text-xs hover:text-kyron-teal2 transition text-center">
              Forgot your Patient ID?
            </button>
            <button type="button" onClick={() => setMode('choose')} className="w-full text-slate-500 text-xs hover:text-slate-300 transition">
              ← Back
            </button>
          </motion.form>
        )}

        {/* ── Forgot ID ── */}
        {mode === 'forgot-id' && (
          <motion.div
            key="forgot"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="w-full max-w-sm space-y-4"
          >
            <h2 className="text-white text-lg font-bold text-center">Recover Patient ID</h2>
            <p className="text-slate-400 text-xs text-center">
              Enter your phone number or email. We&apos;ll send your Patient ID.
            </p>

            {!reminderSent ? (
              <form onSubmit={handleSendReminder} className="space-y-4">
                <input className={inputClass} placeholder="Phone or Email" value={reminderContact}
                  onChange={(e) => setReminderContact(e.target.value)} required />
                {error && <p className="text-red-400 text-xs text-center">{error}</p>}
                <button type="submit" className={btnPrimary} disabled={loading}>
                  {loading ? 'Sending…' : 'Send Reminder'}
                </button>
              </form>
            ) : (
              <div className="text-center space-y-3">
                <div className="w-12 h-12 mx-auto rounded-full bg-emerald-500/20 flex items-center justify-center">
                  <span className="text-emerald-400 text-xl">✓</span>
                </div>
                <p className="text-emerald-400 text-sm">Reminder sent!</p>
                {maskedEmail && (
                  <p className="text-slate-400 text-xs">Check your email at {maskedEmail}</p>
                )}
                <p className="text-slate-500 text-xs">Once you have your ID, enter it below.</p>
                <button onClick={() => { setMode('returning'); setReminderSent(false); }} className={btnPrimary}>
                  Enter Patient ID
                </button>
              </div>
            )}

            <button type="button" onClick={() => { setMode('returning'); setError(''); setReminderSent(false); }}
              className="w-full text-slate-500 text-xs hover:text-slate-300 transition">
              ← Back
            </button>
          </motion.div>
        )}

        {/* ── Success — show generated ID with manual Continue button ── */}
        {mode === 'success' && pendingResult && (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-sm text-center space-y-5"
          >
            <div className="w-16 h-16 mx-auto rounded-full bg-emerald-500/20 flex items-center justify-center">
              <span className="text-emerald-400 text-3xl">✓</span>
            </div>
            <div>
              <h2 className="text-white text-xl font-bold">Welcome, {pendingResult.patientName}!</h2>
              <p className="text-slate-400 text-sm mt-1">Your account has been created.</p>
            </div>

            {/* Patient ID display */}
            <div className="glass rounded-xl px-6 py-5 space-y-2">
              <p className="text-slate-500 text-xs uppercase tracking-wider">Your Patient ID</p>
              <p className="text-kyron-teal text-2xl font-mono font-bold tracking-widest">
                {pendingResult.patientId}
              </p>
              <p className="text-slate-500 text-xs">Save this — you&apos;ll need it for future visits</p>
            </div>

            {/* Copy button */}
            <button
              onClick={handleCopyId}
              className={`w-full py-2.5 rounded-xl font-medium text-sm transition-all border ${
                copied
                  ? 'border-emerald-500/50 text-emerald-400 bg-emerald-500/10'
                  : 'border-white/10 text-slate-300 bg-white/[0.06] hover:bg-white/[0.1]'
              }`}
            >
              {copied ? '✓ Copied!' : '📋 Copy Patient ID'}
            </button>

            {/* Manual Continue button */}
            <button
              onClick={() => onComplete(pendingResult)}
              className={btnPrimary}
            >
              I&apos;ve saved my ID — Continue to Chat →
            </button>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  );
}
