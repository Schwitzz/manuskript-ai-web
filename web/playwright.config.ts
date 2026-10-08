import { defineConfig } from '@playwright/test';

// One fresh server (and data dir) per project, so first-run setup is testable at both widths.
const servers = [
{ name: 'phone', port: 8766, viewport: { width: 390, height: 844 }, hasTouch: true },
{ name: 'desktop', port: 8767, viewport: { width: 1440, height: 900 }, hasTouch: false }
];

export default defineConfig({
testDir: 'e2e',
workers: 1,
projects: servers.map((s) => ({
name: s.name,
use: { baseURL: `http://127.0.0.1:${s.port}`, viewport: s.viewport, hasTouch: s.hasTouch }
})),
webServer: servers.map((s) => ({
command: `rm -rf /tmp/msk-e2e-${s.name} && cd ../server && MSK_DATA_DIR=/tmp/msk-e2e-${s.name} MSK_COOKIE_SECURE=false MSK_STATIC_DIR=../web/build uv run uvicorn app.main:app --port ${s.port}`,
url: `http://127.0.0.1:${s.port}/api/health`,
reuseExistingServer: false,
timeout: 60_000
}))
});
