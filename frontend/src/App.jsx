import { Link, Navigate, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { Spinner } from "./components/ui";
import { homeFor, useAuth } from "./context/AuthContext";
import Account from "./pages/Account";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import MyTickets from "./pages/customer/MyTickets";
import NewTicket from "./pages/customer/NewTicket";
import TicketDetail from "./pages/customer/TicketDetail";
import Analytics from "./pages/staff/Analytics";
import KnowledgeBase from "./pages/staff/KnowledgeBase";
import ReviewDetail from "./pages/staff/ReviewDetail";
import TicketList from "./pages/staff/TicketList";

function Home() {
  const { user, checking } = useAuth();
  if (checking) return <Spinner />;
  return <Navigate to={user ? homeFor(user) : "/login"} replace />;
}

function NotFound() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
      <div className="text-5xl">🧞</div>
      <h1 className="text-xl font-semibold">Page not found</h1>
      <Link to="/" className="text-brand-600 hover:underline">Go home</Link>
    </div>
  );
}

const customer = (el) => <ProtectedRoute role="customer">{el}</ProtectedRoute>;
const staff = (el) => <ProtectedRoute role="staff">{el}</ProtectedRoute>;

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/account" element={<Account />} />
        <Route path="/tickets" element={customer(<MyTickets />)} />
        <Route path="/tickets/new" element={customer(<NewTicket />)} />
        <Route path="/tickets/:id" element={customer(<TicketDetail />)} />

        <Route path="/staff/queue" element={staff(<TicketList mode="queue" />)} />
        <Route path="/staff/tickets" element={staff(<TicketList mode="all" />)} />
        <Route path="/staff/review/:id" element={staff(<ReviewDetail />)} />
        <Route path="/staff/kb" element={staff(<KnowledgeBase />)} />
        <Route path="/staff/analytics" element={staff(<Analytics />)} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
