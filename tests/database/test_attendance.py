"""Attendance schema, coherent roster and transactional recovery contracts."""
from tests.database.attendance_fixtures import *
class AttendanceTests(AttendanceCase):
    def test_unsaved_sheet_is_unmarked_and_read_does_not_create_sheet(self):
        self.check(f"SELECT ({sheet()}->>'sheet_version')||':'||({sheet()}#>>'{{rows,0,status}}' IS NULL); RESET ROLE; SELECT count(*) FROM public.attendance_sheets;",['0:true','0'])
    def test_private_tables_have_rls_and_no_client_grants(self):
        names=['attendance_sheets','attendance_records','attendance_record_events','attendance_request_receipts','parent_signals','parent_signal_request_receipts','parent_items']
        vals=','.join("('"+n+"')" for n in names)
        self.assertEqual(run_sql(f"SELECT count(*) FROM (VALUES {vals}) t(n) JOIN pg_class c ON c.oid=('public.'||n)::regclass WHERE relrowsecurity AND NOT has_table_privilege('authenticated',c.oid,'SELECT,INSERT,UPDATE,DELETE') AND NOT has_table_privilege('anon',c.oid,'SELECT,INSERT,UPDATE,DELETE');"),'7')
    def test_save_receipt_records_audit_and_stable_item_correction(self):
        self.check(f"SELECT {save()}->>'sheet_version'; RESET ROLE; CREATE TEMP TABLE original_item AS SELECT id,created_at,payload FROM public.parent_items; SET ROLE authenticated; SELECT {save('late',1,R2)}->>'sheet_version'; RESET ROLE; SELECT i.id=o.id AND i.created_at=o.created_at AND i.payload<>o.payload FROM public.parent_items i CROSS JOIN original_item o; SELECT (SELECT count(*) FROM public.attendance_records)||':'||(SELECT count(*) FROM public.attendance_record_events)||':'||(SELECT count(*) FROM public.parent_items)||':'||(SELECT count(*) FROM public.attendance_request_receipts);",['1','2','t','1:2:1:2'])
    def test_old_receipt_does_not_return_latest_sheet(self):
        self.check(f"SELECT {save()}; SELECT {save('late',1,R2)}; SELECT {save()}->>'sheet_version'; SELECT {sheet()}->>'sheet_version';",['1','2'])
    def test_request_collision_compares_entire_payload(self):
        self.check(f"SELECT {save()};"+denied(f"PERFORM {save('absent')};",'unique_violation')+"SELECT 'denied';",['denied'])
    def test_all_five_statuses_are_explicitly_saved(self):
        for status in ['present','late','absent','excused','make_up']:
            with self.subTest(status=status):self.check(f"SELECT {save(status)}; SELECT {sheet()}#>>'{{rows,0,status}}';",[status])
    def test_stale_sheet_or_token_fails_without_receipt(self):
        for call in [save(version=1),save(token="repeat('a',64)")]:
            with self.subTest(call=call):self.check(denied(f"PERFORM {call};",'serialization_failure')+"RESET ROLE; SELECT count(*) FROM public.attendance_request_receipts;",['0'])
    def test_session_version_is_owned_by_lifecycle_trigger(self):
        self.check(f"RESET ROLE; UPDATE public.schedule_sessions SET version=99 WHERE id='{S}'; SELECT version FROM public.schedule_sessions; UPDATE public.schedule_sessions SET status='cancelled',version=99 WHERE id='{S}'; SELECT version FROM public.schedule_sessions;",['1','2'])
    def test_malformed_records_fail_closed(self):
        for data in ['null','[]','{}',records('unknown'),records().replace('"status": "present"','"status": "present", "extra": 1')]:
            with self.subTest(data=data):self.check(denied(f"PERFORM public.app_save_attendance('{W}','{S}',1,0,repeat('a',64),'{data}','{R}');",'invalid_parameter_value')+"SELECT 'denied';",['denied'])
    def test_each_transaction_stage_failure_rolls_back_everything(self):
        for table in ['attendance_records','attendance_record_events','parent_items','attendance_request_receipts']:
            with self.subTest(table=table):
                self.check(f"RESET ROLE; CREATE FUNCTION pg_temp.fail_attendance() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic failure'; END $$; CREATE TRIGGER fail_attendance BEFORE INSERT ON public.{table} FOR EACH ROW EXECUTE FUNCTION pg_temp.fail_attendance(); SET ROLE authenticated;"+injected_failure(f"PERFORM {save()};",'synthetic failure')+"RESET ROLE; SELECT (SELECT count(*) FROM public.attendance_sheets)+(SELECT count(*) FROM public.attendance_records)+(SELECT count(*) FROM public.attendance_record_events)+(SELECT count(*) FROM public.parent_items)+(SELECT count(*) FROM public.attendance_request_receipts);",['0'])
    def test_current_authority_required_for_old_receipt(self):
        self.check(f"SELECT {save()}; RESET ROLE; UPDATE public.workspace_children SET status='restricted'; SET ROLE authenticated;"+denied(f"PERFORM {save()};")+"SELECT 'denied';",['denied'])
    def test_exact_public_rpc_inventory_and_private_helpers(self):
        signatures=['app_today_academies(uuid)','app_today_sessions(uuid,date,timestamp with time zone,uuid)','app_attendance_sheet(uuid,uuid)','app_save_attendance(uuid,uuid,integer,integer,text,jsonb,uuid)','app_attendance_request_status(uuid,uuid,uuid,jsonb)','app_session_parent_signals(uuid,uuid,uuid,uuid)','app_parent_academies(uuid,uuid)','app_parent_batches(uuid,uuid,uuid)','app_parent_sessions(uuid,uuid,date,uuid,timestamp with time zone,uuid)','app_send_parent_signal(uuid,uuid,uuid,integer,text,text,uuid)','app_parent_signal_request_status(uuid,uuid,uuid,uuid,jsonb)','app_parent_items(uuid,uuid,uuid,timestamp with time zone,uuid)','app_parent_attendance_week(uuid,uuid,date,uuid)']
        vals=','.join("('public."+s+"')" for s in signatures)
        self.assertEqual(run_sql(f"SELECT count(*) FROM (VALUES {vals}) f(sig) JOIN pg_proc p ON p.oid=to_regprocedure(sig) WHERE p.prosecdef AND p.prorettype='jsonb'::regtype AND has_function_privilege('authenticated',p.oid,'EXECUTE') AND NOT has_function_privilege('anon',p.oid,'EXECUTE'); SELECT count(*) FROM pg_proc WHERE proname IN ('attendance_staff','attendance_roster','attendance_payload','parent_signal_payload','attendance_parent') AND (prosecdef OR has_function_privilege('authenticated',oid,'EXECUTE') OR has_function_privilege('anon',oid,'EXECUTE'));"), '13\n0')
    def test_status_unknown_and_known_use_full_normalized_payload(self):
        self.check(f"CREATE TEMP TABLE pending AS SELECT jsonb_build_object('operation','save_attendance','workspace_id','{W}','session_id','{S}','expected_session_version',1,'expected_sheet_version',0,'roster_token',{sheet()}->>'roster_token','records','{records()}'::jsonb) p; SELECT public.app_attendance_request_status('{W}','{S}','{R}',(SELECT p FROM pending))->>'state'; CREATE TEMP TABLE saved_receipt AS SELECT {save()} r; SELECT public.app_attendance_request_status('{W}','{S}','{R}',(SELECT p FROM pending))->>'state';"+denied(f"PERFORM public.app_attendance_request_status('{W}','{S}','{R}',(SELECT p||jsonb_build_object('expected_sheet_version',1) FROM pending));",'unique_violation')+"SELECT 'bound';",['unknown','known','bound'])
    def test_payload_reordered_keys_and_uppercase_uuids_normalize_on_retry(self):
        first=[dict(enrollment_id=E,child_id=C,status='present'),dict(enrollment_id=E2,child_id=C2,status='late')]
        reordered=[dict(status='late',child_id=C2.upper(),enrollment_id=E2.upper()),dict(status='present',child_id=C.upper(),enrollment_id=E.upper())]
        self.check(extra_children(((C2,E2,B),))+f"CREATE TEMP TABLE original_receipt AS SELECT {save_records(first)} r; CREATE TEMP TABLE retry_receipt AS SELECT {save_records(reordered)} r; SELECT o.r=r.r FROM original_receipt o CROSS JOIN retry_receipt r; RESET ROLE; SELECT (SELECT count(*) FROM public.attendance_records)||':'||(SELECT count(*) FROM public.attendance_record_events)||':'||(SELECT count(*) FROM public.attendance_request_receipts);",['t','2:2:1'])
    def test_duplicate_normalized_child_or_enrollment_rejected(self):
        import json
        a=dict(enrollment_id=E,child_id=C,status='present')
        for b in [dict(a),dict(a,enrollment_id=E.upper(),child_id=T),dict(a,enrollment_id=T,child_id=C.upper())]:
            with self.subTest(b=b):self.check(denied(f"PERFORM public.app_save_attendance('{W}','{S}',1,0,repeat('a',64),'{json.dumps([a,b])}','{R}');",'invalid_parameter_value')+"SELECT 'denied';",['denied'])
    def test_creator_guardian_and_connection_scope_is_not_staff_scope(self):
        self.check(f"SELECT set_config('request.jwt.claim.sub','{B}',true);"+denied(f"PERFORM {sheet()};")+"SELECT 'denied';",['denied'])
    def test_assigned_coach_and_admin_have_access_unassigned_coach_does_not(self):
        self.check(f"RESET ROLE; INSERT INTO public.workspace_memberships(id,workspace_id,user_id,role,status) VALUES('{R2}','{W}','{D}','coach','active'); SET ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{D}',true);"+denied(f"PERFORM {sheet()};")+f"RESET ROLE; INSERT INTO public.batch_coach_assignments VALUES('{W}','{T}','{R2}'); SET ROLE authenticated; SELECT {sheet()}->>'sheet_version'; RESET ROLE; UPDATE public.workspace_memberships SET role='admin' WHERE id='{R2}'; DELETE FROM public.batch_coach_assignments; SET ROLE authenticated; SELECT {sheet()}->>'sheet_version';",['0','0'])
    def test_roster_cap_is_before_inactive_connection_filter(self):
        fixture=f"""RESET ROLE;
INSERT INTO public.children(id,display_name,created_by) SELECT md5('cap-'||g)::uuid,'Synthetic '||g,'{B}'::uuid FROM generate_series(1,200) g;
INSERT INTO public.workspace_children(workspace_id,child_id,status) SELECT '{W}'::uuid,md5('cap-'||g)::uuid,'restricted' FROM generate_series(1,200) g;
INSERT INTO public.enrollments(workspace_id,batch_id,child_id,created_by) SELECT '{W}'::uuid,'{T}'::uuid,md5('cap-'||g)::uuid,'{A}'::uuid FROM generate_series(1,199) g;
SET ROLE authenticated;
SELECT ({sheet()}->>'roster_too_large')||':'||jsonb_array_length({sheet()}->'rows');
RESET ROLE; INSERT INTO public.enrollments(workspace_id,batch_id,child_id,created_by) VALUES('{W}','{T}',md5('cap-200')::uuid,'{A}'); SET ROLE authenticated;
SELECT ({sheet()}->>'roster_too_large')||':'||jsonb_array_length({sheet()}->'rows')||':'||({sheet()}#>>'{{session,roster_size}}' IS NULL);
"""
        self.check(fixture,['false:1','true:0:true'])
    def test_roster_200_connected_rows_is_complete(self):
        fixture=f"""RESET ROLE;
INSERT INTO public.children(id,display_name,created_by) SELECT md5('full-'||g)::uuid,'Synthetic '||g,'{B}'::uuid FROM generate_series(1,199) g;
INSERT INTO public.workspace_children(workspace_id,child_id) SELECT '{W}'::uuid,md5('full-'||g)::uuid FROM generate_series(1,199) g;
INSERT INTO public.enrollments(workspace_id,batch_id,child_id,created_by) SELECT '{W}'::uuid,'{T}'::uuid,md5('full-'||g)::uuid,'{A}'::uuid FROM generate_series(1,199) g;
SET ROLE authenticated; SELECT jsonb_array_length({sheet()}->'rows');
CREATE TEMP TABLE full_sheet AS SELECT {sheet()} data;
SELECT public.app_save_attendance('{W}','{S}',1,0,(SELECT data->>'roster_token' FROM full_sheet),(SELECT jsonb_agg(jsonb_build_object('enrollment_id',r->'enrollment_id','child_id',r->'child_id','status','present')) FROM full_sheet,jsonb_array_elements(data->'rows') r),'{R}')->>'record_count';
"""
        self.check(fixture,['200','200'])
    def test_pause_resume_aba_changes_token_and_retains_historical_record(self):
        self.check(f"CREATE TEMP TABLE before_token AS SELECT {sheet()}->>'roster_token' token; SELECT {save()}; SELECT * FROM public.app_change_enrollment('{E}','paused',1,'other',gen_random_uuid()); SELECT {sheet()}#>>'{{session,roster_size}}'; SELECT * FROM public.app_change_enrollment('{E}','active',2,NULL,gen_random_uuid()); SELECT ({sheet()}->>'roster_token')<>(SELECT token FROM before_token);"+denied(f"PERFORM public.app_save_attendance('{W}','{S}',1,1,(SELECT token FROM before_token),'{records()}','{R2}');",'serialization_failure')+"RESET ROLE; SELECT count(*) FROM public.attendance_records;",['0',E+'|active|3','t','1'])
    def test_cancelled_session_allows_historical_receipt_but_not_new_save(self):
        self.check(f"SELECT {save()}; RESET ROLE; UPDATE public.schedule_sessions SET status='cancelled'; SET ROLE authenticated; SELECT {save()}->>'sheet_version';"+denied(f"PERFORM {save('late',1,R2)};",'serialization_failure')+"SELECT 'denied';",['1','denied'])
    def test_invalid_payload_operation_null_is_rejected(self):
        self.check(denied(f"PERFORM public.app_attendance_request_status('{W}','{S}','{R}',jsonb_build_object('operation',null,'workspace_id','{W}','session_id','{S}','expected_session_version',1,'expected_sheet_version',0,'roster_token',repeat('a',64),'records','{records()}'::jsonb));",'invalid_parameter_value')+"SELECT 'denied';",['denied'])
    def test_repeatable_read_write_and_status_are_rejected(self):
        call=save(token="repeat('a',64)")
        base=f"BEGIN ISOLATION LEVEL REPEATABLE READ; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{A}',true);"
        self.check(denied(f"PERFORM {call};",'active_sql_transaction')+"SELECT 'denied';",['denied'],base)
    def test_sessions_tied_cursor_50_1_and_local_day_boundaries(self):
        self.check(f"""RESET ROLE; DELETE FROM public.schedule_sessions;
INSERT INTO public.schedule_sessions(id,workspace_id,batch_id,starts_at,ends_at,created_by,creation_request_id)
SELECT md5('session-page-'||g)::uuid,'{W}','{T}','2026-11-10 10:00Z'::timestamptz,'2026-11-10 11:00Z'::timestamptz,'{A}',gen_random_uuid() FROM generate_series(1,51) g;
SET ROLE authenticated;
CREATE TEMP TABLE page AS SELECT public.app_today_sessions('{W}','2026-11-10') p;
SELECT jsonb_array_length(p->'sessions') FROM page;
SELECT jsonb_array_length(public.app_today_sessions('{W}','2026-11-10',(SELECT (p#>>'{{next,starts_at}}')::timestamptz FROM page),(SELECT (p#>>'{{next,id}}')::uuid FROM page))->'sessions');
""",['50','1'])
    def test_dst_separate_midnights_and_cross_midnight_appears_once(self):
        self.check(f"""RESET ROLE; UPDATE public.workspaces SET scheduling_time_zone='America/New_York' WHERE id='{W}'; DELETE FROM public.schedule_sessions;
INSERT INTO public.schedule_sessions(workspace_id,batch_id,starts_at,ends_at,created_by,creation_request_id) VALUES
('{W}','{T}','2026-11-01 04:00Z','2026-11-01 05:00Z','{A}',gen_random_uuid()),
('{W}','{T}','2026-11-02 04:30Z','2026-11-02 05:30Z','{A}',gen_random_uuid()),
('{W}','{T}','2026-11-02 05:00Z','2026-11-02 06:00Z','{A}',gen_random_uuid());
SET ROLE authenticated; SELECT jsonb_array_length(public.app_today_sessions('{W}','2026-11-01')->'sessions'); SELECT jsonb_array_length(public.app_today_sessions('{W}','2026-11-02')->'sessions');
""",['2','1'])
    def test_invalid_dates_and_half_cursor_and_zone_fail_closed(self):
        self.check(denied(f"PERFORM public.app_today_sessions('{W}',NULL);",'invalid_parameter_value')+denied(f"PERFORM public.app_today_sessions('{W}','infinity');",'invalid_parameter_value')+denied(f"PERFORM public.app_today_sessions('{W}','1999-12-31');",'invalid_parameter_value')+denied(f"PERFORM public.app_today_sessions('{W}','2026-11-10',clock_timestamp(),NULL);",'invalid_parameter_value')+f"RESET ROLE; UPDATE public.workspaces SET scheduling_time_zone=NULL WHERE id='{W}'; SET ROLE authenticated;"+denied(f"PERFORM {sheet()};",'invalid_parameter_value')+"SELECT 'denied';",['denied'])
    def test_academy_navigation_pages_50_1_and_coach_without_assignments(self):
        self.check(f"""RESET ROLE;
INSERT INTO public.workspaces(id,name,type,created_by,creation_request_id,scheduling_time_zone) SELECT md5('academy-page-'||g)::uuid,'Academy '||g,'academy','{A}',gen_random_uuid(),'UTC' FROM generate_series(1,50) g;
INSERT INTO public.workspace_memberships(workspace_id,user_id,role,status) SELECT md5('academy-page-'||g)::uuid,'{A}','coach','active' FROM generate_series(1,50) g;
SET ROLE authenticated; CREATE TEMP TABLE page AS SELECT public.app_today_academies() p; SELECT jsonb_array_length(p->'academies') FROM page;
SELECT jsonb_array_length(public.app_today_academies((SELECT (p->>'next_after')::uuid FROM page))->'academies');
SELECT jsonb_array_length(public.app_today_sessions(md5('academy-page-1')::uuid,'2026-11-10')->'sessions');
""",['50','1','0'])
    def test_another_authorized_actor_cannot_reuse_request(self):
        self.check(f"SELECT {save()}; RESET ROLE; INSERT INTO public.workspace_memberships(workspace_id,user_id,role,status) VALUES('{W}','{D}','admin','active'); SET ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{D}',true);"+denied(f"PERFORM {save()};",'unique_violation')+"SELECT 'denied';",['denied'])
    def test_roster_exact_pairs_and_empty_roster_cannot_create_sheet(self):
        self.check(denied(f"PERFORM public.app_save_attendance('{W}','{S}',1,0,{sheet()}->>'roster_token','[{{\"enrollment_id\":\"{E}\",\"child_id\":\"{T}\",\"status\":\"present\"}}]','{R}');",'insufficient_privilege')+f"RESET ROLE; UPDATE public.enrollments SET status='paused'; SET ROLE authenticated; SELECT jsonb_array_length({sheet()}->'rows');"+denied(f"PERFORM public.app_save_attendance('{W}','{S}',1,0,{sheet()}->>'roster_token','[]','{R}');",'invalid_parameter_value')+"RESET ROLE; SELECT count(*) FROM public.attendance_sheets;",['0','0'])
    def test_response_timestamps_are_utc_even_when_caller_zone_differs(self):
        self.check(f"SET LOCAL TIME ZONE 'Asia/Kolkata'; SELECT ({save()}->>'saved_at') ~ '(\\+00:00|Z)$';",['t'])
    def test_clock_helper_is_real_time_invoker_and_fully_private(self):
        self.assertEqual(run_sql("SELECT NOT prosecdef AND NOT has_function_privilege('authenticated',oid,'EXECUTE') AND NOT has_function_privilege('anon',oid,'EXECUTE') FROM pg_proc WHERE oid='public.attendance_clock()'::regprocedure; SELECT abs(extract(epoch from(public.attendance_clock()-pg_catalog.clock_timestamp())))<1;"),'t\nt')
        self.check(denied("PERFORM public.attendance_clock();")+denied("EXECUTE 'CREATE OR REPLACE FUNCTION public.attendance_clock() RETURNS timestamptz LANGUAGE sql AS $body$ SELECT pg_catalog.clock_timestamp() $body$';")+"SELECT 'denied';",['denied'])
    def test_failed_multirow_correction_preserves_full_snapshots_and_same_key_retry(self):
        """I1 fills a coverage gap; existing SQL is expected to remain atomic."""
        # A successful RPC without the injector must fail this assertion helper.
        with self.assertRaisesRegex(AssertionError,'Expected injected failure was not observed'):
            self.check(injected_failure(f"PERFORM {save()};",'synthetic correction failure'),['unreachable'])
        initial=[dict(enrollment_id=E,child_id=C,status='present'),dict(enrollment_id=E2,child_id=C2,status='late'),dict(enrollment_id=E3,child_id=C3,status='excused')]
        active=initial[:2]
        correction=[dict(enrollment_id=E,child_id=C,status='absent'),dict(enrollment_id=E2,child_id=C2,status='make_up')]
        request='f0000000-0000-4000-8000-000000000003'
        for table in ['attendance_records','attendance_record_events','parent_items','attendance_request_receipts']:
            with self.subTest(table=table):
                # Fail on the second row (or the final receipt), after prior work.
                condition=f"NEW.request_id='{request}'" if table=='attendance_request_receipts' else f"NEW.child_id='{C2}'"
                call=save_records(correction,2,request,token="(SELECT token FROM correction_input)")
                setup=extra_children()+f"CREATE TEMP TABLE first_receipt AS SELECT {save_records(initial)} r; SELECT * FROM public.app_change_enrollment('{E3}','paused',1,'other',gen_random_uuid()); CREATE TEMP TABLE second_receipt AS SELECT {save_records(active,1,R2)} r; CREATE TEMP TABLE correction_input AS SELECT {sheet()}->>'roster_token' token; RESET ROLE;"
                setup+=capture_snapshot('before_correction')
                setup+=f"CREATE FUNCTION pg_temp.fail_correction() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF {condition} THEN RAISE EXCEPTION 'synthetic correction failure'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_correction BEFORE INSERT ON public.{table} FOR EACH ROW EXECUTE FUNCTION pg_temp.fail_correction(); SET ROLE authenticated;"
                reject=injected_failure(f"PERFORM {call};",'synthetic correction failure')+'RESET ROLE;'+snapshot_unchanged('before_correction')
                reject+=f"SELECT NOT EXISTS(SELECT 1 FROM public.attendance_request_receipts WHERE request_id='{request}'); DROP TRIGGER fail_correction ON public.{table}; SET ROLE authenticated; CREATE TEMP TABLE retry_receipt AS SELECT {call} r; CREATE TEMP TABLE replay_receipt AS SELECT {call} r; SELECT a.r=b.r AND (a.r->>'sheet_version')::integer=3 FROM retry_receipt a CROSS JOIN replay_receipt b; RESET ROLE;"
                verify=f"SELECT count(*) FROM public.attendance_request_receipts WHERE request_id='{request}'; SELECT (SELECT version FROM public.attendance_sheets)||':'||(SELECT count(*) FROM public.attendance_records)||':'||(SELECT count(*) FROM public.attendance_record_events)||':'||(SELECT count(*) FROM public.parent_items)||':'||(SELECT count(*) FROM public.attendance_request_receipts);"
                verify+=f"SELECT to_jsonb(r)=(SELECT value FROM before_correction,jsonb_array_elements(data->'attendance_records') WHERE value->>'enrollment_id'='{E3}') FROM public.attendance_records r WHERE enrollment_id='{E3}'; SELECT bool_and(i.id=(old->>'id')::uuid AND i.created_at=(old->>'created_at')::timestamptz) FROM public.parent_items i JOIN (SELECT value old FROM before_correction,jsonb_array_elements(data->'parent_items')) o ON i.child_id=(old->>'child_id')::uuid;"
                self.check(setup+reject+verify,['t','t','t','1','3:3:7:3:3','t','t'])

    def test_valid_extreme_academy_local_dates_open_and_save_sheet(self):
        for zone,local in [('Pacific/Kiritimati','2000-01-01 00:30'),('America/Los_Angeles','2100-12-31 23:30')]:
            with self.subTest(zone=zone):
                date=local[:10]
                self.check(f"RESET ROLE; UPDATE public.workspaces SET scheduling_time_zone='{zone}' WHERE id='{W}'; UPDATE public.schedule_sessions SET starts_at='{local}'::timestamp AT TIME ZONE '{zone}',ends_at=('{local}'::timestamp AT TIME ZONE '{zone}')+interval '1 hour'; SET ROLE authenticated; SELECT jsonb_array_length(public.app_today_sessions('{W}','{date}')->'sessions'); SELECT {sheet()}->>'sheet_version'; SELECT {save_records([dict(enrollment_id=E,child_id=C,status='present')],session_version=2)}->>'sheet_version'; RESET ROLE; SELECT payload->>'date' FROM public.parent_items;",['1','0','1',date])

    def test_session_sheet_and_save_reject_dates_outside_academy_local_range(self):
        for zone,local in [('Pacific/Kiritimati','1999-12-31 23:30'),('America/Los_Angeles','1999-12-31 23:30'),('Pacific/Kiritimati','2101-01-01 00:30'),('America/Los_Angeles','2101-01-01 00:30')]:
            with self.subTest(zone=zone):
                call=save_records([dict(enrollment_id=E,child_id=C,status='present')],session_version=2,token='(SELECT token FROM original_scope)')
                self.check(f"CREATE TEMP TABLE original_scope AS SELECT {sheet()}->>'roster_token' token; RESET ROLE; UPDATE public.workspaces SET scheduling_time_zone='{zone}' WHERE id='{W}'; UPDATE public.schedule_sessions SET starts_at='{local}'::timestamp AT TIME ZONE '{zone}',ends_at=('{local}'::timestamp AT TIME ZONE '{zone}')+interval '1 hour'; SET ROLE authenticated;"+denied(f"PERFORM {sheet()};",'invalid_parameter_value')+denied(f"PERFORM {call};",'invalid_parameter_value')+"RESET ROLE; SELECT count(*) FROM public.attendance_sheets;",['0'])
    def test_shared_denial_helper_rejects_success_when_expect_raise_exception(self):
        with self.assertRaisesRegex(AssertionError,'unexpected success'):
            run_sql('BEGIN;'+denied('PERFORM 1;','raise_exception')+'ROLLBACK;')
