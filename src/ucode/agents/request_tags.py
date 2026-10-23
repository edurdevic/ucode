"""Request-tag header helper shared by coding-agent launchers."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

from ucode.constants import AI_GATEWAY_REQUEST_TAGS_ENV_VAR, AI_GATEWAY_REQUEST_TAGS_PROJECT_FILE
from ucode.ui import print_warning_err


def request_tags_header_value(
    env: Mapping[str, str] | None = None, cwd: Path | None = None
) -> str | None:
    """The ``Databricks-Ai-Gateway-Request-Tags`` value for this session, or None.

    Reads ``AI_GATEWAY_REQUEST_TAGS`` (defaulting to the process environment) and
    returns its stripped value when set. When it is unset or blank, falls back to
    the project default at ``.ucode/request-tags.json`` under ``cwd`` (defaulting
    to the process working directory) so callers can simply skip the header when
    neither is present.

    A value containing a line break cannot be sent as a single HTTP header: for
    Claude it would spill into extra header lines, and other agents' HTTP clients
    reject it before the request reaches the gateway. An env var value with a line
    break is warned about and skipped (returns None) rather than silently
    corrupting the request; a project file may be pretty-printed across multiple
    lines and is instead re-serialized onto a single line."""
    source = os.environ if env is None else env
    value = (source.get(AI_GATEWAY_REQUEST_TAGS_ENV_VAR) or "").strip()
    if not value:
        return _project_request_tags_file_value(cwd)
    if "\n" in value or "\r" in value:
        print_warning_err(
            f"Ignoring {AI_GATEWAY_REQUEST_TAGS_ENV_VAR}: value contains line breaks. Provide the tags as JSON on a single line."
        )
        return None
    try:
        # Make sure the value is a JSON object
        parsed = json.loads(value)
        if type(parsed) is not dict:
            print_warning_err(
                f"Ignoring {AI_GATEWAY_REQUEST_TAGS_ENV_VAR}: expected a JSON object, but got a {type(parsed)}"
            )
            return None
        return value
    except Exception as e:
        print_warning_err(
            f"Ignoring {AI_GATEWAY_REQUEST_TAGS_ENV_VAR}: value is not valid JSON. Provide the tags as JSON on a single line.\n{e}"
        )
        return None


def _project_request_tags_file_value(cwd: Path | None) -> str | None:
    """The request-tags header value from the project's default tags file, or None.

    Reads the JSON object at ``AI_GATEWAY_REQUEST_TAGS_PROJECT_FILE`` under ``cwd``
    (defaulting to the process working directory) when it exists, and returns it
    re-serialized onto a single line so it is always safe to send as one HTTP
    header value. A missing file is not a warning; it just means no project
    default is configured. An unreadable, malformed, or non-object file is warned
    about and skipped (returns None)."""
    directory = Path.cwd() if cwd is None else cwd
    path = directory / AI_GATEWAY_REQUEST_TAGS_PROJECT_FILE
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        print_warning_err(f"Ignoring {path}: could not read file.\n{e}")
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except Exception as e:
        print_warning_err(
            f"Ignoring {path}: value is not valid JSON. Provide the tags as a JSON object.\n{e}"
        )
        return None
    if type(parsed) is not dict:
        print_warning_err(f"Ignoring {path}: expected a JSON object, but got a {type(parsed)}")
        return None
    return json.dumps(parsed, separators=(",", ":"))
