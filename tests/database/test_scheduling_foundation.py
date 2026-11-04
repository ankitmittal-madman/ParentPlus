"""Deny-by-default scheduling data and workspace integrity tests."""
import unittest
from tests.database.test_authorization import run_sql

SETUP = """
BEGIN;
UPDATE public.class_setup_controls SET enabled=true WHERE id=true;
INSERT INTO public.workspaces (id, name, type, created_by, creation_request_id) VALUES
 ('a0000000-0000-4000-8000-000000000001', 'Academy A', 'academy', '11111111-1111-4111-8111-111111111111', 'a1000000-0000-4000-8000-000000000001'),
 ('a0000000-0000-4000-8000-000000000002', 'Academy B', 'academy', '22222222-2222-4222-8222-222222222222', 'a1000000-0000-4000-8000-000000000002');
INSERT INTO public.workspace_memberships (id, workspace_id, user_id, role, status) VALUES
 ('b0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', '11111111-1111-4111-8111-111111111111', 'coach', 'active'),
 ('b0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000002', '22222222-2222-4222-8222-222222222222', 'coach', 'active');
INSERT INTO public.courses (id, workspace_id, name) VALUES
 ('c0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'Music');
"""

# Historical behavior tests temporarily grant these draft functions inside their
# rolled-back transaction. Separate tests verify the real post-migration ACL.
LEGACY_SETUP = SETUP.replace("BEGIN;", """BEGIN;
GRANT EXECUTE ON FUNCTION public.create_course(uuid,text,uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.create_batch(uuid,uuid,text,uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.create_course_and_batch(uuid,text,text,uuid) TO authenticated;
""", 1)

class SchedulingFoundationTests(unittest.TestCase):
    def test_valid_same_workspace_batch_and_assignment(self):
        out = run_sql(SETUP + """
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES
 ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
INSERT INTO public.batch_coach_assignments (workspace_id, batch_id, membership_id) VALUES
 ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001');
SELECT count(*) FROM public.batch_coach_assignments;
ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1')

    def test_cross_workspace_course_is_rejected(self):
        out = run_sql(SETUP + """
DO $$ BEGIN
 INSERT INTO public.batches (workspace_id, course_id, name) VALUES
 ('a0000000-0000-4000-8000-000000000002', 'c0000000-0000-4000-8000-000000000001', 'Wrong');
 RAISE EXCEPTION 'cross-workspace course accepted';
EXCEPTION WHEN foreign_key_violation THEN NULL; END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 'denied')

    def test_cross_workspace_membership_is_rejected(self):
        out = run_sql(SETUP + """
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES
 ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
DO $$ BEGIN
 INSERT INTO public.batch_coach_assignments (workspace_id, batch_id, membership_id) VALUES
 ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000002');
 RAISE EXCEPTION 'cross-workspace membership accepted';
EXCEPTION WHEN foreign_key_violation THEN NULL; END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 'denied')

    def test_application_roles_cannot_read_or_write_tables(self):
        out = run_sql("""
SELECT bool_and(NOT has_table_privilege(role_name, table_name, privilege))
FROM unnest(ARRAY['anon','authenticated']) role_name
CROSS JOIN unnest(ARRAY['public.courses','public.batches','public.batch_coach_assignments']) table_name
CROSS JOIN unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER']) privilege;
""")
        self.assertEqual(out, 't')

    def test_rls_is_enabled_without_permissive_policies(self):
        out = run_sql("""
SELECT count(*) = 3 AND bool_and(c.relrowsecurity)
 AND NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename IN ('courses','batches','batch_coach_assignments'))
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname IN ('courses','batches','batch_coach_assignments');
""")
        self.assertEqual(out, 't')

    def test_schedule_helper_allows_active_owner_admin_and_assigned_coach(self):
        out = run_sql(SETUP + """
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES
 ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
INSERT INTO public.batch_coach_assignments (workspace_id, batch_id, membership_id) VALUES
 ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001');
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
SELECT public.assert_schedule_write_access('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001');
DELETE FROM public.batch_coach_assignments;
UPDATE public.workspace_memberships SET role = 'owner' WHERE id = 'b0000000-0000-4000-8000-000000000001';
SELECT public.assert_schedule_write_access('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001');
UPDATE public.workspace_memberships SET role = 'admin' WHERE id = 'b0000000-0000-4000-8000-000000000001';
SELECT public.assert_schedule_write_access('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001');
SELECT 'allowed'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 'allowed')

    def test_schedule_helper_rejects_unassigned_inactive_cross_workspace_and_anonymous(self):
        out = run_sql(SETUP + """
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES
 ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
DO $$ BEGIN
 FOR i IN 1..5 LOOP
  PERFORM set_config('request.jwt.claim.sub', CASE WHEN i = 1 THEN '' WHEN i = 2 THEN '22222222-2222-4222-8222-222222222222' ELSE '11111111-1111-4111-8111-111111111111' END, true);
  IF i = 4 THEN UPDATE public.workspace_memberships SET status = 'suspended' WHERE id = 'b0000000-0000-4000-8000-000000000001'; END IF;
  IF i = 5 THEN UPDATE public.workspace_memberships SET status = 'active', role = 'owner' WHERE id = 'b0000000-0000-4000-8000-000000000001'; UPDATE public.workspaces SET status = 'suspended' WHERE id = 'a0000000-0000-4000-8000-000000000001'; END IF;
  BEGIN
   PERFORM public.assert_schedule_write_access('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001');
   RAISE EXCEPTION 'unauthorized actor accepted';
  EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 END LOOP;
END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 'denied')

    def test_schedule_helper_is_not_executable_by_application_roles(self):
        out = run_sql("""
SELECT NOT has_function_privilege('anon', 'public.assert_schedule_write_access(uuid,uuid)', 'EXECUTE')
   AND NOT has_function_privilege('authenticated', 'public.assert_schedule_write_access(uuid,uuid)', 'EXECUTE');
""")
        self.assertEqual(out, 't')

    def test_private_session_write_creates_and_retries_same_request(self):
        out = run_sql(SETUP + """
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
INSERT INTO public.batch_coach_assignments (workspace_id, batch_id, membership_id) VALUES ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001');
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
SELECT public.create_private_session('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', '2026-11-03 11:30+00', '2026-11-03 12:30+00', 'e0000000-0000-4000-8000-000000000001') =
 public.create_private_session('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', '2026-11-03 11:30+00', '2026-11-03 12:30+00', 'e0000000-0000-4000-8000-000000000001');
SELECT count(*) FROM public.schedule_sessions;
ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:], ['t', '1'])

    def test_private_session_write_rejects_changed_retry(self):
        out = run_sql(SETUP + """
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
SELECT public.create_private_session('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', '2026-11-03 11:30+00', '2026-11-03 12:30+00', 'e0000000-0000-4000-8000-000000000001');
DO $$ BEGIN
 PERFORM public.create_private_session('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', '2026-11-03 11:30+00', '2026-11-03 13:30+00', 'e0000000-0000-4000-8000-000000000001');
 RAISE EXCEPTION 'changed retry accepted';
EXCEPTION WHEN unique_violation THEN NULL; END $$;
SELECT count(*) FROM public.schedule_sessions; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1')

    def test_private_session_write_rejects_unauthorized_and_invalid_time(self):
        out = run_sql(SETUP + """
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
DO $$ BEGIN
 BEGIN PERFORM public.create_private_session('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', '2026-11-03 11:30+00', '2026-11-03 12:30+00', 'e0000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'unassigned coach accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
 BEGIN PERFORM public.create_private_session('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', '2026-11-03 12:30+00', '2026-11-03 11:30+00', 'e0000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'invalid time accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
END $$;
SELECT count(*) FROM public.schedule_sessions; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_private_session_table_and_write_are_closed_to_app_roles(self):
        out = run_sql("""
SELECT NOT has_table_privilege('anon', 'public.schedule_sessions', 'SELECT')
 AND NOT has_table_privilege('authenticated', 'public.schedule_sessions', 'INSERT')
 AND NOT has_function_privilege('anon', 'public.create_private_session(uuid,uuid,timestamp with time zone,timestamp with time zone,uuid)', 'EXECUTE')
 AND NOT has_function_privilege('authenticated', 'public.create_private_session(uuid,uuid,timestamp with time zone,timestamp with time zone,uuid)', 'EXECUTE');
""")
        self.assertEqual(out, 't')

    def local_time_setup(self):
        return SETUP + """
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
"""

    def test_workspace_local_session_uses_workspace_zone(self):
        out = run_sql(self.local_time_setup() + """
UPDATE public.workspaces SET scheduling_time_zone='Asia/Kolkata' WHERE id='a0000000-0000-4000-8000-000000000001';
SELECT public.create_private_local_session('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', '2026-11-03 17:00', 60, 'e0000000-0000-4000-8000-000000000001');
SELECT starts_at = '2026-11-03 11:30+00'::timestamptz AND ends_at = '2026-11-03 12:30+00'::timestamptz FROM public.schedule_sessions; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 't')

    def test_workspace_local_session_rejects_new_york_gap_and_fold(self):
        out = run_sql(self.local_time_setup() + """
UPDATE public.workspaces SET scheduling_time_zone='America/New_York' WHERE id='a0000000-0000-4000-8000-000000000001';
DO $$ DECLARE local_time timestamp; BEGIN
 FOREACH local_time IN ARRAY ARRAY['2026-03-08 02:30'::timestamp, '2026-11-01 01:30'::timestamp] LOOP
  BEGIN PERFORM public.create_private_local_session('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', local_time, 60, gen_random_uuid()); RAISE EXCEPTION 'clock conflict accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
 END LOOP;
END $$;
SELECT count(*) FROM public.schedule_sessions; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_workspace_local_session_rejects_half_hour_gap_and_fold(self):
        out = run_sql(self.local_time_setup() + """
UPDATE public.workspaces SET scheduling_time_zone='Australia/Lord_Howe' WHERE id='a0000000-0000-4000-8000-000000000001';
DO $$ DECLARE local_time timestamp; BEGIN
 FOREACH local_time IN ARRAY ARRAY['2026-10-04 02:15'::timestamp, '2026-04-05 01:45'::timestamp] LOOP
  BEGIN PERFORM public.create_private_local_session('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', local_time, 60, gen_random_uuid()); RAISE EXCEPTION 'clock conflict accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
 END LOOP;
END $$;
SELECT count(*) FROM public.schedule_sessions; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_workspace_local_session_rejects_missing_and_invalid_zone(self):
        out = run_sql(self.local_time_setup() + """
DO $$ DECLARE zone_name text; BEGIN
 FOREACH zone_name IN ARRAY ARRAY[NULL::text, 'Invalid/Zone'] LOOP
  UPDATE public.workspaces SET scheduling_time_zone=zone_name WHERE id='a0000000-0000-4000-8000-000000000001';
  BEGIN PERFORM public.create_private_local_session('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', '2026-11-03 17:00', 60, gen_random_uuid()); RAISE EXCEPTION 'invalid zone accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
 END LOOP;
END $$;
SELECT count(*) FROM public.schedule_sessions; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_workspace_local_session_is_private(self):
        out = run_sql("""
SELECT NOT has_function_privilege('anon', 'public.create_private_local_session(uuid,uuid,timestamp without time zone,integer,uuid)', 'EXECUTE')
 AND NOT has_function_privilege('authenticated', 'public.create_private_local_session(uuid,uuid,timestamp without time zone,integer,uuid)', 'EXECUTE');
""")
        self.assertEqual(out, 't')

    def test_private_zone_setup_allows_active_owner_and_admin_with_same_retry(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
SELECT public.configure_private_workspace_zone('a0000000-0000-4000-8000-000000000001', 'Asia/Kolkata');
UPDATE public.workspace_memberships SET role='admin' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT public.configure_private_workspace_zone('a0000000-0000-4000-8000-000000000001', 'Asia/Kolkata');
SELECT scheduling_time_zone FROM public.workspaces WHERE id='a0000000-0000-4000-8000-000000000001'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 'Asia/Kolkata')

    def test_private_zone_setup_rejects_unauthorized_actors(self):
        out = run_sql(SETUP + """
DO $$ DECLARE i int; BEGIN
 FOR i IN 1..5 LOOP
  PERFORM set_config('request.jwt.claim.sub', CASE WHEN i=1 THEN '' WHEN i=2 THEN '22222222-2222-4222-8222-222222222222' ELSE '11111111-1111-4111-8111-111111111111' END, true);
  IF i=4 THEN UPDATE public.workspace_memberships SET role='owner', status='suspended' WHERE id='b0000000-0000-4000-8000-000000000001'; END IF;
  IF i=5 THEN UPDATE public.workspace_memberships SET status='active' WHERE id='b0000000-0000-4000-8000-000000000001'; UPDATE public.workspaces SET status='suspended' WHERE id='a0000000-0000-4000-8000-000000000001'; END IF;
  BEGIN PERFORM public.configure_private_workspace_zone('a0000000-0000-4000-8000-000000000001', 'Asia/Kolkata'); RAISE EXCEPTION 'unauthorized zone setup'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 END LOOP;
END $$;
SELECT scheduling_time_zone IS NULL FROM public.workspaces WHERE id='a0000000-0000-4000-8000-000000000001'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 't')

    def test_private_zone_setup_rejects_invalid_and_changed_zone(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
DO $$ BEGIN
 BEGIN PERFORM public.configure_private_workspace_zone('a0000000-0000-4000-8000-000000000001', 'Invalid/Zone'); RAISE EXCEPTION 'invalid zone accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
 PERFORM public.configure_private_workspace_zone('a0000000-0000-4000-8000-000000000001', 'Asia/Kolkata');
 BEGIN PERFORM public.configure_private_workspace_zone('a0000000-0000-4000-8000-000000000001', 'Europe/London'); RAISE EXCEPTION 'changed zone accepted'; EXCEPTION WHEN check_violation THEN NULL; END;
END $$;
SELECT scheduling_time_zone FROM public.workspaces WHERE id='a0000000-0000-4000-8000-000000000001'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 'Asia/Kolkata')

    def test_private_zone_setup_cannot_be_executed_by_app_roles(self):
        out = run_sql("""
SELECT NOT has_function_privilege('anon', 'public.configure_private_workspace_zone(uuid,text)', 'EXECUTE')
 AND NOT has_function_privilege('authenticated', 'public.configure_private_workspace_zone(uuid,text)', 'EXECUTE');
""")
        self.assertEqual(out, 't')

    def test_private_course_and_batch_create_and_retry(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
CREATE TEMP TABLE created_ids(course_id uuid, batch_id uuid);
INSERT INTO created_ids(course_id) SELECT public.create_private_course('a0000000-0000-4000-8000-000000000001', ' Dance ', 'e0000000-0000-4000-8000-000000000001');
UPDATE created_ids SET batch_id=public.create_private_batch('a0000000-0000-4000-8000-000000000001', course_id, ' Beginners ', 'e0000000-0000-4000-8000-000000000002');
SELECT course_id=public.create_private_course('a0000000-0000-4000-8000-000000000001', 'Dance', 'e0000000-0000-4000-8000-000000000001') AND batch_id=public.create_private_batch('a0000000-0000-4000-8000-000000000001', course_id, 'Beginners', 'e0000000-0000-4000-8000-000000000002') FROM created_ids;
SELECT (SELECT count(*) FROM public.courses WHERE name='Dance') || ':' || (SELECT count(*) FROM public.batches WHERE name='Beginners'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:], ['t', '1:1'])

    def test_private_course_and_batch_reject_changed_retries_and_cross_workspace(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='admin' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
DO $$ BEGIN
 PERFORM public.create_private_course('a0000000-0000-4000-8000-000000000001', 'Dance', 'e0000000-0000-4000-8000-000000000001');
 BEGIN PERFORM public.create_private_course('a0000000-0000-4000-8000-000000000001', 'Music', 'e0000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'changed course retry accepted'; EXCEPTION WHEN unique_violation THEN NULL; END;
 PERFORM public.create_private_batch('a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning', 'e0000000-0000-4000-8000-000000000002');
 BEGIN PERFORM public.create_private_batch('a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Evening', 'e0000000-0000-4000-8000-000000000002'); RAISE EXCEPTION 'changed batch retry accepted'; EXCEPTION WHEN unique_violation THEN NULL; END;
 INSERT INTO public.workspace_memberships (workspace_id, user_id, role, status) VALUES ('a0000000-0000-4000-8000-000000000002', '11111111-1111-4111-8111-111111111111', 'admin', 'active');
 BEGIN PERFORM public.create_private_batch('a0000000-0000-4000-8000-000000000002', 'c0000000-0000-4000-8000-000000000001', 'Other', 'e0000000-0000-4000-8000-000000000003'); RAISE EXCEPTION 'cross-workspace accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
END $$;
SELECT count(*) FROM public.batches; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1')

    def test_private_course_and_batch_reject_invalid_or_unauthorized_input(self):
        out = run_sql(SETUP + """
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
DO $$ BEGIN
 BEGIN PERFORM public.create_private_course('a0000000-0000-4000-8000-000000000001', 'Dance', gen_random_uuid()); RAISE EXCEPTION 'coach accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
 BEGIN PERFORM public.create_private_course('a0000000-0000-4000-8000-000000000001', '  ', gen_random_uuid()); RAISE EXCEPTION 'empty course accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
 BEGIN PERFORM public.create_private_batch('a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', '', gen_random_uuid()); RAISE EXCEPTION 'empty batch accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
END $$;
SELECT count(*) FROM public.batches; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_private_course_and_batch_operations_are_not_public(self):
        out = run_sql("""
SELECT NOT has_function_privilege('anon', 'public.create_private_course(uuid,text,uuid)', 'EXECUTE') AND NOT has_function_privilege('authenticated', 'public.create_private_course(uuid,text,uuid)', 'EXECUTE') AND NOT has_function_privilege('anon', 'public.create_private_batch(uuid,uuid,text,uuid)', 'EXECUTE') AND NOT has_function_privilege('authenticated', 'public.create_private_batch(uuid,uuid,text,uuid)', 'EXECUTE');
""")
        self.assertEqual(out, 't')

    def test_private_coach_assignment_and_retry(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
INSERT INTO public.workspace_memberships (id, workspace_id, user_id, role, status) VALUES ('b0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000001', '33333333-3333-4333-8333-333333333333', 'coach', 'active');
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000003', 'e1000000-0000-4000-8000-000000000001');
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000003', 'e1000000-0000-4000-8000-000000000001');
SELECT count(*) FROM public.batch_coach_assignments; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1')

    def test_private_coach_assignment_rejects_invalid_target_and_cross_workspace(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='admin' WHERE id='b0000000-0000-4000-8000-000000000001';
INSERT INTO public.workspace_memberships (id, workspace_id, user_id, role, status) VALUES ('b0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000001', '33333333-3333-4333-8333-333333333333', 'coach', 'suspended');
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
DO $$ DECLARE target uuid; BEGIN
 FOREACH target IN ARRAY ARRAY['b0000000-0000-4000-8000-000000000001'::uuid, 'b0000000-0000-4000-8000-000000000002'::uuid, 'b0000000-0000-4000-8000-000000000003'::uuid, gen_random_uuid()] LOOP
  BEGIN PERFORM public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', target, 'e1000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'invalid target accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
 END LOOP;
END $$;
SELECT count(*) FROM public.batch_coach_assignments; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_private_coach_assignment_rejects_unauthorized_actor(self):
        out = run_sql(SETUP + """
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
DO $$ BEGIN
 BEGIN PERFORM public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001', 'e1000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'coach assigned self'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
SELECT count(*) FROM public.batch_coach_assignments; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_private_coach_assignment_cannot_be_executed_by_app_roles(self):
        out = run_sql("""
SELECT NOT has_function_privilege('anon', 'public.assign_private_batch_coach(uuid,uuid,uuid,uuid)', 'EXECUTE') AND NOT has_function_privilege('authenticated', 'public.assign_private_batch_coach(uuid,uuid,uuid,uuid)', 'EXECUTE');
""")
        self.assertEqual(out, 't')

    def test_private_coach_removal_revokes_future_access_and_retries(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
INSERT INTO public.workspace_memberships (id, workspace_id, user_id, role, status) VALUES ('b0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000001', '33333333-3333-4333-8333-333333333333', 'coach', 'active');
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
INSERT INTO public.batch_coach_assignments VALUES ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000003');
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
SELECT public.remove_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000003', 'e2000000-0000-4000-8000-000000000002');
SELECT public.remove_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000003', 'e2000000-0000-4000-8000-000000000002');
SELECT set_config('request.jwt.claim.sub', '33333333-3333-4333-8333-333333333333', true);
DO $$ BEGIN BEGIN PERFORM public.create_private_session('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', '2026-11-03 11:30+00', '2026-11-03 12:30+00', gen_random_uuid()); RAISE EXCEPTION 'unassigned coach succeeded'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT (SELECT count(*) FROM public.batch_coach_assignments) || ':' || (SELECT count(*) FROM public.schedule_sessions) || ':' || (SELECT count(*) FROM public.batches); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0:0:1')

    def test_private_coach_removal_rejects_unauthorized_actor(self):
        out = run_sql(SETUP + """
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
INSERT INTO public.batch_coach_assignments VALUES ('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001');
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
DO $$ BEGIN BEGIN PERFORM public.remove_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001', 'e2000000-0000-4000-8000-000000000002'); RAISE EXCEPTION 'coach removed assignment'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT count(*) FROM public.batch_coach_assignments; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1')

    def test_private_coach_removal_rejects_cross_workspace_batch(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES ('d0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'c0000000-0000-4000-8000-000000000001', 'Morning');
INSERT INTO public.courses (id, workspace_id, name) VALUES ('c0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000002', 'Other course');
INSERT INTO public.batches (id, workspace_id, course_id, name) VALUES ('d0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000002', 'c0000000-0000-4000-8000-000000000002', 'Other batch');
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
DO $$ BEGIN BEGIN PERFORM public.remove_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000002', 'b0000000-0000-4000-8000-000000000002', 'e2000000-0000-4000-8000-000000000002'); RAISE EXCEPTION 'cross-workspace batch accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END; END $$;
SELECT count(*) FROM public.batches; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '2')

    def test_private_coach_removal_cannot_be_executed_by_app_roles(self):
        self.assertEqual(run_sql("SELECT NOT has_function_privilege('anon', 'public.remove_private_batch_coach(uuid,uuid,uuid,uuid)', 'EXECUTE') AND NOT has_function_privilege('authenticated', 'public.remove_private_batch_coach(uuid,uuid,uuid,uuid)', 'EXECUTE');"), 't')

    def test_old_assignment_retry_does_not_restore_removed_coach(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
INSERT INTO public.workspace_memberships (id,workspace_id,user_id,role,status) VALUES ('b0000000-0000-4000-8000-000000000003','a0000000-0000-4000-8000-000000000001','33333333-3333-4333-8333-333333333333','coach','active');
INSERT INTO public.batches (id,workspace_id,course_id,name) VALUES ('d0000000-0000-4000-8000-000000000001','a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Morning');
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000003', 'e1000000-0000-4000-8000-000000000001');
SELECT public.remove_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000003', 'e2000000-0000-4000-8000-000000000002');
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000003', 'e1000000-0000-4000-8000-000000000001');
SELECT set_config('request.jwt.claim.sub','33333333-3333-4333-8333-333333333333',true);
DO $$ BEGIN BEGIN PERFORM public.create_private_session('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','2026-11-03 11:30+00','2026-11-03 12:30+00',gen_random_uuid()); RAISE EXCEPTION 'removed coach regained access'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT count(*) FROM public.batch_coach_assignments; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_old_removal_retry_does_not_remove_reassigned_coach(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
INSERT INTO public.workspace_memberships (id,workspace_id,user_id,role,status) VALUES ('b0000000-0000-4000-8000-000000000003','a0000000-0000-4000-8000-000000000001','33333333-3333-4333-8333-333333333333','coach','active');
INSERT INTO public.batches (id,workspace_id,course_id,name) VALUES ('d0000000-0000-4000-8000-000000000001','a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Morning');
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000003', 'e1000000-0000-4000-8000-000000000001');
SELECT public.remove_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000003', 'e2000000-0000-4000-8000-000000000002');
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000003', 'e1000000-0000-4000-8000-000000000003');
SELECT public.remove_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000003', 'e2000000-0000-4000-8000-000000000002');
SELECT count(*) FROM public.batch_coach_assignments; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1')

    def test_coach_request_id_cannot_change_action_batch_or_member(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
INSERT INTO public.workspace_memberships (id,workspace_id,user_id,role,status) VALUES ('b0000000-0000-4000-8000-000000000003','a0000000-0000-4000-8000-000000000001','33333333-3333-4333-8333-333333333333','coach','active');
INSERT INTO public.batches (id,workspace_id,course_id,name) VALUES ('d0000000-0000-4000-8000-000000000001','a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Morning'), ('d0000000-0000-4000-8000-000000000002','a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Evening');
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000003','e1000000-0000-4000-8000-000000000001');
DO $$ BEGIN
 BEGIN PERFORM public.remove_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000003','e1000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'changed action accepted'; EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN PERFORM public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000002','b0000000-0000-4000-8000-000000000003','e1000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'changed batch accepted'; EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN PERFORM public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000001','e1000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'changed member accepted'; EXCEPTION WHEN unique_violation THEN NULL; END;
END $$;
SELECT (SELECT count(*) FROM public.batch_coach_assignments) || ':' || (SELECT count(*) FROM public.batch_coach_mutation_requests); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1:1')

    def test_coach_request_replay_denied_after_manager_suspension_and_receipts_are_private(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
INSERT INTO public.workspace_memberships (id,workspace_id,user_id,role,status) VALUES ('b0000000-0000-4000-8000-000000000003','a0000000-0000-4000-8000-000000000001','33333333-3333-4333-8333-333333333333','coach','active');
INSERT INTO public.batches (id,workspace_id,course_id,name) VALUES ('d0000000-0000-4000-8000-000000000001','a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Morning');
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000003','e1000000-0000-4000-8000-000000000001');
UPDATE public.workspace_memberships SET status='suspended' WHERE id='b0000000-0000-4000-8000-000000000001';
DO $$ BEGIN BEGIN PERFORM public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001','d0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000003','e1000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'suspended manager replay accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT NOT has_table_privilege('authenticated','public.batch_coach_mutation_requests','SELECT') AND NOT has_function_privilege('authenticated','public.mutate_private_batch_coach(uuid,uuid,uuid,uuid,text)','EXECUTE'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 't')

    def test_private_class_journey_assignment_session_and_removal(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
INSERT INTO public.workspace_memberships (id,workspace_id,user_id,role,status) VALUES ('b0000000-0000-4000-8000-000000000003','a0000000-0000-4000-8000-000000000001','33333333-3333-4333-8333-333333333333','coach','active');
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE journey(course_id uuid, batch_id uuid, session_id uuid);
INSERT INTO journey(course_id) SELECT public.create_private_course('a0000000-0000-4000-8000-000000000001','Dance','f0000000-0000-4000-8000-000000000001');
UPDATE journey SET batch_id=public.create_private_batch('a0000000-0000-4000-8000-000000000001',course_id,'Beginners','f0000000-0000-4000-8000-000000000002');
SELECT public.configure_private_workspace_zone('a0000000-0000-4000-8000-000000000001','Asia/Kolkata');
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001',batch_id,'b0000000-0000-4000-8000-000000000003','f0000000-0000-4000-8000-000000000003') FROM journey;
SELECT set_config('request.jwt.claim.sub','33333333-3333-4333-8333-333333333333',true);
UPDATE journey SET session_id=public.create_private_local_session('a0000000-0000-4000-8000-000000000001',batch_id,'2026-11-03 17:00',60,'f0000000-0000-4000-8000-000000000004');
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.remove_private_batch_coach('a0000000-0000-4000-8000-000000000001',batch_id,'b0000000-0000-4000-8000-000000000003','f0000000-0000-4000-8000-000000000005') FROM journey;
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001',batch_id,'b0000000-0000-4000-8000-000000000003','f0000000-0000-4000-8000-000000000003') FROM journey;
SELECT set_config('request.jwt.claim.sub','33333333-3333-4333-8333-333333333333',true);
DO $$ BEGIN BEGIN PERFORM public.create_private_local_session('a0000000-0000-4000-8000-000000000001',(SELECT batch_id FROM journey),'2026-11-10 17:00',60,'f0000000-0000-4000-8000-000000000006'); RAISE EXCEPTION 'removed coach retained access'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT (SELECT count(*) FROM public.schedule_sessions s JOIN journey j ON s.id=j.session_id WHERE s.starts_at='2026-11-03 11:30+00') || ':' || (SELECT count(*) FROM public.batch_coach_assignments) || ':' || (SELECT count(*) FROM public.schedule_sessions); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1:0:1')

    def test_authenticated_course_creation_owner_and_admin_retry(self):
        out = run_sql(LEGACY_SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.create_course('a0000000-0000-4000-8000-000000000001',' Dance ','e3000000-0000-4000-8000-000000000001') = public.create_course('a0000000-0000-4000-8000-000000000001','Dance','e3000000-0000-4000-8000-000000000001');
RESET ROLE;
UPDATE public.workspace_memberships SET role='admin' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated;
SELECT public.create_course('a0000000-0000-4000-8000-000000000001','Advanced Dance','e3000000-0000-4000-8000-000000000002') IS NOT NULL;
RESET ROLE;
SELECT count(*) FROM public.courses WHERE name IN ('Dance','Advanced Dance'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-3:], ['t', 't', '2'])

    def test_authenticated_course_creation_rejects_unapproved_roles_and_suspensions(self):
        out = run_sql(LEGACY_SETUP + """
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_course('a0000000-0000-4000-8000-000000000001','Dance',gen_random_uuid()); RAISE EXCEPTION 'coach accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
DO $$ BEGIN BEGIN PERFORM public.create_course('a0000000-0000-4000-8000-000000000001','Dance',gen_random_uuid()); RAISE EXCEPTION 'other workspace accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE;
UPDATE public.workspace_memberships SET role='owner',status='suspended' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_course('a0000000-0000-4000-8000-000000000001','Dance',gen_random_uuid()); RAISE EXCEPTION 'suspended member accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE;
UPDATE public.workspace_memberships SET status='active' WHERE id='b0000000-0000-4000-8000-000000000001'; UPDATE public.workspaces SET status='suspended' WHERE id='a0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN PERFORM public.create_course('a0000000-0000-4000-8000-000000000001','Dance',gen_random_uuid()); RAISE EXCEPTION 'suspended workspace accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SELECT count(*) FROM public.courses WHERE name='Dance'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_authenticated_course_creation_rejects_bad_input_and_changed_retry(self):
        out = run_sql(LEGACY_SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN
 BEGIN PERFORM public.create_course('a0000000-0000-4000-8000-000000000001',' ',gen_random_uuid()); RAISE EXCEPTION 'blank accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
 PERFORM public.create_course('a0000000-0000-4000-8000-000000000001','Dance','e3000000-0000-4000-8000-000000000001');
 BEGIN PERFORM public.create_course('a0000000-0000-4000-8000-000000000001','Painting','e3000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'changed retry accepted'; EXCEPTION WHEN unique_violation THEN NULL; END;
END $$;
RESET ROLE; SELECT count(*) FROM public.courses WHERE name='Dance'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1')

    def test_authenticated_course_creation_does_not_grant_table_or_anonymous_access(self):
        out = run_sql("""
BEGIN;
SET LOCAL ROLE anon;
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_course(gen_random_uuid(),'Dance',gen_random_uuid()); RAISE EXCEPTION 'anonymous invocation succeeded'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE;
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN INSERT INTO public.courses (workspace_id,name) VALUES (gen_random_uuid(),'Bypass'); RAISE EXCEPTION 'direct insert succeeded'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE;
SELECT NOT has_function_privilege('authenticated','public.create_course(uuid,text,uuid)','EXECUTE') AND NOT has_function_privilege('anon','public.create_course(uuid,text,uuid)','EXECUTE') AND NOT has_table_privilege('authenticated','public.courses','SELECT') AND NOT has_table_privilege('authenticated','public.courses','INSERT');
ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 't')

    def test_authenticated_course_wrapper_metadata_and_private_helper_denial(self):
        out = run_sql("""
SELECT p.prosecdef AND p.proconfig @> ARRAY['search_path=""'] AND pg_catalog.pg_get_userbyid(p.proowner)=current_user
 AND NOT has_function_privilege('authenticated','public.create_private_course(uuid,text,uuid)','EXECUTE')
 AND NOT has_function_privilege('authenticated','public.assert_private_workspace_manager(uuid)','EXECUTE')
FROM pg_catalog.pg_proc p WHERE p.oid='public.create_course(uuid,text,uuid)'::regprocedure;
""")
        self.assertEqual(out, 't')

    def test_authenticated_course_creation_rejects_missing_identity(self):
        out = run_sql(LEGACY_SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','',true);
DO $$ BEGIN BEGIN PERFORM public.create_course('a0000000-0000-4000-8000-000000000001','Dance',gen_random_uuid()); RAISE EXCEPTION 'missing identity accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SELECT count(*) FROM public.courses WHERE name='Dance'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_authenticated_batch_creation_owner_admin_and_retry(self):
        out = run_sql(LEGACY_SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001',' Beginners ','e4000000-0000-4000-8000-000000000001') = public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Beginners','e4000000-0000-4000-8000-000000000001');
RESET ROLE; UPDATE public.workspace_memberships SET role='admin' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated; SELECT public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Advanced','e4000000-0000-4000-8000-000000000002') IS NOT NULL;
RESET ROLE; SELECT count(*) FROM public.batches WHERE name IN ('Beginners','Advanced'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-3:], ['t', 't', '2'])

    def test_authenticated_batch_rejects_unauthorized_missing_or_suspended_actor(self):
        out = run_sql(LEGACY_SETUP + """
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','',true);
DO $$ BEGIN BEGIN PERFORM public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Beginners',gen_random_uuid()); RAISE EXCEPTION 'missing actor accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Beginners',gen_random_uuid()); RAISE EXCEPTION 'coach accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; UPDATE public.workspace_memberships SET role='owner',status='suspended' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN PERFORM public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Beginners',gen_random_uuid()); RAISE EXCEPTION 'suspended member accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; UPDATE public.workspace_memberships SET status='active' WHERE id='b0000000-0000-4000-8000-000000000001'; UPDATE public.workspaces SET status='suspended' WHERE id='a0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN PERFORM public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Beginners',gen_random_uuid()); RAISE EXCEPTION 'suspended workspace accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SELECT count(*) FROM public.batches; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_authenticated_batch_rejects_cross_workspace_course_and_changed_retry(self):
        out = run_sql(LEGACY_SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('a0000000-0000-4000-8000-000000000002','11111111-1111-4111-8111-111111111111','admin','active');
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN
 BEGIN PERFORM public.create_batch('a0000000-0000-4000-8000-000000000002','c0000000-0000-4000-8000-000000000001','Other',gen_random_uuid()); RAISE EXCEPTION 'cross-workspace course accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
 BEGIN PERFORM public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001',' ',gen_random_uuid()); RAISE EXCEPTION 'blank accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
 PERFORM public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Beginners','e4000000-0000-4000-8000-000000000001');
 BEGIN PERFORM public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Advanced','e4000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'changed retry accepted'; EXCEPTION WHEN unique_violation THEN NULL; END;
END $$;
RESET ROLE; SELECT count(*) FROM public.batches WHERE name='Beginners'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1')

    def test_authenticated_batch_denies_anon_direct_table_and_private_access(self):
        out = run_sql("""
BEGIN; SET LOCAL ROLE anon; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_batch(gen_random_uuid(),gen_random_uuid(),'Beginners',gen_random_uuid()); RAISE EXCEPTION 'anonymous accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN INSERT INTO public.batches (workspace_id,course_id,name) VALUES (gen_random_uuid(),gen_random_uuid(),'Bypass'); RAISE EXCEPTION 'direct insert succeeded'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE;
SELECT NOT has_function_privilege('authenticated','public.create_batch(uuid,uuid,text,uuid)','EXECUTE') AND NOT has_function_privilege('anon','public.create_batch(uuid,uuid,text,uuid)','EXECUTE') AND NOT has_function_privilege('authenticated','public.create_private_batch(uuid,uuid,text,uuid)','EXECUTE') AND NOT has_table_privilege('authenticated','public.batches','SELECT') AND NOT has_table_privilege('authenticated','public.batches','INSERT'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 't')

    def test_authenticated_batch_wrapper_security_metadata(self):
        self.assertEqual(run_sql("SELECT p.prosecdef AND p.proconfig @> ARRAY['search_path=\"\"'] AND pg_catalog.pg_get_userbyid(p.proowner)=current_user FROM pg_catalog.pg_proc p WHERE p.oid='public.create_batch(uuid,uuid,text,uuid)'::regprocedure;"), 't')

    def test_atomic_class_setup_creates_both_and_retries_for_owner_and_admin(self):
        out = run_sql(LEGACY_SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE first_setup AS SELECT * FROM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','Beginners','e5000000-0000-4000-8000-000000000001');
SELECT (SELECT course_id FROM first_setup) = (SELECT course_id FROM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001',' Dance ',' Beginners ','e5000000-0000-4000-8000-000000000001'));
RESET ROLE; UPDATE public.workspace_memberships SET role='admin' WHERE id='b0000000-0000-4000-8000-000000000001'; SET LOCAL ROLE authenticated;
SELECT count(*) FROM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Painting','Intermediate','e5000000-0000-4000-8000-000000000002');
RESET ROLE; SELECT (SELECT count(*) FROM public.courses WHERE name IN ('Dance','Painting')) || ':' || (SELECT count(*) FROM public.batches WHERE name IN ('Beginners','Intermediate')); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-3:], ['t', '1', '2:2'])

    def test_atomic_class_setup_rolls_back_when_batch_invalid(self):
        out = run_sql(LEGACY_SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','  ',gen_random_uuid()); RAISE EXCEPTION 'invalid batch accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END; END $$;
RESET ROLE; SELECT (SELECT count(*) FROM public.courses WHERE name='Dance') || ':' || (SELECT count(*) FROM public.batches); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0:0')

    def test_atomic_class_setup_rejects_changed_retry_without_mutation(self):
        out = run_sql(LEGACY_SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN
 PERFORM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','Beginners','e5000000-0000-4000-8000-000000000001');
 BEGIN PERFORM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','Advanced','e5000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'changed batch accepted'; EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN PERFORM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Painting','Beginners','e5000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'changed course accepted'; EXCEPTION WHEN unique_violation THEN NULL; END;
END $$;
RESET ROLE; SELECT (SELECT count(*) FROM public.courses WHERE name='Dance') || ':' || (SELECT count(*) FROM public.batches WHERE name='Beginners') || ':' || (SELECT count(*) FROM public.batches WHERE name='Advanced'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1:1:0')

    def test_atomic_class_setup_rejects_coach_and_missing_identity(self):
        out = run_sql(LEGACY_SETUP + """
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','Beginners',gen_random_uuid()); RAISE EXCEPTION 'coach accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT set_config('request.jwt.claim.sub','',true);
DO $$ BEGIN BEGIN PERFORM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','Beginners',gen_random_uuid()); RAISE EXCEPTION 'missing identity accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SELECT count(*) FROM public.courses WHERE name='Dance'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_atomic_class_setup_denies_anon_and_direct_access(self):
        out = run_sql("""
BEGIN; SET LOCAL ROLE anon; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_course_and_batch(gen_random_uuid(),'Dance','Beginners',gen_random_uuid()); RAISE EXCEPTION 'anonymous accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SELECT NOT has_function_privilege('authenticated','public.create_course_and_batch(uuid,text,text,uuid)','EXECUTE') AND NOT has_function_privilege('anon','public.create_course_and_batch(uuid,text,text,uuid)','EXECUTE') AND NOT has_table_privilege('authenticated','public.courses','INSERT') AND NOT has_table_privilege('authenticated','public.batches','INSERT'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 't')

    def test_atomic_class_setup_does_not_adopt_standalone_request_ids(self):
        out = run_sql(LEGACY_SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE standalone_course AS SELECT public.create_course('a0000000-0000-4000-8000-000000000001','Dance','e5000000-0000-4000-8000-000000000003') AS id;
CREATE TEMP TABLE atomic_after_course AS SELECT * FROM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','Beginners','e5000000-0000-4000-8000-000000000003');
CREATE TEMP TABLE standalone_batch AS SELECT public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Evening','e5000000-0000-4000-8000-000000000004') AS id;
CREATE TEMP TABLE atomic_after_batch AS SELECT * FROM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Painting','Evening','e5000000-0000-4000-8000-000000000004');
SELECT (SELECT id FROM standalone_course) <> (SELECT course_id FROM atomic_after_course) AND (SELECT id FROM standalone_batch) <> (SELECT batch_id FROM atomic_after_batch);
RESET ROLE; SELECT (SELECT count(*) FROM public.courses WHERE name='Dance') || ':' || (SELECT count(*) FROM public.batches WHERE name='Evening'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:], ['t', '2:2'])

    def test_atomic_class_setup_wrapper_and_receipt_are_private_by_default(self):
        out = run_sql("""
SELECT p.prosecdef AND p.proconfig @> ARRAY['search_path=""'] AND pg_catalog.pg_get_userbyid(p.proowner)=current_user
 AND NOT has_table_privilege('authenticated','public.class_setup_requests','SELECT')
 AND NOT has_table_privilege('authenticated','public.class_setup_requests','INSERT')
 AND NOT has_function_privilege('authenticated','public.create_private_course(uuid,text,uuid)','EXECUTE')
FROM pg_catalog.pg_proc p WHERE p.oid='public.create_course_and_batch(uuid,text,text,uuid)'::regprocedure;
""")
        self.assertEqual(out, 't')

    def test_atomic_class_setup_rolls_back_actual_batch_insert_failure_and_retries(self):
        out = run_sql(LEGACY_SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
CREATE FUNCTION public.test_reject_batch_insert() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic batch failure'; END $$;
CREATE TRIGGER test_reject_batch_insert BEFORE INSERT ON public.batches FOR EACH ROW EXECUTE FUNCTION public.test_reject_batch_insert();
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','Beginners','e5000000-0000-4000-8000-000000000005'); RAISE EXCEPTION USING ERRCODE='P0002',MESSAGE='batch failure not raised'; EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'synthetic batch failure' THEN RAISE; END IF; END; END $$;
RESET ROLE;
SELECT (SELECT count(*) FROM public.courses WHERE name='Dance') || ':' || (SELECT count(*) FROM public.batches WHERE name='Beginners') || ':' || (SELECT count(*) FROM public.class_setup_requests WHERE request_id='e5000000-0000-4000-8000-000000000005');
DROP TRIGGER test_reject_batch_insert ON public.batches;
SET LOCAL ROLE authenticated;
SELECT count(*) FROM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','Beginners','e5000000-0000-4000-8000-000000000005');
RESET ROLE;
SELECT (SELECT count(*) FROM public.courses WHERE name='Dance') || ':' || (SELECT count(*) FROM public.batches WHERE name='Beginners') || ':' || (SELECT count(*) FROM public.class_setup_requests WHERE request_id='e5000000-0000-4000-8000-000000000005'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-3:], ['0:0:0', '1', '1:1:1'])

    def test_atomic_class_setup_database_switch_denies_authenticated_manager(self):
        out = run_sql(LEGACY_SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
UPDATE public.class_setup_controls SET enabled=false WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN
 BEGIN PERFORM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','Beginners',gen_random_uuid()); RAISE EXCEPTION 'disabled atomic setup succeeded'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN PERFORM public.create_course('a0000000-0000-4000-8000-000000000001','Dance',gen_random_uuid()); RAISE EXCEPTION 'disabled course creation succeeded'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN PERFORM public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Beginners',gen_random_uuid()); RAISE EXCEPTION 'disabled batch creation succeeded'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
RESET ROLE; SELECT (SELECT count(*) FROM public.courses WHERE name='Dance') || ':' || (SELECT count(*) FROM public.class_setup_requests); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0:0')

    def test_atomic_class_setup_database_switch_is_private_and_disabled_by_default(self):
        out = run_sql("""
SELECT NOT enabled AND NOT has_table_privilege('anon','public.class_setup_controls','UPDATE') AND NOT has_table_privilege('authenticated','public.class_setup_controls','SELECT') AND NOT has_table_privilege('authenticated','public.class_setup_controls','UPDATE') FROM public.class_setup_controls WHERE id=true;
""")
        self.assertEqual(out, 't')

    def test_class_setup_reservation_returns_same_id_for_matching_retry(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE first_reservation AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT (SELECT id FROM first_reservation) = public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001',' Dance ',' Beginners ');
ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 't')

    def test_class_setup_reservation_rejects_changed_payload(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners');
DO $$ BEGIN BEGIN PERFORM public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Advanced'); RAISE EXCEPTION 'changed request accepted'; EXCEPTION WHEN unique_violation THEN NULL; END; END $$;
SELECT count(*) FROM public.class_setup_intents; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1')

    def test_class_setup_reservation_denies_coach_and_disabled_control(self):
        out = run_sql(SETUP + """
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners'); RAISE EXCEPTION 'coach accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001'; UPDATE public.class_setup_controls SET enabled=false WHERE id=true;
DO $$ BEGIN BEGIN PERFORM public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners'); RAISE EXCEPTION 'disabled accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT count(*) FROM public.class_setup_intents; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_class_setup_reservation_is_inaccessible_to_app_roles(self):
        out = run_sql("""
SELECT NOT has_table_privilege('authenticated','public.class_setup_intents','SELECT')
 AND NOT has_table_privilege('anon','public.class_setup_intents','INSERT')
 AND NOT has_function_privilege('authenticated','public.reserve_private_class_setup(uuid,text,text)','EXECUTE')
 AND NOT has_function_privilege('anon','public.reserve_private_class_setup(uuid,text,text)','EXECUTE');
""")
        self.assertEqual(out, 't')

    def test_class_setup_reservation_rejects_invalid_details_and_missing_identity(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','  ','Beginners'); RAISE EXCEPTION 'empty name accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END; END $$;
SELECT set_config('request.jwt.claim.sub','',true);
DO $$ BEGIN BEGIN PERFORM public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners'); RAISE EXCEPTION 'missing identity accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT count(*) FROM public.class_setup_intents; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_class_setup_reservations_are_scoped_to_actor_and_workspace(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners');
SELECT set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000002','Painting','Advanced');
DO $$ BEGIN BEGIN PERFORM public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Painting','Advanced'); RAISE EXCEPTION 'cross workspace allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT count(*) FROM public.class_setup_intents; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '2')

    def test_reserved_setup_completion_retries_return_same_records(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved_intent AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
CREATE TEMP TABLE first_result AS SELECT * FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent));
SELECT (SELECT course_id FROM first_result) = (SELECT course_id FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent)));
SELECT (SELECT count(*) FROM public.courses WHERE name='Dance') || ':' || (SELECT count(*) FROM public.batches WHERE name='Beginners') || ':' || (SELECT count(*) FROM public.class_setup_intents WHERE id=(SELECT id FROM saved_intent) AND completed_course_id IS NOT NULL); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:], ['t', '1:1:1'])

    def test_reserved_setup_completion_rejects_wrong_actor_and_unknown_id(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner';
INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('a0000000-0000-4000-8000-000000000001','22222222-2222-4222-8222-222222222222','admin','active');
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved_intent AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
DO $$ BEGIN BEGIN PERFORM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent)); RAISE EXCEPTION 'cross actor accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',gen_random_uuid()); RAISE EXCEPTION 'missing intent accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT count(*) FROM public.courses WHERE name='Dance'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_reserved_setup_completion_rolls_back_batch_failure(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved_intent AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
CREATE FUNCTION public.test_reject_reserved_batch() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic batch failure'; END $$;
CREATE TRIGGER test_reject_reserved_batch BEFORE INSERT ON public.batches FOR EACH ROW EXECUTE FUNCTION public.test_reject_reserved_batch();
DO $$ BEGIN BEGIN PERFORM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent)); RAISE EXCEPTION USING ERRCODE='P0002', MESSAGE='expected failure missing'; EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'synthetic batch failure' THEN RAISE; END IF; END; END $$;
SELECT (SELECT count(*) FROM public.courses WHERE name='Dance') || ':' || (SELECT count(*) FROM public.class_setup_requests WHERE request_id=(SELECT id FROM saved_intent)) || ':' || (SELECT count(*) FROM public.class_setup_intents WHERE completed_course_id IS NOT NULL);
DROP TRIGGER test_reject_reserved_batch ON public.batches;
SELECT count(*) FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent)); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:], ['0:0:0', '1'])

    def test_reserved_setup_completion_is_inaccessible_to_app_roles(self):
        out = run_sql("""
SELECT NOT has_function_privilege('authenticated','public.complete_private_class_setup(uuid,uuid)','EXECUTE') AND NOT has_function_privilege('anon','public.complete_private_class_setup(uuid,uuid)','EXECUTE');
""")
        self.assertEqual(out, 't')

    def test_reserved_completion_does_not_adopt_separate_atomic_receipt(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved_intent AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
CREATE TEMP TABLE separate_result AS SELECT * FROM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','Beginners',(SELECT id FROM saved_intent));
SELECT (SELECT course_id FROM separate_result) <> (SELECT course_id FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent)));
SELECT (SELECT count(*) FROM public.courses WHERE name='Dance') || ':' || (SELECT count(*) FROM public.batches WHERE name='Beginners'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:], ['t','2:2'])

    def test_class_setup_status_reports_unknown_pending_and_completed(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT state FROM public.private_class_setup_status('a0000000-0000-4000-8000-000000000001');
CREATE TEMP TABLE saved_intent AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT state FROM public.private_class_setup_status('a0000000-0000-4000-8000-000000000001');
SELECT count(*) FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent));
SELECT state FROM public.private_class_setup_status('a0000000-0000-4000-8000-000000000001'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-4:], ['unknown','pending','1','completed'])

    def test_class_setup_status_does_not_reveal_another_manager_intent(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner';
INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('a0000000-0000-4000-8000-000000000001','22222222-2222-4222-8222-222222222222','admin','active');
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners');
SELECT set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
SELECT state || ':' || (intent_id IS NULL)::text FROM public.private_class_setup_status('a0000000-0000-4000-8000-000000000001'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 'unknown:true')

    def test_class_setup_status_denies_coach_and_disabled_control(self):
        out = run_sql(SETUP + """
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.private_class_setup_status('a0000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'coach allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001'; UPDATE public.class_setup_controls SET enabled=false WHERE id=true;
DO $$ BEGIN BEGIN PERFORM public.private_class_setup_status('a0000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'disabled allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 'denied')

    def test_class_setup_status_denies_application_roles(self):
        out=run_sql("SELECT NOT has_function_privilege('authenticated','public.private_class_setup_status(uuid)','EXECUTE') AND NOT has_function_privilege('anon','public.private_class_setup_status(uuid)','EXECUTE');")
        self.assertEqual(out,'t')

    def test_unreserved_class_creation_denied_to_app_roles_even_when_enabled(self):
        out = run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN
 BEGIN PERFORM public.create_course('a0000000-0000-4000-8000-000000000001','Dance',gen_random_uuid()); RAISE EXCEPTION 'course bypass allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN PERFORM public.create_batch('a0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','Beginners',gen_random_uuid()); RAISE EXCEPTION 'batch bypass allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN PERFORM public.create_course_and_batch('a0000000-0000-4000-8000-000000000001','Dance','Beginners',gen_random_uuid()); RAISE EXCEPTION 'combined bypass allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
RESET ROLE; SELECT (SELECT count(*) FROM public.courses WHERE name='Dance') || ':' || (SELECT count(*) FROM public.batches); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0:0')

    def test_class_setup_acknowledgement_is_idempotent_and_retains_receipt(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved_intent AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT count(*) FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent));
SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent));
SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent));
SELECT (SELECT acknowledged FROM public.class_setup_intents WHERE id=(SELECT id FROM saved_intent)) AND (SELECT count(*) FROM public.class_setup_intents)=1;
ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-4:], ['1','t','t','t'])

    def test_class_setup_acknowledgement_rejects_pending_and_wrong_actor(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner';
INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('a0000000-0000-4000-8000-000000000001','22222222-2222-4222-8222-222222222222','admin','active');
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved_intent AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
DO $$ BEGIN BEGIN PERFORM public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent)); RAISE EXCEPTION 'pending accepted'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
SELECT count(*) FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent));
SELECT set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
DO $$ BEGIN BEGIN PERFORM public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent)); RAISE EXCEPTION 'other actor accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT NOT acknowledged FROM public.class_setup_intents WHERE id=(SELECT id FROM saved_intent); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 't')

    def test_class_setup_acknowledgement_does_not_release_slot(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved_intent AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT count(*) FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent));
SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent));
SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners')=(SELECT id FROM saved_intent);
DO $$ BEGIN BEGIN PERFORM public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Advanced'); RAISE EXCEPTION 'slot released'; EXCEPTION WHEN unique_violation THEN NULL; END; END $$;
SELECT count(*) FROM public.courses WHERE name='Dance'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:], ['t','1'])

    def test_class_setup_acknowledgement_is_private(self):
        out=run_sql("SELECT NOT has_function_privilege('authenticated','public.acknowledge_private_class_setup(uuid,uuid)','EXECUTE') AND NOT has_function_privilege('anon','public.acknowledge_private_class_setup(uuid,uuid)','EXECUTE');")
        self.assertEqual(out,'t')

    def test_class_setup_acknowledgement_denies_suspension_and_disabled_control(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved_intent AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT count(*) FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent));
UPDATE public.workspace_memberships SET status='suspended' WHERE id='b0000000-0000-4000-8000-000000000001';
DO $$ BEGIN BEGIN PERFORM public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent)); RAISE EXCEPTION 'suspended accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
UPDATE public.workspace_memberships SET status='active' WHERE id='b0000000-0000-4000-8000-000000000001'; UPDATE public.class_setup_controls SET enabled=false WHERE id=true;
DO $$ BEGIN BEGIN PERFORM public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM saved_intent)); RAISE EXCEPTION 'disabled accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT NOT acknowledged FROM public.class_setup_intents WHERE id=(SELECT id FROM saved_intent); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], 't')

    def test_next_class_transition_retries_same_token_without_releasing_history(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE prior AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT count(*) FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
CREATE TEMP TABLE next_intent AS SELECT public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),'e6000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT (SELECT id FROM next_intent) <> (SELECT id FROM prior) AND (SELECT id FROM next_intent)=public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),'e6000000-0000-4000-8000-000000000001',' Dance ',' Beginners ');
DO $$ BEGIN BEGIN PERFORM public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners'); RAISE EXCEPTION 'legacy retry rebound'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
SELECT (SELECT count(*) FROM public.class_setup_intent_history WHERE id=(SELECT id FROM prior)) || ':' || (SELECT count(*) FROM public.class_setup_intents WHERE id=(SELECT id FROM next_intent)) || ':' || (SELECT count(*) FROM public.courses WHERE name='Dance'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:], ['t','1:1:1'])

    def test_next_class_transition_requires_completed_acknowledged_prior(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE prior AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
DO $$ BEGIN BEGIN PERFORM public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),gen_random_uuid(),'Art','Morning'); RAISE EXCEPTION 'pending accepted'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
SELECT count(*) FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
DO $$ BEGIN BEGIN PERFORM public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),gen_random_uuid(),'Art','Morning'); RAISE EXCEPTION 'unacknowledged accepted'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
SELECT count(*) FROM public.class_setup_intents WHERE id=(SELECT id FROM prior); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1')

    def test_next_class_transition_rejects_token_reuse_with_changed_details(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE prior AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT count(*) FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
SELECT public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),'e6000000-0000-4000-8000-000000000002','Art','Morning');
DO $$ BEGIN BEGIN PERFORM public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),'e6000000-0000-4000-8000-000000000002','Art','Evening'); RAISE EXCEPTION 'changed token accepted'; EXCEPTION WHEN unique_violation THEN NULL; END; END $$;
DO $$ BEGIN BEGIN PERFORM public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',gen_random_uuid(),'e6000000-0000-4000-8000-000000000002','Art','Morning'); RAISE EXCEPTION 'changed prior accepted'; EXCEPTION WHEN unique_violation THEN NULL; END; END $$;
SELECT count(*) FROM public.class_setup_intents WHERE course_name='Art' AND batch_name='Morning'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '1')

    def test_next_class_transition_is_inaccessible_to_app_roles(self):
        out=run_sql("SELECT NOT has_function_privilege('authenticated','public.advance_private_class_setup(uuid,uuid,uuid,text,text)','EXECUTE') AND NOT has_function_privilege('anon','public.advance_private_class_setup(uuid,uuid,uuid,text,text)','EXECUTE') AND NOT has_table_privilege('authenticated','public.class_setup_intent_history','SELECT') AND NOT has_table_privilege('authenticated','public.class_setup_next_requests','SELECT');")
        self.assertEqual(out,'t')

    def test_next_class_old_token_replay_after_later_transition_is_nonmutating(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE prior AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT * FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
CREATE TEMP TABLE second AS SELECT public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),'e6000000-0000-4000-8000-000000000003','Art','Morning') AS id;
SELECT * FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM second));
SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM second));
CREATE TEMP TABLE third AS SELECT public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM second),'e6000000-0000-4000-8000-000000000004','Music','Evening') AS id;
SELECT public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),'e6000000-0000-4000-8000-000000000003','Art','Morning')=(SELECT id FROM second);
SELECT count(*) FROM public.class_setup_intents WHERE id=(SELECT id FROM third) AND course_name='Music'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:], ['t','1'])

    def test_next_class_transition_rolls_back_when_receipt_insert_fails(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE prior AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT * FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
CREATE FUNCTION public.test_reject_next_receipt() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic receipt failure'; END $$;
CREATE TRIGGER test_reject_next_receipt BEFORE INSERT ON public.class_setup_next_requests FOR EACH ROW EXECUTE FUNCTION public.test_reject_next_receipt();
DO $$ BEGIN BEGIN PERFORM public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),'e6000000-0000-4000-8000-000000000005','Art','Morning'); RAISE EXCEPTION USING ERRCODE='P0002',MESSAGE='failure missing'; EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'synthetic receipt failure' THEN RAISE; END IF; END; END $$;
SELECT (SELECT count(*) FROM public.class_setup_intents WHERE id=(SELECT id FROM prior)) || ':' || (SELECT count(*) FROM public.class_setup_intent_history) || ':' || (SELECT count(*) FROM public.class_setup_next_requests);
DROP TRIGGER test_reject_next_receipt ON public.class_setup_next_requests;
SELECT public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),'e6000000-0000-4000-8000-000000000005','Art','Morning') IS NOT NULL; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:], ['1:0:0','t'])

    def test_current_class_recovery_finds_next_request_after_lost_response(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE prior AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT * FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
CREATE TEMP TABLE next_intent AS SELECT public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),'e6000000-0000-4000-8000-000000000001','Art','Morning') AS id;
SELECT state='pending' AND intent_id=(SELECT id FROM next_intent) AND prior_intent_id=(SELECT id FROM prior) AND request_id='e6000000-0000-4000-8000-000000000001' AND course_name='Art' AND batch_name='Morning' FROM public.recover_private_current_class_setup('a0000000-0000-4000-8000-000000000001');
SELECT count(*) FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM next_intent));
SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM next_intent));
SELECT state='completed' AND acknowledged AND course_id IS NOT NULL AND batch_id IS NOT NULL FROM public.recover_private_current_class_setup('a0000000-0000-4000-8000-000000000001'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-4:],['t','1','t','t'])

    def test_current_class_recovery_reports_unknown_and_initial_reservation(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT state || ':' || (intent_id IS NULL)::text FROM public.recover_private_current_class_setup('a0000000-0000-4000-8000-000000000001');
SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners');
SELECT state || ':' || (request_id IS NULL AND prior_intent_id IS NULL)::text FROM public.recover_private_current_class_setup('a0000000-0000-4000-8000-000000000001'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-3], 'unknown:true'); self.assertEqual(out.splitlines()[-1], 'pending:true')

    def test_current_class_recovery_hides_other_manager_and_denies_apps(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner';
INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('a0000000-0000-4000-8000-000000000001','22222222-2222-4222-8222-222222222222','admin','active');
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners');
SELECT set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
SELECT state || ':' || (intent_id IS NULL AND course_name IS NULL)::text FROM public.recover_private_current_class_setup('a0000000-0000-4000-8000-000000000001');
SELECT NOT has_function_privilege('authenticated','public.recover_private_current_class_setup(uuid)','EXECUTE') AND NOT has_function_privilege('anon','public.recover_private_current_class_setup(uuid)','EXECUTE'); ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:], ['unknown:true','t'])

    def test_current_class_recovery_denies_inactive_manager_and_disabled_control(self):
        out=run_sql(SETUP + """
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.recover_private_current_class_setup('a0000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'coach accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001'; UPDATE public.class_setup_controls SET enabled=false WHERE id=true;
DO $$ BEGIN BEGIN PERFORM public.recover_private_current_class_setup('a0000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'disabled accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1],'denied')

    def test_current_class_recovery_rejects_mismatched_receipt_payload(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner' WHERE id='b0000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE prior AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT * FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
SELECT public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),'e6000000-0000-4000-8000-000000000001','Art','Morning');
UPDATE public.class_setup_next_requests SET course_name='Tampered' WHERE request_id='e6000000-0000-4000-8000-000000000001';
DO $$ BEGIN BEGIN PERFORM public.recover_private_current_class_setup('a0000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'mismatched receipt accepted'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1],'denied')

    def test_current_class_recovery_rejects_foreign_history_reference(self):
        out=run_sql(SETUP + """
UPDATE public.workspace_memberships SET role='owner';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE prior AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000001','Dance','Beginners') AS id;
SELECT * FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior)); SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior));
SELECT public.advance_private_class_setup('a0000000-0000-4000-8000-000000000001',(SELECT id FROM prior),'e6000000-0000-4000-8000-000000000001','Art','Morning');
SELECT set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
CREATE TEMP TABLE other_prior AS SELECT public.reserve_private_class_setup('a0000000-0000-4000-8000-000000000002','Music','Evening') AS id;
SELECT * FROM public.complete_private_class_setup('a0000000-0000-4000-8000-000000000002',(SELECT id FROM other_prior)); SELECT public.acknowledge_private_class_setup('a0000000-0000-4000-8000-000000000002',(SELECT id FROM other_prior));
SELECT public.advance_private_class_setup('a0000000-0000-4000-8000-000000000002',(SELECT id FROM other_prior),'e6000000-0000-4000-8000-000000000002','Yoga','Noon');
UPDATE public.class_setup_next_requests SET prior_intent_id=(SELECT id FROM other_prior) WHERE request_id='e6000000-0000-4000-8000-000000000001';
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.recover_private_current_class_setup('a0000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'foreign history accepted'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1],'denied')
