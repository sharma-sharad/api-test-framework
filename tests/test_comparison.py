import unittest

from src.api_tester.comparison import compare_api_results, diff_json


class ComparisonTests(unittest.TestCase):
    def test_compares_same_testcase_pair_response_and_status(self):
        old = {"status_code": 200, "response_text": '{"id": 1, "status": "OPEN"}', "elapsed_ms": 100}
        new = {"status_code": 200, "response_text": '{"status": "OPEN", "id": 1}', "elapsed_ms": 90}

        result = compare_api_results(old, new)

        self.assertTrue(result["status_match"])
        self.assertTrue(result["response_match"])
        self.assertTrue(result["performance_match"])
        self.assertTrue(result["overall_pass"])
        self.assertEqual(result["differences"], [])

    def test_detects_exact_response_difference(self):
        old = {"id": 1, "status": "OPEN", "amount": 100}
        new = {"id": 1, "status": "CLOSED", "currency": "USD"}

        differences = diff_json(old, new)

        self.assertIn({"path": "$.amount", "type": "removed", "old": 100, "new": None}, differences)
        self.assertIn({"path": "$.currency", "type": "added", "old": None, "new": "USD"}, differences)
        self.assertIn({"path": "$.status", "type": "changed", "old": "OPEN", "new": "CLOSED"}, differences)

    def test_status_mismatch_fails_overall_even_when_body_matches(self):
        old = {"status_code": 200, "response_text": '{"ok": true}', "elapsed_ms": 100}
        new = {"status_code": 500, "response_text": '{"ok": true}', "elapsed_ms": 100}

        result = compare_api_results(old, new)

        self.assertFalse(result["status_match"])
        self.assertTrue(result["response_match"])
        self.assertFalse(result["overall_pass"])


if __name__ == "__main__":
    unittest.main()
