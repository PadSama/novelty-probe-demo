# novelty-probe

A fully logged, AI-assisted workflow for probing the literature around a research idea, built as a tutorial demo.

You describe an idea in one or two sentences. The pipeline breaks it into facets, builds Boolean queries, searches OpenAlex and Semantic Scholar, merges and deduplicates the results (linking preprints to their published versions), ranks the candidates, maps the top candidates to each facet of the idea, and checks every DOI against Crossref (or OpenAlex). Optional citation chasing from the relevant papers finds work that keyword search misses because it uses different wording.

The workflow **does not judge novelty**. It collects evidence with verifiable identifiers so that the researcher can make that judgment.

> The step-by-step guide (`HOWTO.md`) is bilingual, Chinese and English paragraph by paragraph, with every prompt in both languages. The assistant's rules (`PROJECT.md`) are in Chinese and summarized below.

## Ground rules

From `PROJECT.md`:

1. **Evidence, not verdicts.** The assistant reports what it found and which part of the idea each paper relates to. It never states whether the idea is novel.
2. **Every paper needs a DOI or arXiv ID** taken from a retrieval result, never from memory. Papers without one are marked `UNVERIFIED`.
3. **Everything is logged.** Every command and output file is appended to `logs/RUN_LOG.md`.

## Pipeline

| Step | Done by | Output |
|---|---|---|
| T1 Write the idea | You | `idea/idea.md` |
| T2 Facets and queries | AI assistant | `facets/facets.md` (5 facets × 3–5 English search terms), `queries/queries.json` (6 Boolean queries) |
| T3 Search | `scripts/search.py` | `results/raw/{source}_{query}.json` (top 25 per query and source) |
| T4 Merge and deduplicate | `scripts/merge.py` | `results/merged/merged.json`, `results/merged/candidates.csv` (top 20, with authors), `candidates.ris` (for Zotero or EndNote), `run_manifest.json` and `search_report.md` (PRISMA-S style) |
| T5 Evidence table and verification | `scripts/enrich.py`, AI assistant, `scripts/verify.py` | `evidence/evidence_table.md`: each candidate labeled overlap / differ / unknown on every facet, with DOI checks |
| T5b Citation chasing (optional) | `scripts/snowball.py` + you | `results/merged/chase_*.csv`: papers linked by citations to the evidence-table papers you mark as relevant |
| T6 Difference statement | AI assistant + you | `evidence/difference_statement.md` |

The five facets are research question, mechanism, context, data and methods, and expected findings. Each query has a purpose: *component*, *application*, *method*, or *concurrent* (recent work, 2023 onwards).

Steps that need judgment are done by an AI coding assistant run in this directory, from paste-ready prompts in `HOWTO.md`, and are meant to be reviewed by the researcher. The worked example used Claude Code; any assistant that follows `AGENTS.md` can do these steps, for example ZCode with GLM. These are T2, the facet labels in T5, and choosing the closest papers in T6. Everything else is a script.

## Quick start

**Requirements**

- Python 3.9 or later. The scripts use only the standard library.
- Network access to `api.openalex.org`, `api.semanticscholar.org`, `doi.org` and `api.crossref.org`.
- API keys, read from environment variables:
  - `OPENALEX_API_KEY`: strongly recommended. The free key avoids OpenAlex's shared daily budget.
  - `S2_API_KEY`: optional. With a key, Semantic Scholar allows 1 request per second across all endpoints; `search.py` throttles every Semantic Scholar request (including pages and retries) to stay within it.

**Steps**

1. Clear the example outputs (`HOWTO.md` §1) and write your idea in `idea/idea.md`.
2. Ask the assistant to write `facets/facets.md` and `queries/queries.json` (prompt in `HOWTO.md` §3). Then check the query syntax offline:

```bash
python3 scripts/search.py --dry-run
```

3. Run the scripted steps. Each command is wrapped in `logrun.py`, which appends the command and its output to the run log:

```bash
python3 scripts/logrun.py "T3 search" -- python3 scripts/search.py
```

```bash
python3 scripts/logrun.py "T4 merge" -- python3 scripts/merge.py
```

```bash
python3 scripts/logrun.py "T5 abstracts from other versions" -- python3 scripts/enrich.py --top 20
```

   Authors come with the search results, and the merge also writes the candidates as RIS, a run manifest and a search report, so there is no separate step for any of them. `authors.py` is needed only for results searched before November 2026, which have no authors.

4. Ask the assistant to write `evidence/evidence_table.md` (prompt in `HOWTO.md` §6). Then verify the DOIs:

```bash
python3 scripts/logrun.py "T5 verify" -- python3 scripts/verify.py
```

5. Optional: chase citations from the evidence-table papers with at least two overlapping facets, in one hop or as two-hop co-citation through citing papers that match a term group you choose (`HOWTO.md` §6, T5b):

```bash
python3 scripts/logrun.py "T5b chase" -- python3 scripts/snowball.py --from-evidence evidence/evidence_table.md --cocite --citer-filter 'scientist*'
```

To run another round without overwriting the first, use version suffixes, for example `search.py --queries queries/queries_v2.json --suffix _v2` and `merge.py --suffix _v2` (`HOWTO.md` §8). `compare.py --runs ,_v2 --known <DOI>` then compares the rounds, including where papers you already know rank.

## How the scripts work

- **`search.py`** parses each generic Boolean query once into a syntax tree (malformed queries are rejected with an error code and position) and runs it against every enabled source from the source registry (`novelty_probe/sources/`). Adding a source takes one module and one recorded test fixture. The per-source conversion:
  - OpenAlex: `filter=title_and_abstract.search` with the Boolean query kept and results ranked by relevance. Truncated words are replaced by full words, because OpenAlex rejects wildcards in its default stemmed search.
  - Semantic Scholar: `/graph/v1/paper/search/bulk`, with `AND` written as `+` and `OR` as `|`. This endpoint has no relevance ranking, so the script fetches all hits (up to 3,000) and re-ranks them locally: number of AND groups matched in the title and abstract, then BM25, then citation count. Records without an abstract are ranked separately and interleaved in proportion; duplicate titles are kept once.
  - Exclusions are written `AND NOT ("a" OR "b")`. OpenAlex receives them unchanged, and Semantic Scholar receives `+ -("a" | "b")`. Before saving OpenAlex results, the script compares the parse tree OpenAlex returns with the query group by group, and stops if OpenAlex changed the grouping or dropped the NOT (a lower-case `not` would silently turn the exclusion into a requirement).
  - Crossref (optional, off by default): it has no Boolean search, so the include terms are sent as one bag of words, and the Boolean query is applied locally to the titles and abstracts of up to 1,000 retrieved records. In tests, short queries work well and long ones find little.

  For each query and source it saves the top 25 records (title, year, DOI, arXiv ID, venue, abstract, authors), the exact query string sent, and the hit count reported by the API. It retries on HTTP 429 and 5xx, and fails fast when an API asks it to wait more than 60 seconds. `--dry-run` checks query syntax without network access and prints how many requests each source will receive at most.
- **`qa.py`** (optional) reports how many retrieved records satisfy the original query in their title and abstract, using Porter stemming as an approximation of the APIs' matching. It also measures that approximation: for sources that run the Boolean query on the server, every returned record satisfies the query, so the share that local matching judges non-conforming bounds its false-negative rate (1.1% for OpenAlex and 6.4% for Semantic Scholar in the tutorial's v1b round).
- **`merge.py`** deduplicates records and ranks the candidates:
  - **Matching:** two records count as one work if they share a DOI (case, URL query strings and landing-page suffixes ignored) or an arXiv ID; versioned preprint DOIs on OSF, TechRxiv and Research Square count as the same work. Versions of one work are then linked by title, with authors as evidence: titles must match after normalization (dropping publication-status notes such as "(Just accepted by Nature…)") and pass conservative checks (years at most 3 apart, not two different journal DOIs, not a dataset, not a "Re:" letter or correction, abstracts consistent, at least one author name in common when both records have authors); nearly identical titles are linked only when the records share authors. Doubtful pairs stay separate. Every merge and every separation is recorded with a rule code (D1–D5, R1–R8), so deduplication needs no manual review.
  - **Provenance:** each work keeps references to its raw records (`raw_refs`) and, for every field, the raw record it came from (`field_source`). Title-based merges are flagged, and works with neither a DOI nor an arXiv ID are marked `UNVERIFIED`. The year is that of the version of record; the earliest version's year is kept as `year_first`.
  - **Ranking:** reciprocal rank fusion over the query × source result lists (score = Σ 1/(60 + rank)), with BM25 over all query terms breaking ties. `--legacy` reproduces the original method (ranking by "hits", the number of result lists containing the work) used for the committed v1 and v2 outputs.
  - **Outputs for the write-up:** the top candidates as RIS (`candidates.ris`), a run manifest with the hash of every input and output file, the queries as written and as sent, dates and the configuration fingerprint (`run_manifest.json`), and a search report generated from it following PRISMA-S (`search_report.md`).
- **`export.py`** writes RIS for all merged works (`--all`) or for the rows of an evidence table, with each facet label as a keyword (`--evidence`). **`report.py`** regenerates the search report from a manifest, in Chinese or English (`render`), and compares two runs (`diff`).
- **`authors.py`** fills in authors from OpenAlex, by DOI, for candidates whose merged record has none (results searched before November 2026).
- **`enrich.py`** finds other versions of each candidate in OpenAlex (same title, years at most 3 apart, at least one shared author surname) and records any abstract or arXiv ID they have, with its source, in `evidence/enrichment.json`. Journal versions often have no abstract in either API, while their preprints do.
- **`verify.py`** checks each DOI two ways and writes both results into the `verified` column:
  - It fetches the registered metadata through doi.org content negotiation and compares the registered title with the table's title. If Crossref has no record (arXiv and other DOIs registered with DataCite), it looks the DOI up in OpenAlex instead.
  - It follows the DOI to the publisher's landing page and records the HTTP status and page title, upgrading https-to-http redirects to https (`--no-landing` skips this check).
- **`snowball.py`** chases citations from seed papers via OpenAlex: one hop (papers citing or cited by the seeds, ordered by the number of seeds they are linked to and by text similarity to the seeds), or two-hop co-citation (papers that cite the seeds and match a term group you choose, then the works they cite in common, ordered by that count). Versions of one work are counted once; letters and corrections are not counted.
- **`compare.py`** compares rounds: ranks of known papers in the merged results and chase lists, ties at the cutoff, and the make-up of the top 10 and top 20.
- **`textmatch.py`** forwards to `novelty_probe/text.py`, the shared, standard-library text matching: a Porter stemmer (identical to Snowball's "porter" on its 42,603-word test vocabulary), Boolean matching, BM25, TF-IDF similarity and the version-linking rule.
- **`evidence.py`** checks an evidence table against the retrieval results: labels are valid, every DOI and arXiv ID comes from the search results, titles, years and authors match them, and quoted English text in the rationale is verbatim from an abstract. It also converts the Markdown table to JSON (`import-md`) and back (`render`, in Chinese or English). The JSON can serve as the source of truth: `verify.py --table <json>` stores structured results there and regenerates the Markdown, and refuses to overwrite a Markdown file that was edited by hand.
- **`config.py`** shows or checks the project configuration (`show`, `show --diff`, `check`, `init`).
- **`logrun.py`** runs any command and appends the command and its output to `logs/RUN_LOG.md`.

All scripts share the standard-library package `novelty_probe/`: one HTTP client (per-host throttling, retries with jittered backoff, a circuit breaker, a cache, and record/replay of real responses), response-shape checks, the configuration, the interface language and the evidence JSON. Every script accepts `--root` (project folder), `--config` and `--lang zh|en`.

## Configuration and language

`novelty-probe.json` in the project root holds only the settings that differ from the built-in defaults: facets and their labels, label values, column names, query purposes and their start years, the truncation table, records per source, the RRF and BM25 parameters, the version-linking prefixes and year window, stopwords, and per-host HTTP policies. Methods themselves (stemming, the BM25 and RRF formulas, the order of the version-linking rules) are not configurable, because changing them would make results incomparable. Each output file records a `config_hash` of the effective configuration. `python3 scripts/config.py show` prints every setting.

Help, error messages and the verified column are in Chinese by default; `--lang en`, `NP_LANG=en` or `"language": "en"` in the configuration switches them to English.

## Tests

The offline self-test checks the scripts without network access, using local mock servers and recorded real responses. A guard makes any attempt to reach the network fail the test, in child processes too. The suite re-runs the merge with `--legacy` on the committed raw results and confirms that the output matches the committed files byte for byte. GitHub Actions runs it on Python 3.9–3.13 on Ubuntu, Windows and macOS.

```bash
python3 -m unittest discover -s tests -v
```

Six optional live checks (one request each) confirm that OpenAlex, Semantic Scholar and Crossref still behave as the scripts assume. Run them before a new search round:

```bash
NP_LIVE=1 python3 -m unittest tests.test_live_contract -v
```

## Worked example

The repository holds a complete run on one idea (original in Chinese): *Does researchers' use of AI tools narrow the range of research topics in a discipline? To be tested with large-scale publication data.*

**Round 1 (v1, no field specified).**
- 6 queries × 2 sources returned 217 records, which merged into 161 works.
- The top-10 evidence table and the difference statement are in `evidence/`.
- Crossref confirmed all 10 DOIs in the table.

**What round 1 missed.** The researcher's reference paper was not among the 217 records: Hao, Xu, Li & Evans, *Artificial intelligence tools expand scientists' impact but contract science's focus*, Nature 649, 1237–1243 (2026), doi:10.1038/s41586-025-09922-y. The diagnosis is in RUN_LOG Step 11:
- The Nature version has no abstract in OpenAlex or Semantic Scholar, so only its title could match.
- Its arXiv preprint (arXiv:2412.07727) calls AI "Artificial Intelligence (AI)" and "AI tools", and calls the outcome a "narrowing of scientific focus". None of the v1 queries match that wording.

**Round 2 (v2, management and economics).**
- **Changes:** the context was narrowed to management and economics research. The vocabulary was broadened (`AI tools`, `artificial intelligence`, `narrowing`), and one query was added for the same relation in other sciences.
- **Results:** 235 records merged into 191 works. The reference paper ranks 3rd among the candidates. It overlaps with the idea on four of the five facets and differs on context: its preprint abstract describes 41.3 million papers across the natural sciences.
- **Caveat:** the v2 vocabulary was adjusted after the miss was known, so finding the paper confirms the fix but is not an independent test of recall.
- **Side effect:** broadening to `narrowing` also pulled in papers about "narrow AI", 4 of the top 10.

**Improvements and evaluation (v1b, v2b).** The known issues of rounds 1 and 2 were researched (similar open-source tools, methods literature, live API tests) and addressed; the plan, references and results are in `docs/IMPROVEMENT_PLAN.md`. Both rounds were re-run with the improved pipeline:
- **Ties:** works tied at the top-20 cutoff fell from 42 to 1 (v1) and from 32 to 1 (v2).
- **Noise:** with `AND NOT ("narrow AI" OR "narrow artificial intelligence")` added to the queries using *narrowing*, "narrow AI"-type papers in the v2 top 10 fell from 4 to 0 (one remains in the top 20).
- **Versions:** the Nature paper and its arXiv preprint are now one work, dated 2026 (preprint 2024), and the merged record carries the preprint's abstract.
- **Recall:** the v1 queries still cannot retrieve the reference paper. Two-hop co-citation from the v1 evidence-table papers, through citing papers that mention *scientists*, ranks it first. With a different term group it does not appear at all, and that filter was found while the target was known, so this is one positive case, not a validation.

Every decision, command and output is in `logs/RUN_LOG.md`, including mistakes and how they were fixed.

## Limitations

- Only the top 25 records per query and source are kept, and the ranking reflects how well the text matches the queries, not relevance to the idea. Broad or very narrow queries limit what any ranking can do.
- Matching uses titles and abstracts only. A record without an abstract can only be found through its title, unless another version of the same work has one.
- Version linking relies on titles; versions whose titles changed substantially are not merged.
- Citation chasing depends on the seeds and on the term group used to filter citing papers; results can change completely with a different group.
- Facet labels are produced by an AI assistant from abstracts and need human review.
- In the cloud environment used for this run, publisher landing pages were not reachable, so verification relies on Crossref and OpenAlex metadata.

## License

The code and documentation in this repository are released under the [MIT License](LICENSE). The search results in `results/` and `evidence/` include metadata and abstracts retrieved from OpenAlex and Semantic Scholar. Those abstracts remain under the copyright of their publishers or authors, and this license does not cover them.

## How to cite

If you use novelty-probe, please cite it using the metadata in [`CITATION.cff`](CITATION.cff). GitHub shows it under "Cite this repository".

## Repository layout

```
idea/            the idea (idea.md; idea_v2.md for round 2)
facets/          facet decomposition and search terms
queries/         Boolean queries (queries.json, queries_v2.json; queries_v2b.json adds NOT for the evaluation)
results/raw/     raw search results per source and query; chase_* citation-chasing results
results/merged/  deduplicated works, top-20 candidates (CSV and RIS), run manifests, search reports, chase lists,
                 comparisons
evidence/        evidence tables, authors (older rounds), abstracts from other versions, difference statement
logs/RUN_LOG.md  append-only log of every step
scripts/         search.py, qa.py, merge.py, export.py, report.py, authors.py, enrich.py, verify.py, snowball.py,
                 compare.py, evidence.py, config.py, textmatch.py (forwards to the package), logrun.py
novelty_probe/   shared package: query syntax tree, sources, HTTP client and cache, response checks, configuration,
                 i18n, evidence JSON, text matching, merged records, dedupe rules, ranking, RIS, run manifest and report
novelty-probe.json  project configuration (only what differs from the defaults)
examples/        frozen copy of the tutorial outputs, used as test fixtures
tests/           offline self-test, recorded responses, optional live checks
docs/            IMPROVEMENT_PLAN.md (known issues), ARCHITECTURE_REVIEW.md (tool-layer review) and ROADMAP.md
                 (plan and progress of the tool-layer iteration), in Chinese
.github/         GitHub Actions workflow for the offline tests
PROJECT.md       the assistant's role and rules (Chinese)
AGENTS.md        instructions for AI coding assistants (Chinese)
HANDOFF.md       handoff notes: status, data contracts, design decisions, known issues (Chinese)
HOWTO.md         step-by-step guide with commands and prompts (Chinese / English)
LICENSE          MIT License
CITATION.cff     citation metadata
```
