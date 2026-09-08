import test from "node:test";
import assert from "node:assert/strict";
import { generateProceduralDrumSamples } from "./local-procedural-kit.js";

test("procedural drum kit is deterministic, bounded, and non-silent", () => {
  const a = generateProceduralDrumSamples(44100, 77);
  const b = generateProceduralDrumSamples(44100, 77);

  assert.deepEqual(a.kick, b.kick);
  assert.deepEqual(a.snare, b.snare);
  assert.deepEqual(a.hat, b.hat);

  for (const samples of [a.kick, a.snare, a.hat, a.ghostSnare]) {
    assert.ok(samples.length > 100);
    assert.ok(samples.some((value) => Math.abs(value) > 0.01));
    assert.ok(samples.every((value) => Number.isFinite(value) && Math.abs(value) <= 1));
  }
});

test("procedural drums use different envelopes and lengths", () => {
  const kit = generateProceduralDrumSamples(44100, 12);
  assert.ok(kit.kick.length > kit.snare.length);
  assert.ok(kit.snare.length > kit.hat.length);
  assert.notDeepEqual(kit.kick.slice(0, 100), kit.snare.slice(0, 100));
});
