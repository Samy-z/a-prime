"""Connecting a cell to a real model server.

A `Cell` takes a `ChatFn`: messages and tool schemas in, a response body out.
This builds one backed by Ollama, with the same discipline the standalone
adapter enforces (`src/aprime/systems/ollama.py`).

Every parameter that affects output is explicit and none is defaulted to the
vendor's choice, because defaults differ across the pool — temperature 1.0 for
one member and 0.15 for another — so comparing vendor defaults compares sampling
configurations rather than models (BCH-009).

`think` is off. Two of the four pool models reject it with HTTP 400, and for
the study it is held off deliberately so that measured differences cannot come
from reasoning performance. It remains a parameter rather than a hardcoded
constant, because the tool must still expose what the study controls
(HANDOFF §10).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class OllamaChat:
    model: str
    host: str = "http://127.0.0.1:11434"
    num_ctx: int = 8192
    temperature: float = 0.2
    top_p: float = 0.9
    top_k: int = 40
    # 320 truncated a quarter of the first live run mid-sentence. A cut-off
    # output is a confound: the detector would read a length difference that
    # came from this number rather than from the system. `finish_reason`
    # records when it still happens.
    num_predict: int = 512
    seed: int | None = None
    think: bool = False
    # Keep the model resident *during* a run and unload once at the end, via
    # `release()`. Setting this to 0 unloads after every single call, which
    # means paying a multi-gigabyte reload per call -- fine for a handful of
    # probes, ruinous for a batch. Learned the expensive way.
    keep_alive: str | int = "2m"
    timeout: float = 300.0
    # Observed, not configured: the highest prompt size any call reached. This
    # is the measurement D11 asks for before the context cap is fixed.
    peak_prompt_tokens: int = 0
    calls: int = 0

    def options(self) -> dict:
        o = {
            "num_ctx": self.num_ctx,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "num_predict": self.num_predict,
        }
        if self.seed is not None:
            o["seed"] = self.seed
        return o

    def __call__(self, messages: list[dict], tools: list[dict] | None) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": self.think,
            "keep_alive": self.keep_alive,
            "options": self.options(),
        }
        if tools:
            payload["tools"] = tools
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            body = json.loads(r.read().decode())
        self.calls += 1
        pt = body.get("prompt_eval_count") or 0
        if pt > self.peak_prompt_tokens:
            self.peak_prompt_tokens = pt
        return body

    def release(self) -> None:
        """Unload the model now, rather than waiting out the idle timeout.

        Called once when a run finishes. Leaving several gigabytes resident on
        someone else's GPU because a script ended is rude; unloading after every
        call to avoid that is far worse.
        """
        payload = {"model": self.model, "messages": [], "keep_alive": 0}
        req = urllib.request.Request(
            f"{self.host}/api/chat", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=30).read()
        except (urllib.error.URLError, OSError):
            pass
