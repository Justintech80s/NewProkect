import { JustMakerBrowserAudioEngine, type LocalDspMetrics } from "./browser-audio-engine.js";
import { JustMakerLocalSampleChopper, type SampleChopPlan } from "./local-sample-chopper.js";
import { JustMakerLocalSequencer, type LocalBeatPlan } from "./local-sequencer.js";
import { JustMakerSampleChopRenderer } from "./sample-chop-renderer.js";
import { JustMakerWebAudioSequencerRenderer, type LocalSampleKit } from "./web-audio-sequencer-renderer.js";
import { encodePcm16Wav } from "./wav-encoder.js";
import type { WasmModuleLoader } from "./wasm-dsp.js";

export type LocalInstrumentalRenderInput = {
  prompt: string;
  kit: LocalSampleKit;
  sampleSource?: AudioBuffer | null;
  sampleRightsAttested?: boolean;
  bpm?: number;
  swing?: number;
  seed?: number;
  rootMidi?: number;
  scale?: number[];
  sampleRate?: number;
  channels?: 1 | 2;
  drumGain?: number;
  sampleGain?: number;
};

export type LocalInstrumentalRenderResult = {
  beatPlan: LocalBeatPlan;
  chopPlan: SampleChopPlan | null;
  interleaved: Float32Array<ArrayBufferLike>;
  wav: ArrayBuffer;
  metrics: LocalDspMetrics;
  sampleRate: number;
  channels: number;
  durationSeconds: number;
  filename: string;
  renderMode: "local-browser-free-engine";
};

export function beatDurationSeconds(plan: LocalBeatPlan): number {
  const bars = plan.sections.reduce((sum, section) => sum + section.bars, 0);
  return bars * 4 * (60 / plan.bpm);
}

export function interleaveAudioBuffer(buffer: AudioBuffer): Float32Array<ArrayBufferLike> {
  const channels = buffer.numberOfChannels;
  const frames = buffer.length;
  const output = new Float32Array(frames * channels);
  for (let frame = 0; frame < frames; frame += 1) {
    for (let channel = 0; channel < channels; channel += 1) {
      output[frame * channels + channel] = buffer.getChannelData(channel)[frame] || 0;
    }
  }
  return output;
}

export class JustMakerLocalInstrumentalRenderer {
  private readonly wasmLoader: WasmModuleLoader;
  private readonly OfflineAudioContextCtor: typeof OfflineAudioContext | undefined;

  constructor({
    wasmLoader,
    OfflineAudioContextCtor = globalThis.OfflineAudioContext,
  }: {
    wasmLoader: WasmModuleLoader;
    OfflineAudioContextCtor?: typeof OfflineAudioContext;
  }) {
    if (typeof wasmLoader !== "function") throw new Error("wasmLoader is required");
    this.wasmLoader = wasmLoader;
    this.OfflineAudioContextCtor = OfflineAudioContextCtor;
  }

  async render(input: LocalInstrumentalRenderInput): Promise<LocalInstrumentalRenderResult> {
    if (!this.OfflineAudioContextCtor) {
      throw new Error("Offline Web Audio rendering is not available in this browser");
    }
    if (!input.prompt?.trim()) throw new Error("prompt is required");

    const sequencer = new JustMakerLocalSequencer();
    const beatPlan = sequencer.build({
      prompt: input.prompt,
      bpm: input.bpm,
      swing: input.swing,
      seed: input.seed,
      rootMidi: input.rootMidi,
      scale: input.scale,
    });

    const sampleRate = Math.max(22050, Math.min(96000, Math.round(input.sampleRate ?? 44100)));
    const channels = input.channels ?? 2;
    const durationSeconds = beatDurationSeconds(beatPlan) + 2.0;
    const frames = Math.ceil(durationSeconds * sampleRate);
    const offline = new this.OfflineAudioContextCtor(channels, frames, sampleRate);

    const drumBus = offline.createGain();
    const sampleBus = offline.createGain();
    const compressor = offline.createDynamicsCompressor();

    drumBus.gain.value = Math.max(0, Math.min(1.5, input.drumGain ?? 0.92));
    sampleBus.gain.value = Math.max(0, Math.min(1.5, input.sampleGain ?? 0.72));
    compressor.threshold.value = -8;
    compressor.knee.value = 12;
    compressor.ratio.value = 3;
    compressor.attack.value = 0.008;
    compressor.release.value = 0.16;

    drumBus.connect(compressor);
    sampleBus.connect(compressor);
    compressor.connect(offline.destination);

    new JustMakerWebAudioSequencerRenderer(offline).schedule(
      beatPlan,
      input.kit,
      drumBus,
      0.05,
    );

    let chopPlan: SampleChopPlan | null = null;
    if (input.sampleSource) {
      if (!input.sampleRightsAttested) {
        throw new Error(
          "Sample source requires confirmation that it is user-owned, cleared, or licensed",
        );
      }
      const chopper = new JustMakerLocalSampleChopper();
      const interleavedSource = interleaveAudioBuffer(input.sampleSource);
      const slices = chopper.detectTransients(
        interleavedSource,
        input.sampleSource.sampleRate,
        input.sampleSource.numberOfChannels,
        {
          threshold: 0.08,
          minSpacingMs: 70,
          maxSlices: 16,
        },
      );
      chopPlan = chopper.buildPlan(
        slices,
        input.sampleSource.sampleRate,
        input.sampleSource.numberOfChannels,
        {
          rightsAttested: true,
          prompt: input.prompt,
          bpm: beatPlan.bpm,
          seed: beatPlan.seed + 7919,
          sections: beatPlan.sections.map((section) => ({
            name: section.name,
            bars: section.bars,
            energy: section.energy,
          })),
        },
      );
      new JustMakerSampleChopRenderer(offline).schedule(
        chopPlan,
        input.sampleSource,
        sampleBus,
        0.05,
      );
    }

    const rendered = await offline.startRendering();
    const rawInterleaved = interleaveAudioBuffer(rendered);

    const dsp = new JustMakerBrowserAudioEngine({
      wasmLoader: this.wasmLoader,
      AudioContextCtor: undefined,
    });
    const mastered = await dsp.processInterleaved(rawInterleaved, {
      channels,
      sampleRate,
      options: {
        removeDc: true,
        highPassHz: 24,
        softClipDrive: 1.18,
        normalizePeakDb: -1.0,
      },
    });

    const wav = encodePcm16Wav(mastered.samples, {
      channels,
      sampleRate,
    });

    return {
      beatPlan,
      chopPlan,
      interleaved: mastered.samples,
      wav,
      metrics: mastered.metrics,
      sampleRate,
      channels,
      durationSeconds: mastered.samples.length / channels / sampleRate,
      filename: `just-maker-free-${beatPlan.seed}.wav`,
      renderMode: "local-browser-free-engine",
    };
  }
}
