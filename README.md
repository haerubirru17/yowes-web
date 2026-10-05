# Yowes Web UI

Simple web front-end for the [Yowes](https://github.com/hirotomasato/yowes) document generator — fill a form in the browser instead of using the terminal.

## Features
- Country → document types & school list auto-load
- Form: name, position, DOB, photo gender
- One-click generate → inline PNG previews + per-file download
- All results saved server-side to `yowes/output/`

## Setup (VPS)
```bash
# requires the yowes repo cloned at /home/agentuser/.hermes/cache/scratch/yowes
# with its deps installed (Pillow) in the Hermes venv
pip install fastapi uvicorn pydantic
python webui.py            # serves on 0.0.0.0:18800
```

## systemd (optional)
```ini
[Unit]
Description=Yowes Web UI
After=network.target

[Service]
ExecStart=/home/agentuser/.hermes/hermes-agent/venv/bin/python /home/agentuser/yowes-web/webui.py
Restart=always
User=agentuser

[Install]
WantedBy=multi-user.target
```

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | form page |
| GET | `/api/countries` | countries + doc types |
| GET | `/api/schools?country=xx` | school list |
| POST | `/api/generate` | render PNGs |
| GET | `/files/{name}` | serve PNG |

> For fiction/creative/testing purposes only.
