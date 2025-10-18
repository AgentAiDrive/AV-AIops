"""Utilities for parsing chat slash-commands with consistent grammar."""
from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


class SlashCommandError(ValueError):
    """Raised when a slash command cannot be parsed."""


@dataclass
class SlashCommand:
    """Normalized representation of a chat slash command."""
    name: str
    action: Optional[str]
    args: List[str]
    options: Dict[str, str]
    body: str
    raw: str

    def option(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.options.get(key.lower(), default)


# Keep hints simple to avoid escaping issues
_USAGE_HINTS: Dict[str, str] = {
    "agent:run":   'Usage: /agent run <agent name> recipe="<recipe name>"',
    "recipe:new":  'Usage: /recipe new <recipe name>',
    "recipe:attach": 'Usage: /recipe attach agent="<agent name>" recipe="<recipe name>"',
    "tool:health": 'Usage: /tool health <connector name>',
    "tool:action": 'Usage: /tool action <connector name> {"action":...}',
    "sop":         'Usage: /sop agent="Support" name="Reset Projector"\n<Steps...>',
}


def _split_head_tail(command: str) -> Tuple[str, Optional[str], str]:
    parts = command.strip().split(None, 2)
    if not parts:
        raise SlashCommandError("Slash command is empty. Type /help for examples.")
    name = parts[0].lower()
    action = parts[1].lower() if len(parts) >= 2 else None
    tail = parts[2] if len(parts) >= 3 else ""
    return name, action, tail


def _parse_tokens(tail: str) -> List[str]:
    if not tail:
        return []
    try:
        return shlex.split(tail, posix=True)
    except ValueError as exc:
        # Simple message; no tricky escaping
        raise SlashCommandError(
            'Could not parse arguments. Wrap multi-word values in quotes, e.g., "Projector Reset".'
        ) from exc


def parse_slash_command(text: str) -> SlashCommand:
    """Parse `/agent run ...` style commands using shlex for quoting."""
    if not text.strip().startswith("/"):
        raise SlashCommandError("Commands must start with '/'.")
    first_line, *rest = text.strip().splitlines()
    command_text = first_line.lstrip("/")
    body = "\n".join(rest).strip()

    name, action, tail = _split_head_tail(command_text)
    tokens = _parse_tokens(tail)

    args: List[str] = []
    options: Dict[str, str] = {}
    for tok in tokens:
        if "=" in tok:
            key, value = tok.split("=", 1)
            options[key.lower()] = value
        else:
            args.append(tok)

    return SlashCommand(
        name=name,
        action=action,
        args=args,
        options=options,
        body=body,
        raw=text,
    )


def usage_hint(command: SlashCommand | str, action: Optional[str] = None) -> str:
    if isinstance(command, SlashCommand):
        key = f"{command.name}:{command.action}" if command.action else command.name
    else:
        key = f"{command}:{action}" if action else command
    return _USAGE_HINTS.get(key, "See sidebar examples for supported commands.")


# ---- Back-compat + explicit exports -----------------------------------------
# Some older files may import the private name; keep a shim so they don't crash.
_usage_hint = usage_hint

__all__ = [
    "SlashCommand",
    "SlashCommandError",
    "parse_slash_command",
    "usage_hint",
    "_usage_hint",   # temporary back-compat export
]
