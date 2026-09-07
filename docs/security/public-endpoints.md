# Just Maker Public Endpoint Classification

Pass 2 classifies the following routes as intentionally public at the repository level:

- GET /
- GET /health
- GET /ready
- GET /v1/generation-workers
- GET /v1/music-brain/status
- POST /v1/music-brain/search
- POST /v1/music-brain/rights/check
- POST /v1/render
- POST /v1/generate

All user-scoped routes for jobs, retries, feedback, private artifacts, preferences, creative memory, and usage require authenticated user context.

Public classification is explicit rather than accidental. Production operators may place additional gateway authentication in front of public generation routes without changing the internal job-ownership model.
