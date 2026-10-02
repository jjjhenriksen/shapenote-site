import importlib.util
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from site_fixtures import sources

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("assembly", ROOT / "scripts/assemble.py")
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


class AssemblyTests(unittest.TestCase):
    def test_layout_and_bytes_match_each_independent_source(self):
        with tempfile.TemporaryDirectory(prefix="assembly test ") as tmp:
            root = Path(tmp)
            hub, atlas, ai, hollow = sources(root)
            (hollow / "private.txt").write_text("Exclude")
            output = assembly.assemble(hub, atlas, ai, hollow, root / "site", atlas_built=True)
            self.assertEqual((output / "index.html").read_bytes(), (hub / "index.html").read_bytes())
            for published, original in (("atlas/assets/app.js", atlas / "dist/assets/app.js"),
                                        ("local-ai/image.webp", ai / "presentation/image.webp"),
                                        ("hollow-square/app.js", hollow / "app.js")):
                self.assertEqual((output / published).read_bytes(), original.read_bytes())
            self.assertFalse((output / "hollow-square/private.txt").exists())
            self.assertEqual({p.name for p in output.iterdir()},
                             {"index.html", "styles.css", "CNAME", ".nojekyll", "atlas", "local-ai", "hollow-square"})

    def test_preflight_and_build_failure_preserve_inputs_and_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hub, atlas, ai, hollow = sources(root)
            output = root / "site"
            output.mkdir()
            (output / "user.txt").write_text("Keep")
            with patch.object(assembly.subprocess, "run", side_effect=AssertionError("Must not build")):
                with self.assertRaises(FileExistsError):
                    assembly.assemble(hub, atlas, ai, hollow, output)
            self.assertEqual((output / "user.txt").read_text(), "Keep")
            with patch.object(assembly.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "npm")):
                with self.assertRaises(subprocess.CalledProcessError):
                    assembly.assemble(hub, atlas, ai, hollow, root / "failed")
            self.assertFalse((root / "failed").exists())
            (ai / "presentation/index.html").unlink()
            with self.assertRaisesRegex(ValueError, "Required regular file"):
                assembly.assemble(hub, atlas, ai, hollow, root / "missing", atlas_built=True)
            self.assertFalse((root / "missing").exists())

    def test_failed_staged_copy_does_not_publish_or_leave_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hub, atlas, ai, hollow = sources(root)
            (ai / "presentation/external.webp").symlink_to(root / "unrelated.webp")
            with self.assertRaisesRegex(ValueError, "symlink"):
                assembly.assemble(hub, atlas, ai, hollow, root / "site", atlas_built=True)
            self.assertFalse((root / "site").exists())
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["atlas", "hollow", "hub", "local-ai"])

    def test_output_inside_source_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub, atlas, ai, hollow = sources(Path(tmp))
            with self.assertRaisesRegex(ValueError, "outside"):
                assembly.assemble(hub, atlas, ai, hollow, atlas / "site", atlas_built=True)

    def test_cli_serves_all_production_subpaths(self):
        with tempfile.TemporaryDirectory(prefix="serve test ") as tmp:
            root = Path(tmp)
            hub, atlas, ai, hollow = sources(root)
            command = [sys.executable, str(ROOT / "scripts/assemble.py"), "--hub", str(hub),
                       "--atlas", str(atlas), "--local-ai", str(ai), "--hollow-square", str(hollow),
                       "--output", str(root / "site"), "--atlas-built", "--serve", "0"]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            lines = queue.Queue()
            def read_output():
                for line in process.stdout:
                    lines.put(line)
            thread = threading.Thread(target=read_output, daemon=True)
            thread.start()
            try:
                preview = None
                for _ in range(3):
                    line = lines.get(timeout=10)
                    match = re.search(r"http://127\.0\.0\.1:(\d+)/", line)
                    if match:
                        preview = f"http://127.0.0.1:{match.group(1)}"
                        break
                self.assertIsNotNone(preview)
                for route, expected in (("/", hub / "index.html"), ("/atlas/", atlas / "dist/index.html"),
                                        ("/atlas/assets/app.js", atlas / "dist/assets/app.js"),
                                        ("/local-ai/", ai / "presentation/index.html"),
                                        ("/hollow-square/", hollow / "index.html")):
                    with urlopen(preview + route, timeout=5) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.read(), expected.read_bytes())
            finally:
                process.terminate()
                process.wait(timeout=5)
                thread.join(timeout=5)
                process.stdout.close()
                process.stderr.close()


if __name__ == "__main__":
    unittest.main()
