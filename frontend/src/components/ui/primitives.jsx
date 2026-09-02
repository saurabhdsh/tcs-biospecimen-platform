export function StatusBadge({ status }) {
  const map = {
    RECEIVED: "bg-sky-50 text-sky-800 ring-sky-200",
    ACCESSIONED: "bg-indigo-50 text-indigo-800 ring-indigo-200",
    IN_STORAGE: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    CHECKED_OUT: "bg-amber-50 text-amber-800 ring-amber-200",
    QUARANTINED: "bg-rose-50 text-rose-800 ring-rose-200",
    RELEASED: "bg-teal-50 text-teal-800 ring-teal-200",
    DISPOSED: "bg-slate-100 text-slate-600 ring-slate-200",
    OPEN: "bg-rose-50 text-rose-800 ring-rose-200",
    UNDER_REVIEW: "bg-amber-50 text-amber-800 ring-amber-200",
    RESOLVED: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    CLOSED: "bg-slate-100 text-slate-600 ring-slate-200",
    VALIDATED: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    VALIDATION_FAILED: "bg-rose-50 text-rose-800 ring-rose-200",
    COMMITTED: "bg-teal-50 text-teal-800 ring-teal-200",
    UPLOADED: "bg-sky-50 text-sky-800 ring-sky-200",
    ACCESSIONING: "bg-indigo-50 text-indigo-800 ring-indigo-200",
    COMPLETE: "bg-teal-50 text-teal-800 ring-teal-200",
    PASS: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    FAIL: "bg-rose-50 text-rose-800 ring-rose-200",
    ACTIVE: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    INACTIVE: "bg-slate-100 text-slate-600 ring-slate-200",
  };
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold tracking-wide ring-1 ${map[status] || "bg-slate-50 text-slate-700 ring-slate-200"}`}>
      {status}
    </span>
  );
}

export function PageHeader({ kicker, title, description, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {kicker && <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">{kicker}</div>}
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900">{title}</h1>
        {description && <p className="mt-1 max-w-3xl text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ children, className = "", ...props }) {
  return (
    <div className={`rounded-md border border-slate-200 bg-white shadow-sm ${className}`} {...props}>
      {children}
    </div>
  );
}

export function Button({ children, variant = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-ink-900 text-white hover:bg-ink-800",
    accent: "bg-accent-600 text-white hover:bg-accent-500",
    ghost: "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50",
    danger: "bg-rose-700 text-white hover:bg-rose-600",
  };
  return (
    <button
      className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Input({ className = "", ...props }) {
  return (
    <input
      className={`w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-teal-600/30 focus:ring-2 ${className}`}
      {...props}
    />
  );
}

export function Select({ children, ...props }) {
  return (
    <select
      className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-teal-600/30 focus:ring-2"
      {...props}
    >
      {children}
    </select>
  );
}

export function Skeleton({ className = "h-8" }) {
  return <div className={`animate-pulse rounded bg-slate-200 ${className}`} />;
}

export function Empty({ title, body }) {
  return (
    <div className="px-6 py-16 text-center">
      <div className="text-sm font-medium text-slate-700">{title}</div>
      <div className="mt-1 text-sm text-slate-500">{body}</div>
    </div>
  );
}
