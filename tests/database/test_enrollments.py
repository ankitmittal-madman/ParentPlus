"""Enrolment RPC contracts on isolated, synthetic PostgreSQL records."""
import unittest
import uuid

from tests.database.test_authorization import run_sql
from tests.database.test_family_invitations import denied
from tests.database.test_scheduling_foundation import SETUP

A = '11111111-1111-4111-8111-111111111111'
B = '22222222-2222-4222-8222-222222222222'
D = '33333333-3333-4333-8333-333333333333'
W = 'a0000000-0000-4000-8000-000000000001'
W2 = 'a0000000-0000-4000-8000-000000000002'
C = 'd0000000-0000-4000-8000-000000000001'
T = 'e0000000-0000-4000-8000-000000000001'
T2 = 'e0000000-0000-4000-8000-000000000002'
R = 'f0000000-0000-4000-8000-000000000001'
R2 = 'f0000000-0000-4000-8000-000000000002'
BASE = SETUP + f"""
UPDATE public.workspace_memberships SET role='owner';
INSERT INTO public.batches(id,workspace_id,course_id,name) VALUES
 ('{T}','{W}','c0000000-0000-4000-8000-000000000001','Morning'),
 ('{T2}','{W}','c0000000-0000-4000-8000-000000000001','Evening');
INSERT INTO public.children(id,display_name,created_by) VALUES('{C}','Fictional Child','{B}');
INSERT INTO public.guardianships(child_id,guardian_user_id) VALUES('{C}','{B}');
INSERT INTO public.workspace_children(workspace_id,child_id) VALUES('{W}','{C}');
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{A}',true);
"""
SAVE = f"SELECT * FROM public.app_save_enrollment('{W}','{T}','{C}','{R}');\n"
SAVED = f"CREATE TEMP TABLE saved AS SELECT * FROM public.app_save_enrollment('{W}','{T}','{C}','{R}');\n"


def change(status='paused', version=1, reason="'temporary_break'", request=R2):
    return f"SELECT * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'{status}',{version},{reason},'{request}');\n"


class EnrollmentTests(unittest.TestCase):
    def check_sql(self, sql, expected):
        out = run_sql(BASE + sql + '\nROLLBACK;')
        self.assertEqual(out.splitlines()[-len(expected):], expected)

    def test_connection_does_not_auto_enroll_and_manager_metadata_is_scoped(self):
        self.check_sql(f"SELECT batch_name || ':' || course_name FROM public.app_enrollment_batches('{W}') ORDER BY batch_name; SELECT child_name FROM public.app_enrollment_candidates('{W}'); SELECT count(*) FROM public.app_batch_enrollments('{W}','{T}');", ['Evening:Music','Morning:Music','Fictional Child','0'])

    def test_save_retry_and_new_request_share_one_enrollment_and_event(self):
        self.check_sql(SAVED + SAVE + f"SELECT * FROM public.app_save_enrollment('{W}','{T}','{C}','{R2}'); RESET ROLE; SELECT (SELECT count(*) FROM public.enrollments) || ':' || (SELECT count(*) FROM public.enrollment_events) || ':' || (SELECT count(*) FROM public.enrollment_request_receipts);", ['1:1:2'])

    def test_save_is_visible_to_manager_and_eligible_parent(self):
        self.check_sql(SAVED + f"SELECT child_name || ':' || status || ':' || version FROM public.app_batch_enrollments('{W}','{T}'); SELECT set_config('request.jwt.claim.sub','{B}',true); SELECT academy_name || ':' || batch_name || ':' || course_name || ':' || status || ':' || version FROM public.app_parent_enrollments('{C}');", ['Fictional Child:active:1',B,'Academy A:Morning:Music:active:1'])

    def test_pause_resume_complete_increment_versions_and_events(self):
        self.check_sql(SAVED + change() + change('active',2,'NULL',str(uuid.uuid4())) + change('completed',3,'NULL',str(uuid.uuid4())) + "RESET ROLE; SELECT status || ':' || version FROM public.enrollments; SELECT count(*) FROM public.enrollment_events;", ['completed:4','4'])

    def test_withdrawal_requires_enum_and_terminal_state_cannot_reopen(self):
        self.check_sql(SAVED + change('withdrawn',1,"'schedule_change'") + denied("PERFORM * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'active',2,NULL,gen_random_uuid());",'invalid_parameter_value') + "RESET ROLE; SELECT status || ':' || version FROM public.enrollments;", ['withdrawn:2'])

    def test_paused_enrollment_can_complete_or_withdraw(self):
        for target,reason in [('completed','NULL'),('withdrawn',"'other'")]:
            with self.subTest(target=target):
                self.check_sql(SAVED+change()+change(target,2,reason,str(uuid.uuid4()))+"RESET ROLE; SELECT status || ':' || version FROM public.enrollments;",[target+':3'])

    def test_save_does_not_silently_resume_or_reopen(self):
        for state in ['paused','completed','withdrawn','pending','cancelled']:
            with self.subTest(state=state):
                self.check_sql(SAVED + f"RESET ROLE; UPDATE public.enrollments SET status='{state}'; SET ROLE authenticated;" + denied(f"PERFORM * FROM public.app_save_enrollment('{W}','{T}','{C}','{R2}');",'unique_violation') + "RESET ROLE; SELECT count(*) FROM public.enrollment_events;",['1'])

    def test_original_receipts_return_original_result_after_later_changes(self):
        self.check_sql(SAVED+change()+change('active',2,'NULL',str(uuid.uuid4()))+f"SELECT status || ':' || version FROM public.app_save_enrollment('{W}','{T}','{C}','{R}'); SELECT status || ':' || version FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'paused',1,'temporary_break','{R2}'); SELECT status || ':' || version FROM public.app_batch_enrollments('{W}','{T}');",['active:1','paused:2','active:3'])

    def test_old_save_and_change_receipts_do_not_reopen_terminal_enrollment(self):
        self.check_sql(SAVED+change()+change('withdrawn',2,"'other'",str(uuid.uuid4()))+SAVE+change()+"RESET ROLE; SELECT status || ':' || version FROM public.enrollments; SELECT count(*) FROM public.enrollment_events;",['withdrawn:3','3'])

    def test_stale_version_cannot_overwrite_newer_status(self):
        self.check_sql(SAVED+change()+denied("PERFORM * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'completed',1,NULL,gen_random_uuid());",'serialization_failure')+"RESET ROLE; SELECT status || ':' || version FROM public.enrollments; SELECT count(*) FROM public.enrollment_events;",['paused:2','2'])

    def test_invalid_status_reason_and_version_leave_no_receipt(self):
        cases=[('pending',1,'NULL'),('cancelled',1,'NULL'),('active',1,'NULL'),('paused',1,'NULL'),('paused',1,"'private note'"),('completed',1,"'other'"),('withdrawn',1,'NULL'),('paused',0,"'other'"),('paused','NULL',"'other'"),('NULL',1,'NULL')]
        for state,version,reason in cases:
            with self.subTest(state=state,version=version,reason=reason):
                sqlstate='NULL' if state=='NULL' else "'"+state+"'"
                self.check_sql(SAVED+denied(f"PERFORM * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),{sqlstate},{version},{reason},gen_random_uuid());",'invalid_parameter_value')+"RESET ROLE; SELECT (SELECT count(*) FROM public.enrollment_request_receipts) || ':' || (SELECT count(*) FROM public.enrollment_events);",['1:1'])

    def test_request_uuid_binds_entire_save_payload(self):
        self.check_sql(SAVED+denied(f"PERFORM * FROM public.app_save_enrollment('{W}','{T2}','{C}','{R}');",'unique_violation')+"RESET ROLE; SELECT count(*) FROM public.enrollments;",['1'])

    def test_request_uuid_binds_change_payload_and_operation(self):
        for call in [f"PERFORM * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'completed',1,NULL,'{R2}');",f"PERFORM * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'paused',2,'temporary_break','{R2}');",f"PERFORM * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'paused',1,'other','{R2}');",f"PERFORM * FROM public.app_save_enrollment('{W}','{T}','{C}','{R2}');"]:
            with self.subTest(call=call):
                self.check_sql(SAVED+change()+denied(call,'unique_violation')+"RESET ROLE; SELECT count(*) FROM public.enrollment_events;",['2'])

    def test_request_uuid_cannot_be_reused_by_another_manager(self):
        self.check_sql(SAVED+f"RESET ROLE; INSERT INTO public.workspace_memberships(workspace_id,user_id,role,status) VALUES('{W}','{D}','admin','active'); SET ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{D}',true);"+denied(f"PERFORM * FROM public.app_save_enrollment('{W}','{T}','{C}','{R}');",'unique_violation')+"SELECT 'denied';",['denied'])

    def test_missing_request_and_cross_workspace_target_are_rejected(self):
        self.check_sql(f"RESET ROLE; INSERT INTO public.workspace_memberships(workspace_id,user_id,role,status) VALUES('{W2}','{A}','admin','active'); SET ROLE authenticated;"+denied(f"PERFORM * FROM public.app_save_enrollment('{W}','{T}','{C}',NULL);",'invalid_parameter_value')+denied(f"PERFORM * FROM public.app_save_enrollment('{W2}','{T}','{C}',gen_random_uuid());")+denied(f"PERFORM * FROM public.app_save_enrollment('{W}','{T}','{T2}',gen_random_uuid());")+"RESET ROLE; SELECT count(*) FROM public.enrollments;",['0'])

    def test_null_and_missing_enrollment_change_are_rejected(self):
        self.check_sql(SAVED+denied("PERFORM * FROM public.app_change_enrollment(NULL,'completed',1,NULL,gen_random_uuid());")+denied(f"PERFORM * FROM public.app_change_enrollment('{T}','completed',1,NULL,gen_random_uuid());")+denied("PERFORM * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'completed',1,NULL,NULL);",'invalid_parameter_value')+"SELECT 'denied';",['denied'])

    def test_parent_and_coach_cannot_admit_or_change(self):
        for actor in [B,D]:
            with self.subTest(actor=actor):
                self.check_sql(SAVED+f"RESET ROLE; INSERT INTO public.workspace_memberships(workspace_id,user_id,role,status) VALUES('{W}','{D}','coach','active'); SET ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true);"+denied(f"PERFORM * FROM public.app_save_enrollment('{W}','{T2}','{C}',gen_random_uuid());")+denied("PERFORM * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'completed',1,NULL,gen_random_uuid());")+"SELECT 'denied';",['denied'])

    def test_assigned_coach_reads_only_assigned_batch_metadata_and_roster(self):
        self.check_sql(SAVED+f"RESET ROLE; INSERT INTO public.workspace_memberships(id,workspace_id,user_id,role,status) VALUES('{R2}','{W}','{D}','coach','active'); INSERT INTO public.batch_coach_assignments VALUES('{W}','{T}','{R2}'); SET ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{D}',true); SELECT batch_name FROM public.app_enrollment_batches('{W}'); SELECT child_name FROM public.app_batch_enrollments('{W}','{T}');"+denied(f"PERFORM * FROM public.app_batch_enrollments('{W}','{T2}');")+denied(f"PERFORM * FROM public.app_enrollment_candidates('{W}');")+"SELECT 'scoped';",['Morning','Fictional Child','scoped'])

    def test_admin_can_admit_and_change_without_being_owner(self):
        self.check_sql("RESET ROLE; UPDATE public.workspace_memberships SET role='admin'; SET ROLE authenticated;"+SAVED+change()+f"SELECT status || ':' || version FROM public.app_batch_enrollments('{W}','{T}');",['paused:2'])

    def test_suspended_coach_cannot_read_assigned_metadata_or_roster(self):
        self.check_sql(SAVED+f"RESET ROLE; INSERT INTO public.workspace_memberships(id,workspace_id,user_id,role,status) VALUES('{R2}','{W}','{D}','coach','suspended'); INSERT INTO public.batch_coach_assignments VALUES('{W}','{T}','{R2}'); SET ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{D}',true);"+denied(f"PERFORM * FROM public.app_enrollment_batches('{W}');")+denied(f"PERFORM * FROM public.app_batch_enrollments('{W}','{T}');")+"SELECT 'denied';",['denied'])

    def test_read_and_retry_recheck_revoked_workspace_manager_and_connection(self):
        for mutation in [f"UPDATE public.workspaces SET status='suspended' WHERE id='{W}'",f"UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id='{W}'",f"UPDATE public.workspace_memberships SET role='coach' WHERE workspace_id='{W}'",f"UPDATE public.workspace_children SET status='restricted' WHERE workspace_id='{W}'"]:
            with self.subTest(mutation=mutation):
                self.check_sql(SAVED+change()+f"RESET ROLE; {mutation}; SET ROLE authenticated;"+denied(f"PERFORM * FROM public.app_save_enrollment('{W}','{T}','{C}','{R}');")+denied(f"PERFORM * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'paused',1,'temporary_break','{R2}');")+"SELECT 'denied';",['denied'])

    def test_parent_requires_own_created_child_and_current_eligible_guardianship(self):
        for mutation in [f"UPDATE public.children SET created_by='{D}' WHERE id='{C}'",f"UPDATE public.guardianships SET status='revoked' WHERE child_id='{C}'",f"UPDATE public.guardianships SET status='disputed' WHERE child_id='{C}'",f"DELETE FROM public.guardianships WHERE child_id='{C}'"]:
            with self.subTest(mutation=mutation):
                self.check_sql(SAVED+f"RESET ROLE; {mutation}; SET ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{B}',true);"+denied(f"PERFORM * FROM public.app_parent_enrollments('{C}');")+"SELECT 'denied';",['denied'])

    def test_parent_and_roster_hide_inactive_connection(self):
        self.check_sql(SAVED+f"RESET ROLE; UPDATE public.workspace_children SET status='archived'; SET ROLE authenticated; SELECT count(*) FROM public.app_batch_enrollments('{W}','{T}'); SELECT count(*) FROM public.app_enrollment_candidates('{W}'); SELECT set_config('request.jwt.claim.sub','{B}',true); SELECT count(*) FROM public.app_parent_enrollments('{C}');",['0','0',B,'0'])

    def test_parent_hides_suspended_academy_and_other_child_data(self):
        self.check_sql(SAVED+f"RESET ROLE; UPDATE public.workspaces SET status='suspended' WHERE id='{W}'; SET ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{B}',true); SELECT count(*) FROM public.app_parent_enrollments('{C}');"+denied(f"PERFORM * FROM public.app_parent_enrollments('{T}');")+"SELECT 'scoped';",['0','scoped'])

    def test_write_event_failure_rolls_back_enrollment_and_receipt(self):
        self.check_sql("RESET ROLE; CREATE FUNCTION pg_temp.fail_enrollment() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic enrollment event failure'; END $$; CREATE TRIGGER fail_enrollment BEFORE INSERT ON public.enrollment_events FOR EACH ROW EXECUTE FUNCTION pg_temp.fail_enrollment(); SET ROLE authenticated;"+denied(f"PERFORM * FROM public.app_save_enrollment('{W}','{T}','{C}','{R}');",'raise_exception')+"RESET ROLE; SELECT (SELECT count(*) FROM public.enrollments) || ':' || (SELECT count(*) FROM public.enrollment_request_receipts);",['0:0'])

    def test_change_receipt_failure_rolls_back_state_and_event(self):
        self.check_sql(SAVED+"RESET ROLE; CREATE FUNCTION pg_temp.fail_enrollment_receipt() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic receipt failure'; END $$; CREATE TRIGGER fail_enrollment_receipt BEFORE INSERT ON public.enrollment_request_receipts FOR EACH ROW EXECUTE FUNCTION pg_temp.fail_enrollment_receipt(); SET ROLE authenticated;"+denied("PERFORM * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'paused',1,'other',gen_random_uuid());",'raise_exception')+"RESET ROLE; SELECT status || ':' || version FROM public.enrollments; SELECT count(*) FROM public.enrollment_events;",['active:1','1'])

    def test_change_event_failure_rolls_back_state_and_receipt(self):
        self.check_sql(SAVED+"RESET ROLE; CREATE FUNCTION pg_temp.fail_enrollment_change() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic change event failure'; END $$; CREATE TRIGGER fail_enrollment_change BEFORE INSERT ON public.enrollment_events FOR EACH ROW EXECUTE FUNCTION pg_temp.fail_enrollment_change(); SET ROLE authenticated;"+denied("PERFORM * FROM public.app_change_enrollment((SELECT enrollment_id FROM saved),'paused',1,'other',gen_random_uuid());",'raise_exception')+"RESET ROLE; SELECT status || ':' || version FROM public.enrollments; SELECT count(*) FROM public.enrollment_request_receipts;",['active:1','1'])

    def test_event_history_records_enum_reason_and_actor_without_personal_notes(self):
        self.check_sql(SAVED+change()+change('active',2,'NULL',str(uuid.uuid4()))+"RESET ROLE; SELECT coalesce(from_status,'new') || ':' || to_status || ':' || version || ':' || coalesce(reason,'none') || ':' || (actor_id='"+A+"') FROM public.enrollment_events ORDER BY version;",['new:active:1:none:true','active:paused:2:temporary_break:true','paused:active:3:none:true'])

    def test_candidates_and_roster_paginate_without_overlap_at_fifty(self):
        self.check_sql(f"""RESET ROLE;
INSERT INTO public.children(id,display_name,created_by) SELECT md5('enrollment-child-'||g)::uuid,'Fictional '||g,'{B}'::uuid FROM generate_series(1,51) g;
INSERT INTO public.workspace_children(workspace_id,child_id) SELECT '{W}'::uuid,md5('enrollment-child-'||g)::uuid FROM generate_series(1,51) g;
INSERT INTO public.enrollments(workspace_id,batch_id,child_id,created_by) SELECT '{W}'::uuid,'{T}'::uuid,md5('enrollment-child-'||g)::uuid,'{A}'::uuid FROM generate_series(1,51) g;
SET ROLE authenticated;
CREATE TEMP TABLE candidates AS SELECT * FROM public.app_enrollment_candidates('{W}');
SELECT count(*) FROM candidates;
SELECT count(*) FROM public.app_enrollment_candidates('{W}',(SELECT max(child_id::text)::uuid FROM candidates));
CREATE TEMP TABLE roster AS SELECT * FROM public.app_batch_enrollments('{W}','{T}');
SELECT count(*) FROM roster;
SELECT count(*) FROM public.app_batch_enrollments('{W}','{T}',(SELECT max(enrollment_id::text)::uuid FROM roster));
""",['50','2','50','1'])

    def test_parent_results_are_bounded_at_one_hundred(self):
        self.check_sql(f"""RESET ROLE;
INSERT INTO public.batches(id,workspace_id,course_id,name) SELECT md5('parent-batch-'||g)::uuid,'{W}'::uuid,'c0000000-0000-4000-8000-000000000001'::uuid,'Fictional batch '||g FROM generate_series(1,101) g;
INSERT INTO public.enrollments(workspace_id,batch_id,child_id,created_by) SELECT '{W}'::uuid,md5('parent-batch-'||g)::uuid,'{C}'::uuid,'{A}'::uuid FROM generate_series(1,101) g;
SET ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{B}',true);
SELECT count(*) FROM public.app_parent_enrollments('{C}');""",['100'])

    def test_private_tables_helpers_and_anonymous_execution_remain_denied(self):
        out=run_sql("""SELECT count(*) FROM (VALUES ('anon'),('authenticated')) r(role_name)
CROSS JOIN (VALUES ('enrollments'),('enrollment_request_receipts'),('enrollment_events')) t(table_name)
WHERE has_table_privilege(role_name,'public.'||table_name,'SELECT,INSERT,UPDATE,DELETE');
SELECT count(*) FROM pg_class WHERE oid IN ('public.enrollments'::regclass,'public.enrollment_request_receipts'::regclass,'public.enrollment_events'::regclass) AND relrowsecurity;
SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'app_%enrollment%' AND has_function_privilege('anon',p.oid,'EXECUTE');
""")
        self.assertEqual(out.splitlines(),['0','3','0'])

    def test_exact_rpc_inventory_is_authenticated_only_and_private_helper_is_denied(self):
        out=run_sql("""SELECT count(*) FROM (VALUES
 ('public.app_enrollment_batches(uuid)'),('public.app_enrollment_candidates(uuid,uuid)'),
 ('public.app_batch_enrollments(uuid,uuid,uuid)'),('public.app_save_enrollment(uuid,uuid,uuid,uuid)'),
 ('public.app_change_enrollment(uuid,text,integer,text,uuid)'),('public.app_parent_enrollments(uuid)')) f(signature)
WHERE has_function_privilege('authenticated',signature,'EXECUTE') AND NOT has_function_privilege('anon',signature,'EXECUTE');
SELECT has_function_privilege('authenticated','public.assert_private_enrollment_target(uuid,uuid,uuid)','EXECUTE') OR has_function_privilege('anon','public.assert_private_enrollment_target(uuid,uuid,uuid)','EXECUTE');""")
        self.assertEqual(out.splitlines(),['6','f'])

    def test_anonymous_auth_claim_and_parent_cannot_read_manager_directory(self):
        self.check_sql(f"SELECT set_config('request.jwt.claim.sub','',true);"+denied(f"PERFORM * FROM public.app_enrollment_batches('{W}');")+f"SELECT set_config('request.jwt.claim.sub','{B}',true);"+denied(f"PERFORM * FROM public.app_enrollment_candidates('{W}');")+"SELECT 'denied';",['denied'])


class EnrollmentRaceTests(unittest.TestCase):
    """Every history proves PostgreSQL blocking before releasing the first session."""
    def setUp(self):
        from tests.database.test_concurrent_authorization import query
        self.w,self.c,self.course,self.batch,self.member=[str(uuid.uuid4()) for _ in range(5)]
        query(f"""BEGIN;
INSERT INTO public.workspaces(id,name,type,created_by,creation_request_id) VALUES('{self.w}','Enrollment Race Academy','academy','{A}',gen_random_uuid());
INSERT INTO public.workspace_memberships(id,workspace_id,user_id,role,status) VALUES('{self.member}','{self.w}','{A}','owner','active');
INSERT INTO public.courses(id,workspace_id,name) VALUES('{self.course}','{self.w}','Race Course');
INSERT INTO public.batches(id,workspace_id,course_id,name) VALUES('{self.batch}','{self.w}','{self.course}','Race Batch');
INSERT INTO public.children(id,display_name,created_by) VALUES('{self.c}','Race Child','{B}');
INSERT INTO public.guardianships(child_id,guardian_user_id) VALUES('{self.c}','{B}');
INSERT INTO public.workspace_children(workspace_id,child_id) VALUES('{self.w}','{self.c}'); COMMIT;""")

    def tearDown(self):
        from tests.database.test_concurrent_authorization import query
        query(f"""BEGIN;
DELETE FROM public.enrollment_events WHERE enrollment_id IN (SELECT id FROM public.enrollments WHERE workspace_id='{self.w}');
DELETE FROM public.enrollment_request_receipts WHERE workspace_id='{self.w}';
DELETE FROM public.enrollments WHERE workspace_id='{self.w}';
DELETE FROM public.batch_coach_assignments WHERE workspace_id='{self.w}';
DELETE FROM public.batches WHERE workspace_id='{self.w}'; DELETE FROM public.courses WHERE workspace_id='{self.w}';
DELETE FROM public.workspace_children WHERE workspace_id='{self.w}'; DELETE FROM public.guardianships WHERE child_id='{self.c}'; DELETE FROM public.children WHERE id='{self.c}';
DELETE FROM public.workspace_memberships WHERE workspace_id='{self.w}'; DELETE FROM public.workspace_creation_receipts WHERE workspace_id='{self.w}'; DELETE FROM public.workspaces WHERE id='{self.w}'; COMMIT;""")
        self.assertEqual(query(f"SELECT (SELECT count(*) FROM public.workspaces WHERE id='{self.w}') + (SELECT count(*) FROM public.workspace_creation_receipts WHERE workspace_id='{self.w}');").splitlines()[-1],'0')

    def actor_sql(self,actor=A):
        return f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{actor}',true);"

    def save_sql(self,request):
        return self.actor_sql()+f"SELECT * FROM public.app_save_enrollment('{self.w}','{self.batch}','{self.c}','{request}');"

    def run_history(self, first_sql, second_sql, fails=False, rollback=False):
        from tests.database.test_concurrent_authorization import start_psql_session,wait_for_session_marker,wait_for_blocking_relationship,close_psql_session
        first,second=start_psql_session(),start_psql_session()
        n1,n2='enrollment_first_'+uuid.uuid4().hex,'enrollment_second_'+uuid.uuid4().hex
        try:
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{n1}',false);"+first_sql+"SELECT 'FIRST_LOCKED';\n");first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{n2}',false);"+second_sql+"COMMIT;\n");second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(n2,n1),'Expected observed PostgreSQL blocking')
            first.stdin.write(('ROLLBACK;' if rollback else 'COMMIT;')+"SELECT 'FIRST_RELEASED';\n");first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_RELEASED'))
            second.stdin.close();second.stdin=None
            output,errors=second.communicate(timeout=15)
            self.assertEqual(second.returncode,3 if fails else 0,errors)
            if fails:self.assertTrue('denied' in errors.lower() or 'unavailable' in errors.lower() or 'version' in errors.lower(),errors)
            return output
        finally:
            close_psql_session(second);close_psql_session(first)

    def test_concurrent_admissions_with_different_requests_write_once(self):
        from tests.database.test_concurrent_authorization import query
        self.run_history(self.save_sql(str(uuid.uuid4())),self.save_sql(str(uuid.uuid4())))
        self.assertEqual(query(f"SELECT (SELECT count(*) FROM public.enrollments WHERE workspace_id='{self.w}') || ':' || (SELECT count(*) FROM public.enrollment_events WHERE enrollment_id IN (SELECT id FROM public.enrollments WHERE workspace_id='{self.w}')) || ':' || (SELECT count(*) FROM public.enrollment_request_receipts WHERE workspace_id='{self.w}');").splitlines()[-1],'1:1:2')

    def test_concurrent_same_request_replays_one_receipt(self):
        from tests.database.test_concurrent_authorization import query
        request=str(uuid.uuid4())
        self.run_history(self.save_sql(request),self.save_sql(request))
        self.assertEqual(query(f"SELECT count(*) FROM public.enrollment_request_receipts WHERE workspace_id='{self.w}';").splitlines()[-1],'1')

    def test_waiting_admission_can_succeed_after_first_rollback(self):
        from tests.database.test_concurrent_authorization import query
        self.run_history(self.save_sql(str(uuid.uuid4())),self.save_sql(str(uuid.uuid4())),rollback=True)
        self.assertEqual(query(f"SELECT count(*) FROM public.enrollment_request_receipts WHERE workspace_id='{self.w}';").splitlines()[-1],'1')

    def revocation_history(self,kind,write_first,operation='save'):
        from tests.database.test_concurrent_authorization import query
        mutation={
          'workspace':f"UPDATE public.workspaces SET status='suspended' WHERE id='{self.w}';",
          'membership':f"UPDATE public.workspace_memberships SET status='suspended' WHERE id='{self.member}';",
          'connection':f"UPDATE public.workspace_children SET status='restricted' WHERE workspace_id='{self.w}';",
          'guardian':f"UPDATE public.guardianships SET status='revoked' WHERE child_id='{self.c}';",
          'assignment':f"DELETE FROM public.batch_coach_assignments WHERE workspace_id='{self.w}';"
        }[kind]
        call=self.save_sql(str(uuid.uuid4()))
        if operation!='save':
            query('BEGIN;'+call+'COMMIT;')
            if operation=='change':
                enrollment=query(f"SELECT id FROM public.enrollments WHERE workspace_id='{self.w}';").splitlines()[-1]
                call=self.actor_sql()+f"SELECT * FROM public.app_change_enrollment('{enrollment}','paused',1,'other',gen_random_uuid());"
            elif operation=='parent':
                call=self.actor_sql(B)+f"SELECT * FROM public.app_parent_enrollments('{self.c}');"
            elif operation=='coach':
                query(f"UPDATE public.workspace_memberships SET role='coach' WHERE id='{self.member}'; INSERT INTO public.batch_coach_assignments VALUES('{self.w}','{self.batch}','{self.member}');")
                call=self.actor_sql()+f"SELECT * FROM public.app_batch_enrollments('{self.w}','{self.batch}');"
        # Parent reads filter inactive workspace/connection to an empty result;
        # direct profile/guardian and staff authority failures deny execution.
        filters=operation=='parent' and kind in ('workspace','connection')
        output=self.run_history(call if write_first else mutation,mutation if write_first else call,fails=not write_first and not filters)
        if filters and not write_first:self.assertNotIn('Race Batch',output)
        expected='1' if write_first or operation!='save' else '0'
        self.assertEqual(query(f"SELECT count(*) FROM public.enrollments WHERE workspace_id='{self.w}';").splitlines()[-1],expected)
        if operation=='change':self.assertEqual(query(f"SELECT status FROM public.enrollments WHERE workspace_id='{self.w}';").splitlines()[-1],'paused' if write_first else 'active')

    def test_admission_first_locks_workspace_membership_and_connection(self):
        for kind in ['workspace','membership','connection']:
            with self.subTest(kind=kind):
                if kind!='workspace':self.tearDown();self.setUp()
                self.revocation_history(kind,True)

    def test_revocation_first_prevents_admission(self):
        for kind in ['workspace','membership','connection']:
            with self.subTest(kind=kind):
                if kind!='workspace':self.tearDown();self.setUp()
                self.revocation_history(kind,False)

    def test_change_first_holds_connection_until_commit(self):
        self.revocation_history('connection',True,'change')

    def test_connection_revoked_first_prevents_change(self):
        self.revocation_history('connection',False,'change')

    def test_parent_read_first_holds_eligible_guardian_until_commit(self):
        self.revocation_history('guardian',True,'parent')

    def test_guardian_revoked_first_prevents_parent_read(self):
        self.revocation_history('guardian',False,'parent')

    def test_parent_read_first_holds_active_connection_until_commit(self):
        self.revocation_history('connection',True,'parent')

    def test_connection_revoked_first_filters_parent_read(self):
        self.revocation_history('connection',False,'parent')

    def test_parent_read_first_holds_active_workspace_until_commit(self):
        self.revocation_history('workspace',True,'parent')

    def test_workspace_revoked_first_filters_parent_read(self):
        self.revocation_history('workspace',False,'parent')

    def test_coach_read_first_holds_assignment_until_commit(self):
        self.revocation_history('assignment',True,'coach')

    def test_assignment_removed_first_prevents_coach_read(self):
        self.revocation_history('assignment',False,'coach')

    def test_concurrent_status_edits_reject_stale_version(self):
        from tests.database.test_concurrent_authorization import query
        query('BEGIN;'+self.save_sql(str(uuid.uuid4()))+'COMMIT;')
        enrollment=query(f"SELECT id FROM public.enrollments WHERE workspace_id='{self.w}';").splitlines()[-1]
        pause=self.actor_sql()+f"SELECT * FROM public.app_change_enrollment('{enrollment}','paused',1,'other',gen_random_uuid());"
        complete=self.actor_sql()+f"SELECT * FROM public.app_change_enrollment('{enrollment}','completed',1,NULL,gen_random_uuid());"
        self.run_history(pause,complete,fails=True)
        self.assertEqual(query(f"SELECT status || ':' || version FROM public.enrollments WHERE id='{enrollment}';").splitlines()[-1],'paused:2')
