# Install

1. Copy `.env.example` to `.env`. Set `MSK_SECRET_KEY` (`openssl rand -hex 32`).
2. Set `MSK_UID`/`MSK_GID` in `.env` to `id -u` / `id -g`. The data folders are created for you on first start by a small helper container (`prepare-data` in `docker-compose.yml`) that makes them belong to that user; you do not need to create them. Put your projects in `./data/projects/` (a Manuskript project is a folder holding a `MANUSKRIPT` file).
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
- `./data/app/app.db`: the account and login state (back it up).
- `./data/app/ai/`: AI provider settings, edited agent prompts, and chat history. **API keys are stored here as plain text**, so keep `./data/` private and out of any public backup.
- `./data/projects/`: your writing.
- `./data/templates/`: saved project templates.
Deleted items go to a `.trash` folder inside the project, never a hard delete.
If you lose `MSK_SECRET_KEY`, everyone is logged out; nothing else is lost.

## Locked out of two-factor
Use a recovery code. If none are left, stop the container and run:
`sqlite3 data/app/app.db "UPDATE user SET totp_enabled=0, totp_secret=NULL"`


## If the container keeps restarting
Run `docker compose logs manuskript`. "unable to open database file" or "Permission denied" on `/data/...` means `./data` is owned by the wrong user (for example it was created by an earlier start as root). `docker compose up -d` repairs this by itself; if you started the app some other way, run `sudo chown -R "$(id -u):$(id -g)" data` and start again.
