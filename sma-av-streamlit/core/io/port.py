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
