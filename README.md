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

## Assemble and preview locally

Requires Python 3.10+ and Node 22.12+ (the Atlas's Vite build requirement), with
Git checkouts of all three independent sources. Use paths to the checkout
roots, not their `dist/` or `presentation/` subdirectories:

```sh
git clone https://github.com/jjjhenriksen/shapenote-atlas.git ../atlas-source
git clone https://github.com/jjjhenriksen/sacred-harp-finetune.git ../local-ai-source
git clone https://github.com/jjjhenriksen/hollow-square.git ../hollow-square-source
python3 scripts/assemble.py \
  --atlas ../atlas-source \
  --local-ai ../local-ai-source \
  --hollow-square ../hollow-square-source \
  --output site \
  --serve 8877
```

The command checks source/hub files, runs `npm ci` and the Atlas build with
`--base=/atlas/`, stages the same layout used by Actions, then publishes it to
a **new** output directory. It does not train a model or deploy a site. Atlas
dependencies and generated `dist/` are written in the chosen Atlas checkout;
use an isolated checkout to preserve an existing working environment. With
an already built Atlas, `--atlas-built` skips npm and checks for `dist/index.html`;
the caller must ensure that build used `/atlas/` as its base.

At `http://127.0.0.1:8877/`, the hub and `/atlas/`, `/local-ai/`, and
`/hollow-square/` retain their production paths. Ctrl-C stops the loopback
preview. Omit `--serve` to assemble only; serve an existing output with
`python3 -m http.server 8877 --bind 127.0.0.1 --directory site`.

An existing output (including a symlink) is refused. Preserve or move it to a
new backup path before rebuilding; no automatic deletion occurs. A failed
build/copy leaves a prior output untouched and removes only its temporary
staging directory. Actions invokes this exact assembler, rather than a second
copy recipe.
