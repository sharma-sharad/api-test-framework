import unittest

from src.api_tester.comparison import compare_api_results, diff_json, format_path, summarize_differences


class ComparisonTests(unittest.TestCase):
    def test_compares_same_testcase_pair_response_and_status(self):
        old = {"status_code": 200, "response_text": '{"id": 1, "status": "OPEN"}', "elapsed_ms": 100}
        new = {"status_code": 200, "response_text": '{"status": "OPEN", "id": 1}', "elapsed_ms": 90}

        result = compare_api_results(old, new)

        self.assertTrue(result["status_match"])
        self.assertTrue(result["response_match"])
        self.assertTrue(result["performance_match"])
        self.assertTrue(result["overall_pass"])
        self.assertEqual(result["differences"], {})

    def test_detects_exact_response_difference(self):
        old = {"id": 1, "status": "OPEN", "amount": 100}
        new = {"id": 1, "status": "CLOSED", "currency": "USD"}

        differences = diff_json(old, new)

        self.assertIn("root['amount']", differences["dictionary_item_removed"])
        self.assertIn("root['currency']", differences["dictionary_item_added"])
        self.assertEqual(
            differences["values_changed"]["root['status']"],
            {"new_value": "CLOSED", "old_value": "OPEN"},
        )

    def test_formats_deepdiff_path_for_qa_readability(self):
        self.assertEqual(
            format_path("root['claim']['payments'][0]['amount']"),
            "claim > payments > record 1 > amount",
        )

    def test_detects_nested_response_difference_with_deepdiff_paths(self):
        old = {
            "claim": {
                "id": 101,
                "status": "OPEN",
                "payments": [{"id": 1, "amount": 50}, {"id": 2, "amount": 75}],
            }
        }
        new = {
            "claim": {
                "id": 101,
                "status": "CLOSED",
                "payments": [{"id": 1, "amount": 55}, {"id": 2, "amount": 75}],
            }
        }

        result = compare_api_results(
            {"status_code": 200, "response_text": json_dump(old), "elapsed_ms": 100},
            {"status_code": 200, "response_text": json_dump(new), "elapsed_ms": 100},
        )

        self.assertFalse(result["response_match"])
        self.assertFalse(result["overall_pass"])
        self.assertEqual(
            result["differences"]["values_changed"]["root['claim']['status']"],
            {"new_value": "CLOSED", "old_value": "OPEN"},
        )
        self.assertEqual(
            result["differences"]["values_changed"]["root['claim']['payments'][0]['amount']"],
            {"new_value": 55, "old_value": 50},
        )
        self.assertIn(
            'For claim, field status changed from "OPEN" in old API to "CLOSED" in new API.',
            result["differences_summary"],
        )
        self.assertIn(
            "For claim > payments > record 1, field amount changed from 50 in old API to 55 in new API.",
            result["differences_summary"],
        )

    def test_status_mismatch_fails_overall_even_when_body_matches(self):
        old = {"status_code": 200, "response_text": '{"ok": true}', "elapsed_ms": 100}
        new = {"status_code": 500, "response_text": '{"ok": true}', "elapsed_ms": 100}

        result = compare_api_results(old, new)

        self.assertFalse(result["status_match"])
        self.assertTrue(result["response_match"])
        self.assertFalse(result["overall_pass"])

    def test_can_ignore_array_order_for_nested_payloads(self):
        old = {
            "claim": {
                "payments": [
                    {"id": 1, "amount": 50},
                    {"id": 2, "amount": 75},
                ]
            }
        }
        new = {
            "claim": {
                "payments": [
                    {"id": 2, "amount": 75},
                    {"id": 1, "amount": 50},
                ]
            }
        }

        ordered_result = compare_api_results(
            {"status_code": 200, "response_text": json_dump(old), "elapsed_ms": 100},
            {"status_code": 200, "response_text": json_dump(new), "elapsed_ms": 100},
        )
        ignored_order_result = compare_api_results(
            {"status_code": 200, "response_text": json_dump(old), "elapsed_ms": 100},
            {"status_code": 200, "response_text": json_dump(new), "elapsed_ms": 100},
            ignore_order=True,
        )

        self.assertFalse(ordered_result["response_match"])
        self.assertTrue(ignored_order_result["response_match"])
        self.assertEqual(ignored_order_result["differences"], {})

    def test_summarizes_added_and_removed_fields_for_qa(self):
        differences = diff_json(
            {"claim": {"amount": 100, "status": "OPEN"}},
            {"claim": {"status": "OPEN", "currency": "USD"}},
        )

        summary = summarize_differences(differences)

        self.assertIn(
            "Field amount existed under claim in old API but is missing in new API. Old API value was 100.",
            summary,
        )
        self.assertIn(
            'In new API, field currency was added under claim with value "USD".',
            summary,
        )

    def test_summarizes_added_and_removed_list_records_for_qa(self):
        differences = diff_json(
            {"claim": {"payments": [{"id": 1, "amount": 40}]}},
            {
                "claim": {
                    "payments": [
                        {"id": 1, "amount": 40},
                        {"id": 2, "amount": 50},
                    ]
                }
            },
        )

        summary = summarize_differences(differences)

        self.assertIn(
            'New API added claim > payments > record 2 with value {"amount": 50, "id": 2}.',
            summary,
        )


def json_dump(value):
    import json

    return json.dumps(value)


if __name__ == "__main__":
    unittest.main()
