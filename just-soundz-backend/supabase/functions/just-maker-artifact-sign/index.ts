import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "POST required" }), {
      status: 405,
      headers: { "content-type": "application/json" },
    });
  }

  const authorization = req.headers.get("Authorization") || "";
  const token = authorization.toLowerCase().startsWith("bearer ")
    ? authorization.slice(7).trim()
    : "";

  if (!token) {
    return new Response(JSON.stringify({ error: "missing bearer token" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
  const serviceRole = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const admin = createClient(supabaseUrl, serviceRole, {
    auth: { persistSession: false },
  });

  const { data: userData, error: userError } = await admin.auth.getUser(token);
  const user = userData?.user;
  if (userError || !user?.id) {
    return new Response(JSON.stringify({ error: "invalid or expired token" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  const body = await req.json();
  const jobId = String(body.job_id || "");
  const artifactId = String(body.artifact_id || "");
  const expiresIn = Math.max(60, Math.min(Number(body.expires_in || 900), 86400));

  if (!jobId || !artifactId) {
    return new Response(JSON.stringify({ error: "job_id and artifact_id are required" }), {
      status: 400,
      headers: { "content-type": "application/json" },
    });
  }

  const { data: job } = await admin
    .from("generation_jobs")
    .select("id,user_id")
    .eq("id", jobId)
    .eq("user_id", user.id)
    .maybeSingle();

  if (!job) {
    return new Response(JSON.stringify({ error: "job not found" }), {
      status: 404,
      headers: { "content-type": "application/json" },
    });
  }

  const { data: artifact, error } = await admin
    .from("generation_artifacts")
    .select("id,job_id,user_id,filename,bucket,object_path")
    .eq("id", artifactId)
    .eq("job_id", jobId)
    .eq("user_id", user.id)
    .maybeSingle();

  if (error || !artifact) {
    return new Response(JSON.stringify({ error: "artifact not found" }), {
      status: 404,
      headers: { "content-type": "application/json" },
    });
  }

  if (!artifact.bucket || !artifact.object_path) {
    return new Response(JSON.stringify({ error: "artifact not persisted" }), {
      status: 409,
      headers: { "content-type": "application/json" },
    });
  }

  const { data: signed, error: signError } = await admin.storage
    .from(artifact.bucket)
    .createSignedUrl(artifact.object_path, expiresIn, {
      download: artifact.filename || true,
    });

  if (signError || !signed?.signedUrl) {
    return new Response(JSON.stringify({ error: "unable to sign artifact" }), {
      status: 503,
      headers: { "content-type": "application/json" },
    });
  }

  return new Response(JSON.stringify({
    signed: true,
    signed_url: signed.signedUrl,
    expires_in: expiresIn,
    filename: artifact.filename,
  }), {
    headers: { "content-type": "application/json" },
  });
});
