# OmniAI Studio

The browser playground for OmniAI. The first workspace supports Kokoro text-to-speech and is structured to add more models and modalities later.

## Run locally

Start the OmniAI API from the repository root:

```bash
OMNIAI_HOME="$PWD/models" uv run uvicorn main:app --reload
```

Then start the studio in another terminal:

```bash
cd studio
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/v1` requests to `http://localhost:8000`.

For a separately hosted API, copy `.env.example` to `.env` and set `VITE_API_BASE_URL` to its origin. That API must allow the studio origin through CORS.

## Current API integration

- `GET /v1/audio/voices?model=kokoro`
- `POST /v1/audio/speech`

Kokoro currently supports voice selection and WAV output. The speed and alternate-format controls are visible as forward-compatible settings, but remain disabled or informational until the backend accepts those parameters.
