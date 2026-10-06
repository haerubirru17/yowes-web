#!/usr/bin/env bash
# Yowes Web UI — one-command VPS installer
# Usage: bash install.sh [DOMAIN]
#   DOMAIN optional; default <server-IP>.sslip.io
# Root required. Ubuntu/Debian only.
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "❌ Jalankan sebagai root: sudo bash install.sh"; exit 1; }
. /etc/os-release 2>/dev/null || true
case "${ID:-}" in ubuntu|debian) ;; *) echo "❌ Hanya Ubuntu/Debian (terdeteksi: ${ID:-unknown})"; exit 1;; esac

REPO="https://github.com/haerubirru17/yowes-web.git"
YOWES_REPO="https://github.com/hirotomasato/yowes.git"
BASE=/opt
IP=$(curl -s -4 https://api.ipify.org || hostname -I | awk '{print $1}')
DOMAIN="${1:-${IP}.sslip.io}"
WITH_TLS=ask

echo "════════════════════════════════════════════"
echo " Yowes Web UI installer"
echo "   IP     : $IP"
echo "   Domain : $DOMAIN"
echo "════════════════════════════════════════════"

# 1. system deps
echo "── [1/7] Dependensi sistem…"
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip git certbot curl >/dev/null
apt-get install -y -qq fonts-dejavu-core fonts-noto-core >/dev/null 2>&1 || true

# 2. engine yowes (never modified)
echo "── [2/7] Clone engine yowes…"
[[ -d $BASE/yowes ]] || git clone -q "$YOWES_REPO" "$BASE/yowes"
echo "   engine di $BASE/yowes (tidak dimodifikasi)"

# 3. this repo + venv
echo "── [3/7] Clone yowes-web + venv…"
if [[ -d $BASE/yowes-web/.git ]]; then
  git -C "$BASE/yowes-web" pull -q || true
else
  git clone -q "$REPO" "$BASE/yowes-web"
fi
cd "$BASE/yowes-web"
[[ -d venv ]] || python3 -m venv venv
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q fastapi uvicorn pydantic pillow

# 4. TLS
echo "── [4/7] TLS (Let's Encrypt)…"
read -r -p "Pakai HTTPS? (Y/n) " a; [[ ${a:-y} =~ ^[Yy] ]] && WITH_TLS=yes || WITH_TLS=no
CERT_DIR=""
if [[ $WITH_TLS == yes ]]; then
  systemctl stop yowes-web 2>/dev/null || true
  certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos \
    -m "admin@${DOMAIN#*.}" || { echo "⚠️  certbot gagal (port 80/443 terbuka? DNS benar?). Lanjut TANPA TLS."; WITH_TLS=no; }
  [[ $WITH_TLS == yes ]] && CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
fi

# 5. systemd unit
echo "── [5/7] Service systemd…"
PORT=$([[ $WITH_TLS == yes ]] && echo 443 || echo 8080)
SSL_LINES=""
if [[ $WITH_TLS == yes ]]; then
  SSL_LINES="Environment=SSL_CERT=$CERT_DIR/fullchain.pem
Environment=SSL_KEY=$CERT_DIR/privkey.pem"
fi
cat > /etc/systemd/system/yowes-web.service <<EOF
[Unit]
Description=Yowes Doc Generator Web UI
After=network.target

[Service]
User=root
WorkingDirectory=$BASE/yowes-web
Environment=YOWES_DIR=$BASE/yowes
Environment=YOWES_OUTPUT_DIR=$BASE/yowes/output
Environment=PORT=$PORT
$SSL_LINES
ExecStart=$BASE/yowes-web/venv/bin/python $BASE/yowes-web/webui.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
mkdir -p "$BASE/yowes/output"
systemctl daemon-reload
systemctl enable --now yowes-web
sleep 3

# certbot renew hook
if [[ $WITH_TLS == yes ]]; then
  mkdir -p /etc/letsencrypt/renewal-hooks/deploy
  printf '#!/bin/sh\nsystemctl restart yowes-web\n' > /etc/letsencrypt/renewal-hooks/deploy/yowes.sh
  chmod +x /etc/letsencrypt/renewal-hooks/deploy/yowes.sh
fi

# 6. health check
echo "── [6/7] Health check…"
SCHEME=$([[ $WITH_TLS == yes ]] && echo https || echo http)
for i in 1 2 3 4 5 6; do
  code=$(curl -sk -o /dev/null -w '%{http_code}' "$SCHEME://127.0.0.1:$PORT/api/countries" || true)
  [[ ${code:-000} == 200 ]] && break; sleep 3
done
[[ ${code:-000} == 200 ]] || { echo "❌ API tidak merespons (HTTP $code). Cek: journalctl -u yowes-web -n 30"; exit 1; }

# 7. end-to-end generate test
echo "── [7/7] Tes generate end-to-end…"
out=$(curl -sk -m 120 -X POST "$SCHEME://127.0.0.1:$PORT/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"country":"indonesia","first_name":"Budi","last_name":"Santoso","school_name":"SMA Negeri 3 Jakarta","position":"Guru Matematika","date_of_birth":"1 Jan 1990"}' || true)
echo "$out" | grep -q '"ok":true' && echo "   ✅ generate OK" || { echo "   ❌ generate gagal:"; echo "$out"; exit 1; }

URL="$SCHEME://$DOMAIN"
echo
echo "════════════════════════════════════════════"
echo " ✅ Backend siap: $URL"
echo "    Buka https://haerubirru17.github.io/yowes-web/"
echo "    → isi 'Alamat server API' dengan: $URL"
echo "    Firewall: pastikan port $PORT terbuka (TCP)."
echo "════════════════════════════════════════════"
