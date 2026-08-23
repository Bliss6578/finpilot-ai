import { expect, test } from "@playwright/test";

test("public experience has no horizontal overflow and auth routes load", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Paymentor/i);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  expect(overflow).toBe(false);
  await page.goto("/signin");
  await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  await page.goto("/signup");
  await expect(page.getByRole("button", { name: /create paymentor account/i })).toBeVisible();
});

test("authenticated workspace regression", async ({ page }) => {
  test.skip(!process.env.PAYMENTOR_E2E_EMAIL || !process.env.PAYMENTOR_E2E_PASSWORD, "Set safe E2E credentials to run private workspace checks");
  await page.goto("/signin");
  await page.getByLabel(/email/i).fill(process.env.PAYMENTOR_E2E_EMAIL!);
  await page.getByLabel(/password/i).fill(process.env.PAYMENTOR_E2E_PASSWORD!);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/dashboard/);
  for (const path of ["dashboard", "transactions", "cash-flow", "ai-cfo", "scenario-lab", "alerts", "intelligence", "settings"]) {
    await page.goto(`/${path}`);
    await expect(page.locator("main")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1)).toBe(false);
  }
});
