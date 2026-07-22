const { test, expect } = require("@playwright/test");

async function expectNoHorizontalOverflow(page) {
  const dimensions = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.width + 1);
}

test("dashboard, archive, detail, and calibration render cleanly", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Field operations" })).toBeVisible();
  await expect(page.locator(".capture-card").first()).toBeVisible();
  await expect
    .poll(() =>
      page.locator(".capture-card img").first().evaluate((image) => image.naturalWidth),
    )
    .toBeGreaterThan(0);
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: testInfo.outputPath("dashboard.png"),
    fullPage: true,
  });

  await page.getByRole("button", { name: "Captures", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Captures by date" })).toBeVisible();
  await expect(page.locator(".date-group")).toHaveCount(8);
  await expectNoHorizontalOverflow(page);

  await page.locator("#capture-archive .capture-card").first().click();
  await expect(page.locator("#capture-dialog")).toBeVisible();
  await expect
    .poll(() => page.locator("#capture-detail-image").evaluate((image) => image.naturalWidth))
    .toBeGreaterThan(0);
  await page.getByRole("button", { name: "RGB", exact: true }).click();
  await expect(page.locator("#ndvi-scale")).toBeHidden();
  await expect
    .poll(() =>
      page.locator("#capture-detail-image").evaluate((image) =>
        image.complete && image.naturalWidth > 0 ? image.naturalWidth : 0,
      ),
    )
    .toBeGreaterThan(0);
  await page.screenshot({
    path: testInfo.outputPath("capture-detail.png"),
    fullPage: false,
  });
  await page.locator('[data-close-dialog="capture-dialog"]').click();

  await page.getByRole("button", { name: "Calibration", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Calibration profile" })).toBeVisible();
  await expect(page.locator("#rgb-profile")).toContainText("4608 x 2592");
  await expect(page.locator("#nir-profile")).toContainText("850 nm band-pass");
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: testInfo.outputPath("calibration.png"),
    fullPage: true,
  });
});

test("compact dashboard remains usable without horizontal page overflow", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Field operations" })).toBeVisible();
  await expect(page.locator(".capture-card").first()).toBeVisible();
  await expect
    .poll(() =>
      page.locator(".capture-card img").first().evaluate((image) => image.naturalWidth),
    )
    .toBeGreaterThan(0);
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: testInfo.outputPath("dashboard-mobile.png"),
    fullPage: true,
  });

  await page.getByRole("button", { name: "Calibration", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Calibration profile" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});
