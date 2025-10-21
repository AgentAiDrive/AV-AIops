import os
import json
from pathlib import Path
import requests

BASE_URL = os.environ["SERVICENOW_BASE_URL"].rstrip("/")
API_TOKEN = os.environ.get("SERVICENOW_BOT_TOKEN")  # if using API key auth

def _headers(json_body=True):
    h = {"Accept": "application/json"}
    if API_TOKEN:
        h["x-sn-apikey"] = API_TOKEN
    if json_body:
        h["Content-Type"] = "application/json"
    return h

def kb_create(short_description: str, html_text: str, kb_base_sys_id: str, **extra):
    payload = {
        "short_description": short_description,
        "text": html_text,  # HTML body
        "kb_knowledge_base": kb_base_sys_id,
    }
    payload.update({k: v for k, v in extra.items() if v is not None})
    r = requests.post(
        f"{BASE_URL}/api/now/table/kb_knowledge",
        headers=_headers(json_body=True),
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["result"]

def kb_get(sys_id: str):
    r = requests.get(
        f"{BASE_URL}/api/now/table/kb_knowledge/{sys_id}",
        headers=_headers(json_body=False),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["result"]

def kb_update(sys_id: str, **fields):
    r = requests.patch(
        f"{BASE_URL}/api/now/table/kb_knowledge/{sys_id}",
        headers=_headers(json_body=True),
        json=fields,
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["result"]

def kb_attach(sys_id: str, file_path: str):
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(p)
    with p.open("rb") as f:
        files = {"file": (p.name, f, "application/octet-stream")}
        params = {
            "table_name": "kb_knowledge",
            "table_sys_id": sys_id,
            "file_name": p.name,
        }
        r = requests.post(
            f"{BASE_URL}/api/now/attachment/file",
            headers=_headers(json_body=False),
            files=files,
            params=params,
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["result"]
