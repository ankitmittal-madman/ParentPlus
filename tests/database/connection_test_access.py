"""Temporary grants for legacy behavior tests in an isolated disposable DB only."""

from tests.database.test_concurrent_authorization import query


SIGNATURES = "public.request_workspace_connection(uuid,uuid,uuid), public.approve_guardian_connection(uuid)"


def grant_connection_test_access():
    state = query("""
SELECT has_function_privilege('authenticated', 'public.request_workspace_connection(uuid,uuid,uuid)', 'EXECUTE'),
       has_function_privilege('authenticated', 'public.approve_guardian_connection(uuid)', 'EXECUTE');
""")
    if state != "f|f":
        raise AssertionError("Connection test grants require a disabled baseline")
    query(f"GRANT EXECUTE ON FUNCTION {SIGNATURES} TO authenticated;")


def revoke_connection_test_access():
    query(f"REVOKE ALL ON FUNCTION {SIGNATURES} FROM authenticated;")
    state = query("""
SELECT has_function_privilege('authenticated', 'public.request_workspace_connection(uuid,uuid,uuid)', 'EXECUTE'),
       has_function_privilege('authenticated', 'public.approve_guardian_connection(uuid)', 'EXECUTE');
""")
    if state != "f|f":
        raise AssertionError("Connection test grants were not removed")
