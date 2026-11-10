"""Synthetic attendance contract fixtures; every ordinary test rolls back."""
import json
import unittest
from tests.database.test_authorization import run_sql
from tests.database.test_enrollments import A,B,D,W,W2,C,T,T2,R,R2,BASE as ENROLLMENT_BASE
from tests.database.test_family_invitations import denied
S='90000000-0000-4000-8000-000000000001'
E='91000000-0000-4000-8000-000000000001'
BASE=ENROLLMENT_BASE.replace('SET LOCAL ROLE authenticated;',f"""
UPDATE public.workspaces SET scheduling_time_zone='UTC' WHERE id='{W}';
INSERT INTO public.enrollments(id,workspace_id,batch_id,child_id,created_by) VALUES('{E}','{W}','{T}','{C}','{A}');
INSERT INTO public.schedule_sessions(id,workspace_id,batch_id,starts_at,ends_at,created_by,creation_request_id)
VALUES('{S}','{W}','{T}',date_trunc('day',clock_timestamp())+interval '10 hours',date_trunc('day',clock_timestamp())+interval '11 hours','{A}',gen_random_uuid());
SET LOCAL ROLE authenticated;""")
def sheet():return f"public.app_attendance_sheet('{W}','{S}')"
def records(status='present'):return json.dumps([dict(enrollment_id=E,child_id=C,status=status)])
def save(status='present',version=0,request=R,token=None):
    token=token or f"({sheet()}->>'roster_token')"
    return f"public.app_save_attendance('{W}','{S}',1,{version},{token},'{records(status)}'::jsonb,'{request}')"
def parent():return f"SELECT set_config('request.jwt.claim.sub','{B}',true);"
class AttendanceCase(unittest.TestCase):
    def check(self,sql,expected,base=BASE):
        out=run_sql(base+sql+'\nROLLBACK;').splitlines()
        self.assertEqual(out[-len(expected):],expected)

C2='d0000000-0000-4000-8000-000000000002'
C3='d0000000-0000-4000-8000-000000000003'
E2='91000000-0000-4000-8000-000000000002'
E3='91000000-0000-4000-8000-000000000003'

def extra_children(children=((C2,E2,B),(C3,E3,B))):
    """Retained synthetic identities; caller starts/ends in authenticated role."""
    sql='RESET ROLE;'
    for child,enrollment,actor in children:
        sql+=f"""INSERT INTO public.children(id,display_name,created_by) VALUES('{child}','Additional fictional child','{actor}');
INSERT INTO public.guardianships(child_id,guardian_user_id) VALUES('{child}','{actor}');
INSERT INTO public.workspace_children(workspace_id,child_id) VALUES('{W}','{child}');
INSERT INTO public.enrollments(id,workspace_id,batch_id,child_id,created_by) VALUES('{enrollment}','{W}','{T}','{child}','{A}');
"""
    return sql+'SET ROLE authenticated;'

def save_records(data,version=0,request=R,token=None,session_version=1):
    token=token or f"({sheet()}->>'roster_token')"
    return f"public.app_save_attendance('{W}','{S}',{session_version},{version},{token},'{json.dumps(data)}'::jsonb,'{request}')"

ATTENDANCE_SNAPSHOT_TABLES={
    'attendance_sheets':'session_id',
    'attendance_records':'session_id,enrollment_id',
    'attendance_record_events':'session_id,enrollment_id,sheet_version,id',
    'parent_items':'id',
    'attendance_request_receipts':'request_id',
}
SIGNAL_SNAPSHOT_TABLES={**ATTENDANCE_SNAPSHOT_TABLES,
    'parent_signals':'id','parent_signal_request_receipts':'request_id'}

def full_snapshot(tables=ATTENDANCE_SNAPSHOT_TABLES):
    """Full persisted rows, ordered by keys independently of mutation logic."""
    fields=[]
    for table,order in tables.items():
        fields.extend([f"'{table}'",f"coalesce((SELECT jsonb_agg(to_jsonb(x) ORDER BY {order}) FROM public.{table} x WHERE workspace_id='{W}'),'[]'::jsonb)"])
    return 'jsonb_build_object('+','.join(fields)+')'

def capture_snapshot(name,tables=ATTENDANCE_SNAPSHOT_TABLES):
    return f"CREATE TEMP TABLE {name} AS SELECT data,data::text bytes,encode(sha256(convert_to(data::text,'UTF8')),'hex') fingerprint FROM (SELECT {full_snapshot(tables)} data) snapshot;"

def snapshot_unchanged(name,tables=ATTENDANCE_SNAPSHOT_TABLES):
    return f"SELECT data=(SELECT data FROM {name}) AND data::text=(SELECT bytes FROM {name}) AND encode(sha256(convert_to(data::text,'UTF8')),'hex')=(SELECT fingerprint FROM {name}) FROM (SELECT {full_snapshot(tables)} data) snapshot;"

def injected_failure(sql,message):
    """Require the injector's actual error; never catch our success assertion."""
    return f"""DO $$ DECLARE observed boolean:=false; BEGIN
 BEGIN {sql}
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'{message}' THEN RAISE; END IF;
  observed:=true;
 END;
 IF NOT observed THEN RAISE EXCEPTION 'Expected injected failure was not observed'; END IF;
END $$;
"""
