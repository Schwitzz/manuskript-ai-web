# Install

1. Copy `.env.example` to `.env`. Set `MSK_SECRET_KEY` (`openssl rand -hex 32`).
2. Create the data folders yourself, as your user: `mkdir -p data/projects data/app` (if Docker creates them they end up owned by root). Set `MSK_UID`/`MSK_GID` in `.env` to `id -u` / `id -g`. Put your projects in `./data/projects/` (a Manuskript project is a folder holding a `MANUSKRIPT` file).
3. `docker compose up -d`, then open `http://<host>:8000`.
4. First visit asks you to create the one account. This page only works while no account exists.
5. Open More, then Two-factor login, to turn on an authenticator app. Save the 10 recovery codes.

## Behind HTTPS (recommended)
Put a reverse proxy in front (`deploy/Caddyfile.example` or `deploy/nginx.conf.example`) and set in `.env`:

- `MSK_COOKIE_SECURE=true`
- `MSK_TRUSTED_PROXIES=<the proxy's IP as the app sees it>`. The app ignores `X-Forwarded-*` from any other address.
- Optional: `MSK_LOGIN_ALLOW_CIDRS=192.168.0.0/16,10.8.0.0/24` limits logins to your LAN and VPN.

## Phone
Open the HTTPS address, then Android Chrome: menu, Install app. iOS Safari: Share, Add to Home Screen.
Installing needs HTTPS (or `localhost`).

## Data
`./data/app/app.db` holds the account and login state (back it up). `./data/projects/` holds your writing.
Deleted items go to a `.trash` folder inside the project, never a hard delete.
If you lose `MSK_SECRET_KEY`, everyone is logged out; nothing else is lost.

## Locked out of two-factor
Use a recovery code. If none are left, stop the container and run:
`sqlite3 data/app/app.db "UPDATE user SET totp_enabled=0, totp_secret=NULL"`
