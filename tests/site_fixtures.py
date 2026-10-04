from pathlib import Path
import subprocess


def sources(root: Path):
    hub, atlas, ai, hollow = (root / name for name in ("hub", "atlas", "local-ai", "hollow"))
    for path in (hub, atlas, ai, hollow):
        path.mkdir()
    for name in ("index.html", "styles.css", "favicon.ico", "CNAME", ".nojekyll"):
        (hub / name).write_text(f"Hub {name}")
    (atlas / "package.json").write_text('{"scripts":{"build":"vite build"}}')
    (atlas / "package-lock.json").write_text('{}')
    (atlas / "dist/assets").mkdir(parents=True)
    (atlas / "dist/index.html").write_text('<script src="/atlas/assets/app.js"></script>')
    (atlas / "dist/assets/app.js").write_text('console.log("atlas")')
    (ai / "presentation").mkdir()
    (ai / "presentation/index.html").write_text('<img src="image.webp">')
    (ai / "presentation/image.webp").write_bytes(b"fictional image fixture")
    for name in ("index.html", "styles.css", "app.js", "artwork.js", "harmony-data.js",
                 "marginalia.css", "marginalia.js",
                 "assets/fonts/Caveat-notes.woff2", "assets/fonts/Caveat-OFL.txt",
                 "assets/fonts/Caveat-SOURCE.txt",
                 "vendor/opensheetmusicdisplay.min.js", "vendor/opensheetmusicdisplay.min.js.LICENSE.txt"):
        path = hollow / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"Hollow {name}")
    for path, repository in ((hub, "shapenote-site"), (atlas, "shapenote-atlas"),
                             (ai, "sacred-harp-finetune"), (hollow, "hollow-square")):
        commands = [("init", "-q"), ("remote", "add", "origin", f"https://github.com/jjjhenriksen/{repository}.git"),
                    ("add", "."), ("commit", "-qm", "Fictional publication fixture")]
        for command in commands:
            subprocess.run(["git", "-C", str(path), "-c", "user.name=Publication Fixture",
                            "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
                            "-c", "core.hooksPath=/dev/null", *command], check=True, capture_output=True)
    return hub, atlas, ai, hollow
