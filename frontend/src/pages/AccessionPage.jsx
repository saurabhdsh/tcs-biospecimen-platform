import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, ScanBarcode, Sparkles } from "lucide-react";
import { SampleAPI } from "../api/client";
import { Button, Card, Input, PageHeader, StatusBadge } from "../components/ui/primitives";
import { FieldGrid, WorkflowSteps } from "../components/ui/ops";
import { formatDay, formatWhen } from "../lib/manifestCsv";
import { useAuth } from "../stores/auth";
import { useToast } from "../stores/toast";

function sampleFields(sample) {
  return [
    ["Internal ID", sample.sample_id, true],
    ["Barcode", sample.barcode, true],
    ["External ID", sample.external_id, true],
    ["Status", sample.status],
    ["Sample type", sample.sample_type],
    ["Material", sample.material_type],
    ["Quantity remaining", `${sample.quantity_remaining} ${sample.quantity_unit}`],
    ["Original quantity", `${sample.quantity_original} ${sample.quantity_unit}`],
    ["Collection date", formatDay(sample.collection_date)],
    ["Received date", formatDay(sample.received_date)],
    ["Source location", sample.source_location],
    ["Temperature", sample.temperature_requirement],
    ["Shipment", sample.shipment_reference, true],
    ["Storage", sample.current_location?.path_label],
    ["Custodian", sample.custodian?.name],
    ["Accessioned", formatWhen(sample.accessioned_at)],
    ["Registered", formatWhen(sample.created_at)],
    ["Restriction", sample.restriction_flag ? "Restricted" : "None"],
  ];
}

export default function AccessionPage() {
  const [params] = useSearchParams();
  const [q, setQ] = useState(params.get("q") || "");
  const [sample, setSample] = useState(null);
  const [busy, setBusy] = useState(false);
  const [justAccessioned, setJustAccessioned] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const videoRef = useRef(null);
  const can = useAuth((s) => s.canOperate());
  const toast = useToast();
  const navigate = useNavigate();

  const queue = useQuery({
    queryKey: ["accession-queue"],
    queryFn: () => SampleAPI.list({ status: "RECEIVED", page_size: 50 }),
  });

  async function lookup(value) {
    const query = (value || "").trim();
    if (!query) {
      toast.error({ message: "Enter a barcode or sample ID" });
      return;
    }
    setBusy(true);
    setJustAccessioned(false);
    try {
      const s = await SampleAPI.lookup(query);
      setSample(s);
      setQ(s.barcode || query);
    } catch (e) {
      setSample(null);
      toast.error(e);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    const initial = params.get("q");
    if (initial) lookup(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  useEffect(() => {
    document.getElementById("accession-barcode")?.focus();
  }, []);

  async function accession() {
    if (!sample) return;
    setBusy(true);
    try {
      const next = await SampleAPI.accession(sample.id);
      setSample(next);
      setJustAccessioned(true);
      toast.push(`Accessioned ${next.sample_id}`);
      queue.refetch();
    } catch (e) {
      toast.error(e);
    } finally {
      setBusy(false);
    }
  }

  function resetBench() {
    setSample(null);
    setJustAccessioned(false);
    setQ("");
    document.getElementById("accession-barcode")?.focus();
  }

  async function startCamera() {
    if (!("BarcodeDetector" in window)) {
      toast.push("Browser barcode detection is not supported. Use Scanner Input.");
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    setCameraOn(true);
    videoRef.current.srcObject = stream;
    await videoRef.current.play();
    const detector = new window.BarcodeDetector({ formats: ["code_128", "code_39", "qr_code"] });
    const tick = async () => {
      try {
        const codes = await detector.detect(videoRef.current);
        if (codes[0]) {
          setQ(codes[0].rawValue);
          lookup(codes[0].rawValue);
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
      } catch {
        /* keep scanning */
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  const pending = queue.data?.items || [];
  const step = justAccessioned || sample?.status === "ACCESSIONED" ? 2 : sample ? 1 : 0;

  return (
    <div>
      <PageHeader
        kicker="Accessioning"
        title="Receive into laboratory custody"
        description="Type or scan a barcode, review the full sample record, and accession it into the laboratory."
      />
      <WorkflowSteps
        current={step}
        steps={[
          { title: "Identify", body: "Enter the tube barcode or internal sample ID." },
          { title: "Review", body: "Confirm identity, quantity, source, and shipment." },
          { title: "Accession", body: "Take the sample into laboratory custody." },
        ]}
      />

      <div className="grid gap-4 xl:grid-cols-12">
        <Card className="order-2 space-y-4 p-5 xl:order-1 xl:col-span-4">
          <div className="flex items-center gap-2">
            <ScanBarcode className="text-teal-700" size={18} />
            <div className="text-sm font-semibold text-ink-900">Scanner Input</div>
          </div>
          <label className="block text-sm font-medium" htmlFor="accession-barcode">
            Barcode or sample ID
          </label>
          <div className="flex gap-2">
            <Input
              id="accession-barcode"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && lookup(q)}
              placeholder="Scan or type barcode / sample ID"
              autoComplete="off"
              className="mono"
            />
            <Button onClick={() => lookup(q)} disabled={busy}>
              Lookup
            </Button>
          </div>
          <p className="text-xs leading-5 text-slate-500">
            Manual entry is fully supported. Paste a barcode from the sample CSV, or pick a received tube from the queue below.
          </p>
          <Button variant="ghost" onClick={startCamera}>
            Use camera (where supported)
          </Button>
          {cameraOn && <video ref={videoRef} className="mt-2 w-full rounded bg-black/80" />}

          <div>
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Received queue · {pending.length}
            </div>
            <div className="max-h-72 space-y-1 overflow-auto">
              {pending.length === 0 && <div className="text-xs text-slate-500">No samples waiting for accession.</div>}
              {pending.map((s) => (
                <button
                  key={s.id}
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs hover:bg-slate-50 ${
                    sample?.id === s.id ? "bg-teal-50 ring-1 ring-teal-200" : "bg-slate-50"
                  }`}
                  onClick={() => {
                    setQ(s.barcode || s.sample_id);
                    lookup(s.barcode || s.sample_id);
                  }}
                >
                  <span>
                    <span className="mono font-semibold text-ink-900">{s.barcode || s.sample_id}</span>
                    <span className="ml-2 text-slate-500">{s.sample_type}</span>
                  </span>
                  <StatusBadge status={s.status} />
                </button>
              ))}
            </div>
          </div>
        </Card>

        <div className="order-1 xl:order-2 xl:col-span-8">
          {sample ? (
            <Card className="overflow-hidden">
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 bg-gradient-to-r from-ink-950 to-ink-800 px-5 py-5 text-white">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-300">Sample record</div>
                  <div className="mono mt-1 text-2xl font-semibold">{sample.sample_id}</div>
                  <div className="mono mt-1 text-sm text-slate-300">{sample.barcode || "No barcode"}</div>
                </div>
                <StatusBadge status={sample.status} />
              </div>

              {justAccessioned && (
                <div className="flex items-start gap-3 border-b border-emerald-100 bg-emerald-50 px-5 py-4 text-sm text-emerald-900">
                  <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
                  <div>
                    <div className="font-semibold">Accessioned into laboratory custody</div>
                    <div className="mt-0.5 text-emerald-800">
                      {sample.sample_id} is ready for labeling, storage assignment, and Sample 360 review.
                    </div>
                  </div>
                </div>
              )}

              <div className="p-5">
                <FieldGrid items={sampleFields(sample)} />
                <div className="mt-5 flex flex-wrap gap-2">
                  {can && (
                    <Button disabled={busy || sample.status !== "RECEIVED"} onClick={accession}>
                      Accession
                    </Button>
                  )}
                  <Button variant="ghost" onClick={() => navigate(`/samples/${sample.id}`)}>
                    Open Sample 360
                  </Button>
                  {sample.shipment_id && (
                    <Button variant="ghost" onClick={() => navigate(`/shipments/${sample.shipment_id}`)}>
                      Open shipment
                    </Button>
                  )}
                  {(justAccessioned || sample.status !== "RECEIVED") && (
                    <Button variant="accent" onClick={resetBench}>
                      <Sparkles size={16} />
                      Accession next
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ) : (
            <Card className="flex min-h-[420px] flex-col items-center justify-center p-10 text-center">
              <div className="rounded-full bg-teal-50 p-4 text-teal-800">
                <ScanBarcode size={28} />
              </div>
              <div className="mt-4 text-lg font-semibold text-ink-900">Waiting for a barcode</div>
              <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
                Scan or enter a barcode to retrieve the sample. The complete identity, shipment, quantity, and custody record will appear here before you accession.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
