import { useCallback, useEffect, useRef, useState } from "react";
import { FileUp, Search, Trash2 } from "lucide-react";

import { errorMessage } from "../../api/client";
import { kbApi } from "../../api/endpoints";
import { Badge, Button, Card, EmptyState, ErrorBox, inputClass, PageHeader, Spinner } from "../../components/ui";
import { timeAgo } from "../../utils/format";

const STATUS_TONE = { ready: "green", processing: "amber", failed: "red" };

function Uploader({ onUploaded }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const upload = async (file) => {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      await kbApi.upload(file);
      onUploaded();
    } catch (err) {
      setError(errorMessage(err, "Upload failed"));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); upload(e.dataTransfer.files?.[0]); }}
        className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
          dragging ? "border-brand-500 bg-brand-50" : "border-slate-300 bg-white"}`}
      >
        <FileUp className="mb-2 h-8 w-8 text-slate-400" />
        <p className="text-sm text-slate-600">Drag a help document here, or</p>
        <Button className="mt-3" variant="secondary" loading={busy} onClick={() => inputRef.current?.click()}>Choose file</Button>
        <p className="mt-2 text-xs text-slate-400">.md, .txt or .pdf · max 2 MB · indexed automatically (chunk → embed → pgvector)</p>
        <input ref={inputRef} type="file" accept=".md,.markdown,.txt,.pdf" className="hidden" onChange={(e) => upload(e.target.files?.[0])} />
      </div>
      <div className="mt-2"><ErrorBox message={error} /></div>
    </div>
  );
}

function SearchBox() {
  const [q, setQ] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async (e) => {
    e.preventDefault();
    if (q.trim().length < 2) return;
    setBusy(true);
    setError("");
    try {
      setResult(await kbApi.search(q.trim(), 3));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="p-5">
      <h2 className="font-semibold text-slate-900">Test retrieval</h2>
      <p className="mb-3 text-sm text-slate-500">See exactly which passages the AI would read for a question.</p>
      <form onSubmit={run} className="flex gap-2">
        <input className={inputClass} placeholder="e.g. refund kab aayega" value={q} onChange={(e) => setQ(e.target.value)} />
        <Button type="submit" loading={busy}><Search className="h-4 w-4" /> Search</Button>
      </form>
      <div className="mt-3"><ErrorBox message={error} /></div>
      {result && (
        <ul className="mt-4 space-y-2">
          {result.results.length === 0 && <li className="text-sm text-slate-500">No results.</li>}
          {result.results.map((r, i) => (
            <li key={i} className="rounded-lg border border-slate-100 p-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-slate-800">{r.title}{r.section ? ` › ${r.section}` : ""}</span>
                <Badge tone={r.score >= 0.75 ? "green" : r.score >= 0.64 ? "amber" : "red"}>{r.score.toFixed(3)}</Badge>
              </div>
              <p className="mt-1 line-clamp-3 text-xs text-slate-500">{r.content}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function KnowledgeBase() {
  const [docs, setDocs] = useState(null);
  const [error, setError] = useState("");
  const [confirmId, setConfirmId] = useState(null);

  const load = useCallback(() => {
    kbApi.list().then((d) => { setDocs(d); setError(""); }).catch((err) => setError(errorMessage(err)));
  }, []);
  useEffect(load, [load]);

  // poll while something is still being indexed
  useEffect(() => {
    if (!docs?.some((d) => d.status === "processing")) return undefined;
    const t = setInterval(load, 2500);
    return () => clearInterval(t);
  }, [docs, load]);

  const remove = async (id) => {
    try {
      await kbApi.remove(id);
      setConfirmId(null);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const totalChunks = docs?.reduce((n, d) => n + d.chunk_count, 0) ?? 0;

  return (
    <div>
      <PageHeader title="Knowledge base" subtitle={docs ? `${docs.length} documents · ${totalChunks} searchable chunks` : "Help documents the AI answers from"} />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Uploader onUploaded={load} />
          <ErrorBox message={error} onRetry={load} />
          {!docs && !error && <Spinner />}
          {docs?.length === 0 && <EmptyState title="No documents yet" text="Upload help-center articles so the AI can answer from them." />}
          {docs?.length > 0 && (
            <Card className="divide-y divide-slate-100">
              {docs.map((d) => (
                <div key={d.id} className="flex items-center gap-4 px-5 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium text-slate-900">{d.title}</div>
                    <div className="text-xs text-slate-500">
                      {d.filename} · {d.chunk_count} chunks · {timeAgo(d.created_at)}
                      {d.error && <span className="text-red-600"> · {d.error}</span>}
                    </div>
                  </div>
                  <Badge tone={STATUS_TONE[d.status]}>{d.status}</Badge>
                  {confirmId === d.id ? (
                    <span className="flex items-center gap-1">
                      <Button size="sm" variant="danger" onClick={() => remove(d.id)}>Delete</Button>
                      <Button size="sm" variant="ghost" onClick={() => setConfirmId(null)}>Cancel</Button>
                    </span>
                  ) : (
                    <button onClick={() => setConfirmId(d.id)} className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600" title="Delete">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </Card>
          )}
        </div>
        <div><SearchBox /></div>
      </div>
    </div>
  );
}
