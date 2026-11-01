-- ParentPlus M2: Restrict sensitive table privileges.
-- Explicitly remove direct API-role access.
-- Authorized operations use controlled SECURITY DEFINER functions.

REVOKE ALL ON TABLE public.children
FROM PUBLIC, anon, authenticated;

REVOKE ALL ON TABLE public.guardianships
FROM PUBLIC, anon, authenticated;

REVOKE ALL ON TABLE public.connection_requests
FROM PUBLIC, anon, authenticated;

REVOKE ALL ON TABLE public.connection_events
FROM PUBLIC, anon, authenticated;

REVOKE ALL ON TABLE public.workspace_children
FROM PUBLIC, anon, authenticated;
