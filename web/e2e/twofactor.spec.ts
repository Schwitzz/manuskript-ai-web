import { test, expect } from '@playwright/test';
import { totp } from './totp';

const PW = 'correct horse battery';
const section = (page: import('@playwright/test').Page) =>
page.getByRole('region', { name: 'Two-factor authentication' });

// Runs after login.spec.ts (alphabetical order) so the account already exists.
test('enable two-factor, log in with a code and a recovery code, disable', async ({ page }) => {
await page.goto('/login');
await page.getByLabel('Username').fill('ab');
await page.getByLabel(/Password/).fill(PW);
await page.getByRole('button', { name: 'Log in' }).click();
await expect(page).toHaveURL(/\/write/);

await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'More' }).click();
const tf = section(page);
await tf.getByRole('button', { name: 'Set up' }).click();
await expect(tf.getByRole('img', { name: 'Two-factor QR code' })).toBeVisible();
const secret = (await tf.locator('code').textContent())!.trim();

// A wrong code is rejected, the right one turns it on and shows 10 recovery codes.
await tf.getByLabel('Code').fill('000000');
await tf.getByRole('button', { name: 'Turn on' }).click();
await expect(tf.getByRole('alert')).toContainText('Wrong code');
await tf.getByLabel('Code').fill(totp(secret));
await tf.getByRole('button', { name: 'Turn on' }).click();
const items = tf.getByRole('list', { name: 'Recovery codes' }).getByRole('listitem');
await expect(items).toHaveCount(10);
const recovery = (await items.allTextContents()).map((s) => s.trim());
await tf.getByRole('button', { name: 'I have saved them' }).click();
await page.screenshot({ path: `screenshots/more-2fa-${test.info().project.name}.png` });

// Log out; password alone is no longer enough.
await page.getByRole('button', { name: 'Log out' }).click();
await page.getByLabel('Username').fill('ab');
await page.getByLabel(/Password/).fill(PW);
await page.getByRole('button', { name: 'Log in' }).click();
await expect(page.getByText(/6-digit code/)).toBeVisible();
await page.getByLabel('Code').fill('111111');
await page.getByRole('button', { name: 'Verify' }).click();
await expect(page.getByRole('alert')).toContainText('Wrong code');

// A recovery code works once.
await page.getByLabel('Code').fill(recovery[0]);
await page.getByRole('button', { name: 'Verify' }).click();
await expect(page).toHaveURL(/\/write/);

// Turn it off again with a fresh code (a code may already be used within its 30 s step).
await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'More' }).click();
await section(page).getByRole('button', { name: 'Turn off' }).click();
await section(page).getByLabel('Code').fill(totp(secret));
await section(page).getByRole('button', { name: 'Turn off' }).last().click();
await expect(section(page).getByRole('button', { name: 'Set up' })).toBeVisible();
});
