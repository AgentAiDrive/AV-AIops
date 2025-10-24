from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence, Set, Any

__all__ = ["PolicyViolation", "assert_allowed", "is_allowed", "enforce_policy"]

@dataclass
class PolicyViolation(Exception):
    action: str
    tool: Optional[str] = None
    tags: Sequence[str] = ()
    reason: str = "Blocked by policy"
    def __str__(self) -> str:
        t = f" tool={self.tool}" if self.tool else ""
        g = f" tags={list(self.tags)}" if self.tags else ""
        return f"{self.reason}: action={self.action}{t}{g}"

def _as_set(x: Optional[Iterable[str]]) -> Set[str]:
    if not x:
        return set()
    return {str(i).strip() for i in x if str(i).strip()}

def _norm_policy(policy: Optional[Mapping[str, Any]]) -> Mapping[str, Set[str]]:
    """
    Normalize a loose policy mapping into allow/deny sets.
    Supports any/all of:
      - allow_tools / deny_tools
      - allow_actions / deny_actions
      - allow_tags / deny_tags
    Missing keys => permissive by default.
    """
    policy = policy or {}
    return {
        "allow_tools": _as_set(policy.get("allow_tools")),
        "deny_tools": _as_set(policy.get("deny_tools")),
        "allow_actions": _as_set(policy.get("allow_actions")),
        "deny_actions": _as_set(policy.get("deny_actions")),
        "allow_tags": _as_set(policy.get("allow_tags")),
        "deny_tags": _as_set(policy.get("deny_tags")),
    }

def is_allowed(
    action: str,
    *,
    tool: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
    policy: Optional[Mapping[str, Any]] = None,
) -> bool:
    p = _norm_policy(policy)
    tagset = _as_set(tags)

    # 1) hard denies win
    if tool and tool in p["deny_tools"]:
        return False
    if action in p["deny_actions"]:
        return False
    if tagset and (tagset & p["deny_tags"]):
        return False

    # 2) allows (if present) must match at least one dimension
    any_allows = any(p[k] for k in ("allow_tools", "allow_actions", "allow_tags"))
    if any_allows:
        allow_ok = False
        if tool and p["allow_tools"] and tool in p["allow_tools"]:
            allow_ok = True
        if p["allow_actions"] and action in p["allow_actions"]:
            allow_ok = True
        if tagset and p["allow_tags"] and (tagset & p["allow_tags"]):
            allow_ok = True
        return allow_ok

    # 3) default permissive
    return True

def assert_allowed(
    action: str,
    *,
    tool: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
    policy: Optional[Mapping[str, Any]] = None,
    reason: Optional[str] = None,
) -> None:
    """
    Back-compatible guard used by fixed agents and workflow engine.
    If `policy` is None or empty -> permissive.
    """
    if not is_allowed(action, tool=tool, tags=tags, policy=policy):
        raise PolicyViolation(
            action=action,
            tool=tool,
            tags=list(tags or []),
            reason=reason or "Blocked by policy",
        )

def enforce_policy(
    action: str,
    *,
    tool: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
    policy: Optional[Mapping[str, Any]] = None,
) -> None:
    """Alias kept for older call-sites."""
    assert_allowed(action, tool=tool, tags=tags, policy=policy)
