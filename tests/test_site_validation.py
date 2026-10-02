import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_site import check


def publication(root):
    pages = {
        "index.html": '<a href="/atlas/">Atlas</a><a href="./local-ai/">AI</a><a href="./hollow-square/">Game</a>',
        "atlas/index.html": '<script src="/atlas/assets/app.js?v=1"></script><link href="/atlas/assets/app.css" rel="stylesheet">',
        "local-ai/index.html": '<meta http-equiv="refresh" content="0; url=detail.html"><a href="detail.html">Presentation</a>',
        "local-ai/detail.html": '<img src="image%20one.png"><a href="https://external.invalid/missing">External</a>',
        "hollow-square/index.html": '<script src="app.js"></script><link href="style.css" rel="stylesheet"><a href="#notes">Notes</a>',
    }
    for name, body in pages.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'<!doctype html><html><head><title>Fixture</title></head><body>{body}</body></html>')
    for name in ("atlas/assets/app.js", "local-ai/image one.png", "hollow-square/app.js"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Asset")
    (root / "atlas/assets/app.css").write_text("body {background: url('../../local-ai/image%20one.png?v=2#image')}")
    (root / "hollow-square/style.css").write_text("/* url(missing-comment.png) */ .shape { fill: url(#shape) } .a { background: url('data:image/png;base64,FAKE') }")


class SiteValidationTests(unittest.TestCase):
    def test_all_routes_assets_queries_css_and_external_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            publication(root)
            report = check(root)
            self.assertEqual(report["issues"], [])
            self.assertGreater(report["local_references_checked"], 8)

    def test_missing_assets_in_each_source_are_reported_with_locations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            publication(root)
            for name in ("atlas/assets/app.js", "local-ai/image one.png", "hollow-square/style.css"):
                (root / name).unlink()
            report = check(root)
            documents = {issue["file"] for issue in report["issues"]}
            self.assertTrue({"atlas/index.html", "local-ai/detail.html", "hollow-square/index.html"}.issubset(documents))
            self.assertTrue(all(issue["line"] is not None for issue in report["issues"] if issue["file"].endswith('.html')))

    def test_missing_landing_or_wrong_atlas_base_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            publication(root)
            (root / "atlas/index.html").write_text('<html><title>Wrong base</title><script src="/assets/app.js"></script></html>')
            (root / "local-ai/index.html").unlink()
            issues = check(root)["issues"]
            self.assertTrue(any(issue.get("reference_path") == "/assets/app.js" for issue in issues))
            self.assertTrue(any(issue["file"] == "local-ai/index.html" and issue["issue"] == "Missing landing page" for issue in issues))

    def test_base_tag_same_origin_and_css_imports_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            publication(root)
            (root / "CNAME").write_text("example.invalid\n")
            (root / "atlas/index.html").write_text('<html><title>Base</title><base href="/atlas/assets/"><script src="app.js"></script><a href="https://example.invalid/local-ai/">AI</a></html>')
            with (root / "atlas/assets/app.css").open("a") as file:
                file.write('\n@import "../../hollow-square/style.css";')
            self.assertEqual(check(root)["issues"], [])

    def test_non_html_landing_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            publication(root)
            (root / "hollow-square/index.html").write_text("Not a document")
            self.assertTrue(any(issue["file"] == "hollow-square/index.html" for issue in check(root)["issues"]))

    def test_encoded_escape_and_symlink_document_do_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "site"
            root.mkdir()
            publication(root)
            outside = Path(tmp) / "outside.html"
            outside.write_text("Unrelated user data")
            (root / "external.html").symlink_to(outside)
            with (root / "index.html").open("a") as file:
                file.write('<a href="/%2e%2e/outside.html">Escape</a>')
            issues = check(root)["issues"]
            self.assertTrue(any(issue["issue"] == "Symlink document is not read" for issue in issues))
            self.assertTrue(any(issue["issue"] == "Missing/outside local reference" for issue in issues))
            self.assertEqual(outside.read_text(), "Unrelated user data")

    def test_cli_is_read_only_and_exits_nonzero_for_broken_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            publication(root)
            (root / "hollow-square/app.js").unlink()
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = subprocess.run([sys.executable, str(ROOT / "scripts/check_site.py"), str(root)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(json.loads(result.stdout)["issues"])
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()
