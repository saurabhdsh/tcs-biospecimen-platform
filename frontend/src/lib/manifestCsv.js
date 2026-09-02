const HEADER =
  "shipment_reference,sample_external_id,external_barcode,sample_type,material_type,quantity,quantity_unit,collection_date,received_date,source_location,temperature_requirement";

const SPECIMENS = [
  { type: "Whole Blood", material: "Blood", qty: "10", unit: "mL", temp: "-80C" },
  { type: "Plasma", material: "Plasma", qty: "5", unit: "mL", temp: "-80C" },
  { type: "Serum", material: "Serum", qty: "4", unit: "mL", temp: "-80C" },
  { type: "PBMC", material: "Cells", qty: "2", unit: "mL", temp: "-196C" },
  { type: "DNA", material: "Nucleic Acid", qty: "50", unit: "uL", temp: "-80C" },
];

function pad(n) {
  return String(n).padStart(2, "0");
}

function isoDay(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function buildBlankManifestTemplate() {
  return `${HEADER}\n`;
}

export function buildSampleManifest() {
  const now = new Date();
  const ymd = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
  const token = Math.random().toString(36).slice(2, 6).toUpperCase();
  const shipment = `SHP-BLR-${ymd}-${token}`;
  const collected = new Date(now);
  collected.setDate(collected.getDate() - 4);
  const received = new Date(now);
  received.setDate(received.getDate() - 1);
  const site = "Bengaluru Clinical Site";

  const samples = SPECIMENS.map((s, i) => {
    const seq = pad(i + 1);
    return {
      shipment_reference: shipment,
      sample_external_id: `EXT-BLR-${ymd}-${token}-${seq}`,
      external_barcode: `GSK-BLR-${ymd}-${token}-${seq}`,
      sample_type: s.type,
      material_type: s.material,
      quantity: s.qty,
      quantity_unit: s.unit,
      collection_date: isoDay(collected),
      received_date: isoDay(received),
      source_location: site,
      temperature_requirement: s.temp,
    };
  });

  const csv = [HEADER, ...samples.map((r) => Object.values(r).join(","))].join("\n") + "\n";
  return { shipment, filename: `${shipment}.csv`, csv, samples };
}

export function downloadTextFile(filename, text, type = "text/csv") {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function formatWhen(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString();
}

export function formatDay(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString();
}
