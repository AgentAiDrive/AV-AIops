# sma-av-streamlit/core/agents/fixed/kb_publisher.py
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Optional, Tuple
from urllib.parse import quote_plus

import requests
import streamlit as st

from core.agents.fixed.policies import assert_allowed


class KBPublisher:
    """
    Fixed Agent: Publishes a KB article to ServiceNow (table: kb_knowledge).

    Inputs (payload):
      - title: str               # KB title (maps to short_description)
      - html: str                # KB HTML body (maps to text)
      - tags: list[str] | None   # optional tags/keywords
      - audience: str | None     # used as category/folder label when present
      - meta: dict | None        # carried through into 'work_notes' JSON

    Config & Secrets resolution (priority order):
      1) st.secrets["servicenow"][...]
      2) flat st.secrets["SERVICENOW_*"]
      3) environment variables SERVICENOW_* (optional fallback)

    Required:
      - instance (e.g., https://dev12345.service-now.com)
      and EITHER:
        - username + token (treated as password for Basic auth)
        - token with 'Bearer ' prefix (Bearer auth)

    Optional:
      - kb_knowledge_base (sys_id or name) -> if name, we will attempt to resolve
    """

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    # ---- public callable -----------------------------------------------------

    def __call__(
        self,
        *,
        title: str,
        html: str,
        tags: Optional[Iterable[str]] = None,
        audience: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        actor_roles: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the publish operation. Raises on failure. Returns metadata dict.

        The workflow engine should pass actor roles; if omitted, we assume ["admin"]
        so local/manual runs by admins don't get blocked unexpectedly.
        """
        actor_roles = actor_roles or ["admin"]

        # Guardrails: RBAC + maintenance window + external write
        assert_allowed("KBPublisher", actor_roles, wants_external_write=True)

        # Resolve config & auth
        cfg = self._load_cfg()
        base = cfg["instance"].rstrip("/")
        auth_kind, auth_value = self._build_auth(cfg)

        # Upsert by title (avoid dup spam). If exists with same title, update.
        # 1) find existing record
        existing = self._find_kb_by_title(base, auth_kind, auth_value, title)

        # 2) compute payload
        payload = self._build_payload(
            cfg=cfg, title=title, html=html, tags=list(tags or []),
            audience=audience, meta=meta or {}
        )

        # 3) create or update
        if existing is None:
            rec = self._create_kb(base, auth_kind, auth_value, payload)
        else:
            rec = self._update_kb(base, auth_kind, auth_value, existing["sys_id"], payload)

        # normalized outputs for the run store / dashboard chips
        sys_id = rec.get("sys_id") or ""
        number = rec.get("number") or ""
        url = f"{base}/kb_view.do?sys_kb_id={quote_plus(sys_id)}" if sys_id else f"{base}/kb_knowledge_list.do"

        return {"kb_number": number, "sys_id": sys_id, "url": url, "status": "published"}

    # ---- config & auth -------------------------------------------------------

    def _load_cfg(self) -> Dict[str, str]:
        # nested secrets
        sn = st.secrets.get("servicenow", {})
        instance = str(sn.get("instance") or st.secrets.get("SERVICENOW_INSTANCE") or os.getenv("SERVICENOW_INSTANCE") or "").strip()
        username = str(sn.get("username") or st.secrets.get("SERVICENOW_USERNAME") or os.getenv("SERVICENOW_USERNAME") or "").strip()
        token = str(sn.get("token") or st.secrets.get("SERVICENOW_TOKEN") or os.getenv("SERVICENOW_TOKEN") or "").strip()
        kb_id = str(sn.get("kb_knowledge_base") or st.secrets.get("SERVICENOW_KB_ID_OR_NAME") or os.getenv("SERVICENOW_KB_ID_OR_NAME") or "").strip()

        if not instance:
            raise RuntimeError("ServiceNow instance not configured (servicenow.instance or SERVICENOW_INSTANCE).")
        if not token and not (username and token):
            raise RuntimeError("ServiceNow credentials not configured (username+token for Basic, or Bearer token).")

        return {
            "instance": instance,
            "username": username,
            "token": token,
            "kb_knowledge_base": kb_id,
        }

    def _build_auth(self, cfg: Dict[str, str]) -> Tuple[str, Any]:
        token = cfg.get("token", "")
        username = cfg.get("username", "")

        if token.startswith("Bearer "):
            # Bearer token auth
            return ("bearer", {"Authorization": token})
        elif username and token:
            # Basic auth (username + token as password)
            return ("basic", (username, token))
        else:
            # token without "Bearer " but no username → treat as bearer
            return ("bearer", {"Authorization": f"Bearer {token}"})

    # ---- payload helpers -----------------------------------------------------

    def _build_payload(
        self,
        *,
        cfg: Dict[str, str],
        title: str,
        html: str,
        tags: list[str],
        audience: Optional[str],
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build a kb_knowledge payload. ServiceNow core fields:
          - short_description: Title
          - text: HTML body
          - kb_knowledge_base: sys_id (optional but recommended)
          - workflow_state: 'published' (try; instance may control via workflow)
          - keywords: comma-separated keywords (fallback for "tags")
          - category: string (we map audience here)
          - work_notes: string (we store meta JSON)
        """
        payload: Dict[str, Any] = {
            "short_description": title[:160],   # SN platform wide limit guard
            "text": html,
            "workflow_state": "published",      # attempt publish; instance may override
            "keywords": ",".join([t for t in tags if t]),
            "category": (audience or "").strip(),
            "work_notes": f"SMA AV-AI Ops metadata: {json.dumps(meta)[:2000]}",
        }

        kb_base = (cfg.get("kb_knowledge_base") or "").strip()
        if kb_base:
            # Accept a sys_id OR a name; if name, resolve to sys_id
            if self._looks_like_sys_id(kb_base):
                payload["kb_knowledge_base"] = kb_base
            else:
                resolved = self._resolve_kb_base(cfg["instance"], *self._build_auth(cfg), kb_base)
                if resolved:
                    payload["kb_knowledge_base"] = resolved

        return payload

    @staticmethod
    def _looks_like_sys_id(value: str) -> bool:
        # crude sys_id check: 32-char hex
        v = value.replace("-", "").lower()
        return len(v) == 32 and all(c in "0123456789abcdef" for c in v)

    # ---- REST primitives -----------------------------------------------------

    def _headers(self, auth_kind: str, auth_value: Any) -> Dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if auth_kind == "bearer":
            headers.update(auth_value)
        return headers

    def _get(self, base: str, auth_kind: str, auth_value: Any, path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        url = f"{base.rstrip('/')}{path}"
        if auth_kind == "basic":
            r = self.session.get(url, params=params, auth=auth_value, headers=self._headers(auth_kind, auth_value), timeout=30)
        else:
            r = self.session.get(url, params=params, headers=self._headers(auth_kind, auth_value), timeout=30)
        self._ensure_ok(r, "GET", url)
        return r.json()

    def _post(self, base: str, auth_kind: str, auth_value: Any, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{base.rstrip('/')}{path}"
        body = json.dumps(data)
        if auth_kind == "basic":
            r = self.session.post(url, data=body, auth=auth_value, headers=self._headers(auth_kind, auth_value), timeout=30)
        else:
            r = self.session.post(url, data=body, headers=self._headers(auth_kind, auth_value), timeout=30)
        self._ensure_ok(r, "POST", url)
        return r.json()

    def _patch(self, base: str, auth_kind: str, auth_value: Any, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{base.rstrip('/')}{path}"
        body = json.dumps(data)
        if auth_kind == "basic":
            r = self.session.patch(url, data=body, auth=auth_value, headers=self._headers(auth_kind, auth_value), timeout=30)
        else:
            r = self.session.patch(url, data=body, headers=self._headers(auth_kind, auth_value), timeout=30)
        self._ensure_ok(r, "PATCH", url)
        return r.json()

    @staticmethod
    def _ensure_ok(r: requests.Response, method: str, url: str) -> None:
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise RuntimeError(f"ServiceNow {method} {url} failed: {r.status_code} • {detail}")

    # ---- domain ops ----------------------------------------------------------

    def _resolve_kb_base(self, instance: str, auth_kind: str, auth_value: Any, name: str) -> Optional[str]:
        # Table: kb_knowledge_base; field: name; return sys_id if found
        data = self._get(
            instance, auth_kind, auth_value,
            "/api/now/table/kb_knowledge_base",
            params={"sysparm_query": f"name={name}", "sysparm_limit": "1", "sysparm_fields": "sys_id,name"},
        )
        res = data.get("result") or []
        return res[0].get("sys_id") if res else None

    def _find_kb_by_title(self, base: str, auth_kind: str, auth_value: Any, title: str) -> Optional[Dict[str, str]]:
        # Query kb_knowledge by short_description. Return latest if any.
        data = self._get(
            base, auth_kind, auth_value,
            "/api/now/table/kb_knowledge",
            params={
                "sysparm_query": f"short_description={title}^ORDERBYDESCsys_created_on",
                "sysparm_limit": "1",
                "sysparm_fields": "sys_id,number,short_description,workflow_state",
            },
        )
        res = data.get("result") or []
        return res[0] if res else None

    def _create_kb(self, base: str, auth_kind: str, auth_value: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._post(base, auth_kind, auth_value, "/api/now/table/kb_knowledge", payload)
        return data.get("result") or {}

    def _update_kb(self, base: str, auth_kind: str, auth_value: Any, sys_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._patch(base, auth_kind, auth_value, f"/api/now/table/kb_knowledge/{sys_id}", payload)
        return data.get("result") or {}
