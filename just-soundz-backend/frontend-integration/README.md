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
