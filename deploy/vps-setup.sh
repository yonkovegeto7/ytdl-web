#!/usr/bin/env bash
# ============================================================
#  YouTube Downloader — one-shot VPS deploy (any provider)
#
#  Works on Ubuntu 20.04 / 22.04 / 24.04 and Debian 11/12 (x86_64 or arm64).
#  Tested flows: Contabo, Hetzner, DigitalOcean, Vultr, Oracle, RackNerd.
#
#  Usage:
#    1) copy the webapp folder to the server:
#         scp -r webapp root@<VPS-IP>:/tmp/ytdl
#    2) on the server:
#         sudo mv /tmp/ytdl /opt/ytdl
#         sudo APP_PORT=7860 DOMAIN=yourdomain.com EMAIL=you@mail.com \
#              bash /opt/ytdl/deploy/vps-setup.sh
#
#  DOMAIN is optional:
#    * with DOMAIN  -> Caddy + free HTTPS on 80/443 (best for Adsterra)
#    * without      -> app listens on 0.0.0.0:$APP_PORT (http://IP:port)
# ============================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ytdl}"
APP_PORT="${APP_PORT:-7860}"
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"
MAX_CONCURRENT="${MAX_CONCURRENT:-3}"

log() { echo -e "\n\033[1;36m==> $*\033[0m"; }
warn() { echo -e "\033[1;33m!!  $*\033[0m"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this with sudo:  sudo bash $0" >&2
  exit 1
fi

if [ ! -f "$APP_DIR/app.py" ]; then
  echo "app.py not found in $APP_DIR — copy the webapp folder there first." >&2
  exit 1
fi

# ---------------------------------------------------------------- 1. Docker --
log "Installing Docker, curl, ffmpeg"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl iptables ffmpeg
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

# ------------------------------------------------------------- 2. firewall --
log "Opening ports ${APP_PORT}, 80 and 443"
if command -v ufw >/dev/null 2>&1; then
  ufw allow 22/tcp || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
  ufw allow "${APP_PORT}"/tcp || true
  yes | ufw enable || true
fi

# ------------------------------------------------------------------ 3. build --
log "Building the image"
cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
fi
# keep one-job-at-a-time on small VPS, more on bigger ones
sed -i "s/^MAX_CONCURRENT=.*/MAX_CONCURRENT=${MAX_CONCURRENT}/" .env || true
# never delete finished files by age
grep -q '^FILE_TTL=' .env && sed -i 's/^FILE_TTL=.*/FILE_TTL=0/' .env || echo 'FILE_TTL=0' >> .env
grep -q '^MAX_STORAGE_MB=' .env || echo 'MAX_STORAGE_MB=8000' >> .env

docker build -t ytd-web .

log "Starting the container (auto-restart on reboot)"
docker rm -f ytd-web >/dev/null 2>&1 || true

if [ -n "$DOMAIN" ]; then
  # Caddy terminates TLS and proxies to the container on localhost only
  docker run -d --name ytd-web --restart always \
    --env-file .env -p "127.0.0.1:${APP_PORT}:${APP_PORT}" ytd-web
else
  docker run -d --name ytd-web --restart always \
    --env-file .env -p "${APP_PORT}:${APP_PORT}" ytd-web
fi

sleep 5
if curl -fsS "http://127.0.0.1:${APP_PORT}/healthz" >/dev/null; then
  log "Container is healthy"
else
  warn "Container did not answer yet — check: docker logs -f ytd-web"
fi

# ------------------------------------------------------------------ 4. HTTPS --
if [ -n "$DOMAIN" ]; then
  log "Installing Caddy for https://$DOMAIN"
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https gnupg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y
  apt-get install -y caddy

  cat > /etc/caddy/Caddyfile <<EOF
{
  email ${EMAIL}
}
$DOMAIN {
    encode gzip zstd
    reverse_proxy 127.0.0.1:${APP_PORT} {
        transport http {
            read_timeout 20m
            write_timeout 20m
        }
    }
    request_body {
        max_size 1GB
    }
    header {
        Referrer-Policy strict-origin-when-cross-origin
    }
}
EOF

  systemctl reload caddy || systemctl restart caddy
  log "HTTPS issued for https://$DOMAIN (A record must point to this VPS)"
else
  PUBLIC_IP="$(curl -4 -fsS https://api.ipify.org || echo '<VPS-IP>')"
  cat <<EOF

  App is public now:  http://${PUBLIC_IP}:${APP_PORT}

  For a real domain + free HTTPS (recommended for Adsterra):
     sudo DOMAIN=yourdomain.com EMAIL=you@mail.com bash $0

EOF
fi

log "Done."
echo "  Health : http://127.0.0.1:${APP_PORT}/healthz"
echo "  Logs   : docker logs -f ytd-web"
echo "  Update : cd $APP_DIR && docker build -t ytd-web . && docker restart ytd-web"
