import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PlatformAPI } from "../api/client";
import { Card, PageHeader, StatusBadge } from "../components/ui/primitives";

export default function ExceptionsPage() {
  const { data } = useQuery({ queryKey: ["exceptions"], queryFn: () => PlatformAPI.exceptions() });
  return (
    <div>
      <PageHeader kicker="Quality" title="Exceptions" description="Temperature excursions and quarantine cases awaiting scientific review." />
      <Card>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-[11px] uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Case</th>
              <th>Sample</th>
              <th>Status</th>
              <th>Opened</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map((c) => (
              <tr key={c.id} className="border-t border-slate-100">
                <td className="px-4 py-2 font-medium">{c.case_number}</td>
                <td>
                  <Link className="mono text-teal-800 underline" to={`/samples/${c.sample_id}`}>
                    {c.sample_business_id}
                  </Link>
                </td>
                <td>
                  <StatusBadge status={c.status} />
                </td>
                <td>{new Date(c.opened_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
