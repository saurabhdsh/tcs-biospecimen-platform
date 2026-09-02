import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PlatformAPI } from "../api/client";
import { Card, PageHeader, StatusBadge } from "../components/ui/primitives";

export default function ShipmentsPage() {
  const { data } = useQuery({ queryKey: ["shipments"], queryFn: PlatformAPI.shipments });
  return (
    <div>
      <PageHeader kicker="Intake" title="Shipments" description="Inbound shipments and associated sample registration status." />
      <Card>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-[11px] uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Reference</th>
              <th>Status</th>
              <th>Samples</th>
              <th>Accessioned</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map((s) => (
              <tr key={s.id} className="border-t border-slate-100">
                <td className="px-4 py-2">
                  <Link className="mono font-medium text-teal-800 hover:underline" to={`/shipments/${s.id}`}>
                    {s.shipment_reference}
                  </Link>
                </td>
                <td>
                  <StatusBadge status={s.status} />
                </td>
                <td>{s.sample_count}</td>
                <td>{s.accessioned_count}</td>
                <td>{s.source_location}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
