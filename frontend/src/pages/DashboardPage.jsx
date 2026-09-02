import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PlatformAPI } from "../api/client";
import { Card, PageHeader, Skeleton, StatusBadge } from "../components/ui/primitives";

export default function DashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: PlatformAPI.dashboard });
  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    );
  }
  const kpis = [
    ["Total samples", data.total_samples],
    ["Received", data.received],
    ["Accessioned", data.accessioned],
    ["In storage", data.in_storage],
    ["Checked out", data.checked_out],
    ["Quarantined", data.quarantined],
    ["Open exceptions", data.open_exceptions],
    ["Shipments", data.shipments],
  ];
  return (
    <div>
      <PageHeader kicker="Operations" title="Overview" description="Current inventory, exceptions, and recent laboratory activity." />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {kpis.map(([label, value]) => (
          <Card key={label} className="p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
            <div className="mt-2 text-3xl font-semibold tabular-nums text-ink-900">{value}</div>
          </Card>
        ))}
      </div>
      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="p-4">
          <div className="mb-3 text-sm font-semibold">Samples by status</div>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={data.samples_by_status}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="status" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#0b7c6e" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="p-4">
          <div className="mb-3 text-sm font-semibold">Storage occupancy</div>
          <div className="grid grid-cols-3 gap-3 text-center">
            {["total_positions", "occupied", "available"].map((k) => (
              <div key={k} className="rounded-md bg-slate-50 p-4">
                <div className="text-[11px] uppercase text-slate-500">{k.replace("_", " ")}</div>
                <div className="mt-1 text-2xl font-semibold">{data.storage_occupancy[k]}</div>
              </div>
            ))}
          </div>
          <div className="mt-6 text-sm font-semibold">Recent activity</div>
          <div className="mt-2 max-h-48 space-y-2 overflow-auto">
            {data.recent_activity.map((e) => (
              <div key={e.id} className="flex items-center justify-between text-xs">
                <span className="font-medium">{e.event_type}</span>
                <span className="text-slate-500">{new Date(e.timestamp).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
