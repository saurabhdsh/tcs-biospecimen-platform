import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { SampleAPI } from "../api/client";
import { Card, Input, PageHeader, Select, StatusBadge } from "../components/ui/primitives";

export default function SamplesPage() {
  const [filters, setFilters] = useState({ page: 1, page_size: 25 });
  const { data } = useQuery({ queryKey: ["samples", filters], queryFn: () => SampleAPI.list(filters) });
  function set(k, v) {
    setFilters((f) => ({ ...f, page: 1, [k]: v }));
  }
  return (
    <div>
      <PageHeader kicker="Inventory" title="Samples" description="Search and filter registered samples by identity, status, location, and custodian." />
      <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-6">
        <Input placeholder="Sample ID" onBlur={(e) => set("sample_id", e.target.value)} />
        <Input placeholder="Barcode" onBlur={(e) => set("barcode", e.target.value)} />
        <Input placeholder="Type" onBlur={(e) => set("sample_type", e.target.value)} />
        <Select defaultValue="" onChange={(e) => set("status", e.target.value)}>
          <option value="">All statuses</option>
          {["RECEIVED", "ACCESSIONED", "IN_STORAGE", "CHECKED_OUT", "QUARANTINED", "RELEASED", "DISPOSED"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </Select>
        <Input placeholder="Freezer" onBlur={(e) => set("freezer", e.target.value)} />
        <Input placeholder="Custodian" onBlur={(e) => set("custodian", e.target.value)} />
      </div>
      <Card>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-[11px] uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Sample ID</th>
              <th>Barcode</th>
              <th>Type</th>
              <th>Status</th>
              <th>Location</th>
              <th>Qty</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items || []).map((s) => (
              <tr key={s.id} className="border-t border-slate-100">
                <td className="px-4 py-2">
                  <Link className="mono font-medium text-teal-800 hover:underline" to={`/samples/${s.id}`}>
                    {s.sample_id}
                  </Link>
                </td>
                <td className="mono">{s.barcode}</td>
                <td>{s.sample_type}</td>
                <td>
                  <StatusBadge status={s.status} />
                </td>
                <td className="text-xs">{s.current_location?.path_label || "—"}</td>
                <td>
                  {s.quantity_remaining} {s.quantity_unit}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex items-center justify-between px-4 py-3 text-xs text-slate-500">
          <span>{data?.total || 0} records</span>
          <button className="text-teal-700" onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}>
            Next page
          </button>
        </div>
      </Card>
    </div>
  );
}
