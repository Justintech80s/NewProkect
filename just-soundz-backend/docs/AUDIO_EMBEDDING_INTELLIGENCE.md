# Phase 49 — Audio embedding intelligence

Music Brain now has a dedicated sonic representation path in addition to text
metadata embeddings.

Audio embeddings can represent broad sonic similarity such as:

- timbre
- texture
- energy
- instrumentation character
- spectral balance
- rhythmic feel

The embedding backend is designed for a CLAP-compatible or equivalent licensed
audio/text embedding service.

## Rights boundary

General metadata records remain text/reference knowledge only.

The automatic audio-embedding index is for cleared sample assets and user-owned
audio. An audio asset must have an eligible rights status, sampling permission,
and commercial-use permission (except user-owned audio) before it can enter the
automatic sonic index.

## Storage

Cleared audio embeddings are stored separately in
`sample_audio_embeddings` using pgvector. This prevents metadata-only song
records from being confused with sampleable audio assets.

## Retrieval

Music Brain can compare an audio query embedding against cleared sample assets,
allowing searches such as:

- similar drum texture
- similar low-end character
- similar instrumental density
- similar sonic palette

This is similarity retrieval, not melody copying.
