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

test("falls back to local generation when remote worker is unavailable", async () => {
  const c = client();
  c.generateAndWait = async () => {
    const error = new Error("No configured generation worker produced audio.");
    error.status = 503;
    throw error;
  };

  const events = [];
  const result = await c.generateWithFallback(
    { prompt: "90s east coast beat" },
    {
      callbacks: {
        onFallback: (event) => events.push(event.reason),
      },
      localGenerate: async () => ({
        playback: {
          url: "blob:local-beat",
          filename: "beat.wav",
          source: "local-free-engine",
        },
      }),
    },
  );

  assert.equal(result.source, "local-free-engine");
  assert.equal(result.playback.url, "blob:local-beat");
  assert.deepEqual(events, ["remote-unavailable"]);
});

test("does not hide authentication failures behind local fallback", async () => {
  const c = client();
  c.generateAndWait = async () => {
    const error = new Error("Unauthorized");
    error.status = 401;
    throw error;
  };

  let localCalled = false;
  await assert.rejects(
    () => c.generateWithFallback(
      { prompt: "beat" },
      {
        localGenerate: async () => {
          localCalled = true;
          return {};
        },
      },
    ),
    /Unauthorized/,
  );
  assert.equal(localCalled, false);
});

test("preferLocal bypasses the remote backend", async () => {
  const c = client();
  let remoteCalled = false;
  c.generateAndWait = async () => {
    remoteCalled = true;
    return {};
  };

  const result = await c.generateWithFallback(
    { prompt: "free local beat" },
    {
      preferLocal: true,
      localGenerate: async () => ({
        playback: {
          url: "blob:local",
          filename: "local.wav",
          source: "local-free-engine",
        },
      }),
    },
  );

  assert.equal(remoteCalled, false);
  assert.equal(result.source, "local-free-engine");
});

test("fallback classifier accepts network and paid-GPU availability errors", () => {
  const c = client();
  assert.equal(c.shouldFallbackToLocal(Object.assign(new Error("Purchase credit to run this model"), { status: 402 })), true);
  assert.equal(c.shouldFallbackToLocal(Object.assign(new Error("Service unavailable"), { status: 503 })), true);
  assert.equal(c.shouldFallbackToLocal(new TypeError("Failed to fetch")), true);
  assert.equal(c.shouldFallbackToLocal(Object.assign(new Error("Bad input"), { status: 400 })), false);
});
