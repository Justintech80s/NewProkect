import type { LocalInstrumentalRenderInput, LocalInstrumentalRenderResult } from "./local-instrumental-renderer.js";
import { JustMakerLocalInstrumentalRenderer } from "./local-instrumental-renderer.js";
import type { LocalSampleKit } from "./web-audio-sequencer-renderer.js";
import type { WasmModuleLoader } from "./wasm-dsp.js";

type CompositionInput = {
  prompt?: string;
  genre?: string;
  mood?: string;
  bpm?: number | string | null;
  key?: string | null;
  duration?: number;
  duration_seconds?: number;
  swing?: number;
  seed?: number;
  rootMidi?: number;
  scale?: number[];
  sampleRightsAttested?: boolean;
};

type LocalAssets = {
  kit: LocalSampleKit;
  sampleSource?: AudioBuffer | null;
};

type CompositionCallbacks = {
  onQueued?: (value: unknown) => void;
  onProgress?: (value: unknown) => void;
  onFallback?: (value: { reason: string; error: unknown }) => void;
  onComplete?: (value: unknown) => void;
  onError?: (error: unknown) => void;
};

type CompositionClientLike = {
  generateWithFallback(
    input: CompositionInput,
    options: {
      localGenerate: (
        input: CompositionInput,
        callbacks: CompositionCallbacks,
      ) => Promise<{
        playback: {
          url: string;
          filename: string;
          expiresAt: null;
          source: "local-free-engine";
          revoke: () => void;
        };
        render: LocalInstrumentalRenderResult;
      }>;
      callbacks?: CompositionCallbacks;
      preferLocal?: boolean;
    },
  ): Promise<unknown>;
};

export type JustMakerGenerateControllerOptions = {
  client: CompositionClientLike;
  wasmLoader: WasmModuleLoader;
  getLocalAssets: () => Promise<LocalAssets>;
  createObjectURL?: (blob: Blob) => string;
  revokeObjectURL?: (url: string) => void;
};

export class JustMakerGenerateController {
  private readonly client: CompositionClientLike;
  private readonly getLocalAssets: () => Promise<LocalAssets>;
  private readonly renderer: JustMakerLocalInstrumentalRenderer;
  private readonly createObjectURL: (blob: Blob) => string;
  private readonly revokeObjectURL: (url: string) => void;
  private currentLocalUrl: string | null = null;

  constructor({
    client,
    wasmLoader,
    getLocalAssets,
    createObjectURL = (blob) => URL.createObjectURL(blob),
    revokeObjectURL = (url) => URL.revokeObjectURL(url),
  }: JustMakerGenerateControllerOptions) {
    if (!client) throw new Error("Composition client is required");
    if (typeof getLocalAssets !== "function") {
      throw new Error("getLocalAssets must be a function");
    }
    this.client = client;
    this.getLocalAssets = getLocalAssets;
    this.renderer = new JustMakerLocalInstrumentalRenderer({ wasmLoader });
    this.createObjectURL = createObjectURL;
    this.revokeObjectURL = revokeObjectURL;
  }

  async generate(
    input: CompositionInput,
    {
      callbacks = {},
      preferLocal = false,
    }: {
      callbacks?: CompositionCallbacks;
      preferLocal?: boolean;
    } = {},
  ): Promise<unknown> {
    return this.client.generateWithFallback(input, {
      callbacks,
      preferLocal,
      localGenerate: async (originalInput, localCallbacks) => {
        localCallbacks.onProgress?.({
          jobId: null,
          status: "rendering",
          stage: "local-free-engine",
          progress: 0.12,
          local: true,
        });

        const assets = await this.getLocalAssets();
        const renderInput = this.toLocalRenderInput(originalInput, assets);

        localCallbacks.onProgress?.({
          jobId: null,
          status: "rendering",
          stage: "local-arrangement",
          progress: 0.32,
          local: true,
        });

        const render = await this.renderer.render(renderInput);

        localCallbacks.onProgress?.({
          jobId: null,
          status: "rendering",
          stage: "local-mastering",
          progress: 0.88,
          local: true,
        });

        if (this.currentLocalUrl) {
          this.revokeObjectURL(this.currentLocalUrl);
          this.currentLocalUrl = null;
        }

        const blob = new Blob([render.wav], { type: "audio/wav" });
        const url = this.createObjectURL(blob);
        this.currentLocalUrl = url;

        localCallbacks.onProgress?.({
          jobId: null,
          status: "complete",
          stage: "local-complete",
          progress: 1,
          local: true,
        });

        return {
          render,
          playback: {
            url,
            filename: render.filename,
            expiresAt: null,
            source: "local-free-engine" as const,
            revoke: () => {
              if (this.currentLocalUrl === url) {
                this.revokeObjectURL(url);
                this.currentLocalUrl = null;
              }
            },
          },
        };
      },
    });
  }

  dispose(): void {
    if (this.currentLocalUrl) {
      this.revokeObjectURL(this.currentLocalUrl);
      this.currentLocalUrl = null;
    }
  }

  private toLocalRenderInput(
    input: CompositionInput,
    assets: LocalAssets,
  ): LocalInstrumentalRenderInput {
    const prompt = [input.prompt, input.genre, input.mood]
      .map((value) => String(value || "").trim())
      .filter(Boolean)
      .join(", ");

    return {
      prompt,
      kit: assets.kit,
      sampleSource: assets.sampleSource || null,
      sampleRightsAttested: Boolean(input.sampleRightsAttested),
      bpm: input.bpm == null || input.bpm === "" ? undefined : Number(input.bpm),
      swing: input.swing,
      seed: input.seed,
      rootMidi: input.rootMidi,
      scale: input.scale,
    };
  }
}

export function bindJustMakerGenerateButton({
  button,
  readInput,
  controller,
  callbacks = {},
  preferLocal = false,
}: {
  button: HTMLButtonElement;
  readInput: () => CompositionInput;
  controller: JustMakerGenerateController;
  callbacks?: CompositionCallbacks;
  preferLocal?: boolean;
}): () => void {
  if (!(button instanceof HTMLButtonElement)) {
    throw new Error("button must be an HTMLButtonElement");
  }
  if (typeof readInput !== "function") {
    throw new Error("readInput must be a function");
  }

  let running = false;

  const onClick = async (event: Event) => {
    event.preventDefault();
    if (running) return;
    running = true;
    button.disabled = true;

    try {
      await controller.generate(readInput(), { callbacks, preferLocal });
    } catch (error) {
      callbacks.onError?.(error);
      throw error;
    } finally {
      running = false;
      button.disabled = false;
    }
  };

  button.addEventListener("click", onClick);
  return () => button.removeEventListener("click", onClick);
}
