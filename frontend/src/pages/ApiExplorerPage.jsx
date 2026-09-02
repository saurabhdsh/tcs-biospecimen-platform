import { useEffect, useState } from "react";
import { SampleAPI } from "../api/client";
import { Button, Card, Input, PageHeader } from "../components/ui/primitives";
import { useToast } from "../stores/toast";

export default function ApiExplorerPage() {
  const [spec, setSpec] = useState(null);
  const [sampleId, setSampleId] = useState("");
  const [payload, setPayload] = useState(null);
  const toast = useToast();
  useEffect(() => {
    fetch("/openapi.json")
      .then((r) => r.json())
      .then(setSpec)
      .catch((e) => toast.error(e));
  }, [toast]);
  return (
    <div>
      <PageHeader
        kicker="Integrations"
        title="Platform APIs"
        description="Published REST APIs for laboratory integrations. Look up a sample against the live service."
        actions={
          <a className="text-sm text-teal-800 underline" href="/openapi.json">
            Download openapi.json
          </a>
        }
      />
      <Card className="mb-4 p-4">
        <div className="text-sm font-semibold">GET /api/v1/samples/{"{sample_id}"}</div>
        <div className="mt-2 flex gap-2">
          <Input value={sampleId} onChange={(e) => setSampleId(e.target.value)} placeholder="UUID or lookup then paste UUID" />
          <Button
            onClick={async () => {
              try {
                let id = sampleId;
                if (!id.includes("-") || id.startsWith("SMP") || id.startsWith("GSK") || id.startsWith("EXT") || id.startsWith("BC")) {
                  const s = await SampleAPI.lookup(sampleId);
                  id = s.id;
                }
                setPayload(await SampleAPI.get(id));
              } catch (e) {
                toast.error(e);
              }
            }}
          >
            Execute
          </Button>
        </div>
        {payload && <pre className="mt-3 max-h-80 overflow-auto rounded bg-slate-50 p-3 text-xs">{JSON.stringify(payload, null, 2)}</pre>}
      </Card>
      <Card className="p-4 text-sm">
        <div className="font-semibold">{spec?.info?.title}</div>
        <div className="text-slate-500">OpenAPI {spec?.openapi}</div>
        <div className="mt-3 max-h-96 overflow-auto">
          {spec &&
            Object.keys(spec.paths || {}).map((p) => (
              <div key={p} className="mono text-xs">
                {Object.keys(spec.paths[p]).join(", ").toUpperCase()} {p}
              </div>
            ))}
        </div>
        <a className="mt-3 inline-block text-teal-800 underline" href="/docs" target="_blank" rel="noreferrer">
          Open Swagger UI
        </a>
      </Card>
    </div>
  );
}
