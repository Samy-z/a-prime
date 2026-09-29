# reader — METHODS

The `reader` seat exists because of a failure that the author of a document
cannot see: writing for somebody who already knows. Every internal term feels
obvious once you have used it for a week, so the person who built the thing is
the worst possible judge of whether its description is readable.

This is the same structural argument that separates `engine` from `bench`. You
cannot audit your own blind spot, so the audit needs a different seat.

## The mandate

This seat owns every artifact a stranger will encounter, and is **forbidden from
assuming project context**. Concretely, it must be able to read an artifact cold,
having opened no other file, and come away able to say what the project does and
why someone would use it.

If that is not possible, the artifact is wrong, not the reader.

## The audience contract

Style is not one thing, because the reader is not one person. What is correct in
a ledger is wrong in a README.

| Artifact | Reader | May assume | Must define |
|---|---|---|---|
| `README.md` | a stranger who found the repo | general software literacy | **everything else** |
| the paper | a researcher in a neighbouring field | statistics, ML vocabulary | project terms, fault classes, the method |
| dataset cards | someone deciding whether to use the data | the domain | provenance, licence, known gaps |
| `docs/knowledge/*.md` | someone about to change that subsystem | project context | the subsystem's own internals |
| `docs/*/LEDGER.md` | a maintainer with full context | everything | nothing — terseness and grep-ability win |
| `HANDOFF.md` | future maintainers, the owner | project context | the reasoning, not the terms |

**The ledgers are deliberately outside this seat's remit.** They should stay
dense and identifier-heavy. Someone grepping `MTH-018` at midnight wants the
finding, not an on-ramp.

**Linking a document from an outward-facing artifact changes its audience.** A
file under `docs/knowledge/` is normally written for someone who already has
project context. The moment the README points a stranger at it as a suggested
entry point, it inherits the README's contract and has to define its own terms.
Either rewrite it for that reader or stop linking it. This was missed when the
contract was first written: `probes.md` and `detector.md` were classed as
maintainer documents while the README sent newcomers straight to them (RDR-003).

## Rules for outward-facing artifacts

1. **Expand on first use, every artifact, no exceptions.** Not "FDR" but "false
   discovery rate — of everything the tool flags, the share that is not really a
   change". An acronym expanded in `probes.md` is still unexpanded in the README.
2. **No internal identifier as a load-bearing reference.** `MTH-018` may appear
   as a parenthetical pointer *after* the idea has been explained in plain words.
   It may never be the explanation.
3. **Name outside ideas properly.** "The Daikon idea" tells a reader nothing.
   "Daikon, a 2001 tool that watched programs run and guessed the rules their
   variables obeyed" tells them what they need and takes one clause.
4. **Show before you characterise.** A worked example with real input and real
   output beats any amount of description, and belongs before the tables.
5. **Numbers need their question.** A table of figures before the reader knows
   what question the figures answer is decoration.
6. **Bullet points must stand alone.** Lists are what people read first, and
   often all they read. A bullet that only makes sense after the paragraph above
   it has failed at the job bullets are for. Each one states its point, gives the
   number, and says why it matters, without depending on its neighbours.

## Style, with the specific habits to avoid

The house voice sits between a research paper and an accessible repository:
precise about claims, plain about language. Aiming for a reader who is competent
but busy and does not already care.

**Habits that read as machine-written, and are worth breaking anyway:**

- **Em dashes.** Target under 1 per 300 words in outward-facing prose. Commas,
  colons and full stops do the same work without the tic.
- **Staccato fragments.** "The sign names the fault." reads as a slogan rather
  than a sentence. Vary length, and let most sentences be 15 to 25 words.
- **The "not X, but Y" reversal**, used more than once or twice per page. It
  manufactures drama and quickly becomes a mannerism.
- **Tricolons.** Three-item lists as a rhetorical rhythm rather than because
  there happen to be three things.
- **Bold as emphasis on every other clause.** Bold marks the thing a scanner
  must not miss. More than a few per section and it marks nothing.
- **Insider tone.** "Ideas worth stealing", "what's honest about", "the point of
  the whole design". Confiding in the reader before they trust you.
- **Opening with a thesis in bold.** Start with the problem, then the claim.

## Checking rather than hoping

`python scripts/check_prose.py <file>` reports em-dash density, sentence-length
distribution, bold density, and terms used without being defined nearby. It is a
**report, not a gate** — the numbers are advisory and a document can have a good
reason to break any of them. But the same discipline applies here as everywhere
else in this project: measure the thing rather than asserting it improved.
