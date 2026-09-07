import test from "node:test";
import assert from "node:assert/strict";
import { JustMakerCompositionClient } from "./composition-client.js";

function client() {
  return new JustMakerCompositionClient({
    apiBaseUrl: "https://api.example.com/",
    getAccessToken: async () => "token",
    pollIntervalMs: 750,
  });
}

test("normalizes Composition controls into generation request", () => {
  const value = client().normalizeInput({
    prompt: "soulful hip hop instrumental",
    genre: "hip hop",
    mood: "uplifting",
    duration: 180,
    bpm: 92,
    key: "C minor",
  });
  assert.equal(value.prompt, "soulful hip hop instrumental, hip hop, uplifting");
  assert.equal(value.duration_seconds, 180);
  assert.equal(value.bpm, 92);
  assert.equal(value.key, "C minor");
  assert.equal(value.candidate_mode, "adaptive");
  assert.equal(value.candidate_count, 2);
});

test("rejects an empty Composition prompt", () => {
  assert.throws(() => client().normalizeInput({}), /Describe the instrumental/);
});

test("creates a generation job with bearer authentication", async () => {
  const originalFetch = globalThis.fetch;
  let request;
  globalThis.fetch = async (url, options) => {
    request = { url, options };
    return new Response(JSON.stringify({ job_id: "job-1", status: "queued" }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const result = await client().createComposition({ prompt: "original drum-heavy beat" });
    assert.equal(result.job_id, "job-1");
    assert.equal(request.url, "https://api.example.com/v1/jobs");
    assert.equal(request.options.headers.Authorization, "Bearer token");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("resolves a private master artifact to a signed playback URL", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(
    JSON.stringify({ signed_url: "https://storage.example.com/master.wav", expires_at: "later" }),
    { status: 200, headers: { "content-type": "application/json" } },
  );

  try {
    const playback = await client().getPlayback({
      job_id: "job-1",
      status: "complete",
      artifacts: [{ id: "artifact-1", artifact_type: "master", filename: "master.wav" }],
    });
    assert.equal(playback.url, "https://storage.example.com/master.wav");
    assert.equal(playback.filename, "master.wav");
    assert.equal(playback.source, "signed-artifact");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
