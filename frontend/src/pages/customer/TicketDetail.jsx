import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ArrowLeft, Bot, ChevronDown, Clock, FileText, ThumbsDown, ThumbsUp, UserRound } from "lucide-react";

import { errorMessage } from "../../api/client";
import { ticketsApi } from "../../api/endpoints";
import { Card, ErrorBox, Spinner, StatusBadge } from "../../components/ui";
import { formatDateTime } from "../../utils/format";

const POLL_MS = 10000;

function Sources({ sources }) {
  const [open, setOpen] = useState(false);
  if (!sources?.length) return null;
  return (
    <div className="mt-4 border-t border-slate-100 pt-3">
      <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-700">
        <FileText className="h-3.5 w-3.5" /> Based on {sources.length} help-center article{sources.length > 1 ? "s" : ""}
        <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <ul className="mt-2 space-y-2">
          {sources.map((s, i) => (
            <li key={i} className="rounded-lg bg-slate-50 p-3 text-xs">
              <div className="font-medium text-slate-700">{s.title}{s.section ? ` › ${s.section}` : ""}</div>
              <p className="mt-1 text-slate-500">{s.snippet}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Feedback({ ticket, onDone }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const answered = ticket.status === "ai_resolved" || ticket.status === "agent_resolved";
  if (!answered && ticket.feedback === null) return null;

  if (ticket.feedback !== null) {
    return (
      <p className="mt-4 text-sm text-slate-500">
        {ticket.feedback === 1
          ? "Thanks for your feedback! 🙌"
          : ticket.status === "pending_review"
            ? "Sorry this didn't help. A support specialist will follow up with you."
            : "Thanks for your feedback - we'll use it to improve."}
      </p>
    );
  }

  const send = async (rating) => {
    setBusy(true);
    setError("");
    try {
      onDone(await ticketsApi.feedback(ticket.id, rating));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-4 flex flex-wrap items-center gap-3">
      <span className="text-sm text-slate-600">Was this helpful?</span>
      <button disabled={busy} onClick={() => send(1)}
        className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-sm hover:border-emerald-300 hover:bg-emerald-50 disabled:opacity-50">
        <ThumbsUp className="h-4 w-4" /> Yes
      </button>
      <button disabled={busy} onClick={() => send(-1)}
        className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-sm hover:border-red-300 hover:bg-red-50 disabled:opacity-50">
        <ThumbsDown className="h-4 w-4" /> No, I need more help
      </button>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}

export default function TicketDetail() {
  const { id } = useParams();
  const location = useLocation();
  const [ticket, setTicket] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    ticketsApi.get(id).then((t) => { setTicket(t); setError(""); }).catch((err) => setError(errorMessage(err)));
  }, [id]);
  useEffect(load, [load]);

  // while a specialist is reviewing, refresh automatically
  useEffect(() => {
    if (ticket?.status !== "pending_review") return;
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [ticket?.status, load]);

  if (error && !ticket) return <ErrorBox message={error} onRetry={load} />;
  if (!ticket) return <Spinner />;

  const pending = ticket.status === "pending_review" || ticket.status === "open";
  const byAgent = ticket.answered_by === "agent";

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/tickets" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft className="h-4 w-4" /> My requests
      </Link>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-slate-900">{ticket.subject}</h1>
        <StatusBadge status={ticket.status} />
        <span className="text-xs text-slate-400">#{ticket.id} · {formatDateTime(ticket.created_at)}</span>
      </div>

      {/* customer's message */}
      <div className="mb-4 flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-3 text-sm text-white shadow-sm whitespace-pre-wrap">
          {ticket.body}
        </div>
      </div>

      {/* answer */}
      {pending ? (
        <Card className="flex items-start gap-3 border-amber-200 bg-amber-50 p-5">
          <Clock className="mt-0.5 h-5 w-5 text-amber-600" />
          <div>
            <p className="font-medium text-amber-900">A support specialist is looking into this</p>
            <p className="mt-1 text-sm text-amber-800">
              {location.state?.justCreated
                ? "Your request needs a human check, so we've passed it to our team with all the details. "
                : ""}
              You'll see the reply here - this page refreshes automatically.
            </p>
          </div>
        </Card>
      ) : (
        <div className="flex gap-3">
          <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${byAgent ? "bg-blue-100 text-blue-700" : "bg-brand-100 text-brand-700"}`}>
            {byAgent ? <UserRound className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
          </div>
          <Card className="flex-1 p-5">
            <div className="mb-2 text-xs font-medium text-slate-500">
              {byAgent ? "ShopNest support specialist" : "SupportGenie (AI assistant)"}
              {ticket.resolved_at && ` · ${formatDateTime(ticket.resolved_at)}`}
            </div>
            <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">{ticket.reply}</div>
            <Sources sources={ticket.sources} />
            <Feedback ticket={ticket} onDone={setTicket} />
          </Card>
        </div>
      )}
    </div>
  );
}
