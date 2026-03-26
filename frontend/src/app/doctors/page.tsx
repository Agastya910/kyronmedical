import Link from 'next/link';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Our Doctors | Kyron Care',
  description: 'Meet our team of specialists.',
};

export default function DoctorsPage() {
  const doctors = [
    {
      id: "dr_chen",
      name: "Dr. Sarah Chen",
      specialty: "Orthopedic Surgery",
      description: "Treats bone and joint conditions, and specializes in sports medicine.",
      photo: "SC",
    },
    {
      id: "dr_webb",
      name: "Dr. Marcus Webb",
      specialty: "Cardiology",
      description: "Treats heart conditions and manages preventive cardiology.",
      photo: "MW",
    },
    {
      id: "dr_nair",
      name: "Dr. Priya Nair",
      specialty: "Dermatology",
      description: "Treats skin, hair, and nail disorders with medical and cosmetic expertise.",
      photo: "PN",
    },
    {
      id: "dr_rivera",
      name: "Dr. James Rivera",
      specialty: "Neurology",
      description: "Treats headaches, seizures, and neurodegenerative diseases.",
      photo: "JR",
    },
  ];

  return (
    <main className="relative min-h-screen pt-12 pb-16 px-6" style={{ background: 'var(--kyron-navy)' }}>
      {/* Background Orbs */}
      <div className="bg-orb bg-orb-1" />
      <div className="bg-orb bg-orb-2" />

      <div className="relative z-10 max-w-5xl mx-auto">
        <h1 className="text-4xl font-bold text-white mb-4 text-center tracking-tight drop-shadow-md">Our Doctors</h1>
        <p className="text-white/70 text-center mb-12 max-w-2xl mx-auto text-lg">
          Meet our team of board-certified specialists dedicated to providing top-tier, personalized medical care.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {doctors.map(doc => (
            <div key={doc.id} className="backdrop-blur-md bg-white/10 border border-white/20 rounded-2xl p-6 hover:scale-[1.02] transition-transform duration-300 flex items-start gap-5 shadow-lg">
              <div className="w-16 h-16 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-2xl font-bold shrink-0 shadow-inner">
                {doc.photo}
              </div>
              <div>
                <h2 className="text-xl font-bold text-white mb-1">{doc.name}</h2>
                <p className="text-blue-400 font-semibold mb-3">{doc.specialty}</p>
                <p className="text-white/80 text-sm mb-5 leading-relaxed">
                  {doc.description}
                </p>
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-500/20 text-green-400 text-xs font-semibold uppercase tracking-wider">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
                  Accepting New Patients
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
