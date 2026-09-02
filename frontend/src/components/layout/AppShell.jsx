import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Activity,
  Boxes,
  ClipboardList,
  FileSearch,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  LogOut,
  PackageSearch,
  Search,
  ShieldAlert,
  SlidersHorizontal,
  Truck,
  Upload,
} from "lucide-react";
import { PlatformAPI } from "../../api/client";
import { useAuth } from "../../stores/auth";
import { useToast } from "../../stores/toast";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/intake", label: "Intake", icon: Upload },
  { to: "/accession", label: "Accession", icon: ClipboardList },
  { to: "/shipments", label: "Shipments", icon: Truck },
  { to: "/samples", label: "Samples", icon: FlaskConical },
  { to: "/inventory", label: "Inventory", icon: Boxes },
  { to: "/lineage", label: "Lineage", icon: GitBranch },
  { to: "/exceptions", label: "Exceptions", icon: ShieldAlert },
  { to: "/reports", label: "Reports", icon: FileSearch },
  { to: "/traceability", label: "Traceability", icon: Activity },
  { to: "/api-explorer", label: "APIs", icon: PackageSearch },
  { to: "/admin", label: "Administration", icon: SlidersHorizontal, admin: true },
];

export default function AppShell() {
  const { user, logout, isAdmin } = useAuth();
  const toasts = useToast((s) => s.items);
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState([]);

  useEffect(() => {
    if (q.length < 2) {
      setHits([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        setHits(await PlatformAPI.search(q));
      } catch {
        setHits([]);
      }
    }, 180);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col bg-ink-950 text-slate-200">
        <div className="border-b border-white/10 px-5 py-5 pl-7">
          <img src="/TCS-logo-white.svg" alt="TCS" className="h-8 w-auto max-w-[188px] object-contain object-left" />
        </div>
        <nav className="flex-1 space-y-0.5 p-3">
          {NAV.filter((n) => !n.admin || isAdmin()).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-md px-3 py-2 text-[13px] ${
                  isActive ? "bg-white/10 text-white" : "text-slate-300 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <item.icon size={16} />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-slate-200 bg-white px-6 py-3">
          <div className="relative w-full max-w-xl">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search sample ID, barcode, shipment…"
              className="w-full rounded-md border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-sm outline-none focus:bg-white focus:ring-2 focus:ring-teal-600/30"
            />
            {hits.length > 0 && (
              <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg">
                {hits.map((h) => (
                  <button
                    key={`${h.kind}-${h.id}`}
                    className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50"
                    onClick={() => {
                      setQ("");
                      setHits([]);
                      navigate(h.kind === "sample" ? `/samples/${h.id}` : `/shipments/${h.id}`);
                    }}
                  >
                    <span>
                      <span className="mono font-medium">{h.label}</span>
                      <span className="ml-2 text-slate-500">{h.subtitle}</span>
                    </span>
                    <span className="text-[11px] uppercase text-slate-400">{h.kind}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div className="text-right">
              <div className="font-medium text-ink-900">{user?.full_name}</div>
              <div className="text-[11px] uppercase tracking-wide text-slate-500">{user?.roles?.join(" · ")}</div>
            </div>
            <button
              onClick={() => {
                logout();
                navigate("/login");
              }}
              className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
              title="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 space-y-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto rounded-md px-4 py-3 text-sm shadow-lg ${
              t.tone === "error" ? "bg-rose-700 text-white" : "bg-ink-900 text-white"
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </div>
  );
}
