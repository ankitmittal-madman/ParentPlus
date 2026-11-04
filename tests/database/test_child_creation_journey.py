"""Synthetic tests for the default-off parent child-creation journey."""
import unittest
import uuid
from tests.database.test_concurrent_authorization import query, start_psql_session, wait_for_session_marker, wait_for_blocking_relationship, close_psql_session
from tests.database.test_child_authorization import run_sql


class ChildCreationJourneyTests(unittest.TestCase):
    def test_child_journey_default_off_and_legacy_rpc_private(self):
        result = run_sql("""
BEGIN; SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM * FROM public.app_current_child_creation(); RAISE EXCEPTION 'disabled status allowed'; EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM <> 'Child creation unavailable' THEN RAISE; END IF; END; END $$;
RESET ROLE;
SELECT NOT has_function_privilege('authenticated','public.create_child(text,uuid)','EXECUTE')
 AND NOT has_function_privilege('anon','public.app_begin_child_creation(text,uuid,uuid)','EXECUTE')
 AND has_function_privilege('authenticated','public.app_begin_child_creation(text,uuid,uuid)','EXECUTE')
 AND has_function_privilege('authenticated','public.app_current_child_creation()','EXECUTE')
 AND has_function_privilege('authenticated','public.app_ack_child_creation(uuid)','EXECUTE')
 AND NOT has_table_privilege('authenticated','public.child_creation_intents','SELECT'); ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-1], 't')

    def test_child_journey_private_helpers_and_wrapper_ownership(self):
        result = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.lock_private_child_creation_actor(); RAISE EXCEPTION 'private helper allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
DO $$ BEGIN BEGIN PERFORM count(*) FROM public.child_creation_intents; RAISE EXCEPTION 'private table allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE;
SELECT count(*)=3 AND bool_and(p.prosecdef AND p.proconfig @> ARRAY['search_path=""'] AND pg_catalog.pg_get_userbyid(p.proowner)=current_user AND has_function_privilege('authenticated',p.oid,'EXECUTE') AND NOT has_function_privilege('anon',p.oid,'EXECUTE'))
FROM pg_catalog.pg_proc p WHERE p.oid IN ('public.app_begin_child_creation(text,uuid,uuid)'::regprocedure,'public.app_current_child_creation()'::regprocedure,'public.app_ack_child_creation(uuid)'::regprocedure);
ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-1], 't')

    def test_child_journey_direct_legacy_call_denied_even_when_enabled(self):
        result = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_child('Synthetic child','dddddddd-4444-4444-8444-dddddddddddd'); RAISE EXCEPTION 'legacy call allowed'; EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM NOT LIKE 'permission denied for function create_child%' THEN RAISE; END IF; END; END $$;
RESET ROLE; SELECT count(*) FROM public.children WHERE creation_request_id='dddddddd-4444-4444-8444-dddddddddddd'; ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-1], '0')

    def test_child_journey_missing_control_and_identity_fail_closed(self):
        result = run_sql("""
BEGIN; DELETE FROM public.child_creation_controls WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'missing control allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; INSERT INTO public.child_creation_controls (id,enabled) VALUES (true,true);
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','',true);
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'missing identity allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SELECT count(*) FROM public.child_creation_intents; ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-1], '0')

    def test_child_journey_does_not_adopt_existing_same_name_profile(self):
        result = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
INSERT INTO public.children (id,display_name,created_by,creation_request_id) VALUES ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','Synthetic child','11111111-1111-4111-8111-111111111111','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');
INSERT INTO public.guardianships (child_id,guardian_user_id,status,verification_level) VALUES ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111','provisional','self_declared');
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT child_id <> 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'::uuid FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
RESET ROLE; SELECT count(*) FROM public.children WHERE display_name='Synthetic child'; ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-2:], ['t', '2'])

    def test_child_journey_retry_acknowledge_and_next_profile(self):
        result = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT count(*) FROM public.app_current_child_creation();
CREATE TEMP TABLE first_result AS SELECT * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
CREATE TEMP TABLE retry_result AS SELECT * FROM public.app_begin_child_creation(' Synthetic child ',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT (SELECT intent_id FROM first_result)=(SELECT intent_id FROM retry_result)
 AND (SELECT child_id FROM first_result)=(SELECT child_id FROM retry_result);
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Different child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'changed initial request allowed'; EXCEPTION WHEN unique_violation THEN NULL; END; END $$;
SELECT public.app_ack_child_creation((SELECT intent_id FROM first_result));
CREATE TEMP TABLE next_result AS SELECT * FROM public.app_begin_child_creation('Synthetic child',(SELECT intent_id FROM first_result),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
CREATE TEMP TABLE next_retry AS SELECT * FROM public.app_begin_child_creation('Synthetic child',(SELECT intent_id FROM first_result),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
SELECT (SELECT child_id FROM first_result)<>(SELECT child_id FROM next_result)
 AND (SELECT intent_id FROM next_result)=(SELECT intent_id FROM next_retry);
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'stale initial request allowed'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
RESET ROLE; SELECT count(*) FROM public.children WHERE display_name='Synthetic child'; ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-5:], ['0', 't', 't', 't', '2'])

    def test_child_journey_is_scoped_to_current_actor(self):
        result = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved AS SELECT * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
SELECT count(*) FROM public.app_current_child_creation();
DO $$ BEGIN BEGIN PERFORM public.app_ack_child_creation((SELECT intent_id FROM saved)); RAISE EXCEPTION 'other actor acknowledged'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic child',(SELECT intent_id FROM saved),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb'); RAISE EXCEPTION 'other actor used token'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
SELECT 'denied'; ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-2:], ['0', 'denied'])

    def test_child_journey_denies_read_and_retry_after_guardian_revocation(self):
        result = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved AS SELECT * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
RESET ROLE; UPDATE public.guardianships SET status='revoked' WHERE child_id=(SELECT child_id FROM saved);
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN PERFORM * FROM public.app_current_child_creation(); RAISE EXCEPTION 'revoked status allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Different',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'revoked retry allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
DO $$ BEGIN BEGIN PERFORM public.app_ack_child_creation((SELECT intent_id FROM saved)); RAISE EXCEPTION 'revoked acknowledgement allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT 'denied'; ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-1], 'denied')

    def test_child_journey_rolls_back_if_guardian_insert_fails(self):
        result = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
CREATE FUNCTION public.test_child_journey_reject_guardian() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic guardian failure'; END $$;
CREATE TRIGGER test_child_journey_reject_guardian BEFORE INSERT ON public.guardianships FOR EACH ROW EXECUTE FUNCTION public.test_child_journey_reject_guardian();
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic failure child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'expected failure missing'; EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'synthetic guardian failure' THEN RAISE; END IF; END; END $$;
RESET ROLE; SELECT (SELECT count(*) FROM public.children WHERE display_name='Synthetic failure child') || ':' || (SELECT count(*) FROM public.child_creation_intents); ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-1], '0:0')

    def test_child_journey_rolls_back_if_intent_write_fails(self):
        result = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
CREATE FUNCTION public.test_child_journey_reject_intent() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic intent failure'; END $$;
CREATE TRIGGER test_child_journey_reject_intent BEFORE INSERT OR UPDATE ON public.child_creation_intents FOR EACH ROW EXECUTE FUNCTION public.test_child_journey_reject_intent();
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic intent child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); RAISE EXCEPTION 'expected failure missing'; EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'synthetic intent failure' THEN RAISE; END IF; END; END $$;
RESET ROLE; SELECT (SELECT count(*) FROM public.children WHERE display_name='Synthetic intent child') || ':' || (SELECT count(*) FROM public.child_creation_intents);
DROP TRIGGER test_child_journey_reject_intent ON public.child_creation_intents;
SET LOCAL ROLE authenticated;
CREATE TEMP TABLE saved AS SELECT * FROM public.app_begin_child_creation('Synthetic intent child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM saved));
RESET ROLE; CREATE TRIGGER test_child_journey_reject_intent BEFORE INSERT OR UPDATE ON public.child_creation_intents FOR EACH ROW EXECUTE FUNCTION public.test_child_journey_reject_intent();
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic intent child',(SELECT intent_id FROM saved),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb'); RAISE EXCEPTION 'expected failure missing'; EXCEPTION WHEN raise_exception THEN IF SQLERRM <> 'synthetic intent failure' THEN RAISE; END IF; END; END $$;
SELECT intent_id=(SELECT intent_id FROM saved) FROM public.app_current_child_creation();
RESET ROLE; SELECT count(*) FROM public.children WHERE display_name='Synthetic intent child'; ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-4:], ['0:0', 't', 't', '1'])

    def run_child_journey_begin_race(self, changed, next_generation, rollback_first=False, changed_token=False):
        actor = '11111111-1111-4111-8111-111111111111'
        name = 'Synthetic child race '+uuid.uuid4().hex
        first_name, second_name = 'journey_first_'+uuid.uuid4().hex, 'journey_second_'+uuid.uuid4().hex
        self.addCleanup(query, f"BEGIN; DELETE FROM public.child_creation_intents WHERE actor_id='{actor}' AND display_name='{name}'; DELETE FROM public.guardianships WHERE child_id IN (SELECT id FROM public.children WHERE created_by='{actor}' AND display_name='{name}'); DELETE FROM public.children WHERE created_by='{actor}' AND display_name='{name}'; UPDATE public.child_creation_controls SET enabled=false WHERE id=true; COMMIT;")
        query("UPDATE public.child_creation_controls SET enabled=true WHERE id=true;")
        prior = 'NULL'
        request_id, initial_request_id = str(uuid.uuid4()), str(uuid.uuid4())
        if next_generation:
            response = query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); SELECT 'INTENT:' || intent_id FROM public.app_begin_child_creation('{name}',NULL,'{initial_request_id}'); COMMIT;")
            prior_id = next(line.removeprefix('INTENT:') for line in response.splitlines() if line.startswith('INTENT:'))
            query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); SELECT public.app_ack_child_creation('{prior_id}'); COMMIT;")
            prior = f"'{prior_id}'"
        first = second = None
        try:
            first = start_psql_session(); second = start_psql_session()
            for process, label in ((first, first_name), (second, second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{label}',false); SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true);\n")
            first.stdin.write(f"SELECT 'FIRST:' || disposition FROM public.app_begin_child_creation('{name}',{prior},'{request_id}'); SELECT 'FIRST_READY';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST:created')); self.assertTrue(wait_for_session_marker(first, 'FIRST_READY'))
            second_name_value = name+' changed' if changed else name
            second_request_id = str(uuid.uuid4()) if changed_token else request_id
            second.stdin.write(f"SELECT 'SECOND:' || disposition FROM public.app_begin_child_creation('{second_name_value}',{prior},'{second_request_id}'); COMMIT; SELECT 'SECOND_DONE';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write(("ROLLBACK" if rollback_first else "COMMIT") + "; SELECT 'FIRST_DONE';\n"); first.stdin.flush(); self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            if changed or changed_token:
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0); self.assertIn('Resolve the existing child profile first', errors)
            else:
                self.assertTrue(wait_for_session_marker(second, 'SECOND:created' if rollback_first else 'SECOND:existing')); self.assertTrue(wait_for_session_marker(second, 'SECOND_DONE'))
            expected = '2' if next_generation else '1'
            self.assertEqual(query(f"SELECT count(*) FROM public.children WHERE created_by='{actor}' AND display_name='{name}';"), expected)
        finally:
            if second is not None: close_psql_session(second)
            if first is not None: close_psql_session(first)

    def test_child_journey_concurrent_same_initial_request(self):
        self.run_child_journey_begin_race(False, False)

    def test_child_journey_concurrent_changed_initial_request(self):
        self.run_child_journey_begin_race(True, False)

    def test_child_journey_retry_creates_after_first_transaction_rolls_back(self):
        self.run_child_journey_begin_race(False, False, True)

    def test_child_journey_concurrent_same_next_request(self):
        self.run_child_journey_begin_race(False, True)

    def test_child_journey_concurrent_changed_next_request(self):
        self.run_child_journey_begin_race(True, True)

    def test_child_journey_concurrent_different_initial_token(self):
        self.run_child_journey_begin_race(False, False, changed_token=True)

    def test_child_journey_concurrent_different_next_token(self):
        self.run_child_journey_begin_race(False, True, changed_token=True)

    def test_child_journey_rejects_stale_prior_after_multiple_profiles(self):
        result = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE first_result AS SELECT * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.app_ack_child_creation((SELECT intent_id FROM first_result));
CREATE TEMP TABLE second_result AS SELECT * FROM public.app_begin_child_creation('Synthetic child',(SELECT intent_id FROM first_result),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
SELECT public.app_ack_child_creation((SELECT intent_id FROM second_result));
CREATE TEMP TABLE third_result AS SELECT * FROM public.app_begin_child_creation('Synthetic child',(SELECT intent_id FROM second_result),'cccccccc-3333-4333-8333-cccccccccccc');
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic child',(SELECT intent_id FROM first_result),'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb'); RAISE EXCEPTION 'stale prior accepted'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END; END $$;
RESET ROLE; SELECT count(*) FROM public.children WHERE display_name='Synthetic child'; ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-1], '3')

    def run_child_journey_access_race(self, change_first, target):
        actor = '11111111-1111-4111-8111-111111111111'
        name = 'Synthetic child access '+uuid.uuid4().hex
        first_name, second_name = 'journey_access_first_'+uuid.uuid4().hex, 'journey_access_second_'+uuid.uuid4().hex
        self.addCleanup(query, f"BEGIN; DELETE FROM public.child_creation_intents WHERE actor_id='{actor}' AND display_name='{name}'; DELETE FROM public.guardianships WHERE child_id IN (SELECT id FROM public.children WHERE created_by='{actor}' AND display_name='{name}'); DELETE FROM public.children WHERE created_by='{actor}' AND display_name='{name}'; UPDATE public.child_creation_controls SET enabled=false WHERE id=true; COMMIT;")
        query("UPDATE public.child_creation_controls SET enabled=true WHERE id=true;")
        response = query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); SELECT 'CHILD:' || child_id FROM public.app_begin_child_creation('{name}',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'); COMMIT;")
        child = next(line.removeprefix('CHILD:') for line in response.splitlines() if line.startswith('CHILD:'))
        first = second = None
        read = f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); SELECT 'ROWS:' || count(*) FROM public.app_current_child_creation();\n"
        change = (f"UPDATE public.guardianships SET status='revoked' WHERE child_id='{child}';\n" if target == 'guardian' else "UPDATE public.child_creation_controls SET enabled=false WHERE id=true;\n")
        try:
            first = start_psql_session(); second = start_psql_session()
            for process, label in ((first, first_name), (second, second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{label}',false);\n")
            first.stdin.write(change if change_first else read); first.stdin.write("SELECT 'FIRST_READY';\n"); first.stdin.flush()
            if not change_first: self.assertTrue(wait_for_session_marker(first, 'ROWS:1'))
            self.assertTrue(wait_for_session_marker(first, 'FIRST_READY'))
            second.stdin.write(read if change_first else change); second.stdin.write("COMMIT; SELECT 'SECOND_DONE';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_DONE';\n"); first.stdin.flush(); self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            if change_first:
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0); self.assertIn('Child creation unavailable', errors)
            else:
                self.assertTrue(wait_for_session_marker(second, 'SECOND_DONE'))
        finally:
            if second is not None: close_psql_session(second)
            if first is not None: close_psql_session(first)

    def test_child_journey_status_after_guardian_revocation(self):
        self.run_child_journey_access_race(True, 'guardian')

    def test_child_journey_status_before_guardian_revocation(self):
        self.run_child_journey_access_race(False, 'guardian')

    def test_child_journey_status_after_control_disabled(self):
        self.run_child_journey_access_race(True, 'control')

    def test_child_journey_status_before_control_disabled(self):
        self.run_child_journey_access_race(False, 'control')

    def test_child_journey_recovers_exact_status_across_transactions(self):
        actor = '11111111-1111-4111-8111-111111111111'
        name = 'Synthetic recovery '+uuid.uuid4().hex
        self.addCleanup(query, f"BEGIN; DELETE FROM public.child_creation_intents WHERE actor_id='{actor}' AND display_name='{name}'; DELETE FROM public.guardianships WHERE child_id IN (SELECT id FROM public.children WHERE created_by='{actor}' AND display_name='{name}'); DELETE FROM public.children WHERE created_by='{actor}' AND display_name='{name}'; UPDATE public.child_creation_controls SET enabled=false WHERE id=true; COMMIT;")
        query("UPDATE public.child_creation_controls SET enabled=true WHERE id=true;")
        def as_actor(statement):
            return query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true); {statement} COMMIT;")
        first = as_actor(f"SELECT 'RESULT:' || intent_id || '|' || child_id FROM public.app_begin_child_creation('{name}',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');")
        first_ids = next(line.removeprefix('RESULT:') for line in first.splitlines() if line.startswith('RESULT:'))
        first_intent, first_child = first_ids.split('|')
        current = as_actor("SELECT 'STATUS:' || intent_id || '|' || child_id || '|' || display_name || '|' || acknowledged::text || '|' || coalesce(prior_intent_id::text,'initial') || '|' || request_id FROM public.app_current_child_creation();")
        self.assertIn(f'STATUS:{first_intent}|{first_child}|{name}|false|initial|aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa', current.splitlines())
        as_actor(f"SELECT public.app_ack_child_creation('{first_intent}');")
        current = as_actor("SELECT 'STATUS:' || intent_id || '|' || child_id || '|' || display_name || '|' || acknowledged::text || '|' || coalesce(prior_intent_id::text,'initial') || '|' || request_id FROM public.app_current_child_creation();")
        self.assertIn(f'STATUS:{first_intent}|{first_child}|{name}|true|initial|aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa', current.splitlines())
        second = as_actor(f"SELECT 'RESULT:' || intent_id || '|' || child_id FROM public.app_begin_child_creation('{name}','{first_intent}','bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');")
        second_ids = next(line.removeprefix('RESULT:') for line in second.splitlines() if line.startswith('RESULT:'))
        second_intent, second_child = second_ids.split('|')
        self.assertNotEqual(first_intent, second_intent); self.assertNotEqual(first_child, second_child)
        current = as_actor("SELECT 'STATUS:' || intent_id || '|' || child_id || '|' || display_name || '|' || acknowledged::text || '|' || coalesce(prior_intent_id::text,'initial') || '|' || request_id FROM public.app_current_child_creation();")
        self.assertIn(f'STATUS:{second_intent}|{second_child}|{name}|false|{first_intent}|bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb', current.splitlines())

    def test_child_journey_distinguishes_competing_request_tokens(self):
        result = run_sql("""
BEGIN; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved AS SELECT * FROM public.app_begin_child_creation('Synthetic child',NULL,'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
DO $$ BEGIN BEGIN PERFORM * FROM public.app_begin_child_creation('Synthetic child',NULL,'bbbbbbbb-1111-4111-8111-bbbbbbbbbbbb'); RAISE EXCEPTION 'different request adopted'; EXCEPTION WHEN unique_violation THEN NULL; END; END $$;
SELECT request_id FROM public.app_current_child_creation(); ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-1], 'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa')
