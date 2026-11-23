import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpenText, Brain, CheckCircle2, PenLine, ShieldCheck } from "lucide-react";

import { errorMessage } from "../../api/client";
import { ticketsApi } from "../../api/endpoints";
import { Button, Card, ErrorBox, Field, inputClass, PageHeader } from "../../components/ui";

// What the LangGraph agent does on the backend, shown while the customer waits
const STEPS = [
  { icon: ShieldCheck, text: "Protecting your personal details" },
  { icon: Brain, text: "Understanding your issue" },
  { icon: BookOpenText, text: "Searching the ShopNest help center" },
  { icon: PenLine, text: "Writing your answer" },
];

const EXAMPLES = [
  { subject: "Forgot my password", body: "I forgot my password and can't log in. How do I reset it?" },
  { subject: "Refund kab aayega?", body: "Mera return pickup ho gaya hai, UPI se payment kiya tha. Refund kitne din mein aayega?" },
  { subject: "Same-day delivery", body: "Do you have same-day delivery in Pune? How much does it cost?" },
  { subject: "Charged twice", body: "I was charged twice for the same order. Please check and refund the extra amount." },
];

function AgentProgress() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 1800);
    return () => clearInterval(t);
  }, []);
  return (
    <Card className="p-6">
      <h2 className="font-semibold text-slate-900">SupportGenie is working on your request…</h2>
      <ol className="mt-5 space-y-3">
        {STEPS.map(({ icon: Icon, text }, i) => (
          <li key={text} className={`flex items-center gap-3 text-sm ${i > step ? "text-slate-400" : "text-slate-700"}`}>
            {i < step ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            ) : (
              <Icon className={`h-5 w-5 ${i === step ? "sg-pulse text-brand-600" : ""}`} />
            )}
            {text}
          </li>
        ))}
      </ol>
      <p className="mt-5 text-xs text-slate-400">This usually takes 5-15 seconds.</p>
    </Card>
  );
}

export default function NewTicket() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ subject: "", body: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (form.subject.trim().length < 3) return setError("Please add a short subject.");
    if (form.body.trim().length < 10) return setError("Please describe your issue in a bit more detail.");
    setError("");
    setLoading(true);
    try {
      const ticket = await ticketsApi.create({ subject: form.subject.trim(), body: form.body.trim() });
      navigate(`/tickets/${ticket.id}`, { state: { justCreated: true } });
    } catch (err) {
      setError(errorMessage(err, "Could not submit your request"));
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="How can we help?" subtitle="Describe your issue - you'll usually get an answer in seconds." />
      {loading ? (
        <AgentProgress />
      ) : (
        <Card className="p-6">
          <form onSubmit={onSubmit} className="space-y-4">
            <ErrorBox message={error} />
            <Field label="Subject">
              <input className={inputClass} maxLength={200} placeholder="e.g. Refund not received"
                value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
            </Field>
            <Field label="Message" hint={`${form.body.length}/4000 · English, Hindi or Hinglish - all fine. Never share OTPs or card PINs.`}>
              <textarea rows={6} maxLength={4000} className={inputClass}
                placeholder="Tell us what happened. Include your order ID (like SN-12345678) if you have one."
                value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
            </Field>
            <div className="flex justify-end">
              <Button type="submit" size="lg">Get help</Button>
            </div>
          </form>

          <div className="mt-6 border-t border-slate-100 pt-4">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Try an example</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button key={ex.subject} type="button" onClick={() => setForm(ex)}
                  className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700">
                  {ex.subject}
                </button>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
