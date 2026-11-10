"""Two-session histories observe real PostgreSQL blocking before release."""
import json
import unittest
import uuid
from tests.database.attendance_fixtures import A,B
from tests.database import test_enrollments as enrollments
from tests.database.test_concurrent_authorization import query
class AttendanceConcurrencyTests(unittest.TestCase):
    # Borrow the barrier harness only; no inherited/duplicated enrollment cases.
    run_history=enrollments.EnrollmentRaceTests.run_history
    def setUp(self):
        enrollments.EnrollmentRaceTests.setUp(self)
        self.e,self.s=[str(uuid.uuid4()) for _ in range(2)]
        query(f"""BEGIN;
UPDATE public.workspaces SET scheduling_time_zone='UTC' WHERE id='{self.w}';
INSERT INTO public.enrollments(id,workspace_id,batch_id,child_id,created_by) VALUES('{self.e}','{self.w}','{self.batch}','{self.c}','{A}');
INSERT INTO public.schedule_sessions(id,workspace_id,batch_id,starts_at,ends_at,created_by,creation_request_id) VALUES('{self.s}','{self.w}','{self.batch}',date_trunc('day',clock_timestamp())+interval '10 hours',date_trunc('day',clock_timestamp())+interval '11 hours','{A}',gen_random_uuid()); COMMIT;""")
        self.token=self.sheet_token()
    def tearDown(self):
        query(f"""BEGIN;
DELETE FROM public.parent_signal_request_receipts WHERE workspace_id='{self.w}';
DELETE FROM public.parent_signals WHERE workspace_id='{self.w}';
DELETE FROM public.attendance_request_receipts WHERE workspace_id='{self.w}';
DELETE FROM public.parent_items WHERE workspace_id='{self.w}';
DELETE FROM public.attendance_record_events WHERE workspace_id='{self.w}';
DELETE FROM public.attendance_records WHERE workspace_id='{self.w}';
DELETE FROM public.attendance_sheets WHERE workspace_id='{self.w}';
DELETE FROM public.schedule_sessions WHERE workspace_id='{self.w}'; COMMIT;""")
        enrollments.EnrollmentRaceTests.tearDown(self)
    def actor(self,who=A):return f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{who}',true);"
    def sheet_token(self):
        lines=query('BEGIN;'+self.actor()+f"SELECT public.app_attendance_sheet('{self.w}','{self.s}')->>'roster_token'; ROLLBACK;").splitlines()
        return next(line for line in lines if len(line)==64 and all(c in '0123456789abcdef' for c in line))
    def save(self,request=None,version=0):
        rec=json.dumps([dict(enrollment_id=self.e,child_id=self.c,status='present')])
        return self.actor()+f"SELECT public.app_save_attendance('{self.w}','{self.s}',1,{version},'{self.token}','{rec}','{request or uuid.uuid4()}');"
    def signal(self,request=None):return self.actor(B)+f"SELECT public.app_send_parent_signal('{self.c}','{self.w}','{self.s}',1,'running_late',NULL,'{request or uuid.uuid4()}');"
    def change(self,status='paused',version=1):return self.actor()+f"SELECT * FROM public.app_change_enrollment('{self.e}','{status}',{version},{'NULL' if status=='active' else chr(39)+'other'+chr(39)},gen_random_uuid());"
    def count(self,table):return query(f"SELECT count(*) FROM public.{table} WHERE workspace_id='{self.w}';").splitlines()[-1]
    def lifecycle(self,kind):
        mutation={'cancel':"status='cancelled'",'move':"starts_at=starts_at+interval '1 hour',ends_at=ends_at+interval '1 hour'",'restore':"status='scheduled'"}[kind]
        return f"SELECT 1 FROM public.batches WHERE id='{self.batch}' FOR UPDATE; UPDATE public.schedule_sessions SET {mutation} WHERE id='{self.s}';"
    def test_duplicate_save_requests_serialize_without_share_upgrade(self):
        request=str(uuid.uuid4());call=self.save(request)
        self.run_history(call,call)
        self.assertEqual(self.count('attendance_request_receipts'),'1')
        self.assertEqual(self.count('attendance_record_events'),'1')
    def test_waiting_save_after_rollback_writes_once(self):
        self.run_history(self.save(),self.save(),rollback=True)
        self.assertEqual(self.count('attendance_sheets'),'1')
    def test_save_first_blocks_actual052_pause(self):
        self.run_history(self.save(),self.change())
        self.assertEqual(self.count('attendance_request_receipts'),'1')
    def test_actual052_pause_first_rejects_waiting_save(self):
        self.run_history(self.change(),self.save(),fails=True)
        self.assertEqual(self.count('attendance_request_receipts'),'0')
    def test_save_first_blocks_actual052_withdrawal(self):
        self.run_history(self.save(),self.change('withdrawn'))
        self.assertEqual(self.count('attendance_request_receipts'),'1')
    def test_actual052_withdrawal_first_rejects_waiting_save(self):
        self.run_history(self.change('withdrawn'),self.save(),fails=True)
        self.assertEqual(self.count('attendance_request_receipts'),'0')
    def test_pause_resume_aba_first_rejects_old_token(self):
        self.run_history(self.change()+self.change('active',2),self.save(),fails=True)
        self.assertNotEqual(self.token,self.sheet_token())
    def test_save_first_blocks_pause_resume_aba(self):
        self.run_history(self.save(),self.change()+self.change('active',2))
        self.assertNotEqual(self.token,self.sheet_token())
    def test_cancel_first_rejects_waiting_save(self):
        self.run_history(self.lifecycle('cancel'),self.save(),fails=True)
    def test_save_first_blocks_cancel(self):
        self.run_history(self.save(),self.lifecycle('cancel'))
    def test_move_first_rejects_waiting_save_version(self):
        self.run_history(self.lifecycle('move'),self.save(),fails=True)
    def test_save_first_blocks_move(self):
        self.run_history(self.save(),self.lifecycle('move'))
    def revocation(self,kind):
        return {'workspace':f"UPDATE public.workspaces SET status='suspended' WHERE id='{self.w}';",'membership':f"UPDATE public.workspace_memberships SET status='suspended' WHERE id='{self.member}';",'connection':f"UPDATE public.workspace_children SET status='restricted' WHERE workspace_id='{self.w}';",'guardian':f"UPDATE public.guardianships SET status='revoked' WHERE child_id='{self.c}';",'assignment':f"DELETE FROM public.batch_coach_assignments WHERE workspace_id='{self.w}';"}[kind]
    def test_save_first_holds_workspace(self):self.run_history(self.save(),self.revocation('workspace'))
    def test_workspace_revoked_first_denies_save(self):self.run_history(self.revocation('workspace'),self.save(),fails=True)
    def test_save_first_holds_membership(self):self.run_history(self.save(),self.revocation('membership'))
    def test_membership_revoked_first_denies_save(self):self.run_history(self.revocation('membership'),self.save(),fails=True)
    def test_save_first_holds_connection(self):self.run_history(self.save(),self.revocation('connection'))
    def test_connection_revoked_first_denies_save(self):self.run_history(self.revocation('connection'),self.save(),fails=True)
    def test_signal_first_holds_guardian(self):self.run_history(self.signal(),self.revocation('guardian'))
    def test_guardian_revoked_first_denies_signal(self):self.run_history(self.revocation('guardian'),self.signal(),fails=True)
    def test_signal_first_holds_connection(self):self.run_history(self.signal(),self.revocation('connection'))
    def test_connection_revoked_first_denies_signal(self):self.run_history(self.revocation('connection'),self.signal(),fails=True)
    def test_signal_first_blocks_pause(self):self.run_history(self.signal(),self.change())
    def test_pause_first_rejects_signal(self):self.run_history(self.change(),self.signal(),fails=True)
    def test_duplicate_signal_requests_write_one_append(self):
        call=self.signal(str(uuid.uuid4()));self.run_history(call,call)
        self.assertEqual(self.count('parent_signals'),'1')
    def test_status_waits_for_save_commit_and_returns_known(self):
        request=str(uuid.uuid4())
        p=json.dumps(dict(operation='save_attendance',workspace_id=self.w,session_id=self.s,expected_session_version=1,expected_sheet_version=0,roster_token=self.token,records=[dict(enrollment_id=self.e,child_id=self.c,status='present')]))
        status=self.actor()+f"SELECT public.app_attendance_request_status('{self.w}','{self.s}','{request}','{p}')->>'state';"
        self.assertIn('known',self.run_history(self.save(request),status))
    def test_status_waits_for_save_rollback_and_returns_unknown(self):
        request=str(uuid.uuid4())
        p=json.dumps(dict(operation='save_attendance',workspace_id=self.w,session_id=self.s,expected_session_version=1,expected_sheet_version=0,roster_token=self.token,records=[dict(enrollment_id=self.e,child_id=self.c,status='present')]))
        status=self.actor()+f"SELECT public.app_attendance_request_status('{self.w}','{self.s}','{request}','{p}')->>'state';"
        self.assertIn('unknown',self.run_history(self.save(request),status,rollback=True))
    def hidden_setup(self):
        child,enrollment=str(uuid.uuid4()),str(uuid.uuid4())
        query(f"INSERT INTO public.children(id,display_name,created_by) VALUES('{child}','Hidden synthetic','{B}'); INSERT INTO public.workspace_children(workspace_id,child_id,status) VALUES('{self.w}','{child}','restricted'); INSERT INTO public.enrollments(id,workspace_id,batch_id,child_id,created_by) VALUES('{enrollment}','{self.w}','{self.batch}','{child}','{A}');")
        return child
    def test_save_first_locks_initially_hidden_connection_against_reactivation(self):
        child=self.hidden_setup()
        try:self.run_history(self.save(),f"UPDATE public.workspace_children SET status='active' WHERE workspace_id='{self.w}' AND child_id='{child}';")
        finally:
            query(f"DELETE FROM public.enrollments WHERE child_id='{child}'; DELETE FROM public.workspace_children WHERE child_id='{child}'; DELETE FROM public.children WHERE id='{child}';")
    def test_hidden_connection_reactivated_first_invalidates_roster(self):
        child=self.hidden_setup()
        try:self.run_history(f"UPDATE public.workspace_children SET status='active' WHERE workspace_id='{self.w}' AND child_id='{child}';",self.save(),fails=True)
        finally:
            query(f"DELETE FROM public.enrollments WHERE child_id='{child}'; DELETE FROM public.workspace_children WHERE child_id='{child}'; DELETE FROM public.children WHERE id='{child}';")
    def admission(self):
        child=str(uuid.uuid4())
        query(f"INSERT INTO public.children(id,display_name,created_by) VALUES('{child}','Admission synthetic','{B}'); INSERT INTO public.workspace_children(workspace_id,child_id) VALUES('{self.w}','{child}');")
        return child,self.actor()+f"SELECT * FROM public.app_save_enrollment('{self.w}','{self.batch}','{child}',gen_random_uuid());"
    def remove_extra_child(self,child):
        query(f"DELETE FROM public.enrollment_request_receipts WHERE child_id='{child}'; DELETE FROM public.enrollment_events WHERE enrollment_id IN(SELECT id FROM public.enrollments WHERE child_id='{child}'); DELETE FROM public.enrollments WHERE child_id='{child}'; DELETE FROM public.workspace_children WHERE child_id='{child}'; DELETE FROM public.children WHERE id='{child}';")
    def test_save_first_blocks_actual052_admission(self):
        child,call=self.admission()
        try:self.run_history(self.save(),call)
        finally:self.remove_extra_child(child)
    def test_actual052_admission_first_invalidates_roster(self):
        child,call=self.admission()
        try:self.run_history(call,self.save(),fails=True)
        finally:self.remove_extra_child(child)
    def test_restore_aba_first_rejects_old_session_version(self):
        self.run_history(self.lifecycle('cancel')+self.lifecycle('restore'),self.save(),fails=True)
    def test_save_first_blocks_cancel_restore_aba(self):
        self.run_history(self.save(),self.lifecycle('cancel')+self.lifecycle('restore'))
    def assigned(self):
        query(f"UPDATE public.workspace_memberships SET role='coach' WHERE id='{self.member}'; INSERT INTO public.batch_coach_assignments VALUES('{self.w}','{self.batch}','{self.member}');")
    def test_save_first_holds_assignment(self):
        self.assigned();self.run_history(self.save(),self.revocation('assignment'))
    def test_assignment_revoked_first_denies_save(self):
        self.assigned();self.run_history(self.revocation('assignment'),self.save(),fails=True)
    def test_signal_first_holds_workspace(self):self.run_history(self.signal(),self.revocation('workspace'))
    def test_workspace_revoked_first_denies_signal(self):self.run_history(self.revocation('workspace'),self.signal(),fails=True)
    def test_signal_first_blocks_cancel(self):self.run_history(self.signal(),self.lifecycle('cancel'))
    def test_cancel_first_rejects_signal(self):self.run_history(self.lifecycle('cancel'),self.signal(),fails=True)
    def test_signal_status_waits_for_commit(self):
        request=str(uuid.uuid4())
        p=json.dumps(dict(operation='send_parent_signal',child_id=self.c,workspace_id=self.w,session_id=self.s,expected_session_version=1,type='running_late',reason=None))
        call=self.actor(B)+f"SELECT public.app_parent_signal_request_status('{self.c}','{self.w}','{self.s}','{request}','{p}')->>'state';"
        self.assertIn('known',self.run_history(self.signal(request),call))
    def today(self):return self.actor()+f"SELECT public.app_today_sessions('{self.w}',(clock_timestamp() AT TIME ZONE 'UTC')::date);"
    def test_today_read_first_holds_coach_assignment(self):
        self.assigned();self.run_history(self.today(),self.revocation('assignment'))
    def test_assignment_revoked_first_denies_waiting_today_summary(self):
        self.assigned();self.run_history(self.revocation('assignment'),self.today(),fails=True)
    def test_actual052_resume_first_invalidates_old_active_token(self):
        query('BEGIN;'+self.change()+'COMMIT;')
        self.run_history(self.change('active',2),self.save(),fails=True)
    def test_locked_paused_sheet_read_first_blocks_actual052_resume(self):
        query('BEGIN;'+self.change()+'COMMIT;')
        read=self.actor()+f"SELECT public.app_attendance_sheet('{self.w}','{self.s}');"
        self.run_history(read,self.change('active',2))
    def clock_fixture(self):
        """Privileged synthetic seam only; production helper always reads real time."""
        from tests.database.test_authorization import run_sql
        self.assertEqual(run_sql("SELECT to_regprocedure('public.attendance_clock()') IS NOT NULL;"),'t')
        original=run_sql("SELECT pg_get_functiondef('public.attendance_clock()'::regprocedure);")
        query("CREATE TABLE public.attendance_test_clock(value timestamptz NOT NULL); REVOKE ALL ON public.attendance_test_clock FROM PUBLIC,anon,authenticated; INSERT INTO public.attendance_test_clock VALUES(date_trunc('day',clock_timestamp())+interval '12 hours'); CREATE OR REPLACE FUNCTION public.attendance_clock() RETURNS timestamptz LANGUAGE sql VOLATILE SET search_path='' AS $$ SELECT value FROM public.attendance_test_clock $$;")
        return original
    def clock_history(self,advance):
        from tests.database.test_concurrent_authorization import start_psql_session,wait_for_session_marker,wait_for_blocking_relationship,close_psql_session
        original=self.clock_fixture();request=str(uuid.uuid4());first=second=None
        try:
            first,second=start_psql_session(),start_psql_session()
            n1,n2='attendance_clock_lock_'+uuid.uuid4().hex,'attendance_clock_send_'+uuid.uuid4().hex
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SET application_name='{n1}'; SELECT pg_advisory_xact_lock(hashtextextended('parent-signal-request:{request}',0)); SELECT 'CLOCK_LOCKED';\n");first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'CLOCK_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SET application_name='{n2}';"+self.signal(request)+"COMMIT;\n");second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(n2,n1))
            # Only now, after observing the blocked caller, advance the test day.
            mutation="UPDATE public.attendance_test_clock SET value=value+interval '1 day';" if advance else ''
            first.stdin.write(mutation+"COMMIT; SELECT 'CLOCK_RELEASED';\n");first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'CLOCK_RELEASED'))
            second.stdin.close();second.stdin=None
            output,errors=second.communicate(timeout=15)
            self.assertEqual(second.returncode,3 if advance else 0,errors)
            if advance:self.assertIn('local day changed',errors)
            self.assertEqual(self.count('parent_signals'),'0' if advance else '1')
        finally:
            for process in [second,first]:
                if process is not None:close_psql_session(process)
            query(original+'; DROP TABLE public.attendance_test_clock;')
    def test_signal_rechecks_local_day_after_observed_request_lock_wait(self):self.clock_history(True)
    def test_signal_same_local_day_after_observed_request_lock_wait_succeeds(self):self.clock_history(False)
    def test_signal_receipt_replays_on_later_local_day_without_new_append(self):
        original=self.clock_fixture();request=str(uuid.uuid4())
        try:
            query('BEGIN;'+self.signal(request)+'COMMIT;')
            query("UPDATE public.attendance_test_clock SET value=value+interval '1 day';")
            query('BEGIN;'+self.signal(request)+'COMMIT;')
            self.assertEqual(self.count('parent_signals'),'1')
        finally:query(original+'; DROP TABLE public.attendance_test_clock;')
