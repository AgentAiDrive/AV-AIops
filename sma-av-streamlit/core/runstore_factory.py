"""
core/runstore_factory.py
----------------------------------

This module exposes a factory function for constructing a run log store.
In a small, self‑contained deployment we simply return an instance of
``RunStore`` backed by the SQLite database located at the repository root.
Future versions could detect configuration options or environment
variables to select between different backends (e.g. SQL vs. Redis vs.
external API).  Centralising the factory logic here decouples the
Dashboard from a specific storage implementation and makes it easier to
introduce alternative stores without touching the UI code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .runs_store import RunStore


def make_runstore(db_path: Optional[Path] = None) -> RunStore:
    """Instantiate and return a ``RunStore``.

    Parameters
    ----------
    db_path : Optional[Path], optional
        An explicit path to the SQLite file.  If not provided, the default
        ``avops.db`` in the repository root will be used.  This argument
        exists primarily for testing or advanced deployments.

    Returns
    -------
    RunStore
        A new run store bound to the specified or default database.
    """
    if db_path is None:
        # Base directory of the repo (sma-av-streamlit)
        base_dir = Path(__file__).resolve().parents[1]
        db_path = base_dir / "avops.db"
    return RunStore(db_path=db_path)