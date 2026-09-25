"""Run provenance.

The rail is that every number in the paper traces to a run id and a config
hash. This is the thing that makes that true, and it has to exist before the
first real run rather than after, because provenance cannot be reconstructed
retroactively — by the time a number looks wrong, the environment that produced
it is gone.

What gets captured splits into two kinds, and the distinction matters:

- **Inputs to the config hash** — anything that changes the result. Instrument
  revisions, k, the FDR budget, thresholds, the corpus fingerprint. Two runs
  with the same config hash should be comparable; if they are not, something
  that affects results is missing from the hash, and that is a bug worth
  hunting rather than living with.
- **Recorded but not hashed** — the git commit, platform, package versions,
  wall-clock. These explain a discrepancy after the fact without making every
  environment change look like a different configuration.

Dirty working trees are recorded and warned about, not blocked. Blocking would
push people to commit noise to satisfy a tool; a loud warning plus a permanent
record in the run file is the honest trade.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_TRACKED_PACKAGES = (
    "torch",
    "transformers",
    "sentence-transformers",
    "numpy",
    "scipy",
)


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).resolve().parents[2],
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _package_versions() -> dict[str, str]:
    from importlib.metadata import PackageNotFoundError, version

    out: dict[str, str] = {}
    for name in _TRACKED_PACKAGES:
        try:
            out[name] = version(name)
        except PackageNotFoundError:
            continue
    return out


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def corpus_fingerprint(input_ids: list[str], texts: dict[str, str] | None = None) -> str:
    """Stable digest of which inputs a run covered.

    Order-independent, so a reshuffled corpus is recognised as the same corpus.
    Includes the text when available, because two runs over the same ids with
    different content are not the same run.
    """
    h = hashlib.sha256()
    for iid in sorted(input_ids):
        h.update(iid.encode())
        if texts and iid in texts:
            h.update(b"\x00")
            h.update(texts[iid].encode())
        h.update(b"\n")
    return h.hexdigest()[:16]


@dataclass
class RunProvenance:
    run_id: str
    config_hash: str
    created_utc: str
    # Hashed — these change the result.
    instruments: dict[str, str] = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    corpus: str = ""
    # Recorded but not hashed — these explain a discrepancy.
    git_commit: str | None = None
    git_branch: str | None = None
    git_dirty: bool = False
    platform: str = ""
    python: str = ""
    packages: dict[str, str] = field(default_factory=dict)
    notes: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    def write(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(), encoding="utf-8")
        return p


def compute_config_hash(
    instruments: dict[str, str], params: dict, corpus: str
) -> str:
    """Digest of everything that changes the result.

    Sorted and canonically serialised so a dict built in a different order
    hashes the same — otherwise the hash would report spurious differences and
    quickly stop being trusted, which is worse than not having one.
    """
    payload = json.dumps(
        {"instruments": instruments, "params": params, "corpus": corpus},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def capture(
    instruments: dict[str, str],
    params: dict,
    corpus: str = "",
    notes: dict | None = None,
    warn_if_dirty: bool = True,
) -> RunProvenance:
    """Snapshot everything needed to explain this run later.

    `instruments` maps a role to `hub_id@revision` — the revision, not the
    name. A bare model name is not a pin, because what sits behind a name on the
    hub can change.
    """
    for role, ident in instruments.items():
        if "@" not in ident:
            warnings.warn(
                f"instrument {role!r} recorded as {ident!r} with no revision. "
                "A bare model name is not a pin; resolve the commit SHA.",
                stacklevel=2,
            )

    status = _git("status", "--porcelain")
    dirty = bool(status)
    if dirty and warn_if_dirty:
        n = len(status.splitlines()) if status else 0
        warnings.warn(
            f"working tree has {n} uncommitted change(s). The run is recorded "
            "anyway, but its git commit does not describe the code that ran.",
            stacklevel=2,
        )

    return RunProvenance(
        run_id=new_run_id(),
        config_hash=compute_config_hash(instruments, params, corpus),
        created_utc=datetime.now(timezone.utc).isoformat(),
        instruments=dict(instruments),
        params=dict(params),
        corpus=corpus,
        git_commit=_git("rev-parse", "HEAD"),
        git_branch=_git("rev-parse", "--abbrev-ref", "HEAD"),
        git_dirty=dirty,
        platform=platform.platform(),
        python=sys.version.split()[0],
        packages=_package_versions(),
        notes=notes or {},
    )
