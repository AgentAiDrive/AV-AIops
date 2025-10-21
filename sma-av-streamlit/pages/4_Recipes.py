# pages/4_Recipes.py
"""
Recipes page for the AV operations assistant.
This script provides a UI for creating, viewing and editing YAML recipes
that encode operational workflows.  Guardrails (timeouts, rollback
actions and success metrics) help avoid runaway automation and should be
included in every recipe.  The page also displays success metrics for
previous runs and integrates with version control to surface git hints.
"""
from __future__ import annotations  # <-- must be here (after docstring)
import os
import subprocess
import json  # Added import so json.dumps works:contentReference[oaicite:2]{index=2}
from datetime import datetime
from pathlib import Path
from core.db.models import Recipe
from core.db.session import get_session
from core.recipes.service import load_recipe_dict, save_recipe_yaml
from core.recipes.validator import validate_yaml_text
from core.runs_store import RunStore
from core.ui.page_tips import show as show_tip
import io, zipfile
from typing import List, Dict, Any
import streamlit as st
import yaml  # ensure PyYAML is in requirements
from core.io.port import import_zip  # reuses your existing import/merge logic

# -----------------------------------------------------------------------------
# Page setup
#
PAGE_KEY = "Recipes"  # identifies this page in the page tips helper
show_tip(PAGE_KEY)

st.title("📜 Recipes")

# --- Recipes Toolbar: Drag-and-drop YAML import --------------------------------

def _slug(name: str) -> str:
    s = "".join(c if (c.isalnum() or c in ("-", "_")) else "-" for c in (name or "").strip())
    while "--" in s:
        s = s.replace("--", "-")
    return (s.strip("-_") or "recipe").lower()

def _guess_recipe_name(text: str, fallback: str) -> str:
    try:
        doc = yaml.safe_load(text) or {}
        if isinstance(doc, dict):
            n = str(doc.get("name", "")).strip()
            if n:
                return n
    except Exception:
        pass
    return fallback  # fallback to filename stem

def _build_zip_from_yamls(files: List["UploadedFile"]) -> bytes:
    """
    Build an in-memory zip compatible with core.io.port.import_zip:
      - manifest.json (JSON)
      - recipes.json  (JSON: [{name, file}])
      - recipes/<slug>.yaml (the uploaded content)
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        index: List[Dict[str, str]] = []
        seen_names = set()

        for f in files:
            raw = f.read().decode("utf-8", "replace")
            base_name = Path(f.name).stem
            name = _guess_recipe_name(raw, fallback=base_name)

            # de-dupe names within the same batch
            candidate = name
            i = 2
            while candidate.lower() in seen_names:
                candidate = f"{name} ({i})"
                i += 1
            name = candidate
            seen_names.add(name.lower())

            fn = f"recipes/{_slug(name)}.yaml"
            z.writestr(fn, raw)
            index.append({"name": name, "file": fn})

        manifest = {
            "package": "sma-avops-recipes-only",
            "version": "1.0.0",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "counts": {"recipes": len(index)},
            "includes": ["recipes"],
        }
        # Write REAL JSON (import_zip expects JSON)
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        z.writestr("recipes.json", json.dumps(index, ensure_ascii=False, indent=2))
    return buf.getvalue()

st.divider()
st.subheader("📥 Add Recipes (Drag & Drop YAML)")

with st.expander("Import YAML files into the recipe library", expanded=True):
    uploads = st.file_uploader(
        "Drop one or more .yaml/.yml files here",
        type=["yaml", "yml"],
        accept_multiple_files=True,
        help="Each file should be a valid IPAV recipe. If the YAML has a 'name:' field, that will be used."
    )

    merge = st.radio(
        "On duplicate names in the database…",
        options=["skip", "overwrite", "rename"],
        index=0,
        help="• skip: keep existing records\n• overwrite: replace existing YAML/content\n• rename: keep both by appending (2), (3)…",
        horizontal=True,
    )
    colA, colB = st.columns(2)
    with colA:
        dry = st.checkbox("Dry run (preview only)", value=True)
    with colB:
        st.caption("Tip: Start with a **Dry run** to see what would change before applying.")

    def _run_import(dry_run: bool):
        if not uploads:
            st.warning("Add at least one YAML file to continue.")
            return
        try:
            zip_bytes = _build_zip_from_yamls(uploads)
            result = import_zip(zip_bytes, recipes_dir="recipes", merge=merge, dry_run=dry_run)
            st.json(result, expanded=False)
            if not dry_run:
                st.success("Recipes imported successfully.")
                st.toast("Recipes imported; refreshing…")
                st.rerun()
        except Exception as e:
            st.error(f"Import failed: {type(e).__name__}: {e}")

    c1, c2 = st.columns([1, 1])
    if c1.button("Preview import (Dry run)"):
        _run_import(dry_run=True)
    if c2.button("Import now"):
        _run_import(dry_run=dry)

st.caption("Files are saved to the local **recipes/** folder and registered in the database so they appear here and in Workflows.")
# --- End Recipes Toolbar ------------------------------------------------------


# Directory where recipe YAML files are stored.  It is created on demand.
RECIPES_DIR = os.path.join(os.getcwd(), "recipes")
os.makedirs(RECIPES_DIR, exist_ok=True)


def _make_store() -> RunStore:
    """Create a RunStore instance for accessing run metrics."""
    db_path = Path(__file__).resolve().parents[1] / "avops.db"
    try:
        return RunStore(db_path=db_path)
    except TypeError:
        # Fall back to default in-memory store when db_path is not accepted
        return RunStore()


def _git_commit_hint(path: str) -> str:
    """Return a short git commit summary for the given file or an "untracked" hint."""
    try:
        rel = os.path.relpath(path, os.getcwd())
        out = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%h %cs", "--", rel],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or "uncommitted"
    except Exception:
        return "untracked"


store = _make_store()

st.info(
    "Guardrails help avoid runaway actions. Include timeouts, rollback actions, and success metrics in every recipe."
)
st.caption(
    "Tip: Commit recipe changes to Git for peer review before enabling them in production."
)

st.subheader("Create Recipe")
new_name = st.text_input("Recipe name")
new_file = st.text_input("Filename (e.g. my_recipe.yaml)")
default_yaml = (
    "name: Example\n"
    "description: Demo\n"
    "guardrails:\n"
    "  timeout_minutes: 30\n"
    "  rollback_actions:\n"
    "    - Notify on-call engineer\n"
    "success_metrics:\n"
    "  - metric: resolution_time_seconds\n"
    "    target: 1800\n"
    "intake: []\n"
    "plan: []\n"
    "act: []\n"
    "verify: []\n"
)
new_text = st.text_area("YAML", height=260, value=default_yaml)
if st.button("Save Recipe") and new_name and new_file:
    ok, msg = validate_yaml_text(new_text)
    if not ok:
        st.error(msg)
    else:
        try:
            # Ensure filename ends with .yaml
            fname = new_file.strip()
            if not fname.lower().endswith((".yaml", ".yml")):
                fname += ".yaml"
            # Save the YAML file to disk
            save_recipe_yaml(fname, new_text)
            # Register in the database if not already present
            with get_session() as db:  # type: ignore
                if not db.query(Recipe).filter(Recipe.name == new_name).first():
                    db.add(Recipe(name=new_name, yaml_path=fname))
                    db.commit()
            st.success("Recipe saved with guardrails template.")
            # Refresh the page so the new recipe shows up immediately
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save recipe: {type(e).__name__}: {e}")

st.divider()
st.subheader("Existing Recipes")

recipe_search = st.text_input("Search recipes", placeholder="Filter by name...")

with get_session() as db:  # type: ignore
    recipes = db.query(Recipe).order_by(Recipe.name).all()
    if recipe_search:
        term = recipe_search.lower()
        recipes = [r for r in recipes if term in r.name.lower()]

    if not recipes:
        st.info("No recipes match your filter yet.")
    for r in recipes:
        with st.expander(r.name):
            # Determine the on-disk path of the YAML file
            path = os.path.join(RECIPES_DIR, r.yaml_path)
            try:
                text = open(path, "r", encoding="utf-8").read()
                parsed = load_recipe_dict(r.yaml_path)
            except Exception as e:
                st.error(f"Unable to read {r.yaml_path}: {e}")
                continue

            # Fetch run metrics for this recipe
            metrics = store.recipe_metrics(r.id)
            success = metrics.get("success_rate", 0.0)
            dot = "🟢" if success >= 80 else ("🟡" if success >= 50 else "🔴")
            updated_at = (
                r.updated_at.strftime("%Y-%m-%d %H:%M")
                if isinstance(r.updated_at, datetime)
                else str(r.updated_at)
            )
            git_hint = _git_commit_hint(path)
            st.caption(
                f"{dot} Success: {success:.1f}% over {metrics.get('runs', 0)} run(s) · "
                f"Avg: {metrics.get('avg_ms', 0):.0f} ms · Last status: {metrics.get('last_status')}"
            )
            st.caption(f"Version: updated {updated_at} · Git: {git_hint}")

            # Warn/inform about missing guardrails or success metrics
            if "guardrails" not in parsed:
                st.warning("Add a guardrails block with timeout and rollback actions.")
            if "success_metrics" not in parsed:
                st.info("Consider defining success_metrics to track performance.")

            # Editable YAML textarea
            edited = st.text_area(
                f"Edit {r.yaml_path}", value=text, height=260, key=f"e-{r.id}"
            )
            if st.button("Update", key=f"u-{r.id}"):
                ok, msg = validate_yaml_text(edited)
                if ok:
                    try:
                        save_recipe_yaml(r.yaml_path, edited)
                        st.success("Recipe updated.")
                    except Exception as e:
                        st.error(f"Failed to update: {type(e).__name__}: {e}")
                else:
                    st.error(msg)
            if st.button("Delete", key=f"d-{r.id}"):
                try:
                    os.remove(path)
                except Exception:
                    pass
                db.delete(r)
                db.commit()
                st.rerun()

st.divider()
with st.expander("Recipe version control best practices", expanded=False):
    # Use single quotes to avoid conflicts with inner double quotes
    st.markdown(
        '- Commit YAML changes with descriptive messages (e.g., `git commit -am "recipe: add timeout"`)\n'
        '- Use pull requests for review of guardrails and rollback plans\n'
        '- Tag releases that correspond to production recipe baselines'
    )
