import { test, expect } from '@playwright/test';

const PW = 'correct horse battery';

// Serial: the first test creates the only account.
test.describe.configure({ mode: 'serial' });

test('setup, shell, navigation, logout, login', async ({ page }, info) => {
await page.goto('/');
await expect(page).toHaveURL(/\/login/);
await expect(page.getByText('This only works once')).toBeVisible();

// Short password is blocked by the browser; a good one creates the account.
await page.getByLabel('Username').fill('ab');
await page.getByLabel(/Password/).fill(PW);
await page.getByRole('button', { name: 'Create account' }).click();
await expect(page).toHaveURL(/\/write/);
await page.screenshot({ path: `screenshots/write-${info.project.name}.png` });

// Bottom navigation: five tabs, each at least 44px tall.
const nav = page.getByRole('navigation', { name: 'Main' });
for (const name of ['Write', 'Outline', 'Cards', 'Characters', 'More']) {
const link = nav.getByRole('link', { name });
await expect(link).toBeVisible();
const box = await link.boundingBox();
expect(box!.height).toBeGreaterThanOrEqual(44);
}
await nav.getByRole('link', { name: 'Outline' }).click();
await expect(page).toHaveURL(/\/outline/);

// Log out, then the guard sends us back to /login; log in again.
await nav.getByRole('link', { name: 'More' }).click();
await page.getByRole('button', { name: 'Log out' }).click();
await expect(page).toHaveURL(/\/login/);
await expect(page.getByText('Log in to continue')).toBeVisible();
await page.screenshot({ path: `screenshots/login-${info.project.name}.png` });

await page.getByLabel('Username').fill('ab');
await page.getByLabel(/Password/).fill('wrong password here');
await page.getByRole('button', { name: 'Log in' }).click();
await expect(page.getByRole('alert')).toContainText('Wrong username or password');

await page.getByLabel(/Password/).fill(PW);
await page.getByRole('button', { name: 'Log in' }).click();
await expect(page).toHaveURL(/\/write/);
});
