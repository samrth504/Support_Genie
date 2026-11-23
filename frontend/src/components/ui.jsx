/** Small, reusable UI building blocks (Tailwind). */
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";

const cx = (...classes) => classes.filter(Boolean).join(" ");

export function Button({ variant = "primary", size = "md", loading = false, disabled = false, className, children, ...props }) {
  const variants = {
    primary: "bg-brand-600 text-white hover:bg-brand-700 shadow-sm",
    secondary: "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50",
    danger: "bg-white text-red-600 border border-red-200 hover:bg-red-50",
    success: "bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm",
    ghost: "text-slate-600 hover:bg-slate-100",
  };
  const sizes = { sm: "px-3 py-1.5 text-sm", md: "px-4 py-2 text-sm", lg: "px-5 py-2.5 text-base" };
  return (
    <button
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
      disabled={loading || disabled}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Card({ className, children, ...props }) {
  return (
    <div className={cx("rounded-xl border border-slate-200 bg-white shadow-sm", className)} {...props}>
      {children}
    </div>
  );
}

export function Field({ label, hint, error, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      {children}
      {error ? (
        <span className="mt-1 block text-xs text-red-600">{error}</span>
      ) : (
        hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>
      )}
    </label>
  );
}

export const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100";

export function Badge({ tone = "slate", className, children }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
    blue: "bg-blue-50 text-blue-700 ring-1 ring-blue-200",
    amber: "bg-amber-50 text-amber-800 ring-1 ring-amber-200",
    red: "bg-red-50 text-red-700 ring-1 ring-red-200",
    brand: "bg-brand-50 text-brand-700 ring-1 ring-brand-200",
  };
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium", tones[tone], className)}>
      {children}
    </span>
  );
}

const CUSTOMER_STATUS = {
  open: ["Processing", "slate"],
  ai_resolved: ["Answered", "green"],
  pending_review: ["With a specialist", "amber"],
  agent_resolved: ["Answered", "blue"],
  rejected: ["Closed", "slate"],
};
const STAFF_STATUS = {
  open: ["Open", "slate"],
  ai_resolved: ["AI resolved", "green"],
  pending_review: ["Pending review", "amber"],
  agent_resolved: ["Agent resolved", "blue"],
  rejected: ["Rejected", "red"],
};

export function StatusBadge({ status, staff = false }) {
  const [label, tone] = (staff ? STAFF_STATUS : CUSTOMER_STATUS)[status] || [status, "slate"];
  return <Badge tone={tone}>{label}</Badge>;
}

export function PriorityBadge({ priority }) {
  const tone = { high: "red", medium: "amber", low: "slate" }[priority] || "slate";
  return <Badge tone={tone}>{priority?.toUpperCase()}</Badge>;
}

export function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <Loader2 className="h-5 w-5 animate-spin text-brand-600" /> {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">{message}</div>
      {onRetry && (
        <button className="font-medium underline" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ icon: Icon = Inbox, title, text, action }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
      <Icon className="mb-3 h-10 w-10 text-slate-300" />
      <h3 className="font-semibold text-slate-700">{title}</h3>
      {text && <p className="mt-1 max-w-sm text-sm text-slate-500">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function ConfidenceBar({ value }) {
  if (value === null || value === undefined) return <span className="text-sm text-slate-400">–</span>;
  const pctValue = Math.round(value * 100);
  const color = value >= 0.8 ? "bg-emerald-500" : value >= 0.7 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-200">
        <div className={cx("h-full rounded-full", color)} style={{ width: `${pctValue}%` }} />
      </div>
      <span className="text-sm font-medium tabular-nums text-slate-700">{pctValue}%</span>
    </div>
  );
}
