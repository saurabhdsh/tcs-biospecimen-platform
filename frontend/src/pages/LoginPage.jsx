import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../stores/auth";
import { Button, Input } from "../components/ui/primitives";

export default function LoginPage() {
  const login = useAuth((s) => s.login);
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-ink-950 lg:flex-row">
      <div className="flex min-h-[320px] flex-col justify-between border-r border-white/10 p-8 text-slate-200 lg:min-h-screen lg:w-[46%] lg:p-12">
        <img src="/TCS-logo-white.svg" alt="TCS" className="ml-3 h-12 w-auto max-w-[280px] object-contain object-left" />
        <div className="max-w-md">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-teal-400">TCS Life Sciences</div>
          <h1 className="mt-3 text-4xl font-semibold leading-tight text-white">Biospecimen Platform</h1>
          <p className="mt-4 text-sm leading-6 text-slate-400">
            Manage sample intake, accessioning, storage, custody, scientific lineage, and environmental exceptions in one operational workspace.
          </p>
          <div className="mt-8 text-xs text-slate-500">Authorized laboratory personnel only</div>
        </div>
      </div>
      <div className="flex flex-1 items-center justify-center bg-slate-50 p-8">
        <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4 rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">Sign in</div>
            <h2 className="mt-1 text-xl font-semibold text-ink-900">Sign in to the platform</h2>
          </div>
          {error && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</div>}
          <label className="block text-sm" htmlFor="email">
            <span className="mb-1 block text-slate-600">Email</span>
            <Input id="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
          </label>
          <label className="block text-sm" htmlFor="password">
            <span className="mb-1 block text-slate-600">Password</span>
            <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </label>
          <Button className="w-full justify-center" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </div>
  );
}
