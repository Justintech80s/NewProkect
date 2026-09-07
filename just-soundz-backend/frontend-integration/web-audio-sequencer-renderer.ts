import type { LocalBeatPlan, DrumPattern, BassNote, StepEvent } from "./local-sequencer.js";

export type LocalSampleKit = {
  kick: AudioBuffer;
  snare: AudioBuffer;
  hat: AudioBuffer;
  ghostSnare?: AudioBuffer;
};

export class JustMakerWebAudioSequencerRenderer {
  constructor(private readonly context: BaseAudioContext) {}

  schedule(
    plan: LocalBeatPlan,
    kit: LocalSampleKit,
    destination: AudioNode,
    startTime = this.context.currentTime + 0.05,
  ): number {
    const secondsPerStep = 60 / plan.bpm / 4;
    let cursor = startTime;

    for (const section of plan.sections) {
      const pattern = plan.drums[section.name];
      const bass = plan.bass[section.name];

      for (let bar = 0; bar < section.bars; bar += 1) {
        const barStart = cursor + bar * plan.stepsPerBar * secondsPerStep;
        this.scheduleDrums(pattern, kit, destination, barStart, secondsPerStep, bar);
        this.scheduleBass(bass, destination, barStart, secondsPerStep, section.energy);
      }

      cursor += section.bars * plan.stepsPerBar * secondsPerStep;
    }

    return cursor;
  }

  private scheduleDrums(
    pattern: DrumPattern,
    kit: LocalSampleKit,
    destination: AudioNode,
    barStart: number,
    secondsPerStep: number,
    barIndex: number,
  ): void {
    this.scheduleEvents(pattern.kick, kit.kick, destination, barStart, secondsPerStep, barIndex);
    this.scheduleEvents(pattern.snare, kit.snare, destination, barStart, secondsPerStep, barIndex);
    this.scheduleEvents(pattern.hats, kit.hat, destination, barStart, secondsPerStep, barIndex);
    if (kit.ghostSnare) {
      this.scheduleEvents(pattern.ghostSnare, kit.ghostSnare, destination, barStart, secondsPerStep, barIndex);
    }
  }

  private scheduleEvents(
    events: StepEvent[],
    sample: AudioBuffer,
    destination: AudioNode,
    barStart: number,
    secondsPerStep: number,
    barIndex: number,
  ): void {
    for (const event of events) {
      if (!this.probabilityGate(event.probability, event.step, barIndex)) continue;

      const source = this.context.createBufferSource();
      const gain = this.context.createGain();
      source.buffer = sample;
      gain.gain.value = event.velocity;
      source.connect(gain);
      gain.connect(destination);

      const when = Math.max(
        this.context.currentTime,
        barStart + event.step * secondsPerStep + event.offsetMs / 1000,
      );
      source.start(when);
    }
  }

  private scheduleBass(
    notes: BassNote[],
    destination: AudioNode,
    barStart: number,
    secondsPerStep: number,
    energy: number,
  ): void {
    for (const note of notes) {
      const osc = this.context.createOscillator();
      const gain = this.context.createGain();
      const filter = this.context.createBiquadFilter();

      osc.type = "triangle";
      osc.frequency.value = 440 * Math.pow(2, (note.midi - 69) / 12);
      filter.type = "lowpass";
      filter.frequency.value = 420 + energy * 360;
      filter.Q.value = 0.7;

      const start = Math.max(
        this.context.currentTime,
        barStart + note.step * secondsPerStep + note.offsetMs / 1000,
      );
      const end = start + Math.max(secondsPerStep * note.lengthSteps, 0.06);

      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(Math.max(0.02, note.velocity * 0.25), start + 0.008);
      gain.gain.exponentialRampToValueAtTime(0.0001, end);

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(destination);
      osc.start(start);
      osc.stop(end + 0.02);
    }
  }

  private probabilityGate(probability: number, step: number, barIndex: number): boolean {
    if (probability >= 1) return true;
    const x = Math.sin((step + 1) * 12.9898 + (barIndex + 1) * 78.233) * 43758.5453;
    const deterministic = x - Math.floor(x);
    return deterministic <= probability;
  }
}
