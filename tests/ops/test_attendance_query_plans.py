"""The performance evidence must inspect the shipped storage queries, not copies."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]

class AttendanceQueryPlanTests(unittest.TestCase):
    def load(self):
        spec=importlib.util.spec_from_file_location('attendance_plans',ROOT/'scripts/ci/attendance-query-plans.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_extracts_five_shipped_queries_and_rejects_missing_or_ambiguous_source(self):
        module=self.load()
        source=(ROOT/'supabase/migrations/20261110005300_attendance_today.sql').read_text()
        queries=module.storage_queries(source)
        self.assertEqual(set(queries),{'sessions','roster','latest_signals','feed','weekly'})
        self.assertIn('limit 201',queries['roster'])
        self.assertIn('limit 51',queries['sessions'])
        self.assertIn('distinct on(s.child_id,s.actor_id)',queries['latest_signals'])
        for name in ('sessions','feed','weekly'):
            self.assertIn('p_workspace_id',queries[name])
        with self.assertRaisesRegex(ValueError,'query shape'):
            module.storage_queries(source.replace('with facts as(', 'with changed_facts as('))
        with self.assertRaisesRegex(ValueError,'query shape'):
            module.storage_queries(source+source)
