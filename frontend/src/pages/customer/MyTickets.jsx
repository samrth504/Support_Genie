import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, MessageSquarePlus } from "lucide-react";

import { errorMessage } from "../../api/client";
import { ticketsApi } from "../../api/endpoints";
import { Button, Card, EmptyState, ErrorBox, PageHeader, Spinner, StatusBadge } from "../../components/ui";
import { timeAgo } from "../../utils/format";

export default function MyTickets() {
  const [tickets, setTickets] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setError("");
    ticketsApi.list().then(setTickets).catch((err) => setError(errorMessage(err)));
  }, []);
  useEffect(load, [load]);

  const newButton = (
    <Link to="/tickets/new"><Button><MessageSquarePlus className="h-4 w-4" /> New request</Button></Link>
  );

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="My requests" subtitle="All your questions and their answers." actions={newButton} />
      <ErrorBox message={error} onRetry={load} />
      {!tickets && !error && <Spinner />}
      {tickets?.length === 0 && (
        <EmptyState title="No requests yet" text="Ask anything about orders, refunds, delivery or your account." action={newButton} />
      )}
      {tickets?.length > 0 && (
        <Card className="divide-y divide-slate-100">
          {tickets.map((t) => (
            <Link key={t.id} to={`/tickets/${t.id}`} className="flex items-center gap-4 px-5 py-4 transition-colors hover:bg-slate-50">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate font-medium text-slate-900">{t.subject}</span>
                  <StatusBadge status={t.status} />
                </div>
                <p className="mt-0.5 truncate text-sm text-slate-500">{t.reply || t.body}</p>
              </div>
              <span className="shrink-0 text-xs text-slate-400">{timeAgo(t.created_at)}</span>
              <ChevronRight className="h-4 w-4 shrink-0 text-slate-300" />
            </Link>
          ))}
        </Card>
      )}
    </div>
  );
}
