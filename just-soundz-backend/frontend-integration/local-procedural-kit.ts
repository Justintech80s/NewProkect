export type ProceduralDrumSamples = {
  kick: Float32Array;
  snare: Float32Array;
  hat: Float32Array;
  ghostSnare: Float32Array;
  sampleRate: number;
};

function seededNoise(seed: number): () => number {
  let state = (seed >>> 0) || 1;
  return () => {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    return ((state >>> 0) / 0xffffffff) * 2 - 1;
  };
}

function clamp(value: number): number {
  return Math.max(-1, Math.min(1, Number.isFinite(value) ? value : 0));
}

export function generateProceduralDrumSamples(
  sampleRate = 44100,
  seed = 1337,
): ProceduralDrumSamples {
  const sr = Math.max(22050, Math.min(96000, Math.round(sampleRate)));
  const noise = seededNoise(seed);

  const kickLength = Math.round(sr * 0.42);
  const kick = new Float32Array(kickLength);
  let phase = 0;
  for (let i = 0; i < kickLength; i += 1) {
    const t = i / sr;
    const normalized = i / kickLength;
    const frequency = 148 * Math.exp(-t * 22) + 43;
    phase += (2 * Math.PI * frequency) / sr;
    const envelope = Math.exp(-t * 9.5) * (1 - Math.pow(normalized, 5));
    const click = i < sr * 0.008 ? (1 - i / (sr * 0.008)) * 0.22 : 0;
    kick[i] = clamp(Math.sin(phase) * envelope * 0.94 + click);
  }

  const snareLength = Math.round(sr * 0.28);
  const snare = new Float32Array(snareLength);
  const ghostSnare = new Float32Array(snareLength);
  for (let i = 0; i < snareLength; i += 1) {
    const t = i / sr;
    const body = Math.sin(2 * Math.PI * 190 * t) * Math.exp(-t * 18) * 0.30;
    const n = noise();
    const texture =
      n *
      (i === 0 ? 1 : (n - (snare[i - 1] || 0) * 0.15)) *
      Math.exp(-t * 14);
    snare[i] = clamp(body + texture * 0.66);
    ghostSnare[i] = clamp((body + texture * 0.52) * 0.62);
  }

  const hatLength = Math.round(sr * 0.095);
  const hat = new Float32Array(hatLength);
  let previous = 0;
  for (let i = 0; i < hatLength; i += 1) {
    const t = i / sr;
    const n = noise();
    const high = n - previous * 0.92;
    previous = n;
    const metallic =
      Math.sin(2 * Math.PI * 6720 * t) * 0.16 +
      Math.sin(2 * Math.PI * 9340 * t) * 0.11;
    hat[i] = clamp((high * 0.48 + metallic) * Math.exp(-t * 42));
  }

  return { kick, snare, hat, ghostSnare, sampleRate: sr };
}

function toAudioBuffer(samples: Float32Array, sampleRate: number): AudioBuffer {
  if (typeof AudioBuffer === "undefined") {
    throw new Error("AudioBuffer is not available in this browser");
  }
  const buffer = new AudioBuffer({
    length: samples.length,
    numberOfChannels: 1,
    sampleRate,
  });
  const target = buffer.getChannelData(0);
  for (let i = 0; i < samples.length; i += 1) {
    target[i] = samples[i];
  }
  return buffer;
}

export function createProceduralLocalSampleKit(
  sampleRate = 44100,
  seed = 1337,
): {
  kick: AudioBuffer;
  snare: AudioBuffer;
  hat: AudioBuffer;
  ghostSnare: AudioBuffer;
} {
  const samples = generateProceduralDrumSamples(sampleRate, seed);
  return {
    kick: toAudioBuffer(samples.kick, samples.sampleRate),
    snare: toAudioBuffer(samples.snare, samples.sampleRate),
    hat: toAudioBuffer(samples.hat, samples.sampleRate),
    ghostSnare: toAudioBuffer(samples.ghostSnare, samples.sampleRate),
  };
}
