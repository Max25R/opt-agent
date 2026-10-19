"""Every Claude API call goes through call(): one request, sent with our own timed retries,
replayed from a cache when it has been sent before, and never raising an API error.

- **One request dict.** The caller builds it once (formulate.build_request,
  explain.build_request); the same dict is sent, hashed, cached, and logged, so the log
  can't drift from what was actually sent.
- **Pinned settings.** Thinking and effort are written out even though they're the current
  defaults for claude-haiku-5-5 (adaptive thinking with its text omitted; medium effort),
  so a change of defaults can't silently change a run.
- **Our own retries.** The SDK retries too, but it doesn't say how long that took. We turn
  its retries off and use the same rule (connection errors, 408, 409, 429, 5xx, or the
  server's x-should-retry header), so retry time is measured apart from latency.
- **A failure is a result, not an exception.** After the last try the error comes back in
  CallInfo.error, so the run goes on and the problem is counted as failed, not skipped.
- **The cache** keys each response by the SHA-256 of the full request. Sending the same
  request again replays the response: a crashed run resumes where it stopped, and a
  finished run can be reproduced without an API key. Failed calls aren't cached, so a
  re-run retries them.
"""

import hashlib
import json
import os
import time
from pathlib import Path

import anthropic
from anthropic.types import Message
from pydantic import BaseModel

MAX_TOKENS = 16_000  # leaves room for thinking, which counts toward max_tokens
THINKING = {"type": "adaptive", "display": "omitted"}
EFFORT = "medium"

MAX_TRIES = 5
FIRST_WAIT_S, MAX_WAIT_S = 0.5, 60.0

# Why a reply is unfinished, for every stop_reason other than end_turn and stop_sequence.
UNFINISHED = {
    "refusal": "Claude declined to answer",
    "max_tokens": f"the reply was cut off at {MAX_TOKENS} tokens",
    "model_context_window_exceeded": "the reply was cut off at the context window's limit",
    "pause_turn": "the API paused the turn before the reply was finished",
    "tool_use": "Claude asked for a tool, but none was offered",
}


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0  # includes thinking tokens
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    thinking_tokens: int | None = None  # as the API reports it, when it does


class CallInfo(BaseModel):
    """How a call went, apart from what Claude said."""

    request_sha256: str  # the cache key
    tries: int = 0
    latency_s: float = 0.0  # the try that got the response (or the last one that failed)
    retry_s: float = 0.0  # failed tries and the waits after them
    cached: bool = False  # replayed from the cache; the times are the original call's
    error: str | None = None  # the API error, if every try failed


def request_sha256(request: dict) -> str:
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def call(
    client: anthropic.Anthropic, request: dict, cache: "Cache | None" = None
) -> tuple[Message | None, CallInfo]:
    key = request_sha256(request)
    if cache is not None and (hit := cache.get(key)) is not None:
        return hit
    response, info = _send(client, request, key)
    if cache is not None and response is not None:
        cache.put(key, request, response, info)
    return response, info


def _send(client: anthropic.Anthropic, request: dict, key: str) -> tuple[Message | None, CallInfo]:
    client = client.with_options(max_retries=0)  # we retry, so we can time it
    retry_s = 0.0
    for number in range(1, MAX_TRIES + 1):
        start = time.perf_counter()
        try:
            response = client.messages.create(**request)
        except anthropic.APIError as error:
            elapsed = time.perf_counter() - start
            if number == MAX_TRIES or not retryable(error):
                info = CallInfo(request_sha256=key, tries=number, latency_s=elapsed,
                                retry_s=retry_s, error=describe(error))  # fmt: skip
                return None, info
            wait = wait_s(error, number)
            time.sleep(wait)
            retry_s += elapsed + wait
            continue
        latency = time.perf_counter() - start
        return response, CallInfo(request_sha256=key, tries=number, latency_s=latency,
                                  retry_s=retry_s)  # fmt: skip
    raise AssertionError("unreachable: the last try always returns")


def retryable(error: anthropic.APIError) -> bool:
    """The SDK's own rule (anthropic._base_client._should_retry)."""
    if isinstance(error, anthropic.APIConnectionError):  # includes time-outs
        return True
    if not isinstance(error, anthropic.APIStatusError):
        return False
    told = error.response.headers.get("x-should-retry")
    if told in ("true", "false"):
        return told == "true"
    return error.status_code in (408, 409, 429) or error.status_code >= 500


def wait_s(error: anthropic.APIError, number: int) -> float:
    """What the server asks for (retry-after), else exponential backoff: 0.5, 1, 2, ... s."""
    if isinstance(error, anthropic.APIStatusError):
        try:
            return min(max(float(error.response.headers.get("retry-after")), 0.0), MAX_WAIT_S)
        except (TypeError, ValueError):
            pass  # missing, or an HTTP date: fall back to backoff
    return min(FIRST_WAIT_S * 2 ** (number - 1), MAX_WAIT_S)


def describe(error: anthropic.APIError) -> str:
    status = f" ({error.status_code})" if isinstance(error, anthropic.APIStatusError) else ""
    return f"{type(error).__name__}{status}: {error.message}"


def reply_text(response: Message) -> str:
    """The text blocks, in order. Thinking blocks are skipped (their text is omitted anyway)."""
    return "".join(block.text for block in response.content if block.type == "text")


def usage_of(response: Message | None) -> TokenUsage:
    if response is None:
        return TokenUsage()
    u = response.usage
    details = getattr(u, "output_tokens_details", None)
    return TokenUsage(
        input_tokens=u.input_tokens,
        output_tokens=u.output_tokens,
        cache_read_input_tokens=u.cache_read_input_tokens or 0,
        cache_creation_input_tokens=u.cache_creation_input_tokens or 0,
        thinking_tokens=getattr(details, "thinking_tokens", None),
    )


class Cache:
    """Successful responses on disk, one JSON file per request hash."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)

    def get(self, key: str) -> tuple[Message, CallInfo] | None:
        path = self._path(key)
        if not path.exists():
            return None
        entry = json.loads(path.read_text())
        info = CallInfo.model_validate(entry["info"]).model_copy(update={"cached": True})
        return Message.model_validate(entry["response"]), info

    def put(self, key: str, request: dict, response: Message, info: CallInfo) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        entry = {
            "request": request,
            "response": response.model_dump(mode="json"),
            "info": info.model_dump(mode="json"),
        }
        temporary = self._path(key).with_suffix(".tmp")
        temporary.write_text(json.dumps(entry, indent=1, ensure_ascii=False) + "\n")
        os.replace(temporary, self._path(key))  # atomic: a crash never leaves half a file

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"
