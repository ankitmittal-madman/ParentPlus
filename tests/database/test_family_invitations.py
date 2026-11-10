"""Real PostgreSQL family invitation and academy connection contracts."""
import unittest
from tests.database.test_authorization import run_sql
from tests.database.test_scheduling_foundation import SETUP

A='11111111-1111-4111-8111-111111111111'
B='22222222-2222-4222-8222-222222222222'
W='a0000000-0000-4000-8000-000000000001'
C='d0000000-0000-4000-8000-000000000001'
R='e0000000-0000-4000-8000-000000000001'
TOKEN='ab'*32
BASE=SETUP+f"""
UPDATE public.workspace_memberships SET role='owner';
INSERT INTO public.children(id,display_name,created_by) VALUES('{C}','Fictional Child','{B}');
INSERT INTO public.guardianships(child_id,guardian_user_id) VALUES('{C}','{B}');
SELECT set_config('request.jwt.claim.sub','{A}',true); SET ROLE authenticated;
"""
ISSUE=f"SELECT * FROM public.app_issue_family_invite('{W}','{R}','{TOKEN}');\n"
ACCEPT=f"SELECT public.app_accept_family_invite('{TOKEN}','{C}');\n"
PARENT=f"SELECT set_config('request.jwt.claim.sub','{B}',true);\n"

def denied(sql, error='insufficient_privilege'):
    return f"DO $$ DECLARE observed boolean:=false; BEGIN BEGIN {sql} EXCEPTION WHEN {error} THEN observed:=true; END; IF NOT observed THEN RAISE EXCEPTION 'unexpected success'; END IF; END $$;\n"

class FamilyInvitationTests(unittest.TestCase):
    def test_issue_retry_is_payload_bound_and_hash_only(self):
        out=run_sql(BASE+ISSUE+ISSUE+denied(f"PERFORM * FROM public.app_issue_family_invite('{W}','{R}','{'cd'*32}');",'unique_violation')+"RESET ROLE; SELECT count(*) || ':' || bool_and(length(token_hash)=64 AND token_hash <> '"+TOKEN+"') FROM public.family_invites; ROLLBACK;")
        self.assertEqual(out.splitlines()[-1],'1:true')
    def test_accept_is_atomic_idempotent_and_separate_from_enrolment(self):
        out=run_sql(BASE+ISSUE+PARENT+ACCEPT+ACCEPT+f"SELECT count(*) FROM public.app_child_academies('{C}'); RESET ROLE; SELECT (SELECT count(*) FROM public.workspace_children) || ':' || (SELECT count(*) FROM public.connection_requests) || ':' || (SELECT count(*) FROM public.connection_events); ROLLBACK;")
        self.assertEqual(out.splitlines()[-2:],['1','1:1:1'])
    def test_fake_expired_and_wrong_child_are_refused(self):
        out=run_sql(BASE+ISSUE+PARENT+denied(f"PERFORM public.app_accept_family_invite('{'cc'*32}','{C}');")+denied(f"PERFORM public.app_accept_family_invite('{TOKEN}','{W}');")+f"RESET ROLE; UPDATE public.family_invites SET expires_at=clock_timestamp()-interval '1 second'; SET ROLE authenticated;"+denied(f"PERFORM public.app_accept_family_invite('{TOKEN}','{C}');")+"RESET ROLE; SELECT count(*) FROM public.workspace_children; ROLLBACK;")
        self.assertEqual(out.splitlines()[-1],'0')
    def test_used_invite_cannot_be_claimed_by_other_actor_or_child(self):
        out=run_sql(BASE+ISSUE+PARENT+ACCEPT+f"SELECT set_config('request.jwt.claim.sub','{A}',true);"+denied(f"PERFORM public.app_accept_family_invite('{TOKEN}','{C}');")+PARENT+denied(f"PERFORM public.app_accept_family_invite('{TOKEN}','{W}');")+"SELECT 'denied'; ROLLBACK;")
        self.assertEqual(out.splitlines()[-1],'denied')
    def test_issuer_workspace_and_guardian_revocations_are_respected(self):
        for mutation in [f"UPDATE public.workspace_memberships SET status='suspended' WHERE user_id='{A}'",f"UPDATE public.workspaces SET status='suspended' WHERE id='{W}'","UPDATE public.guardianships SET status='revoked'"]:
            with self.subTest(mutation=mutation):
                out=run_sql(BASE+ISSUE+f"RESET ROLE; {mutation}; SET ROLE authenticated;"+PARENT+denied(f"PERFORM public.app_accept_family_invite('{TOKEN}','{C}');")+"RESET ROLE; SELECT count(*) FROM public.workspace_children; ROLLBACK;")
                self.assertEqual(out.splitlines()[-1],'0')
    def test_restricted_relationship_is_never_reactivated(self):
        out=run_sql(BASE+ISSUE+f"RESET ROLE; INSERT INTO public.workspace_children(workspace_id,child_id,status) VALUES('{W}','{C}','restricted'); SET ROLE authenticated;"+PARENT+denied(f"PERFORM public.app_accept_family_invite('{TOKEN}','{C}');")+"RESET ROLE; SELECT status FROM public.workspace_children; ROLLBACK;")
        self.assertEqual(out.splitlines()[-1],'restricted')
    def test_direct_and_anonymous_access_denied_and_legacy_grants_unchanged(self):
        out=run_sql("SELECT NOT has_table_privilege('authenticated','public.family_invites','SELECT') AND NOT has_function_privilege('anon','public.app_preview_family_invite(text)','EXECUTE') AND NOT has_function_privilege('authenticated','public.approve_guardian_connection(uuid)','EXECUTE');")
        self.assertEqual(out,'t')
    def test_roster_and_parent_connections_are_scoped(self):
        out=run_sql(BASE+ISSUE+PARENT+ACCEPT+denied(f"PERFORM * FROM public.app_family_roster('{W}',NULL);")+f"SELECT set_config('request.jwt.claim.sub','{A}',true); SELECT child_name FROM public.app_family_roster('{W}',NULL);"+denied(f"PERFORM * FROM public.app_child_academies('{C}');")+f"SELECT count(*) FROM public.app_family_roster('{W}','ffffffff-ffff-4fff-8fff-ffffffffffff'); ROLLBACK;")
        self.assertEqual(out.splitlines()[-2:],['Fictional Child','0'])
    def test_accept_failure_rolls_back_invite_and_connection(self):
        out=run_sql(BASE+ISSUE+"RESET ROLE; CREATE FUNCTION pg_temp.fail_family() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic family failure'; END $$; CREATE TRIGGER fail_family BEFORE INSERT ON public.connection_events FOR EACH ROW EXECUTE FUNCTION pg_temp.fail_family(); SET ROLE authenticated;"+PARENT+denied(f"PERFORM public.app_accept_family_invite('{TOKEN}','{C}');",'raise_exception')+"RESET ROLE; SELECT (SELECT count(*) FROM public.workspace_children) || ':' || (SELECT count(*) FROM public.connection_requests) || ':' || (SELECT count(*) FROM public.family_invites WHERE accepted_by IS NOT NULL); ROLLBACK;")
        self.assertEqual(out.splitlines()[-1],'0:0:0')
    def test_normal_coach_and_wrong_workspace_cannot_issue(self):
        out=run_sql(BASE+"RESET ROLE; UPDATE public.workspace_memberships SET role='coach'; SET ROLE authenticated;"+denied(f"PERFORM * FROM public.app_issue_family_invite('{W}','{R}','{TOKEN}');")+"SELECT 'denied'; ROLLBACK;")
        self.assertEqual(out.splitlines()[-1],'denied')
    def test_malformed_tokens_are_rejected(self):
        out=run_sql(BASE+denied(f"PERFORM * FROM public.app_issue_family_invite('{W}','{R}','short');",'invalid_parameter_value')+"SELECT 'denied'; ROLLBACK;")
        self.assertEqual(out.splitlines()[-1],'denied')
    def test_preview_contains_academy_only_and_used_state(self):
        out=run_sql(BASE+ISSUE+PARENT+f"SELECT academy_name || ':' || state FROM public.app_preview_family_invite('{TOKEN}');"+ACCEPT+f"SELECT state FROM public.app_preview_family_invite('{TOKEN}'); ROLLBACK;")
        self.assertIn('Academy A:pending',out.splitlines())
        self.assertEqual(out.splitlines()[-1],'accepted')

    def test_roster_paginates_more_than_fifty_saved_connections(self):
        out=run_sql(BASE+f"""
RESET ROLE;
INSERT INTO public.children(id,display_name,created_by)
 SELECT md5('family-child-'||g)::uuid,'Fictional '||g,'{B}'::uuid FROM generate_series(1,51) g;
INSERT INTO public.workspace_children(id,workspace_id,child_id)
 SELECT md5('family-connection-'||g)::uuid,'{W}'::uuid,md5('family-child-'||g)::uuid FROM generate_series(1,51) g;
SET ROLE authenticated;
CREATE TEMP TABLE page_one AS SELECT * FROM public.app_family_roster('{W}',NULL);
SELECT count(*) FROM page_one;
SELECT count(*) FROM public.app_family_roster('{W}',(SELECT relationship_id FROM page_one ORDER BY relationship_id DESC LIMIT 1));
ROLLBACK;
""")
        self.assertEqual(out.splitlines()[-2:],['50','1'])

class FamilyInvitationRaceTests(unittest.TestCase):
    def race(self, kind, accept_first):
        import uuid
        from tests.database.test_concurrent_authorization import query,start_psql_session,wait_for_session_marker,wait_for_blocking_relationship,close_psql_session
        w,c,r,r2=[str(uuid.uuid4()) for _ in range(4)]
        token2=uuid.uuid4().hex+uuid.uuid4().hex
        token=uuid.uuid4().hex+uuid.uuid4().hex
        first=second=None
        mutation={
          'workspace':f"UPDATE public.workspaces SET status='suspended' WHERE id='{w}';",
          'issuer':f"UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id='{w}';",
          'guardian':f"UPDATE public.guardianships SET status='revoked' WHERE child_id='{c}';",
          'restriction':f"UPDATE public.workspace_children SET status='restricted' WHERE workspace_id='{w}' AND child_id='{c}';",
          'other-invite':f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{B}',true); SELECT public.app_accept_family_invite('{token2}','{c}');",
          'expiry-workspace':f"SELECT id FROM public.workspaces WHERE id='{w}' FOR UPDATE;",
          'expiry-relationship':f"SELECT id FROM public.workspace_children WHERE workspace_id='{w}' AND child_id='{c}' FOR UPDATE;",
          'expiry-invite':f"SELECT id FROM public.family_invites WHERE id='{r}' FOR UPDATE;",
          'expiry':f"SELECT pg_advisory_xact_lock(hashtextextended('{w}'||':'||'{c}',0));",
          'retry':f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{B}',true); SELECT public.app_accept_family_invite('{token}','{c}');"
        }[kind]
        acceptance=f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{B}',true); SELECT public.app_accept_family_invite('{token}','{c}');"
        try:
            query(f"""BEGIN;
INSERT INTO public.workspaces(id,name,type,created_by,creation_request_id) VALUES('{w}','Race Academy','academy','{A}',gen_random_uuid());
INSERT INTO public.workspace_memberships(workspace_id,user_id,role,status) VALUES('{w}','{A}','owner','active');
INSERT INTO public.children(id,display_name,created_by) VALUES('{c}','Race Child','{B}');
INSERT INTO public.guardianships(child_id,guardian_user_id) VALUES('{c}','{B}');
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{A}',true);
SELECT * FROM public.app_issue_family_invite('{w}','{r}','{token}'); RESET ROLE;
""" + (f"INSERT INTO public.workspace_children(workspace_id,child_id) VALUES('{w}','{c}');" if kind in ('restriction','expiry-relationship') else '') + (f"UPDATE public.family_invites SET expires_at=clock_timestamp()+interval '1 second' WHERE id='{r}';" if kind.startswith('expiry') else '') + (f"SET LOCAL ROLE authenticated; SELECT * FROM public.app_issue_family_invite('{w}','{r2}','{token2}'); RESET ROLE;" if kind=='other-invite' else '') + "COMMIT;")
            # committed synthetic records only; never touches a hosted database.
            n1='family_first_'+uuid.uuid4().hex;n2='family_second_'+uuid.uuid4().hex
            first=start_psql_session();first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{n1}',false);"+(acceptance if accept_first else mutation)+"SELECT 'FIRST_LOCKED';\n");first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second=start_psql_session();second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{n2}',false);"+(mutation if accept_first else acceptance)+"COMMIT;\n");second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(n2,n1),'Expected actual PostgreSQL blocking')
            if kind.startswith('expiry'):query("SELECT pg_sleep(1.1);")
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n");first.stdin.flush();self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            second.stdin.close();second.stdin=None;_,errors=second.communicate(timeout=15)
            self.assertEqual(second.returncode,0 if accept_first or kind=='retry' else 3,errors)
            self.assertEqual(query(f"SELECT (SELECT count(*) FROM public.workspace_children WHERE workspace_id='{w}') || ':' || (SELECT count(*) FROM public.connection_events WHERE connection_request_id='{r}');").splitlines()[-1],'1:1' if accept_first or kind=='retry' else ('1:0' if kind in ('restriction','expiry-relationship') else '0:0'))
            if kind=='other-invite':
                self.assertEqual(query(f"SELECT count(*) FROM public.family_invites WHERE workspace_id='{w}' AND accepted_by IS NOT NULL;").splitlines()[-1],'2')
        finally:
            for process in (first,second):
                if process:close_psql_session(process)
            query(f"""BEGIN; DELETE FROM public.family_invites WHERE workspace_id='{w}';
DELETE FROM public.connection_events WHERE connection_request_id IN (SELECT id FROM public.connection_requests WHERE workspace_id='{w}'); DELETE FROM public.connection_requests WHERE workspace_id='{w}';
DELETE FROM public.workspace_children WHERE workspace_id='{w}'; DELETE FROM public.guardianships WHERE child_id='{c}'; DELETE FROM public.children WHERE id='{c}';
DELETE FROM public.workspace_memberships WHERE workspace_id='{w}'; DELETE FROM public.workspace_creation_receipts WHERE workspace_id='{w}'; DELETE FROM public.workspaces WHERE id='{w}'; COMMIT;""")
            self.assertEqual(query(f"SELECT count(*) FROM public.workspace_creation_receipts WHERE workspace_id='{w}';").splitlines()[-1],'0','Race fixture must clean its workspace tombstone receipt')
    def test_revocation_commits_before_acceptance(self):
        for kind in ['workspace','issuer','guardian','restriction']:
            with self.subTest(kind=kind):self.race(kind,False)
    def test_acceptance_commits_before_revocation(self):
        for kind in ['workspace','issuer','guardian','restriction']:
            with self.subTest(kind=kind):self.race(kind,True)
    def test_concurrent_acceptance_retries_write_one_relationship_and_event(self):
        self.race('retry',True)

    def test_expiry_is_rechecked_after_relationship_advisory_lock_wait(self):
        for kind in ['expiry','expiry-workspace','expiry-relationship','expiry-invite']:
            with self.subTest(kind=kind):self.race(kind,False)

    def test_different_invitations_for_same_child_serialize_one_relationship(self):
        self.race('other-invite',True)
