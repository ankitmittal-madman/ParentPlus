"""Parent navigation, typed parcels and exact weekly saved facts."""
from tests.database.attendance_fixtures import *
class ParentItemTests(AttendanceCase):
    def test_parent_navigation_returns_workspace_and_batch_ids(self):
        self.check(parent()+f"SELECT public.app_parent_academies('{C}')#>>'{{academies,0,workspace_id}}'; SELECT public.app_parent_batches('{C}','{W}')#>>'{{batches,0,batch_id}}';",[W,T])
    def test_saved_item_envelope_and_week_facts(self):
        self.check(f"SELECT {save()};"+parent()+f"SELECT public.app_parent_items('{C}','{W}')#>>'{{items,0,type}}'; SELECT public.app_parent_attendance_week('{C}','{W}',date_trunc('week',clock_timestamp())::date)->>'attended_count';",['attendance','1'])
    def test_other_parent_denied_even_for_unknown_item_type(self):
        self.check(f"SELECT {save()}; RESET ROLE; UPDATE public.parent_items SET type='future'; SET ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{D}',true);"+denied(f"PERFORM public.app_parent_items('{C}','{W}');")+"SELECT 'denied';",['denied'])
    def test_expired_items_are_excluded(self):
        self.check(f"SELECT {save()}; RESET ROLE; UPDATE public.parent_items SET expires_at=clock_timestamp()-interval '1 second'; SET ROLE authenticated;"+parent()+f"SELECT jsonb_array_length(public.app_parent_items('{C}','{W}')->'items');",['0'])
    def test_items_cursor_ties_and_envelope_exact_keys(self):
        self.check(f"SELECT {save()}; RESET ROLE; INSERT INTO public.parent_items(workspace_id,batch_id,child_id,enrollment_id,source_session_id,type,schema_version,created_at,updated_at,payload) SELECT '{W}','{T}','{C}','{E}','{S}','future-'||g,2,'2026-11-10 10:00Z','2026-11-10 10:00Z','{{}}' FROM generate_series(1,51) g; SET ROLE authenticated;"+parent()+f"CREATE TEMP TABLE page AS SELECT public.app_parent_items('{C}','{W}') p; SELECT jsonb_array_length(p->'items') FROM page; SELECT jsonb_array_length(public.app_parent_items('{C}','{W}',NULL,(SELECT (p#>>'{{next,created_at}}')::timestamptz FROM page),(SELECT (p#>>'{{next,id}}')::uuid FROM page))->'items'); SELECT string_agg(k,',' ORDER BY k) FROM page,jsonb_object_keys(p#>'{{items,0}}') k;",['50','2','child_id,class_id,created_at,expires_at,id,payload,priority,schema_version,type'])
    def test_unknown_item_base_authority_cannot_bypass_revoked_guardian(self):
        for mutation in ["UPDATE public.guardianships SET status='disputed'", "UPDATE public.children SET created_by='"+D+"'", "UPDATE public.workspaces SET status='suspended' WHERE id='"+W+"'", "UPDATE public.workspace_children SET status='alumni'"]:
            with self.subTest(mutation=mutation):self.check(f"SELECT {save()}; RESET ROLE; UPDATE public.parent_items SET type='future',schema_version=99; {mutation}; SET ROLE authenticated;"+parent()+denied(f"PERFORM public.app_parent_items('{C}','{W}');")+"SELECT 'denied';",['denied'])
    def test_week_exact_counts_beyond_fifty_detail_rows(self):
        self.check(f"""RESET ROLE;
INSERT INTO public.schedule_sessions(id,workspace_id,batch_id,starts_at,ends_at,created_by,creation_request_id)
SELECT md5('week-'||g)::uuid,'{W}','{T}','2026-11-09 10:00Z'::timestamptz,'2026-11-09 11:00Z'::timestamptz,'{A}',gen_random_uuid() FROM generate_series(1,51) g;
INSERT INTO public.attendance_sheets SELECT id,workspace_id,batch_id,1,1,repeat('a',64),1,'{A}',clock_timestamp() FROM public.schedule_sessions WHERE id<>'{S}';
INSERT INTO public.attendance_records(session_id,workspace_id,batch_id,enrollment_id,child_id,status,sheet_version,confirmed_by,confirmed_at)
SELECT id,workspace_id,batch_id,'{E}','{C}',CASE WHEN id=md5('week-1')::uuid THEN 'absent' ELSE 'late' END,1,'{A}',clock_timestamp() FROM public.schedule_sessions WHERE id<>'{S}';
SET ROLE authenticated;"""+parent()+f"CREATE TEMP TABLE week AS SELECT public.app_parent_attendance_week('{C}','{W}','2026-11-09') p; SELECT (p->>'attended_count')||':'||(p->>'recorded_count')||':'||jsonb_array_length(p->'rows')||':'||(p->>'has_more') FROM week;",['50:51:50:true'])
    def test_invalid_week_date_cursor_and_batch_fail_closed(self):
        self.check(parent()+denied(f"PERFORM public.app_parent_attendance_week('{C}','{W}','2026-11-10');",'invalid_parameter_value')+denied(f"PERFORM public.app_parent_items('{C}','{W}','{T2}');")+denied(f"PERFORM public.app_parent_items('{C}','{W}',NULL,'infinity',NULL);",'invalid_parameter_value')+"SELECT 'denied';",['denied'])
    def test_parent_batch_cursor_has_50_1_split_and_no_enrollment_id_substitution(self):
        self.check(f"RESET ROLE; INSERT INTO public.batches(id,workspace_id,course_id,name) SELECT md5('parent-page-'||g)::uuid,'{W}','c0000000-0000-4000-8000-000000000001','Batch '||g FROM generate_series(1,50) g; INSERT INTO public.enrollments(workspace_id,batch_id,child_id,created_by) SELECT '{W}',md5('parent-page-'||g)::uuid,'{C}','{A}' FROM generate_series(1,50) g; SET ROLE authenticated;"+parent()+f"CREATE TEMP TABLE page AS SELECT public.app_parent_batches('{C}','{W}') p; SELECT jsonb_array_length(p->'batches') FROM page; SELECT jsonb_array_length(public.app_parent_batches('{C}','{W}',(SELECT (p->>'next_after')::uuid FROM page))->'batches');",['50','1'])
    def test_parent_academy_navigation_pages_50_1(self):
        self.check(f"""RESET ROLE;
INSERT INTO public.workspaces(id,name,type,created_by,creation_request_id) SELECT md5('parent-academy-'||g)::uuid,'Academy '||g,'academy','{A}',gen_random_uuid() FROM generate_series(1,50) g;
INSERT INTO public.courses(id,workspace_id,name) SELECT md5('parent-course-'||g)::uuid,md5('parent-academy-'||g)::uuid,'Course' FROM generate_series(1,50) g;
INSERT INTO public.batches(id,workspace_id,course_id,name) SELECT md5('parent-batch-'||g)::uuid,md5('parent-academy-'||g)::uuid,md5('parent-course-'||g)::uuid,'Batch' FROM generate_series(1,50) g;
INSERT INTO public.workspace_children(workspace_id,child_id) SELECT md5('parent-academy-'||g)::uuid,'{C}' FROM generate_series(1,50) g;
INSERT INTO public.enrollments(workspace_id,batch_id,child_id,created_by) SELECT md5('parent-academy-'||g)::uuid,md5('parent-batch-'||g)::uuid,'{C}','{A}' FROM generate_series(1,50) g;
SET ROLE authenticated;"""+parent()+f"CREATE TEMP TABLE page AS SELECT public.app_parent_academies('{C}') p; SELECT jsonb_array_length(p->'academies') FROM page; SELECT jsonb_array_length(public.app_parent_academies('{C}',(SELECT (p->>'next_after')::uuid FROM page))->'academies');",['50','1'])
