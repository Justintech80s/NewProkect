export type WavEncodingOptions = {
  channels: number;
  sampleRate: number;
  bitDepth?: 16;
};

function clampSample(value: number): number {
  return Math.max(-1, Math.min(1, Number.isFinite(value) ? value : 0));
}

export function encodePcm16Wav(
  interleaved: Float32Array<ArrayBufferLike>,
  options: WavEncodingOptions,
): ArrayBuffer {
  const channels = Math.max(1, Math.min(8, Math.round(options.channels)));
  const sampleRate = Math.max(8000, Math.min(192000, Math.round(options.sampleRate)));
  if (interleaved.length % channels !== 0) {
    throw new Error("interleaved sample count must be divisible by channels");
  }

  const bytesPerSample = 2;
  const dataBytes = interleaved.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataBytes);
  const view = new DataView(buffer);

  const ascii = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i += 1) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  };

  ascii(0, "RIFF");
  view.setUint32(4, 36 + dataBytes, true);
  ascii(8, "WAVE");
  ascii(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * channels * bytesPerSample, true);
  view.setUint16(32, channels * bytesPerSample, true);
  view.setUint16(34, 16, true);
  ascii(36, "data");
  view.setUint32(40, dataBytes, true);

  let offset = 44;
  for (let i = 0; i < interleaved.length; i += 1) {
    const sample = clampSample(interleaved[i]);
    const pcm = sample < 0 ? Math.round(sample * 32768) : Math.round(sample * 32767);
    view.setInt16(offset, pcm, true);
    offset += bytesPerSample;
  }

  return buffer;
}

export function wavBlob(
  interleaved: Float32Array<ArrayBufferLike>,
  options: WavEncodingOptions,
): Blob {
  return new Blob([encodePcm16Wav(interleaved, options)], { type: "audio/wav" });
}
