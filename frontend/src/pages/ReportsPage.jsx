import { useState } from "react";
import { PlatformAPI, SampleAPI, downloadAuth } from "../api/client";
import { Button, Card, Input, PageHeader } from "../components/ui/primitives";
import { useToast } from "../stores/toast";

export default function ReportsPage() {
  const [q, setQ] = useState("");
  const [history, setHistory] = useState(null);
  const [inventory, setInventory] = useState(null);
  const toast = useToast();
  return (
    <div>
      <PageHeader kicker="Reporting" title="Reports" description="Generate sample history and inventory extracts from current laboratory records." />
      <Card className="mb-4 flex flex-wrap gap-2 p-4">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Sample ID or barcode" />
        <Button
          onClick={async () => {
            try {
              const s = await SampleAPI.lookup(q);
              setHistory(await PlatformAPI.sampleHistory(s.id));
            } catch (e) {
              toast.error(e);
            }
          }}
        >
          Sample history
        </Button>
        <Button
          variant="ghost"
          onClick={async () => {
            try {
              setInventory(await PlatformAPI.inventoryReport());
            } catch (e) {
              toast.error(e);
            }
          }}
        >
          Inventory report
        </Button>
      </Card>
      {history && (
        <Card className="mb-4 p-4 text-sm">
          <div className="font-semibold">Sample history {history.identity.sample_id}</div>
          <div>Report run {history.report_run_id}</div>
          <button
            className="text-teal-800 underline"
            onClick={() => downloadAuth(PlatformAPI.sampleHistoryCsv(history.identity.id), "sample-history.csv")}
          >
            Download CSV
          </button>
          <pre className="mt-3 max-h-96 overflow-auto rounded bg-slate-50 p-3 text-xs">{JSON.stringify(history, null, 2)}</pre>
        </Card>
      )}
      {inventory && (
        <Card className="p-4 text-sm">
          <div className="font-semibold">Inventory · {inventory.rows.length} rows · run {inventory.report_run_id}</div>
          <table className="mt-2 w-full text-xs">
            <thead>
              <tr className="text-left text-slate-500">
                <th>ID</th>
                <th>Status</th>
                <th>Location</th>
              </tr>
            </thead>
            <tbody>
              {inventory.rows.map((r) => (
                <tr key={r.id} className="border-t">
                  <td className="mono py-1">{r.sample_id}</td>
                  <td>{r.status}</td>
                  <td>{r.current_location?.path_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
