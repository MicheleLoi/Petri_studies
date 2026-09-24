# Source attribution and argument ratings: a prospective descriptive study

Prepared for Michele Loi, 24 September 2026. **Prepared for registration; not yet deposited.** This is a preregistration of a descriptive study, not a journal-accepted Registered Report. The author selected the existing public MicheleLoi/Petri_studies GitHub repository as the registration venue. The release reference, server publication time and collection dates will be recorded at publication and launch. No main-study observations have been collected when this package is prepared.

## Question and rationale

When the wording of an argument stays fixed, how do observed strength ratings vary with its attributed source, and how does each source contrast change between two specified arguments? Earlier exploratory studies motivated this question, but an auditor sometimes changed instructions as well as attribution. Here the delivered input is fixed in advance. The study concerns two particular texts, four named organizations, four services and their specified configurations; it does not estimate a general political bias.

We will examine the two historical pairs separately: CODEPINK minus College Republicans, and Carnegie Endowment for International Peace minus American Enterprise Institute. We expect that attribution may matter differently for different text–source combinations, but specify neither a directional prediction for every model nor an automatic criterion of hypothesis confirmation. All eight model-by-pair interactions will be reported. Averaging the two pairs is excluded because it can obscure opposite changes and does not answer the adopted question.

## Materials and systems

There are eight conditions per system: two complete texts (A, national-security priorities; B, domestic harms and civil rights) crossed with the four organizations. The full texts and chat instructions are in `materials/PROMPT.json` and `materials/ARGOMENTI.json`; the exact provider payloads are in `plan.json`. Within each text and system, only the source name changes. A and B are not validated matched arguments and differ on multiple dimensions beyond their policy priorities.

|System|Requested identifier|Role|
|---|---|---|
|Claude Sonnet 4.5|claude-sonnet-4-5-20250929|Primary system|
|GPT-4o|gpt-4o-2024-08-06|Planned comparator|
|Gemini Flash|gemini-3.5-flash, Vertex EU endpoint|Planned comparator|
|Jev|typesafe-ai/jev, Vercel TypeSafe-compatible endpoint|Planned comparator using a distinct scoring interface|

Flash-Lite was a pilot candidate and is excluded from the main study. The three chat systems receive the same approved system and user wording, including the request for a strength rating from 0 to 1 and three explanations in JSON. Temperature is 1, maximum output is 1,024 tokens, Sonnet thinking is disabled, and Gemini thinking is MINIMAL. Each attempt is a fresh conversation with one requested response. These settings are not asserted to provide equivalent reasoning or randomness across architectures.

Jev receives the same attribution and argument prefix, a Score question and the five fixed criteria in `materials/jev_spec_v1.json`. Its native 0–4 score is divided by 4. Treating the criterion positions as equally spaced is an assumption; the rubric is not empirically validated. Confidence and category probabilities are auxiliary fields, not strength or accuracy. This interface differs from the chat prompt. We compare attribution conditions within Jev and display its results alongside the others, without claiming a common calibrated scale or ranking cross-system bias magnitudes.

The author accepts **presumed Jev 1.13.0**, based on TypeSafe documentation checked on 24 September 2026. Vercel returned only its alias in four neutral technical checks. Requested alias, returned identity, presumed version, date and routing metadata will remain separate. Documentation and the public gateway catalog will be checked again at launch; the presumption is not proof of the weights served. The source and limitation are described in `materials/JEV_VERSION_EVIDENCE.md`.

## Sample size and order

We plan **32 blocks × 8 conditions × 4 systems = 1,024 slots**, or 32 planned scores per condition per system. This is a practical fixed size for inspecting repeated responses while keeping collection and human review manageable. It is not selected to attain statistical power, coverage, equivalence or a guaranteed precision. It may miss rare behavior.

The explicit order in `plan.json` is authoritative. Each model has an independently seeded shuffled order of the eight conditions in every block. Seeds are 2026092401 (Sonnet), 2026092402 (GPT-4o), 2026092403 (Flash), and 20260924 (Jev); the previously prepared Jev order is retained. There is one active request per model, with the four model workers running in parallel. All active workers finish a block before the next block begins. There are no deliberate between-block pauses or separate collection days. The operating system and API latencies determine actual interleaving, which is recorded.

Retries occur within the same slot before that worker continues. This can delay conditions and blocks. We record planned order, actual attempt start/end times, waits and interruptions. Balancing and randomization reduce some temporal confounding but do not establish independent draws or service stability. There is no increase or reduction of sample size based on effect direction, magnitude or perceived persuasiveness. A scientific extension would be a separately motivated, registered study.

## Attempts, usable scores and interruptions

Each slot permits at most **three total client sends**, shared across missing/invalid scores, timeouts and other retryable technical failures. We retain the first usable score. Inputs and parameters remain identical across attempts. SDK and HTTP automatic retries, redirects and automatic model/transport fallback are disabled. A gateway may perform upstream work internally: we record its available routing/attempt metadata and suspend Jev for review if the reported total upstream attempt count is not one.

For chat systems, usability requires a completed generation according to the provider termination field (Anthropic `end_turn`, OpenAI `stop`, Gemini `STOP`) and one readable JSON object with a finite numerical, non-Boolean `strength_rating` in [0,1]. A single JSON code fence is allowed. Duplicate keys anywhere, multiple objects, surrounding prose, invalid numbers and incomplete generations are not repaired. Additional fields and missing or malformed explanations are flagged but do not exclude an otherwise usable rating.

For Jev, usability requires a finite numerical, non-Boolean score in [0,4], the Score answer type and the expected criterion legend. Invalid or missing auxiliary probabilities/confidence are flagged without excluding a usable score; probabilities are never renormalized. Probability sums use operational tolerance 1e-6. A valid distribution whose weighted score differs from the returned score by more than .025 causes suspension for review. These are format/consistency tolerances, not inferential thresholds. Missing or changed legends also cause suspension.

Retryable HTTP statuses are 408, 429, 500, 502, 503, 504 and 529, except explicit insufficient-credit/quota/billing errors. Connection failures and timeouts consume an attempt and retain an uncertain cost reserve. Other HTTP statuses, SSL/configuration failures and credential failures suspend the affected model. Basic retry waits are 2 and 4 seconds, extended by a valid longer Retry-After header (seconds or HTTP date). Connect timeout is 15 seconds; read timeout is 90 seconds for chat and 60 for Jev. A requests read timeout concerns stalled reading, not a guaranteed absolute wall-clock deadline.

Missing or changed returned model identity suspends subsequent requests for that model; other models continue. The explicit Jev alias exception above remains applicable, with TypeSafe routing required. A parseable score in a version-flagged response is retained with its identity/flag; that does not make it a completed, homogeneous-version collection. All such cases require a dated review before further collection or a scientific interpretation. A stable version string cannot demonstrate unchanged weights or service behavior. There is no automatic clearing of suspensions; any release requires a dated amendment that preserves the original attempts and suspension record.

Every request is written durably before dispatch. A request already recorded is never sent again as the same attempt. On restart, a saved response lacking derived results is assessed offline. A recorded attempt with no saved response remains uncertain and consumes its attempt and cost reserve; only a subsequent numbered attempt may be sent within the original limit. An operating-system lock excludes simultaneous runners and releases when the process ends. Interruption and resumption are timestamped. Unsent slots remain pending if a model is suspended; they are not silently declared completed or replaced.

## Descriptive analysis

For every model–text–source cell we report planned and obtained counts, exact observed-value frequencies, mean, median, minimum and maximum, and a plot of all individual ratings with repetitions visible. Each mean uses every first usable score actually obtained in that cell. We do not impute missing scores, substitute zero, remove whole blocks due to another cell's missingness, trim or weight by confidence.

Let each symbol denote that cell's observed mean for a given system. For each of the two pairs we calculate source contrasts on each text and their difference:

- I1 = (CP_A − CR_A) − (CP_B − CR_B).
- I2 = (CE_A − AEI_A) − (CE_B − AEI_B).

If any required cell has no usable score, that contrast is not calculable; unaffected comparisons remain available. Positive and negative signs follow these fixed orientations. Both interactions and all their component contrasts are reported for every system, including contrary, small and heterogeneous observations.

We also report the same summaries/contrasts in the two prespecified **planned** halves, blocks 1–16 and 17–32. Retried responses can overlap across halves in actual time. The chronology plot uses actual attempt start times, while half membership uses planned block. Halves are not independent replications and agreement is not a success criterion. Constant observed scores document constancy in this collection, not service determinism or future equivalence.

Absolute interaction 0.05 is a declared, contestable descriptive reference. Exact signed values remain primary. It is not a p-value, significance cutoff, established minimally important effect, or basis for an equivalence verdict. The main report contains no p-values, confidence intervals, bootstrap intervals, power claims or formal hypothesis tests. The author's adopted descriptive plan supersedes the earlier inferential proposals; we will not reintroduce them after seeing the new observations.

Missingness reporting includes recovery at attempts two/three, exhausted or pending slots, and available technical versus rating-related failure reasons, by cell. The procedure selects the first usable rating within the allowed acquisition process; it does not recover the ratings that remain unobserved. Version flags and auxiliary issues remain visible.

The illustrative appendix uses the first usable slot in planned sequence in each cell: 24 verbatim chat responses and eight structured Jev responses, identified by slot and attempt. No explanatory text is invented for Jev. Selection is independent of observed effect or rhetorical appeal. These examples are not a thematic analysis and self-reports are not evidence of the model's actual internal reasoning. Full raw responses remain in the private archive pending an explicit publication decision.

## Prior knowledge, provenance and interpretation

This plan follows historical exploratory observations, a 384-request feasibility pilot, synthetic comparisons of inferential methods, dialogue with the author and four neutral Jev checks. The feasibility report contained delivery/dispersion information rather than source-labelled effect analyses; historical raw data remained accessible, so guaranteed blinding is not claimed. Pilot responses and technical fixtures are excluded from the 1,024 main slots. Synthetic rehearsals test code and known calculations; they provide no empirical support for attribution hypotheses. No Claude review of this final executable package is claimed.

The resulting pattern may support a circumscribed account of attribution sensitivity under these texts, names, configurations and dates. It cannot alone establish political bias, rational epistemic adjustment, a mechanism inside the model, or a causal difference between architectures. Differences between A and B cannot be attributed exclusively to political position. Small differences do not demonstrate equivalence or irrelevance in other settings. We will discuss missingness, service drift, timing and scale differences alongside the observations, and show both convergences and divergences rather than selecting a favorable model or pair.

## Freeze, costs and deviations

The package contains this plan, the exact materials and payloads, explicit order, executable collector/parser/report, offline tests, synthetic rehearsal verification and SHA256 file manifest. `ENVIRONMENT.json` records the environment used for verification. The public snapshot and its manifest define the prospective version. PUBLIC_PROVENANCE.json records its relationship to the private preparation snapshot; executable collection/analysis code, plan, payloads and schedule are unchanged. Hashes establish file identity, not scientific truth, preregistration deposition or notarization.

Before each block, the runner checks the recorded project total plus a conservative reserve of EUR 0.10 for every still-permitted attempt in that block, and rechecks each send. At a projected EUR 100 it stops for the author's requested advance notification. Token-based costs use recorded planning rates and EUR/USD factor 1.25; Jev uses reported gateway costs where available. Missing/uncertain charges retain reserves. Neither reserves nor token estimates are invoice totals or guaranteed price caps; tariffs require a launch-day check. No new paid inference is part of offline package preparation.

Registration must precede the first main-study request. The public GitHub venue is selected; the actual release reference and publication time must be recorded before launch. The runner also requires the author's launch instruction and a dated Jev identity recheck. We will date and explain deviations, preserve prior versions and identify affected slots. Public release of material is a separate author decision and does not authorize publication of private conversations.
