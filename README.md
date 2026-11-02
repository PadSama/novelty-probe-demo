# novelty-probe

A fully logged, AI-assisted workflow for probing the literature around a research idea, built as a tutorial demo.

You describe an idea in one or two sentences. The pipeline breaks it into facets, builds Boolean queries, searches OpenAlex and Semantic Scholar, merges and deduplicates the results, maps the top candidates to each facet of the idea, and checks every DOI against Crossref.

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
| T4 Merge and deduplicate | `scripts/merge.py` | `results/merged/merged.json`, `results/merged/candidates.csv` (top 20) |
| T5 Evidence table and verification | `scripts/authors.py`, AI assistant, `scripts/verify.py` | `evidence/evidence_table.md`: each candidate labeled overlap / differ / unknown on every facet, with DOI checks |
| T6 Difference statement | AI assistant + you | `evidence/difference_statement.md` |

The five facets are research question, mechanism, context, data and methods, and expected findings. Each query has a purpose: *component*, *application*, *method*, or *concurrent* (recent work, 2023 onwards).

Steps that need judgment are done by an AI coding assistant run in this directory, from paste-ready prompts in `HOWTO.md`, and are meant to be reviewed by the researcher. The worked example used Claude Code; any assistant that follows `AGENTS.md` can do these steps, for example ZCode with GLM. These are T2, the facet labels in T5, and choosing the closest papers in T6. Everything else is a script.

## Quick start

**Requirements**

- Python 3.9 or later. The scripts use only the standard library.
- Network access to `api.openalex.org`, `api.semanticscholar.org`, `doi.org` and `api.crossref.org`.
- API keys, read from environment variables:
  - `OPENALEX_API_KEY`: strongly recommended. The free key avoids OpenAlex's shared daily budget.
  - `S2_API_KEY`: optional.

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
python3 scripts/logrun.py "T5 authors" -- python3 scripts/authors.py --top 10
```

4. Ask the assistant to write `evidence/evidence_table.md` (prompt in `HOWTO.md` §6). Then verify the DOIs:

```bash
python3 scripts/logrun.py "T5 verify" -- python3 scripts/verify.py
```

To run another round without overwriting the first, use version suffixes, for example `search.py --queries queries/queries_v2.json --suffix _v2` and `merge.py --suffix _v2` (`HOWTO.md` §8).

## How the scripts work

- **`search.py`** converts each generic Boolean query into each source's syntax:
  - OpenAlex: `filter=title_and_abstract.search` with the Boolean query kept and results ranked by relevance. Truncated words are replaced by full words, because OpenAlex rejects wildcards in its default stemmed search.
  - Semantic Scholar: `/graph/v1/paper/search/bulk`, with `AND` written as `+` and `OR` as `|`. Results are ranked by citation count, because this endpoint has no relevance ranking.

  For each query and source it saves the top 25 records (title, year, DOI, arXiv ID, venue, abstract), the exact query string sent, and the hit count reported by the API. It retries on HTTP 429 and 5xx, and fails fast when an API asks it to wait more than 60 seconds. `--dry-run` checks query syntax without network access.
- **`merge.py`** deduplicates records and ranks the candidates:
  - **Matching:** two records count as one work if they share a DOI, an arXiv ID, or a normalized title of at least five words. Matches chain together, so if A matches B and B matches C, all three are one work. Versioned preprint DOIs on OSF, TechRxiv and Research Square count as the same work.
  - **Provenance:** each work keeps references to its raw records (`raw_refs`). Merges based only on the title are flagged, and works with neither a DOI nor an arXiv ID are marked `UNVERIFIED`.
  - **Ranking:** candidates are ranked by "hits", the number of query × source result lists that contain the work.
- **`authors.py`** looks up authors by DOI in OpenAlex. The search results do not include authors.
- **`verify.py`** checks each DOI two ways and writes both results into the `verified` column:
  - It fetches the registered metadata through doi.org content negotiation and compares the registered title with the table's title.
  - It follows the DOI to the publisher's landing page and records the HTTP status and page title.
- **`logrun.py`** runs any command and appends the command and its output to `logs/RUN_LOG.md`.

## Tests

An offline self-test checks the scripts without network access. It also re-runs the merge on the committed raw results and confirms that the output matches the committed files byte for byte:

```bash
python3 -m unittest discover -s tests -v
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

Every decision, command and output is in `logs/RUN_LOG.md`, including mistakes and how they were fixed.

## Limitations

- Only the top 25 records per query and source are kept. For Semantic Scholar these are the most-cited matches, not the most relevant.
- The candidate ranking reflects agreement between the two sources, not relevance to the idea. In both rounds, all top-20 slots came from a group of tied works, so the tie-breakers decided the selection.
- Matching uses titles and abstracts only. A record without an abstract can only be found through its title.
- Facet labels are produced by an AI assistant from abstracts and need human review.
- In the cloud environment used for this run, publisher landing pages were not reachable, so verification relies on Crossref metadata.

## License

The code and documentation in this repository are released under the [MIT License](LICENSE). The search results in `results/` and `evidence/` include metadata and abstracts retrieved from OpenAlex and Semantic Scholar. Those abstracts remain under the copyright of their publishers or authors, and this license does not cover them.

## How to cite

If you use novelty-probe, please cite it using the metadata in [`CITATION.cff`](CITATION.cff). GitHub shows it under "Cite this repository".

## Repository layout

```
idea/            the idea (idea.md; idea_v2.md for round 2)
facets/          facet decomposition and search terms
queries/         Boolean queries (queries.json, queries_v2.json)
results/raw/     raw search results per source and query
results/merged/  deduplicated works and top-20 candidates
evidence/        evidence tables, authors, difference statement
logs/RUN_LOG.md  append-only log of every step
scripts/         search.py, merge.py, authors.py, verify.py, logrun.py
tests/           offline self-test
PROJECT.md       the assistant's role and rules (Chinese)
AGENTS.md        instructions for AI coding assistants (Chinese)
HANDOFF.md       handoff notes: status, data contracts, design decisions, known issues (Chinese)
HOWTO.md         step-by-step guide with commands and prompts (Chinese / English)
LICENSE          MIT License
CITATION.cff     citation metadata
```
