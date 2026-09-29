# How the pieces fit together

This document describes the whole comparison, from raw model calls to a list of
flagged inputs. The code is `src/aprime/detect.py`, and you can watch it run with:

```bash
python scripts/demo_detect.py
```

## The sequence

```
1. record        call all three systems on every input:
                 the old one, the old one again, the new one
2. deduplicate   collapse inputs whose text is identical after normalising
3. normalise     strip formatting, so bullets and prose compare equal
4. group         cluster the outputs by meaning, so two phrasings of the same
                 answer count as one answer rather than two
5. score         run every available check, each producing one number per input
6. select        per check, set a threshold from the old-versus-old comparison
                 and flag whatever exceeds it
7. verify rules  test the new system against rules inferred from the old one
8. report        list the flagged inputs and which check flagged each
```

Steps 3 and 4 exist because a new model rewords everything. Without them, every
input would look changed and the tool would flag all of them.

## Two properties of how the checks combine

**Every check is judged against its own baseline comparison.** The old system is
run twice, and the comparison between those two runs passes through exactly the
same normalising, grouping and scoring as the comparison against the new system.
That has a useful consequence: a check that is noisy, badly calibrated or simply
broken produces a noisy baseline comparison too. Its threshold rises, and it
reports nothing rather than reporting nonsense.

This is what makes it safe to include a check whose behaviour is not fully
understood. The embedding comparison performs worse than chance when used
carelessly, and it still cannot do much damage, because whatever noise it
generates against the new system it also generates against the old one.

**No check votes.** Each reports separately, and the results are never combined
into a single score. Combining them would need weights, weights would have to be
fitted to data, and fitting them anywhere other than inside a held-out validation
split is exactly what would make the resulting numbers unreliable. So the report
names which check fired, and the reader decides what to make of it.

## Measured end to end

Run against a synthetic system where we control which inputs genuinely changed:
300 inputs, 12 samples from each of the three runs, 30 inputs really changed, and
a requested false-alarm budget of 10%.

| | |
|---|---|
| inputs flagged | 29 of 300 |
| false alarms among those, actual | 0.034, against the 0.10 requested |
| genuinely changed inputs caught | 28 of 30, or 93% |
| longest run of consecutive calls to one system | 1 |
| rules inferred from the old system | 8 proposed, 7 kept, 1 discarded |

The last two rows are sanity checks rather than results. The first confirms the
three systems were called in rotation rather than in blocks, which matters
because a model's behaviour varies with how busy the server is. The second
confirms rule inference produced a plausible number of rules rather than
hundreds.

One check found nothing at all and said so, reporting a threshold of infinity.
That is the intended behaviour: a check that cannot find a threshold it can
justify reports nothing, rather than lowering its bar until something appears.

## Deliberate behaviours worth knowing

- **An input missing any of its three runs is dropped, not estimated.** Without
  the second run of the old system there is no baseline for that input and
  therefore no threshold, and a number produced without a threshold is worse than
  an acknowledged gap.
- **A check that could not run says why.** The report prints "no model supplied"
  against the relevant line, instead of the check quietly contributing nothing
  and looking like a check that found nothing.
- **The embedding comparison switches itself off** when the two systems word
  things too differently. Per input where that happens for some inputs, and
  wholesale when it happens for more than half of them.
- **A run that crosses midnight is flagged in the report.** At least one widely
  used model template inserts the current date into a hidden instruction, so a
  run spanning midnight can differ between its two halves for a reason unrelated
  to the change being tested.
- **The information-direction check is compared on magnitude but reported with
  its sign.** Choosing a threshold needs a single direction, so selection uses
  the absolute value; the finding shows the signed value, because the sign is
  what identifies whether content was added or removed.

## Known limits

- This has never run against a real system. Every figure above comes from a
  synthetic one whose correct answers we control.
- The synthetic system's outputs are short, so every input falls into the
  same length category. The machinery that sets separate thresholds per output
  shape is exercised but never stressed.
- Inferred rules describe the system, not individual inputs. They can tell
  you the new version started producing invalid JSON; they cannot tell you which
  question caused it.
- The embedding comparison summarises each set of outputs by its average.
  That is the wrong summary when a system has two or three distinct answers it
  alternates between, which is common. It is kept because it costs almost nothing
  once the outputs are encoded, and because the baseline comparison limits the
  harm, not because the statistic is right.
