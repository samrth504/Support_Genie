import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { errorMessage } from "../api/client";
import { Button, ErrorBox, Field, inputClass } from "../components/ui";
import { homeFor, useAuth } from "../context/AuthContext";
import AuthLayout from "./AuthLayout";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to={homeFor(user)} replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const me = await login(form.email.trim(), form.password);
      const from = location.state?.from;
      navigate(from && !from.startsWith("/login") ? from : homeFor(me), { replace: true });
    } catch (err) {
      setError(errorMessage(err, "Login failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Welcome back" subtitle="Log in to get help with your ShopNest orders.">
      <form onSubmit={onSubmit} className="space-y-4">
        <ErrorBox message={error} />
        <Field label="Email">
          <input type="email" required autoComplete="email" className={inputClass} placeholder="you@example.com"
            value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Password">
          <input type="password" required autoComplete="current-password" className={inputClass}
            value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </Field>
        <Button type="submit" className="w-full" size="lg" loading={loading}>Log in</Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        New to ShopNest?{" "}
        <Link to="/signup" className="font-medium text-brand-600 hover:underline">Create an account</Link>
      </p>

      <div className="mt-8 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
        <span className="font-semibold text-slate-600">Demo customer:</span>{" "}
        <button type="button" className="font-mono text-brand-600 hover:underline"
          onClick={() => setForm({ email: "rahul.demo@shopnest.com", password: "Demo12345" })}>
          rahul.demo@shopnest.com / Demo12345
        </button>
      </div>
    </AuthLayout>
  );
}
