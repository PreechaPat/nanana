# Repository Guidelines

## Project Structure & Module Organization
- `src/nanana/cli.py` exposes the top-level CLI and should stay minimal—dispatch heavy lifting to helpers.
- `src/nanana/command/` hosts subcommands (`cluster`, `polish`, `setup_taxonkit`, etc.) that wrap workflows; mirror this layout when adding new commands.
- `src/nanana/lib/` holds reusable domain logic (alignment, clustering, FASTA helpers, taxonomy). New utilities belong here with focused modules.
- `test_data/` provides sample inputs for smoke tests; keep large datasets external and document download steps.
- `notebook/` is for exploratory work—export verified insights back into `src/` before shipping features.

## Environment Setup
- Use `pixi install -e default` to create the dev environment with runtime plus `ruff` and `mypy`.
- Activate the environment with `pixi shell -e default` before running commands locally.

## Build, Test, and Development Commands
- `pixi run -e default nanana --help` prints CLI usage; prefer this for quick smoketests.
- `pixi run -e default nanana-clust test_data/demo.fasta --output /tmp/out/clusters.tsv` clusters FASTA/FASTQ reads.
- `pixi run -e default nanana-hydrate /tmp/out/clusters.tsv --dist yes.tsv --output /tmp/out/hydrated.tsv` adds taxonomy metadata.
- `pixi run -e default nanana-plot /tmp/out/hydrated.tsv --png /tmp/out/hydrated.png` generates a plot from cluster coordinates.
- `pixi run -e default mypy src/nanana` enforces typing contracts.
- `pixi run -e default ruff check src` and `pixi run -e default ruff format src` keep style consistent.
- `./build.sh` assembles the Docker image tagged `nanana:0.1.0` for deployment.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; keep functions short and typed.
- Name modules and packages with lowercase underscores; public classes use `CamelCase`, functions and variables use `snake_case`.
- Centralize constants in the module they serve and prefix CLI-specific options with `cli_` to avoid collisions.

## Testing Guidelines
- No automated test suite is committed yet; when adding features, supply a `pytest` module under `tests/` (e.g., `tests/test_cluster.py`) and run via `pixi run -e default python -m pytest` before opening a PR.
- Use `test_data/` for deterministic fixtures; document new datasets in `README.md`.
- Capture CLI smoke results (command + sample output snippet) in the PR description for traceability.

## Commit & Pull Request Guidelines
- Write imperative, present-tense commit subjects ≤72 chars (e.g., `Add HDBSCAN fallback for sparse inputs`).
- Squash incidental commits before review and ensure `ruff`/`mypy` pass on the final revision.
- PRs should explain the problem, solution, and testing evidence; link related issues and attach screenshots or logs when behavior changes.
