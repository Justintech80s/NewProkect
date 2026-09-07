export class JustMakerCompositionClient {
  constructor({ apiBaseUrl, getAccessToken, pollIntervalMs = 2000 }) {
    if (!apiBaseUrl) throw new Error("apiBaseUrl is required");
    if (typeof getAccessToken !== "function") {
      throw new Error("getAccessToken must be a function");
    }
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, "");
    this.getAccessToken = getAccessToken;
    this.pollIntervalMs = Math.max(750, pollIntervalMs);
  }

  async createComposition(input) {
    const payload = this.normalizeInput(input);
    return this.request("/v1/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getJob(jobId) {
    return this.request(`/v1/jobs/${encodeURIComponent(jobId)}`);
  }

  async retryJob(jobId) {
    return this.request(`/v1/jobs/${encodeURIComponent(jobId)}/retry`, {
      method: "POST",
    });
  }

  async getPlayback(job) {
    if (!job || job.status !== "complete") return null;

    const artifacts = job.artifacts || [];
    const master =
      artifacts.find((item) => item.artifact_type === "master") ||
      artifacts.find((item) => item.type === "master") ||
      artifacts[0];

    if (master?.id) {
      const signed = await this.request(
        `/v1/jobs/${encodeURIComponent(job.job_id)}/artifacts/${encodeURIComponent(master.id)}/signed-url`,
        { method: "POST" },
      );
      return {
        url: signed.url || signed.signed_url,
        expiresAt: signed.expires_at || null,
        filename: master.filename || "just-maker-instrumental.wav",
        source: "signed-artifact",
      };
    }

    const generation = job.result?.generation || {};
    if (generation.audio_url) {
      return {
        url: generation.audio_url,
        expiresAt: null,
        filename: "just-maker-instrumental.wav",
        source: "generation-url",
      };
    }

    return null;
  }

  async generateAndWait(input, callbacks = {}) {
    const queued = await this.createComposition(input);
    const jobId = queued.job_id;
    callbacks.onQueued?.(queued);

    while (true) {
      await this.sleep(this.pollIntervalMs);
      const job = await this.getJob(jobId);
      callbacks.onProgress?.({
        jobId,
        status: job.status,
        stage: job.stage || job.status,
        progress: Number(job.progress || 0),
        job,
      });

      if (job.status === "complete") {
        const playback = await this.getPlayback(job);
        const result = { jobId, job, playback };
        callbacks.onComplete?.(result);
        return result;
      }

      if (job.status === "failed") {
        const error = new Error(job.error || "Instrumental generation failed");
        error.job = job;
        callbacks.onError?.(error);
        throw error;
      }
    }
  }

  normalizeInput(input = {}) {
    const promptParts = [input.prompt, input.genre, input.mood]
      .map((value) => String(value || "").trim())
      .filter(Boolean);

    if (!promptParts.length) {
      throw new Error("Describe the instrumental you want to create");
    }

    const duration = Number(input.duration_seconds ?? input.duration ?? 120);
    const bpm = input.bpm === "" || input.bpm == null ? null : Number(input.bpm);

    return {
      prompt: promptParts.join(", "),
      duration_seconds: Math.min(600, Math.max(10, duration)),
      bpm: bpm == null ? null : Math.min(240, Math.max(40, bpm)),
      key: input.key || null,
      make_stems: input.make_stems !== false,
      quality_threshold: Number(input.quality_threshold ?? 0.78),
      candidate_count: Math.min(3, Math.max(1, Number(input.candidate_count ?? 2))),
      candidate_mode: input.candidate_mode || "adaptive",
      variation: Number(input.variation ?? 0),
    };
  }

  async request(path, options = {}) {
    const token = await this.getAccessToken();
    if (!token) throw new Error("Sign in before generating an instrumental");

    const response = await fetch(`${this.apiBaseUrl}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      },
    });

    const contentType = response.headers.get("content-type") || "";
    const body = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const message =
        body?.detail?.message || body?.detail || body?.message || `Request failed (${response.status})`;
      const error = new Error(typeof message === "string" ? message : JSON.stringify(message));
      error.status = response.status;
      error.body = body;
      throw error;
    }

    return body;
  }

  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
