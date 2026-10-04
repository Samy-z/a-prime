"""ENG-003: the partition is derived once per comparison and shared.

The detector used to re-cluster once per statistic and count only the first
pass, so the cost line under-reported the dominant cost by three. After the
fix the cost line must equal what the predicate actually did, and the
statistics must be exactly what a single joint clustering gives. A counting
predicate stands in for the cross-encoder, so this runs without a model and
the ratio is counted rather than asserted.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime import stats  # noqa: E402
from aprime.clustering import cluster_jointly  # noqa: E402
from aprime.detect import PARTITION_STATS, detect  # noqa: E402
from aprime.recorder import iter_invocations, record  # noqa: E402
from aprime.stub import build_arms  # noqa: E402


class CountingPredicate:
    """Equivalent when the first word matches. Cheap, and it counts."""

    def __init__(self):
        self.pairs_judged = 0
        self.batches = 0

    def equivalent(self, pairs):
        self.pairs_judged += len(pairs)
        self.batches += 1
        return [a.split()[:1] == b.split()[:1] for a, b in pairs]


def _rec(n_inputs=30, n_affected=6, k=8, seed=3):
    ids = [f"in{i:03d}" for i in range(n_inputs)]
    affected = set(ids[:n_affected])
    a, ap, b = build_arms(ids, affected, "mode_share", strength=0.9, seed=seed)
    return record(iter_invocations(ids), {"A": a, "A_prime": ap, "B": b}, k=k)


def test_the_cost_line_reports_what_the_predicate_actually_did():
    rec = _rec()
    pred = CountingPredicate()
    rep = detect(rec, predicate=pred, q=0.10)
    assert rep.cost["predicate_calls"] == pred.pairs_judged
    assert rep.cost["predicate_calls"] > 0
    # One clustering per input per arm pair, and all of them counted.
    assert rep.cost["clusterings"] == 2 * rep.n_inputs


def test_the_three_statistics_come_from_one_partition_each():
    rec = _rec()
    rep = detect(rec, predicate=CountingPredicate(), q=0.10)
    ca, cp, cb = rec.clouds("A"), rec.clouds("A_prime"), rec.clouds("B")
    ids = list(dict.fromkeys(rec.input_ids))
    for other, which in ((cb, "targets"), (cp, "decoys")):
        expect = {s: [] for s in PARTITION_STATS}
        for iid in ids:
            ma, mb, _ = cluster_jointly(ca[iid], other[iid], CountingPredicate())
            expect["mode_share"].append(stats.tv_distance(ma, mb))
            expect["dispersion"].append(stats.dispersion_ratio(ma, mb))
            expect["novel_mode"].append(stats.novel_mode_mass(ma, mb))
        for s in PARTITION_STATS:
            got = getattr(rep.channels[s], which)
            assert np.array_equal(got, np.asarray(expect[s])), (s, which)


def test_re_clustering_per_statistic_would_cost_three_times_as_much():
    """The ratio ENG-003 recorded, counted on the same clouds."""
    rec = _rec()
    ca, cb = rec.clouds("A"), rec.clouds("B")
    ids = list(dict.fromkeys(rec.input_ids))

    once = CountingPredicate()
    for iid in ids:
        cluster_jointly(ca[iid], cb[iid], once)

    thrice = CountingPredicate()
    for _ in PARTITION_STATS:
        for iid in ids:
            cluster_jointly(ca[iid], cb[iid], thrice)

    assert once.pairs_judged > 0
    assert thrice.pairs_judged == 3 * once.pairs_judged


def test_exact_match_path_is_unchanged_and_free():
    rec = _rec()
    rep = detect(rec, q=0.10)
    assert rep.cost["predicate_calls"] == 0
    assert rep.cost["clusterings"] == 2 * rep.n_inputs
