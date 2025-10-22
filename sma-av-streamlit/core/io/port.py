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
    Import a bundle produced by export_zip(), with robust fallbacks:
      - Agents: accept agents.json or JSON files under agents/
      - Recipes: accept recipes.json index; or fallback to recipes/*.yaml (parse name from YAML)
      - Workflows: accept workflows.json; or fallback to workflows/*.json (normalize common keys)
    Writes recipe YAMLs into recipes_dir (must be writable).
    Returns detailed counts & messages.
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

    def _maybe_commit(db):
        if not dry_run:
            db.commit()

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z, get_session() as db:
        names = z.namelist()

        # ---------- Agents ----------
        agents_rows: List[Dict[str, Any]] = []
        if "agents.json" in names:
            try:
                agents_rows = json.loads(_read_text_from_zip(z, "agents.json"))
                if not isinstance(agents_rows, list):
                    raise ValueError("agents.json must be a list")
            except Exception as e:
                result["messages"].append(f"agents.json parse error: {e}")
        else:
            for n in names:
                if n.startswith("agents/") and n.lower().endswith(".json"):
                    try:
                        agents_rows.append(json.loads(_read_text_from_zip(z, n)))
                    except Exception as e:
                        result["messages"].append(f"{n} parse error: {e}")

        if agents_rows:
            existing = {a.name.lower(): a for a in db.query(Agent).all()}
            for row in agents_rows:
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
                        candidate = f"{name} ({i})"
                        while candidate.lower() in existing:
                            i += 1
                            candidate = f"{name} ({i})"
                        name = candidate
                        key = name.lower()
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
            _maybe_commit(db)

        # ---------- Recipes ----------
        recipes_index: List[Dict[str, str]] = []
        if "recipes.json" in names:
            try:
                recipes_index = json.loads(_read_text_from_zip(z, "recipes.json"))
                if not isinstance(recipes_index, list):
                    raise ValueError("recipes.json must be a list")
            except Exception as e:
                result["messages"].append(f"recipes.json parse error: {e}")
        else:
            yaml_paths = [n for n in names if n.startswith("recipes/") and n.lower().endswith((".yml", ".yaml"))]
            if yaml_paths:
                _ensure_yaml(yaml)
            for yp in yaml_paths:
                ytxt = _read_text_from_zip(z, yp)
                name = None
                try:
                    data = yaml.safe_load(ytxt) if yaml else None
                    if isinstance(data, dict):
                        name = (data.get("name") or "").strip()
                except Exception:
                    pass
                if not name:
                    fn = yp.split("/")[-1]
                    name = re.sub(r"\\.ya?ml$", "", fn, flags=re.I).replace("_", " ").replace("-", " ").strip() or fn
                recipes_index.append({"name": name, "file": yp})

        if recipes_index:
            recipes_dir.mkdir(parents=True, exist_ok=True)
            existing = {r.name.lower(): r for r in db.query(Recipe).all()}
            for entry in recipes_index:
                name = (entry.get("name") or "").strip()
                file_in_zip = entry.get("file")
                if not name or not file_in_zip:
                    result["messages"].append(f"Recipe entry invalid: {entry!r}")
                    result["skipped"]["recipes"] += 1
                    continue

                ytxt = _read_text_from_zip(z, file_in_zip)
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
                            fn = _slug(name) + ".yaml"
                            (recipes_dir / fn).write_text(ytxt, encoding="utf-8")
                            if hasattr(r, "yaml_path"):
                                r.yaml_path = fn
                            elif hasattr(r, "yaml"):
                                setattr(r, "yaml", ytxt)
                        result["updated"]["recipes"] += 1
                        continue
                if not dry_run:
                    fn = _slug(name) + ".yaml"
                    (recipes_dir / fn).write_text(ytxt, encoding="utf-8")
                    db.add(Recipe(name=name, yaml_path=fn))
                result["created"]["recipes"] += 1
            _maybe_commit(db)

        # ---------- Workflows ----------
        workflows_rows: List[Dict[str, Any]] = []
        if "workflows.json" in names:
            try:
                workflows_rows = json.loads(_read_text_from_zip(z, "workflows.json"))
                if not isinstance(workflows_rows, list):
                    raise ValueError("workflows.json must be a list")
            except Exception as e:
                result["messages"].append(f"workflows.json parse error: {e}")
        else:
            for n in names:
                if n.startswith("workflows/") and n.lower().endswith(".json"):
                    try:
                        workflows_rows.append(json.loads(_read_text_from_zip(z, n)))
                    except Exception as e:
                        result["messages"].append(f"{n} parse error: {e}")

        def norm_wf(row: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "name": (row.get("name") or "").strip(),
                "enabled": bool(row.get("enabled", True)),
                "trigger": row.get("trigger") or row.get("trigger_type") or "manual",
                "interval_minutes": row.get("interval_minutes") or row.get("trigger_value"),
                "agent_name": row.get("agent_name") or row.get("agent_ref") or "",
                "recipe_name": row.get("recipe_name") or row.get("recipe_ref") or "",
            }

        if workflows_rows:
            existing_by_name = {wf.name.lower(): wf for wf in list_workflows(db)}
            agents_by_name = {a.name.lower(): a for a in db.query(Agent).all()}
            recipes_by_name = {r.name.lower(): r for r in db.query(Recipe).all()}

            for raw in workflows_rows:
                row = norm_wf(raw)
                name = row["name"]
                if not name:
                    result["messages"].append(f"Workflow with empty/missing name skipped: {raw!r}")
                    result["skipped"]["workflows"] += 1
                    continue

                agent = agents_by_name.get((row["agent_name"] or "").lower())
                recipe = recipes_by_name.get((row["recipe_name"] or "").lower())
                if not agent or not recipe:
                    result["messages"].append(
                        f"Workflow '{name}' skipped — missing agent/recipe: "
                        f"{row['agent_name']} / {row['recipe_name']}"
                    )
                    result["skipped"]["workflows"] += 1
                    continue

                key = name.lower()
                if key in existing_by_name:
                    if merge == "skip":
                        result["skipped"]["workflows"] += 1
                        continue
                    if merge == "rename":
                        i = 2
                        candidate = f"{name} ({i})"
                        while candidate.lower() in existing_by_name:
                            i += 1
                            candidate = f"{name} ({i})"
                        name = candidate
                        key = name.lower()
                    elif merge == "overwrite":
                        if not dry_run:
                            wf = existing_by_name[key]
                            update_workflow(
                                db, wf.id,
                                name=name,
                                agent_id=agent.id,
                                recipe_id=recipe.id,
                                trigger_type=row["trigger"],
                                trigger_value=row["interval_minutes"],
                                enabled=1 if row["enabled"] else 0,
                            )
                        result["updated"]["workflows"] += 1
                        continue

                # create new
                if not dry_run:
                    new_wf = create_workflow(
                        db,
                        name=name,
                        agent_id=agent.id,
                        recipe_id=recipe.id,
                        trigger_type=row["trigger"],
                        trigger_value=row["interval_minutes"],
                    )
                    if not row["enabled"]:
                        update_workflow(db, new_wf.id, enabled=0)
                result["created"]["workflows"] += 1
            _maybe_commit(db)

    return result
