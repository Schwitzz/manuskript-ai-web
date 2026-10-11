# Google Drive sync: archived research (dropped 11 Oct 2026)

This was Phase 7 of PLAN.md. The decision was to skip Google integration and sync project
files another way, so none of this is being built. It is kept in case that changes: the OAuth
and scope findings took real effort to gather and are dated 8 Oct 2026.

## 13. Phase 7: Google Drive two-way sync (4-6 days)

Goal: each project mirrors to a Drive folder, both ways, without ever silently losing text.

### 13.1 One-time Google setup (documented in docs/google-drive.md)
1. Create a Google Cloud project and enable the Drive API.
2. OAuth consent screen: user type External. **Publishing status must be "In production".** Confirmed in several sources: an External app in Testing gets refresh tokens that expire after 7 days (dev.to write-up quoting Google's OAuth docs; developers.google.com/health/setup; a Google Ads API forum advisor at groups.google.com/g/adwords-api/c/Z_kihrf6VCE). Re-authenticating in Testing only buys another 7 days (dev.to).
3. Once published ("In Production"), refresh tokens generally do not expire unless revoked or unused for a prolonged period, typically six months (developers.google.com/health/setup). Other expiry causes listed by third parties quoting Google's docs: user revocation, and a limit of 100 live refresh tokens per Google Account per OAuth client ID, after which the oldest is invalidated without warning (unified.to). So: sync at least occasionally, and never loop on re-authentication. My own precaution, NOT from a source: after publishing, disconnect and reconnect Drive once so the app holds a token issued under the production status.
4. Publishing can have prerequisites. One developer's write-up (dev.to, not an official source) says the Publish button was greyed out until branding fields were filled in: an application homepage URL and a privacy policy URL are named, and the excerpt I saw cuts off before the rest. A 2023 blog (newscrewdriver.com) reports that clicking Publish for an app with sensitive scopes asked for verification: privacy policy link, a demo video, a written justification and all domains verified in Search Console. Plan on needing a domain you control and a public privacy page. Not confirmed for your account or for the `drive` scope.
5. Scope choice. Confirmed on developers.google.com/drive/api/guides/api-specific-auth (page last updated 2026-09-03): `https://www.googleapis.com/auth/drive` ("View and manage all your Drive files") is listed under RESTRICTED scopes; `drive.file` is listed as non-sensitive and grants per-file access to files the app creates, or that the user opens or shares with it through the Google Picker API or the app's file picker; the page recommends migrating to non-sensitive scopes where possible. So full `drive` is the only scope that would let the server see files desktop Manuskript writes through another sync client, and it is the one Google restricts.
6. Verification. Confirmed: Google's help page "When is verification not needed" (support.google.com/cloud/answer/13464323, fetched) says a personal-use app (fewer than 100 users) can continue without going through verification, users click through the "unverified app" warning, and the "production" tier project should have the published status "In Production"; apps in testing mode are also not subject to verification but keep the unverified screen and the 100-user cap. The Drive scopes page (fetched) adds: restricted-scope data stored on servers requires a security assessment, and only specific app types may use restricted Drive scopes (backup and sync, productivity and education, reporting and security). A personal single-user sync app plausibly fits "backup and sync", but that is my reading, not Google's statement. The restricted-scope verification page (not re-fetched in this step) says assessments recur at least every 12 months, and Google's FAQ (support.google.com/cloud/answer/13463817) puts verification at about 6 weeks. Not confirmed: whether the console lets you publish a personal project with `drive` without forcing verification. Fallback if it forces it: use `drive.file` plus the Google Picker (you pick the project folders once; the app sees only those items), and keep desktop Manuskript syncing through the web app's export or its own rclone job rather than through Drive's files directly.
7. OAuth client type: Web application, redirect URI `https://<your-domain>/api/sync/google/callback` (only your browser has to reach it, so the VPN is fine). NOT checked in this research; from memory.

### 13.2 Design
- The server runs `rclone bisync` between `/data/projects/<Project>` and `Drive:Manuskript/<Project>`. rclone remote and token are created through the app's own OAuth flow; the config file is 0600 and its secrets are encrypted (confirm rclone's config-password support in the first spike).
- Per-project on/off toggle and a Drive folder picker (list folders through the Drive API).
- Triggers: 30 seconds after the last save, every few minutes, on app start, and a "Sync now" button. One pass at a time per project (rclone's lock file plus our own lock).
- Exclusions: `.trash/`, `.lock`, `*.tmp`, sync state, and Google Docs (`--drive-skip-gdocs`).
- All writes by the server are atomic (temp file then rename) so a pass never sees half a file.

### 13.3 Safety rules (non-negotiable)
1. **Explicit flags only.** Read from the rclone.org/bisync page on 8 Oct 2026: `--max-delete PERCENT` (safety check on the maximum percentage of deleted files; the run aborts if exceeded; default 50%), `--force` (bypasses the max-delete check), `--check-access` with `--check-filename` (default RCLONE_TEST), `--check-sync` (true|false|only), `--compare` (default size,modtime), `--conflict-resolve` (default none: keep and rename both files), `--conflict-loser` (default num: append a number to the conflict suffix), `--conflict-suffix`, `--resilient` (retry after less-serious errors instead of requiring --resync), `--recover` (recover from interruptions without --resync), `--max-lock` (expire old lock files; default never; minimum 2m), `--backup-dir1` and `--backup-dir2`, `--resync` / `--resync-mode`, `--ignore-listing-checksum`. The page's own example also uses `--drive-skip-gdocs`. Flag spellings change between releases, so the first step of the phase is still a spike that runs `rclone bisync --help` on the pinned version.
2. **Conflicts never overwrite.** With the documented defaults (`--conflict-resolve none`, `--conflict-loser num`) nothing is auto-resolved and the conflicting files are renamed with a numeric suffix. Confirm in the spike, then list them in the app with Compare, Keep mine, Keep theirs.
3. **Delete limit.** Use `--max-delete` with a LOW percentage. The docs say it is a percentage with a default of 50%, and the run aborts when it is exceeded; the safety-measures section says this protects against a failed listing being read as all files deleted. `--force` bypasses the check, so the app never passes `--force` by itself. A 50% default is too loose for a book project, so choose a small value in the spike (small projects with few files may need an absolute-count guard of our own as well). Desktop Manuskript can delete and rewrite a whole project folder on save, and bisync propagates deletions both ways, so this matters.
4. **Backup dirs.** Every pass keeps overwritten and deleted files in a dated backup folder outside the synced tree on both sides (`--backup-dir1/2`), pruned after a retention period.
5. **Access check.** `RCLONE_TEST` marker files so a missing or empty mount can never look like a mass delete.
6. **First connect is a guided, previewed step.** `--resync` makes one side win. The app shows a dry run and asks: Drive wins, this server wins, or merge keeping both. Never automatic.
7. **Resync repair never runs by itself.** If bisync reports it needs a resync, the app shows the same guided choice.

### 13.4 After each pass
- Diff the changed files, reload them through msklib, bump document versions, emit an SSE event.
- A document with unsaved edits in an open tab that also changed remotely shows the version-conflict prompt from Phase 3.
- Status panel: last sync time, files changed, conflicts, errors, and a log viewer.

### 13.5 Failure handling
- `invalid_grant` or revoked access: banner "Reconnect Google Drive" with a one-click re-auth; writing is never blocked.
- Network down: exponential backoff, a clear offline badge, no data loss.
- Rate limiting: back off and retry, and use our own OAuth client ID rather than a shared one.
- Refresh-token hygiene: keep one token per client ID in use; Google reportedly invalidates the oldest of 100 per account and client ID (unified.to quoting Google's docs), so the app never re-authenticates in a loop.

### 13.6 Your Ubuntu desktop
- Google does not ship an official Drive desktop client for Linux (from my own knowledge, not checked in this research), so desktop Manuskript needs its own sync. Provide docs/desktop-sync.md with an `rclone bisync` systemd timer using the same safety flags, or mount Drive through GNOME Online Accounts.
- Rule of thumb: let one device be the editor at a time; the safety rules above cover accidents.

### 13.7 Tests
- Two local folders as fake remotes (rclone's local backend): edit both sides, delete one side, mass delete, empty remote, interrupted pass, lock contention.
- Mocked 400 `invalid_grant` shows the reconnect banner.
- A live round trip against a throwaway Drive folder with your account.
- Check that desktop Manuskript opens a project after it has travelled through Drive and back.

Done when: an edit on the phone reaches the Ubuntu desktop and back, a forced conflict leaves both versions, and a simulated mass delete is stopped.

### 13.8 Open questions to settle in the spike
- Exact flag spellings and defaults for the rclone version we ship (pin it in the Dockerfile), and a sensible `--max-delete` percentage for projects with few files.
- Whether a `--backup-dir1/2` layout works with Drive. The rclone page shows them as per-side directories and warns that deleted files from both paths would mix if one shared `--backup-dir` is used; I did not confirm any further rule about overlap.
- How rclone stores the Drive token (config-file encryption) and whether the app can supply it at run time instead of a file.
- `drive` (full scope, restricted, personal-use exemption, possible forced verification on publish) versus `drive.file` (per-file via the Picker, non-sensitive, cannot see desktop-written files). Decide first; it shapes the whole of Phase 7.
- Whether Publish is blocked, or pushes you into verification, for your project with the `drive` scope.
- Whether a published, unverified, personal-use app keeps its refresh token alive in practice. Documents say yes; weeks of real use will confirm. The reconnect banner is the safety net.

### 13.9 Sources retrieved on 8 Oct 2026 (and what was NOT)
Retrieved and read:
- developers.google.com/health/setup: 7-day expiry in Testing; generally no expiry once In Production unless revoked or unused for about six months.
- dev.to/ko-hi/googles-oauth-testing-mode-expires-refresh-tokens-in-7-days-publish-the-consent-screen-before-24hm: 7-day rule quoting Google's docs; re-authenticating only buys 7 days; Publish button greyed out until branding fields are filled (not an official source).
- groups.google.com/g/adwords-api/c/Z_kihrf6VCE: Google Ads API forum advisor says to change the status to In production.
- unified.to/blog/why_google_oauth_returns, unipile.com, cdata.com: third-party summaries of Google's expiry conditions, including the 100-token cap and six-month inactivity (third party, quoting Google).
- newscrewdriver.com/2023/02/04/google-oauth-test-tokens-expire-weekly: Publish prompting verification for sensitive scopes (2023, one user).
- support.google.com/cloud/answer/13464323 (fetched directly): personal use, fewer than 100 users, no verification, "In Production", unverified-app screen and the 100-user cap in testing.
- developers.google.com/drive/api/guides/api-specific-auth (fetched directly, updated 2026-09-03): `drive` is restricted, `drive.file` is non-sensitive and per-file, restricted-scope app categories, security assessment for server-side storage.
- support.google.com/cloud/answer/13463817: verification types and timings (restricted scope about 6 weeks, security assessment).
- developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification: exceptions include personal use; server-side storage needs a security assessment; recurring every 12 months.
- rclone.org/bisync (fetched and read directly): flags and defaults, safety measures, Dropbox filter examples in its table of contents.
NOT retrieved, from memory: the OAuth client type and redirect URI in 13.1 item 7; that Google ships no official Linux Drive client (13.6); how rclone stores or encrypts the Drive token; whether publishing with `drive` forces verification for a personal project.

