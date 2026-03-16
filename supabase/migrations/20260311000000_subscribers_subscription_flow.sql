-- =============================================================================
-- Subscribers: Add confirmed opt-in and unsubscribe token
-- =============================================================================
-- Supports double opt-in email subscription flow for AI News (thomasbustos.com).
-- confirmed: tracks whether the subscriber clicked the confirmation link.
-- unsubscribe_token: unique UUID used for both confirmation and unsubscribe links.
-- =============================================================================

ALTER TABLE public.subscribers
  ADD COLUMN IF NOT EXISTS confirmed boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS unsubscribe_token uuid UNIQUE DEFAULT gen_random_uuid();

CREATE INDEX IF NOT EXISTS subscribers_unsubscribe_token_idx
  ON public.subscribers (unsubscribe_token);
