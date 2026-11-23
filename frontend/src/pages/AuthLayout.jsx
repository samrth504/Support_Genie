/** Split-screen layout for login / signup: product pitch on the left, form on the right. */
import { Bot, ShieldCheck, Sparkles, Zap } from "lucide-react";

const POINTS = [
  { icon: Zap, text: "Instant answers from ShopNest's help center" },
  { icon: Sparkles, text: "Replies in your language: English, Hindi or Hinglish" },
  { icon: ShieldCheck, text: "Tricky issues go to a real specialist" },
];

export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="grid min-h-full lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-brand-700 via-brand-600 to-indigo-500 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-2 text-xl font-bold">
          <span className="text-3xl">🧞</span> SupportGenie
        </div>
        <div>
          <h2 className="text-3xl font-bold leading-tight">ShopNest Help,<br />powered by AI.</h2>
          <ul className="mt-8 space-y-4">
            {POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-brand-50">
                <span className="rounded-lg bg-white/15 p-2"><Icon className="h-5 w-5" /></span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="flex items-center gap-2 text-sm text-brand-100">
          <Bot className="h-4 w-4" /> ML classification · RAG · LangGraph human-in-the-loop
        </p>
        <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-white/10" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-80 w-80 rounded-full bg-white/5" />
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden text-center text-2xl font-bold">🧞 Support<span className="text-brand-600">Genie</span></div>
          <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          <div className="mt-8">{children}</div>
        </div>
      </div>
    </div>
  );
}
