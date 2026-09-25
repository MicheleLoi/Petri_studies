# Source attribution across topics and model configurations

Prepared 25 September 2026. This local package is prepared for prospective public registration; it is not yet a published registration. No extension study responses have been collected. Neutral technical checks are excluded from the study.

## Question and scope

For identical argument wording, does changing the attributed source change the strength rating, and does that source contrast differ between two arguments? We examine whether the resulting pattern is consistent with a penalty for perceived incongruity between a source and its attributed position (coherence bias). The interpretive argument also considers the explanations returned by the models and historical exploratory work. An interaction alone does not identify that mechanism uniquely.

This is a descriptive extension of [source-attribution-descriptive-v1](https://github.com/MicheleLoi/Petri_studies/releases/tag/preregistered-source-attribution-descriptive-v1), package commit `b52bec9bec5e22b287f3da9cdabc99e0faac2958`. It preserves fresh contexts, named-source attribution, two texts, separate source pairs, rating policy, randomized complete blocks and descriptive reporting. The deliberately adopted changes are topics and models, a fifth German source, 16 rather than 32 blocks, and a limited reasoning configuration comparison. There is no anonymous-source condition.

Topics and identities are purposively selected following exploratory work and documentary evaluation, including a search for a clearer parallel between political organizations and specialist organizations. They are not a random sample of topics, sources or models. German debt-brake arguments and the Swiss pro-nuclear argument are historical English stimuli; the Swiss opposing argument was newly written and adopted before collection. No translation or factual modernization is performed. Preserving a historical claim does not endorse its correctness today. Argument orientation, rhetorical quality and factual content are not independently manipulated.

## Fixed collection matrix

Each block contains every eligible source × text combination for a given model configuration. Sixteen complete blocks are scheduled. A slot is one planned cell observation, not one API attempt; a slot may consume up to three attempts under the rule below.

| Case | Sources | Texts | Configurations | Blocks | Planned slots |
|---|---:|---:|---:|---:|---:|
| German debt brake | 5 | 2 | 4 without reasoning | 16 | 640 |
| Swiss nuclear policy | 4 | 2 | 4 without reasoning | 16 | 512 |
| US AI policy | 4 | 2 | Sol and Sonnet 5 without reasoning | 16 | 256 |
| US AI policy | 4 | 2 | Sol medium and Sonnet 5 high | 16 | 256 |
| **Total** | | | | | **1,664** |

The four main models are `gpt-4o-2024-08-06`, `claude-sonnet-4-5-20250929`, `gpt-6-sol` and `claude-sonnet-5`. The previous US study on GPT-4o, Sonnet 4.5, Gemini and Jev is retained separately with all 32 observations per cell; those collections are not repeated. No new German/Swiss AI case or Gemini/Jev request is included. Sonnet 4.5 provides continuity with the preceding US study; it is not the historical Sonnet 4 used in the original German/Swiss explorations.

Sixteen is a prospective pragmatic resource allocation, informed by prior exploration and descriptive stability checks, not a sample size derived from an inferential power target. It is fixed before extension data collection. We will not enlarge only promising, borderline or inconvenient cases after seeing results. Any later study would be a separately documented collection. An exploratory post hoc p-value check of the preceding US data is not part of that study's original registration or this extension's planned analysis.

## Stimuli, sources and contrasts

`materials/ARGUMENTS.json` fixes all six English texts with UTF-8 hashes and provenance. `materials/CASES.json` fixes the names shown to models. `plan.json` contains the complete API payload for every eligible condition and its hash. US message lists exactly preserve those in the previous public package; the German/Swiss prompts replace the topic and organization and insert the adopted arguments into the same template. All source attributions are experimental manipulations, not purported authentic quotations.

| Case | Text A / text B | Separate source pairs |
|---|---|---|
| Germany | Reform debt brake / maintain debt brake | Grüne Jugend − Junge Liberale; DIW Berlin − ifo Institut; AfD − Junge Liberale |
| Switzerland | Reconsider nuclear power / prioritize alternatives and maintain phase-out | Junge Grüne Schweiz − Jungfreisinnige Schweiz; SES − Avenir Suisse |
| United States | Prioritize national security / prioritize domestic rights and accountability | CODEPINK − College Republicans; Carnegie − AEI |

For each pair L/R, report the source contrast on each text, ΔA = mean(L,A) − mean(R,A) and ΔB = mean(L,B) − mean(R,B), then I = ΔA − ΔB. Report both component contrasts and I, together with all individual cell summaries. Do not pool the pairs or the German political sources into one average. AfD − Grüne Jugend is not an additional prespecified contrast.

The AfD comparison asks whether sources broadly aligned on maintaining the debt brake receive different treatment of the same arguments, and whether that difference depends on the argument. AfD is a national party whereas Junge Liberale is a youth organization; reputation, familiarity and perceived competence are not held constant. Political versus specialist organization and anticipated prestige are interpretive assumptions, not independently validated treatments. The specific organization names and arguments are the scope of observation.

## Configurations and API constraints

All contexts are new and contain only the fixed system and user messages. No tools, browsing, memory, preceding responses or cross-slot conversation are supplied. The prompt asks for a strength rating in [0,1], strongest point, weakest point and overall assessment in JSON.

| Configuration | Reasoning | Generation cap | Sampling |
|---|---|---:|---|
| GPT-4o | No reasoning setting | 1,024 | temperature 1 |
| Sonnet 4.5 | Explicitly disabled | 1,024 | temperature 1 |
| Sol | none | 1,024 | temperature 1 |
| Sonnet 5 | Explicitly disabled | 1,024 | Native default; sampling parameters omitted |
| Sol reasoning | medium | 8,192 | temperature omitted as required by API |
| Sonnet 5 reasoning | adaptive, high | 8,192 | Native default; sampling parameters omitted |

Generation caps in the reasoning conditions include reasoning and response tokens. The author chose to retain the original cap in main conditions and increase it only for reasoning. Consequently, the on/off comparison is between these declared configurations, which differ in reasoning, generation allowance and necessary API adaptations. It is not an isolated causal estimate of internal reasoning or equal computation across providers. A cap is not a target response length. Native tokenizer differences are retained. Neutral checks produced complete parseable responses in all four new configurations; they do not guarantee nontruncation on every study request.

The exact returned model ID is checked on each response. Sol and Sonnet 5 are currently provider model IDs without a separately adopted dated snapshot; matching the ID does not certify an immutable backend. A missing or changed ID suspends all configurations of that base model. No automatic substitute is used. All version warnings and any usable rating returned with a warning are retained for transparent review.

## Scheduling and acquisition

The explicit schedule in `plan.json` is authoritative. For each of four base models, independently seeded randomization shuffles all its eligible case/cell/configuration slots within each of 16 blocks. Sol and Sonnet 5 on/off AI slots are thus interspersed. Four workers may operate concurrently, but at most one API call per base model is active; the next global block starts only when all active workers finish the current one. There are no deliberate gaps. Longer reasoning requests can still affect elapsed time, which is recorded. Blocks and halves are not assumed independent replications.

Within a slot, retain the first usable rating from at most three total client sends, counting both technical failures and unusable responses. Retry transient HTTP responses 408/429/500/502/503/504/529, connection errors and timeouts within that total. Honor Retry-After or the planned 2/4-second delay. Other configuration, credentials, billing or version failures suspend the base model; other models may continue. Suspensions persist across restarts and cannot be silently cleared. Any change requires a dated amendment before affected collection resumes.

Persist each request before sending it. Never resend an existing request as the same attempt. After interruption, re-assess any saved response offline; preserve an attempt without a response as uncertain and count its cost reserve. Continue only with the next permitted attempt. The operating-system lock prevents duplicate runners and is never deleted to force access. Timeouts are 15 seconds to connect, 90 seconds to read in main conditions and 180 seconds with reasoning; uncertain timed-out sends are preserved, not treated as free.

Use only complete generations containing one parseable JSON object (a single JSON Markdown fence is accepted). The designated `strength_rating` must be a finite numeric value in [0,1], not a Boolean. Invalid/missing explanations or extra fields are flagged but do not discard an otherwise valid primary rating. Duplicate JSON keys, malformed JSON, missing/invalid ratings and incomplete generation make the attempt unusable. Do not repair prose, extract a convenient alternative score or impute missing slots. Analyze all obtained valid ratings; unequal obtained counts do not cause deletion of other cells.

## Prespecified descriptive report

For every case × configuration, report planned and obtained counts, mean, median, range and exact rating frequencies in every cell; all the designated pair contrasts and interactions; the same summaries in fixed blocks 1–8 and 9–16; and actual acquisition chronology. Include every unsuccessful attempt, recovery, unknown-cost outcome, suspension and version warning in the operational record. The first usable response in planned sequence for each cell is the prespecified illustration; no selection by rhetorical appeal or effect size. All other responses remain available in the private archive. This does not introduce a new systematic qualitative coding scheme.

For US AI, additionally show on-minus-off cell means and on-minus-off interactions within Sol and Sonnet 5, accompanied by the configurations' full cell summaries. Place historical US results alongside new results as separate cohorts; do not pool them or discard half of the historical observations to equalize n. Time, service and version differences limit generation comparisons.

The magnitude reference |I| = 0.05 is a contestable descriptive assumption in rating units, not a p-value threshold, an equivalence margin used for a test, or a publication gate. No p-values, confidence intervals, formal significance or equivalence verdicts are planned for this extension. Report small, contrary and ambiguous patterns as well as large ones. Interpret coherence bias through the full pattern, explanations and competing accounts; do not automatically mark the hypothesis established. Because there is no anonymous baseline, differences are relative between named sources, not changes from an unattributed argument.

## Integrity, costs and release sequence

The package includes the collector, descriptive report and offline tests, exact input payloads, random order, dependency versions and SHA256 manifest. The report must be generated using that same published code in a new private output directory. Registration publication must precede the first scientific request, documented by a genuine publication reference and UTC timestamp in a private launch record covering the exact manifest. A local freeze is not public registration or a notarial attestation. Never revise the deposited package in place.

API credentials, private conversations, Giano identifiers/implementation, neutral raw checks and scientific responses are excluded from this package. Raw study data and reports remain private until separately authorized for publication. Giano receives proposals about decisions and artifacts; only the author approves them.

Cumulative cost monitoring includes previous study API costs, preparatory checks, the historical EU price adjustment and reserves for uncertain outcomes. Before a new block, reserve all remaining permitted attempts in that block; check again before every send. Notify the author before the projected cumulative value including that reserve reaches EUR 100. Estimates use recorded token usage and USD × 1.25 as a planning convention, not an exchange-rate observation or verified invoice. Output tokens charged for reasoning are included. No fixed worst-case whole-study spending authorization is inferred from sample size.
