# Yowes Web UI

Web front-end + REST API untuk generator dokumen [Yowes](https://github.com/hirotomasato/yowes) — isi form di browser, tanpa terminal.

- **Frontend (GitHub Pages):** https://haerubirru17.github.io/yowes-web/
- **Repo:** https://github.com/haerubirru17/yowes-web
- **Backend:** FastAPI, deploy di VPS mana pun (lihat [Instalasi](#instalasi-backend-di-vps))

> ⚠️ Dokumen yang dihasilkan adalah dokumen verifikasi **fiksi/kreatif/test**. Penggunaan sebagai identitas asli = pemalsuan dokumen.

---

## Arsitektur

```
Browser → GitHub Pages (docs/index.html, statis, HTTPS)
        → GET/POST → Backend FastAPI di VPS (port 443, TLS sslip.io/Let's Encrypt)
                   → engine yowes (clone terpisah, TIDAK dimodifikasi) → PNG
```

- Frontend statis di `docs/` (GitHub Pages); alamat API bisa diganti dari UI (tersimpan di localStorage).
- Backend membaca engine yowes dari `YOWES_DIR`. **Source yowes tidak boleh dimodifikasi** — semua adaptasi ada di lapisan `webui.py` / `meta_api.py`.

## File utama

| File | Fungsi |
|---|---|
| `webui.py` | FastAPI: form, `/api/countries`, `/api/schools`, `/api/generate`, `/files` |
| `meta_api.py` | `/api/meta` (kamus 13 negara) + `/api/resolve` (Auto Magic: cocokkan nama → negara) |
| `docs/index.html` | Frontend GitHub Pages (Claymorphism UI, alamat API configurable) |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | halaman form |
| GET | `/api/countries` | daftar negara + jenis dokumen |
| GET | `/api/schools?country=xx` | daftar sekolah |
| POST | `/api/generate` | render PNG, return URL |
| GET | `/files/{name}` | serve PNG |
| GET | `/api/meta` | kamus data 13 negara (nama, sekolah, posisi) |
| POST | `/api/resolve` | cocokkan nama depan/belakang → negara + profil |

---

## Instalasi Backend di VPS

Semua perintah sebagai root di Ubuntu/Debian. Ganti `NAMA_DOMAIN` dengan `<IP>.sslip.io` (gratis & otomatis) atau domain sendiri.

### 1. Dependensi sistem

```bash
apt update && apt install -y python3-venv python3-pip git certbot
apt install -y fonts-dejavu-core fonts-noto-core   # font untuk render PNG
```

### 2. Clone engine yowes (JANGAN diubah isinya)

```bash
cd /opt
git clone https://github.com/hirotomasato/yowes.git
cd yowes && git checkout <tag/commit-stabil>   # opsional, pin versi
```

### 3. Clone web UI + venv

```bash
cd /opt
git clone https://github.com/haerubirru17/yowes-web.git
cd yowes-web
python3 -m venv venv
venv/bin/pip install fastapi uvicorn pydantic pillow
```

Catatan: `yowes/requirements.txt` mencantumkan `customtkinter` & `mcp` — itu untuk mode desktop/MCP saja. **Web UI tidak butuh keduanya** (hanya Pillow darinya, sudah dipasang di atas).

### 4. TLS (wajib bila frontend via GitHub Pages — browser memblokir mixed content)

```bash
systemctl stop yowes-web 2>/dev/null   # jika sudah ada
certbot certonly --standalone -d NAMA_DOMAIN --non-interactive --agree-tos -m admin@NAMA_DOMAIN
```

Lewati langkah ini jika hanya HTTP lokal (frontend harus dibuka dari VPS yang sama).

### 5. Service systemd

`/etc/systemd/system/yowes-web.service`:

```ini
[Unit]
Description=Yowes Doc Generator Web UI
After=network.target

[Service]
User=root
WorkingDirectory=/opt/yowes-web
Environment=YOWES_DIR=/opt/yowes
Environment=YOWES_OUTPUT_DIR=/opt/yowes/output
Environment=PORT=443
Environment=SSL_CERT=/etc/letsencrypt/live/NAMA_DOMAIN/fullchain.pem
Environment=SSL_KEY=/etc/letsencrypt/live/NAMA_DOMAIN/privkey.pem
ExecStart=/opt/yowes-web/venv/bin/python /opt/yowes-web/webui.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Tanpa TLS: hapus baris `SSL_*` dan set `PORT=8080` (port yang terbuka di firewall).

```bash
systemctl daemon-reload
systemctl enable --now yowes-web
systemctl status yowes-web --no-pager
```

### 6. Verifikasi

```bash
curl -sk https://127.0.0.1/api/countries | head -c 160
curl -sk -X POST https://127.0.0.1/api/generate \
  -H "Content-Type: application/json" \
  -d '{"country":"indonesia","first_name":"Budi","last_name":"Santoso","school_name":"SMA Negeri 3 Jakarta","position":"Guru Matematika","date_of_birth":"1 Jan 1990"}'
# harapan: JSON {"ok":true,"files":[...],"school":"SMA Negeri 3 Jakarta"}
```

### 7. Sambungkan frontend

1. Buka https://haerubirru17.github.io/yowes-web/
2. Isi **Alamat server API** = `https://NAMA_DOMAIN` → Simpan (tersimpan di localStorage browser)

---

## Firewall

Backend hanya butuh `22` (SSH) + port API (`443` dengan TLS; `80`/`8080` tanpa TLS). Contoh rule cloud firewall: allow TCP `22,443`, sisanya drop.

## Renew TLS otomatis

Sertifikat Let's Encrypt berlaku 90 hari; certbot memasang timer renew otomatis. Karena `--standalone` butuh port 443 saat renew, pasang deploy-hook supaya service di-restart:

```bash
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/yowes.sh <<'EOF'
#!/bin/sh
systemctl restart yowes-web
EOF
chmod +x /etc/letsencrypt/renewal-hooks/deploy/yowes.sh
```

(Alternatif: pakai `--webroot` + nginx agar tanpa stop service.)

---

## Migrasi ke VPS baru (checklist)

1. [ ] Provision VPS baru, install dependensi (langkah 1)
2. [ ] Clone `yowes` + `yowes-web`, buat venv (langkah 2-3)
3. [ ] Sertifikat TLS untuk domain (langkah 4) — `<IP-baru>.sslip.io` otomatis mengikuti IP baru
4. [ ] Pasang systemd unit, sesuaikan `YOWES_DIR`/port/paths (langkah 5)
5. [ ] Verifikasi generate end-to-end (langkah 6)
6. [ ] Frontend: ganti alamat API di UI (localStorage), atau update default di `docs/index.html` + push
7. [ ] Opsional: salin output lama — `rsync -a lama:/opt/yowes/output/ /opt/yowes/output/`

Waktu total ±5 menit.

## Troubleshooting

| Gejala | Sebab / Solusi |
|---|---|
| `Sekolah 'X' tidak ditemukan` | Nama harus persis seperti daftar (dropdown aman; ketik manual harus exact) |
| Frontend "server tak terjangkau" | Port belum dibuka di firewall, atau mixed content (frontend HTTPS wajib backend HTTPS) |
| `meta_api unavailable` di log | `meta_api.py` hilang — core generate tetap jalan, Auto Magic nonaktif; `git pull` untuk pulihkan |
| Font rusak saat render | Install `fonts-dejavu-core` / `fonts-noto-core` |
| Generate lambat pertama kali | Normal — cold start font cache engine (±10-30 detik) |
| `undefined dokumen dibuat` | Bug frontend lama; `git pull` (sudah diperbaiki) |

## MCP Server (mode Hermes/desktop, opsional)

Yowes juga menyediakan MCP server (`mcp_server.py`) untuk dipakai dari Hermes:

```jsonc
// ~/.hermes/config.yaml
mcp_servers:
  yowes:
    command: /path/to/venv/bin/python
    args: ["/opt/yowes/mcp_server.py"]   # path langsung = tidak butuh cwd
```

Verifikasi: `hermes mcp test yowes`, lalu `/reload-mcp`.

---

> Untuk keperluan fiksi/kreatif/test saja.
