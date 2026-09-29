"""Why did a channel report nothing? Read its target and decoy distributions.

`0 flagged, thr=inf` is the only thing a channel says when it fails, and it says
the same thing whether the systems are identical, whether the statistic is blind
to the change, or whether the null is simply too wide for the signal. Those need
different fixes, and the report cannot tell them apart.

This reruns the detector over a recording already on disk and prints, per
channel, where the targets sit against the decoys, split by whether the fault
actually fired. Reading it:

- **Targets on fired inputs above the decoys** means the statistic sees the
  change and the threshold could not be set, which is a power or sample-size
  problem.
- **Targets on fired inputs sitting among the decoys** means the statistic is
  blind to this change, which is a channel problem and no amount of data fixes
  it.
- **Decoys spread as wide as the targets** means the system's own run-to-run
  variation is as large as the fault's effect, which is a property of the system
  and not a defect anywhere.

Needs the NLI model but no system under test, so it is cheap and repeatable.
"""

from __future__ import annotations

import glob
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.net import enable_os_truststore  # noqa: E402

enable_os_truststore()

import numpy as np  # noqa: E402

from aprime.clustering import NLIEquivalence  # noqa: E402
from aprime.detect import detect  # noqa: E402
from aprime.probes.channels import NLI_MODELS, NLIChannel  # noqa: E402
from aprime.recorder import Recording, load_checkpoint  # noqa: E402


def newest(pattern: str) -> Path:
    hits = sorted(glob.glob(str(ROOT / "results" / pattern)))
    if not hits:
        raise SystemExit(f"no file matching {pattern} under results/")
    return Path(hits[-1])


def describe(name: str, vals: np.ndarray) -> str:
    if len(vals) == 0:
        return f"{name}: empty"
    v = sorted(float(x) for x in vals)
    return (f"{name}: n={len(v)} min={v[0]:.4f} med={st.median(v):.4f} "
            f"max={v[-1]:.4f}")


def main() -> int:
    cp = Path(sys.argv[1]) if len(sys.argv) > 1 else newest("cell_detection_*.jsonl")
    art = newest("cell_detection_*.json")
    samples, done, _ = load_checkpoint(cp)
    k = max(s.sample_idx for s in samples) + 1
    ids = list(dict.fromkeys(s.input_id for s in samples))
    rec = Recording(samples=samples, k=k, input_ids=ids)
    activation = json.loads(art.read_text(encoding="utf-8")).get("activation", {})
    fired = [i for i in ids if activation.get(i)]
    quiet = [i for i in ids if i in activation and not activation[i]]

    print(f"recording {cp.name}: {len(samples)} samples, {len(ids)} inputs, k={k}")
    print(f"activation from {art.name}: {len(fired)} fired, {len(quiet)} quiet")
    print()

    nli = NLIChannel(next(s for s in NLI_MODELS if s.key == "deberta_mnli"))
    rep = detect(rec, predicate=NLIEquivalence(nli, threshold=0.7),
                 nli_channel=nli, q=0.10)

    order = {iid: n for n, iid in enumerate(ids)}
    fi = np.array([order[i] for i in fired if i in order], dtype=int)
    qi = np.array([order[i] for i in quiet if i in order], dtype=int)

    for name, ch in rep.channels.items():
        if ch.skipped:
            print(f"--- {name}: SKIPPED ({ch.skipped})")
            print()
            continue
        t, d = np.asarray(ch.targets, float), np.asarray(ch.decoys, float)
        print(f"--- {name}")
        print("    " + describe("targets, fault fired", t[fi] if len(fi) else t[:0]))
        print("    " + describe("targets, fault quiet", t[qi] if len(qi) else t[:0]))
        print("    " + describe("decoys, all inputs  ", d))

        # The question the FDR estimator actually asks: is there a cut where
        # many targets sit above almost every decoy?
        best = None
        for cut in np.unique(t)[::-1]:
            above_t = int((t >= cut).sum())
            above_d = int((d >= cut).sum())
            est = (1 + above_d) / max(above_t, 1)
            if best is None or est < best[0]:
                best = (est, float(cut), above_t, above_d)
        if best:
            est, cut, at, ad = best
            print(f"    best achievable estimate {est:.3f} at cut {cut:.4f} "
                  f"({at} targets, {ad} decoys above) -- needs <= 0.100")
        sep = 0.0
        if len(fi):
            sep = float(np.mean(t[fi]) - np.mean(d))
        print(f"    mean(target|fired) - mean(decoy) = {sep:+.4f}")
        print()

    print("conformance:", rep.contract.summary() if hasattr(rep.contract, "summary")
          else rep.contract)
    print()
    print("cost:", json.dumps(rep.cost))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
