"""Parent reports remain append-only and never imply coach attendance."""
from tests.database.attendance_fixtures import *
def signal(kind='running_late',reason='NULL',request=R):return f"public.app_send_parent_signal('{C}','{W}','{S}',1,'{kind}',{reason},'{request}')"
class ParentSignalTests(AttendanceCase):
    def test_signal_is_report_only_and_identical_request_replays(self):
        self.check(parent()+f"SELECT {signal()}->>'signal_id'; SELECT {signal()}->>'signal_id'; RESET ROLE; SELECT (SELECT count(*) FROM public.parent_signals)||':'||(SELECT count(*) FROM public.attendance_records);",['1:0'])
    def test_all_four_enums_and_missing_reason_contract(self):
        for kind,reason in [('running_late','NULL'),('missing_today',"'unwell'"),('dropped_off','NULL'),('picked_up','NULL')]:
            with self.subTest(kind=kind):self.check(parent()+f"SELECT {signal(kind,reason)}->>'type';",[kind])
    def test_invalid_reason_is_not_stored(self):
        for kind,reason in [('missing_today','NULL'),('running_late',"'other'"),('unknown','NULL')]:
            with self.subTest(kind=kind):self.check(parent()+denied(f"PERFORM {signal(kind,reason)};",'invalid_parameter_value')+"RESET ROLE; SELECT count(*) FROM public.parent_signals;",['0'])
    def test_history_appends_and_coach_sees_latest_report(self):
        self.check(parent()+f"SELECT {signal()}; SELECT {signal('picked_up',request=R2)}; SELECT set_config('request.jwt.claim.sub','{A}',true); SELECT public.app_session_parent_signals('{W}','{S}')#>>'{{signals,0,type}}'; RESET ROLE; SELECT count(*) FROM public.parent_signals;",['picked_up','2'])
    def test_paused_child_cannot_send_but_can_recover_saved_signal(self):
        self.check(parent()+f"SELECT {signal()}; RESET ROLE; UPDATE public.enrollments SET status='paused'; SET ROLE authenticated; SELECT {signal()}->>'type';"+denied(f"PERFORM {signal(request=R2)};",'serialization_failure')+"SELECT 'denied';",['running_late','denied'])
    def test_signal_request_changed_payload_is_collision(self):
        self.check(parent()+f"SELECT {signal()};"+denied(f"PERFORM {signal('picked_up')};",'unique_violation')+"RESET ROLE; SELECT count(*) FROM public.parent_signals;",['1'])
    def test_signal_status_unknown_and_known_full_payload(self):
        p=f"jsonb_build_object('operation','send_parent_signal','child_id','{C}','workspace_id','{W}','session_id','{S}','expected_session_version',1,'type','running_late','reason',null)"
        self.check(parent()+f"SELECT public.app_parent_signal_request_status('{C}','{W}','{S}','{R}',{p})->>'state'; CREATE TEMP TABLE saved_signal_receipt AS SELECT {signal()} r; SELECT public.app_parent_signal_request_status('{C}','{W}','{S}','{R}',{p})->>'state';",['unknown','known'])
    def test_signal_wrong_local_day_is_rejected_without_history(self):
        self.check(f"RESET ROLE; UPDATE public.schedule_sessions SET starts_at=starts_at-interval '1 day',ends_at=ends_at-interval '1 day'; SET ROLE authenticated;"+parent()+denied(f"PERFORM public.app_send_parent_signal('{C}','{W}','{S}',2,'running_late',NULL,'{R}');",'serialization_failure')+"RESET ROLE; SELECT count(*) FROM public.parent_signals;",['0'])
    def assert_signal_failure_snapshot_and_retry(self,table):
        call=signal('picked_up',request=R2)
        condition=f"NEW.request_id='{R2}'" if table=='parent_signal_request_receipts' else "NEW.type='picked_up'"
        setup=f"CREATE TEMP TABLE saved_attendance AS SELECT {save()} r;"+parent()+f"CREATE TEMP TABLE original_signal AS SELECT {signal()} r; RESET ROLE;"+capture_snapshot('before_signal',SIGNAL_SNAPSHOT_TABLES)
        setup+=f"CREATE FUNCTION pg_temp.fail_signal() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF {condition} THEN RAISE EXCEPTION 'synthetic signal failure'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_signal BEFORE INSERT ON public.{table} FOR EACH ROW EXECUTE FUNCTION pg_temp.fail_signal(); SET ROLE authenticated;"
        reject=injected_failure(f"PERFORM {call};",'synthetic signal failure')+'RESET ROLE;'+snapshot_unchanged('before_signal',SIGNAL_SNAPSHOT_TABLES)
        reject+=f"SELECT NOT EXISTS(SELECT 1 FROM public.parent_signal_request_receipts WHERE request_id='{R2}'); DROP TRIGGER fail_signal ON public.{table}; SET ROLE authenticated; CREATE TEMP TABLE retry_signal AS SELECT {call} r; RESET ROLE;"+capture_snapshot('after_retry',SIGNAL_SNAPSHOT_TABLES)
        reject+=f"SET ROLE authenticated; CREATE TEMP TABLE replay_signal AS SELECT {call} r; SELECT a.r=b.r FROM retry_signal a CROSS JOIN replay_signal b; RESET ROLE;"+snapshot_unchanged('after_retry',SIGNAL_SNAPSHOT_TABLES)
        verify=f"SELECT (SELECT count(*) FROM public.parent_signals)||':'||(SELECT count(*) FROM public.parent_signal_request_receipts)||':'||(SELECT count(*) FROM public.parent_signal_request_receipts WHERE request_id='{R2}');"
        verify+="SELECT to_jsonb(s)=(SELECT value FROM before_signal,jsonb_array_elements(data->'parent_signals') WHERE value->>'id'=s.id::text) FROM public.parent_signals s WHERE type='running_late';"
        # All attendance tables stay byte-identical even after the successful send.
        verify+=f"SELECT (a.data-ARRAY['parent_signals','parent_signal_request_receipts'])::text=(b.data-ARRAY['parent_signals','parent_signal_request_receipts'])::text FROM before_signal a CROSS JOIN after_retry b;"
        self.check(setup+reject+verify,['t','t','t','t','2:2:1','t','t'])
    def test_signal_receipt_failure_rolls_back_append(self):
        self.assert_signal_failure_snapshot_and_retry('parent_signal_request_receipts')
    def test_signal_insert_failure_preserves_snapshots_and_same_key_retry(self):
        self.assert_signal_failure_snapshot_and_retry('parent_signals')
    def test_parent_sessions_only_include_own_latest_signal_and_saved_attendance(self):
        self.check(f"SELECT {save()};"+parent()+f"SELECT {signal()}; CREATE TEMP TABLE ps AS SELECT public.app_parent_sessions('{C}','{W}',(clock_timestamp() AT TIME ZONE 'UTC')::date) p; SELECT (p#>>'{{sessions,0,attendance,status}}')||':'||(p#>>'{{sessions,0,own_latest_signal,type}}')||':'||(p#>>'{{sessions,0,can_signal}}') FROM ps;",['present:running_late:true'])
    def test_other_actor_cannot_recover_signal_and_guardian_revocation_denies_replay(self):
        other=f"public.app_send_parent_signal('{C2}','{W}','{S}',1,'running_late',NULL,'{R}')"
        payload=f"jsonb_build_object('operation','send_parent_signal','child_id','{C2}','workspace_id','{W}','session_id','{S}','expected_session_version',1,'type','running_late','reason',null)"
        self.check(extra_children(((C2,E2,D),))+parent()+f"CREATE TEMP TABLE first_signal AS SELECT {signal()} r; SELECT set_config('request.jwt.claim.sub','{D}',true);"+denied(f"PERFORM {other};",'unique_violation')+denied(f"PERFORM public.app_parent_signal_request_status('{C2}','{W}','{S}','{R}',{payload});",'unique_violation')+denied(f"PERFORM {signal()};",'insufficient_privilege')+f"RESET ROLE; UPDATE public.guardianships SET status='revoked' WHERE child_id='{C}'; SET ROLE authenticated;"+parent()+denied(f"PERFORM {signal()};",'insufficient_privilege')+"RESET ROLE; SELECT (SELECT count(*) FROM public.parent_signals)||':'||(SELECT count(*) FROM public.parent_signal_request_receipts);",['1:1'])
    def test_coach_signal_cursor_ties_50_1(self):
        self.check(f"""RESET ROLE;
INSERT INTO public.children(id,display_name,created_by) SELECT md5('signal-page-'||g)::uuid,'Child '||g,'{B}' FROM generate_series(1,51) g;
INSERT INTO public.guardianships(child_id,guardian_user_id) SELECT md5('signal-page-'||g)::uuid,'{B}' FROM generate_series(1,51) g;
INSERT INTO public.workspace_children(workspace_id,child_id) SELECT '{W}',md5('signal-page-'||g)::uuid FROM generate_series(1,51) g;
INSERT INTO public.enrollments(id,workspace_id,batch_id,child_id,created_by) SELECT md5('signal-enrollment-'||g)::uuid,'{W}','{T}',md5('signal-page-'||g)::uuid,'{A}' FROM generate_series(1,51) g;
INSERT INTO public.parent_signals(workspace_id,batch_id,session_id,enrollment_id,child_id,actor_id,type,created_at) SELECT '{W}','{T}','{S}',md5('signal-enrollment-'||g)::uuid,md5('signal-page-'||g)::uuid,'{B}','running_late','2026-11-10 10:00Z' FROM generate_series(1,51) g;
SET ROLE authenticated; CREATE TEMP TABLE page AS SELECT public.app_session_parent_signals('{W}','{S}') p; SELECT jsonb_array_length(p->'signals') FROM page;
SELECT jsonb_array_length(public.app_session_parent_signals('{W}','{S}',(SELECT (p#>>'{{next,child_id}}')::uuid FROM page),(SELECT (p#>>'{{next,actor_id}}')::uuid FROM page))->'signals');
""",['50','1'])
    def test_parent_sessions_cursor_ties_50_1(self):
        self.check(f"""RESET ROLE; DELETE FROM public.schedule_sessions;
INSERT INTO public.schedule_sessions(id,workspace_id,batch_id,starts_at,ends_at,created_by,creation_request_id) SELECT md5('parent-session-page-'||g)::uuid,'{W}','{T}','2026-11-10 10:00Z'::timestamptz,'2026-11-10 11:00Z'::timestamptz,'{A}',gen_random_uuid() FROM generate_series(1,51) g;
SET ROLE authenticated;"""+parent()+f"CREATE TEMP TABLE page AS SELECT public.app_parent_sessions('{C}','{W}','2026-11-10') p; SELECT jsonb_array_length(p->'sessions') FROM page; SELECT jsonb_array_length(public.app_parent_sessions('{C}','{W}','2026-11-10',NULL,(SELECT (p#>>'{{next,starts_at}}')::timestamptz FROM page),(SELECT (p#>>'{{next,id}}')::uuid FROM page))->'sessions');",['50','1'])
    def test_signal_accepts_supported_extreme_local_dates_with_owner_test_clock(self):
        for zone,local in [('Pacific/Kiritimati','2000-01-01 00:30'),('America/Los_Angeles','2100-12-31 23:30')]:
            with self.subTest(zone=zone):
                # Function/table DDL is inside this rolled-back synthetic transaction.
                self.check(f"RESET ROLE; UPDATE public.workspaces SET scheduling_time_zone='{zone}' WHERE id='{W}'; UPDATE public.schedule_sessions SET starts_at='{local}'::timestamp AT TIME ZONE '{zone}',ends_at=('{local}'::timestamp AT TIME ZONE '{zone}')+interval '1 hour'; CREATE TEMP TABLE boundary_clock(value timestamptz); INSERT INTO boundary_clock VALUES('{local}'::timestamp AT TIME ZONE '{zone}'); CREATE OR REPLACE FUNCTION public.attendance_clock() RETURNS timestamptz LANGUAGE sql VOLATILE SET search_path='' AS $$ SELECT value FROM pg_temp.boundary_clock $$; SET ROLE authenticated;"+parent()+f"SELECT public.app_send_parent_signal('{C}','{W}','{S}',2,'running_late',NULL,'{R}')->>'type';",['running_late'])
    def test_signal_rejects_session_dates_outside_academy_local_range(self):
        for zone,local in [('Pacific/Kiritimati','1999-12-31 23:30'),('America/Los_Angeles','1999-12-31 23:30'),('Pacific/Kiritimati','2101-01-01 00:30'),('America/Los_Angeles','2101-01-01 00:30')]:
            with self.subTest(zone=zone):
                self.check(f"RESET ROLE; UPDATE public.workspaces SET scheduling_time_zone='{zone}' WHERE id='{W}'; UPDATE public.schedule_sessions SET starts_at='{local}'::timestamp AT TIME ZONE '{zone}',ends_at=('{local}'::timestamp AT TIME ZONE '{zone}')+interval '1 hour'; SET ROLE authenticated;"+parent()+denied(f"PERFORM public.app_send_parent_signal('{C}','{W}','{S}',2,'running_late',NULL,'{R}');",'invalid_parameter_value')+"RESET ROLE; SELECT count(*) FROM public.parent_signals;",['0'])
