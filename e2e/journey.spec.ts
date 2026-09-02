import { test, expect } from "@playwright/test";

function csv(tag: string) {
  const ref = `SHP-E2E-${tag}`;
  return [
    "shipment_reference,sample_external_id,external_barcode,sample_type,material_type,quantity,quantity_unit,collection_date,received_date,source_location,temperature_requirement",
    `${ref},EXT-E2E-${tag}-1,BC-E2E-${tag}-1,Whole Blood,Blood,10,mL,2026-08-01,2026-08-03,London,-80C`,
    `${ref},EXT-E2E-${tag}-2,BC-E2E-${tag}-2,Plasma,Plasma,5,mL,2026-08-01,2026-08-03,London,-80C`,
  ].join("\n");
}

async function login(page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("LabOps@2026");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible({ timeout: 20000 });
}

test("end-to-end biospecimen journey", async ({ page }) => {
  const tag = Date.now().toString(36).toUpperCase();
  await login(page, "operator@biospecimen.local");

  await page.getByRole("link", { name: "Intake" }).click();
  const [fileChooser] = await Promise.all([
    page.waitForEvent("filechooser"),
    page.getByText("Upload manifest").click(),
  ]);
  await fileChooser.setFiles({
    name: `e2e-${tag}.csv`,
    mimeType: "text/csv",
    buffer: Buffer.from(csv(tag)),
  });
  await expect(page.getByText("Source → canonical mapping")).toBeVisible();
  await page.getByRole("button", { name: "Validate" }).click();
  await expect(page.getByText("VALIDATED")).toBeVisible();
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "Commit" }).click();
  await expect(page.getByText("COMMITTED")).toBeVisible();
  await page.getByRole("link", { name: "open shipment" }).click();
  await page.locator("a.mono").first().click();
  await expect(page.getByText("Sample 360")).toBeVisible();

  await page.getByRole("link", { name: "Accession" }).click();
  await page.getByPlaceholder("Scan or type barcode / sample ID").fill(`BC-E2E-${tag}-1`);
  await page.getByRole("button", { name: "Lookup" }).click();
  await page.getByRole("button", { name: "Accession" }).click();
  await expect(page.getByText("ACCESSIONED")).toBeVisible();
  await page.getByRole("button", { name: "Open Sample 360" }).click();

  await page.getByRole("button", { name: "Labels" }).click();
  await page.getByRole("button", { name: "Generate label" }).click();
  await page.getByPlaceholder("Mandatory reprint reason").fill("Playwright reprint");
  await page.getByRole("button", { name: "Reprint" }).click();

  await page.getByRole("button", { name: "Inventory" }).click();
  await page.locator("select").first().selectOption({ index: 1 });
  await page.getByRole("button", { name: "Assign / Move" }).click();

  await page.getByRole("button", { name: "Custody" }).click();
  await page.locator("select").first().selectOption({ index: 1 });
  await page.getByRole("button", { name: "Assign" }).click();
  await page.getByRole("button", { name: "Checkout" }).click();
  await page.locator("select").nth(1).selectOption({ index: 1 });
  await page.getByRole("button", { name: "Return" }).click();

  await page.getByRole("button", { name: "Environmental" }).click();
  await page.getByRole("button", { name: "Record excursion" }).click();
  await expect(page.getByText("QUARANTINED")).toBeVisible();

  await page.getByRole("button", { name: /Sign out|LogOut/i }).click().catch(async () => {
    await page.locator("button[title='Sign out']").click();
  });
  await login(page, "reviewer@biospecimen.local");
  await page.getByRole("link", { name: "Exceptions" }).click();
  await page.locator("a.mono").first().click();
  await page.getByRole("button", { name: "Exceptions" }).click();
  await page.getByPlaceholder("Resolution comment").fill("Material remains viable after logger review.");
  await page.getByRole("button", { name: "Resolve" }).click();

  await page.getByRole("button", { name: "Lineage" }).click();
  await page.getByRole("button", { name: "Create aliquot" }).click();

  await page.getByPlaceholder("Search sample ID, barcode, shipment…").fill(`BC-E2E-${tag}-1`);
  await page.waitForTimeout(400);
  await page.getByText(`BC-E2E-${tag}-1`).first().click().catch(async () => {
    await page.getByText("sample", { exact: false }).first().click();
  });

  await page.getByRole("link", { name: "Reports" }).click();
  await page.getByPlaceholder("Sample ID or barcode").fill(`BC-E2E-${tag}-1`);
  await page.getByRole("button", { name: "Sample history" }).click();
  await expect(page.getByText("Sample history")).toBeVisible();

  await page.getByRole("link", { name: "API Explorer" }).click();
  await page.getByPlaceholder("UUID or lookup then paste UUID").fill(`BC-E2E-${tag}-1`);
  await page.getByRole("button", { name: "Execute" }).click();
  await expect(page.getByText("sample_id")).toBeVisible();
});
