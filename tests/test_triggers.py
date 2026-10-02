import json
import os
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from dispatch import dispatch
from triggers import payload, SOURCES, trigger_info, current_trigger
from revisions import manifest
from site_fixtures import sources

SHA = "1" * 40


class TriggerTests(unittest.TestCase):
    def test_all_three_offline_requests_match_receiver_event_types(self):
        workflow = yaml.load((ROOT / ".github/workflows/deploy-pages.yml").read_text(), Loader=yaml.BaseLoader)
        configured = set(workflow["on"]["repository_dispatch"]["types"])
        types = set()
        for source in ("atlas", "local-ai", "hollow-square"):
            with patch("dispatch.request", side_effect=AssertionError("Offline must not contact GitHub")):
                receipt = dispatch(source, SHA, "fixture-verify", False)
            self.assertFalse(receipt["accepted"])
            self.assertEqual(receipt["receiver"], "jjjhenriksen/shapenote-site")
            body = receipt["request"]
            types.add(body["event_type"])
            info = trigger_info("repository_dispatch", {"action": body["event_type"], "client_payload": body["client_payload"]})
            self.assertEqual(info["requested_commit"], SHA)
            self.assertEqual(info["verification_id"], "fixture-verify")
        self.assertEqual(types, configured)

    def test_send_resolves_main_before_post_and_emits_only_safe_metadata(self):
        with patch("dispatch.request", side_effect=[json.dumps({"sha": SHA}), ""]) as request:
            receipt = dispatch("atlas", None, "test-verify", True)
        self.assertTrue(receipt["accepted"])
        self.assertEqual(request.call_args_list[0].args[0], ["repos/jjjhenriksen/shapenote-atlas/commits/main"])
        self.assertEqual(request.call_args_list[1].args[1], payload("atlas", SHA, "test-verify"))

    def test_stale_requested_revision_is_not_sent(self):
        with patch("dispatch.request", return_value=json.dumps({"sha": SHA})) as request:
            with self.assertRaisesRegex(ValueError, "current source main"):
                dispatch("atlas", "2" * 40, "test", True)
        self.assertEqual(request.call_count, 1)

    def test_unknown_source_or_invalid_identity_is_not_sent(self):
        with patch("dispatch.request", side_effect=AssertionError("Must not send")):
            for source, sha, identity in (("unknown", SHA, "test"), ("atlas", "short", "test"),
                                          ("atlas", SHA, "private text with spaces")):
                with self.subTest(source=source, sha=sha), self.assertRaises(ValueError):
                    dispatch(source, sha, identity, False)

    def test_legacy_empty_payload_and_unrelated_events_are_bounded(self):
        info = trigger_info("repository_dispatch", {"action": "local-ai-updated", "client_payload": {}})
        self.assertIsNone(info["requested_commit"])
        self.assertEqual(trigger_info("push", {"private": "FAKE-PRIVATE"}), {"event": "push"})
        info = trigger_info("repository_dispatch", {"action": "atlas-updated", "client_payload": {
            **payload("atlas", SHA, "test")["client_payload"], "instruction": "FAKE-PRIVATE do something else"}})
        self.assertNotIn("FAKE-PRIVATE", json.dumps(info))

    def test_invalid_receiver_metadata_fails_without_echoing_it(self):
        for body in ([], None, "private", {"repository": "FAKE-TOKEN"}, {"sha": "short"}, {"verification_id": "FAKE-PRIVATE text"}):
            with self.subTest(body=body), self.assertRaises(ValueError) as context:
                trigger_info("repository_dispatch", {"action": "atlas-updated", "client_payload": body})
            self.assertNotIn("FAKE-TOKEN", str(context.exception))
            self.assertNotIn("FAKE-PRIVATE", str(context.exception))

    def test_dispatch_event_is_retained_in_assembled_manifest_without_raw_private_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkouts = sources(root)
            event = root / "event.json"
            body = payload("hollow-square", SHA, "fixture-receipt")
            event.write_text(json.dumps({"action": body["event_type"], "sender": "FAKE-PRIVATE",
                                         "client_payload": body["client_payload"]}))
            with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "repository_dispatch", "GITHUB_EVENT_PATH": str(event)}):
                data = manifest(dict(zip(("hub", "atlas", "local_ai", "hollow_square"), checkouts)), True, False)
            self.assertEqual(data["trigger"]["verification_id"], "fixture-receipt")
            self.assertEqual(data["trigger"]["requested_commit"], SHA)
            self.assertNotIn("FAKE-PRIVATE", json.dumps(data))

    def test_non_dispatch_does_not_read_event_file(self):
        with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "pull_request", "GITHUB_EVENT_PATH": "/not/a/file"}):
            self.assertEqual(current_trigger(), {"event": "pull_request"})


if __name__ == "__main__":
    unittest.main()
