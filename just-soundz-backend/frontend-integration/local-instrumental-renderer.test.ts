import test from "node:test";
import assert from "node:assert/strict";
import { JustMakerLocalSequencer } from "./local-sequencer.js";
import { beatDurationSeconds } from "./local-instrumental-renderer.js";
import { encodePcm16Wav } from "./wav-encoder.js";

test("full local render duration follows the arrangement", () => {
  const plan = new JustMakerLocalSequencer().build({
    prompt: "90s east coast boom bap",
    bpm: 92,
    seed: 42,
  });
  const bars = plan.sections.reduce((sum, section) => sum + section.bars, 0);
  assert.equal(bars, 64);
  assert.ok(Math.abs(beatDurationSeconds(plan) - (64 * 4 * 60 / 92)) < 1e-9);
});

test("WAV encoder creates a valid PCM16 RIFF file", () => {
  const samples = new Float32Array([0, 0.5, -0.5, 1, -1, 0]);
  const wav = encodePcm16Wav(samples, { channels: 2, sampleRate: 44100 });
  const view = new DataView(wav);
  const text = (offset: number, length: number) =>
    String.fromCharCode(...Array.from({ length }, (_, index) => view.getUint8(offset + index)));

  assert.equal(text(0, 4), "RIFF");
  assert.equal(text(8, 4), "WAVE");
  assert.equal(text(36, 4), "data");
  assert.equal(view.getUint16(22, true), 2);
  assert.equal(view.getUint32(24, true), 44100);
  assert.equal(view.getUint16(34, true), 16);
  assert.equal(wav.byteLength, 44 + samples.length * 2);
});

test("WAV encoder rejects malformed interleaved audio", () => {
  assert.throws(
    () => encodePcm16Wav(new Float32Array([0, 1, 0]), { channels: 2, sampleRate: 44100 }),
    /divisible by channels/,
  );
});

test("WAV encoder clamps out-of-range and non-finite samples", () => {
  const wav = encodePcm16Wav(
    new Float32Array([2, -2, Number.NaN, Number.POSITIVE_INFINITY]),
    { channels: 1, sampleRate: 44100 },
  );
  const view = new DataView(wav);
  assert.equal(view.getInt16(44, true), 32767);
  assert.equal(view.getInt16(46, true), -32768);
  assert.equal(view.getInt16(48, true), 0);
  assert.equal(view.getInt16(50, true), 0);
});
