# Changelog

All notable changes, by version. Details and the reasons behind each change are in `logs/RUN_LOG.md` (the step numbers below), `docs/IMPROVEMENT_PLAN.md` and `docs/ROADMAP.md`.

## Unreleased

- Docs only: `HANDOFF.md` §3–4 is now a tested local setup guide for v2.0.0. It covers three install routes (from a clone, from the release archive, or without installing), a virtual environment with current pip and setuptools, a package mirror for restricted networks, how to check that the API keys are set without showing them, offline checks, and a first message for an AI assistant in ZCode. The roadmap and handoff record the decisions made after the release.
- Docs only: the README now opens with what the tool is, says that it is not on PyPI, explains the repository name and shows the test status. The limitations and the worked example come before the technical details, and the limitations add that results depend on the sources, which change over time (Step 93).

## 2.0.0 — 2026-11-03

From a tutorial demo to a tool for real research use: install it once, keep one project folder per idea, and run the scripted steps with one command. Everything since 1.0.0 is included.

### Use it

- Install: `python3 -m pip install "https://github.com/PadSama/novelty-probe-demo/archive/refs/tags/v2.0.0.zip"` (no dependencies; Python 3.9+).
- `novelty-probe init my-idea` creates a project folder; write the idea in `idea/idea.md`; an AI coding assistant writes the queries (`HOWTO.md` §3); `novelty-probe run` does the rest up to the evidence table.

### Added

- **One command, installable** (Steps 88–): `novelty-probe <command>` (also `python -m novelty_probe <command>`) with `init`, `run`, `search`, `qa`, `merge`, `authors`, `enrich`, `evidence`, `verify`, `snowball`, `compare`, `export`, `report`, `config`, `logrun`.
- **`novelty-probe init`**: a project folder with the rules, assistant instructions, guide, idea template, configuration and run log. It never overwrites existing files, `--update-docs` refreshes the three documents after an upgrade, and it refuses to put a project inside the tool repository, so research ideas do not end up next to the tool's code.
- **`novelty-probe run`**: check the queries → search → quality check → merge → missing authors (only if needed) → abstracts from other versions. Every step goes to the run log; it stops at the first error and prints the command to resume (`--from`); `--to`, `--suffix` and `--dry-run`.
- **`--log "<step name>"`** on every command, and automatic Step numbers in `logs/RUN_LOG.md`.
- **Records with authors and provenance** (Steps 81–87): authors come with every search; merged records keep which raw record each field came from.
- **Automatic, traceable deduplication**: every merge (D1–D5) and every pair kept apart (R1–R8) carries a rule code; authors count as evidence; no manual review step.
- **Outputs for the write-up**: candidates as RIS, a run manifest with the hash of every input and output, and a search report in PRISMA-S style; `export` and `report` for other selections, the other language, and diffs between runs.
- **Query syntax tree with error codes** (Steps 73–80): malformed queries are rejected with a code and position; each source is served from the same parsed query; OpenAlex's own parse is checked group by group.
- **Source registry** with an optional **Crossref** source (off by default).
- **HTTP layer** (Steps 67–68): per-host throttling, retries with jittered backoff, a circuit breaker, a cache, recording and replay of real responses, resumable pagination, response-shape checks, request estimates and OpenAlex credit warnings.
- **Configuration and languages** (Steps 69–72): `novelty-probe.json` holds only what differs from the defaults; Chinese and English interface; the evidence table can be kept as JSON with machine checks (`evidence check`).
- **Search improvements** (Steps 24–64): `AND NOT (…)` exclusions; Semantic Scholar results re-ranked locally from all hits; preprint and journal versions linked as one work; reciprocal rank fusion for the candidates; abstracts from other versions (`enrich`); citation chasing in one hop or two-hop co-citation (`snowball`); DOI verification falling back to OpenAlex for DataCite DOIs; search quality and local-matching bias (`qa`); comparison of rounds (`compare`).
- **Privacy and data terms** (Step 91): the search report lists each data source with its terms (Semantic Scholar with the link-back its license requires); the run log writes your home folder as `~`; recorded API responses are stored without e-mail addresses; the `.gitignore` written by `init` shows how to keep third-party data out of a public repository; the README states the sources and terms of the data in this repository; release archives contain only the tool (the worked example's data, test fixtures and run log stay in the repository).
- **Tests and CI**: offline tests with a network guard and recorded responses; GitHub Actions on Python 3.9–3.13 × Ubuntu / Windows, including the installed command and the PowerShell forms (macOS is not tested in CI); six optional live interface checks.

### Changed

- Commands moved into the package (`novelty_probe/commands/`). The 1.x entry points `scripts/*.py` still work and forward to them; their outputs are byte for byte the same.
- Queries that 1.x let through but that made the sources search different things are now errors (unbalanced quotes, commas, missing OR or AND; codes Q111–Q117).
- The default merge ranks candidates by reciprocal rank fusion and writes schema `novelty-probe/merged@2` (new fields: `authors`, `n_authors`, `field_source`, `dedupe_rules`, `rrf`, `bm25`, `n_conform`, `year_first`, `review`). `merge --legacy` reproduces the 1.0 outputs byte for byte.
- The candidates CSV has more columns (`rrf`, `bm25`, `n_conform`, `authors`, `year_first`, `review`); readers use column names, so both formats work.
- `logrun` numbers entries that do not already start with "Step N".
- Commands stop with an error when no project folder is found, instead of falling back to the tool's location; the HTTP cache defaults to `.cache/http` in the project folder.
- `HOWTO.md`, `AGENTS.md` and `PROJECT.md` are written for any project folder and are the same in the repository and in new projects; every command in the guide works in bash and in PowerShell.

### Not changed

- The three rules: evidence only, no novelty verdicts; every paper needs a DOI or arXiv ID from the retrieval results; every step is logged.
- No dependencies; Python 3.9 or later; MIT License. Not published to PyPI.

## 1.0.0 — 2026-11-01

First release: the tutorial workflow from idea to facets, Boolean queries, OpenAlex and Semantic Scholar search, merge and deduplication, a facet-by-facet evidence table, Crossref-verified DOIs and a difference statement, with a worked example (rounds v1 and v2) and the full run log (Steps 0–22).
