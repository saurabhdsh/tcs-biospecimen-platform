import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { Background, Controls, MiniMap, ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { InventoryAPI, LabelAPI, PlatformAPI, SampleAPI, downloadAuth } from "../api/client";
import { Button, Card, Input, PageHeader, Select, StatusBadge } from "../components/ui/primitives";
import { useAuth } from "../stores/auth";
import { useToast } from "../stores/toast";

const TABS = ["Overview", "Identity", "Shipment", "Inventory", "Custody", "Lineage", "Environmental", "Exceptions", "Labels", "Audit Timeline"];

function useFreePositions() {
  return useQuery({
    queryKey: ["free-positions"],
    queryFn: async () => {
      async function walk(parent) {
        const nodes = await InventoryAPI.tree(parent);
        let out = [];
        for (const n of nodes) {
          if (n.location_type === "POSITION") out.push(n);
          else out = out.concat(await walk(n.id));
        }
        return out;
      }
      const all = await walk();
      const withOcc = await Promise.all(all.map(async (p) => ({ ...p, occ: await InventoryAPI.occupancy(p.id) })));
      return withOcc.filter((p) => p.occ.available > 0).slice(0, 40);
    },
  });
}

export default function Sample360Page() {
  const { id } = useParams();
  const qc = useQueryClient();
  const toast = useToast();
  const canOp = useAuth((s) => s.canOperate());
  const canRev = useAuth((s) => s.canReview());
  const [tab, setTab] = useState("Overview");
  const { data, refetch } = useQuery({ queryKey: ["sample360", id], queryFn: () => SampleAPI.get360(id) });
  const { data: positions } = useFreePositions();
  const { data: custodians } = useQuery({ queryKey: ["custodians"], queryFn: PlatformAPI.custodians });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["sample360", id] });

  if (!data) return <div className="text-sm text-slate-500">Loading sample…</div>;
  const s = data.overview;
  const nodes = (data.lineage?.nodes || []).map((n, i) => ({
    id: n.id,
    position: { x: n.is_center ? 280 : 80 + (i % 4) * 180, y: n.is_center ? 160 : 40 + Math.floor(i / 4) * 110 },
    data: { label: `${n.sample_id}\n${n.sample_type} · ${n.quantity}${n.unit}\n${n.status}` },
    style: {
      fontSize: 11,
      whiteSpace: "pre",
      border: n.is_center ? "2px solid #0b7c6e" : "1px solid #cbd5e1",
      background: "#fff",
      width: 160,
    },
  }));
  const edges = (data.lineage?.edges || []).map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: `${e.relationship_type} ${e.consumed}→${e.produced} ${e.unit}`,
  }));

  return (
    <div>
      <PageHeader
        kicker="Sample 360"
        title={s.sample_id}
        description={`${s.sample_type} · ${s.barcode || "no barcode"}`}
        actions={<StatusBadge status={s.status} />}
      />
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {[
          ["Barcode", s.barcode || "—"],
          ["Status", s.status],
          ["Location", s.current_location?.path_label || "—"],
          ["Custodian", s.custodian?.name || "—"],
          ["Quantity", `${s.quantity_remaining} ${s.quantity_unit}`],
          ["Shipment", s.shipment_reference || "—"],
        ].map(([k, v]) => (
          <Card key={k} className="p-3">
            <div className="text-[11px] uppercase text-slate-500">{k}</div>
            <div className="mt-1 text-sm font-medium">{v}</div>
          </Card>
        ))}
      </div>
      <div className="mb-4 flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium ${tab === t ? "bg-ink-900 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Overview" && (
        <Card className="p-5">
          <div className="mb-4 text-sm leading-6 text-slate-600">
            Internal identifiers are assigned at registration and cannot be edited.
            {s.shipment_id && (
              <span>
                {" "}
                <Link className="text-teal-800 underline" to={`/shipments/${s.shipment_id}`}>
                  Open parent shipment
                </Link>
              </span>
            )}
          </div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
            {[
              ["Internal ID", s.sample_id],
              ["Barcode", s.barcode],
              ["External ID", s.external_id],
              ["Sample type", s.sample_type],
              ["Material", s.material_type],
              ["Quantity remaining", `${s.quantity_remaining} ${s.quantity_unit}`],
              ["Original quantity", `${s.quantity_original} ${s.quantity_unit}`],
              ["Collection date", s.collection_date ? new Date(s.collection_date).toLocaleDateString() : "—"],
              ["Received date", s.received_date ? new Date(s.received_date).toLocaleDateString() : "—"],
              ["Source location", s.source_location],
              ["Temperature", s.temperature_requirement],
              ["Shipment", s.shipment_reference],
              ["Storage", s.current_location?.path_label],
              ["Custodian", s.custodian?.name],
              ["Accessioned", s.accessioned_at ? new Date(s.accessioned_at).toLocaleString() : "—"],
              ["Registered", s.created_at ? new Date(s.created_at).toLocaleString() : "—"],
              ["Restriction", s.restriction_flag ? "Restricted" : "None"],
            ].map(([k, v]) => (
              <div key={k} className="rounded-lg bg-slate-50 px-3 py-2.5">
                <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{k}</div>
                <div className="mt-1 break-all text-sm font-medium text-ink-900">{v || "—"}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
      {tab === "Identity" && (
        <Card className="p-5">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Identifiers</div>
              {(data.identity.identifiers || []).map((i) => (
                <div key={i.value} className="mb-2 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span className="text-slate-500">{i.type}</span>
                  <div className="mono font-medium">{i.value}</div>
                </div>
              ))}
            </div>
            <div>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Aliases</div>
              {(data.identity.aliases || []).map((i) => (
                <div key={i.value} className="mb-2 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span className="text-slate-500">{i.type}</span>
                  <div className="mono font-medium">{i.value}</div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
      {tab === "Shipment" && (
        <Card className="p-5 text-sm">
          {data.shipment.id ? (
            <div className="grid gap-2 md:grid-cols-3">
              <div className="rounded-lg bg-slate-50 px-3 py-2">
                <div className="text-[10px] uppercase text-slate-500">Reference</div>
                <Link className="font-medium text-teal-800 underline" to={`/shipments/${data.shipment.id}`}>
                  {data.shipment.reference}
                </Link>
              </div>
              <div className="rounded-lg bg-slate-50 px-3 py-2">
                <div className="text-[10px] uppercase text-slate-500">Status</div>
                <div className="mt-1 font-medium">{data.shipment.status || "—"}</div>
              </div>
            </div>
          ) : (
            "No shipment"
          )}
        </Card>
      )}
      {tab === "Inventory" && (
        <ActionsInventory sample={s} positions={positions} canOp={canOp} toast={toast} invalidate={invalidate} rows={data.inventory} />
      )}
      {tab === "Custody" && (
        <ActionsCustody sample={s} custodians={custodians} canOp={canOp} toast={toast} invalidate={invalidate} data={data.custody} positions={positions} />
      )}
      {tab === "Lineage" && (
        <div className="space-y-3">
          <Card className="h-[420px]">
            <ReactFlow nodes={nodes} edges={edges} fitView>
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </Card>
          {canOp && <AliquotForm sampleId={s.id} toast={toast} invalidate={invalidate} />}
        </div>
      )}
      {tab === "Environmental" && (
        <EnvForm sampleId={s.id} canOp={canOp} toast={toast} invalidate={invalidate} rows={data.environmental} />
      )}
      {tab === "Exceptions" && (
        <Card className="p-4 text-sm">
          {data.exceptions.map((c) => (
            <div key={c.id} className="mb-3 border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <span className="font-medium">{c.case_number}</span>
                <StatusBadge status={c.status} />
              </div>
              <div className="text-slate-600">{c.reason}</div>
              {canRev && c.status === "OPEN" && (
                <ResolveBox id={c.id} toast={toast} invalidate={invalidate} />
              )}
            </div>
          ))}
        </Card>
      )}
      {tab === "Labels" && (
        <LabelsPanel sampleId={s.id} labels={data.labels} canOp={canOp} toast={toast} invalidate={invalidate} />
      )}
      {tab === "Audit Timeline" && (
        <Card className="p-4">
          <ol className="space-y-3">
            {data.audit.map((a) => (
              <li key={a.id} className="border-l-2 border-teal-600 pl-3 text-sm">
                <div className="font-medium">{a.event_type}</div>
                <div className="text-xs text-slate-500">{new Date(a.timestamp).toLocaleString()}</div>
                {a.reason && <div className="text-xs">{a.reason}</div>}
              </li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}

function ActionsInventory({ sample, positions, canOp, toast, invalidate, rows }) {
  const [loc, setLoc] = useState("");
  const [reason, setReason] = useState("Putaway");
  return (
    <div className="space-y-3">
      {canOp && (
        <Card className="flex flex-wrap items-end gap-2 p-4">
          <Select value={loc} onChange={(e) => setLoc(e.target.value)}>
            <option value="">Select free position</option>
            {(positions || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.path_label}
              </option>
            ))}
          </Select>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} />
          <Button
            disabled={!loc}
            onClick={async () => {
              try {
                const fn = sample.status === "ACCESSIONED" || !sample.current_location ? SampleAPI.assignStorage : SampleAPI.move;
                await fn(sample.id, loc, reason);
                toast.push("Storage updated");
                invalidate();
              } catch (e) {
                toast.error(e);
              }
            }}
          >
            Assign / Move
          </Button>
        </Card>
      )}
      <Card>
        <table className="w-full text-xs">
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-t">
                <td className="px-3 py-2">{r.type}</td>
                <td>{r.reason}</td>
                <td>{new Date(r.at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function ActionsCustody({ sample, custodians, canOp, toast, invalidate, data, positions }) {
  const [cid, setCid] = useState("");
  const [purpose, setPurpose] = useState("Bench work");
  const [ret, setRet] = useState("");
  return (
    <div className="space-y-3">
      {canOp && (
        <Card className="grid gap-2 p-4 md:grid-cols-3">
          <div>
            <div className="mb-1 text-xs uppercase text-slate-500">Assign custodian</div>
            <Select value={cid} onChange={(e) => setCid(e.target.value)}>
              <option value="">Select</option>
              {(custodians || []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
            <Button
              className="mt-2"
              disabled={!cid}
              onClick={async () => {
                try {
                  await SampleAPI.assignCustodian(sample.id, cid, "Primary assignment");
                  toast.push("Custodian assigned");
                  invalidate();
                } catch (e) {
                  toast.error(e);
                }
              }}
            >
              Assign
            </Button>
          </div>
          <div>
            <div className="mb-1 text-xs uppercase text-slate-500">Checkout</div>
            <Input value={purpose} onChange={(e) => setPurpose(e.target.value)} />
            <Button
              className="mt-2"
              onClick={async () => {
                try {
                  await SampleAPI.checkout(sample.id, purpose);
                  toast.push("Checked out");
                  invalidate();
                } catch (e) {
                  toast.error(e);
                }
              }}
            >
              Checkout
            </Button>
          </div>
          <div>
            <div className="mb-1 text-xs uppercase text-slate-500">Return</div>
            <Select value={ret} onChange={(e) => setRet(e.target.value)}>
              <option value="">Position</option>
              {(positions || []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.path_label}
                </option>
              ))}
            </Select>
            <Button
              className="mt-2"
              disabled={!ret}
              onClick={async () => {
                try {
                  await SampleAPI.returnTo(sample.id, ret);
                  toast.push("Returned to storage");
                  invalidate();
                } catch (e) {
                  toast.error(e);
                }
              }}
            >
              Return
            </Button>
          </div>
        </Card>
      )}
      <Card className="p-4 text-sm">
        {data.assignments.map((a, i) => (
          <div key={i}>
            {a.custodian} ({a.code}) · {a.is_active ? "current" : "ended"}
          </div>
        ))}
      </Card>
    </div>
  );
}

function AliquotForm({ sampleId, toast, invalidate }) {
  const [qty, setQty] = useState("1");
  return (
    <Card className="flex items-end gap-2 p-4">
      <label className="text-sm">
        Output qty (mL)
        <Input value={qty} onChange={(e) => setQty(e.target.value)} />
      </label>
      <Button
        onClick={async () => {
          try {
            const child = await SampleAPI.children(sampleId, {
              relationship_type: "ALIQUOT",
              output_quantity: qty,
              output_unit: "mL",
              parent_quantity_consumed: qty,
              child_sample_type: "Aliquot",
            });
            toast.push(`Created ${child.sample_id}`);
            invalidate();
          } catch (e) {
            toast.error(e);
          }
        }}
      >
        Create aliquot
      </Button>
    </Card>
  );
}

function EnvForm({ sampleId, canOp, toast, invalidate, rows }) {
  const [val, setVal] = useState("-20");
  return (
    <div className="space-y-3">
      {canOp && (
        <Card className="flex items-end gap-2 p-4">
          <label className="text-sm">
            Measured °C
            <Input value={val} onChange={(e) => setVal(e.target.value)} />
          </label>
          <Button
            onClick={async () => {
              try {
                await SampleAPI.environmental(sampleId, {
                  measured_value: val,
                  unit: "C",
                  acceptable_min: -86,
                  acceptable_max: -70,
                  source: "Manual probe",
                  notes: "Recorded from Sample 360",
                  create_exception: true,
                });
                toast.push("Environmental event recorded");
                invalidate();
              } catch (e) {
                toast.error(e);
              }
            }}
          >
            Record excursion
          </Button>
        </Card>
      )}
      <Card className="p-4 text-sm">
        {rows.map((r) => (
          <div key={r.id}>
            {r.measured_value}
            {r.unit} at {new Date(r.occurred_at).toLocaleString()} {r.is_excursion ? "(excursion)" : ""}
          </div>
        ))}
      </Card>
    </div>
  );
}

function ResolveBox({ id, toast, invalidate }) {
  const [comment, setComment] = useState("");
  const [disp, setDisp] = useState("RELEASE_TO_INVENTORY");
  return (
    <div className="mt-2 flex gap-2">
      <Input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Resolution comment" />
      <Select value={disp} onChange={(e) => setDisp(e.target.value)}>
        <option>RELEASE_TO_INVENTORY</option>
        <option>RELEASE_WITH_RESTRICTION</option>
        <option>DISPOSE</option>
      </Select>
      <Button
        onClick={async () => {
          try {
            await PlatformAPI.resolve(id, { resolution_comment: comment, disposition: disp });
            toast.push("Exception resolved");
            invalidate();
          } catch (e) {
            toast.error(e);
          }
        }}
      >
        Resolve
      </Button>
    </div>
  );
}

function LabelsPanel({ sampleId, labels, canOp, toast, invalidate }) {
  const [reason, setReason] = useState("");
  return (
    <div className="space-y-3">
      {canOp && (
        <Button
          onClick={async () => {
            try {
              await SampleAPI.createLabel(sampleId);
              toast.push("Label generated");
              invalidate();
            } catch (e) {
              toast.error(e);
            }
          }}
        >
          Generate label
        </Button>
      )}
      {labels.map((l) => (
        <Card key={l.id} className="p-4">
          <div className="font-medium">{l.label_code}</div>
          <div className="mt-2 flex gap-3 text-sm">
            <button className="text-teal-800 underline" onClick={() => downloadAuth(l.png_url, `${l.label_code}.png`)}>
              PNG
            </button>
            <button className="text-teal-800 underline" onClick={() => downloadAuth(l.pdf_url, `${l.label_code}.pdf`)}>
              PDF
            </button>
          </div>
          {l.print_events.map((pe) => (
            <div key={pe.sequence_number} className="text-xs text-slate-600">
              #{pe.sequence_number} {pe.is_reprint ? "reprint" : "print"} — {pe.reason}
            </div>
          ))}
          {canOp && (
            <div className="mt-2 flex gap-2">
              <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Mandatory reprint reason" />
              <Button
                variant="ghost"
                onClick={async () => {
                  try {
                    await LabelAPI.reprint(l.id, reason);
                    toast.push("Reprint recorded");
                    invalidate();
                  } catch (e) {
                    toast.error(e);
                  }
                }}
              >
                Reprint
              </Button>
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
