/** Human-in-the-loop screen: see what the AI saw and wrote, then approve / edit / reject. */
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, Eye, EyeOff, FileText, Send, ShieldAlert, X } from "lucide-react";

import { errorMessage } from "../../api/client";
import { reviewApi } from "../../api/endpoints";
import {
  Badge, Button, Card, ConfidenceBar, ErrorBox, inputClass, PriorityBadge, Spinner, StatusBadge,
} from "../../components/ui";
import { formatDateTime, humanize } from "../../utils/format";
import { ReasonChips } from "./TicketList";

function Info({ label, children }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium text-slate-800">{children}</span>
    </div>
  );
}

export default function ReviewDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(null);
  const [reply, setReply] = useState("");
  const [showOriginal, setShowOriginal] = useState(false);
  const [confirmReject, setConfirmReject] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    reviewApi.get(id)
      .then((t) => { setTicket(t); setReply(t.ai_draft || ""); setError(""); })
      .catch((err) => setError(errorMessage(err)));
  }, [id]);
  useEffect(load, [load]);

  if (error && !ticket) return <ErrorBox message={error} onRetry={load} />;
  if (!ticket) return <Spinner />;

  const pending = ticket.status === "pending_review";
  const edited = reply.trim() !== (ticket.ai_draft || "").trim();

  const act = async (action) => {
    setBusy(action);
    setError("");
    try {
      // approve -> backend sends the AI draft · edit -> our text · reject -> our text only if we wrote one,
      // otherwise the backend's standard "could not process" message (never the unapproved draft)
      const payload = action === "approve" ? null : action === "reject" && !edited ? null : reply.trim() || null;
      await reviewApi.act(ticket.id, action, payload);
      navigate("/staff/queue");
    } catch (err) {
      setError(errorMessage(err));
      setBusy("");
    }
  };

  return (
    <div>
      <Link to="/staff/queue" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft className="h-4 w-4" /> Review queue
      </Link>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-slate-900">{ticket.subject}</h1>
        <StatusBadge status={ticket.status} staff />
        <PriorityBadge priority={ticket.priority} />
        <span className="text-xs text-slate-400">#{ticket.id}</span>
      </div>

      {ticket.injection_flag && (
        <div className="mb-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <b>Possible prompt-injection attempt.</b> This message tried to give instructions to the AI, so it was
            never sent to the LLM. Review it carefully - rejecting is usually right.
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        {/* LEFT: what the customer sent + what the AI saw */}
        <div className="space-y-6 lg:col-span-2">
          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">Customer message</h2>
              {ticket.body_masked && ticket.body_masked !== ticket.body && (
                <button onClick={() => setShowOriginal((s) => !s)} className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800">
                  {showOriginal ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  {showOriginal ? "Show masked" : "Show original"}
                </button>
              )}
            </div>
            <p className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
              {showOriginal ? ticket.body : ticket.body_masked || ticket.body}
            </p>
            <p className="mt-2 text-xs text-slate-500">
              {ticket.customer_name} · {ticket.customer_email} · {formatDateTime(ticket.created_at)}
            </p>
          </Card>

          <Card className="p-5">
            <h2 className="mb-2 font-semibold text-slate-900">AI analysis</h2>
            <div className="divide-y divide-slate-100">
              <Info label="Category (ML model)">
                {ticket.category || "–"}{ticket.category_prob != null && <span className="ml-1 text-slate-400">({Math.round(ticket.category_prob * 100)}%)</span>}
              </Info>
              <Info label="Overall confidence"><ConfidenceBar value={ticket.confidence} /></Info>
              <Info label="Sentiment">{ticket.sentiment ? humanize(ticket.sentiment) : "–"}</Info>
              <Info label="Language">{ticket.language ? humanize(ticket.language) : "–"}</Info>
            </div>
            {ticket.review_reasons?.length > 0 && (
              <div className="mt-3">
                <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">Why it needs a human</div>
                <ReasonChips reasons={ticket.review_reasons} />
              </div>
            )}
          </Card>
        </div>

        {/* RIGHT: draft + decision */}
        <div className="space-y-6 lg:col-span-3">
          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">{pending ? "AI draft reply" : "Reply sent to customer"}</h2>
              {pending && edited && <Badge tone="brand">Edited</Badge>}
            </div>

            {pending ? (
              <>
                {!ticket.ai_draft && (
                  <p className="mb-2 text-sm text-slate-500">No AI draft for this ticket - please write the reply yourself.</p>
                )}
                <textarea rows={9} className={inputClass} value={reply} onChange={(e) => setReply(e.target.value)}
                  placeholder="Write the reply the customer will see…" />
                <ErrorBox message={error} />
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {edited ? (
                    <Button variant="success" loading={busy === "edit"} disabled={!reply.trim() || !!busy} onClick={() => act("edit")}>
                      <Send className="h-4 w-4" /> Send edited reply
                    </Button>
                  ) : (
                    <Button variant="success" loading={busy === "approve"} disabled={!ticket.ai_draft || !!busy} onClick={() => act("approve")}>
                      <Check className="h-4 w-4" /> Approve &amp; send
                    </Button>
                  )}
                  {edited && ticket.ai_draft && (
                    <Button variant="ghost" onClick={() => setReply(ticket.ai_draft)} disabled={!!busy}>Undo edits</Button>
                  )}
                  <div className="ml-auto">
                    {confirmReject ? (
                      <span className="flex items-center gap-2 text-sm">
                        Reject this ticket?
                        <Button variant="danger" size="sm" loading={busy === "reject"} onClick={() => act("reject")}>Yes, reject</Button>
                        <Button variant="ghost" size="sm" onClick={() => setConfirmReject(false)}>Cancel</Button>
                      </span>
                    ) : (
                      <Button variant="danger" disabled={!!busy} onClick={() => setConfirmReject(true)}>
                        <X className="h-4 w-4" /> Reject
                      </Button>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <p className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-700">{ticket.final_reply || "–"}</p>
            )}
          </Card>

          <Card className="p-5">
            <h2 className="mb-3 flex items-center gap-2 font-semibold text-slate-900">
              <FileText className="h-4 w-4" /> Help-center sources the AI used
            </h2>
            {ticket.sources?.length ? (
              <ul className="space-y-2">
                {ticket.sources.map((s, i) => (
                  <li key={i} className="rounded-lg border border-slate-100 p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-slate-800">{s.title}{s.section ? ` › ${s.section}` : ""}</span>
                      <Badge tone={s.score >= 0.75 ? "green" : s.score >= 0.64 ? "amber" : "red"}>match {Math.round(s.score * 100)}%</Badge>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{s.snippet}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No sources (no relevant help-center article was found).</p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
