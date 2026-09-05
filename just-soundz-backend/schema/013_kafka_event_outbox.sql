CREATE TABLE IF NOT EXISTS public.event_outbox (
    event_id UUID PRIMARY KEY,
    topic TEXT NOT NULL,
    event_key TEXT,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','published','failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    next_attempt_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS event_outbox_pending_idx
ON public.event_outbox(status,next_attempt_at,created_at);

CREATE INDEX IF NOT EXISTS event_outbox_topic_idx
ON public.event_outbox(topic,created_at DESC);

ALTER TABLE public.event_outbox ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.event_outbox FROM anon,authenticated;
GRANT ALL ON public.event_outbox TO service_role;

CREATE POLICY just_maker_service_event_outbox
ON public.event_outbox
FOR ALL TO service_role
USING (true) WITH CHECK (true);
