import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ManifestAPI } from "../api/client";
import { Button, Card, PageHeader, StatusBadge } from "../components/ui/primitives";
import { FieldGrid, WorkflowSteps } from "../components/ui/ops";
import { formatWhen } from "../lib/manifestCsv";
import { useAuth } from "../stores/auth";
import { useToast } from "../stores/toast";

export default function ManifestDetailPage() {
  const { id } = useParams();
  const { data, refetch } = useQuery({ queryKey: ["manifest", id], queryFn: () => ManifestAPI.get(id) });
  const can = useAuth((s) => s.canOperate());
  const toast = useToast();
  const qc = useQueryClient();
  const autoTried = useRef(false);

  const validate = useMutation({
    mutationFn: () => ManifestAPI.validate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["manifest", id] });
      toast.push("Validation completed");
    },
    onError: (e) => toast.error(e),
  });
  const commit = useMutation({
    mutationFn: () => ManifestAPI.commit(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["manifest", id] });
      toast.push("Shipment and samples committed");
      refetch();
    },
    onError: (e) => toast.error(e),
  });

  useEffect(() => {
    if (!data || !can || autoTried.current) return;
    if (data.status === "UPLOADED") {
      autoTried.current = true;
      validate.mutate();
    }
  }, [data, can, validate]);

  if (!data) return null;

  const step = data.status === "COMMITTED" ? 2 : data.status === "VALIDATED" || data.status === "VALIDATION_FAILED" ? 1 : 0;
  const firstBarcode = data.rows?.find((r) => r.canonical_data?.external_barcode)?.canonical_data?.external_barcode;
  const committedRows = (data.rows || []).filter((r) => r.committed_sample_id);

  return (
    <div>
      <PageHeader
        kicker="Manifest"
        title={data.original_filename}
        description={`SHA-256 ${data.checksum_sha256}`}
        actions={
          <>
            <StatusBadge status={data.status} />
            {can && (
              <Button variant="ghost" onClick={() => validate.mutate()} disabled={validate.isPending}>
                Validate
              </Button>
            )}
            {can && data.status !== "COMMITTED" && (
              <Button
                disabled={commit.isPending}
                onClick={() => {
                  if (window.confirm("Commit valid rows into shipment and sample records?")) commit.mutate();
                }}
              >
                Commit
              </Button>
            )}
            <a className="text-sm text-teal-700" href={ManifestAPI.validationReportUrl(id)} target="_blank" rel="noreferrer">
              Download validation CSV
            </a>
          </>
        }
      />

      <WorkflowSteps
        current={step}
        steps={[
          { title: "Uploaded", body: `${data.row_count} rows received and mapped.` },
          { title: "Validated", body: `${data.valid_row_count} valid · ${data.invalid_row_count} invalid.` },
          { title: "Registered", body: data.status === "COMMITTED" ? "Samples are ready for accessioning." : "Commit valid rows to create the shipment." },
        ]}
      />

      {data.status === "VALIDATION_FAILED" && (
        <Card className="mb-4 border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          Some rows failed validation. You can still commit — only valid rows will be registered.
        </Card>
      )}

      {data.status === "COMMITTED" && (
        <Card className="mb-4 border-teal-200 bg-gradient-to-br from-teal-50 to-white p-5">
          <div className="text-sm font-semibold text-ink-900">Shipment registered</div>
          <p className="mt-1 text-sm text-slate-600">
            {committedRows.length} samples are now in RECEIVED status. Enter a barcode on Accessioning to complete laboratory custody.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {data.committed_shipment_id && (
              <Link className="text-teal-800 underline" to={`/shipments/${data.committed_shipment_id}`}>
                open shipment
              </Link>
            )}
            {firstBarcode && (
              <Link
                className="inline-flex rounded-md bg-ink-900 px-3 py-2 text-sm font-medium text-white"
                to={`/accession?q=${encodeURIComponent(firstBarcode)}`}
              >
                Continue to accessioning
              </Link>
            )}
          </div>
          {committedRows.length > 0 && (
            <ul className="mt-4 grid gap-2 md:grid-cols-2">
              {committedRows.map((r) => (
                <li key={r.id} className="rounded-lg bg-white px-3 py-2 text-xs ring-1 ring-slate-200">
                  <div className="mono font-semibold text-ink-900">{r.canonical_data?.external_barcode}</div>
                  <div className="mt-0.5 text-slate-500">
                    {r.canonical_data?.sample_type} · {r.canonical_data?.quantity} {r.canonical_data?.quantity_unit}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      <div className="mb-4 grid gap-4 lg:grid-cols-3">
        <Card className="p-4 lg:col-span-1">
          <div className="text-sm font-semibold">Manifest summary</div>
          <div className="mt-3">
            <FieldGrid
              cols="grid-cols-1"
              items={[
                ["Rows", data.row_count],
                ["Valid", data.valid_row_count],
                ["Invalid", data.invalid_row_count],
                ["Uploaded", formatWhen(data.uploaded_at)],
                ["Validated", formatWhen(data.validated_at)],
                ["Committed", formatWhen(data.committed_at)],
              ]}
            />
          </div>
        </Card>
        <Card className="p-4 lg:col-span-2">
          <div className="text-sm font-semibold">Source → canonical mapping</div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs md:grid-cols-3">
            {Object.entries(data.column_mapping || {}).map(([k, v]) => (
              <div key={k} className="rounded bg-slate-50 px-2 py-1">
                <span className="text-slate-500">{k}</span> ← <span className="mono">{v || "unmapped"}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card className="overflow-x-auto">
        <table className="w-full min-w-[960px] text-xs">
          <thead className="bg-slate-50 text-left uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">Row</th>
              <th>External ID</th>
              <th>Barcode</th>
              <th>Type</th>
              <th>Material</th>
              <th>Qty</th>
              <th>Collected</th>
              <th>Source</th>
              <th>Temp</th>
              <th>Valid</th>
              <th>Errors</th>
            </tr>
          </thead>
          <tbody>
            {(data.rows || []).map((r) => {
              const c = r.canonical_data || {};
              return (
                <tr key={r.id} className={`border-t border-slate-100 ${r.is_valid === false ? "bg-rose-50/50" : ""}`}>
                  <td className="px-3 py-2">{r.row_number}</td>
                  <td className="mono">{c.sample_external_id}</td>
                  <td className="mono font-medium">{c.external_barcode}</td>
                  <td>{c.sample_type}</td>
                  <td>{c.material_type || "—"}</td>
                  <td>
                    {c.quantity} {c.quantity_unit}
                  </td>
                  <td>{c.collection_date || "—"}</td>
                  <td>{c.source_location || "—"}</td>
                  <td>{c.temperature_requirement || "—"}</td>
                  <td>{r.is_valid == null ? "—" : r.is_valid ? "Yes" : "No"}</td>
                  <td className="max-w-xs text-rose-700">
                    {r.errors?.map((e) => e.message || e.code).join("; ")}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
