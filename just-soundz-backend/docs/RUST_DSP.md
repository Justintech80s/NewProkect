# Just Maker Rust DSP

Rust is an optional acceleration layer for CPU-heavy digital signal processing.
Python/FastAPI remains the orchestration and AI layer.

## Accelerated primitives

- DC-offset removal
- high-pass filtering
- gain application
- soft clipping
- peak normalization
- RMS measurement
- peak measurement

The first integrations are the mastering engine and stem mixer.

## Build

Install Rust and maturin, then from `just-soundz-backend`:

`pip install -r requirements-rustdsp.txt`

`maturin develop --release -m rust-dsp/Cargo.toml`

The compiled Python extension is named `just_maker_dsp`.

## Fallback behavior

If the Rust extension is not installed, disabled, or fails to import, Just Maker
uses the existing NumPy implementations. Rust is therefore an accelerator, not
a hard runtime dependency.

## Architecture

- Python/FastAPI: AI orchestration and generation planning
- PyTorch/CUDA workers: music generation
- Rust/PyO3: performance-heavy DSP
- Supabase/Postgres: authoritative state
- Kafka: event backbone
- RocksDB: local hot cache

No frontend changes are required.
