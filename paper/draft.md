# Does label-free regression detection transfer across domains?

*Draft in progress. Every section is drafted, section 8 against a partial
matrix with its gaps bracketed, with appendices A to F and an abstract whose
result is left blank; `docs/reader/paper-outline.md` maps each
claim to its backing.*

## Abstract

When the model behind a feature is swapped, re-prompted or re-indexed,
nothing in a normal test suite says which inputs now behave differently,
because the tests check the code and not the model's judgement, and nobody
has labels for their own domain. We describe a method that finds those inputs
from the output text alone, with a false-alarm rate the user chooses in
advance, and we ask whether such a method built on one domain still works when
moved to another, which no published work answers.

The method runs the old system twice. The second run is a comparison in which
nothing changed, so its differences are noise, and that noise sets the
threshold for the real comparison. Asking for at most 10 percent false alarms
produced 10.1 percent or fewer on a synthetic system where the truth is known,
across nine settings. The same second run prunes rules inferred from the old
system's own output, which catch a class of failure no meaning check can see.
Of eight kinds of factual change, one judging model catches seven at 83 to 100
percent of cases; the eighth, a deleted condition, needs the same model asked a
different question, and the sign of that answer names the fault. Comparing
embeddings, the obvious approach, performed below chance on three model
families.

[RESULT: across N systems spanning three domains and three output formats,
with every threshold chosen without sight of the held-out system, the detector
flagged changed inputs at the chosen budget and caught injected faults down to
severity s per class; performance on an unseen system is expected within
[lower, upper]. Filled from the nine-system study.]

Two limits matter most. The method cannot report fewer than ten changed
inputs at its default setting, by arithmetic, so an empty report means fewer
than ten changed and not that nothing did. And every figure describes one
judging model: a second model of the same kind reproduced the direction of
every finding and none of the magnitudes, with gaps of up to 47 points.
Nothing here has yet run against a production system.

---

---

## 1. The problem: you swapped the model, and nothing you have can tell you what broke

You run a feature that calls a language model. One day something behind it
changes. Perhaps you move to a cheaper model, or your provider retires the
snapshot you were pinned to, or you bump a locally served model by one
version, or someone edits two lines of the system prompt. Your unit tests
still pass, because they test your code and not the model's judgement. You
have no labelled data for your own domain, because almost nobody does. And
every output now reads slightly differently, because the new model phrases
things its own way.

We call that change a **regression** when it alters what the feature does on
inputs it used to handle, whether or not any score you can compute moves. The
question this paper is about is how to find those inputs **without labels**,
meaning without reference answers or hand-written assertions, and **through
the black box**, meaning from the text that comes out and nothing else, so
that the method works against a hosted API you do not control.

### How long regressions go unnoticed

The incident record says the problem is real and that the industry has no
channel for it. We counted the public status-page incidents of the two
largest model providers over their published history windows: 25 for one over
about forty days, 93 for the other over about ninety. Of those 118, none
describes a drop in output quality. Every one is an error rate, a latency, an
availability or an authentication or billing failure. One provider's own
month-long quality degradation, which affected up to 16 percent of requests on
one surface, was never a status incident; it surfaced as an engineering blog
post after the fact. Status pages do not under-report this class of failure.
They have no category for it.

Hard failures are caught in minutes. Silent ones are not. In the written-up
cases we could find with a documented timeline, a sycophancy regression in a
widely used assistant was live for about four days before user reaction forced
a rollback; a routing fault that degraded quality at one provider ran for
about thirty days and was found through user reports; a city government's
business chatbot gave wrong legal guidance for about five months until
journalists tested it; a tool-surface change silently broke 474 agents on an
open-source platform for about ten months and was found by a manual database
query; and an airline's chatbot gave a customer wrong refund policy that took
fifteen months and a tribunal to surface. Not one of these was caught by the
operator's own automated evaluation. Every one was found by a person noticing,
or by somebody running a ground-truth probe.

[Verify before submission: the sycophancy post-mortem is cited through two
secondary sources because the originals returned an access error; the quotes
agree across both.]

### What the incident record also tells us

The same record shapes the rest of this paper. Production prompt edits,
measured across fourteen commits of a flagship deployment's published prompts,
are one to three lines, so a test harness that rewrites whole prompts tests
something that does not happen. Three unrelated serving faults, a
misconfigured accelerator, a miscompiled operation and an aggressive
quantisation, all produced the same visible symptom, wrong-script characters
or raw escape codes in otherwise correct replies, so one check covers all
three. And the same routing bug ran at below 0.0004 percent of requests on one
deployment surface and 16 percent on another in the same week, so how many
requests a fault touches is a property of where it sits in the deployment
rather than of what kind of fault it is. Section 6 builds the test harness on
those three facts.

### What this paper offers

A method that takes your old system, your new system and a few hundred of
your own inputs, and reports which inputs changed behaviour and how often it
is likely to be wrong when it says so. It does this without knowing what your
outputs mean. The method is a tool; the contribution we care more about is the
study attached to it, which asks whether detection built on one domain still
works when moved to another. Nobody has published an answer to that, and the
study is designed so that the answer, when it comes, can be no.

---

## 2. What already exists, and where the gap is

This is not an empty field, and one project got to the core idea first. We
write this section with a rule: no claim that a named tool lacks a capability
is made from reading its documentation alone. Where we have not run the tool,
we say what appears to be the case.

The statistics of comparing two model versions are settled. Repeated sampling
with the right error bars for a paired comparison is shipped by Inspect, the
evaluation framework from the UK AI Safety Institute, and at least four
open-source or preprint projects gate a change on whether its delta exceeds
the noise. We use those statistics and claim nothing for them.

Metamorphic testing, checking that a transformation which should not change
an answer in fact does not, has been a task-agnostic methodology since
CheckList in 2020; a 2025 survey catalogued 191 such relations for language
tasks and ran about 560,000 tests, and Giskard ships invariance testing as a
named primitive. We use the idea and claim nothing for it. The one narrow gap
adjacent to it, inferring which relations apply to a system from its own
unlabelled traffic, is close to what section 5 does with structure.

Grouping outputs by meaning and ranking the groups by how far they drifted
from a reference set is shipped by Arize Phoenix. Replaying inputs, embedding
the outputs and reviewing the top of the list by displacement is a sound
engineering composition and not a novel mechanism; section 4 also measures
why it is a poor one for this job.

The nearest work is Clausius, an open-source project that detects regressions
without labels on unlabelled production prompts, using a measured null for
comparison, validated across five model families and seven task domains with
published sensitivity figures. It is further along than we are on the
evidence. Two things leave room beside it. It reads the model's internal token
probabilities, so it works only with models you host yourself and cannot be
pointed at a commercial API, where most deployments live; and its own
documentation says its null must be re-measured on each new stack. a-prime
reads only the text that comes out, which is slower and less informative and
works anywhere.

Two things appear not to exist. No tool we found infers rules about a
system's output from the baseline's own output distribution; everything
adjacent, schema assertions and constrained decoding, is written by hand. The
nearest ancestor is Daikon, a 2001 program-analysis tool, and it was never
ported to language-model output. And no tool we found uses a repeated baseline
run as a general way to calibrate a black-box comparison; the target-decoy
construction behind it is standard in proteomics and has, as far as we can
tell, no prior use in evaluating language models.

And one thing has not been studied at all: whether any of this transfers
across domains. One recent paper tested moving a detection threshold across
domains for a related task and found its apparent transfer was driven by how
often the target occurred in each domain rather than by the method. That is a
warning about design, which section 7 takes, and it is not an answer to the
question.

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

## 5. Rules the baseline teaches about itself

The checks in section 4 read meaning. Some failures have none to read. A
model that starts emitting Thai characters in the middle of English replies,
or raw `\u` escape codes instead of the glyphs they stand for, or JSON with a
key missing, has not changed what it is claiming. A judging model, asked
whether the corrupted output means the same as the clean one, answers
correctly: yes. So these failures need a check that reads structure and
ignores meaning, and such a check needs rules about what the output should
look like.

We do not write those rules. The baseline writes them, by example.

### Where the idea comes from

In 2001 a tool called Daikon watched programs run and guessed the rules their
variables obeyed: this value is never negative, that list is always sorted.
The rules were inferred from observed executions rather than written by the
programmer, and they turned out to be a good way to catch a change in
behaviour, because a rule that held for a thousand runs and breaks on the next
one is worth a look. Nobody appears to have applied the idea to the text a
language model produces.

Daikon's known weakness is that it proposes far more rules than a person can
review, and most of them are true by coincidence. Fit a range exactly to the
values seen so far and every range is a rule. The two mechanisms below are the
answer to that.

### What is inferred, and what each rule is for

From a few hundred baseline outputs, the tool proposes candidate rules of
these kinds: the output parses as JSON; a named key is always present and
always of the same type; a field only ever takes one of a handful of values;
the characters belong to one script; there are no raw escape sequences or
control characters; the text ends with a terminator rather than mid-sentence;
no refusal phrase appears; the word count and line count stay inside a range.

None of these is invented. Each kind corresponds to a failure that has
happened in production. A large professional network measured schema errors in
model output at about 10 percent and cut them to about 0.01 percent with a
defensive parser. Three unrelated serving faults at two providers, a
misconfigured accelerator, a miscompiled operation and an aggressive
quantisation, all produced wrong-script characters or raw escapes in otherwise
correct replies. Truncation leaves a mid-sentence stop. Refusal drift leaves a
phrase.

Rules are fitted tight, in Daikon's style. A range fitted exactly to the
observed minimum and maximum is the strongest claim the data supports, and
guessing a safety margin up front would be inventing a number. Ranges rarely
survive as hard rules, and that is informative rather than a defect.

### The second baseline run prunes coincidence

Every candidate rule is checked on both baseline runs. A rule that holds on
the first run of a system and breaks on a second run of the same system was
never a rule; it was an accident of one sample. This is the decoy arm doing a
second job beyond calibrating the false-alarm rate, at no extra cost, because
those samples already exist.

What survives is sorted into three bands by how often it held on both runs:

| held on both baseline runs | what happens |
|---|---|
| 99 percent of the time or more | enforced against the candidate, no person involved |
| between 60 and 99 percent | shown to a person as a question: "this held 87 percent of the time, is it a rule or usual variation?" |
| less than 60 percent | discarded |

A rule that clears 99 percent on the first run and fails on the second is
demoted to the middle band rather than discarded, because the data says
something is going on, just not that it is an invariant. Only the top band is
enforced automatically; firing on the middle band would bring back the flood
the band exists to prevent. The person never sees a thousand candidates. They
answer a few dozen questions the system has already established are worth
asking.

### What the rules caught that nothing else could

On a synthetic system producing realistic 150-word outputs, we injected six
kinds of fault at three severities each and ran both the meaning checks and
the rules. Refusals and truncations were caught by both. Deleted content was
caught by the meaning checks, 73 percent of the time at the lowest severity
and always above it. Corrupted characters and raw escape codes were caught by
the rules at every severity and by no meaning check at any, for the reason
given at the top of this section: a corrupted output means the same thing.
The rules are not a supplement there. They are the only cover for a whole
class of fault.

A rule describes the system as a whole, not one input, so it is not subject
to the ten-input floor of section 3. On the first run against a real system,
where that floor suppressed every meaning check, the rules were the one part
of the report that could say anything: eight rules were inferred, all eight
held on both baseline runs, and the candidate broke two of them, a word-count
range on 2 of 120 outputs and a line-count range once. That is a small number
of changes reported from a run that otherwise reported none, and it was not
designed for.

### What has not been shown

The pruning mechanism has not yet been exercised by a realistic system. The
synthetic one produces no coincidental rule for the second baseline run to
knock down, so every "zero pruned" reading so far says nothing about whether
pruning is needed. Daikon's over-generation may be milder at this sample size
than its reputation suggests, because three hundred draws already explore a
range; that is a hypothesis, not a finding.

A tightly fitted rule can be tipped by an ordinary draw of the baseline. One
shifted draw produced a word-count violation on 2 of 200 outputs from a
candidate where nothing had changed, a 1 percent false-alarm rate on that
rule. That is one draw and not a measured rate, and it is what the middle band
is for.

All rules are about the whole corpus. Nothing yet infers "for this input the
answer always mentions 42,000", which is plausible at twenty samples per cloud
and untried. The script rule will produce a permissive rule and catch nothing
on a system that legitimately switches language per input. And the cap of six
distinct values for an enumerated field is a guess, not a measurement.

---

## 6. The systems under test, and the faults

To find out whether detection transfers across domains, we need systems in
several domains where we know, for every input, whether a given fault touched
it. No real deployment tells you that. So we built nine systems whose
knowledge we author and whose tools we control, which is the only way to have
per-input ground truth, and we accept the cost that comes with it: nothing
here has run against a production system, which is limit 4 in section 9.

### Nine systems: three domains by three output formats

Each system is a tool-calling agent over a knowledge pack in one of three
domains: banking, logistics, hospitality. Each exposes the same eight tools,
looking up a record, searching its history, reading a policy, computing a
ratio, evaluating eligibility, listing prior records, verifying a document and
recording an action, under domain-specific names. The packs are generated from
a seed with identical structure in every domain, differing only in vocabulary
and subject matter. If the detector behaves differently on banking than on
logistics, the difference cannot be that one domain was given a richer agent.

The three output formats are a JSON object with four named keys, three to
five sentences of prose, and a single decision line beginning APPROVE, DECLINE
or ESCALATE. All three call the tools, because real extraction and
summarisation agents retrieve before they write, and they differ in what they
must produce, which is what the per-shape thresholds of section 3 depend on.

Two things were measured before the systems were committed to. The 8-billion-
parameter models we use picked the right tool on 16 of 16 single-tool
requests among the eight, and the eight tool schemas cost 461 to 751 prompt
tokens, not the 1,200 to 2,000 the design had assumed. Eight tools cost
nothing in reliability.

### What the first live run found

Running all nine systems against a live model for the first time, 36
invocations in 185 seconds, found four defects in the systems themselves, and
none of them had been caught by 159 unit tests. A quarter of every corpus
returned an empty output, because the one request that needed a figure could
not reach it through any tool and the model ran out of steps hunting for it.
The model wrote its deliberation into the output and closed it with a tag it
never opened. A quarter of outputs were cut mid-sentence by a generation cap
set too low. And an amount filter named no direction, so "above 1000" became
"at most 1000".

The second and third of those matter beyond this project. How much a model
thinks aloud, and where it gets cut off, are exactly the kinds of thing that
change when a model is swapped. Left in place, either would have produced a
strong and entirely spurious regression signal. Both are now stripped or
recorded, and the run that found them is why every test double in this
project is built from captured responses of a live server rather than written
from memory of the API: eight separate divergences between the two were found
that way, each of them a place where a hand-written fake was more cooperative
than reality.

The decision-line format is the one that did not come right. It produces a
distinct output shape, which the grid needs, but it obeys its own instruction
on 4 of 12 attempts, puts the decision last, and varies 36-fold in length where
summaries vary 3-fold. Three rounds of fixes bought three inputs, at which
point further fixing becomes tuning the bench until the number looks right. It
is kept as it is.

### The models

Four locally served models from four labs, two of them with different
architectures, all under a permissive licence. They were chosen for family
diversity rather than capability, because capability did not discriminate:
every 8-billion-parameter model tested drove a chained two-step tool loop 12
times out of 12, and the one 3-billion-parameter model failed a quarter of the
chains. That smaller model is kept as a deliberately weak system, whose high
natural error rate tests whether the detector reads "bad" as "changed".

Two of the four, as shipped, silently inject faults the study is trying to
measure. One vendor template inserts a hidden system prompt of about 540
tokens that interpolates today's date, so the prompt changes every midnight
and a run straddling midnight compares two prompts nobody edited. Another
defaults to reasoning before answering and can spend its whole generation
budget on the reasoning and return an empty string, which is indistinguishable
from a truncation fault. So every system under test gets an explicit system
message and explicit sampling parameters, vendor defaults are never compared
(default temperature alone differs 1.0 to 0.15 across the pool), and a run
that crosses midnight is flagged in the report.

### The faults

The faults come from a taxonomy of fourteen classes, frozen in a dated
document before any threshold in the detector was tuned, so that the detector
could not be fitted to the faults it would be scored on. Nine classes have at
least one documented production incident behind them: a model swap, a prompt
regression, a change to the tool surface, provider drift, a stale or corrupted
knowledge base, cache contamination, serving-stack corruption at a fixed model
version, sticky routing, and persona drift. Five more have a documented
mechanism and no incident with a measured blast radius: input truncation,
retrieval degradation, output truncation, refusal drift, and a mismatch in how
the prompt is serialised to tokens. That grading is carried into the results
rather than smoothed over. One class the original design listed, a change in
decoding parameters, was dropped for having no documented instance at all.

Every fault is injected across the blast radii that occur in the wild, which
is a separate axis from its class. The documented split is not real-versus-
injected but shared-artifact versus request-path. A fault in something with
one copy, a system prompt or a model version, hits at least 84 percent of
requests and usually all of them. A fault on the request path, in routing or
load balancing or provider selection, runs between 0.0004 and 16 percent, and
the same routing bug measured below 0.0004 percent on one surface and 16
percent on another in the same week. Sticky routing concentrates a request-
level rate onto a subset of users: 0.8 to 16 percent of requests became about
30 percent of users. If the harness injected every fault globally, a detector
would learn that "global" means "injected", which is an artifact of the
harness with no counterpart in production.

Two severity floors are set by published evidence rather than by us. A
controlled study on five hundred questions found that corrupting 10 percent of
retrieved rows produced no measurable change in any downstream metric, so a
miss at that level is not a detector failure. And real production prompt
edits, measured across fourteen commits of a flagship deployment's published
prompts, are one to three lines; a harness that rewrites whole prompts injects
something that does not happen.

### Ground truth is per input, never per system

A fault configured on a system is wrong as a label for every input it never
touched. Truncation cannot truncate a four-word answer. A schema break only
bites JSON. A refusal only bites where the system would otherwise have
answered. Labelling every input of a faulty system as changed is label noise
by construction, and it is the kind that inflates every downstream number in
the direction that looks like success. So every injection records, per input
and per sample, whether it actually fired, and that record is what the
detector is scored against. On the first real run, a stale-data fault
configured on the whole system fired on 15 of 30 inputs, and the detector was
graded on those fifteen.

The harness injects a fault in one of three ways, and the difference is about
whose fingerprints are on the output. The first rewrites an output after the
fact: truncating it, inserting corrupted characters, replacing it with a
refusal. That works on any system, including one we did not build, and it
leaves our vocabulary and sentence shape in the output, so in principle a
check could learn to spot us rather than the fault. The second degrades what
the system's tools return, serving older rows of the right record, or
well-formed rows of the wrong one, and lets the model write a different answer
itself. The third edits the lines of the system prompt, on the one-to-three-
line ladder above, and again lets the model write. Outputs from the second and
third carry only the model's own fingerprints, which is what a real regression
looks like.

For a prompt edit, whether an input counts as affected is decided by exposure:
the edited prompt was sent and the model answered. Whether the edit actually
changed the answer is the detector's question, and deciding it in the harness
would need a second clean call for every input at double the recording cost.
That convention errs towards scoring the detector as having missed inputs it
had no way to see, never the reverse, and it is why recall on prompt
regressions is reported as a lower bound.

### Keeping the detector away from the answers

The seat that tunes the detector must not be the seat that seeds the faults,
or the detector will learn the seeds. In this project the guarantee is the
commit history rather than a promise: every threshold in the detector, the
clustering cut, the choice of checks, the false-discovery machinery, was fitted
and committed against the hand-built text pairs and the synthetic system,
neither of which contains an injected fault, before the fault harness existed.
Anyone can check the order.

One further system, a retrieval-augmented assistant for a video game with an
authored knowledge base, is the development system: the one whose correct
answers we know, and the one the detector was built against. It is excluded
from every transfer number and reported on its own.

---

## 7. Study design

Nothing in this section has run. It is written now so that a reader can judge
the design before the result exists, and so that the result, when it comes,
cannot be shaped by the design being written afterwards.

### The claim the study can support

Across a set of systems spanning the three domains and three output formats
above, with the detector's every threshold chosen without sight of the system
it is tested on, the detector flagged changed inputs at the chosen
false-discovery budget and detected injected faults down to a stated severity
per fault class, and its performance on a system it has not seen is expected
to fall within a stated interval.

The interval is wide, and that has to be said before any number. The unit of
evidence for a claim about transfer is the system, not the input, because
inputs within one system are near-replicates of each other. With six systems
and the detector succeeding on every one, the 95 percent lower bound on the
per-system success rate is 0.54. With nine, 0.66. "It worked on every system
we tried" is consistent with failing on a third of the systems we did not.

### Leave one system out

Every threshold and every fittable choice in the detector is selected inside
a held-out loop. Hold out one whole system. Fit everything on the rest. Test
on the one held out. Repeat for each system. The same is done leaving out one
fault class at a time, and the two are crossed. A system is never split
between fitting and testing, not even across severities of one fault, because
a detector will learn a system's identity, its output style and its noise
level, as if it were a fault signature, and random splits inflate every
number. Random-split numbers are reported beside the held-out ones so that the
inflation is visible, and never instead of them.

### The things that would silently invalidate the result

Some mistakes make a study fail loudly. These make it succeed falsely, so
each is a rule rather than a hope.

**Base rates.** A published attempt to transfer a detection threshold across
domains found that its apparent transfer was driven by how often the target
occurred in each domain rather than by the method. So the rate at which
inputs change is controlled across our domain cells by design, before the
study runs. Left uncontrolled, the transfer finding would be uninterpretable
in either direction.

**Pre-registration.** The fault taxonomy and its severity ladders were frozen
in a dated document before any tuning. Changes to it are dated additions with
a reason, never edits in place.

**A sealed holdout of real regressions.** A set of thirty to eighty regressions
that actually happened, opened once, with the opening recorded. It is not
collected yet, and when it is, its power is limited: at thirty cases, a recall
of 0.80 has a 95 percent interval from 0.63 to 0.90, which can show
catastrophic non-transfer and nothing finer. Worse, collectable regressions
are the ones somebody noticed, which are the loud ones.

**Pinned instruments.** The judging model and the embedding models are locked
to specific revisions, listed in the appendix. Changing one makes every earlier
number incomparable and is recorded as such rather than carried over. The
sampling seed is deliberately outside this rule, for the reason in section 3:
pinning it on both baseline runs collapses the yardstick.

**Provenance.** Every number traces to a run identifier and a hash of the
configuration that produced it. The hash covers everything that changes a
result: the instrument revisions, the sample count, the budget, the fault, the
seed policy and a fingerprint of the inputs. It deliberately excludes things
that do not, such as which machine served the model, so that the same run on
two machines is one configuration. A results row without its run identifier
and its hash is refused at write time rather than warned about, because an
untraceable number in a results file looks usable.

### The cost, and where it goes

Detection is cheap and recording is not. On the first run against a real
system, recording took 589 seconds and detection 10. At the working minimum of
twenty samples per cloud and three runs, one system in one domain and format
is 1,800 model calls for thirty inputs, and a chained tool-calling format
costs about three and a half times a summarising one. Three things keep that
tractable: calls for one input are grouped so a server with prompt caching
pays the shared prefix once per input rather than once per call, which on the
measured hardware is the difference between weeks and hours; runs checkpoint
after every triple of calls and resume where they stopped, so a long run can
be paused from another terminal and does not have to finish in one sitting;
and a run whose model server has died is stopped within seconds rather than
recorded as complete, which happened once and produced a checkpoint that
called itself finished while 97 percent of its samples were connection errors.

### What will be reported, and what will not

Every number with its denominator and its interval. Negative results with the
same care as positive ones; a finding that detection does not transfer is the
more interesting outcome and is written up as such. The development system
separately, never pooled. And four things we will not claim: that the method
is domain-agnostic, as a bare statement; any recall or precision on real
regressions beyond what the holdout can support; that the tool can tell a
regression from an improvement; and any headline number produced under a
random split.

Section 8 holds the results. Until the nine-system study has run, it holds a
table of what each result will be backed by.

## 8. Results

This section is partial by design. Two of the three rows of the nine-system
grid have been recorded and analysed; the third is being recorded as this
draft is written, and the paragraphs that depend on it are marked. Everything
below comes from one analysis run and six per-cell result files, each carrying
its run identifier, configuration hash and the code revision that produced it.

### What has run

Six systems: the summary format and the JSON extraction format, each in the
three domains. One fault class: a stale knowledge base, injected as the four
readable tools serving older rows of the right record. One model behind every
system, an 8-billion-parameter model served locally and pinned by the digest
of its weights. Forty inputs per system, six samples per cloud, three runs,
a false-discovery budget of 0.10. Six cells of 240 triples each, 4,320 model
calls, none of which errored. Per-input activation, recorded by the fault
wrapper as each call was made, is the ground truth throughout, with one gap
found while writing this section: in the two cells that were paused and
resumed, a bug in how the resumed session reopened its label file erased the
labels of the inputs recorded before the pause, 20 of 40 in banking
extraction and 5 of 40 in banking summary. Those inputs are label-unknown and
cannot be relabelled, because the label is a difference between two tool
results and the recording keeps outputs, not tool arguments. Every count
below for those two cells is over the labelled inputs, and says so.

Two things to hold in mind while reading the numbers. These cells ran at six
samples per cloud, not the twenty that section 3 calls the working minimum,
because six was what fitted in the nights available, and the choice had no
decision behind it until this draft forced one. Six matters less for this
fault than the power figures of section 3 suggest, and more for the threshold.
The fault is close to all-or-nothing per input: of the 111 inputs it touched,
101 fired on five or six of their six samples and 96 on all six, so a touched
input moves its whole cloud rather than part of it, which is not the gradual
shift those power figures were measured on. What six samples cost instead is
resolution. The share-of-answers statistic can take only seven distinct values
at six samples, the decoy scores land on the same seven, and the threshold
is set from where the decoys stop. The section below on the JSON cells shows
exactly what that costs. And the
false-discovery rates below are only computable because the bench records
which inputs the fault touched. No production user ever has that number. In
production, the budget is the promise and the realised rate is unknowable,
which is why a validation like this one is the only place the promise can be
checked.

### The partial matrix

| | banking | logistics | hospitality |
|---|---|---|---|
| **summary** (prose) | 15 of 17 changed inputs caught, 5 inputs unlabelled; 19 flagged, 4 not known to have changed | 11 of 14; 11 flagged, 0 false | 18 of 21; 21 flagged, 3 false |
| **extraction** (JSON) | 0 of 11, 20 inputs unlabelled; nothing flagged | 11 of 23; 11 flagged, 0 false | 0 of 25; nothing flagged |
| **agent** (decision line) | [recording; 11 of 240 triples at this draft] | [recording] | [recording] |

Each cell reads: inputs the fault actually touched and how many of them were
flagged; then how many inputs were flagged in all and how many of those the
fault had not touched. A cell where nothing was flagged is one where no check
found a threshold it could justify at the budget.

### On prose, detection transferred across all three domains

On the summary format the detector caught 88 percent of the inputs the fault
touched in banking (15 of 17), 79 percent in logistics (11 of 14) and 86
percent in hospitality (18 of 21). Pooled, 44 of 52, with a 95 percent interval
from 72 to 92 percent. Nothing in the detector was tuned to any of these three
domains; every threshold was set by each system's own second baseline run. For
one fault class, one model and one output format, the paper's title question
has the answer yes.

That is the full width of the claim, and the width is set by the unit of
evidence. Three systems succeeded, and three successes out of three bound the
per-system success rate below at 0.29 at 95 percent confidence. The row says
that transfer across these three domains happened; it cannot yet say how often
it happens.

### On JSON, the failure is shaped by format, not domain

The same three domains that detect at 79 to 88 percent on prose split three
ways on JSON. Logistics worked: 11 of 23 touched inputs caught, 11 flagged,
none false. Banking flagged nothing, with 11 touched among the 20 inputs that
kept a label, which is close enough to the ten-input floor of section 3 that a
sizing miss cannot be ruled out, and with 20 inputs whose label is unknown.
Hospitality is the sharp case: 25 of 40 inputs were touched by the fault, well
above the floor, every input labelled, and nothing was flagged.

The diagnosis has run, it is written to a file beside each cell's recording
(Appendix F), and it is not blindness. In hospitality, 18 of the 25 touched
inputs score exactly 1.0 on the share-of-answers check, the highest value the
statistic can take, and none of the 15 untouched inputs does. One decoy, the
baseline against itself, also scores 1.0; it is there in the sorted decoy
array, not inferred. The best cut the estimator could make therefore had 18
inputs above it and that one decoy, an estimate of 0.111 against the 0.100
budget. In banking, 9 of the 11 labelled touched inputs sit at or above the
best cut of 0.667, none of the 9 labelled untouched inputs does, two decoys
do, and the other 8 inputs above the cut are the ones whose label was lost;
the estimate was 0.176. What failed in both cells is resolution. With six
samples per cloud the statistic takes seven values, the decoys pile onto a few
of them, and a single decoy on the top value puts the floor out of reach.
Logistics worked on the same format because its decoys happened not to reach
the top value. So the format-shaped failure is a resolution failure: the
change was seen and could not be reported, which is the same shape as the
first end-to-end run in section 3, arrived at from the other side. The fix is
finer statistics, which means more samples per cloud, and the next paragraph
says what has been committed to.

### The false-alarm budget, on the evidence so far

Two of the three summary cells ran over the budget: 4 flagged inputs not
known to have changed among 19 in banking, a realised rate of at most 0.21,
since 5 of that cell's inputs are label-unknown and the analysis that would
say which inputs those 4 are has not yet been re-run; 3 among 21 in
hospitality, 0.14, every input labelled; none among 11 in logistics. Pooled
across the row, at most 7 in 51, 0.14, with a 95 percent interval from 0.07
to 0.26 that contains the 0.10 asked for. At roughly twenty flags per cell, a realised rate of 0.14 is not yet
distinguishable from an honest 0.10 with ordinary variation around it, and it
is not yet distinguishable from a miscalibration either. The extraction cells
that flagged anything flagged no false alarms, on 11 flags.

The same resolution problem that silenced two JSON cells is the likely driver
here, from the other direction: with decoys on seven values, the cut the
estimator settles on can sit a whole value too low as easily as a whole value
too high. So the following is on record before the run that tests it. The
summary row will be re-recorded at twenty samples per cloud, as a separate
configuration beside this one. The prediction: recall moves modestly, since
the fault is near-binary and was mostly seen already, and the realised
false-alarm rates move towards the budget, because what twenty samples buy is
decoy resolution rather than detection. If that row's recall leaves the
interval of the six-sample row, the whole matrix is re-recorded at twenty. If
it does not, the six-sample matrix stands as the transfer result and twenty
samples are reserved for the measurements that need them. [Result of that
run to be entered here.]

### Which checks carried the result, and why that is not a contradiction

Of everything flagged across the six cells, the share-of-answers check
flagged 57 inputs and the new-answers check 61, with most inputs flagged by
both. The contradiction check flagged 10, all in one cell, and the
information-direction check flagged none. The embedding check was switched
off, as it is in the shipped configuration without an embedding model.

A reader of section 4 will notice that the judging-model checks carried the
load there and the clustering checks carried it here. The two measurements
answer different questions on different material. Section 4 asks which kinds
of change a judging model can see in a single pair of texts, one fact changed
and nothing else. This section asks which statistic separated two clouds of
samples when a stale fact changed which answer the system gave. A fault that
moves the system from one answer to another shows up directly in the mix of
answers, which is what the clustering checks read, and the judging model is
still doing the work underneath them: it is the predicate that decides which
samples count as the same answer. One plausible reason the contradiction
check scored lower on its own, not measured here, is that its per-input score
is an average over paired samples, which dilutes a change present in some of
them. The information-direction check flagging nothing is expected: a stale
fact substitutes one value for another and neither adds nor removes content,
which is the same reading the first end-to-end run gave.

### What is missing from this section

- The agent row, three cells, recording at the time of writing. It completes
  the six-sample matrix.
- The summary row at twenty samples per cloud, with the prediction above on
  record before it runs.
- Leave-one-system-out and leave-one-fault-out numbers. With one fault class
  recorded, leave-one-fault-out is undefined, and leave-one-system-out across
  three systems per row gives the interval above and no more.
- The severity titration per fault class on real systems. The only
  titration so far is on the synthetic system (section 5), and the fault used
  here cannot drive one at any sample count, because it is near-binary per
  input; a titration needs a fault with a severity knob, and at least twenty
  samples per cloud.
- The sealed holdout of real regressions, not yet collected.
- Any second model. Every cell here was driven by one model, so this section
  describes that model, as section 4 described one judging model.

Every number above traces to analysis run `20261005T145729Z` (the hospitality
extraction cell to `20261005T145730Z`), to the six per-cell configuration
hashes listed in Appendix F, and to code revision `26345e7`.

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

## 10. Two ideas that may be useful elsewhere

Both are mechanisms, built and tested on synthetic systems, and neither is a
measured result on a real one.

**The second baseline run does a second job.** It was introduced to set the
false-alarm threshold. It also prunes inferred rules, at no extra cost,
because the samples already exist. A rule that holds on one run of a system
and breaks on a second run of the same system was never a rule, and
discarding it needs no judgement, no schema and no person. Anyone inferring
anything from a stochastic system's output could use a second draw this way.

**One number, read at both ends, names two faults.** Asking a judging model
how much the old output implies the new one, and how much the new implies the
old, and subtracting, gives a number whose sign carries information. Strongly
positive means the new output says less than the old; strongly negative means
it says more. The first implementation took the absolute value and threw away
the only part that identified which fault had occurred. The general point is
that a symmetric distance between two outputs is the wrong summary whenever
the direction of a change matters, and in regression detection it usually
does.

A third is less an idea than a posture. The method cannot report fewer than
ten changed inputs, and we have come to regard that as a feature. A tool that
can be made to find something by lowering its bar will be made to, and a
threshold of infinity, which is what the tool reports when no cut qualifies,
is a more useful answer than a finding it cannot stand behind.

---

## 11. Extensions, in one sentence each

Each of these is constructed or derived and not measured, and is stated in
that register.

The same statistic pointed at time rather than at a candidate detects whether
a hosted model has changed under you: record a baseline now, record it again
later, and score the two periods against the first period's own
baseline-versus-baseline spread; the negative control, a locally served model
whose weights provably did not change, is about an hour of compute and has not
been run, so this is an extension and not a result.

A hosted model as a system under test is one adapter behind the existing
boundary, and it was deferred on cost rather than on principle; the one real
constraint is that the two baseline runs must be the same system, which a
provider that changes a model mid-run would violate, and the recorder keeps
the three calls for one input close in time to bound that exposure.

The judging model is the dominant cost of the detector, and the cost line now
counts every clustering it is asked for, which is the evidence for or against
distilling it into something cheaper once a real study has shown the cost to
bind; fine-tuning anything before that point was considered and cut.

---

## 12. Reproducibility

Every number in this paper traces to a run identifier and a configuration
hash, written into the results file that holds it. The hash covers the
instrument revisions, the sample count, the budget, the fault, the seed policy
and a fingerprint of the inputs. A figure computed from other results names
the runs it was computed from; the blind-spot map prints its three source runs
in its footer.

**Instruments.** The judging model and the embedding models are pinned to the
Hugging Face revisions below, resolved at load time and recorded from the run
rather than copied from a model card. Changing any of them invalidates every
earlier number rather than silently changing it.

| role | model | revision |
|---|---|---|
| judging model, primary | MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli | 6f5cf0a2 |
| judging model, replication | FacebookAI/roberta-large-mnli | 2a8f12d2 |
| embedding, small | sentence-transformers/all-MiniLM-L6-v2 | 1110a243 |
| embedding, base | BAAI/bge-base-en-v1.5 | a5beb1e3 |
| embedding, base, prefixed | intfloat/e5-base-v2 | f52bf8ec |

Full revision hashes are in the repository's methods state file. The systems
under test are served locally through Ollama and pinned by the digest of the
served weights, which the runners read from the server's model listing;
several early runs recorded that digest as unresolved because they asked the
wrong endpoint, and are marked as pinned by name only.

One exception is stated here because it is a real limit on tracing. The
script that scored the probe pairs and produced the four result files behind
the blind-spot map predates the shared provenance capture. It records its
inputs and the model revisions, which is the right thing to pin, and not the
code revision that scored them. Those four files therefore trace to their pair
set and their weights, and not to the code. The script moves onto the shared
capture with the next probe re-run, so that the change in how its hashes are
computed coincides with a run nobody would compare to an old one.

**Code and data.** The code is under the Apache 2.0 licence. The
documentation, the measured results and the findings are under Creative
Commons Attribution 4.0, which asks for attribution when the numbers are
quoted. The test suite runs in seconds without any model download and
includes the checks that the repository's own self-description is current:
that every status row in its index names a file that exists, that the
worked example in its README is what the demo prints, and that the blind-spot
map reproduces the numbers the ledger records.

**To reproduce.** The probe suite, the blind-spot map and the synthetic
validation of the false-discovery guarantee run from the committed result
files or from a model-free demo. The nine-system study needs a machine with a
graphics processor and a local model server; the repository documents what
travels with it and what does not, and the recorder resumes a run from its
checkpoint on any machine that can reach the model server.

---

## Appendix A. Two rules for the same numbers

A few figures in section 4 differ by one to four pairs from the same figures
as first recorded in the project's findings log. The published figures are not
wrong and have not been edited. The map and section 4 follow one rule for
every row, and that rule differs from the first recording in two ways.

First, when the first runs were scored, pairs with an added hedge were
labelled as rewordings, so each check's 5 percent threshold was set over 320
preserving pairs. Those pairs were later reclassified as a change of
register, which is what they are, and the map sets every threshold over the
256 pairs that remain. Second, the signed entailment check is read at both
ends with a budget of 2.5 percent per end, where the first recording quoted
the one-ended 5 percent rate.

Every cell that moved by at least one pair, as counts out of 64:

| quantity | as first recorded | on the map and in section 4 | which rule |
|---|---|---|---|
| contradiction, changed unit | 54 (84%) | 53 (83%) | first |
| contradiction, changed quantifier | 59 (92%) | 57 (89%) | first |
| contradiction, false alarms on reformatting | 12 (19%) | 9 (14%) | first |
| entailment asymmetry, deleted condition | 61 (95%) | 59 (92%) | second |
| second judge, contradiction, changed quantifier | 35 (55%) | 37 (58%) | first |
| second judge, contradiction, changed number | 54 (84%) | 56 (88%) | first |
| second judge, contradiction, changed date | 54 (84%) | 55 (86%) | first |
| second judge, false alarms on rewording | 8 (13%) | 9 (14%) | first |
| second judge, entailment asymmetry, deleted condition | 42 (66%) | 38 (59%) | both |
| smallest embedding model, swapped name | 38 (59%) | 36 (56%) | first |
| smallest embedding model, deleted condition | 21 (33%) | 20 (31%) | first |
| smallest embedding model, false alarms on rewording | 13 (20%) | 10 (16%) | first |
| mid-size embedding model, swapped name | 38 (59%) | 36 (56%) | first |
| mid-size embedding model, deleted condition | 22 (34%) | 18 (28%) | first |
| mid-size embedding model, false alarms on reordering | 11 (17%) | 10 (16%) | first |
| largest embedding model, false alarms on rewording | 11 (17%) | 9 (14%) | first |

Nothing else moved. No direction changed, no ordering between the two judging
models changed, and no conclusion drawn from them changed. The largest move is
four pairs. The ranking scores quoted in section 4 for the embedding models
are the first-recorded ones; they are not on the map and have not been
recomputed under the new preserving set.

## Appendix B. The fault taxonomy

Fourteen classes, frozen in a dated document before any threshold in the
detector was tuned. Changes since the freeze are dated additions to a log at
the foot of that document; two have been made, one splitting a class in two
and one ratifying the exclusions below. The evidence grade is carried into
every result that uses the class.

| class | what changed | evidence |
|---|---|---|
| model swap or downgrade | the model behind the feature | production incidents |
| prompt regression | the instruction text, or old text resurrected by a code path | production incidents; edits measured at one to three lines |
| tool surface change | a tool renamed, removed or re-specified under the agent | production incidents |
| provider drift | the hosted model changed under a fixed name | production incidents |
| knowledge-base staleness or corruption | what a retrieval-backed system knows | production incidents |
| cache contamination | one request's state leaking into another's | production incidents |
| serving-stack corruption at fixed model identity | numerics, compilation or quantisation; wrong-script characters or raw escapes | production incidents, three with one symptom |
| sticky routing, in two variants | a subset of users pinned to a bad backend; or a system that legitimately varies by user, as the control | production incidents |
| persona, tone or sycophancy drift | how confident or agreeable the system sounds, with facts unchanged | production incidents |
| input-side truncation | long inputs cut before the model sees them | documented mechanism, no measured incident |
| retrieval degradation | the retriever returns the wrong rows | controlled study; 10 percent corruption produced no measurable change |
| output-side truncation | long answers cut mid-sentence | documented mechanism |
| refusal drift | the system refuses what it used to answer, or the reverse | documented, unquantified |
| prompt-template or token serialisation mismatch | the same text serialised differently into tokens | documented mechanism |

One class in the original design, a change to decoding parameters such as
temperature, was dropped before the freeze for having no documented
production instance. Three were considered and excluded as out of scope for a
black-box detector that knows nothing about the data or the requester:
retrieval permission drift, a destructive action by an agent, and a group of
practitioner-folklore failures with no graded source. The exclusions are
recorded as deferred, not rejected.

Every class is injected across the blast radii that occur in production,
which is a separate axis: a fault in a shared artifact hits everyone; a fault
on the request path hits a uniform share of requests, or a sticky share of
users at roughly twenty times the request rate.

## Appendix C. How the probe pairs are built and checked

The 896 pairs behind section 4 come from sixteen seed scenarios, four per
subject area (banking, logistics, hospitality and technical operations). Each
scenario is a small record of facts: a decision, a number with a unit, a date,
a name, a quantifier and a condition. Each is rendered in four output shapes,
a short answer of about thirty words, a JSON object, a multi-sentence summary
of about 150 words, and a numbered list of reasoning steps. Both halves of a
pair come from the same scenario and the same shape with one deliberate
difference.

The preserving differences are: a full paraphrase, two independent sentences
reordered, a phrase replaced by a synonym, and prose reformatted as a bulleted
list. The breaking differences are: a decision flipped, a negation inserted, a
number changed, a unit changed, a date changed, a name swapped, a quantifier
changed, and a condition deleted. The register differences are an added hedge
and an added assertion of confidence. Every combination of scenario, shape and
difference is one pair, which gives 64 pairs per kind of difference.

The four shapes were made to span a factor of about five in length, from 32
to 148 words at the median, by giving the summaries realistic filler that is
identical in both halves. The first design spanned only a factor of 1.7, which
is too narrow to separate "the check cannot see meaning" from "the check works
but the change was diluted in a long output".

The pairs have tests of their own that involve no check at all. They assert
that the two halves of every pair differ, that the intended difference is
present, and that nothing else is. On first assembly those tests found three
kinds of pair whose halves were identical: the synonym substitution had no
target phrase in the JSON rendering, the quantifier change had no quantifier
to change in the short answer, and the reformatting collapsed whitespace that
single-line prose did not have. Each would have produced a plausible finding
about a check that was in fact a finding about a broken pair. A new kind of
pair needs such a test before any number derived from it is read.

## Appendix D. A report, annotated

The report below is what the tool prints on the worked example that ships
with the code, a synthetic system of three hundred inputs of which thirty
really changed, twelve samples per cloud, budget 0.10. Each block is followed
by what it means.

```
a-prime report
  300 inputs compared, 12 samples per input from each of three runs: the old system, the old system again, and the new one.
  False-discovery budget q=0.1: of the inputs flagged, at most about 10% are expected to be false alarms. The second run of the old system sets every threshold.
```

The header states the three things the rest depends on: how many inputs, how
many samples per cloud, and the budget. A run id and configuration hash appear
above these lines when the caller supplies them; a report without them should
not be quoted. If any input had fewer usable samples on some arm because
calls failed, a line here says how many, because their thresholds rest on
fewer baseline scores.

```
29 of 300 inputs flagged.
```

The headline, and the least informative line in the report. When this reads
zero, two lines follow it: the floor of ten and the check that came closest,
with its best estimate and the counts behind it.

```
checks  (each judged against its own baseline-vs-baseline scores; none votes)
  mode_share (answer mix)                   28 flagged   short outputs: 28 flagged above 0.583, estimated false-discovery rate 0.07
  dispersion (spread)                        0 flagged   short outputs: 6 input(s) sit above every baseline-vs-baseline score, under the floor of 10: 4 more would have cleared it
  novel_mode (new answers)                  13 flagged   short outputs: 13 flagged above 0.500, estimated false-discovery rate 0.08
  nli_contradiction (contradiction)        skipped: no NLI model supplied
  nli_directional (information direction)  skipped: no NLI model supplied
  embedding (embedding distance)           skipped: no embedder supplied
```

One line per check, named twice: by the name the code uses, so a line can be
searched for, and in plain words. Each line carries one of four readings. A
check that flagged gives its threshold and the estimated false-discovery rate
among what it flagged. A check that separated the arms but fell short of the
floor says how many inputs stood above every baseline score and how many more
would have cleared it; the spread check here saw six, four short. A check with
partial separation gives the counts at its best cut. A check with no
separation says that the new system's scores sit inside the old system's own
variation, and that the report cannot tell whether nothing changed or the
check cannot see this kind of change. A check that did not run says so and
why, because a check that could not run is not a check that found nothing.

```
rules inferred from the old system  (describe the system as a whole, so not subject to the floor above)
  8 candidate rules: 7 held on both old-system runs and are enforced, 0 held often but not always and are listed for a person, 1 discarded (0 of those knocked down by the second run).
  none of the enforced rules was broken by the new system.
```

The three bands of section 5, with counts, then any rule the candidate broke
with how many outputs broke it and an example, then any rule held for a
person to decide. This block is outside the floor, and on the first real run
it was the only block that could report a small number of changes.

```
flagged inputs  (which checks fired, and their scores)
  in025 [short]  answer mix 1.000 · new answers 1.000
  in030 [short]  answer mix 1.000 · new answers 1.000
  ...
```

One line per flagged input: its identifier, the output shape it was judged
in, and each check that fired with its score. When the information-direction
check fires, the signed value is shown with its meaning, "new output says
less" or "new output says more", because the sign is what names the fault.

A notes block follows when there is something to say: inputs dropped for a
missing arm, a run that crossed midnight, the embedding check switched off on
some inputs. A cost line closes the report with how many model judgements of
equivalence were spent and how far normalisation collapsed the samples before
any were made.

## Appendix E. The repository checks its own description

A reader deciding whether to trust what a repository says about itself should
know whether anything checks it. Four things do, and they run with the rest of
the test suite on every change.

The index of the repository's component documents is read by a test that
fails when a row marked done names a file that does not exist, when a row
marked as a gap names a file that does, or when a document has no row. Four
rows were wrong in one week before it existed, in both directions. The
per-family state files are read by a second test that fails when a path they
name does not exist, with the stated limit that it cannot catch a prose
contradiction between two files. The worked example in the README is compared
line by line against what the demo actually prints, because the report format
changed once and the example went on showing the old format until somebody
noticed. And the blind-spot map is recomputed from the committed probe runs by
a test that pins its cells to the counts the findings log records, so a
regenerated figure that disagrees is a changed input file or a drifted
recomputation and never a new finding.

None of these can tell whether a document that exists is current. They close
the gap between "the file is there" and "the index says so", and between "the
example is printed" and "the program prints it".

---

## Appendix F. The cells of section 8

| cell | configuration hash | triples | sessions | inputs labelled | detection time | diagnosis file |
|---|---|---|---|---|---|---|
| banking-summary | `60ac20518858cf53` | 240 | 3 | 35 of 40 | 24.5 s | |
| logistics-summary | `164081630f20c414` | 240 | 1 | 40 | 30.2 s | |
| hospitality-summary | `19ffac0bccf2ddd8` | 240 | 1 | 40 | 32.5 s | |
| banking-extraction | `7e1c3a40f5946fc8` | 240 | 2 | 20 of 40 | 21.5 s | `banking-extraction.7e1c3a40f5946fc8.diagnosis.json` |
| logistics-extraction | `b541f3b106c5d06d` | 240 | 1 | 40 | 21.8 s | |
| hospitality-extraction | `418a3438efcfbb12` | 240 | 1 | 40 | 32.8 s | `hospitality-extraction.418a3438efcfbb12.diagnosis.json` |

Model `granite4.2:8b`, digest `f586c02fdecdf151`. A cell with more than one
session was paused and resumed; the recorder resumes from its checkpoint, and
no sample in any of the six was an errored call. The two resumed cells lost
the activation labels of their earlier sessions to the bug described in
section 8; the fix is in the code that will record the remaining cells. A
diagnosis file holds, for every check, the best cut the estimator could make,
the counts of inputs and decoys above it, and the full sorted target and decoy
scores, with the judging model's pinned revision inside and the recording's
configuration hash in its name; one is written beside any cell that reports
nothing. Detection time is for the
analysis of one recorded cell with the judging model loaded; recording took
hours per cell and is the binding cost, as section 7 says.

---

*Section 8 is drafted against two of three rows; its bracketed paragraphs
fill when the agent row and the twenty-sample summary row land. The abstract's result stays
blank until the matrix is complete.*
