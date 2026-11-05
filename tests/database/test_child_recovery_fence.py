"""Synthetic, transactional tests for an actor-scoped recovery fence."""
import unittest
import uuid
from tests.database.test_concurrent_authorization import query, start_psql_session, wait_for_session_marker, wait_for_blocking_relationship, close_psql_session
from tests.database.test_child_authorization import run_sql


class ChildRecoveryFenceTests(unittest.TestCase):
    def test_fence_prevents_late_initial_creation_and_is_idempotent(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.app_fence_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_fence_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'fenced request was accepted'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
SELECT count(*) FROM public.app_current_child_creation(); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-3:], ['fenced', 'fenced', '0'])

    def test_existing_request_is_reported_without_cancelling_it(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved AS SELECT * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_fence_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT disposition FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-2:], ['created', 'existing'])

    def test_stale_prior_is_unknown_and_does_not_fence(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.app_fence_child_creation('bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb','aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT disposition FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-2:], ['unknown', 'created'])

    def test_fence_rollback_allows_original_request(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SAVEPOINT before_fence;
SELECT public.app_fence_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
ROLLBACK TO before_fence;
SELECT disposition FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-2:], ['fenced', 'created'])

    def test_fence_is_private_and_disabled_by_default(self):
        output = run_sql("""
BEGIN;
SELECT NOT has_table_privilege('authenticated','public.child_creation_fences','SELECT')
 AND NOT has_function_privilege('anon','public.app_fence_child_creation(uuid,uuid)','EXECUTE')
 AND has_function_privilege('authenticated','public.app_fence_child_creation(uuid,uuid)','EXECUTE');
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.app_fence_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'disabled fence accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
ROLLBACK;
""")
        self.assertIn('t', output.splitlines())

    def test_fence_binds_prior_and_is_scoped_to_actor(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.app_fence_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_fence_child_creation('bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb','aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
SELECT disposition FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-4:-2], ['fenced', 'unknown'])
        self.assertEqual(output.splitlines()[-1], 'created')

    def test_cannot_fence_current_request_with_changed_prior(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved AS SELECT * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM saved));
SELECT public.app_fence_child_creation((SELECT intent_id FROM saved),'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT disposition FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-2:], ['unknown', 'existing'])

    def run_fence_race(self, fence_first, rollback_first=False):
        actor = '11111111-1111-4111-8111-111111111111'
        request = str(uuid.uuid4())
        name = 'Synthetic fence '+uuid.uuid4().hex
        first_label = 'fence_first_'+uuid.uuid4().hex
        second_label = 'fence_second_'+uuid.uuid4().hex
        self.addCleanup(query, f"BEGIN; DELETE FROM public.child_creation_fences WHERE actor_id='{actor}' AND request_id='{request}'; DELETE FROM public.child_creation_intents WHERE actor_id='{actor}' AND display_name='{name}'; DELETE FROM public.guardianships WHERE child_id IN (SELECT id FROM public.children WHERE created_by='{actor}' AND display_name='{name}'); DELETE FROM public.children WHERE created_by='{actor}' AND display_name='{name}'; UPDATE public.child_creation_controls SET enabled=false WHERE id=true; COMMIT;")
        query('UPDATE public.child_creation_controls SET enabled=true WHERE id=true;')
        first = second = None
        try:
            first = start_psql_session(); second = start_psql_session()
            for process, label in ((first, first_label), (second, second_label)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{label}',false); SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true);\n")
            fence = f"SELECT 'RESULT:' || public.app_fence_child_creation(NULL,'{request}');"
            create = f"SELECT 'RESULT:' || disposition FROM public.app_begin_child_creation('{name}',NULL,'{request}');"
            first.stdin.write((fence if fence_first else create)+" SELECT 'FIRST_READY';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'RESULT:fenced' if fence_first else 'RESULT:created'))
            self.assertTrue(wait_for_session_marker(first, 'FIRST_READY'))
            second.stdin.write((create if fence_first else fence)+" COMMIT; SELECT 'SECOND_DONE';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_label, first_label))
            first.stdin.write(('ROLLBACK' if rollback_first else 'COMMIT')+"; SELECT 'FIRST_DONE';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            if fence_first and not rollback_first:
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0); self.assertIn('Child creation unavailable', errors)
            else:
                expected = 'RESULT:created' if (fence_first or not rollback_first) else 'RESULT:fenced'
                self.assertTrue(wait_for_session_marker(second, expected)); self.assertTrue(wait_for_session_marker(second, 'SECOND_DONE'))
        finally:
            if second is not None: close_psql_session(second)
            if first is not None: close_psql_session(first)

    def test_fence_commits_before_delayed_create(self):
        self.run_fence_race(True)

    def test_create_commits_before_fence(self):
        self.run_fence_race(False)

    def test_fence_rollback_allows_waiting_create(self):
        self.run_fence_race(True, True)

    def test_create_rollback_allows_waiting_fence(self):
        self.run_fence_race(False, True)

    def test_fence_remains_effective_after_later_profiles(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.app_fence_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
CREATE TEMP TABLE first_profile AS SELECT * FROM public.app_begin_child_creation('Synthetic one',NULL,'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
SELECT public.app_ack_child_creation((SELECT intent_id FROM first_profile));
SELECT disposition FROM public.app_begin_child_creation('Synthetic two',(SELECT intent_id FROM first_profile),'cccccccc-3333-4333-8333-cccccccccccc');
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic late',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'late request accepted'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
SELECT public.app_fence_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-4:], ['fenced', 't', 'created', 'fenced'])

    def test_fence_does_not_expose_revoked_child(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved AS SELECT * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
RESET ROLE; UPDATE public.guardianships SET status='revoked' WHERE child_id=(SELECT child_id FROM saved);
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN PERFORM public.app_fence_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'revoked access accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-1], 'denied')

    def test_missing_identity_cannot_fence(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','',true);
DO $$ BEGIN BEGIN PERFORM public.app_fence_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'missing identity accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-1], 'denied')

    def test_fence_for_next_generation_blocks_exact_delayed_request(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved AS SELECT * FROM public.app_begin_child_creation('Synthetic one',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM saved));
SELECT public.app_fence_child_creation((SELECT intent_id FROM saved),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic delayed',(SELECT intent_id FROM saved),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb'); RAISE EXCEPTION 'late next request accepted'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
SELECT count(*) FROM public.app_current_child_creation(); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-3:], ['t', 'fenced', '1'])

    def test_superseded_request_returns_unknown_without_new_fence(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE first_profile AS SELECT * FROM public.app_begin_child_creation('Synthetic one',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM first_profile));
SELECT disposition FROM public.app_begin_child_creation('Synthetic two',(SELECT intent_id FROM first_profile),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
SELECT public.app_fence_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-3:], ['t', 'created', 'unknown'])

    def run_control_race(self, disable_first):
        actor = '11111111-1111-4111-8111-111111111111'
        request = str(uuid.uuid4())
        first_label, second_label = 'fence_control_first_'+uuid.uuid4().hex, 'fence_control_second_'+uuid.uuid4().hex
        self.addCleanup(query, f"BEGIN; DELETE FROM public.child_creation_fences WHERE actor_id='{actor}' AND request_id='{request}'; UPDATE public.child_creation_controls SET enabled=false WHERE id=true; COMMIT;")
        query('UPDATE public.child_creation_controls SET enabled=true WHERE id=true;')
        first = second = None
        try:
            first = start_psql_session(); second = start_psql_session()
            for process, label in ((first, first_label), (second, second_label)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{label}',false);\n")
            disable = "UPDATE public.child_creation_controls SET enabled=false WHERE id=true;"
            fence = f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); SELECT 'FENCE:' || public.app_fence_child_creation(NULL,'{request}');"
            first.stdin.write((disable if disable_first else fence)+" SELECT 'FIRST_READY';\n"); first.stdin.flush()
            if not disable_first: self.assertTrue(wait_for_session_marker(first, 'FENCE:fenced'))
            self.assertTrue(wait_for_session_marker(first, 'FIRST_READY'))
            second.stdin.write((fence if disable_first else disable)+" COMMIT; SELECT 'SECOND_DONE';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_label, first_label))
            first.stdin.write("COMMIT; SELECT 'FIRST_DONE';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            if disable_first:
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0); self.assertIn('Child creation unavailable', errors)
            else:
                self.assertTrue(wait_for_session_marker(second, 'SECOND_DONE'))
        finally:
            if second is not None: close_psql_session(second)
            if first is not None: close_psql_session(first)

    def test_disable_commits_before_fence(self):
        self.run_control_race(True)

    def test_fence_commits_before_disable(self):
        self.run_control_race(False)
