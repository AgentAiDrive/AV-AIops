# core/io/port.py  — robust bundle import/export for Agents, Recipes, Workflows
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # We'll guard at runtime if YAML parsing is required

from core.db.session import get_session
from core.db.models import Agent, Recipe
from core.workflow.service import list_workflows, create_workflow, update_workflow

PkgMerge = Literal["skip", "overwrite", "rename"]

# ----------------------- helpers -----------------------

_slug_rx = re.compile(r"[^a-z0-9\\-]+")

def _slug(name: str) -> str:
    s = (name or "").strip().lower().replace(" ", "-")
    s = _slug_rx.sub("-", s).strip("-")
    return s or "item"

def _read_text_from_zip(z: zipfile.ZipFile, path: str) -> str:
    return z.read(path).decode("utf-8")

def _ensure_yaml(module: Any) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required to import raw recipe YAMLs in a bundle (missing 'yaml' package).")

# ----------------------- export -----------------------

def export_zip(*, include: Iterable[str], recipes_dir: str | Path = "recipes") -> tuple[bytes, Dict[str, Any]]:
    """
    Export selected objects to a single ZIP (bytes), along with a report.
    include: subset of {"agents","recipes","workflows"}
    recipes_dir: where recipe YAMLs are stored/read from for export references
    """
    include = set(include or [])
    report: Dict[str, Any] = {"counts": {"agents": 0, "recipes": 0, "workflows": 0}}

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z, get_session() as db:
        # Agents ---------------------------------------------------------------
        if "agents" in include:
            agents = db.query(Agent).order_by(Agent.name).all()
            rows = []
            for a in agents:
                rows.append({
                    "name": a.name,
                    "domain": getattr(a, "domain", "") or "",
                    "config_json": getattr(a, "config_json", {}) or {},
                })
            z.writestr("agents.json", json.dumps(rows, indent=2))
            report["counts"]["agents"] = len(rows)

        # Recipes --------------------------------------------------------------
        recipe_index: list[dict] = []
        if "recipes" in include:
            recipes = db.query(Recipe).order_by(Recipe.name).all()
            base = Path(recipes_dir)
            for r in recipes:
                ytxt: Optional[str] = None
                yname = _slug(r.name) + ".yaml"
                yaml_path = getattr(r, "yaml_path", None)
                yaml_text = getattr(r, "yaml", None)

                if yaml_text:
                    ytxt = yaml_text
                elif yaml_path and (base / yaml_path).exists():
                    try:
                        ytxt = (base / yaml_path).read_text(encoding="utf-8")
                    except Exception:
                        pass

                if not ytxt:
                    ytxt = f"# Missing source; stub for recipe '{r.name}'\\napi_version: v1\\nname: {r.name}\\n"

                path_in_zip = f"recipes/{yname}"
                z.writestr(path_in_zip, ytxt)
                recipe_index.append({"name": r.name, "file": path_in_zip})

            z.writestr("recipes.json", json.dumps(recipe_index, indent=2))
            report["counts"]["recipes"] = len(recipe_index)

        # Workflows ------------------------------------------------------------
        if "workflows" in include:
            agents_by_id = {a.id: a.name for a in db.query(Agent).all()}
            recipes_by_id = {r.id: r.name for r in db.query(Recipe).all()}
            rows = []
            for wf in list_workflows(db):
                rows.append({
                    "name": wf.name,
                    "enabled": bool(getattr(wf, "enabled", 1)),
                    "trigger": getattr(wf, "trigger_type", "manual"),
                    "interval_minutes": getattr(wf, "trigger_value", None),
                    "agent_name": agents_by_id.get(getattr(wf, "agent_id", None), ""),
                    "recipe_name": recipes_by_id.get(getattr(wf, "recipe_id", None), ""),
                })
            z.writestr("workflows.json", json.dumps(rows, indent=2))
            report["counts"]["workflows"] = len(rows)

        # Manifest (optional but helpful) -------------------------------------
        from datetime import datetime as _dt
        manifest = {
            "bundle_version": 1,
            "generated_at": _dt.utcnow().isoformat() + "Z",
            "includes": {
                "agents": "agents.json" if "agents" in include else None,
                "recipes": "recipes.json" if "recipes" in include else None,
                "workflows": "workflows.json" if "workflows" in include else None,
            },
        }
        z.writestr("manifest.json", json.dumps(manifest, indent=2))

    return out.getvalue(), report

# ----------------------- import -----------------------

def import_zip(
    zip_bytes: bytes,
    recipes_dir: str | Path = "recipes",
    merge: PkgMerge = "skip",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Imports a previously exported bundle.
    merge:
      - "skip": keep existing, skip duplicates by name
      - "overwrite": update existing objects in place
      - "rename": keep both by appending a numeric suffix
    Returns a report dict with created/updated/skipped counts and messages.
    """
    recipes_dir = Path(recipes_dir)
    result = {
        "dry_run": dry_run,
        "merge": merge,
        "created": {"agents": 0, "recipes": 0, "workflows": 0},
        "updated": {"agents": 0, "recipes": 0, "workflows": 0},
        "skipped": {"agents": 0, "recipes": 0, "workflows": 0},
        "messages": [],
    }
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z, get_session() as db:
        # ---------- Agents ----------
        if "agents.json" in z.namelist():
            agents = json.loads(z.read("agents.json").decode("utf-8"))
            existing = {a.name.lower(): a for a in db.query(Agent).all()}
            for row in agents:
                name = (row.get("name") or "").strip()
                if not name:
                    result["messages"].append("Agent with empty name skipped.")
                    result["skipped"]["agents"] += 1
                    continue
                key = name.lower()
                if key in existing:
                    if merge == "skip":
                        result["skipped"]["agents"] += 1
                        continue
                    if merge == "rename":
                        i = 2
                        new_name = f"{name} ({i})"
                        while new_name.lower() in existing:
                            i += 1
                            new_name = f"{name} ({i})"
                        name = new_name
                    elif merge == "overwrite":
                        if not dry_run:
                            a = existing[key]
                            a.domain = row.get("domain") or a.domain
                            a.config_json = row.get("config_json") or a.config_json
                        result["updated"]["agents"] += 1
                        continue
                if not dry_run:
                    db.add(Agent(name=name, domain=row.get("domain") or "", config_json=row.get("config_json") or {}))
                result["created"]["agents"] += 1
            if not dry_run:
                db.commit()
        # ---------- Recipes ----------
        recipe_map_by_name: Dict[str, str] = {}
        if "recipes.json" in z.namelist():
            recipe_index = json.loads(z.read("recipes.json").decode("utf-8"))
            recipe_map_by_name = {r["name"]: r["file"] for r in recipe_index}
            existing = {r.name.lower(): r for r in db.query(Recipe).all()}
            recipes_dir.mkdir(parents=True, exist_ok=True)
            for name, file_in_zip in recipe_map_by_name.items():
                ytxt = z.read(file_in_zip).decode("utf-8")
                key = name.lower()
                if key in existing:
                    if merge == "skip":
                        result["skipped"]["recipes"] += 1
                        continue
                    if merge == "rename":
                        i = 2
                        candidate = f"{name} ({i})"
                        while candidate.lower() in existing:
                            i += 1
                            candidate = f"{name} ({i})"
                        name = candidate
                        key = name.lower()
                    elif merge == "overwrite":
                        if not dry_run:
                            r = existing[key]
                            # Write new YAML file and update pointer if using yaml_path
                            fn = _slug(name) + ".yaml"
                            (recipes_dir / fn).write_text(ytxt, encoding="utf-8")
                            if hasattr(r, "yaml_path"):
                                r.yaml_path = fn
                            elif hasattr(r, "yaml"):
                                setattr(r, "yaml", ytxt)
                        result["updated"]["recipes"] += 1
                        continue
                # create new
                if not dry_run:
                    fn = _slug(name) + ".yaml"
                    (recipes_dir / fn).write_text(ytxt, encoding="utf-8")
                    db.add(Recipe(name=name, yaml_path=fn))
                result["created"]["recipes"] += 1
            if not dry_run:
                db.commit()
        # ---------- Workflows ----------
        if "workflows.json" in z.namelist():
            wfs = json.loads(z.read("workflows.json").decode("utf-8"))
            existing_names = {wf.name.lower(): wf for wf in list_workflows(db)}
            agents_by_name = {a.name.lower(): a for a in db.query(Agent).all()}
            recipes_by_name = {r.name.lower(): r for r in db.query(Recipe).all()}
            for row in wfs:
                name = (row.get("name") or "").strip()
                if not name:
                    result["messages"].append("Workflow with empty name skipped.")
                    result["skipped"]["workflows"] += 1
                    continue
                agent = agents_by_name.get((row.get("agent_name") or "").lower())
                recipe = recipes_by_name.get((row.get("recipe_name") or "").lower())
                if not agent or not recipe:
                    result["messages"].append(
                        f"Workflow '{name}' skipped (agent/recipe not found: {row.get('agent_name')} / {row.get('recipe_name')})."
                    )
                    result["skipped"]["workflows"] += 1
                    continue
                key = name.lower()
                if key in existing_names:
                    # Handle duplicates based on merge strategy
                    if merge == "skip":
                        result["skipped"]["workflows"] += 1
                        continue
                    if merge == "rename":
                        i = 2
                        candidate = f"{name} ({i})"
                        while candidate.lower() in existing_names:
                            i += 1
                            candidate = f"{name} ({i})"
                        name = candidate
                        key = name.lower()
                    elif merge == "overwrite":
                        if not dry_run:
                            wf = existing_names[key]
                            update_workflow(
                                db, wf.id,
                                name=name,
                                agent_id=agent.id,
                                recipe_id=recipe.id,
                                trigger_type=row.get("trigger", getattr(wf, "trigger_type", "manual")),
                                trigger_value=row.get("interval_minutes", getattr(wf, "trigger_value", None)),
                                enabled=1 if row.get("enabled", True) else 0,
                            )
                        result["updated"]["workflows"] += 1
                        continue
                # Create new workflow
                if not dry_run:
                    new_wf = create_workflow(
                        db,
                        name=name,
                        agent_id=agent.id,
                        recipe_id=recipe.id,
                        trigger_type=row.get("trigger", "manual"),
                        trigger_value=row.get("interval_minutes"),
                    )
                    # If the imported workflow was disabled, reflect that
                    if not row.get("enabled", True):
                        update_workflow(db, new_wf.id, enabled=0)
                result["created"]["workflows"] += 1
            if not dry_run:
                db.commit()
    return result
