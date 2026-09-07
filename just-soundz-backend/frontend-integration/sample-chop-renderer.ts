import type { ChopEvent, SampleChopPlan, SampleSlice } from "./local-sample-chopper.js";

export class JustMakerSampleChopRenderer {
  constructor(private readonly context: BaseAudioContext) {}

  schedule(
    plan: SampleChopPlan,
    sourceBuffer: AudioBuffer,
    destination: AudioNode,
    startTime = this.context.currentTime + 0.05,
  ): number {
    if (sourceBuffer.numberOfChannels < 1) throw new Error("sourceBuffer must contain audio");

    const secondsPerStep = 60 / plan.bpm / 4;
    let cursor = startTime;

    for (const section of plan.sections) {
      for (let bar = 0; bar < section.bars; bar += 1) {
        const barStart = cursor + bar * plan.stepsPerBar * secondsPerStep;
        for (const event of section.events) {
          const slice = plan.slices.find((item) => item.id === event.sliceId);
          if (!slice) continue;
          this.scheduleEvent(event, slice, sourceBuffer, destination, barStart, secondsPerStep);
        }
      }
      cursor += section.bars * plan.stepsPerBar * secondsPerStep;
    }

    return cursor;
  }

  private scheduleEvent(
    event: ChopEvent,
    slice: SampleSlice,
    sourceBuffer: AudioBuffer,
    destination: AudioNode,
    barStart: number,
    secondsPerStep: number,
  ): void {
    const sliceBuffer = event.reverse
      ? this.reverseSlice(sourceBuffer, slice)
      : this.copySlice(sourceBuffer, slice);

    const source = this.context.createBufferSource();
    const gain = this.context.createGain();
    source.buffer = sliceBuffer;
    source.playbackRate.value = Math.pow(2, event.semitones / 12);

    const start = Math.max(this.context.currentTime, barStart + event.step * secondsPerStep);
    const rawDuration = sliceBuffer.duration / source.playbackRate.value;
    const gatedDuration = Math.max(0.025, rawDuration * event.gate);

    gain.gain.setValueAtTime(Math.max(0.001, event.velocity), start);
    gain.gain.setValueAtTime(Math.max(0.001, event.velocity), start + Math.max(0, gatedDuration - 0.012));
    gain.gain.linearRampToValueAtTime(0.0001, start + gatedDuration);

    source.connect(gain);
    gain.connect(destination);
    source.start(start, 0, Math.min(rawDuration, gatedDuration + 0.02));
    source.stop(start + gatedDuration + 0.03);
  }

  private copySlice(source: AudioBuffer, slice: SampleSlice): AudioBuffer {
    const frames = Math.max(1, slice.endFrame - slice.startFrame);
    const buffer = this.context.createBuffer(
      source.numberOfChannels,
      frames,
      source.sampleRate,
    );

    for (let channel = 0; channel < source.numberOfChannels; channel += 1) {
      const from = source.getChannelData(channel);
      const to = buffer.getChannelData(channel);
      to.set(from.subarray(slice.startFrame, slice.endFrame));
    }
    return buffer;
  }

  private reverseSlice(source: AudioBuffer, slice: SampleSlice): AudioBuffer {
    const buffer = this.copySlice(source, slice);
    for (let channel = 0; channel < buffer.numberOfChannels; channel += 1) {
      buffer.getChannelData(channel).reverse();
    }
    return buffer;
  }
}
