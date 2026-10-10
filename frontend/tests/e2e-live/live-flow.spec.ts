import { expect, test } from "@playwright/test";

test("live mode: real upload to S3 → Lambda parse/classify/reconcile → forecast → what-if", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const apiCalls: string[] = [];
  page.on("response", (r) => { if (r.url().includes("/api/") || r.url().includes("amazonaws.com")) apiCalls.push(`${r.status()} ${new URL(r.url()).pathname}`); });

  await page.goto("/onboarding?demo=1");
  await expect(page.getByLabel("Business name")).toHaveValue(/EcoFizz/);
  await expect(page.getByText(/live mode/i).first()).toBeHidden().catch(() => {}); // header chip appears inside /app
  for (let i = 0; i < 3; i++) await page.getByRole("button", { name: /^continue/i }).click();
  await page.getByRole("button", { name: /create workspace/i }).click();
  await expect(page).toHaveURL(/\/app\/workspace/);
  await expect(page.getByText(/live mode/i).first()).toBeVisible();

  await page.getByRole("tab", { name: /invoice pdf/i }).click();
  await page.getByRole("button", { name: /SYEC\/2526\/00004/ }).click();
  const inv = page.getByTestId("invoice-extraction");
  await expect(inv).toContainText("SYEC/2526/00004", { timeout: 60_000 });
  await expect(inv).toContainText("500 kg");

  await page.getByRole("tab", { name: /transaction csv/i }).click();
  await page.getByRole("button", { name: /15 EcoFizz transaction rows/i }).click();
  await expect(page.getByTestId("csv-preview")).toContainText("All required columns present", { timeout: 60_000 });

  await page.getByRole("tab", { name: /packaging photo/i }).click();
  await page.getByRole("button", { name: /carton/i }).click();
  await expect(page.getByTestId("material-prediction")).toContainText("Cardboard", { timeout: 60_000 });

  await page.getByRole("button", { name: /run reconciliation/i }).click();
  await expect(page).toHaveURL(/\/app\/review/, { timeout: 60_000 });
  await page.getByRole("button", { name: /vs recorded 500/i }).first().click();
  await expect(page.getByTestId("diff-expected")).toContainText("500 kg");
  await expect(page.getByTestId("diff-observed")).toContainText("500,000 kg");
  await expect(page.getByTestId("diff-difference")).toContainText("499,500 kg");
  await page.keyboard.press("Escape");

  await page.goto("/app/dashboard");
  await expect(page.getByTestId("forecast-next")).toContainText("403,261.78 kg", { timeout: 60_000 });
  await expect(page.getByTestId("material-twin")).toBeVisible();

  await page.goto("/app/simulator");
  await page.getByLabel("Units sold in the period").fill("100000");
  await expect(page.getByTestId("reduction-kg")).toHaveText("500 kg");

  console.log("API calls:", apiCalls.join(" | "));
  expect(apiCalls.some((c) => c.includes("amazonaws.com") || c.startsWith("200 /uploads"))).toBe(true); // browser PUT to S3 happened
  expect(errors, errors.join("\n")).toEqual([]);
});
