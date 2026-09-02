import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { InventoryAPI } from "../api/client";
import { Card, PageHeader, StatusBadge } from "../components/ui/primitives";

export default function InventoryPage() {
  const [parent, setParent] = useState(null);
  const [stack, setStack] = useState([]);
  const { data } = useQuery({ queryKey: ["tree", parent], queryFn: () => InventoryAPI.tree(parent) });
  const [occ, setOcc] = useState(null);

  return (
    <div>
      <PageHeader kicker="Inventory" title="Storage" description="Navigate site, freezer, rack, box, and position occupancy." />
      <div className="mb-3 text-xs text-slate-500">
        {stack.map((n, i) => (
          <button
            key={n.id}
            className="mr-2 underline"
            onClick={() => {
              setStack(stack.slice(0, i + 1));
              setParent(n.id);
            }}
          >
            {n.code}
          </button>
        ))}
        <button
          className="underline"
          onClick={() => {
            setParent(null);
            setStack([]);
          }}
        >
          root
        </button>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          {(data || []).map((n) => (
            <button
              key={n.id}
              className="flex w-full items-center justify-between border-b border-slate-100 px-4 py-3 text-left text-sm hover:bg-slate-50"
              onClick={async () => {
                if (n.location_type === "POSITION") {
                  setOcc(await InventoryAPI.occupancy(n.id));
                } else {
                  setStack([...stack, n]);
                  setParent(n.id);
                }
              }}
            >
              <span>
                <span className="font-medium">{n.name}</span>
                <span className="ml-2 text-xs text-slate-500">{n.location_type}</span>
              </span>
              <span className="mono text-xs">{n.code}</span>
            </button>
          ))}
        </Card>
        <Card className="p-4 text-sm">
          {occ ? (
            <div className="space-y-2">
              <div className="font-semibold">{occ.path_label}</div>
              <StatusBadge status={occ.status.toUpperCase()} />
              <div>
                Occupied {occ.occupied} / {occ.capacity}
              </div>
              {occ.sample && (
                <div className="mono">
                  {occ.sample.sample_id} · {occ.sample.status}
                </div>
              )}
            </div>
          ) : (
            <div className="text-slate-500">Select a POSITION to inspect occupancy.</div>
          )}
        </Card>
      </div>
    </div>
  );
}
