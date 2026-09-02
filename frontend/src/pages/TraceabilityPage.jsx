import { useQuery } from "@tanstack/react-query";
import { PlatformAPI } from "../api/client";
import { Card, PageHeader, StatusBadge } from "../components/ui/primitives";

export default function TraceabilityPage() {
  const { data } = useQuery({ queryKey: ["trace"], queryFn: PlatformAPI.traceability });
  return (
    <div>
      <PageHeader kicker="Quality" title="Requirement traceability" description="Requirements mapped to test cases, latest execution result, and supporting evidence." />
      <Card>
        <table className="w-full text-xs">
          <thead className="bg-slate-50 text-left uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">Requirement</th>
              <th>Test case</th>
              <th>Last run</th>
              <th>Result</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map((row) => (
              <tr key={row.test_case_code} className="border-t border-slate-100">
                <td className="px-3 py-2">
                  <div className="font-semibold">{row.requirement_code}</div>
                  <div className="text-slate-500">{row.requirement_title}</div>
                </td>
                <td>{row.test_case_code}</td>
                <td>{row.last_run_at ? new Date(row.last_run_at).toLocaleString() : "—"}</td>
                <td>
                  <StatusBadge status={row.last_result} />
                </td>
                <td>{row.evidence.map((e) => e.title).join("; ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
