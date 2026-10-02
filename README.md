# Sacred Harp / Shape Note site

This is the small publication hub for Jacqueline Henriksen's Sacred Harp projects.

- `/atlas/` is built from the independent [`shapenote-atlas`](https://github.com/jjjhenriksen/shapenote-atlas) repository.
- `/local-ai/` is built from the independent [`sacred-harp-finetune`](https://github.com/jjjhenriksen/sacred-harp-finetune) repository's `presentation/` directory.
- `/hollow-square/` is built from the independent [`hollow-square`](https://github.com/jjjhenriksen/hollow-square) repository.

The GitHub Pages workflow assembles those parts at deployment time. The Atlas, Local AI, and Hollow Square source histories stay separate from this hub.

Hollow Square publication uses `scripts/copy_hollow.py` to copy only its
`index.html`, `styles.css`, `app.js`, `artwork.js`, `harmony-data.js`, and the
vendored OpenSheetMusicDisplay script plus its license notice. Repository
metadata, tests, package/development configuration, installed dependencies,
and arbitrary extra files are excluded. Missing assets or symlink assets are
rejected before publication; an existing output directory is preserved.

Run the isolated publication regressions with
`python3 -m unittest discover -s tests -v`. These fixtures do not deploy Pages.
