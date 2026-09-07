export type JustMakerWasmDsp = {
  remove_dc_interleaved_wasm(samples: Float32Array, channels: number): Float32Array;
  high_pass_interleaved_wasm(
    samples: Float32Array,
    channels: number,
    sampleRate: number,
    cutoffHz: number,
  ): Float32Array;
  soft_clip_interleaved_wasm(samples: Float32Array, drive: number): Float32Array;
  normalize_peak_interleaved_wasm(samples: Float32Array, targetPeakDb: number): Float32Array;
  apply_gain_db_interleaved_wasm(samples: Float32Array, gainDb: number): Float32Array;
  rms_dbfs_wasm(samples: Float32Array): number;
  peak_dbfs_wasm(samples: Float32Array): number;
};

export type WasmModuleLoader = () => Promise<unknown>;

function assertFunction(module: Record<string, unknown>, name: string): void {
  if (typeof module[name] !== "function") {
    throw new Error(`Just Maker WASM module is missing ${name}`);
  }
}

export async function loadJustMakerWasmDsp(loader: WasmModuleLoader): Promise<JustMakerWasmDsp> {
  if (typeof loader !== "function") {
    throw new Error("A WASM module loader is required");
  }

  const loaded = await loader();
  const module = loaded as Record<string, unknown>;

  const required = [
    "remove_dc_interleaved_wasm",
    "high_pass_interleaved_wasm",
    "soft_clip_interleaved_wasm",
    "normalize_peak_interleaved_wasm",
    "apply_gain_db_interleaved_wasm",
    "rms_dbfs_wasm",
    "peak_dbfs_wasm",
  ];

  for (const name of required) assertFunction(module, name);

  return module as unknown as JustMakerWasmDsp;
}
