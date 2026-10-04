# Sacred Harp / Shape Note site

This is the small publication hub for Jacqueline Henriksen's Sacred Harp projects.

- `/atlas/` is built from the independent [`shapenote-atlas`](https://github.com/jjjhenriksen/shapenote-atlas) repository.
- `/local-ai/` is built from the independent [`sacred-harp-finetune`](https://github.com/jjjhenriksen/sacred-harp-finetune) repository's `presentation/` directory.
- `/hollow-square/` is built from the independent [`hollow-square`](https://github.com/jjjhenriksen/hollow-square) repository.

The GitHub Pages workflow assembles those parts at deployment time. The Atlas, Local AI, and Hollow Square source histories stay separate from this hub.

Hollow Square publication uses `scripts/copy_hollow.py` to copy only its
`index.html`, `styles.css`, `app.js`, `artwork.js`, `harmony-data.js`, the
marginalia stylesheet and script, the bundled handwriting fonts with their licenses and
source notice, and the vendored OpenSheetMusicDisplay script plus its license notice. Repository
metadata, tests, package/development configuration, installed dependencies,
and arbitrary extra files are excluded. Missing assets or symlink assets are
rejected before publication; an existing output directory is preserved.

Run the isolated publication regressions with
`python3 -m pip install PyYAML==6.0.3` and
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

## Identify and reconstruct a publication

Every assembled output contains `/build-manifest.json` with the full hub,
Atlas, Local AI, and Hollow Square commit SHAs and fixed repository identities.
It also records the publication base, build mode, tool versions, and whether
the source inputs were clean. The Actions build retains this file separately
as the `source-revisions` artifact; it is also inside the Pages artifact.
Only a build of `main` deploys. A manual workflow run on a branch builds and
retains artifacts with read-only repository permissions and skips deployment;
its concurrency group cannot cancel a `main` publication.

For the publication being investigated, download its manifest from the
deployed site or the **specific** Actions run's `source-revisions` artifact:

```sh
gh run download <run-id> --repo jjjhenriksen/shapenote-site \
  --name source-revisions --dir /new/path/to/publication-evidence
```

In a new directory, clone the four repositories named in `sources`, then
`git checkout --detach <recorded-commit>` in each clone. Use the recorded tool
versions and the hub at its recorded commit. From that hub checkout, run the
documented assembler against the three detached source checkouts with a new
output path. The assembler runs the recorded `/atlas/` build and lockfile-based
dependency installation. Compare file bytes to the retained publication if
exact artifact identity is required; timestamps/environment can differ, and
commit identity alone is not a byte-for-byte guarantee. Retain the manifest,
site artifact, and source objects if long-term availability is needed.

Normal publication requires clean Git checkout roots whose origins match the
four documented repositories. Independently checked source clones nested below
the hub (as in Actions) are excluded from the hub's dirty check, then checked
individually. No changes are stashed, discarded, or committed automatically.
For an intentionally edited local preview, add `--allow-dirty`; the manifest
labels those inputs dirty and the SHA is only their committed base. Ignored
extras and a `--atlas-built` output are not proven by their source SHAs; the
latter is explicitly labeled `prebuilt-unverified`. Reconstruct publications
from fresh checkouts using a full build. Unset `ATLAS_PUBLIC_DIR` so a private
fixture tree cannot silently replace the canonical Atlas publication source.

## Pull-request validation

Each PR runs the fixture regressions and the full three-source assembly, then
`python3 scripts/check_site.py site` before uploading artifacts. The build has
only read access to repository contents; Pages and identity-token permissions
belong only to the separate `main` deployment job. PR refs have their own
concurrency group and cannot cancel a `main` publication.

The checker requires the hub and three landing pages and validates static
HTML/CSS file references, including query/fragment paths, base URLs, stylesheet
imports, and the Local AI redirect. It resolves same-CNAME URLs locally and
skips external URLs without fetching them. It is read-only and reports file
locations for missing references. This checks the current publication's static
references, not JavaScript behavior, dynamic requests, srcset, external-link
availability, or every application's interaction; retain separate browser
evidence for those runtime claims.

## Source update notifications

The supported sender is an authenticated maintainer running `scripts/dispatch.py`.
The current source Actions workflows run their own tests/deployments; they **do
not send notifications to this hub**. A source push alone therefore does not
prove a hub rebuild. After an approved update reaches source `main`, explicitly
send its notification using the mapping below:

| Source main | Sender option | Receiver event type | Published path |
| --- | --- | --- | --- |
| `jjjhenriksen/shapenote-atlas` | `atlas` | `atlas-updated` | `/atlas/` |
| `jjjhenriksen/sacred-harp-finetune` | `local-ai` | `local-ai-updated` | `/local-ai/` |
| `jjjhenriksen/hollow-square` | `hollow-square` | `hollow-square-updated` | `/hollow-square/` |

The receiver is `jjjhenriksen/shapenote-site`'s `deploy-pages.yml` on its default
branch. Each accepted event rebuilds **all three latest-main sources**, checks
landing pages/assets, and deploys `main`. The source SHA in the request is a
verification hint, not a checkout override. The manifest records actual
checkout commits separately. GitHub requires the receiver workflow to exist
on its default branch for [repository_dispatch events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#repository_dispatch).

Authenticate `gh` as a maintainer authorized for the hub. A fine-grained PAT or
GitHub App token needs **Contents: write on the hub**; a classic PAT needs the
`repo` scope, according to the [dispatch API permission contract](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event).
Do not put credentials in the request, source files, artifacts, or verification
receipts. An optional future source-CI sender needs a separately configured
hub-authorized credential; these source workflows currently have no sender,
and this change does not provision tokens or secrets. Receiver build permissions
remain read-only, with Pages/token write permissions limited to deployment.

The helper defaults to an offline request preview and requires a full source
SHA. `--send` instead resolves that source's current `main` via GitHub, refusing
an explicitly supplied stale SHA before posting. Its only payload fields are
`repository`, `sha`, and a non-secret `verification_id` (1–80 ASCII letters,
digits, hyphens, or underscores). The receiver validates those hints and retains
only that bounded metadata in `build-manifest.json`; extra payload fields are
ignored. Legacy notifications with an empty payload still rebuild latest main,
but cannot identify the requested source revision.

```sh
# Offline: use the actual full source SHA, with no network request.
python3 scripts/dispatch.py --source atlas --sha <full-source-main-sha> \
  --verification-id atlas-check-01

# Explicit send: resolves current source main and writes a non-secret receipt.
# Keep evidence outside the hub checkout so the checkout stays clean.
python3 scripts/dispatch.py --source atlas --send \
  --verification-id atlas-check-01 > /new/evidence/atlas-receipt.json
```

Repeat with `local-ai` and `hollow-square`, using a unique ID per request. Wait
for each run to finish before sending the next: a newer `main` notification
can cancel the previous `main` run under the publication concurrency policy.
A receipt marked `accepted: true` proves request acceptance only, not that a
workflow built or deployed anything.

To verify an actual source update, retain the source commit and receipt, then:

1. Find the new receiver run with `gh run list --repo jjjhenriksen/shapenote-site
   --workflow deploy-pages.yml --event repository_dispatch --json databaseId,event,displayTitle,headSha,status,conclusion`.
   Its title identifies the event type; retain the selected run ID and hub SHA.
2. Wait for that specific run with `gh run watch <run-id> --repo
   jjjhenriksen/shapenote-site --exit-status`. Inspect its build and deployment
   jobs with `gh run view <run-id> --repo jjjhenriksen/shapenote-site --json
   event,headSha,status,conclusion,jobs`. Both must succeed for publication proof.
3. Download that run's `source-revisions` artifact using the command above.
   Require `trigger.event == "repository_dispatch"`, the matching `trigger.type`,
   `trigger.verification_id`, and `trigger.requested_commit` from the receipt.
   Require `sources.hub.commit` to match the run's hub SHA, then compare the
   corresponding `sources.atlas`, `sources.local_ai`, or `sources.hollow_square`
   commit to the requested source SHA. Check the other source revisions too.
   If source `main` advanced between sending and checkout, establish the
   requested commit is included in the recorded revision or repeat the check;
   do not claim an exact revision match from HTTP acceptance alone.
4. Retain the receipt, run status/log, and manifest together. This proves the
   explicit maintainer notification path for that source update. It does not
   establish unattended source-push delivery or every application's behavior.

If notification delivery is unavailable, the manual fallback is:

```sh
gh workflow run deploy-pages.yml --repo jjjhenriksen/shapenote-site --ref main
```

Find its `workflow_dispatch` run, wait for build/deployment, and retain its
manifest with actual revisions. A manual branch run builds only and skips
publication. An offline sender preview or a failed/canceled run is not evidence
that the source update was published.
