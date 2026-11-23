import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { BarChart3, BookOpen, Inbox, ListChecks, LogOut, Menu, PlusCircle, Ticket, UserRound, X } from "lucide-react";

import { useAuth } from "../context/AuthContext";

const CUSTOMER_LINKS = [
  { to: "/tickets/new", label: "New request", icon: PlusCircle },
  { to: "/tickets", label: "My requests", icon: Ticket, end: true },
];
const STAFF_LINKS = [
  { to: "/staff/queue", label: "Review queue", icon: Inbox },
  { to: "/staff/tickets", label: "All tickets", icon: ListChecks },
  { to: "/staff/kb", label: "Knowledge base", icon: BookOpen },
  { to: "/staff/analytics", label: "Analytics", icon: BarChart3 },
];

export default function Layout() {
  const { user, isStaff, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const links = isStaff ? STAFF_LINKS : CUSTOMER_LINKS;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const linkClass = ({ isActive }) =>
    `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
    }`;

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4">
          <NavLink to="/" className="flex items-center gap-2">
            <span className="text-2xl">🧞</span>
            <span className="text-lg font-bold text-slate-900">
              Support<span className="text-brand-600">Genie</span>
            </span>
            {isStaff && <span className="hidden rounded bg-slate-900 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white sm:inline">Staff</span>}
          </NavLink>

          <nav className="hidden flex-1 items-center gap-1 md:flex">
            {links.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={linkClass}>
                <Icon className="h-4 w-4" /> {label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto hidden items-center gap-3 md:flex">
            <NavLink to="/account" className="rounded-lg px-2 py-1 text-right hover:bg-slate-100" title="Account & password">
              <div className="text-sm font-medium text-slate-800">{user?.name}</div>
              <div className="text-xs text-slate-500">{user?.email}</div>
            </NavLink>
            <button onClick={handleLogout} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800" title="Log out">
              <LogOut className="h-5 w-5" />
            </button>
          </div>

          <button className="ml-auto rounded-lg p-2 text-slate-600 md:hidden" onClick={() => setOpen((o) => !o)} aria-label="Menu">
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {open && (
          <div className="border-t border-slate-200 bg-white px-4 py-3 md:hidden">
            {links.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={linkClass} onClick={() => setOpen(false)}>
                <Icon className="h-4 w-4" /> {label}
              </NavLink>
            ))}
            <NavLink to="/account" className={linkClass} onClick={() => setOpen(false)}>
              <UserRound className="h-4 w-4" /> Account
            </NavLink>
            <button onClick={handleLogout} className="mt-2 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100">
              <LogOut className="h-4 w-4" /> Log out ({user?.name})
            </button>
          </div>
        )}
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
