# Sacred Harp / Shape Note site

This is the small publication hub for Jacqueline Henriksen's Sacred Harp projects.

- `/atlas/` is built from the independent [`shapenote-atlas`](https://github.com/jjjhenriksen/shapenote-atlas) repository.
- `/local-ai/` is built from the independent [`sacred-harp-finetune`](https://github.com/jjjhenriksen/sacred-harp-finetune) repository's `presentation/` directory.
- `/hollow-square/` is built from the independent [`hollow-square`](https://github.com/jjjhenriksen/hollow-square) repository.

The GitHub Pages workflow assembles those parts at deployment time. The Atlas and Local AI source histories stay separate from this hub.

Because the Atlas repository is private, the hub's Actions secrets need an `ATLAS_READ_TOKEN`: a fine-grained GitHub token with read-only Contents access to `jjjhenriksen/shapenote-atlas`. Add it under this repository's Settings → Secrets and variables → Actions, then run the `Build and deploy Shape Note site` workflow.
