/** Staff ticket lists: the review queue (pending, most urgent first) and "all tickets" with a status filter. */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, RefreshCw, ShieldAlert } from "lucide-react";

import { errorMessage } from "../../api/client";
import { reviewApi } from "../../api/endpoints";
import {
  Badge, Button, Card, ConfidenceBar, EmptyState, ErrorBox, PageHeader, PriorityBadge, Spinner, StatusBadge,
} from "../../components/ui";
import { humanize, timeAgo } from "../../utils/format";

const REFRESH_MS = 15000;
const FILTERS = ["", "pending_review", "ai_resolved", "agent_resolved", "rejected"];

export function ReasonChips({ reasons }) {
  if (!reasons?.length) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {reasons.map((r) => (
        <Badge key={r} tone={r.startsWith("prompt_injection") || r.startsWith("money") ? "red" : "amber"}>
          {humanize(r.replace(/_\d\.\d+_below_\d\.\d+$/, ""))}
        </Badge>
      ))}
    </div>
  );
}

function TicketTable({ tickets }) {
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-100 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">Ticket</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">AI confidence</th>
              <th className="px-4 py-3">Why escalated / status</th>
              <th className="px-4 py-3 text-right">Age</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {tickets.map((t) => (
              <tr key={t.id} className="hover:bg-slate-50">
                <td className="px-4 py-3"><PriorityBadge priority={t.priority} /></td>
                <td className="max-w-xs px-4 py-3">
                  <Link to={`/staff/review/${t.id}`} className="font-medium text-slate-900 hover:text-brand-600">
                    {t.injection_flag && <ShieldAlert className="mr-1 inline h-4 w-4 text-red-500" />}
                    {t.subject}
                  </Link>
                  <div className="text-xs text-slate-500">#{t.id} · {t.customer_name}</div>
                </td>
                <td className="px-4 py-3 text-slate-600">{t.category || "–"}</td>
                <td className="px-4 py-3"><ConfidenceBar value={t.confidence} /></td>
                <td className="px-4 py-3">
                  {t.status === "pending_review" ? <ReasonChips reasons={t.review_reasons} /> : <StatusBadge status={t.status} staff />}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-right text-xs text-slate-400">{timeAgo(t.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export default function TicketList({ mode = "queue" }) {
  const [tickets, setTickets] = useState(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const isQueue = mode === "queue";

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      setTickets(isQueue ? await reviewApi.queue() : await reviewApi.all(status));
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRefreshing(false);
    }
  }, [isQueue, status]);

  useEffect(() => {
    setTickets(null);
    load();
    if (!isQueue) return undefined;
    const t = setInterval(load, REFRESH_MS);
    return () => clearInterval(t);
  }, [load, isQueue]);

  return (
    <div>
      <PageHeader
        title={isQueue ? "Review queue" : "All tickets"}
        subtitle={isQueue
          ? "Tickets the AI escalated to a human - most urgent first. Refreshes every 15 s."
          : "Every ticket and how it was handled."}
        actions={<Button variant="secondary" onClick={load} loading={refreshing}><RefreshCw className="h-4 w-4" /> Refresh</Button>}
      />

      {!isQueue && (
        <div className="mb-4 flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button key={f || "all"} onClick={() => setStatus(f)}
              className={`rounded-full px-3 py-1 text-sm ${status === f ? "bg-slate-900 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"}`}>
              {f ? humanize(f) : "All"}
            </button>
          ))}
        </div>
      )}

      <ErrorBox message={error} onRetry={load} />
      {!tickets && !error && <Spinner />}
      {tickets?.length === 0 && (
        <EmptyState icon={CheckCircle2} title={isQueue ? "Queue is empty 🎉" : "No tickets"}
          text={isQueue ? "The AI handled everything, or the team has reviewed all escalations." : "Nothing matches this filter."} />
      )}
      {tickets?.length > 0 && (
        <>
          {isQueue && <p className="mb-3 text-sm text-slate-500">{tickets.length} ticket{tickets.length > 1 ? "s" : ""} waiting</p>}
          <TicketTable tickets={tickets} />
        </>
      )}
    </div>
  );
}
