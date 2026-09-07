export type SampleSlice = {
  id: number;
  startFrame: number;
  endFrame: number;
  peak: number;
};

export type ChopEvent = {
  sliceId: number;
  step: number;
  velocity: number;
  semitones: number;
  reverse: boolean;
  gate: number;
};

export type ChopSection = {
  name: string;
  bars: number;
  events: ChopEvent[];
};

export type SampleChopPlan = {
  sourcePolicy: "user-owned-cleared-or-licensed";
  sampleRate: number;
  channels: number;
  bpm: number;
  stepsPerBar: number;
  slices: SampleSlice[];
  sections: ChopSection[];
  seed: number;
};

export type TransientOptions = {
  threshold?: number;
  minSpacingMs?: number;
  windowFrames?: number;
  maxSlices?: number;
};

type BuildOptions = {
  bpm?: number;
  seed?: number;
  prompt?: string;
  sections?: Array<{ name: string; bars: number; energy?: number }>;
  rightsAttested: boolean;
};

class Random {
  private state: number;
  constructor(seed: number) {
    this.state = (seed >>> 0) || 1;
  }
  next(): number {
    this.state ^= this.state << 13;
    this.state ^= this.state >>> 17;
    this.state ^= this.state << 5;
    return (this.state >>> 0) / 0xffffffff;
  }
  range(min: number, max: number): number {
    return min + (max - min) * this.next();
  }
  pick<T>(items: readonly T[]): T {
    return items[Math.min(items.length - 1, Math.floor(this.next() * items.length))];
  }
  chance(p: number): boolean {
    return this.next() < p;
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function hashText(text: string): number {
  let hash = 2166136261;
  for (const char of text) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

export class JustMakerLocalSampleChopper {
  readonly stepsPerBar = 16;

  detectTransients(
    samples: Float32Array<ArrayBufferLike>,
    sampleRate: number,
    channels: number,
    options: TransientOptions = {},
  ): SampleSlice[] {
    if (!(samples instanceof Float32Array)) throw new Error("samples must be Float32Array");
    if (!Number.isFinite(sampleRate) || sampleRate <= 0) throw new Error("sampleRate must be > 0");
    if (!Number.isInteger(channels) || channels <= 0) throw new Error("channels must be positive");
    if (samples.length % channels !== 0) throw new Error("samples must be interleaved by channel");

    const totalFrames = samples.length / channels;
    if (totalFrames < 2) {
      return [{ id: 0, startFrame: 0, endFrame: totalFrames, peak: this.framePeak(samples, 0, channels) }];
    }

    const threshold = clamp(Number(options.threshold ?? 0.10), 0.01, 1);
    const windowFrames = Math.max(16, Math.round(options.windowFrames ?? sampleRate * 0.006));
    const minSpacingFrames = Math.max(
      windowFrames,
      Math.round(sampleRate * (Number(options.minSpacingMs ?? 70) / 1000)),
    );
    const maxSlices = Math.max(1, Math.min(64, Math.round(options.maxSlices ?? 16)));

    const novelty: Array<{ frame: number; score: number }> = [];
    let previousEnergy = 0;

    for (let frame = 0; frame < totalFrames; frame += windowFrames) {
      const end = Math.min(totalFrames, frame + windowFrames);
      let energy = 0;
      let peak = 0;
      for (let f = frame; f < end; f += 1) {
        let mono = 0;
        for (let ch = 0; ch < channels; ch += 1) {
          mono += Math.abs(samples[f * channels + ch] || 0);
        }
        mono /= channels;
        energy += mono;
        peak = Math.max(peak, mono);
      }
      energy /= Math.max(1, end - frame);
      const flux = Math.max(0, energy - previousEnergy);
      const score = flux * 0.72 + peak * 0.28;
      if (score >= threshold) novelty.push({ frame, score });
      previousEnergy = energy * 0.75 + previousEnergy * 0.25;
    }

    const boundaries = [0];
    for (const candidate of novelty.sort((a, b) => b.score - a.score)) {
      if (boundaries.length >= maxSlices) break;
      if (boundaries.every((existing) => Math.abs(existing - candidate.frame) >= minSpacingFrames)) {
        boundaries.push(candidate.frame);
      }
    }

    boundaries.sort((a, b) => a - b);
    const slices: SampleSlice[] = [];
    for (let i = 0; i < boundaries.length; i += 1) {
      const startFrame = boundaries[i];
      const endFrame = i + 1 < boundaries.length ? boundaries[i + 1] : totalFrames;
      if (endFrame <= startFrame) continue;
      slices.push({
        id: slices.length,
        startFrame,
        endFrame,
        peak: this.slicePeak(samples, startFrame, endFrame, channels),
      });
    }

    return slices.length
      ? slices
      : [{ id: 0, startFrame: 0, endFrame: totalFrames, peak: this.slicePeak(samples, 0, totalFrames, channels) }];
  }

  buildPlan(
    slices: SampleSlice[],
    sampleRate: number,
    channels: number,
    options: BuildOptions,
  ): SampleChopPlan {
    if (!options.rightsAttested) {
      throw new Error("Local sample chopping requires user-owned, cleared, or licensed source audio");
    }
    if (!slices.length) throw new Error("At least one sample slice is required");

    const prompt = String(options.prompt || "").toLowerCase();
    const bpm = clamp(Number(options.bpm ?? (/90s|boom bap|east coast/.test(prompt) ? 92 : 100)), 55, 180);
    const seed = Number.isInteger(options.seed) ? Number(options.seed) : hashText(prompt || "just-maker-chops");
    const random = new Random(seed);
    const sections = options.sections?.length
      ? options.sections
      : [
          { name: "intro", bars: 4, energy: 0.35 },
          { name: "verse-a", bars: 16, energy: 0.58 },
          { name: "hook", bars: 8, energy: 0.82 },
          { name: "verse-b", bars: 16, energy: 0.66 },
          { name: "breakdown", bars: 8, energy: 0.42 },
          { name: "hook-final", bars: 8, energy: 0.90 },
          { name: "outro", bars: 4, energy: 0.30 },
        ];

    const sliceIds = slices.map((slice) => slice.id);
    const tonalPitch = /90s|boom bap|east coast|sample chop/.test(prompt)
      ? [-5, -3, 0, 2, 3]
      : [-2, 0, 2, 5];

    const plannedSections: ChopSection[] = sections.map((section, sectionIndex) => {
      const energy = clamp(Number(section.energy ?? 0.6), 0, 1);
      const density = Math.max(3, Math.min(10, Math.round(3 + energy * 7)));
      const events: ChopEvent[] = [];
      const usedSteps = new Set<number>();

      for (let i = 0; i < density; i += 1) {
        let step = Math.floor(random.range(0, this.stepsPerBar));
        let guard = 0;
        while (usedSteps.has(step) && guard < 16) {
          step = (step + 1 + Math.floor(random.range(0, 3))) % this.stepsPerBar;
          guard += 1;
        }
        usedSteps.add(step);

        const baseSlice = sliceIds[(i + sectionIndex) % sliceIds.length];
        const alternate = random.chance(0.52) ? random.pick(sliceIds) : baseSlice;
        events.push({
          sliceId: alternate,
          step,
          velocity: clamp(0.56 + random.range(-0.08, 0.25) + energy * 0.10, 0.35, 1),
          semitones: random.pick(tonalPitch),
          reverse: energy > 0.55 && random.chance(0.10 + sectionIndex * 0.015),
          gate: clamp(0.42 + random.range(-0.10, 0.42), 0.20, 0.95),
        });
      }

      events.sort((a, b) => a.step - b.step);

      // Deliberate gaps keep the result from becoming one continuous loop.
      if (events.length > 4) {
        const gapIndex = Math.floor(random.range(1, events.length - 1));
        events.splice(gapIndex, 1);
      }

      return {
        name: section.name,
        bars: Math.max(1, Math.round(section.bars)),
        events,
      };
    });

    return {
      sourcePolicy: "user-owned-cleared-or-licensed",
      sampleRate,
      channels,
      bpm,
      stepsPerBar: this.stepsPerBar,
      slices,
      sections: plannedSections,
      seed,
    };
  }

  private framePeak(samples: Float32Array<ArrayBufferLike>, frame: number, channels: number): number {
    let peak = 0;
    for (let ch = 0; ch < channels; ch += 1) {
      peak = Math.max(peak, Math.abs(samples[frame * channels + ch] || 0));
    }
    return peak;
  }

  private slicePeak(
    samples: Float32Array<ArrayBufferLike>,
    startFrame: number,
    endFrame: number,
    channels: number,
  ): number {
    let peak = 0;
    for (let frame = startFrame; frame < endFrame; frame += 1) {
      peak = Math.max(peak, this.framePeak(samples, frame, channels));
    }
    return peak;
  }
}
