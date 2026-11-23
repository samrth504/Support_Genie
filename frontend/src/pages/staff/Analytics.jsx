import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, Clock, Inbox, Lightbulb, Smile, Ticket, TrendingUp } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

import { errorMessage } from "../../api/client";
import { analyticsApi } from "../../api/endpoints";
import { Badge, Card, ErrorBox, PageHeader, Spinner } from "../../components/ui";
import { duration, humanize, pct, timeAgo } from "../../utils/format";

const BRAND = "#4f46e5";
const STATUS_COLORS = { ai_resolved: "#10b981", agent_resolved: "#3b82f6", pending_review: "#f59e0b", rejected: "#ef4444", open: "#94a3b8" };

function Kpi({ icon: Icon, label, value, sub, tone = "brand" }) {
  const tones = { brand: "bg-brand-50 text-brand-600", green: "bg-emerald-50 text-emerald-600", amber: "bg-amber-50 text-amber-600", blue: "bg-blue-50 text-blue-600" };
  return (
    <Card className="p-5">
      <div className="flex items-center gap-3">
        <span className={`rounded-lg p-2 ${tones[tone]}`}><Icon className="h-5 w-5" /></span>
        <span className="text-sm text-slate-500">{label}</span>
      </div>
      <div className="mt-3 text-3xl font-bold tracking-tight text-slate-900">{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </Card>
  );
}

function ChartCard({ title, children }) {
  return (
    <Card className="p-5">
      <h2 className="mb-4 font-semibold text-slate-900">{title}</h2>
      <div className="h-64">{children}</div>
    </Card>
  );
}

function Trends({ trends }) {
  if (!trends) return null;
  return (
    <Card className="p-5">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-semibold text-slate-900"><TrendingUp className="h-4 w-4" /> Trending issues</h2>
        {trends.k > 0 && (
          <span className="text-xs text-slate-400">
            K-means · {trends.tickets_analysed} tickets · K={trends.k} (best silhouette {trends.silhouette} in range 4-8)
          </span>
        )}
      </div>
      <p className="mb-4 text-sm text-slate-500">Similar tickets from the last {trends.days} days, grouped automatically.</p>
      {trends.clusters.length === 0 ? (
        <p className="text-sm text-slate-500">{trends.message}</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {trends.clusters.map((c) => (
            <div key={c.cluster_id} className="rounded-xl border border-slate-200 p-4">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold text-slate-900">{c.label}</h3>
                <span className="text-sm font-semibold text-brand-600">{c.size}</span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-brand-500" style={{ width: `${Math.max(4, c.share * 100)}%` }} />
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {pct(c.share)} of tickets{c.top_category ? ` · mostly ${c.top_category}` : ""}
                {c.pending_review > 0 && <span className="text-amber-600"> · {c.pending_review} waiting</span>}
              </div>
              <div className="mt-3 flex flex-wrap gap-1">
                {c.keywords.map((k) => <Badge key={k}>{k}</Badge>)}
              </div>
              {c.examples?.length > 0 && <p className="mt-2 truncate text-xs text-slate-400">e.g. “{c.examples[0]}”</p>}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function Gaps({ gaps }) {
  return (
    <Card className="p-5">
      <h2 className="mb-1 flex items-center gap-2 font-semibold text-slate-900"><Lightbulb className="h-4 w-4" /> Knowledge gaps</h2>
      <p className="mb-4 text-sm text-slate-500">Questions the help center could not answer - write these docs next.</p>
      {gaps.length === 0 ? (
        <p className="text-sm text-slate-500">No gaps found 🎉</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {gaps.slice(0, 10).map((g) => (
            <li key={g.id} className="flex items-center gap-3 py-2.5 text-sm">
              <div className="min-w-0 flex-1">
                {g.ticket_id ? (
                  <Link to={`/staff/review/${g.ticket_id}`} className="font-medium text-slate-800 hover:text-brand-600">{g.subject || g.query}</Link>
                ) : (
                  <span className="font-medium text-slate-800">{g.query}</span>
                )}
                <div className="truncate text-xs text-slate-500">{g.query}</div>
              </div>
              {g.top_score != null && <Badge tone="red">best match {Math.round(g.top_score * 100)}%</Badge>}
              <span className="text-xs text-slate-400">{timeAgo(g.created_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function Analytics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setError("");
    Promise.all([analyticsApi.summary(14), analyticsApi.trends(30), analyticsApi.gaps(20)])
      .then(([summary, trends, gaps]) => setData({ summary, trends, gaps }))
      .catch((err) => setError(errorMessage(err)));
  }, []);
  useEffect(load, [load]);

  if (error) return <ErrorBox message={error} onRetry={load} />;
  if (!data) return <Spinner label="Crunching the numbers…" />;

  const { summary: s, trends, gaps } = data;
  const speedup = s.avg_ai_response_seconds && s.avg_agent_response_seconds
    ? Math.round(s.avg_agent_response_seconds / s.avg_ai_response_seconds) : null;
  const statusData = Object.entries(s.by_status).filter(([, n]) => n > 0).map(([status, count]) => ({ status: humanize(status), key: status, count }));
  const perDay = s.tickets_per_day.map((d) => ({ ...d, label: d.date.slice(5) }));

  return (
    <div className="space-y-6">
      <PageHeader title="Analytics" subtitle="How SupportGenie is performing." />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi icon={Bot} label="Resolved by AI" value={pct(s.auto_resolution_rate)} sub={`${s.by_status.ai_resolved} of ${s.total_tickets} tickets`} />
        <Kpi icon={Clock} tone="blue" label="Avg AI response" value={duration(s.avg_ai_response_seconds)}
          sub={speedup ? `${speedup}× faster than agents (${duration(s.avg_agent_response_seconds)})` : `Agents: ${duration(s.avg_agent_response_seconds)}`} />
        <Kpi icon={Smile} tone="green" label="Customer satisfaction" value={pct(s.feedback.satisfaction_rate)}
          sub={`👍 ${s.feedback.positive} · 👎 ${s.feedback.negative}`} />
        <Kpi icon={Inbox} tone="amber" label="Waiting for review" value={s.pending_review}
          sub={<Link to="/staff/queue" className="text-brand-600 hover:underline">Open queue →</Link>} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Tickets per day (last 14 days)">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={perDay} margin={{ left: -20, right: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <Tooltip />
              <Line type="monotone" dataKey="count" name="Tickets" stroke={BRAND} strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="How tickets were handled">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={statusData} margin={{ left: -20, right: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="status" tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <Tooltip />
              <Bar dataKey="count" name="Tickets" radius={[6, 6, 0, 0]}>
                {statusData.map((d) => <Cell key={d.key} fill={STATUS_COLORS[d.key] || BRAND} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <ChartCard title="Tickets by category (ML classifier)">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={s.by_category} layout="vertical" margin={{ left: 30, right: 16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} stroke="#94a3b8" />
            <YAxis type="category" dataKey="category" tick={{ fontSize: 11 }} width={100} stroke="#94a3b8" />
            <Tooltip />
            <Bar dataKey="count" name="Tickets" fill={BRAND} radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <Trends trends={trends} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2"><Gaps gaps={gaps} /></div>
        <Card className="p-5">
          <h2 className="mb-3 flex items-center gap-2 font-semibold text-slate-900"><Ticket className="h-4 w-4" /> Knowledge base</h2>
          <div className="text-3xl font-bold text-slate-900">{s.knowledge_base.documents}</div>
          <div className="text-sm text-slate-500">documents · {s.knowledge_base.chunks} chunks</div>
          <div className="mt-4 text-sm text-slate-500">Avg AI confidence</div>
          <div className="text-2xl font-semibold text-slate-900">{pct(s.avg_confidence)}</div>
          <Link to="/staff/kb" className="mt-4 inline-block text-sm text-brand-600 hover:underline">Manage documents →</Link>
        </Card>
      </div>
    </div>
  );
}
