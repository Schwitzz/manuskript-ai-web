import { test, expect, type Page } from '@playwright/test';

const PW = 'correct horse battery';

async function login(page: Page) {
await page.goto('/login');
await page.getByLabel('Username').fill('ab');
await page.getByLabel(/Password/).fill(PW);
await page.getByRole('button', { name: /Log in|Create account/ }).click();
await expect(page).toHaveURL(/\/write/);
}

const css = (page: Page, name: string) =>
page.evaluate((n) => document.documentElement.style.getPropertyValue(n).trim(), name);

test('themes switch live, persist across reload, and stay readable', async ({ page }, info) => {
await login(page);
await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'More' }).click();
const panel = page.getByRole('region', { name: 'Appearance' });

// Default is the dark Midnight scheme.
await expect(page.locator('html')).toHaveAttribute('data-theme', 'midnight');
const darkBg = await css(page, '--bg');

// 32 choices: System + 31 schemes.
await expect(panel.getByRole('radio')).toHaveCount(32 + 3); // themes + 3 density options

// Switch to a light theme: the page restyles immediately, no reload.
await panel.locator('[data-scheme="paper"]').click();
await expect(page.locator('html')).toHaveAttribute('data-theme', 'paper');
expect(await css(page, '--bg')).not.toBe(darkBg);
const bodyBg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
expect(bodyBg).toBe('rgb(244, 245, 247)'); // Paper's window colour
await page.screenshot({ path: `screenshots/theme-paper-${info.project.name}.png` });

// It survives a reload and applies before content shows.
await page.reload();
await expect(page.locator('html')).toHaveAttribute('data-theme', 'paper');

// Another scheme, then density and accent.
await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'More' }).click();
await panel.locator('[data-scheme="dracula"]').click();
await expect(page.locator('html')).toHaveAttribute('data-theme', 'dracula');
await panel.getByRole('radio', { name: 'Spacious' }).click();
await expect(page.locator('html')).toHaveAttribute('data-density', 'spacious');
expect(await css(page, '--ui-scale')).toBe('1.2');
await page.screenshot({ path: `screenshots/theme-dracula-${info.project.name}.png` });

await panel.locator('input[type="color"]').fill('#ff0000');
expect(await css(page, '--accent')).toBe('#ff0000');
await panel.getByRole('button', { name: "Use theme's" }).click();
expect(await css(page, '--accent')).not.toBe('#ff0000');

// Every scheme can be selected and leaves readable text (checked from the real page).
for (const id of await panel.locator('[data-scheme]').evaluateAll((els) => els.map((e) => e.getAttribute('data-scheme')!))) {
await panel.locator(`[data-scheme="${id}"]`).click();
const ratio = await page.evaluate(() => {
const lum = (rgb: string) => {
const [r, g, b] = rgb.match(/\d+/g)!.slice(0, 3).map((v) => {
const c = Number(v) / 255;
return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
});
return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const cs = getComputedStyle(document.body);
const a = lum(cs.color);
const b = lum(cs.backgroundColor);
return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
});
expect(ratio, id).toBeGreaterThanOrEqual(7);
}

// A corrupt saved value never breaks the page.
await page.evaluate(() => localStorage.setItem('msk.appearance', '{broken'));
await page.reload();
await expect(page.locator('html')).toHaveAttribute('data-theme', 'midnight');
});

test('System follows the device colour scheme live', async ({ page }) => {
await login(page);
await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'More' }).click();
await page.getByRole('region', { name: 'Appearance' }).locator('[data-scheme="system"]').click();

await page.emulateMedia({ colorScheme: 'light' });
await expect(page.locator('html')).toHaveAttribute('data-theme', 'paper');
await page.emulateMedia({ colorScheme: 'dark' });
await expect(page.locator('html')).toHaveAttribute('data-theme', 'midnight');
});
