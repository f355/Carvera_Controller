# Visual regression integration tests

These tests boot the real Kivy app, drive it through a set of UI
states, and compare rendered screenshots against committed reference
PNGs. They live in `test_visual_regression.py` and use the helpers in
`conftest.py`.

## Prerequisites

```bash
poetry install --with test
```

## Running the suite

### Container (the path that matches the committed references)

```bash
tests/integration/run-in-container.sh tests/integration -v
```

The committed reference PNGs are pinned to the font, fontconfig,
Mesa, FreeType/HarfBuzz, Kivy text-provider, and locale stack inside
`tests/integration/Containerfile`. The container is the only path
that reliably matches them, and the same path CI uses.

The wrapper builds the image on first use (or when you set
`REBUILD=1`), bind-mounts the repo at `/workspace`, and runs pytest
under Xvfb. Exit code is pytest's exit code. The container runtime
can be overridden via `CONTAINER_CMD=docker`; podman is the default
when both are available.

### Native (any platform, best-effort)

```bash
poetry run pytest tests/integration -v
```

On Linux the same line works under `xvfb-run -s "-screen 0 1280x720x24"`
if you don't have a display attached. A native run is not guaranteed
to match the committed references on any host — even on Linux — because
those references are pinned to the container's specific font/Mesa/Kivy
stack and host versions of any of those layers will shift pixels. For
local iteration without that friction, see the local-references workflow
below.

## Updating reference baselines

Two flags, two workflows.

### Local iteration: `--update-references`

When you want to hack on the UI and have a working visual suite
locally, regenerate references into a per-host set that lives only
in your working tree:

```bash
poetry run pytest tests/integration -v --update-references
```

This writes each fresh screenshot to
`tests/integration/reference.local/<name>.png` (gitignored) instead
of touching the committed baselines. On subsequent runs
`compare_screenshots` prefers the local set over the committed
baseline, so the suite passes natively against PNGs your own machine
just produced. Delete the directory to fall back to the committed
baselines.

### Committed updates: `--update-committed-references`

When you make an intentional UI change that should be reflected in
the committed baselines that CI compares against, regenerate them in
the container:

```bash
tests/integration/run-in-container.sh tests/integration -v --update-committed-references
```

This writes to `tests/integration/reference/<name>.png`. Then commit:

```bash
git add tests/integration/reference/
git commit -m "test: refresh visual baselines for <reason>"
```

Passing both flags is an error.

## Reference-state behaviour matrix

`compare_screenshots` (in `conftest.py`) resolves the reference file
in this order:

| State | What happens |
|---|---|
| `reference.local/<name>.png` exists | Compared against the local reference. |
| `reference/<name>.png` exists | Compared against the committed reference. |
| `reference/<name>.png` missing entirely | Test **fails** with `"No reference baseline for <name>. Run with --update-references to create one."` |

## Outputs and diffs

- `tests/integration/output/` (gitignored) — every test writes its
  rendered screenshot here. Inspect after a failure.
- `tests/integration/output/<name>_DIFF.png` — produced when a
  comparison fails; highlights the differing pixels.

## See also

- `Containerfile` — the Linux/Xvfb test image.
- `run-in-container.sh` — wrapper that picks `podman` or `docker`.
