import { useState } from "react";
import { KeyRound } from "lucide-react";

import { errorMessage } from "../api/client";
import { authApi } from "../api/endpoints";
import { Badge, Button, Card, ErrorBox, Field, inputClass, PageHeader } from "../components/ui";
import { useAuth } from "../context/AuthContext";

const EMPTY = { current: "", next: "", repeat: "" };

export default function Account() {
  const { user } = useAuth();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setDone(false);
    if (form.next.length < 8 || !/[a-zA-Z]/.test(form.next) || !/\d/.test(form.next)) {
      return setError("New password needs 8+ characters with a letter and a number.");
    }
    if (form.next !== form.repeat) return setError("The two new passwords do not match.");
    setError("");
    setBusy(true);
    try {
      await authApi.changePassword(form.current, form.next);
      setForm(EMPTY);
      setDone(true);
    } catch (err) {
      setError(errorMessage(err, "Could not change the password"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg">
      <PageHeader title="Account" subtitle="Your profile and password." />
      <Card className="mb-6 p-5">
        <div className="text-sm text-slate-500">Signed in as</div>
        <div className="mt-1 flex items-center gap-2">
          <span className="font-semibold text-slate-900">{user?.name}</span>
          <Badge tone={user?.role === "staff" ? "brand" : "slate"}>{user?.role}</Badge>
        </div>
        <div className="text-sm text-slate-600">{user?.email}</div>
      </Card>

      <Card className="p-5">
        <h2 className="mb-4 flex items-center gap-2 font-semibold text-slate-900">
          <KeyRound className="h-4 w-4" /> Change password
        </h2>
        <form onSubmit={onSubmit} className="space-y-4">
          <ErrorBox message={error} />
          {done && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
              Password changed. Use the new password next time you log in.
            </div>
          )}
          <Field label="Current password">
            <input type="password" required autoComplete="current-password" className={inputClass}
              value={form.current} onChange={(e) => setForm({ ...form, current: e.target.value })} />
          </Field>
          <Field label="New password" hint="At least 8 characters, with a letter and a number.">
            <input type="password" required autoComplete="new-password" className={inputClass}
              value={form.next} onChange={(e) => setForm({ ...form, next: e.target.value })} />
          </Field>
          <Field label="Repeat new password">
            <input type="password" required autoComplete="new-password" className={inputClass}
              value={form.repeat} onChange={(e) => setForm({ ...form, repeat: e.target.value })} />
          </Field>
          <Button type="submit" loading={busy}>Update password</Button>
        </form>
        <p className="mt-4 text-xs text-slate-500">
          Forgot your password? Ask ShopNest support - staff can reset it for you.
        </p>
      </Card>
    </div>
  );
}
