import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hollow", ROOT / "scripts/copy_hollow.py")
hollow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hollow)


def fixture(root):
    for name in ("index.html", "styles.css", "app.js", "artwork.js", "harmony-data.js",
                 "marginalia.css", "marginalia.js",
                 "assets/fonts/Caveat-notes.woff2", "assets/fonts/Caveat-OFL.txt",
                 "assets/fonts/Caveat-SOURCE.txt",
                 "vendor/opensheetmusicdisplay.min.js", "vendor/opensheetmusicdisplay.min.js.LICENSE.txt"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"Required file: {name}\n")


class RuntimePublicationTests(unittest.TestCase):
    def test_copy_runtime_excludes_repository_and_development_files(self):
        with tempfile.TemporaryDirectory(prefix="publication test ") as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            fixture(source)
            for extra in (".git/config", "tests/game.spec.js", ".github/workflows/ci.yml",
                          "package.json", "package-lock.json", "playwright.config.js",
                          "node_modules/dependency/index.js", "test-results/private.log", "unrelated.txt"):
                path = source / extra
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Should never be published")
            hollow.copy_runtime(source, output)
            published = {str(p.relative_to(output)) for p in output.rglob("*") if p.is_file()}
            self.assertEqual(published, {"index.html", "styles.css", "app.js", "artwork.js", "harmony-data.js",
                 "marginalia.css", "marginalia.js",
                 "assets/fonts/Caveat-notes.woff2", "assets/fonts/Caveat-OFL.txt",
                 "assets/fonts/Caveat-SOURCE.txt",
                                        "vendor/opensheetmusicdisplay.min.js", "vendor/opensheetmusicdisplay.min.js.LICENSE.txt"})
            for name in published:
                self.assertEqual((source / name).read_bytes(), (output / name).read_bytes())

    def test_missing_vendor_is_rejected_before_creating_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            fixture(source)
            (source / "vendor/opensheetmusicdisplay.min.js").unlink()
            with self.assertRaisesRegex(ValueError, "Required runtime file missing"):
                hollow.copy_runtime(source, output)
            self.assertFalse(output.exists())

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source", Path(tmp) / "output"
            fixture(source)
            output.mkdir()
            user_file = output / "user.md"
            user_file.write_text("Preserve me")
            with self.assertRaises(FileExistsError):
                hollow.copy_runtime(source, output)
            self.assertEqual(list(output.iterdir()), [user_file])
            self.assertEqual(user_file.read_text(), "Preserve me")

    def test_symlink_assets_or_vendor_directory_rejected(self):
        for kind in ("asset", "vendor"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source, output = root / "source", root / "output"
                fixture(source)
                if kind == "asset":
                    path = source / "app.js"
                    path.unlink()
                    secret = root / "outside.js"
                    secret.write_text("Unrelated content")
                    path.symlink_to(secret)
                else:
                    (source / "vendor").rename(root / "vendor-outside")
                    (source / "vendor").symlink_to(root / "vendor-outside", target_is_directory=True)
                with self.assertRaisesRegex(ValueError, "symlink"):
                    hollow.copy_runtime(source, output)
                self.assertFalse(output.exists())

    def test_output_inside_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            fixture(source)
            with self.assertRaisesRegex(ValueError, "outside"):
                hollow.copy_runtime(source, source / "publication")
            self.assertFalse((source / "publication").exists())


if __name__ == "__main__":
    unittest.main()
