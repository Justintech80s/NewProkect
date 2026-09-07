export type StepEvent = {
  step: number;
  velocity: number;
  offsetMs: number;
  probability: number;
};

export type DrumPattern = {
  kick: StepEvent[];
  snare: StepEvent[];
  hats: StepEvent[];
  ghostSnare: StepEvent[];
};

export type BassNote = {
  step: number;
  midi: number;
  velocity: number;
  lengthSteps: number;
  offsetMs: number;
};

export type SectionPlan = {
  name: string;
  bars: number;
  energy: number;
  drumDensity: number;
  bassActivity: number;
  variation: number;
};

export type LocalBeatPlan = {
  bpm: number;
  swing: number;
  stepsPerBar: number;
  seed: number;
  sections: SectionPlan[];
  drums: Record<string, DrumPattern>;
  bass: Record<string, BassNote[]>;
};

type BuildOptions = {
  bpm?: number;
  swing?: number;
  seed?: number;
  rootMidi?: number;
  scale?: number[];
  prompt?: string;
};

class DeterministicRandom {
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

  chance(probability: number): boolean {
    return this.next() < probability;
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function hashPrompt(prompt: string): number {
  let hash = 2166136261;
  for (const char of prompt) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

export class JustMakerLocalSequencer {
  readonly stepsPerBar = 16;

  build(options: BuildOptions = {}): LocalBeatPlan {
    const prompt = String(options.prompt || "").toLowerCase();
    const bpm = clamp(Number(options.bpm ?? this.inferBpm(prompt)), 55, 180);
    const swing = clamp(Number(options.swing ?? this.inferSwing(prompt)), 0, 0.72);
    const seed = Number.isInteger(options.seed)
      ? Number(options.seed)
      : hashPrompt(prompt || "just-maker-free-engine");
    const rootMidi = clamp(Math.round(options.rootMidi ?? 36), 24, 60);
    const scale = (options.scale?.length ? options.scale : [0, 3, 5, 7, 10]).map(Number);

    const sections = this.buildSections(prompt);
    const drums: Record<string, DrumPattern> = {};
    const bass: Record<string, BassNote[]> = {};

    sections.forEach((section, index) => {
      const random = new DeterministicRandom(seed + index * 104729);
      drums[section.name] = this.buildDrumPattern(section, swing, random, prompt);
      bass[section.name] = this.buildBassPattern(
        section,
        drums[section.name],
        rootMidi,
        scale,
        swing,
        random,
      );
    });

    return {
      bpm,
      swing,
      stepsPerBar: this.stepsPerBar,
      seed,
      sections,
      drums,
      bass,
    };
  }

  private buildSections(prompt: string): SectionPlan[] {
    const boomBap = /90s|boom bap|east coast/.test(prompt);
    const base: SectionPlan[] = [
      { name: "intro", bars: 4, energy: 0.42, drumDensity: 0.45, bassActivity: 0.30, variation: 0.18 },
      { name: "verse-a", bars: 16, energy: 0.62, drumDensity: 0.72, bassActivity: 0.58, variation: 0.38 },
      { name: "hook", bars: 8, energy: 0.84, drumDensity: 0.86, bassActivity: 0.72, variation: 0.50 },
      { name: "verse-b", bars: 16, energy: 0.68, drumDensity: 0.76, bassActivity: 0.64, variation: 0.58 },
      { name: "breakdown", bars: 8, energy: 0.46, drumDensity: 0.38, bassActivity: 0.42, variation: 0.68 },
      { name: "hook-final", bars: 8, energy: 0.90, drumDensity: 0.92, bassActivity: 0.80, variation: 0.82 },
      { name: "outro", bars: 4, energy: 0.34, drumDensity: 0.34, bassActivity: 0.25, variation: 0.90 },
    ];

    if (boomBap) {
      return base.map((section) => ({
        ...section,
        drumDensity: clamp(section.drumDensity + 0.05, 0, 1),
        variation: clamp(section.variation + 0.05, 0, 1),
      }));
    }
    return base;
  }

  private buildDrumPattern(
    section: SectionPlan,
    swing: number,
    random: DeterministicRandom,
    prompt: string,
  ): DrumPattern {
    const kickSteps = new Set<number>([0, 7, 10]);
    const snareSteps = new Set<number>([4, 12]);

    if (section.energy > 0.75) {
      kickSteps.add(14);
      if (random.chance(0.65)) kickSteps.add(3);
    }
    if (section.drumDensity < 0.5) {
      kickSteps.delete(10);
    }
    if (/east coast|boom bap|90s/.test(prompt) && random.chance(0.75)) {
      kickSteps.add(9);
    }

    const kick = [...kickSteps]
      .sort((a, b) => a - b)
      .map((step) => this.event(step, 0.82, 1.0, swing, random, 7));

    const snare = [...snareSteps]
      .map((step) => this.event(step, 0.88, 1.0, swing, random, 6));

    const hats: StepEvent[] = [];
    for (let step = 0; step < this.stepsPerBar; step += 2) {
      const accent = step % 4 === 0 ? 0.70 : 0.56;
      hats.push(this.event(step, accent, 0.94, swing, random, 8));
      if (section.drumDensity > 0.78 && step % 4 === 2 && random.chance(0.35)) {
        hats.push(this.event(step + 1, 0.38, 0.72, swing, random, 10));
      }
    }

    const ghostSnare: StepEvent[] = [];
    const ghostCandidates = [3, 6, 11, 15];
    for (const step of ghostCandidates) {
      if (random.chance(0.18 + section.variation * 0.45)) {
        ghostSnare.push(this.event(step, 0.26, 0.72, swing, random, 12));
      }
    }

    return { kick, snare, hats, ghostSnare };
  }

  private buildBassPattern(
    section: SectionPlan,
    drums: DrumPattern,
    rootMidi: number,
    scale: number[],
    swing: number,
    random: DeterministicRandom,
  ): BassNote[] {
    const notes: BassNote[] = [];
    const kickSteps = drums.kick.map((event) => event.step);

    for (let index = 0; index < kickSteps.length; index += 1) {
      const step = kickSteps[index];
      if (index > 0 && !random.chance(section.bassActivity)) continue;

      const degree = index === 0 ? 0 : scale[Math.floor(random.range(0, scale.length))] ?? 0;
      const octaveShift = random.chance(0.18 * section.variation) ? 12 : 0;
      notes.push({
        step,
        midi: rootMidi + degree + octaveShift,
        velocity: clamp(0.68 + random.range(-0.09, 0.10), 0.45, 0.92),
        lengthSteps: random.chance(0.25 + section.variation * 0.25) ? 3 : 2,
        offsetMs: this.microtiming(step, swing, random, 9),
      });
    }

    if (section.energy > 0.78 && random.chance(0.70)) {
      const pickupStep = 15;
      const approach = scale[Math.min(1, scale.length - 1)] ?? 0;
      notes.push({
        step: pickupStep,
        midi: rootMidi + approach,
        velocity: 0.52,
        lengthSteps: 1,
        offsetMs: this.microtiming(pickupStep, swing, random, 8),
      });
    }

    return notes.sort((a, b) => a.step - b.step);
  }

  private event(
    step: number,
    baseVelocity: number,
    probability: number,
    swing: number,
    random: DeterministicRandom,
    humanizeMs: number,
  ): StepEvent {
    return {
      step,
      velocity: clamp(baseVelocity + random.range(-0.08, 0.08), 0.08, 1),
      offsetMs: this.microtiming(step, swing, random, humanizeMs),
      probability,
    };
  }

  private microtiming(
    step: number,
    swing: number,
    random: DeterministicRandom,
    humanizeMs: number,
  ): number {
    const swung16th = step % 2 === 1 ? swing * 42 : 0;
    return Math.round(swung16th + random.range(-humanizeMs, humanizeMs));
  }

  private inferBpm(prompt: string): number {
    if (/90s|boom bap|east coast/.test(prompt)) return 92;
    if (/trap|drill/.test(prompt)) return 140;
    if (/house|dance/.test(prompt)) return 124;
    return 100;
  }

  private inferSwing(prompt: string): number {
    if (/90s|boom bap|east coast|swing/.test(prompt)) return 0.58;
    if (/live drums|organic/.test(prompt)) return 0.34;
    return 0.18;
  }
}
