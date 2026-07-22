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
    .poll(
      () =>
        page.locator("#capture-detail-image").evaluate((image) =>
          image.complete && image.naturalWidth > 0 ? image.naturalWidth : 0,
        ),
      { timeout: 15000 },
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
  await expect(page.locator("#capture-interval-input")).toBeVisible();
  await expect(page.locator("#calibration-capture-now")).toBeVisible();
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

test("field RGB and NIR preview controls remain responsive", async ({ page }, testInfo) => {
  const pixel = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "base64",
  );
  const preview = {
    device_id: "field-node-01",
    device_name: "Canopy Node 01",
    site_name: "North Research Plot",
    active: true,
    state: "streaming",
    session_id: "preview-test-1",
    requested_until: "2026-07-22T10:02:00Z",
    interval_seconds: 2,
    preview_width: 960,
    sequence: 4,
    latest_at: new Date().toISOString(),
    resolution: { width: 960, height: 540 },
    sync_delta_ms: 8,
    quality: {
      rgb_blur_score: 240.5,
      nir_blur_score: 218.2,
      rgb_mean: 0.45,
      nir_mean: 0.64,
      rgb_saturated_fraction: 0.01,
      nir_saturated_fraction: 0.01,
    },
    assets: {
      rgb: "/test-device-rgb.png",
      nir: "/test-device-nir.png",
    },
  };

  await page.route("**/test-device-*.png*", (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: pixel }),
  );
  await page.route(/\/api\/devices\/[^/]+\/preview(?:\/.*)?$/, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/stop")) {
      await route.fulfill({
        status: 200,
        json: { ...preview, active: false, state: "stopped" },
      });
      return;
    }
    await route.fulfill({ status: 200, json: preview });
  });
  await page.route(/\/api\/devices\/[^/]+\/commands$/, (route) =>
    route.fulfill({
      status: 201,
      json: {
        id: "command-test-1",
        device_id: "field-node-01",
        type: "capture_now",
        status: "pending",
        payload: {},
        result: {},
        created_at: new Date().toISOString(),
        claimed_at: null,
        completed_at: null,
      },
    }),
  );

  await page.goto("/");
  await page.getByRole("button", { name: "Live", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Field camera preview" })).toBeVisible();
  await expect(page.locator("#device-preview-name")).toContainText("Canopy Node 01");
  await expect(page.locator("#device-preview-state")).toHaveText("Streaming");
  await expect(page.locator("#device-preview-resolution")).toHaveText("960 x 540");
  await expect(page.locator("#device-preview-delta")).toHaveText("8.0 ms");
  await expect
    .poll(() => page.locator("#device-rgb-preview").evaluate((image) => image.naturalWidth))
    .toBeGreaterThan(0);
  await expect
    .poll(() => page.locator("#device-nir-preview").evaluate((image) => image.naturalWidth))
    .toBeGreaterThan(0);
  await page.getByRole("button", { name: "Capture RGB + NIR" }).click();
  await expect(page.locator("#toast")).toContainText("Capture command queued");
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: testInfo.outputPath("field-camera-preview.png"),
    fullPage: true,
  });
});

test("USB RGB test camera controls and snapshot archive remain responsive", async ({ page }, testInfo) => {
  const pixel = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "base64",
  );
  const camera = {
    enabled: true,
    running: true,
    camera_index: 0,
    camera_name: "Test RGB Camera",
    configured: { width: 1280, height: 720, fps: 30, zoom: 1.0 },
    active: { width: 1280, height: 720, fps: 30 },
    frame: {
      captured_at: "2026-07-22T10:00:00+00:00",
      age_ms: 4,
      brightness: 0.455,
      sharpness: 268.01,
      dark_fraction: 0.0227,
      saturated_fraction: 0.0133,
    },
    error: null,
  };
  const snapshot = {
    id: "webcam-test-1",
    captured_at: "2026-07-22T10:00:00Z",
    date_key: "2026-07-22",
    camera_name: "Test RGB Camera",
    resolution: { width: 1280, height: 720 },
    fps: 30,
    zoom: 1,
    quality: {
      blur_score: 268.01,
      mean: 0.455,
      dark_fraction: 0.0227,
      saturated_fraction: 0.0133,
    },
    assets: {
      rgb: "/test-webcam.png",
      thumb: "/test-webcam.png",
    },
  };

  await page.route("**/test-webcam.png", (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: pixel }),
  );
  await page.route(/\/api\/devices\/[^/]+\/preview(?:\/.*)?$/, async (route) => {
    const url = new URL(route.request().url());
    await route.fulfill({
      status: 200,
      json: {
        device_id: "field-node-01",
        device_name: "Canopy Node 01",
        site_name: "North Research Plot",
        active: !url.pathname.endsWith("/stop"),
        state: url.pathname.endsWith("/stop") ? "stopped" : "waiting",
        session_id: "preview-waiting",
        requested_until: "2026-07-22T10:02:00Z",
        interval_seconds: 2,
        preview_width: 960,
        sequence: 0,
        latest_at: null,
        resolution: null,
        sync_delta_ms: null,
        quality: null,
        assets: { rgb: null, nir: null },
      },
    });
  });
  await page.route("**/api/webcam/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/stream.mjpg")) {
      await route.fulfill({ status: 200, contentType: "image/png", body: pixel });
      return;
    }
    if (url.pathname.endsWith("/snapshots")) {
      await route.fulfill({ status: 200, json: [] });
      return;
    }
    if (url.pathname.endsWith("/capture")) {
      await route.fulfill({ status: 201, json: snapshot });
      return;
    }
    if (url.pathname.endsWith("/config")) {
      const requested = route.request().postDataJSON();
      camera.configured = requested;
      camera.active = {
        width: requested.width,
        height: requested.height,
        fps: requested.fps,
      };
    }
    if (url.pathname.endsWith("/stop")) camera.running = false;
    if (url.pathname.endsWith("/start")) camera.running = true;
    await route.fulfill({ status: 200, json: camera });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Live", exact: true }).click();
  await page.getByRole("button", { name: "USB test", exact: true }).click();
  await expect(page.getByRole("heading", { name: "USB RGB test camera" })).toBeVisible();
  await expect(
    page.locator("#webcam-live-panel .preview-channel-label"),
  ).toContainText("RGB only");
  await expect(page.locator("#webcam-name")).toHaveText("Test RGB Camera");
  await expect(page.locator("#webcam-active-mode")).toHaveText("1280 x 720");
  await expect
    .poll(() => page.locator("#webcam-stream").evaluate((image) => image.naturalWidth))
    .toBeGreaterThan(0);

  await page.locator("#webcam-zoom").fill("1.8");
  await page.locator("#webcam-zoom").dispatchEvent("change");
  await expect(page.locator("#webcam-zoom-value")).toHaveText("1.8x");
  await page.getByRole("button", { name: "Capture RGB" }).click();
  await expect(page.locator("#webcam-snapshot-count")).toHaveText("1 saved");
  await expect(page.locator(".webcam-snapshot-card")).toHaveCount(1);
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: testInfo.outputPath("live-camera.png"),
    fullPage: true,
  });
});
