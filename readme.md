# Shadowing Coach — Architecture

## Overview

Visually guided speech shadowing coach. Users upload a master audio sentence, the system analyzes it into a synchronized "speaking blueprint", and the user can practice shadowing with real-time visual feedback.

UX feel: karaoke + rhythm game + speech conductor + pronunciation coach.

---

## Project Structure

```
abhyas/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py       # Settings: sample rate, Whisper path, CUDA config
│   │   ├── routers/
│   │   │   └── shadow.py       # API endpoints: analyze-master, compare-attempt
│   │   ├── schemas/
│   │   │   └── shadow_schema.py # Pydantic models for request/response
│   │   ├── services/
│   │   │   ├── feature_service.py  # librosa: RMS, pitch, pause detection, CPS
│   │   │   ├── whisper_service.py  # faster-whisper transcription with timestamps
│   │   │   └── scoring_service.py  # Multi-dimensional DTW-based comparison
│   │   ├── utils/
│   │   │   └── audio_utils.py  # Placeholder for audio utilities
│   │   └── main.py             # FastAPI app entry point
│   ├── models/
│   │   └── faster-whisper-large-v3/  # Whisper model (not in git)
│   ├── temp/                   # Uploaded audio temp files (not in git)
│   └── requirements.txt
│
├── frontend/                   # SvelteKit SPA
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api.ts          # Axios instance → http://127.0.0.1:8000
│   │   │   ├── types.ts        # TypeScript interfaces
│   │   │   ├── stores.ts       # Legacy Svelte stores (unused)
│   │   │   └── components/
│   │   │       ├── UploadZone.svelte  # Drag-drop file upload
│   │   │       ├── Timeline.svelte    # SVG visualization (core)
│   │   │       └── ScoreCard.svelte   # Score display with gauges
│   │   └── routes/
│   │       ├── +page.svelte    # Main SPA (all UI orchestrated here)
│   │       ├── +layout.svelte  # Root layout
│   │       └── layout.css      # Global styles + Tailwind import
│   ├── package.json
│   └── vite.config.ts
│
└── docs/
    └── ARCHITECTURE.md         # This file
```

---

## Backend

### Tech Stack
- **FastAPI** — REST API server
- **faster-whisper** (large-v3) — transcription with word-level timestamps (CUDA, float16)
- **librosa** — audio feature extraction (RMS, YIN pitch, change-point score)
- **scipy** — median filtering, signal processing
- **numpy** — array operations

### Endpoints

#### `POST /shadow/analyze-master`
Upload a single audio file. Returns:

| Field | Type | Description |
|---|---|---|
| `words` | `[{word, start, end}]` | Transcribed words with timestamps |
| `times` | `[float]` | Per-frame time values (seconds) |
| `rms` | `[float]` | RMS energy envelope |
| `pitch` | `[float]` | YIN pitch contour (Hz, 0 = unvoiced) |
| `pause_mask` | `[bool]` | True where RMS < 15th percentile |
| `pause_regions` | `[{start, end}]` | Contiguous pause blocks (>= 50ms) |
| `cps` | `[float]` | Change-point score (smoothed delta RMS) |
| `duration` | `float` | Total audio duration (seconds) |
| `sample_rate` | `int` | Sample rate (always 16000) |

#### `POST /shadow/compare-attempt`
Upload master + user audio. Returns:

| Field | Description |
|---|---|
| `overall` | Weighted composite score (0-100) |
| `timing` | Duration ratio match (0-100) |
| `pitch` | DTW distance on pitch contours (0-100) |
| `rhythm` | DTW distance on RMS envelopes (0-100) |
| `pacing` | DTW distance on CPS (0-100) |

### Scoring Formula
```
overall = timing * 0.15 + pitch * 0.35 + rhythm * 0.25 + pacing * 0.25
```
DTW distances converted via `score = 100 * exp(-dist / 0.5)`, clipped to [0, 100].

### Key Design Decisions
- Model loads **lazily** (on first request), not on import — avoids CUDA OOM at startup
- All temp files cleaned up in `finally` blocks
- No matplotlib rendering server-side — clean JSON only
- No silent CPU fallback — CUDA required
- Minimum pause region: 50ms

### How to Run
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Frontend

### Tech Stack
- **SvelteKit 2** (Svelte 5 runes mode)
- **TypeScript** (strict mode)
- **Tailwind CSS 4** (via Vite plugin)
- **Vite 8**
- **Axios** — HTTP client

### Page Flow (`+page.svelte`)

1. **Upload** — User drops/selects audio file via `UploadZone`
2. **Analyze** — POST `/shadow/analyze-master`, receives reference data
3. **Blueprint** — `Timeline` renders SVG with all lanes
4. **Playback** — User plays audio, cursor moves, words highlight
5. **Record** — MediaRecorder captures mic, auto-stops at master duration
6. **Compare** — POST `/shadow/compare-attempt`, receives scores
7. **Results** — `ScoreCard` shows overall + sub-scores

### Timeline Visualization (`Timeline.svelte`)

SVG-based rendering with these lanes:

| Lane | Y Position | Description |
|---|---|---|
| Word Track | 0–48 | Words positioned by start time, current word highlighted blue |
| Pitch | 52–158 | Smooth polyline, normalized 0→maxHz, vertical label "PITCH" |
| Volume | 166–248 | Filled area chart, vertical label "VOLUME" |
| Pause Regions | Full height | Semi-transparent red blocks |
| Cursor | Full height | White vertical line at `currentTime` |

- Responsive: fills container width, scrolls horizontally for long audio
- Grid lines for reference
- Time labels every 2 seconds
- Auto-scroll follows current word during playback
- Click anywhere to seek

### Audio Playback
- Browser `<Audio>` element from `URL.createObjectURL(file)`
- `requestAnimationFrame` loop synchronizes cursor at ~60fps
- Progress bar + play/pause button in toolbar

### Recording
- `MediaRecorder` with `getUserMedia({ audio: true })`
- Auto-stops after `reference.duration + 500ms`
- Preview via `<audio controls>`
- Re-record supported

### How to Run
```bash
cd frontend
npm install
npm run dev
```

---

## Component API

### UploadZone
```svelte
<UploadZone onFile={(file: File) => void} />
```
Props: `onFile` — called when a file is selected or dropped.

### Timeline
```svelte
<Timeline
  reference={ReferenceData}
  currentTime={number}
  isPlaying={boolean}
  onPlay={fn}
  onPause={fn}
  onSeek={(t: number) => void}
/>
```

### ScoreCard
```svelte
<ScoreCard score={ScoreData} />
```
ScoreData: `{ overall: number, timing: number, pitch: number, rhythm: number, pacing: number }`

---

## Key Types (`types.ts`)

```typescript
interface Word { word: string; start: number; end: number }
interface PauseRegion { start: number; end: number }
interface ReferenceData {
  words: Word[]; times: number[]; rms: number[]; pitch: number[];
  pause_mask: boolean[]; pause_regions: PauseRegion[]; cps: number[];
  duration: number; sample_rate: number;
}
interface ScoreData {
  overall: number; timing: number; pitch: number; rhythm: number; pacing: number;
}
```

---

## Design Constraints
- No authentication
- No SSR complexity
- No WebSockets (yet)
- Single-page application only
- Backend returns clean JSON (no embedded graphs)
- CUDA required, no silent CPU fallback
- Matplotlib removed from API flow
- Gradio removed entirely
