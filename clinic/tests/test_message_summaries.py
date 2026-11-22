import json
from unittest.mock import patch

from django.test import TestCase

from clinic.message_summaries import MessageSummaryError, group_thread_summaries, summarize_threads
from clinic.testing import make_patient, make_provider, make_thread


class MessageSummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.provider = make_provider()
        cls.patient = make_patient(provider=cls.provider)

    @patch("clinic.message_summaries.gemini.generate_text")
    def test_summarizes_thread_and_validates_ai_result(self, generate_text):
        thread = make_thread(patient=self.patient, category="clinical", body="My knee hurts.")
        generate_text.return_value = json.dumps(
            {"threads": [{"thread_id": thread.pk, "urgency": "urgent", "summary": "Patient reports knee pain."}]}
        )

        result = summarize_threads([thread])

        self.assertEqual(result[thread.pk], {"urgency": "urgent", "summary": "Patient reports knee pain."})
        self.assertIn("My knee hurts.", generate_text.call_args.args[0])
        self.assertNotIn(self.patient.full_name, generate_text.call_args.args[0])

    @patch(
        "clinic.message_summaries.gemini.generate_text",
        return_value='{"threads":[{"thread_id":999,"urgency":"routine","summary":"Summary"}]}',
    )
    def test_rejects_results_for_wrong_thread(self, _generate_text):
        thread = make_thread(patient=self.patient)
        with self.assertRaises(MessageSummaryError):
            summarize_threads([thread])

    def test_groups_by_issue_and_assigned_doctor(self):
        clinical = make_thread(patient=self.patient, category="clinical")
        billing = make_thread(patient=self.patient, category="billing")
        summaries = {
            clinical.pk: {"urgency": "routine", "summary": "Clinical summary."},
            billing.pk: {"urgency": "urgent", "summary": "Billing summary."},
        }

        groups = group_thread_summaries([clinical, billing], summaries)

        self.assertEqual([group["issue"] for group in groups], ["Billing and insurance", "Medical question"])
        self.assertEqual(groups[0]["doctor"], "Unassigned")
        self.assertEqual(groups[1]["doctor"], self.provider.display_name)
        self.assertEqual(groups[0]["items"][0]["badge_class"], "badge-warning")
