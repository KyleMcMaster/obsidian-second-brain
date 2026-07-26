# Retrieval quality baseline

Reference numbers for the vault search stack, measured with the honest eval
harness (`retrieval_eval.py`, all four mode labels true since the 2026-07
stress-test fixes). Re-measure against these before shipping any retrieval
change: **no retrieval change ships without before/after numbers on the same
cases** (the rule since stress-test fix 10).

Case sets are generated per-vault and are gitignored (they contain vault
content). The three reference sets: 35 English paraphrase questions
(`--generate --style semantic`), 30 English keyword lookups
(`--generate --style keyword`), and 16 hand-written Russian/Spanish
paraphrases. Metrics below were measured on the maintainer's ~2,350-note vault,
2026-07-11, embedding model `bge-m3`, fusion weight 20.

## Shipped default (`--mode default` - what the MCP serves)

| case set | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| EN paraphrase | 0.371 | 0.629 | 0.771 | 0.476 |
| EN keyword | 0.733 | 0.933 | 1.000 | 0.820 |
| RU/ES paraphrase | 0.188 | 0.625 | 0.625 | 0.377 |

Re-measured 2026-07-18 on the same three case sets after a week of live vault
growth: **stable, no regression**. EN paraphrase and EN keyword byte-identical
(EN paraphrase MRR 0.474, within noise); RU/ES improved slightly (recall@1
0.250, MRR 0.408). The index tracks vault changes without drift.

## Phase B start vs end (default mode)

Start = first honest measurement after the ruler fix (mxbai-embed-large, flat
1:1 fusion, mean-pooled whole-note vectors, no dispatch/freshness):

| case set | metric | start | end | change |
|---|---|---|---|---|
| EN paraphrase | MRR | 0.207 | 0.476 | +130% |
| EN paraphrase | recall@10 | 0.429 | 0.771 | +80% |
| EN keyword | MRR | 0.621 | 0.820 | +32% |
| EN keyword | recall@10 | 0.767 | 1.000 | perfect |
| RU/ES | MRR | 0.094 | 0.377 | x4 |
| RU/ES | recall@5 | 0.125 | 0.625 | x5 |

## All modes, end state (context for tuning)

Pure semantic slightly leads the default on paraphrase MRR (0.481 vs 0.476);
the default keeps the lexical arm as a tiebreak and as coverage for notes
written since the last index build, plus single-token dispatch (exact lookups
stay lexical) and the freshness re-rank. `--mode hybrid` (flat 1:1) is now
strictly worse than semantic everywhere and exists as a lab reference only.

What produced the gains, in order of impact: multilingual embedding model
(bge-m3), per-chunk vectors with identity headers + best-chunk scoring,
semantic-weighted fusion (w=20, swept per model), single-token dispatch,
freshness re-rank + status fade, 100% index coverage via adaptive splitting.

## How to re-measure

```bash
# per mode x case set; --generate NEW sets only with --force or a new --cases path
uv run python scripts/eval/retrieval_eval.py --mode default --cases scripts/eval/retrieval_cases.jsonl --json
```

## Rejected: type weighting on the fused rank (2026-07-26)

Fix 13/24 rejected multiplicative type weights applied to raw cosine: log notes
were deleted outright and recall halved. It was scored on the two English case
sets, which did not yet include the multilingual one, so the same idea was worth
re-testing at a different layer against the set it had never seen.

Hypothesis: RU/ES misses are not ranking failures but the canonical note losing
to a longer log about the same topic. Inspecting all 6 misses supports that -
the query for `Codru.md` returns `2026-06-27 - codru-team-second-brain-pos...`,
a log. The lexical arm already applies a type weight, but a Russian or Spanish
query shares no terms with an English note, so that arm contributes nothing and
the fused rank is effectively pure cosine with no type awareness.

Applied `_SEARCH_ENTITY_BOOST` / `_SEARCH_LOG_WEIGHT` to the RRF score rather
than to cosine, on the reasoning that RRF is rank-based and bounded so the same
weight is a far gentler nudge.

Measured on all three sets. It is worse everywhere, including the target:

| case set | metric | before | after |
|---|---|---|---|
| EN paraphrase | MRR | 0.474 | 0.335 |
| EN paraphrase | recall@1 | 0.371 | 0.171 |
| EN keyword | recall@10 | 1.000 | 0.833 |
| EN keyword | misses | 0 | 5 |
| RU/ES | MRR | 0.440 | 0.249 |
| RU/ES | misses | 6 | 7 |

Reverted. The likely reason it fails at either layer: a large share of correct
answers ARE logs and dailies, so a flat 0.5 on that type costs more than the
entity boost recovers. Fix 13/24's conclusion holds at the fusion layer too.

**O1 remains open.** The diagnosis stands - r@5 and r@10 are both exactly 0.625,
so for 6 of 16 cases the gold note never enters the candidate pool and no
re-ranking can reach it. Whatever fixes it has to change what the retrieval
stage surfaces, not how the results are ordered.

## Swept and left alone: entity boost / log weight (2026-07-26)

O2 asked why 19 of 35 EN paraphrase cases are missed or buried below rank 3.
Inspecting them shows the opposite pattern to the multilingual set: here an
ENTITY note wins when the answer lives in a log or concept note. "What fix
resolved the ClickFlow issue for Hailey" returns `Hailey Ingeman.md` rather than
the daily log recording the fix; "what process does Eric recommend" returns
`Eric Siu.md` rather than the concept note.

That points straight at `_SEARCH_ENTITY_BOOST` (1.5) and `_SEARCH_LOG_WEIGHT`
(0.5). Both are env-tunable, so the sweep needed no code change.

| entity / log | EN-para r@1 | r@5 | r@10 | MRR | misses |
|---|---|---|---|---|---|
| 1.5 / 0.5 (shipped) | 0.371 | 0.629 | 0.771 | 0.474 | 8 |
| 1.0 / 0.5 | 0.371 | 0.629 | 0.771 | 0.481 | 8 |
| 1.5 / 0.7 | 0.371 | 0.629 | 0.771 | 0.475 | 8 |
| 1.2 / 0.7 | 0.371 | 0.629 | 0.771 | 0.482 | 8 |
| 1.0 / 1.0 | 0.371 | 0.657 | 0.771 | 0.478 | 8 |
| 1.0 / 0.3 | 0.314 | 0.629 | 0.771 | 0.452 | 8 |

EN keyword and RU/ES were byte-identical across every setting tried.

**Defaults unchanged.** The best variant buys one extra case out of 35 on r@5
and 0.008 MRR. On a 35-case set that is noise, and moving a shipped default to
chase it is overfitting to this eval, not improving retrieval.

Two things the sweep did establish, which are worth more than the tuning would
have been:

1. **The type weights barely reach the fused result.** They apply to the lexical
   arm only, and in default mode the semantic arm dominates - which is also why
   the fusion-layer experiment above failed. Anyone reaching for these knobs to
   fix a default-mode ranking is pulling a lever that is mostly disconnected.

2. **The 8 misses are immovable by weighting.** The count is identical in all six
   configurations, so those cases are recall failures like O1's, not ranking
   failures. r@10 never moved either.

**O2 therefore reduces to the same open problem as O1**: the gold note is not in
the candidate pool, and nothing downstream of retrieval can put it there.
