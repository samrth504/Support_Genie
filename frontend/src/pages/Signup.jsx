import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { errorMessage } from "../api/client";
import { Button, ErrorBox, Field, inputClass } from "../components/ui";
import { homeFor, useAuth } from "../context/AuthContext";
import AuthLayout from "./AuthLayout";

// Same rules as the backend (it re-checks them anyway)
function validate({ name, password }) {
  if (name.trim().length < 2) return "Please enter your name.";
  if (password.length < 8 || password.length > 72) return "Password must be 8-72 characters.";
  if (!/[a-zA-Z]/.test(password) || !/\d/.test(password)) return "Password needs at least one letter and one number.";
  return "";
}

export default function Signup() {
  const { user, signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to={homeFor(user)} replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    const problem = validate(form);
    if (problem) return setError(problem);
    setError("");
    setLoading(true);
    try {
      await signup({ name: form.name.trim(), email: form.email.trim(), password: form.password });
      navigate("/tickets/new", { replace: true });
    } catch (err) {
      setError(errorMessage(err, "Sign-up failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Create your account" subtitle="Get answers about orders, refunds, payments and more.">
      <form onSubmit={onSubmit} className="space-y-4">
        <ErrorBox message={error} />
        <Field label="Full name">
          <input required autoComplete="name" className={inputClass} placeholder="Rahul Verma"
            value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Email">
          <input type="email" required autoComplete="email" className={inputClass} placeholder="you@example.com"
            value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Password" hint="At least 8 characters, with a letter and a number.">
          <input type="password" required autoComplete="new-password" className={inputClass}
            value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </Field>
        <Button type="submit" className="w-full" size="lg" loading={loading}>Create account</Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-brand-600 hover:underline">Log in</Link>
      </p>
    </AuthLayout>
  );
}
