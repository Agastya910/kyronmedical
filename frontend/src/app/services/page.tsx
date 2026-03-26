import Link from 'next/link';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Our Services | Kyron Care',
  description: 'Services provided by Kyron Medical Group.',
};

export default function ServicesPage() {
  const services = [
    {
      title: "Appointment Scheduling",
      emoji: "📅",
      description: "Easily book times with our intelligent AI-assisted intake form. Available 24/7 to fit your busy schedule."
    },
    {
      title: "Prescription Refill Requests",
      emoji: "💊",
      description: "Request prescription renewals directly through our platform. Securely processed and sent directly to your pharmacy."
    },
    {
      title: "Insurance Pre-auth Support",
      emoji: "🛡️",
      description: "We handle the complicated paperwork so you don't have to. Automated checks verify your coverage seamlessly."
    },
    {
      title: "After-Hours Nurse Line",
      emoji: "🌙",
      description: "Connect with certified nursing staff for urgent medical questions outside regular clinic hours. Help is a tap away."
    },
    {
      title: "Telehealth Consultations",
      emoji: "📱",
      description: "Secure, high-quality video appointments from the comfort of your home. Perfect for follow-ups and minor urgent care."
    }
  ];

  return (
    <main className="relative min-h-screen pt-12 pb-16 px-6" style={{ background: 'var(--kyron-navy)' }}>
      {/* Background Orbs */}
      <div className="bg-orb bg-orb-1" />
      <div className="bg-orb bg-orb-3" />

      <div className="relative z-10 max-w-5xl mx-auto">
        <h1 className="text-4xl font-bold text-white mb-4 text-center tracking-tight drop-shadow-md">Our Services</h1>
        <p className="text-white/70 text-center mb-12 max-w-2xl mx-auto text-lg">
          From routine checkups to specialized care, we offer a comprehensive suite of digital-first health services.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {services.map((service, i) => (
            <div key={i} className="backdrop-blur-md bg-white/10 border border-white/20 rounded-2xl p-6 hover:-translate-y-1 transition-transform duration-300 shadow-lg flex flex-col items-start">
              <div className="text-4xl mb-5">{service.emoji}</div>
              <h2 className="text-lg font-bold text-white mb-2">{service.title}</h2>
              <p className="text-white/80 text-sm leading-relaxed">
                {service.description}
              </p>
            </div>
          ))}
        </div>

        <div className="text-center">
          <Link href="/" className="inline-flex items-center gap-2 backdrop-blur-md bg-blue-500/20 text-blue-400 border border-blue-500/30 font-semibold py-3 px-8 rounded-full hover:bg-blue-500/30 transition-colors duration-300 shadow-xl">
            Schedule an Appointment <span className="text-xl leading-none">→</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
