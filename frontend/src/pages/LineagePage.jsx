import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { Background, Controls, MiniMap, ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { SampleAPI } from "../api/client";
import { Card, Input, PageHeader } from "../components/ui/primitives";
import { useState } from "react";

export default function LineagePage() {
  const { id } = useParams();
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  const { data } = useQuery({
    queryKey: ["lineage", id],
    queryFn: () => SampleAPI.lineage(id),
    enabled: Boolean(id),
  });
  const nodes = (data?.nodes || []).map((n, i) => ({
    id: n.id,
    position: { x: 60 + (i % 5) * 190, y: 40 + Math.floor(i / 5) * 120 },
    data: { label: `${n.sample_id}\n${n.sample_type}\n${n.quantity} ${n.unit}\n${n.status}` },
    style: { fontSize: 11, whiteSpace: "pre", width: 170, background: n.is_center ? "#ecfdf5" : "#fff", border: "1px solid #cbd5e1" },
  }));
  const edges = (data?.edges || []).map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: `${e.relationship_type}`,
  }));
  return (
    <div>
      <PageHeader kicker="Traceability" title="Scientific lineage" description="Parent–child aliquot and derivative relationships for a selected sample." />
      <div className="mb-3 flex gap-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Lookup sample ID or barcode" />
        <button
          className="rounded-md bg-ink-900 px-3 text-sm text-white"
          onClick={async () => {
            const s = await SampleAPI.lookup(q);
            navigate(`/lineage/${s.id}`);
          }}
        >
          Load graph
        </button>
      </div>
      <Card className="h-[540px]">
        {id ? (
          <ReactFlow nodes={nodes} edges={edges} fitView>
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        ) : (
          <div className="p-8 text-sm text-slate-500">Enter a sample ID or barcode to view lineage.</div>
        )}
      </Card>
    </div>
  );
}
