"""Baseline permissions for the unreleased connection journey."""

import unittest

from tests.database.test_concurrent_authorization import MEERA, query


class ConnectionExposureTests(unittest.TestCase):
    def test_unreleased_connection_functions_deny_application_roles(self):
        result = query("""
SELECT r.role_name,
       has_function_privilege(r.role_name, 'public.request_workspace_connection(uuid,uuid,uuid)', 'EXECUTE'),
       has_function_privilege(r.role_name, 'public.approve_guardian_connection(uuid)', 'EXECUTE')
FROM (VALUES ('anon'),('authenticated')) AS r(role_name) ORDER BY r.role_name;
""")
        self.assertEqual(result.splitlines(), ["anon|f|f", "authenticated|f|f"])
        for call in (
            "SELECT public.request_workspace_connection(NULL,NULL,NULL);",
            "SELECT public.approve_guardian_connection(NULL);",
        ):
            with self.subTest(call=call), self.assertRaisesRegex(AssertionError, "permission denied for function"):
                query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); {call} COMMIT;")
