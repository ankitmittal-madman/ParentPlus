import { test, expect } from "./fixtures";
test("[PWA-001] public install manifest and brand icons load without private data", async ({
  page,
}) => {
  await page.goto("/login");
  const link = page.locator('link[rel="manifest"]');
  await expect(link).toHaveCount(1);
  const href = await link.getAttribute("href");
  expect(href).toBeTruthy();
  const response = await page.request.get(href!);
  expect(response.ok()).toBe(true);
  const manifest = await response.json();
  expect(manifest.display).toBe("standalone");
  expect(manifest.start_url).toBe("/login");
  expect(manifest.scope).toBe("/");
  expect(manifest.name).toBe("Parent Plus");
  expect(manifest.icons).toHaveLength(2);
  for (const icon of manifest.icons) {
    const result = await page.request.get(icon.src);
    expect(result.ok()).toBe(true);
    expect(result.headers()["content-type"]).toContain("image/png");
    const dimensions = await page.evaluate(async (src: string) => {
      const image = new Image();
      image.src = src;
      await image.decode();
      return `${image.naturalWidth}x${image.naturalHeight}`;
    }, icon.src);
    expect(dimensions).toBe(icon.sizes);
  }
  expect(JSON.stringify(manifest)).not.toMatch(
    /access_token|service_role|example\.test/,
  );
  await expect(
    page.locator('meta[name="mobile-web-app-capable"]'),
  ).toHaveAttribute("content", "yes");
  await expect(page.locator('link[rel="apple-touch-icon"]')).toHaveAttribute(
    "href",
    "/icons/parentplus-180.png",
  );
});
