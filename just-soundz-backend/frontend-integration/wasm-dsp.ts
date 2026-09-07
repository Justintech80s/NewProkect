export type JustMakerWasmDsp = {
  remove_dc_interleaved_wasm(samples: Float32Array<ArrayBufferLike>, channels: number): Float32Array<ArrayBufferLike>;
  high_pass_interleaved_wasm(
    samples: Float32Array<ArrayBufferLike>,
    channels: number,
    sampleRate: number,
    cutoffHz: number,
  ): Float32Array<ArrayBufferLike>;
  soft_clip_interleaved_wasm(samples: Float32Array<ArrayBufferLike>, drive: number): Float32Array<ArrayBufferLike>;
  normalize_peak_interleaved_wasm(samples: Float32Array<ArrayBufferLike>, targetPeakDb: number): Float32Array<ArrayBufferLike>;
  apply_gain_db_interleaved_wasm(samples: Float32Array<ArrayBufferLike>, gainDb: number): Float32Array<ArrayBufferLike>;
  rms_dbfs_wasm(samples: Float32Array<ArrayBufferLike>): number;
  peak_dbfs_wasm(samples: Float32Array<ArrayBufferLike>): number;
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
