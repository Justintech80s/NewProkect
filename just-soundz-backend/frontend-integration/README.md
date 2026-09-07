# Just Maker Composition frontend integration

This folder contains the drop-in client for connecting the Just Soundz AI Companion Composition interface to the existing Just Maker backend.

## Backend capabilities already available

The backend already provides:

- CORS support for `https://just-soundz-ai-companion.justmarsh88.chatgpt.site`
- `POST /v1/jobs` to queue generation
- `GET /v1/jobs/{job_id}` to poll stage/progress/results
- `POST /v1/jobs/{job_id}/retry` to retry eligible failed jobs
- `POST /v1/jobs/{job_id}/artifacts/{artifact_id}/signed-url` for private playback/download links
- authenticated user isolation and quotas

## Basic usage

```js
import { JustMakerCompositionClient } from "./composition-client.js";

const client = new JustMakerCompositionClient({
  apiBaseUrl: JUST_MAKER_API_URL,
  getAccessToken: async () => {
    // Return the current signed-in user's Supabase access token.
    return session.access_token;
  },
});

const result = await client.generateAndWait(
  {
    prompt: "original soulful chopped-texture hip-hop instrumental",
    genre: "hip hop",
    mood: "uplifting",
    bpm: 92,
    key: "C minor",
    duration: 180,
    make_stems: true,
  },
  {
    onQueued: ({ job_id }) => console.log("queued", job_id),
    onProgress: ({ stage, progress }) => {
      console.log(stage, Math.round(progress * 100));
    },
    onComplete: ({ playback }) => {
      audioElement.src = playback.url;
    },
  },
);
```

## Recommended Composition UI mapping

- Prompt text area -> `prompt`
- Genre selector -> `genre`
- Mood selector -> `mood`
- BPM -> `bpm`
- Key -> `key`
- Duration -> `duration`
- Generate button -> `generateAndWait()`
- Progress bar -> `onProgress`
- Audio player -> returned `playback.url`
- Save/Download -> use the same signed master URL while valid

## Security

Do not put the Supabase service-role key, GPU worker token, Kafka credentials, or backend secrets into the Site frontend. The browser only needs the signed-in user's access token and the public Just Maker API base URL.

The master audio link is generated as a short-lived signed URL from private storage.

## Current deployment dependency

The client is ready to connect once two runtime values exist:

1. a deployed public HTTPS Just Maker API URL;
2. a signed-in user session that can supply a Supabase bearer token.

Professional audio output still requires at least one real configured GPU generation worker behind the Just Maker router.


## Free Engine browser DSP

The browser integration now includes a local TypeScript/Web Audio engine that can load the Rust DSP WebAssembly package created by the Rust/WASM build.

```ts
import { JustMakerBrowserAudioEngine } from "./browser-audio-engine.js";

const engine = new JustMakerBrowserAudioEngine({
  wasmLoader: () => import("./pkg/just_maker_dsp.js"),
});

const decoded = await engine.decodeAudioBytes(await file.arrayBuffer());
const { buffer, metrics } = await engine.processAudioBuffer(decoded, {
  removeDc: true,
  highPassHz: 24,
  softClipDrive: 1.18,
  normalizePeakDb: -1,
});

await engine.play(buffer);
console.log(metrics);
```

This layer does not alter the current Composition UI. It provides reusable local audio services for later free-engine steps: browser rendering, humanized sequencing, sample-chop processing, local mastering and WAV export.

The browser receives no service-role, GPU, Kafka or database secrets. DSP runs on the user's own device.


## Free Engine Step 3: local sequencing

The browser layer now includes a deterministic local beat sequencer and Web Audio renderer.

It generates:
- 16-step drum patterns with swing and bounded microtiming;
- velocity humanization and probabilistic ghost notes;
- section-specific patterns rather than one copied loop;
- bass notes tied primarily to kick positions and scale tones;
- intro, verses, hooks, breakdown and outro with different density/energy;
- deterministic seeds so the same seed can reproduce a beat plan.

The renderer schedules drum sample playback and a lightweight synthesized bass directly through Web Audio. This is intended as the free CPU/browser path and does not require GPU hosting.


## Free Engine Step 4: local sample chopping

The browser engine now supports transient-aware slicing of user-supplied source audio and creates section-specific chop arrangements locally.

Capabilities:
- amplitude/energy transient detection with bounded slice count;
- short chop reordering instead of static loop playback;
- per-chop pitch changes;
- optional reverse chops;
- gated slice lengths and deliberate silence gaps;
- different chop sequences for intro, verse, hook, breakdown and outro;
- deterministic seeds for reproducible variations;
- Web Audio scheduling with local playback-rate pitch shifting.

The local chopper requires an explicit rights attestation before a plan can be built. It is intended for audio the user owns, has cleared, or is licensed to use.
