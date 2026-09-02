import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { PlatformAPI } from "../api/client";
import { Button, Card, PageHeader, StatusBadge } from "../components/ui/primitives";

export default function ShipmentDetailPage() {
  const { id } = useParams();
  const { data } = useQuery({ queryKey: ["shipment", id], queryFn: () => PlatformAPI.shipment(id) });
  if (!data) return null;
  const total = data.sample_count || 0;
  const accessioned = data.accessioned_count || 0;
  const pct = total ? Math.round((accessioned / total) * 100) : 0;
  return (
    <div>
      <PageHeader
        kicker="Shipment"
        title={data.shipment_reference}
        description={data.manifest_filename || "No manifest filename"}
        actions={
          data.samples?.some((s) => s.status === "RECEIVED") && (
            <Link to={`/accession?q=${encodeURIComponent(data.samples.find((s) => s.status === "RECEIVED")?.barcode || "")}`}>
              <Button>Continue accessioning</Button>
            </Link>
          )
        }
      />
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          ["Status", data.status],
          ["Samples", data.sample_count],
          ["Received", data.received_count],
          ["Accessioned", data.accessioned_count],
        ].map(([k, v]) => (
          <Card key={k} className="p-4">
            <div className="text-[11px] uppercase text-slate-500">{k}</div>
            <div className="mt-1 font-semibold">{typeof v === "string" && k === "Status" ? <StatusBadge status={v} /> : v}</div>
          </Card>
        ))}
      </div>
      <Card className="mb-4 p-4">
        <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
          <span>Accession progress</span>
          <span>
            {accessioned} of {total} · {pct}%
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full bg-teal-600" style={{ width: `${pct}%` }} />
        </div>
      </Card>
      <Card>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-[11px] uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Sample ID</th>
              <th>Barcode</th>
              <th>Type</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.samples.map((s) => (
              <tr key={s.id} className="border-t border-slate-100">
                <td className="px-4 py-3">
                  <Link className="mono text-teal-800 hover:underline" to={`/samples/${s.id}`}>
                    {s.sample_id}
                  </Link>
                </td>
                <td className="mono">{s.barcode}</td>
                <td>{s.sample_type}</td>
                <td>
                  <StatusBadge status={s.status} />
                </td>
                <td className="pr-4 text-right">
                  {s.status === "RECEIVED" ? (
                    <Link className="text-sm text-teal-800 underline" to={`/accession?q=${encodeURIComponent(s.barcode || s.sample_id)}`}>
                      Accession
                    </Link>
                  ) : (
                    <Link className="text-sm text-slate-500 hover:underline" to={`/samples/${s.id}`}>
                      Sample 360
                    </Link>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
