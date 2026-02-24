# MedAI Frontend

Production-grade Next.js 14 frontend for the **MedAI Clinical Co-Pilot** — a multi-modal medical AI assistant powered by MedGemma & Claude.

---

## Quick Start

```bash
# Install dependencies
npm install --legacy-peer-deps

# Copy environment template
cp .env.example .env.local   # adjust NEXT_PUBLIC_API_URL if needed

# Run dev server
npm run dev                   # http://localhost:3000
```

## Available Pages

| Route | Description |
|---|---|
| `/` | Landing page with feature overview |
| `/agent` | Chat-based clinical co-pilot (connects to backend or falls back to mock data) |
| `/case/:id` | Detailed case report view with findings, reasoning, and approval |
| `/timeline/:patientId` | Patient timeline with event filters |
| `/patients` | Patient list with search + create |
| `/admin` | Admin dashboard (requires `admin` role) |
| `/auth/login` | Login page |
| `/auth/register` | Registration page |

## Architecture

```
src/
├── app/                    # Next.js App Router pages
│   ├── admin/              # Admin dashboard (role-gated)
│   ├── agent/              # Chat co-pilot
│   ├── auth/               # Login / Register
│   ├── case/[id]/          # Case report viewer
│   ├── patients/           # Patient management
│   ├── timeline/[patientId]/
│   ├── layout.tsx          # Root layout (ThemeProvider + AuthProvider + ErrorBoundary)
│   └── page.tsx            # Landing page
├── components/
│   ├── agent/              # ChatArea, ChatInput, ChatMessage, CitationsSidebar
│   ├── case/               # ImageViewer, FindingsPanel, ReasoningTrace, ApprovalBar
│   ├── landing/            # Hero, features, CTA sections
│   ├── layout/             # Navbar
│   └── shared/             # ThemeToggle, ErrorBoundary, ProtectedRoute, badges, etc.
├── lib/
│   ├── api/                # API client layer
│   │   ├── client.ts       # Singleton ApiClient with auth token injection
│   │   ├── types.ts        # All API request/response interfaces
│   │   └── index.ts        # Barrel re-export
│   ├── constants.ts        # Centralised route/key/default constants
│   ├── hooks.ts            # React data-fetching hooks
│   ├── mock-data.ts        # Demo/fallback data
│   ├── types.ts            # Frontend domain types
│   └── utils.ts            # cn(), formatDate()
└── providers/
    ├── AuthProvider.tsx     # JWT auth context + login/register/logout
    └── ThemeProvider.tsx    # next-themes wrapper
```

## Key Design Decisions

- **API client singleton** (`apiClient`) auto-injects `Authorization: Bearer <token>` for authenticated requests.
- **Mock fallback** — every page that calls the backend gracefully falls back to mock data when the API is unreachable.
- **ErrorBoundary** wraps the app at the layout level; individual pages have dedicated `error.tsx` files.
- **Accessibility** — ARIA roles/labels throughout, `<label>` for all inputs, `prefers-reduced-motion` support, skip-to-content link.
- **No `dangerouslySetInnerHTML`** — all message rendering uses safe React elements.

## Backend API

The frontend expects a FastAPI backend at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api/v1`).

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/patients` | GET/POST | List / create patients |
| `/patients/:id` | GET | Patient details |
| `/patients/:id/timeline` | GET | Patient timeline events |
| `/patients/:id/reports` | GET | Patient reports |
| `/cases/analyze` | POST | Run case analysis |
| `/cases/reports/:id` | GET | Fetch report |
| `/cases/approve` | POST | Approve/reject report |
| `/auth/login` | POST | Login (JWT) |
| `/auth/register` | POST | Register |
| `/auth/me` | GET | Current user |

## Scripts

```bash
npm run dev       # Development server
npm run build     # Production build
npm run start     # Start production server
npm run lint      # ESLint
```

## Tech Stack

- **Next.js 14** (App Router, TypeScript)
- **React 18** (Client Components)
- **Tailwind CSS 3.4** (custom design tokens)
- **framer-motion** (animations)
- **lucide-react** (icons)
- **next-themes** (dark mode)
