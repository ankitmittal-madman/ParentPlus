"""Deny-by-default scheduling data and workspace integrity tests."""
import unittest
from tests.database.test_authorization import run_sql

SETUP = """
BEGIN;
INSERT INTO public.workspaces (id, name, type, created_by, creation_request_id) VALUES
 ('a0000000-0000-4000-8000-000000000001', 'Academy A', 'academy', '11111111-1111-4111-8111-111111111111', 'a1000000-0000-4000-8000-000000000001'),
 ('a0000000-0000-4000-8000-000000000002', 'Academy B', 'academy', '22222222-2222-4222-8222-222222222222', 'a1000000-0000-4000-8000-000000000002');
INSERT INTO public.workspace_memberships (id, workspace_id, user_id, role, status) VALUES
 ('b0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', '11111111-1111-4111-8111-111111111111', 'coach', 'active'),
 ('b0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000002', '22222222-2222-4222-8222-222222222222', 'coach', 'active');
INSERT INTO public.courses (id, workspace_id, name) VALUES
 ('c0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'Music');
"""

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
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000003');
SELECT public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000003');
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
  BEGIN PERFORM public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', target); RAISE EXCEPTION 'invalid target accepted'; EXCEPTION WHEN invalid_parameter_value THEN NULL; END;
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
 BEGIN PERFORM public.assign_private_batch_coach('a0000000-0000-4000-8000-000000000001', 'd0000000-0000-4000-8000-000000000001', 'b0000000-0000-4000-8000-000000000001'); RAISE EXCEPTION 'coach assigned self'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
SELECT count(*) FROM public.batch_coach_assignments; ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-1], '0')

    def test_private_coach_assignment_cannot_be_executed_by_app_roles(self):
        out = run_sql("""
SELECT NOT has_function_privilege('anon', 'public.assign_private_batch_coach(uuid,uuid,uuid)', 'EXECUTE') AND NOT has_function_privilege('authenticated', 'public.assign_private_batch_coach(uuid,uuid,uuid)', 'EXECUTE');
""")
        self.assertEqual(out, 't')
