import { expect, test, type Page } from "@playwright/test";

/** The 3-minute demo, end to end, in mock mode (no AWS, no env vars). */

/** Opens the demo company and creates the workspace (waits for the form to be prefilled first). */
async function startDemo(page: Page) {
  await page.goto("/onboarding?demo=1");
  await expect(page.getByLabel("Business name")).toHaveValue(/EcoFizz/);
  for (let i = 0; i < 3; i++) await page.getByRole("button", { name: /^continue/i }).click();
  await page.getByRole("button", { name: /create workspace/i }).click();
  await expect(page).toHaveURL(/\/app\/workspace/);
}

async function noHorizontalScroll(page: Page) {
  // clientWidth (not innerWidth): mobile emulation zooms the layout viewport out when content overflows.
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow, "page scrolls horizontally").toBeLessThanOrEqual(1);
}

test("landing → demo company → evidence → mismatch → review → forecast → what-if", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  // 1. Landing and demo company
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("before you file");
  await noHorizontalScroll(page);
  await page.getByRole("link", { name: /explore demo/i }).click();
  await expect(page).toHaveURL(/\/onboarding\?demo=1/);
  await expect(page.getByLabel("Business name")).toHaveValue(/EcoFizz/);
  await expect(page.getByText("Synthetic demo data").first()).toBeVisible();
  await expect(page.getByTestId("applicability-statement")).toContainText(/requires verification/i);
  for (let i = 0; i < 3; i++) await page.getByRole("button", { name: /^continue/i }).click();
  await page.getByRole("button", { name: /create workspace/i }).click();
  await expect(page).toHaveURL(/\/app\/workspace/);
  await noHorizontalScroll(page);

  // 2. Packaging photo → predicted material + confidence
  await page.getByRole("tab", { name: /packaging photo/i }).click();
  await page.getByRole("button", { name: /illustrative pet bottle/i }).click();
  const material = page.getByTestId("material-prediction");
  await expect(material).toContainText("Plastic");
  await expect(material).toContainText("94%");
  await expect(material).toContainText(/not an official EPR or legal category/i);

  // 3. Invoice → extracted values
  await page.getByRole("tab", { name: /invoice pdf/i }).click();
  await page.getByRole("button", { name: /SYEC\/2526\/00004/ }).click();
  const inv = page.getByTestId("invoice-extraction");
  await expect(inv).toContainText("SYEC/2526/00004");
  await expect(inv).toContainText("0.500 Tonne");
  await expect(inv).toContainText("500 kg");

  // 4. CSV → reconcile
  await page.getByRole("tab", { name: /transaction csv/i }).click();
  await page.getByRole("button", { name: /15 EcoFizz transaction rows/i }).click();
  await expect(page.getByTestId("csv-preview")).toContainText("All required columns present");
  await page.getByRole("button", { name: /run reconciliation/i }).click();
  await expect(page).toHaveURL(/\/app\/review/);

  // 5. Mismatch is clear; original is kept after a correction
  await page.getByRole("button", { name: /Invoice 0\.5 MT vs recorded 500 MT/ }).click();
  await expect(page.getByTestId("diff-expected")).toContainText("500 kg");
  await expect(page.getByTestId("diff-observed")).toContainText("500,000 kg");
  await expect(page.getByTestId("diff-difference")).toContainText("499,500 kg");
  await expect(page.getByTestId("why-panel")).toContainText(/rule-based explanation/i);

  await page.getByRole("button", { name: /accept correction/i }).click();
  await page.getByRole("button", { name: /save correction/i }).click();
  await expect(page.getByText(/reason is required|enter the corrected quantity/i).first()).toBeVisible();
  await page.getByLabel(/corrected quantity/i).fill("500");
  await page.getByLabel("Reason", { exact: true }).fill("Supplier confirmed 0.5 MT by email");
  await page.getByRole("button", { name: /save correction/i }).click();
  await expect(page.getByTestId("diff-accepted")).toContainText("500 kg");
  await expect(page.getByTestId("diff-observed")).toContainText("500,000 kg"); // original still visible
  await expect(page.getByTestId("audit-history")).toContainText(/original kept: 500,000 kg/i);
  await page.keyboard.press("Escape");
  await noHorizontalScroll(page);

  // 6. Dashboard: forecast + anomalies
  await page.goto("/app/dashboard");
  await expect(page.getByTestId("forecast-next")).toContainText("403,261.78 kg");
  await expect(page.getByTestId("forecast-chart")).toContainText(/interval unavailable/i);
  await expect(page.getByTestId("anomaly-table")).toContainText(/rule-based/i);
  await expect(page.getByTestId("material-twin")).toBeVisible();
  await noHorizontalScroll(page);

  // 7. What-if: 25 → 20 g
  await page.goto("/app/simulator");
  await expect(page.getByTestId("reduction-pct")).toHaveText("20.0%");
  await page.getByLabel("Units sold in the period").fill("100000");
  await expect(page.getByTestId("baseline-kg")).toHaveText("2,500 kg");
  await expect(page.getByTestId("proposed-kg")).toHaveText("2,000 kg");
  await expect(page.getByTestId("reduction-kg")).toHaveText("500 kg");
  await page.getByLabel("Proposed g / unit").fill("-3");
  await expect(page.getByText(/must be greater than 0/i)).toBeVisible();
  await noHorizontalScroll(page);

  expect(errors, errors.join("\n")).toEqual([]);
});

test("a wrong file type is rejected with a next step", async ({ page }) => {
  await startDemo(page);
  await page.getByRole("tab", { name: /invoice pdf/i }).click();
  await page.locator('input[type="file"]').setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("hello") });
  const alert = page.getByRole("alert").filter({ hasText: /not a supported/i });
  await expect(alert).toBeVisible();
  await expect(alert).toContainText(/what you can do/i);
});

test("3D can be skipped: the 2D flow and table carry the same numbers", async ({ page }) => {
  await startDemo(page);
  await page.goto("/app/dashboard");
  await page.getByRole("button", { name: "2D", exact: true }).click();
  await expect(page.getByTestId("material-flow-2d")).toBeVisible();
  await page.getByTestId("material-flow-2d").getByRole("button", { name: /PET/ }).first().click();
  await expect(page.getByTestId("twin-detail")).toContainText("PET");
  await expect(page.getByRole("table", { name: "Material flow values" })).toContainText("PET bottle");
});
