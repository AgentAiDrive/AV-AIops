# sma-av-streamlit/core/io/port.py
from __future__ import annotations

import io, json, zipfile, tempfile, shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal, Tuple, Dict, Any, List, Optional

import yaml  # PyYAML

from core.db.session import get_session
from core.db.models import Agent, Recipe
from core.workflow.service import list_workflows, create_workflow, update_workflow  # type: ignore

PkgMerge = Literal["skip", "overwrite", "rename"]

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _slug(name: str) -> str:
    s = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in name.strip())
    while "--" in s: s = s.replace("--", "-")
    return s.strip("-_").lower() or "unnamed"

def _safe_yaml(obj: Any) -> str:
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True)

def _recipe_payload(db, r: Recipe, recipes_dir: Path) -> Tuple[str, str]:
    """
    Returns (filename, yaml_text). If r.yaml_path exists, read from disk.
    If not, tries r.yaml or r.yaml_text attributes (if present).
    """
    base = _slug(r.name) or f"recipe-{r.id}"
    fn = f"{base}.yaml"
    # try disk first
    if getattr(r, "yaml_path", None):
        path = (recipes_dir / r.yaml_path) if not Path(r.yaml_path).is_absolute() else Path(r.yaml_path)
        if path.exists():
            return fn, path.read_text(encoding="utf-8")
    # fallbacks (optional columns)
    for attr in ("yaml", "yaml_text", "content"):
        if hasattr(r, attr) and getattr(r, attr):
            return fn, str(getattr(r, attr))
    # minimal stub if nothing else
    return fn, _safe_yaml({"name": r.name, "version": 1, "intake": [], "plan": [], "act": [], "verify": []})

def export_zip(
    include: Iterable[str] = ("agents", "recipes", "workflows"),
    recipes_dir: str | Path = "recipes",
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Creates a portable .zip bundle with:
      - agents.json
      - workflows.json
      - recipes/*.yaml
      - manifest.json
    Returns (zip_bytes, report).
    """
    include = set(i.lower() for i in include)
    recipes_dir = Path(recipes_dir)

    report: Dict[str, Any] = {"exported_at": _utc_now_iso(), "counts": {}, "files": []}
    buf = io.BytesIO()
    with get_session() as db, zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # Agents
        if "agents" in include:
            agents = [
                {"name": a.name, "domain": a.domain, "config_json": getattr(a, "config_json", {})}
                for a in db.query(Agent).order_by(Agent.name).all()
            ]
            z.writestr("agents.json", json.dumps(agents, ensure_ascii=False, indent=2))
            report["counts"]["agents"] = len(agents)
            report["files"].append("agents.json")

        # Recipes (yaml files + index)
        recipe_index: List[Dict[str, str]] = []
        if "recipes" in include:
            for r in db.query(Recipe).order_by(Recipe.name).all():
                fn, ytxt = _recipe_payload(db, r, recipes_dir)
                z.writestr(f"recipes/{fn}", ytxt)
                recipe_index.append({"name": r.name, "file": f"recipes/{fn}"})
                report["files"].append(f"recipes/{fn}")
            z.writestr("recipes.json", json.dumps(recipe_index, ensure_ascii=False, indent=2))
            report["counts"]["recipes"] = len(recipe_index)
            report["files"].append("recipes.json")

        # Workflows (resolved by names, not IDs)
        if "workflows" in include:
            wfs = []
            for wf in list_workflows(db):
                # resolve names
                try:
                    agent_name = db.query(Agent).get(wf.agent_id).name  # type: ignore
                except Exception:
                    agent_name = None
                try:
                    recipe_name = db.query(Recipe).get(wf.recipe_id).name  # type: ignore
                except Exception:
                    recipe_name = None

                wfs.append({
                    "name": wf.name,
                    "enabled": bool(getattr(wf, "enabled", 1)),
                    "trigger": getattr(wf, "trigger", "manual"),
                    "interval_minutes": getattr(wf, "interval_minutes", None),
                    "agent_name": agent_name,
                    "recipe_name": recipe_name,
                })
            z.writestr("workflows.json", json.dumps(wfs, ensure_ascii=False, indent=2))
            report["counts"]["workflows"] = len(wfs)
            report["files"].append("workflows.json")

        manifest = {
            "package": "sma-avops-export",
            "version": "1.0.0",
            "exported_at": report["exported_at"],
            "counts": report["counts"],
            "includes": sorted(list(include)),
        }
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        report["files"].append("manifest.json")

    return buf.getvalue(), report

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
    Returns a report dict with created/updated/skipped and messages.
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
        recipe_map_by_name: Dict[str, str] = {}  # name -> file inside zip
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
                    db.add(Recipe(name=name, yaml_path=fn))  # falls back to column presence
                result["created"]["recipes"] += 1
            if not dry_run:
                db.commit()

        # ---------- Workflows ----------
        if "workflows.json" in z.namelist():
            wfs = json.loads(z.read("workflows.json").decode("utf-8"))
            existing_names = {getattr(w, "name").lower(): w for w in list_workflows(db)}
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
                                agent_id=agent.id,  # type: ignore
                                recipe_id=recipe.id,  # type: ignore
                                trigger=row.get("trigger", getattr(wf, "trigger", "manual")),
                                interval_minutes=row.get("interval_minutes", getattr(wf, "interval_minutes", None)),
                                enabled=1 if row.get("enabled", True) else 0,
                            )
                        result["updated"]["workflows"] += 1
                        continue

                if not dry_run:
                    create_workflow(
                        db,
                        name=name,
                        agent_id=agent.id,  # type: ignore
                        recipe_id=recipe.id,  # type: ignore
                        trigger=row.get("trigger", "manual"),
                        interval_minutes=row.get("interval_minutes"),
                        enabled=1 if row.get("enabled", True) else 0,
                    )
                result["created"]["workflows"] += 1

            if not dry_run:
                db.commit()

    return result