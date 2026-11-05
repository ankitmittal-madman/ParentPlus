"""Synthetic tests for private previous child-creation outcomes."""
import unittest
import uuid
from tests.database.test_concurrent_authorization import query, start_psql_session, wait_for_session_marker, wait_for_blocking_relationship, close_psql_session
from tests.database.test_child_authorization import run_sql


class ChildRecoveryHistoryTests(unittest.TestCase):
    def test_original_request_remains_recoverable_after_advance(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE first_profile AS SELECT * FROM public.app_begin_child_creation('Synthetic one',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM first_profile));
SELECT disposition FROM public.app_begin_child_creation('Synthetic two',(SELECT intent_id FROM first_profile),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
SELECT public.app_historical_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-3:], ['t', 'created', 'found'])

    def test_wrong_prior_and_actor_do_not_reveal_history(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE first_profile AS SELECT * FROM public.app_begin_child_creation('Synthetic one',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM first_profile));
SELECT disposition FROM public.app_begin_child_creation('Synthetic two',(SELECT intent_id FROM first_profile),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
SELECT public.app_historical_child_creation((SELECT intent_id FROM first_profile),'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
SELECT public.app_historical_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-3], 'unknown')
        self.assertEqual(output.splitlines()[-1], 'unknown')

    def test_revoked_guardian_cannot_recover_previous_profile(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE first_profile AS SELECT * FROM public.app_begin_child_creation('Synthetic one',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM first_profile));
SELECT disposition FROM public.app_begin_child_creation('Synthetic two',(SELECT intent_id FROM first_profile),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
RESET ROLE; UPDATE public.guardianships SET status='revoked' WHERE child_id=(SELECT child_id FROM first_profile);
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN PERFORM public.app_historical_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'revoked history exposed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-1], 'denied')

    def test_current_request_is_not_claimed_as_historical(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT disposition FROM public.app_begin_child_creation('Synthetic one',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_historical_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-2:], ['created', 'unknown'])

    def test_history_and_trigger_are_private_and_disabled_by_default(self):
        output = run_sql("""
BEGIN;
SELECT NOT has_table_privilege('authenticated','public.child_creation_history','SELECT')
 AND NOT has_function_privilege('authenticated','public.archive_private_child_creation_intent()','EXECUTE')
 AND NOT has_function_privilege('anon','public.app_historical_child_creation(uuid,uuid)','EXECUTE')
 AND has_function_privilege('authenticated','public.app_historical_child_creation(uuid,uuid)','EXECUTE')
 AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='child_creation_history' AND column_name IN ('display_name','name'))
 AND (SELECT count(*)=2 AND bool_and(p.prosecdef AND p.proconfig @> ARRAY['search_path=""'] AND pg_catalog.pg_get_userbyid(p.proowner)=current_user)
      FROM pg_catalog.pg_proc p WHERE p.oid IN ('public.app_historical_child_creation(uuid,uuid)'::regprocedure,'public.archive_private_child_creation_intent()'::regprocedure));
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.app_historical_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'disabled history accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
ROLLBACK;
""")
        self.assertIn('t', output.splitlines())

    def test_rolled_back_advance_does_not_archive_current(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE first_profile AS SELECT * FROM public.app_begin_child_creation('Synthetic one',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM first_profile));
SAVEPOINT before_advance;
SELECT disposition FROM public.app_begin_child_creation('Synthetic two',(SELECT intent_id FROM first_profile),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
ROLLBACK TO before_advance;
SELECT public.app_historical_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT count(*) FROM public.app_current_child_creation() WHERE intent_id=(SELECT intent_id FROM first_profile); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-3:], ['created', 'unknown', '1'])

    def test_deleted_old_profile_returns_unknown(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE first_profile AS SELECT * FROM public.app_begin_child_creation('Synthetic one',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM first_profile));
SELECT disposition FROM public.app_begin_child_creation('Synthetic two',(SELECT intent_id FROM first_profile),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
RESET ROLE; DELETE FROM public.guardianships WHERE child_id=(SELECT child_id FROM first_profile); DELETE FROM public.children WHERE id=(SELECT child_id FROM first_profile);
SET LOCAL ROLE authenticated; SELECT public.app_historical_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-1], 'unknown')

    def test_reused_request_id_is_bound_to_original_prior(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE first_profile AS SELECT * FROM public.app_begin_child_creation('Synthetic one',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM first_profile));
CREATE TEMP TABLE second_profile AS SELECT * FROM public.app_begin_child_creation('Synthetic two',(SELECT intent_id FROM first_profile),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
SELECT public.app_ack_child_creation((SELECT intent_id FROM second_profile));
SELECT disposition FROM public.app_begin_child_creation('Synthetic three',(SELECT intent_id FROM second_profile),'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_historical_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_historical_child_creation((SELECT intent_id FROM second_profile),'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-3:], ['created', 'found', 'unknown'])

    def test_missing_identity_cannot_recover_history(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','',true);
DO $$ BEGIN BEGIN PERFORM public.app_historical_child_creation(NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'missing identity accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-1], 'denied')

    def test_archive_failure_rolls_back_new_profile_and_intent(self):
        output = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
CREATE FUNCTION public.reject_synthetic_history() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic archive failure'; END $$;
CREATE TRIGGER reject_synthetic_history BEFORE INSERT ON public.child_creation_history FOR EACH ROW EXECUTE FUNCTION public.reject_synthetic_history();
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE first_profile AS SELECT * FROM public.app_begin_child_creation('Synthetic one',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM first_profile));
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic two',(SELECT intent_id FROM first_profile),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb'); RAISE EXCEPTION 'archive failure ignored'; EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'synthetic archive failure' THEN RAISE; END IF; END; END $$;
SELECT count(*) FROM public.app_current_child_creation() WHERE intent_id=(SELECT intent_id FROM first_profile);
RESET ROLE; SELECT count(*) FROM public.children WHERE display_name='Synthetic two'; ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-2:], ['1', '0'])

    def run_advance_race(self, advance_first, rollback_first=False):
        actor = '11111111-1111-4111-8111-111111111111'
        first_request, next_request = str(uuid.uuid4()), str(uuid.uuid4())
        name = 'Synthetic history '+uuid.uuid4().hex
        first_label, second_label = 'history_first_'+uuid.uuid4().hex, 'history_second_'+uuid.uuid4().hex
        self.addCleanup(query, f"BEGIN; DELETE FROM public.child_creation_history WHERE actor_id='{actor}' AND request_id IN ('{first_request}','{next_request}'); DELETE FROM public.child_creation_intents WHERE actor_id='{actor}' AND display_name='{name}'; DELETE FROM public.guardianships WHERE child_id IN (SELECT id FROM public.children WHERE created_by='{actor}' AND display_name='{name}'); DELETE FROM public.children WHERE created_by='{actor}' AND display_name='{name}'; UPDATE public.child_creation_controls SET enabled=false WHERE id=true; COMMIT;")
        query('UPDATE public.child_creation_controls SET enabled=true WHERE id=true;')
        initial = query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); SELECT 'ID:' || intent_id FROM public.app_begin_child_creation('{name}',NULL,'{first_request}'); COMMIT;")
        prior = next(line.removeprefix('ID:') for line in initial.splitlines() if line.startswith('ID:'))
        query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); SELECT public.app_ack_child_creation('{prior}'); COMMIT;")
        first = second = None
        try:
            first = start_psql_session(); second = start_psql_session()
            for process, label in ((first, first_label), (second, second_label)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{label}',false); SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true);\n")
            advance = f"SELECT 'RESULT:' || disposition FROM public.app_begin_child_creation('{name}','{prior}','{next_request}');"
            lookup = f"SELECT 'RESULT:' || public.app_historical_child_creation(NULL,'{first_request}');"
            first.stdin.write((advance if advance_first else lookup)+" SELECT 'FIRST_READY';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'RESULT:created' if advance_first else 'RESULT:unknown'))
            self.assertTrue(wait_for_session_marker(first, 'FIRST_READY'))
            second.stdin.write((lookup if advance_first else advance)+" COMMIT; SELECT 'SECOND_DONE';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_label, first_label))
            first.stdin.write(('ROLLBACK' if rollback_first else 'COMMIT')+"; SELECT 'FIRST_DONE';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            expected = ('RESULT:unknown' if rollback_first else 'RESULT:found') if advance_first else 'RESULT:created'
            self.assertTrue(wait_for_session_marker(second, expected)); self.assertTrue(wait_for_session_marker(second, 'SECOND_DONE'))
        finally:
            if second is not None: close_psql_session(second)
            if first is not None: close_psql_session(first)

    def test_advance_commit_before_history_lookup(self):
        self.run_advance_race(True)

    def test_advance_rollback_before_history_lookup(self):
        self.run_advance_race(True, True)

    def test_history_lookup_commit_before_advance(self):
        self.run_advance_race(False)

    def test_history_lookup_rollback_before_advance(self):
        self.run_advance_race(False, True)

    def run_revocation_race(self, revoke_first):
        actor = '11111111-1111-4111-8111-111111111111'
        first_request, next_request = str(uuid.uuid4()), str(uuid.uuid4())
        name = 'Synthetic history access '+uuid.uuid4().hex
        first_label, second_label = 'history_access_first_'+uuid.uuid4().hex, 'history_access_second_'+uuid.uuid4().hex
        self.addCleanup(query, f"BEGIN; DELETE FROM public.child_creation_history WHERE actor_id='{actor}' AND request_id IN ('{first_request}','{next_request}'); DELETE FROM public.child_creation_intents WHERE actor_id='{actor}' AND display_name='{name}'; DELETE FROM public.guardianships WHERE child_id IN (SELECT id FROM public.children WHERE created_by='{actor}' AND display_name='{name}'); DELETE FROM public.children WHERE created_by='{actor}' AND display_name='{name}'; UPDATE public.child_creation_controls SET enabled=false WHERE id=true; COMMIT;")
        query('UPDATE public.child_creation_controls SET enabled=true WHERE id=true;')
        initial = query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); SELECT 'ID:' || intent_id FROM public.app_begin_child_creation('{name}',NULL,'{first_request}'); SELECT 'CHILD:' || child_id FROM public.app_current_child_creation(); COMMIT;")
        prior = next(line.removeprefix('ID:') for line in initial.splitlines() if line.startswith('ID:'))
        child = next(line.removeprefix('CHILD:') for line in initial.splitlines() if line.startswith('CHILD:'))
        query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); SELECT public.app_ack_child_creation('{prior}'); SELECT disposition FROM public.app_begin_child_creation('{name}','{prior}','{next_request}'); COMMIT;")
        first = second = None
        try:
            first = start_psql_session(); second = start_psql_session()
            for process, label in ((first, first_label), (second, second_label)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{label}',false);\n")
            revoke = f"UPDATE public.guardianships SET status='revoked' WHERE child_id='{child}';"
            lookup = f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); SELECT 'RESULT:' || public.app_historical_child_creation(NULL,'{first_request}');"
            first.stdin.write((revoke if revoke_first else lookup)+" SELECT 'FIRST_READY';\n"); first.stdin.flush()
            if not revoke_first: self.assertTrue(wait_for_session_marker(first, 'RESULT:found'))
            self.assertTrue(wait_for_session_marker(first, 'FIRST_READY'))
            second.stdin.write((lookup if revoke_first else revoke)+" COMMIT; SELECT 'SECOND_DONE';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_label, first_label))
            first.stdin.write("COMMIT; SELECT 'FIRST_DONE';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            if revoke_first:
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0); self.assertIn('Child creation unavailable', errors)
            else:
                self.assertTrue(wait_for_session_marker(second, 'SECOND_DONE'))
        finally:
            if second is not None: close_psql_session(second)
            if first is not None: close_psql_session(first)

    def test_revocation_commits_before_history_lookup(self):
        self.run_revocation_race(True)

    def test_history_lookup_commits_before_revocation(self):
        self.run_revocation_race(False)

    def run_control_race(self, disable_first):
        actor = '11111111-1111-4111-8111-111111111111'
        request = str(uuid.uuid4())
        first_label, second_label = 'history_control_first_'+uuid.uuid4().hex, 'history_control_second_'+uuid.uuid4().hex
        self.addCleanup(query, 'UPDATE public.child_creation_controls SET enabled=false WHERE id=true;')
        query('UPDATE public.child_creation_controls SET enabled=true WHERE id=true;')
        first = second = None
        try:
            first = start_psql_session(); second = start_psql_session()
            for process, label in ((first, first_label), (second, second_label)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{label}',false);\n")
            disable = "UPDATE public.child_creation_controls SET enabled=false WHERE id=true;"
            lookup = f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); SELECT 'RESULT:' || public.app_historical_child_creation(NULL,'{request}');"
            first.stdin.write((disable if disable_first else lookup)+" SELECT 'FIRST_READY';\n"); first.stdin.flush()
            if not disable_first: self.assertTrue(wait_for_session_marker(first, 'RESULT:unknown'))
            self.assertTrue(wait_for_session_marker(first, 'FIRST_READY'))
            second.stdin.write((lookup if disable_first else disable)+" COMMIT; SELECT 'SECOND_DONE';\n"); second.stdin.flush()
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

    def test_disable_commits_before_history_lookup(self):
        self.run_control_race(True)

    def test_history_lookup_commits_before_disable(self):
        self.run_control_race(False)
