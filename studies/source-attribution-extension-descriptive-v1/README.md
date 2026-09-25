# Source-attribution descriptive extension

Private preparation of a package for public preregistration, prior to collecting the extension's scientific data.

Start with [the readable Italian protocol](PROTOCOLLO.md) or [the full registration text](PREREGISTRATION.md). The [operations guide](OPERATIONS.md) explains verification, publication-before-collection, safe resumption and private reporting.

The design contains **1,664 new slots**, 16 blocks, three topics and twelve eligible case/configuration panels. German debt-brake and Swiss nuclear texts are tested on GPT-4o, Sonnet 4.5, Sol and Sonnet 5. US AI texts are tested on the two new models with reasoning off and with Sol medium/Sonnet 5 high. Historical US data are retained as a separate cohort.

- `materials/`: exact English texts, sources, historical provenance and unchanged American message lists.
- `plan.json`: exact payloads, hashes, order, retry/suspension/budget policy and descriptive comparisons.
- `code/`: collector, report and offline tests adapted from the preceding public study.
- `verification/`: synthetic rehearsal evidence, passing tests and neutral technical-check summary; no scientific responses.
- `ENVIRONMENT.json`: observed dependencies.
- `MANIFEST.json`: SHA256 of each file in this local snapshot. This is file identification, not notarial certification or scientific validation.

No API credentials, private conversations, Giano identifiers or implementation, launch receipt, scientific raw data or results are included. No publication is established merely by creating this folder. Once the manifest is finalized, publish an exact copy and do not edit it in place. Record actual publication evidence privately before starting the collector.

SHA256 hashes of files operate on their exact bytes. Structured payload hashes use UTF-8 JSON with sorted keys, compact separators, Unicode retained and non-finite numbers forbidden; see `code/trace.py`. Anyone can reproduce the hashes without access to Giano.

`design.py` and `trace.py` are retained from the previous public package because the parser and artifact helpers import them. Historical candidate settings or logging routines in those modules do not supersede `plan.json` and this registration. No legacy experiment runner is invoked.
