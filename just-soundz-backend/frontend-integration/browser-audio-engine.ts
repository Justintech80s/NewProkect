import { loadJustMakerWasmDsp, type JustMakerWasmDsp, type WasmModuleLoader } from "./wasm-dsp.js";

export type LocalDspOptions = {
  removeDc?: boolean;
  highPassHz?: number | null;
  gainDb?: number;
  softClipDrive?: number | null;
  normalizePeakDb?: number | null;
};

export type LocalDspMetrics = {
  rmsDbfsBefore: number;
  peakDbfsBefore: number;
  rmsDbfsAfter: number;
  peakDbfsAfter: number;
};

export type LocalDspResult = {
  samples: Float32Array<ArrayBufferLike>;
  metrics: LocalDspMetrics;
};

export type PlayableAudio = {
  source: AudioBufferSourceNode;
  stop: () => void;
};

export class JustMakerBrowserAudioEngine {
  private readonly wasmLoader: WasmModuleLoader;
  private readonly AudioContextCtor: typeof AudioContext | undefined;
  private dsp: JustMakerWasmDsp | null = null;
  private context: AudioContext | null = null;

  constructor({
    wasmLoader,
    AudioContextCtor = globalThis.AudioContext,
  }: {
    wasmLoader: WasmModuleLoader;
    AudioContextCtor?: typeof AudioContext;
  }) {
    if (typeof wasmLoader !== "function") {
      throw new Error("wasmLoader is required");
    }
    this.wasmLoader = wasmLoader;
    this.AudioContextCtor = AudioContextCtor;
  }

  async initialize(): Promise<void> {
    if (!this.dsp) {
      this.dsp = await loadJustMakerWasmDsp(this.wasmLoader);
    }
  }

  async processInterleaved(
    samples: Float32Array<ArrayBufferLike>,
    {
      channels,
      sampleRate,
      options = {},
    }: {
      channels: number;
      sampleRate: number;
      options?: LocalDspOptions;
    },
  ): Promise<LocalDspResult> {
    await this.initialize();
    const dsp = this.dsp!;

    if (!(samples instanceof Float32Array)) {
      throw new Error("samples must be a Float32Array");
    }
    if (!Number.isInteger(channels) || channels <= 0) {
      throw new Error("channels must be a positive integer");
    }
    if (!Number.isFinite(sampleRate) || sampleRate <= 0) {
      throw new Error("sampleRate must be > 0");
    }
    if (samples.length % channels !== 0) {
      throw new Error("interleaved sample count must be divisible by channels");
    }

    const rmsDbfsBefore = dsp.rms_dbfs_wasm(samples);
    const peakDbfsBefore = dsp.peak_dbfs_wasm(samples);

    let output = new Float32Array(samples);

    if (options.removeDc !== false) {
      output = dsp.remove_dc_interleaved_wasm(output, channels);
    }

    if (options.highPassHz != null) {
      const cutoff = Math.max(10, Math.min(Number(options.highPassHz), sampleRate * 0.45));
      output = dsp.high_pass_interleaved_wasm(output, channels, sampleRate, cutoff);
    }

    if (options.gainDb != null && Number(options.gainDb) !== 0) {
      output = dsp.apply_gain_db_interleaved_wasm(output, Number(options.gainDb));
    }

    if (options.softClipDrive != null) {
      output = dsp.soft_clip_interleaved_wasm(
        output,
        Math.max(0.01, Math.min(Number(options.softClipDrive), 8)),
      );
    }

    if (options.normalizePeakDb != null) {
      output = dsp.normalize_peak_interleaved_wasm(
        output,
        Math.max(-24, Math.min(Number(options.normalizePeakDb), -0.1)),
      );
    }

    return {
      samples: output,
      metrics: {
        rmsDbfsBefore,
        peakDbfsBefore,
        rmsDbfsAfter: dsp.rms_dbfs_wasm(output),
        peakDbfsAfter: dsp.peak_dbfs_wasm(output),
      },
    };
  }

  async decodeAudioBytes(bytes: ArrayBuffer): Promise<AudioBuffer> {
    const context = await this.getAudioContext();
    return context.decodeAudioData(bytes.slice(0));
  }

  async audioBufferToInterleaved(buffer: AudioBuffer): Promise<Float32Array<ArrayBufferLike>> {
    const channels = buffer.numberOfChannels;
    const frames = buffer.length;
    const interleaved = new Float32Array(frames * channels);

    for (let frame = 0; frame < frames; frame += 1) {
      for (let channel = 0; channel < channels; channel += 1) {
        interleaved[frame * channels + channel] = buffer.getChannelData(channel)[frame];
      }
    }

    return interleaved;
  }

  async interleavedToAudioBuffer(
    samples: Float32Array<ArrayBufferLike>,
    channels: number,
    sampleRate: number,
  ): Promise<AudioBuffer> {
    const context = await this.getAudioContext();
    const frames = Math.floor(samples.length / channels);
    const buffer = context.createBuffer(channels, frames, sampleRate);

    for (let channel = 0; channel < channels; channel += 1) {
      const target = buffer.getChannelData(channel);
      for (let frame = 0; frame < frames; frame += 1) {
        target[frame] = samples[frame * channels + channel];
      }
    }

    return buffer;
  }

  async processAudioBuffer(
    buffer: AudioBuffer,
    options: LocalDspOptions = {},
  ): Promise<{ buffer: AudioBuffer; metrics: LocalDspMetrics }> {
    const interleaved = await this.audioBufferToInterleaved(buffer);
    const processed = await this.processInterleaved(interleaved, {
      channels: buffer.numberOfChannels,
      sampleRate: buffer.sampleRate,
      options,
    });
    return {
      buffer: await this.interleavedToAudioBuffer(
        processed.samples,
        buffer.numberOfChannels,
        buffer.sampleRate,
      ),
      metrics: processed.metrics,
    };
  }

  async play(buffer: AudioBuffer, destination?: AudioNode): Promise<PlayableAudio> {
    const context = await this.getAudioContext();
    if (context.state === "suspended") {
      await context.resume();
    }

    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(destination || context.destination);
    source.start();

    let stopped = false;
    return {
      source,
      stop: () => {
        if (stopped) return;
        stopped = true;
        try {
          source.stop();
        } catch {
          // Source may already have ended.
        }
      },
    };
  }

  async close(): Promise<void> {
    if (this.context && this.context.state !== "closed") {
      await this.context.close();
    }
    this.context = null;
  }

  private async getAudioContext(): Promise<AudioContext> {
    if (this.context && this.context.state !== "closed") {
      return this.context;
    }
    if (!this.AudioContextCtor) {
      throw new Error("Web Audio API is not available in this browser");
    }
    this.context = new this.AudioContextCtor();
    return this.context;
  }
}
