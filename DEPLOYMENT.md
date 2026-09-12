# Production Deployment

This covers taking the already-working Dockerized backend from your machine
to a real server on the public internet with HTTPS. It assumes the
`docker-compose.prod.yml` / `Caddyfile` / `.env.production.example` /
`scripts/backup_postgres.sh` files already in this repo.

## What you need before starting

1. **A server** with a public IP and Docker installed — any VPS works
   (Hetzner, DigitalOcean, Linode, AWS Lightsail, etc.). 1 vCPU / 2GB RAM is
   plenty to start. Ubuntu 22.04/24.04 is the easiest target.
2. **A domain name** (or subdomain, e.g. `api.yourdomain.com`) with access
   to its DNS settings.
3. SSH access to the server.

Nothing in this repo can provision these for you — they require an account
with a hosting provider and a domain registrar, both of which need your own
billing/identity.

## 1. DNS

Create an **A record** (and **AAAA** if the server has IPv6) pointing your
chosen domain/subdomain at the server's public IP. Wait for it to propagate
(`dig +short api.yourdomain.com` should return the server's IP) — Caddy
can't get a certificate until this resolves correctly from the internet.

## 2. Server setup

```bash
# On the server, as a non-root user with sudo:
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# log out and back in for the group change to take effect

# Firewall: only 22 (SSH), 80, 443 need to be open publicly.
# Postgres (5432) and Redis (6379) are NOT published by docker-compose.prod.yml
# at all, so there's nothing to firewall for them — they're only reachable
# from other containers on the private compose network.
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 3. Get the code onto the server

```bash
git clone <your-repo-url> gym-backend   # or scp the directory up
cd gym-backend
```

## 4. Generate production secrets

**Never reuse the JWT keys or passwords from your local `.env`/`secrets/` —
generate fresh ones on (or for) the server:**

```bash
python3 -m venv .venv && .venv/bin/pip install cryptography
.venv/bin/python -m scripts.generate_jwt_keys   # writes ./secrets/jwt_private.pem + jwt_public.pem
openssl rand -base64 32   # use the output as POSTGRES_PASSWORD below
```

`secrets/` is gitignored — if you generated the keys locally instead, copy
the directory up with `scp -r secrets/ user@server:gym-backend/`, don't
commit it.

## 5. Configure environment

```bash
cp .env.production.example .env.production
nano .env.production   # fill in every value — see inline comments
```

At minimum you must set: `DOMAIN`, `ACME_EMAIL`, `POSTGRES_PASSWORD`,
`BOOTSTRAP_ADMIN_EMAIL`/`BOOTSTRAP_ADMIN_PASSWORD`, and `CORS_ORIGINS` (leave
empty if you're only calling the API from the native Flutter mobile app —
CORS doesn't apply to it).

## 6. First deploy

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.production ps          # all three (soon four) healthy
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f caddy   # watch it obtain the TLS cert
```

Migrations run automatically on container start (same as the dev compose
file). The first Caddy start takes a few seconds to request the Let's
Encrypt certificate — watch its logs for `certificate obtained successfully`.

## 7. Bootstrap the admin account

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec api python -m scripts.create_admin
```
Log in as this account and change its password immediately — it was only
ever meant to get you started.

## 8. Verify

```bash
curl https://api.yourdomain.com/health
curl https://api.yourdomain.com/health/ready
curl -I https://api.yourdomain.com/docs
```
All should return over HTTPS with a valid certificate (no `-k` needed).
Point the Flutter app's base URL at `https://api.yourdomain.com/api/v1`.

## 9. Backups

```bash
chmod +x scripts/backup_postgres.sh scripts/restore_postgres.sh
./scripts/backup_postgres.sh ./backups 14   # test it manually first
crontab -e
# add: 0 3 * * * cd /path/to/gym-backend && ./scripts/backup_postgres.sh ./backups 14 >> /var/log/gym-backup.log 2>&1
```
Copy backups off the server periodically (rsync/S3) — a backup that only
lives on the same disk as the database doesn't protect against disk/host
failure. Test `scripts/restore_postgres.sh` against a scratch database at
least once so you know it actually works before you need it for real.

## 10. Redeploying after code changes

```bash
git pull
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```
This rebuilds only what changed and restarts the `api` container; Postgres
data and uploads are untouched (they're on named volumes).

## Known functional gaps to address before relying on this in production

- **Push notifications are a no-op** until you set `PUSH_PROVIDER=fcm` with
  a real Firebase service account (`app/services/push_provider.py` has the
  integration point already stubbed in).
- **Local disk storage** works fine for a single server but won't survive
  moving to multiple instances — switch to `STORAGE_BACKEND=s3` first if you
  ever scale horizontally.
