import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from site_fixtures import sources

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from assemble import assemble
from revisions import git, manifest


class RevisionTests(unittest.TestCase):
    def test_manifest_has_exact_four_commits_and_build_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hub, atlas, ai, hollow = sources(root)
            output = assemble(hub, atlas, ai, hollow, root / "site", atlas_built=True)
            data = json.loads((output / "build-manifest.json").read_text())
            self.assertEqual(set(data["sources"]), {"hub", "atlas", "local_ai", "hollow_square"})
            for key, path in zip(("hub", "atlas", "local_ai", "hollow_square"), (hub, atlas, ai, hollow)):
                self.assertEqual(data["sources"][key]["commit"], git(path, "rev-parse", "HEAD"))
                self.assertFalse(data["sources"][key]["dirty"])
            self.assertEqual(data["build"]["atlas_base"], "/atlas/")
            self.assertEqual(data["build"]["atlas_mode"], "prebuilt-unverified")

    def test_dirty_sources_are_refused_or_explicitly_labeled(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub, atlas, ai, hollow = sources(Path(tmp))
            (hub / "styles.css").write_text("User modification")
            roots = dict(zip(("hub", "atlas", "local_ai", "hollow_square"), (hub, atlas, ai, hollow)))
            with self.assertRaisesRegex(ValueError, "uncommitted"):
                manifest(roots, False, False)
            data = manifest(roots, False, True)
            self.assertTrue(data["sources"]["hub"]["dirty"])
            self.assertFalse(data["build"]["clean_source_revisions"])
            self.assertEqual((hub / "styles.css").read_text(), "User modification")

    def test_actions_nested_checkouts_are_separate_clean_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub, atlas, ai, hollow = sources(Path(tmp))
            nested = []
            for path in (atlas, ai, hollow):
                destination = hub / (path.name + "-source")
                shutil.move(path, destination)
                nested.append(destination)
            data = manifest(dict(zip(("hub", "atlas", "local_ai", "hollow_square"), (hub, *nested))), True, False)
            self.assertTrue(data["build"]["clean_source_revisions"])
            (nested[1] / "presentation/index.html").write_text("Changed source")
            with self.assertRaisesRegex(ValueError, "local_ai has uncommitted"):
                manifest(dict(zip(("hub", "atlas", "local_ai", "hollow_square"), (hub, *nested))), True, False)

    def test_wrong_or_credential_bearing_remote_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub, atlas, ai, hollow = sources(Path(tmp))
            subprocess.run(["git", "-C", str(atlas), "remote", "set-url", "origin", "https://fake:FAKE-TOKEN@example.invalid/repo.git"], check=True)
            with self.assertRaises(ValueError) as context:
                manifest(dict(zip(("hub", "atlas", "local_ai", "hollow_square"), (hub, atlas, ai, hollow))), True, False)
            self.assertNotIn("FAKE-TOKEN", str(context.exception))


if __name__ == "__main__":
    unittest.main()
