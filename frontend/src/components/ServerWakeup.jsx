/**
 * Free hosting (Render) puts the backend to sleep after 15 min idle; waking takes ~1 minute.
 * Instead of a broken page, we ping /health first and show a friendly "waking up" screen.
 */
import { useEffect, useState } from "react";
import { Loader2, ServerCrash } from "lucide-react";

import { healthApi } from "../api/endpoints";
import { Button } from "./ui";

const SLOW_AFTER_MS = 1500;
const MAX_ATTEMPTS = 20;

export default function ServerWakeup({ children }) {
  const [state, setState] = useState("checking"); // checking | slow | ready | down
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const slowTimer = setTimeout(() => !cancelled && setState((s) => (s === "checking" ? "slow" : s)), SLOW_AFTER_MS);

    const ping = async (n) => {
      try {
        await healthApi.check();
        if (!cancelled) setState("ready");
      } catch {
        if (cancelled) return;
        if (n + 1 >= MAX_ATTEMPTS) return setState("down");
        setAttempt(n + 1);
        setTimeout(() => ping(n + 1), 4000);
      }
    };
    ping(0);
    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
    };
  }, []);

  if (state === "ready") return children;
  if (state === "checking") return <div className="h-full bg-slate-50" />;

  return (
    <div className="flex h-full items-center justify-center bg-gradient-to-br from-brand-50 to-white p-6">
      <div className="max-w-md text-center">
        <div className="mb-4 text-5xl">🧞</div>
        {state === "slow" ? (
          <>
            <h1 className="text-xl font-semibold text-slate-900">Waking up the server…</h1>
            <p className="mt-2 text-sm text-slate-600">
              SupportGenie runs on free hosting that sleeps when idle. The first visit can take up to a minute.
            </p>
            <Loader2 className="mx-auto mt-6 h-8 w-8 animate-spin text-brand-600" />
            {attempt > 0 && <p className="mt-3 text-xs text-slate-400">Still trying… (attempt {attempt + 1})</p>}
          </>
        ) : (
          <>
            <ServerCrash className="mx-auto h-10 w-10 text-red-500" />
            <h1 className="mt-3 text-xl font-semibold text-slate-900">Server is not reachable</h1>
            <p className="mt-2 text-sm text-slate-600">Please check that the backend is running, then try again.</p>
            <Button className="mt-6" onClick={() => window.location.reload()}>
              Try again
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
