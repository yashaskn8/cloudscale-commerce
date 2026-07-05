import { test, expect } from "@playwright/test";

test.describe("CloudScale Commerce SaaS E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to local address
    await page.goto("/");
  });

  test("should redirect to login if unauthorized", async ({ page }) => {
    // Since page is protected, it should redirect to /login
    await expect(page).toHaveURL(/.*\/login/);
    await expect(page.locator("h1")).toContainText(/sign in|welcome/i);
  });

  test("allows filling credentials on login form", async ({ page }) => {
    await page.goto("/login");
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');

    await emailInput.fill("customer@cloudscale.io");
    await passwordInput.fill("Password123!");

    await expect(emailInput).toHaveValue("customer@cloudscale.io");
    await expect(passwordInput).toHaveValue("Password123!");
  });

  test("unauthorized page blocks access", async ({ page }) => {
    await page.goto("/unauthorized");
    await expect(page.locator("h1")).toContainText(/sign in|unauthorized|403|welcome/i);
  });
});
