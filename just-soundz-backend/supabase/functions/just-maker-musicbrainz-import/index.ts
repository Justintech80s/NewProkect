import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

type ImportRequest = { query: string; max_records?: number };
const MB_BASE = "https://musicbrainz.org/ws/2/recording/";

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "POST required" }), {
      status: 405,
      headers: { "content-type": "application/json" },
    });
  }

  const body = (await req.json()) as ImportRequest;
  const query = String(body.query || "").trim();
  const maxRecords = Math.min(Math.max(Number(body.max_records || 250), 1), 2000);
  if (query.length < 2) {
    return new Response(JSON.stringify({ error: "query is required" }), {
      status: 400,
      headers: { "content-type": "application/json" },
    });
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { persistSession: false } },
  );

  const jobId = crypto.randomUUID();
  const startedAt = new Date().toISOString();

  await supabase.from("ingestion_jobs").insert({
    id: jobId,
    source_name: "musicbrainz",
    query,
    status: "running",
    started_at: startedAt,
    checkpoint: { processed: 0, stored: 0, failed: 0 },
  });

  let processed = 0, stored = 0, failed = 0, offset = 0;
  const pageSize = Math.min(100, maxRecords);

  try {
    while (processed < maxRecords) {
      const limit = Math.min(pageSize, maxRecords - processed);
      const url = new URL(MB_BASE);
      url.searchParams.set("query", query);
      url.searchParams.set("fmt", "json");
      url.searchParams.set("limit", String(limit));
      url.searchParams.set("offset", String(offset));

      const mbResp = await fetch(url, {
        headers: {
          "User-Agent": "JustMaker/0.7 (metadata importer)",
          "Accept": "application/json",
        },
      });
      if (!mbResp.ok) throw new Error(`MusicBrainz returned ${mbResp.status}`);

      const page = await mbResp.json();
      const recordings = Array.isArray(page.recordings) ? page.recordings : [];
      if (!recordings.length) break;

      for (const recording of recordings) {
        processed += 1;
        try {
          const artistCredit = Array.isArray(recording["artist-credit"]) ? recording["artist-credit"] : [];
          const artistNames = artistCredit.map((c: any) => c?.artist?.name).filter(Boolean);
          const artistIds = artistCredit.map((c: any) => c?.artist?.id).filter(Boolean);
          const releases = Array.isArray(recording.releases) ? recording.releases : [];
          const firstRelease = releases[0] || {};
          const releaseDate = recording["first-release-date"] || firstRelease.date || "";
          const releaseYear = /^\d{4}/.test(releaseDate) ? Number(releaseDate.slice(0, 4)) : null;
          const tags = Array.isArray(recording.tags)
            ? [...new Set(recording.tags.map((t: any) => t?.name).filter(Boolean))]
            : [];

          const mbid = String(recording.id);
          const provenance = {
            source_name: "musicbrainz",
            source_record_id: mbid,
            source_url: `https://musicbrainz.org/recording/${mbid}`,
            license_name: "MusicBrainz metadata terms apply",
            metadata_only: true,
            retrieved_at: new Date().toISOString(),
          };

          const { data: song, error: songErr } = await supabase
            .from("songs")
            .upsert({
              external_id: `musicbrainz:${mbid}`,
              title: recording.title || "Untitled",
              artist_name: artistNames.length ? artistNames.join(" & ") : "Unknown Artist",
              album_name: firstRelease.title || null,
              release_year: releaseYear,
              genres: tags,
              metadata: {
                musicbrainz_recording_id: mbid,
                musicbrainz_artist_ids: artistIds,
                length_ms: recording.length || null,
                score: recording.score || null,
                provenance,
              },
            }, { onConflict: "external_id" })
            .select("id")
            .single();

          if (songErr) throw songErr;

          await supabase.from("song_rights").upsert({
            song_id: song.id,
            status: "reference_only",
            source: "musicbrainz",
            commercial_use: false,
            sampling_allowed: false,
          }, { onConflict: "song_id" });

          await supabase.from("record_provenance").upsert({
            song_id: song.id,
            source_name: "musicbrainz",
            source_record_id: mbid,
            source_url: provenance.source_url,
            retrieved_at: provenance.retrieved_at,
            license_name: provenance.license_name,
            metadata_only: true,
          }, { onConflict: "source_name,source_record_id" });

          stored += 1;
        } catch {
          failed += 1;
        }

        if (processed % 25 === 0) {
          await supabase.from("ingestion_jobs").update({
            processed_count: processed,
            stored_count: stored,
            failed_count: failed,
            checkpoint: { processed, stored, failed, offset },
            updated_at: new Date().toISOString(),
          }).eq("id", jobId);
        }

        if (processed >= maxRecords) break;
      }

      offset += recordings.length;
      if (recordings.length < limit) break;
      await new Promise((resolve) => setTimeout(resolve, 1050));
    }

    await supabase.from("ingestion_jobs").update({
      status: "complete",
      processed_count: processed,
      stored_count: stored,
      failed_count: failed,
      checkpoint: { processed, stored, failed, offset },
      completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }).eq("id", jobId);

    return new Response(JSON.stringify({
      job_id: jobId, status: "complete", query, processed, stored, failed,
    }), { headers: { "content-type": "application/json" } });
  } catch (err) {
    await supabase.from("ingestion_jobs").update({
      status: "failed",
      processed_count: processed,
      stored_count: stored,
      failed_count: failed,
      error_summary: [{ message: String(err) }],
      updated_at: new Date().toISOString(),
    }).eq("id", jobId);

    return new Response(JSON.stringify({
      job_id: jobId, status: "failed", error: String(err),
    }), { status: 500, headers: { "content-type": "application/json" } });
  }
});
