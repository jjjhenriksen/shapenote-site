from pathlib import Path


def sources(root: Path):
    hub, atlas, ai, hollow = (root / name for name in ("hub", "atlas", "local-ai", "hollow"))
    for path in (hub, atlas, ai, hollow):
        path.mkdir()
    for name in ("index.html", "styles.css", "CNAME", ".nojekyll"):
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
                 "vendor/opensheetmusicdisplay.min.js", "vendor/opensheetmusicdisplay.min.js.LICENSE.txt"):
        path = hollow / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"Hollow {name}")
    return hub, atlas, ai, hollow
