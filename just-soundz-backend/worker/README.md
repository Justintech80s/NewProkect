# Just Soundz GPU Worker Contract

The web backend is intentionally separated from heavy music-generation models.

A compatible worker exposes:

## POST /generate

Request:

```json
{
  "plan": {
    "original_prompt": "dark futuristic club instrumental",
    "bpm": 102,
    "key": "F# minor",
    "duration_seconds": 120,
    "arrangement": []
  },
  "variation": 0
}
```

Response:

```json
{
  "provider": "approved-music-model",
  "audio_path": "/shared/output/abc.wav",
  "audio_url": "https://cdn.example.com/abc.wav",
  "metadata": {
    "seed": 123,
    "model": "provider-model-name"
  }
}
```

The worker can internally use any commercially permitted music model or hosted API.
Keeping this contract stable means Just Soundz can swap music engines without
changing its phone/web interface.
