import { expect, test } from "@playwright/test";

test("login reaches overview with real API data", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "SENTINELAI" })).toBeVisible();
  await page.getByLabel("Email").fill("admin@example.com");
  await page.getByLabel("Password").fill("ChangeMeAdmin123!");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: /operations overview/i })).toBeVisible({
    timeout: 15_000,
  });
  // Honest empty/zero metrics are allowed; assert the live panel rendered.
  await expect(page.getByText(/active incidents/i).first()).toBeVisible();
  await expect(page.getByText(/services healthy/i).first()).toBeVisible();
});

test("unauthenticated visit redirects to login", async ({ page }) => {
  await page.goto("/incidents");
  await expect(page).toHaveURL(/\/login/);
});
