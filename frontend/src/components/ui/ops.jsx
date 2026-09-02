export function WorkflowSteps({ steps, current }) {
  return (
    <ol className="mb-6 grid gap-3 md:grid-cols-3">
      {steps.map((step, i) => {
        const active = i === current;
        const done = i < current;
        return (
          <li
            key={step.title}
            className={`rounded-xl border p-4 ${
              active ? "border-teal-600 bg-white shadow-sm" : done ? "border-emerald-200 bg-emerald-50/60" : "border-slate-200 bg-white"
            }`}
          >
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-teal-700">
              {done ? "Complete" : `Step ${i + 1}`}
            </div>
            <div className="mt-1 text-sm font-semibold text-ink-900">{step.title}</div>
            <p className="mt-1 text-xs leading-5 text-slate-500">{step.body}</p>
          </li>
        );
      })}
    </ol>
  );
}

export function Field({ label, value, mono }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2.5">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 break-all text-sm font-medium text-ink-900 ${mono ? "mono" : ""}`}>{value || "—"}</div>
    </div>
  );
}

export function FieldGrid({ items, cols = "md:grid-cols-2 xl:grid-cols-3" }) {
  return (
    <div className={`grid grid-cols-1 gap-2 ${cols}`}>
      {items.map(([label, value, mono]) => (
        <Field key={label} label={label} value={value} mono={mono} />
      ))}
    </div>
  );
}
