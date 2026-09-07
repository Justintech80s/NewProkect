import test from "node:test";
import assert from "node:assert/strict";
import { JustMakerLocalSampleChopper } from "./local-sample-chopper.js";

function syntheticHits(sampleRate = 1000): Float32Array {
  const samples = new Float32Array(sampleRate * 2);
  for (const start of [100, 500, 900, 1400]) {
    for (let i = 0; i < 35; i += 1) {
      samples[start + i] = Math.max(0, 1 - i / 35);
    }
  }
  return samples;
}

test("detects multiple transient slices from hit-like audio", () => {
  const chopper = new JustMakerLocalSampleChopper();
  const slices = chopper.detectTransients(syntheticHits(), 1000, 1, {
    threshold: 0.08,
    minSpacingMs: 120,
    windowFrames: 20,
    maxSlices: 8,
  });
  assert.ok(slices.length >= 4);
  assert.equal(slices[0].startFrame, 0);
  assert.ok(slices.every((slice) => slice.endFrame > slice.startFrame));
});

test("requires rights attestation before building a chop plan", () => {
  const chopper = new JustMakerLocalSampleChopper();
  assert.throws(
    () => chopper.buildPlan(
      [{ id: 0, startFrame: 0, endFrame: 100, peak: 1 }],
      44100,
      1,
      { rightsAttested: false, prompt: "sample chops" },
    ),
    /user-owned, cleared, or licensed/,
  );
});

test("same seed reproduces the same chop arrangement", () => {
  const chopper = new JustMakerLocalSampleChopper();
  const slices = [
    { id: 0, startFrame: 0, endFrame: 100, peak: 1 },
    { id: 1, startFrame: 100, endFrame: 200, peak: 0.8 },
    { id: 2, startFrame: 200, endFrame: 300, peak: 0.9 },
  ];
  const options = { rightsAttested: true, prompt: "90s east coast sample chops", seed: 55 };
  const a = chopper.buildPlan(slices, 44100, 1, options);
  const b = chopper.buildPlan(slices, 44100, 1, options);
  assert.deepEqual(a, b);
});

test("chop plan includes pitch movement gaps and section variation", () => {
  const chopper = new JustMakerLocalSampleChopper();
  const slices = Array.from({ length: 6 }, (_, id) => ({
    id,
    startFrame: id * 100,
    endFrame: (id + 1) * 100,
    peak: 0.9,
  }));
  const plan = chopper.buildPlan(slices, 44100, 1, {
    rightsAttested: true,
    prompt: "90s east coast sample chops",
    seed: 812,
  });

  assert.equal(plan.sourcePolicy, "user-owned-cleared-or-licensed");
  assert.ok(plan.sections.length >= 6);
  assert.ok(plan.sections.some((section) => section.events.some((event) => event.semitones !== 0)));
  assert.notDeepEqual(plan.sections[0].events, plan.sections[2].events);
  assert.ok(plan.sections.every((section) => section.events.length < plan.stepsPerBar));
});
