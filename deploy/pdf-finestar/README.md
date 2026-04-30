## pdf.finestar.hr (Traefik integration)

This deploy uses your **existing** `traefik` container (already running on docker network `proxy` with Cloudflare DNS-01).

### Prereqs

- A DNS record `pdf.finestar.hr` (A/AAAA) pointing to this server
- Existing Traefik has a certresolver named `cloudflare` (confirmed via `docker inspect traefik`)

### Run

```bash
cd /opt/stacks/PaddleOCR/deploy/pdf-finestar
cp .env.example .env
docker compose up -d --build
```

### Notes

- This compose **does not** start Traefik; it only attaches `pdf-app` to the external network `proxy`.
- TLS is handled by Traefik using `traefik.http.routers.pdf.tls.certresolver=cloudflare`.
- OCR models are downloaded on-demand into `/opt/stacks/PaddleOCR/.runtime/ocr-models` (mounted to `/models`).

