# StegoLab — Frontend

Web interface for StegoLab: hide messages in images, extract them, and
analyze images for hidden data.

Built with React 18, TypeScript, Vite and Tailwind CSS. It talks to the
FastAPI backend over REST and holds no analysis logic of its own — every
prediction, metric, score and region shown comes from the API.

---

## Requirements

- Node.js 18 or newer
- The FastAPI backend running and reachable, with migrations applied

## Install and run

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

With the backend in another terminal, from the repository root:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Type-check, then build the production bundle into `dist/` |
| `npm run preview` | Serve the built bundle on port 4173 |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | ESLint over all `.ts` / `.tsx` files |

### Environment

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Backend base URL, no trailing slash |

Only `VITE_`-prefixed variables reach the browser; never put secrets in
them. The backend's CORS settings must allow the frontend's origin
(localhost on any port is allowed by default).

---

## Routes

| Route | Page | Purpose |
|---|---|---|
| `/login`, `/signup`, `/verify-otp` | Auth | Sign in; create an account confirmed by an emailed 6-digit code |
| `/forgot-password`, `/reset-password` | Auth | Request a reset link; set a new password (token is read from the URL fragment) |
| `/` | Dashboard | The three tools, a getting-started guide for new accounts, real activity counts and recent items |
| `/hide` | Hide a Message | Choose an image and message; **Automatic** (adaptive multi-objective selection, with priority presets) or **Manual** method choice; result with before/after slider, changed-pixel map, measurements, candidate comparison and detection summary |
| `/extract` | Extract a Message | Uses the method recorded on the image automatically; manual fallback for unknown images; copy / save as .txt |
| `/analyze` | Analyze an Image | Detector verdict with probability, unusual-area overlay, detector inputs |
| `/history` | History | Tabs for hidden messages and analyses (`?tab=analyses`, `?result=STEGO|CLEAN`, `?page=`) |
| `/history/analyses/:id` | Analysis report | Full stored analysis |
| `/history/hides/:runId` | Hide details | Re-opens a stored automatic run with its full comparison |
| `/settings` | Settings | Account (email, verification, send reset link, sign out), theme, system status |

Old URLs (`/steganography`, `/steganalysis`, `/reports`, `/reports/:id`)
redirect to their replacements. Tools accept `?image=<id>` to pre-select an
image, which the result screens use for "Extract to check" / "Analyze this
image".

---

## Structure

```
src/
  api/            one module per backend resource; client.ts is the only fetch layer
  components/
    ui/           design-system primitives: Button/ButtonLink, Card, Badge, Field,
                  PasswordInput, Callout, Tabs/SegmentedControl, InfoTip, Stat,
                  States (Loading/Working/Empty/Error), Pagination, CopyButton…
    layout/       AppLayout (sidebar + mobile drawer + page header), AuthLayout, Logo
    auth/         password rules shared by signup and reset
    images/       ImagePicker, ImagePreview, CompareSlider, DifferenceMap
    hide/         message input, strategy/presets, result, candidate comparison
    analysis/     verdict, unusual areas, detector inputs
    history/      hidden-message and analysis lists
  context/        Auth (token + profile), Theme (light/dark/system), Toast
  hooks/          useAsync, useImageObjectUrl, useImageFromQuery, usePageTitle
  lib/            describe.ts (plain-language wording), featureCatalog, format, cn
  pages/          one file per route
```

## Design system

- All colours are CSS variables in `src/index.css` (`:root` and `.dark`),
  exposed to Tailwind as `bg`, `surface`, `elevated`, `line`,
  `line-strong`, `fg`, `muted`, `faint`, `accent`, `accent-hover`,
  `accent-soft`, `on-accent`, `clean`, `stego`, `warn`. Use tokens, never
  literal colours.
- Theme preference (`light`, `dark` or `system`) is stored under
  `stegolab.theme`; an inline script in `index.html` applies it before
  first paint.
- Tab titles are `<Page> · StegoLab` via `usePageTitle`.

## Honesty rules for the UI

- Long-running requests show elapsed time and what the server is doing,
  never fake step-by-step progress (the backend does not stream progress).
- Detection results are estimates: verdicts show the class probability,
  note the detector is LSB-statistics based, and "unusual areas" are never
  described as confirmed hiding locations.
- The candidate comparison shows only what the backend measured, including
  skipped and rejected options and the backend's own explanation.
- The changed-pixel map is only offered for lossless originals: browsers
  decode JPEG/WebP slightly differently from the server, which would make
  the map wrong.

## Known limitations

- Hiding is a single request; very large images can take a minute or more.
- Messages are text only and not encrypted.
- Images re-saved or edited after download lose their recorded method and
  usually their message.
