import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Download, FileSpreadsheet, Upload } from "lucide-react";
import { ManifestAPI } from "../api/client";
import { Button, Card, PageHeader, StatusBadge } from "../components/ui/primitives";
import { WorkflowSteps } from "../components/ui/ops";
import { buildBlankManifestTemplate, buildSampleManifest, downloadTextFile, formatWhen } from "../lib/manifestCsv";
import { useAuth } from "../stores/auth";
import { useToast } from "../stores/toast";

export default function IntakePage() {
  const { data } = useQuery({ queryKey: ["manifests"], queryFn: ManifestAPI.list });
  const navigate = useNavigate();
  const qc = useQueryClient();
  const can = useAuth((s) => s.canOperate());
  const toast = useToast();
  const [pack, setPack] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const upload = useMutation({
    mutationFn: (file) => ManifestAPI.upload(file),
    onSuccess: (m) => {
      qc.invalidateQueries({ queryKey: ["manifests"] });
      toast.push("Manifest uploaded");
      navigate(`/intake/${m.id}`);
    },
    onError: (e) => toast.error(e),
  });

  function takeFile(file) {
    if (!file) return;
    upload.mutate(file);
  }

  function downloadSample() {
    const next = buildSampleManifest();
    downloadTextFile(next.filename, next.csv);
    setPack(next);
    toast.push(`Sample CSV ready: ${next.shipment}`);
  }

  return (
    <div>
      <PageHeader
        kicker="Intake"
        title="Sample intake"
        description="Create a shipment CSV, upload the manifest, then register samples into the laboratory."
      />
      <WorkflowSteps
        current={0}
        steps={[
          { title: "Prepare & upload", body: "Download a sample CSV or use your own shipment file." },
          { title: "Validate & register", body: "Confirm every row, then commit valid samples." },
          { title: "Accession", body: "Look up each barcode and take the sample into custody." },
        ]}
      />

      {can && (
        <div className="mb-6 grid gap-4 xl:grid-cols-2">
          <Card className="p-5">
            <div className="flex items-start gap-3">
              <div className="rounded-lg bg-teal-50 p-2 text-teal-800">
                <FileSpreadsheet size={18} />
              </div>
              <div>
                <div className="text-sm font-semibold text-ink-900">Create a sample CSV</div>
                <p className="mt-1 text-sm leading-6 text-slate-500">
                  A ready shipment with five specimens from Bengaluru Clinical Site. Each download uses unique barcodes so you can run the full flow immediately.
                </p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button onClick={downloadSample}>
                <Download size={16} />
                Download sample CSV
              </Button>
              <Button
                variant="ghost"
                onClick={() => downloadTextFile("biospecimen-manifest-template.csv", buildBlankManifestTemplate())}
              >
                Blank template
              </Button>
            </div>
            {pack && (
              <div className="mt-4 rounded-lg border border-teal-100 bg-teal-50/60 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-teal-800">Use these barcodes next</div>
                <div className="mono mt-1 text-sm font-semibold text-ink-900">{pack.shipment}</div>
                <ul className="mt-2 space-y-1 text-xs">
                  {pack.samples.map((s) => (
                    <li key={s.external_barcode} className="flex justify-between gap-3">
                      <span className="mono text-ink-900">{s.external_barcode}</span>
                      <span className="text-slate-500">
                        {s.sample_type} · {s.quantity} {s.quantity_unit}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          <Card
            className={`p-5 ${dragOver ? "border-teal-600 bg-teal-50/40" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              takeFile(e.dataTransfer.files?.[0]);
            }}
          >
            <div className="flex items-start gap-3">
              <div className="rounded-lg bg-ink-900 p-2 text-white">
                <Upload size={18} />
              </div>
              <div>
                <div className="text-sm font-semibold text-ink-900">Register a shipment file</div>
                <p className="mt-1 text-sm leading-6 text-slate-500">
                  CSV or Excel. Required columns: shipment reference, external sample ID, barcode, type, quantity, and unit.
                </p>
              </div>
            </div>
            <label className="mt-5 flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center hover:border-teal-600 hover:bg-white">
              <input
                type="file"
                accept=".csv,.xlsx"
                className="hidden"
                onChange={(e) => {
                  takeFile(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
              <span className="inline-flex rounded-md bg-ink-900 px-3 py-2 text-sm font-medium text-white">
                {upload.isPending ? "Uploading…" : "Upload manifest"}
              </span>
              <span className="mt-2 text-xs text-slate-500">or drop a .csv / .xlsx file here</span>
            </label>
          </Card>
        </div>
      )}

      <Card>
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <div className="text-sm font-semibold text-ink-900">Uploaded manifests</div>
          <div className="text-xs text-slate-500">{(data || []).length} files</div>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">File</th>
              <th>Status</th>
              <th>Rows</th>
              <th>Valid / Invalid</th>
              <th>Checksum</th>
              <th>Uploaded</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-500">
                  No manifests yet. Download the sample CSV and upload it to start.
                </td>
              </tr>
            )}
            {(data || []).map((m) => (
              <tr key={m.id} className="border-t border-slate-100 hover:bg-slate-50/70">
                <td className="px-4 py-3">
                  <Link to={`/intake/${m.id}`} className="font-medium text-teal-800 hover:underline">
                    {m.original_filename}
                  </Link>
                </td>
                <td>
                  <StatusBadge status={m.status} />
                </td>
                <td>{m.row_count}</td>
                <td>
                  {m.valid_row_count} / {m.invalid_row_count}
                </td>
                <td className="mono text-xs text-slate-500">{m.checksum_sha256.slice(0, 12)}…</td>
                <td className="text-slate-500">{formatWhen(m.uploaded_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
