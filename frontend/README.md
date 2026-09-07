# StegoLab — Frontend

Web interface for the **AI-Powered Multi-Objective Adaptive Image
Steganography and Steganalysis Framework**.

Built with React 18, TypeScript, Vite and Tailwind CSS. It talks to the
existing FastAPI backend over REST and holds no analysis logic of its
own — every prediction, metric and region shown comes from the API.

---

## Requirements

- Node.js 18 or newer (developed on Node 22)
- The FastAPI backend running and reachable
- A PostgreSQL database with migrations applied
- A user account created via `POST /users`

There is no self-service registration in the UI by design.

---

## Install

```bash
cd frontend
npm install
cp .env.example .env
```

## Environment variables

Only one variable is used. It lives in `frontend/.env`:

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Base URL of the FastAPI backend, no trailing slash |

Vite only exposes variables prefixed with `VITE_`. Changing this file
requires restarting the dev server.

## Commands

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload on http://localhost:5173 |
| `npm run build` | Type-check then produce a production bundle in `dist/` |
| `npm run preview` | Serve the built bundle locally on port 4173 |
| `npm run typecheck` | `tsc --noEmit` only |
| `npm run lint` | ESLint across all `.ts` / `.tsx` files |

## Running the whole stack

From the repository root, in two terminals:

```bash
# Terminal 1 — backend
uvicorn backend.app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

Then open http://localhost:5173 and sign in.

### CORS

The backend allows `http://localhost:5173`, `http://127.0.0.1:5173` and
`http://localhost:4173` by default, plus any localhost port via a regex.
To serve the frontend from another origin, add it to `CORS_ORIGINS` in
`backend/app/config.py` or set the matching environment variable.

---

## Pages

| Route | Page | What it does |
|---|---|---|
| `/login` | Login | Email/password sign-in, stores the JWT |
| `/` | Dashboard | Totals, recent analyses, detection averages, embedding activity, live API/database/model status |
| `/steganography` | Steganography | Embed and extract payloads; method, channel and bit-depth configuration; capacity meter; MSE / PSNR / SSIM; round-trip extraction verification |
| `/steganalysis` | Steganalysis | Select an image, run detection, view the CLEAN/STEGO verdict, candidate regions, feature vector and report |
| `/reports` | Reports | Paginated history of every analysis session, filterable by predicted class |
| `/reports/:sessionId` | Report detail | Full stored report: image with region overlay, verdict, probabilities, 18 features, raw report data |
| `/settings` | Settings | Theme selection, backend connection details, active model information |

All routes except `/login` are guarded and redirect when no token is
present.

---

## API integration

Requests go through a single client in `src/api/client.ts`. Nothing in
the app calls `fetch` directly.

```
src/api/
  client.ts         base request(), auth header, error mapping, blob fetch
  types.ts          TypeScript mirrors of every backend response
  auth.ts           login, logout, health checks
  images.ts         upload, register-path, list, get, preview
  steganography.ts  methods, capacity, embed, extract, sessions
  steganalysis.ts   analyze, model, stats, sessions
  reports.ts        stored analysis reports
```

### Endpoints consumed

| Method | Path | Used by |
|---|---|---|
| `POST` | `/auth/login` | Login |
| `GET` | `/health`, `/health/db` | Dashboard, Settings |
| `POST` | `/images/upload` | Image selector |
| `POST` | `/images/register-path` | Image selector (dataset files) |
| `GET` | `/images` | Image selector |
| `GET` | `/images/{id}/file` | Every image preview |
| `GET` | `/steganography/methods` | Steganography |
| `GET` | `/steganography/capacity` | Capacity meter |
| `POST` | `/steganography/embed` | Steganography |
| `POST` | `/steganography/extract` | Steganography |
| `GET` | `/steganography/sessions` | Dashboard |
| `POST` | `/steganalysis/analyze/{image_id}` | Steganalysis |
| `GET` | `/steganalysis/model` | Steganalysis, Settings, Dashboard |
| `GET` | `/steganalysis/stats` | Dashboard |
| `GET` | `/steganalysis/sessions` | Dashboard, Reports |
| `GET` | `/steganalysis/sessions/{id}` | Report detail |
| `GET` | `/steganalysis/reports/{id}` | Available via `api/reports.ts` |

### Authentication

The JWT returned by `/auth/login` is kept in `localStorage` under
`stegolab.token` and attached as `Authorization: Bearer <token>` to every
request. Any `401` response clears the session globally and returns the
user to the login screen with an expiry notice, so an expired token never
leaves the interface in a half-working state.

Note that `/auth/login` takes `email` and `password` as **query
parameters**, matching the existing backend signature.

### Error handling

`ApiError` carries the HTTP status and a readable message. FastAPI's
`detail` field is flattened whether it arrives as a string or as a list of
validation objects, and each status code has a sensible fallback (400,
401, 403, 404, 409, 413, 422, 500, 503). A failed connection produces a
"cannot reach the backend" message rather than a raw network error. Python
tracebacks are never surfaced.

### Image previews

Image bytes sit behind bearer auth, so previews cannot use a plain `<img
src>`. `useImageObjectUrl` fetches them authenticated, creates an object
URL and revokes it on unmount. The backend transcodes PGM, PPM and TIFF to
PNG on the fly, which is what makes BOSSBase dataset files viewable in a
browser.

---

## Theme system

Two themes, light and dark, driven by a single `dark` class on the
`<html>` element.

- All colours are CSS custom properties defined in `src/index.css` under
  `:root` and `.dark`, exposed to Tailwind in `tailwind.config.js` as
  `bg`, `surface`, `elevated`, `line`, `fg`, `muted`, `faint`, `accent`,
  `clean`, `stego` and `warn`.
- Because every component uses those tokens rather than literal colours,
  switching the class re-themes the entire application at once.
- `ThemeContext` persists the choice to `localStorage` under
  `stegolab.theme` and falls back to the OS `prefers-color-scheme` on
  first visit.
- The toggle is in the header on every page; Settings has an explicit
  two-option selector.

---

## Project structure

```
src/
  api/          service layer, one module per resource
  components/
    ui/         Button, Card, Badge, Field, States, Progress, Collapsible
    layout/     AppLayout, Sidebar, Header
    ImagePreview.tsx        zoom, fit, region overlay
    ImageSelector.tsx       upload, drag-drop, library, path registration
    AnalysisResultViews.tsx verdict, probability chart, features, regions
    MetricCard.tsx
  context/      AuthContext, ThemeContext, ToastContext
  hooks/        useImageObjectUrl
  lib/          cn, format, featureCatalog
  pages/        one file per route
```

### Feature catalogue

`src/lib/featureCatalog.ts` maps the model's 18 production feature keys to
readable labels and groups them into Image Statistics, LSB Statistics,
Transition Statistics, Pair Statistics, RS Analysis and Sequential LSB
Analysis. The **backend key is always displayed alongside the label and is
never renamed internally**. Any feature the model gains later still
renders, under an "Other Features" group.

---

## Terminology

The interface deliberately avoids overstating what the system detects:

- Regions are labelled **candidate suspicious regions**, ranked by local
  LSB anomaly score, with a legend stating they are **not confirmed
  embedding locations**.
- The verdict card describes results as a statistical classification and
  notes that detector performance is payload-dependent.
- Confidence is presented per-classification and is never labelled as
  overall model accuracy.

Keep this wording if you extend the UI.

---

## Known limitations

- The image library loads up to 60 images without pagination; the reports
  table is paginated but the library is not.
- Extraction requires you to know which method and bit depth were used;
  there is no automatic method detection, because the backend does not
  expose one.
- DCT and DWT expose no tunable parameters, since the services implement
  them with fixed settings on the blue channel.
- The dashboard shows counts and averages but no time-series chart; the
  backend does not currently aggregate by date.
