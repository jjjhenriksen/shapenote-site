from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class WorkflowPolicyTests(unittest.TestCase):
    def test_pr_build_has_no_deployment_permissions_and_steps_are_executable(self):
        workflow = yaml.load((ROOT / ".github/workflows/deploy-pages.yml").read_text(), Loader=yaml.BaseLoader)
        self.assertIn("pull_request", workflow["on"])
        self.assertNotIn("pull_request_target", workflow["on"])
        build = workflow["jobs"]["build"]
        permissions = build.get("permissions", workflow["permissions"])
        self.assertEqual(permissions.get("pages", "none"), "none")
        self.assertEqual(permissions.get("id-token", "none"), "none")
        self.assertEqual(permissions.get("contents"), "read")
        for job in workflow["jobs"].values():
            for step in job["steps"]:
                self.assertEqual(sum(key in step for key in ("uses", "run")), 1)


if __name__ == "__main__":
    unittest.main()
