import test from "node:test";
import assert from "node:assert/strict";
import { JustMakerLocalSequencer } from "./local-sequencer.js";

test("90s east coast prompt produces boom-bap defaults", () => {
  const plan = new JustMakerLocalSequencer().build({
    prompt: "90s east coast hip hop with sample chops live drums and bass",
  });

  assert.equal(plan.bpm, 92);
  assert.ok(plan.swing >= 0.5);
  assert.equal(plan.stepsPerBar, 16);
  assert.ok(plan.sections.length >= 6);
});

test("sequencer is deterministic for the same prompt and seed", () => {
  const sequencer = new JustMakerLocalSequencer();
  const a = sequencer.build({ prompt: "dusty east coast beat", seed: 42 });
  const b = sequencer.build({ prompt: "dusty east coast beat", seed: 42 });
  assert.deepEqual(a, b);
});

test("sections vary instead of reusing one static pattern", () => {
  const plan = new JustMakerLocalSequencer().build({
    prompt: "90s boom bap live drums",
    seed: 7,
  });

  const intro = plan.drums["intro"];
  const hook = plan.drums["hook"];
  assert.notDeepEqual(intro, hook);
  assert.ok(hook.kick.length >= intro.kick.length);
});

test("microtiming and velocity humanization are present but bounded", () => {
  const plan = new JustMakerLocalSequencer().build({
    prompt: "live drums boom bap",
    seed: 99,
  });

  const events = Object.values(plan.drums).flatMap((pattern) => [
    ...pattern.kick,
    ...pattern.snare,
    ...pattern.hats,
    ...pattern.ghostSnare,
  ]);

  assert.ok(events.some((event) => event.offsetMs !== 0));
  assert.ok(events.some((event) => event.velocity !== events[0].velocity));
  assert.ok(events.every((event) => event.velocity > 0 && event.velocity <= 1));
  assert.ok(events.every((event) => Math.abs(event.offsetMs) <= 40));
});

test("bass notes lock primarily to kick positions", () => {
  const plan = new JustMakerLocalSequencer().build({
    prompt: "90s east coast live bass",
    seed: 123,
  });

  for (const section of plan.sections) {
    const kickSteps = new Set(plan.drums[section.name].kick.map((event) => event.step));
    const notes = plan.bass[section.name];
    const locked = notes.filter((note) => kickSteps.has(note.step)).length;
    assert.ok(notes.length === 0 || locked / notes.length >= 0.7);
  }
});
