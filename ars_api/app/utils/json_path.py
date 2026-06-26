from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple, Union


class JsonPathError(ValueError):
    pass


@dataclass(frozen=True)
class _Token:
    kind: str  # 'key' or 'index'
    value: Union[str, int]


def _parse_path(path: str) -> List[_Token]:
    """Parse a very small JSON-path style syntax.

    Supported examples:
      - results[0].flight.flight_id
      - meta.request_id
      - passenger.documents[0].document_number

    Rules:
      - dot-separated keys
      - [n] for list index
      - No wildcards, no filters, no fallback logic
    """
    if not path or not isinstance(path, str):
        raise JsonPathError("json path is empty")

    tokens: List[_Token] = []
    i = 0
    buf = ""

    def flush_key() -> None:
        nonlocal buf
        if buf:
            tokens.append(_Token("key", buf))
            buf = ""

    while i < len(path):
        ch = path[i]
        if ch == '.':
            flush_key()
            i += 1
            continue
        if ch == '[':
            flush_key()
            j = path.find(']', i)
            if j == -1:
                raise JsonPathError(f"unclosed [ in path: {path}")
            idx_txt = path[i + 1:j].strip()
            if not idx_txt.isdigit():
                raise JsonPathError(f"list index must be integer in path: {path}")
            tokens.append(_Token("index", int(idx_txt)))
            i = j + 1
            continue
        buf += ch
        i += 1

    flush_key()
    return tokens


def json_get(obj: Any, path: str) -> Any:
    """Read a nested value using the supported json path.

    STRICT behavior:
      - If any key/index is missing, raise JsonPathError
      - No fallback to alternative keys
    """
    cur = obj
    for t in _parse_path(path):
        if t.kind == "key":
            if not isinstance(cur, dict) or t.value not in cur:
                raise JsonPathError(f"missing key '{t.value}' at path '{path}'")
            cur = cur[t.value]
        else:
            if not isinstance(cur, list):
                raise JsonPathError(f"expected list for index access at path '{path}'")
            idx = int(t.value)
            if idx < 0 or idx >= len(cur):
                raise JsonPathError(f"index {idx} out of range at path '{path}'")
            cur = cur[idx]
    return cur


def json_set(obj: Any, path: str, value: Any) -> Any:
    """Set a nested value using supported json path.

    It *creates* missing dict/list containers as needed.

    Example:
      payload = {}
      json_set(payload, 'results[0].flight.flight_id', 12)
      -> {'results': [{'flight': {'flight_id': 12}}]}

    STRICT behavior:
      - Only the exact path is used. No fallback logic.
    """
    tokens = _parse_path(path)
    if not tokens:
        raise JsonPathError("json path has no tokens")

    # Ensure root is dict
    if obj is None:
        obj = {}

    cur = obj
    for idx, t in enumerate(tokens):
        is_last = idx == len(tokens) - 1
        nxt = tokens[idx + 1] if not is_last else None

        if t.kind == "key":
            key = str(t.value)
            if is_last:
                if not isinstance(cur, dict):
                    raise JsonPathError(f"cannot set key '{key}' on non-dict at path '{path}'")
                cur[key] = value
                return obj

            if not isinstance(cur, dict):
                raise JsonPathError(f"expected dict while walking path '{path}'")

            if key not in cur or cur[key] is None:
                # Create container based on next token
                if nxt and nxt.kind == "index":
                    cur[key] = []
                else:
                    cur[key] = {}

            cur = cur[key]

        else:  # index
            i_list = int(t.value)
            if not isinstance(cur, list):
                raise JsonPathError(f"expected list while walking path '{path}'")

            # Expand list as needed
            while len(cur) <= i_list:
                cur.append(None)

            if is_last:
                cur[i_list] = value
                return obj

            if cur[i_list] is None:
                # Create container based on next token
                if nxt and nxt.kind == "index":
                    cur[i_list] = []
                else:
                    cur[i_list] = {}

            cur = cur[i_list]

    return obj
