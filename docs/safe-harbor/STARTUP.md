# Startup

Configuration is server-side in ignored `.env`. Initial target is a local transaction-capable MongoDB replica set; Atlas can be selected with MONGODB_URI. Never commit credentials.

Planned commands (updated after validation):
1. Create `.venv` and install `backend` editable dependencies.
2. Install frontend with `npm ci`.
3. Start the MongoDB replica set, API, persistent coordinator and Vite using `scripts/safe_harbor_dev.py`.
4. Open the local frontend. Run operational E2E and Playwright against the actual services.

Model runs must use configured provider access and record model identity/usage. Deterministic operational mode is visibly labeled and is not model-improvement evidence.
