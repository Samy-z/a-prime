# Does label-free regression detection transfer across domains?

*Draft in progress. Sections 3, 4 and 9 are drafted; the rest follow
`docs/reader/paper-outline.md`. Section numbers match the outline. Because
sections 1 and 2 are not written yet, a few terms they will introduce are
defined again here where first needed.*

---

## 3. The idea: run the baseline twice

Suppose you have a system that calls a language model, and you are about to
change something behind it: the model, the prompt, a retrieval index. Call the
version you trust the **baseline** and the version you are about to ship the
**candidate**. You have a few hundred inputs that your system actually sees.
You have no labels for them, and no reference answers, because almost nobody
does for their own domain. The question is which inputs now get a different
behaviour, and how often you will be wrong when you say so.

The hard part is not finding differences. A new model rewords everything, so
every output differs from the one before it. The hard part is knowing which
differences are bigger than the ordinary variation the baseline already shows
from one call to the next. That needs a measurement of ordinary variation, and
the baseline can provide it.

So before comparing the baseline to the candidate, run the baseline against
itself a second time. Three runs in all: the baseline, the baseline again, and
the candidate. We call the second baseline run the **decoy** arm, borrowing a
word from the field that invented the trick: a decoy is a comparison in which
nothing changed, run so that its differences can stand for noise. Any
difference the decoy shows against the first baseline run is noise by
construction, because nothing changed between them. That noise is the yardstick. A difference between the
baseline and the candidate counts only if it is larger than the differences
the baseline shows against itself.

### Samples, clouds and checks

Each run calls the system more than once per input, because a language model
answers the same question differently on different calls. We call each answer
a **sample** and the set of samples for one input from one run a **cloud**. A
cloud is what gets compared, never a single answer.

A **check** is one way of turning two clouds into a number that is larger when
the clouds differ more. The simplest one counts how the answers are shared out
between distinct answers and asks how much of that share moved. Section 4
describes the checks that read meaning rather than wording. Every check is
scored twice per input: once for the baseline against the candidate, giving a
**target** score, and once for the baseline against the decoy, giving a
**decoy** score. The decoy scores are the distribution of this check's
nonsense, measured on the same inputs, the same models and the same day.

### What a false discovery rate is, and how the decoys set one

Suppose the tool flags forty inputs as changed. The **false discovery rate** is
the share of those forty that did not really change. You choose a budget for
it before you run anything, written `q`. At the default `q = 0.10`, you are
asking that at most about one flagged input in ten be a false alarm.

The decoys turn that budget into a threshold. Picture every target score and
every decoy score sorted on one line. Slide a cut down from the top. At any
cut, count the targets above it and the decoys above it. A decoy above the cut
is a false alarm that we can see, because we know it is noise, so the decoys
above the cut estimate how many of the targets above it are noise too. The
estimate is

    (decoys above the cut + 1) / (targets above the cut)

and the tool takes the lowest cut at which that estimate is still within `q`.
Everything above that cut is flagged. If no cut qualifies, nothing is flagged.

The `+ 1` is deliberate. Without it, a cut with no decoys above it and one
target above it would claim a false discovery rate of zero on the strength of
one lucky draw. The correction is the one proposed by Barber and Candès in the
knockoff literature, and the whole construction is the target-decoy method
from protein identification by mass spectrometry, where it has been standard
since the mid-2000s. We have not found a prior use of it for comparing two
versions of a language-model system.

The textbook alternative for controlling a false discovery rate is the
Benjamini-Hochberg procedure, which works from p-values. We do not use it, for
a reason that matters in production. Its guarantee depends on how the inputs
depend on each other, and a corpus drawn from real traffic is full of near
duplicates with lumpy dependence that nobody has characterised. The decoys do
not need that dependence characterised, because they are subject to it too.
They also need no distributional assumption and no p-value: any check works
as long as a larger number means more different.

### The floor: the tool cannot report fewer than ten changed inputs

The `+ 1` has a consequence that is arithmetic, not a tuning choice. Even with
no decoys above the cut, the best estimate the tool can make is `1 / targets
above`. At `q = 0.10` that is within budget only once ten targets are above the
cut. At `q = 0.05`, twenty. So the tool cannot report a single changed input,
or any number below `1 / q`.

This is the most important thing to know before using it. An empty report
means fewer than ten inputs cleared the bar. It does not mean nothing changed,
and the two cannot be told apart from the report alone. If what you need is to
catch one specific broken input, compare that input's outputs directly and do
not use this.

It also sets the size of the input set you need. Write `a` for the share of
your inputs on which a change actually fires, and `s` for the share of those
that then clear every decoy. The set must satisfy

    n  ≥  (1 / q) / (a · s)

A worked case from the first run against a real system: thirty inputs, four
samples per cloud, a stale-data fault that fired on fifteen of the thirty.
Two different checks each put nine inputs above every decoy and a third put
eight, with no decoy above the cut in any of them, which is as clean a
separation as the method can produce. Nine is one short of ten, so the best
estimate was `1 / 9 = 0.111`, just over the budget of `0.100`, and the report
said nothing. The report now says why, next to each check
(section 8).

The `s` term is set by how finely a check can score. With four samples per
cloud, the share-of-answers check can only take the values 0, ¼, ½, ¾ and 1, so
most of the fifteen fired inputs landed on the one value with no decoy above
it and the rest fell short. More samples per cloud make the statistic finer;
more inputs make more of them fire. Both help, and they are not
interchangeable, because only the first fixes the coarseness.

### Twenty samples per cloud, not ten

On a synthetic system where we control exactly which inputs changed, we
measured how often a moderate change is caught at the `0.10` budget. With ten
samples per cloud the answer was 8 percent. With twenty it was 73 percent. With
forty, 98 percent. Ten is a floor from counting arguments and it is
indistinguishable from nothing in practice. The working minimum is twenty,
which means sixty model calls per input across the three runs. Budget for that
and reduce the number of inputs before reducing samples per cloud, because the
sample count is what the statistic stands on.

### The seed

Many deployments leave the sampling seed unset, and some pin it for caching or
audit. The three runs should do whatever the deployment does, and the tool
records which. There is one configuration to refuse: both baseline runs pinned
to the same seed. We measured eight repeated calls with the same request under
a pinned seed and got two distinct outputs; with the seed unset, eight. A decoy
arm supported on two points cannot calibrate anything, and the failure is
silent, because the arms record cleanly and the false-discovery column fills
with confident numbers. The tool warns when it can see that both baseline arms
share a pinned seed. It cannot always see it, so the warning is a courtesy and
its absence is not a certificate.

### One threshold per output shape

The cut that gives a 5 percent false-alarm rate on one of the meaning checks
ranged from `0.011` on multi-sentence summaries to `0.888` on numbered lists of
reasoning steps, a factor of eighty. One threshold for all shapes would be
wrong for at least two of them. So the tool sorts inputs by the shape of the
baseline's output, short answer, JSON, list or prose, and calibrates each shape
on its own decoys. A shape with fewer than thirty inputs is pooled with the
others rather than given a threshold fitted to too little, which also means
the `1 / q` floor applies per shape. In every run so far there were fewer than
thirty inputs per shape, so the per-shape machinery is exercised and has never
been stressed.

### Does the promise hold?

The only place a false discovery rate can be checked is a system whose true
answer is known, which no real system provides. On a synthetic one with known
ground truth, across nine combinations of sample count and change size, asking
for at most 10 percent false alarms produced 10.1 percent or less in every
cell. On the worked example that ships with the code, three hundred inputs of
which thirty really changed, the tool flagged twenty-nine, of which one was a
false alarm: 3.4 percent against the 10 percent budget, catching 28 of the 30.

No check votes. Each reports on its own, because combining them would need
weights, weights would have to be fitted, and fitting them anywhere other than
inside the held-out validation described in section 7 is exactly what would
make the result untrustworthy. The report names which check fired on each
input, and the reader decides.

---

## 4. What each check sees, and what it misses

A check is only useful if we know which kinds of change it notices. To find
out, we need cases where the answer is known in advance. So we built 896 pairs
of texts by hand, from templates, where we decided what the relationship
between the two halves is. The relationship is one of three:

- **Preserving**, 256 pairs: only the wording differs. The same facts rendered
  as prose and as a bulleted list; a sentence replaced by a synonym; two
  independent sentences swapped. A good check ignores these.
- **Breaking**, 512 pairs: one fact differs and nothing else. A number, a
  date, a name, a unit, a quantifier such as *all* becoming *some*, a
  decision flipped, a negation inserted, or a condition deleted. A good check
  flags these.
- **Register**, 128 pairs: the facts are identical and the confidence of the
  text changed, by an added hedge or an added assertion. These are reported on
  their own, for a reason given below.

Each pair comes from one template with one deliberate difference, so nothing
varies except the thing we meant to vary. The pairs span four subject areas and
four output shapes, from thirty to about 150 words. The asymmetry between the
preserving and breaking pairs is deliberate. Preserving pairs change a lot of
wording and no facts; breaking pairs change one fact and no wording. That is
what swapping a model does: it rewrites the surface of every output and
changes the substance of a few, and the difficulty is telling those apart.

The pairs have their own tests, independent of any check, because a broken
pair and a blind check produce the same number. On first assembly those tests
found three kinds of pair whose two halves were silently identical, because
the intended change had nothing to act on in that output shape. Any of them
would have produced a clean, plausible finding such as "this check detects none
of the quantifier changes in short answers", and it would have been recorded
as a fact about the check.

### How the numbers are read

Two figures recur. A check is deployed at a false-alarm budget, so we set each
check's threshold at the point where it wrongly fires on 5 percent of the
preserving pairs, and then ask what share of each kind of breaking pair it
catches at that same threshold. We call that share the detection rate, and it
is always out of 64 pairs. Where a check is read at both ends, the budget is
2.5 percent per end.

The second figure is a ranking score, the probability that a randomly chosen
breaking pair scores higher than a randomly chosen preserving pair. A score of
1.0 is perfect, 0.5 is a coin flip, and below 0.5 means the check ranks
rewordings as more different than fact changes, which is worse than useless.

### Figure 1: the blind-spot map

[Figure 1: `docs/figures/blind_spot_map.svg`. Rows are checks, columns are
kinds of change, each cell the share of 64 pairs on which the check fired at
its budget. The grid compares three judging models on the same text; the block
under it is the configuration the tool ships with, where text is normalised
before judging. The bottom block lists the changes that were too small for
anything to see.]

### Comparing embeddings performs worse than chance

An embedding turns a text into a list of numbers, positioned so that texts
with similar meaning sit close together. Comparing the distance between two
outputs is the obvious check, and it was the first design's primary one.

Measured across three embedding models from three different families, the
ranking score was 0.39, 0.44 and 0.53: at or below a coin flip, in all three.
The failures are on the changes that matter most. On a changed number, a
changed date, an inserted negation or a changed quantifier, the detection rate
is 0 to 2 percent for all three models. Only a swapped name clears the noise,
at 34 to 56 percent, and a deleted condition at 6 to 31 percent, the latter
because deleting a sentence changes the length.

The mechanism is mundane. Rewording a sentence moves its embedding about
twenty times further than changing a number, a date or a negation inside it.
Measured with the smallest model, a paraphrase moved the text by 0.030 and a
changed fact by 0.002. So the check reliably reports that a harmless rewording
is a large change and that a flipped decision is a small one.

It recovers when the wording is stable. Compared against only the mildest
rewordings, a single substituted phrase, the same three models rank correctly
at 0.54, 0.61 and 0.82. So the check is not useless; it is conditional on the
new system phrasing things much like the old one, and that condition can be
measured. The tool therefore measures it, and switches the check off for any
input where the wording has drifted past the point at which it was shown to
work. A check that performs below chance is worse than no check, because
somebody will believe it.

### A model that reads two texts together catches seven of the eight

The replacement reads both texts at once. It is a model trained for **natural
language inference**: given two sentences, decide whether the second follows
from the first, contradicts it, or is unrelated. **Entailment** is the
relation where the second text follows from the first; **contradiction** is
the relation where the two cannot both be true. The check asks how strongly the
candidate's output contradicts the baseline's.

On raw text, the model we ship with catches every one of the 64 swapped
names, changed numbers, changed dates and inserted negations, 63 of 64 flipped
decisions, 57 of 64 changed quantifiers and 53 of 64 changed units. It holds
across the four output shapes and the four subject areas: the detection rate
over all seven kinds ranges from 96 to 98 percent per subject area, on 112
pairs each. That stability across subject matter is the first evidence bearing
on this paper's question, and on its own it settles nothing, because it covers
one judging model, one kind of system and four subjects.

### The eighth kind needs a different question

Of the 64 deleted conditions, contradiction catches none. The ranking score is
0.53, a coin flip. The reason is structural rather than a weakness of the
model. A text with a condition removed does not contradict the original. It
says less, and asked "do these contradict?", the model answers truthfully: no.

Asking a different question of the same model fixes it. Instead of
contradiction, measure the asymmetry in entailment: how much more the old
output implies the new one than the reverse. Read at its upper end, that
asymmetry catches 59 of 64 deleted conditions on raw text and 63 of 64 once
text is normalised, and it fires on 0 to 5 percent of every other breaking
kind. The two questions are complementary. Contradiction covers seven kinds and
misses deletion; entailment asymmetry covers deletion and almost nothing else.
Together they cover all eight, and both answers come from the same pair of
model passes, so the second costs nothing extra.

Read at its lower end, the same number catches added content. On the 64 pairs
with an added hedge and the 64 with an added assertion, the lower end fires on
every one, and on 4 percent of the breaking pairs taken together, though on
changed units and quantifiers alone it reaches 12 percent. So one number, read at
both ends, names two different faults: strongly positive means the new output
says less than the old, strongly negative means it says more. The first
implementation took the absolute value, which collapsed the two ends into one
and threw away the only part that identified the fault.

One caution travels with that result. The lower end is not a confidence
detector. Both register directions score negative because both add a clause,
so what is measured is the direction of information volume. Whether it can
tell an added hedge from an added fact is untested.

### Why register is reported on its own

An added hedge changes no fact, so calling it a breaking change would make
that group inconsistent. Calling it preserving would be worse. A change in how
confident a model sounds, with no change in what it says, is a documented
production failure: when a widely used assistant became noticeably sycophantic
in April 2025, every labelled test its developers ran passed, and the change
was rolled back after four days of user complaints. So these pairs are
measured and reported apart from both the false-alarm budget and the detection
rate, and the reader decides what to make of them.

An earlier version of the suite labelled added hedges as preserving. The
judging model refused to treat those pairs as equivalent 80 percent of the
time, which was the first hint the label was wrong.

### Normalising text first buys detection, not fewer false alarms

Reformatting prose as a bulleted list trips the contradiction check on 9 of
64 preserving pairs, and reformatting is among the commonest things a new
model does. So the tool strips presentation before judging: bullets, headings,
whitespace, case. On the figure that is the difference between the grid and
the block beneath it. With normalisation on, the contradiction check catches
all 64 changed units and all 64 changed quantifiers, and the entailment
asymmetry catches 63 of 64 deleted conditions, up from 53, 57 and 59.

What normalisation does not do is reduce false alarms. The total is pinned at
5 percent by the way the threshold is set, so the false alarms moved: from
reformatting, where there are now none, to substituted synonyms, 9 of 64, and
rewordings, 4 of 64. That is a worse place for them to live, because a
substituted word is harder to strip than a bullet, and it is why we report
normalisation as a gain in detection and never as a reduction in false alarms.

### These numbers describe a model, not a method

Substituting a second judging model trained for the same task, from a different
family, reproduced the direction of every finding above and none of the
magnitudes. On the same raw text, it catches 23 of 64 changed units where the
first model catches 53, 37 of 64 changed quantifiers against 57, and 49 of 64
flipped decisions against 63. On deleted conditions through entailment
asymmetry, 38 of 64 against 59. It also fires on 9 of 64 plain rewordings
where the first model fires on none. Individual kinds of change differ by up to
47 points.

So the judging model is a first-order design choice, not an implementation
detail, and every number in this section describes the model named in the
appendix. It also raises a question this study is not designed to answer. The
paper's claim is about whether detection survives a change of subject domain,
and we have direct evidence that it degrades across a change of judging model.
We say so here rather than let a reader assume otherwise.

The second model does catch 18 of 64 deleted conditions through contradiction,
where the first catches none. An earlier version of this work had generalised
one model's zero into a property of the technique. It is a property of that
model.

### Below these sizes, nothing fired

The map's bottom block lists what no check saw, because a map of coverage is
misleading without the floor under it.

- A shift in how often the system picks each of its answers, below about half
  of the share, at twenty samples per cloud. A shift of 0.3 was caught 0
  percent of the time at every sample count tested.
- Fewer than ten changed inputs at the default budget. Nothing can be
  reported, by the arithmetic of section 3, however clean the separation.
- A twelve-word hedge inside a 150-word output. No meaning check caught it; a
  rule about output length caught it incidentally.
- Corrupted characters appended to an otherwise correct output. No meaning
  check can see them, because a corrupted output means the same thing. Only
  the structural rules of section 5 catch them.
- Ten percent of retrieved rows corrupted. A controlled study on five hundred
  questions measured no downstream change at all at that level, so a miss
  there is not scored against the detector.

### What this measurement cannot say

The changes are synthetic and each alters one thing; real regressions combine
several, so these figures are probably optimistic. Only two judging models
were tested and they disagree by up to 47 points per kind of change; the
embedding finding is the more trustworthy of the two because it replicated
across three model families. The 5 percent budget is a convention, and a
different budget moves every detection rate. Everything is English and
generated from templates, and nothing here says anything about other languages
or about free text no template produced.

---

## 9. Honest limits

Each limit below is a measurement or an arithmetic fact, with its number. The
first four are the ones a reader must know before running the tool at all.

1. **The tool cannot report fewer than ten changed inputs at its default
   setting, so a single broken behaviour comes back as an empty report.** The
   false-alarm estimate adds one imaginary false alarm before dividing, so
   nothing clears a 10 percent budget until ten inputs are flagged. An empty
   report means fewer than ten inputs changed, not that none did, and the two
   cannot be told apart. Your input set must be large enough that at least
   ten of its inputs genuinely change when the system does.

2. **Twenty samples from each run is the real minimum, which is sixty model
   calls for every input you test.** At ten samples the tool caught 8 percent
   of moderate changes; at twenty, 73 percent; at forty, 98 percent. Cut the
   number of inputs before cutting samples per cloud.

3. **The figures describe our instruments, not the technique.** Most checks
   depend on one judging model. A second model of the same kind reproduced
   the direction of every finding and none of the magnitudes, with gaps of up
   to 47 points on individual kinds of change. Anyone reusing this should
   re-measure with their own judge.

4. **Nothing here has run against a production system.** Every figure comes
   from a synthetic system whose correct answers we control, from hand-built
   text pairs, or from one real system on which the first run fell under the
   ten-input floor. This is research in progress, not a tool with a track
   record.

5. **Small shifts are invisible, and we can say roughly how small.** A system
   that still produces the same set of answers but shifts how often it picks
   each by about 30 percent was not detected at any sample count. Below about
   a 50 percent shift, the share-of-answers check has nothing to say.

6. **A short hedge inside a long output is near-invisible to every meaning
   check.** A twelve-word hedge inside a 150-word output was caught only by a
   rule about length, incidentally.

7. **Corrupted characters are invisible to every meaning check.** A judging
   model correctly reads a corrupted output as meaning what the clean one
   means. Only the structural rules see this class of fault, and they are the
   only cover for it.

8. **Duplicate inputs are removed only when the wording matches.** Two
   phrasings of the same question count as two inputs. The false-alarm
   guarantee is computed by counting inputs, so undetected duplicates make the
   evidence look more independent than it is and the guarantee slightly
   optimistic.

9. **One threshold was set by judgement rather than measurement**: the one
   deciding whether the embedding check is trustworthy for a given pair of
   systems. It is marked as a guess in the code. Too loose, and it admits a
   check known to perform below chance; too tight, and it contributes nothing.

10. **The tool cannot tell a regression from an improvement.** Every check is
    symmetric in the baseline and the candidate, so swapping them gives the
    same scores. The entailment asymmetry is directional, but it measures
    more information against less, not better against worse. Deciding which
    way a change went is a human's job, and the tool only shortlists.

11. **Transfer across judging models degrades measurably, and the study is
    not designed to answer it.** The question we ask is whether detection
    survives a change of subject domain. We know already that it does not
    fully survive a change of judge.

12. **One output format resists per-shape thresholds.** The decision-line
    format in our test systems varies 36-fold in length where summaries vary
    3-fold. A threshold set per output shape has little to hold on to there,
    and the format obeys its own instruction on 4 of 12 attempts.

13. **Recall on prompt regressions is a lower bound.** For five of the six
    injected prompt edits, an input counts as affected whenever the edited
    prompt was sent and the model answered, whether or not the edit changed
    the answer. Inputs the model answered unchanged are scored as misses.
    Wrong-row retrieval faults draw their rows from the same domain; a
    retriever returning rows from an unrelated corpus is not modelled.

14. **The rule-pruning mechanism has not yet been exercised by a realistic
    system.** The synthetic system produced no coincidental rule for the decoy
    arm to prune. And a tightly induced rule can be tipped by an ordinary draw
    of the baseline: one shifted draw produced a 1 percent false-alarm rate
    on a candidate where nothing had changed. That is one draw, not a measured
    rate.

15. **Every run so far pooled all inputs into one threshold.** The per-shape
    machinery needs thirty inputs per output shape before it fits a separate
    threshold, and no run has had that many. It is tested and has never been
    stressed.

16. **Everything is English and generated from templates.** Nothing here
    speaks to other languages, or to free text that no template produced.

---

*Sections 1, 2, 5, 6, 7, 8, 10, 11 and 12 follow the outline and are not yet
drafted. Section 8 stays a table of gaps until the nine-cell study has run.*
