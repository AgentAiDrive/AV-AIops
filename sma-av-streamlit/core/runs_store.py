# core/runs_store.py
from __future__ import annotations
import contextlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON, DateTime, Float, ForeignKey, Integer, String, create_engine, select
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

UTC = timezone.utc


class Base(DeclarativeBase):
    pass


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recipe_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trigger: Mapped[str] = mapped_column(String(32), default="manual")
    status: Mapped[str] = mapped_column(String(16), default="running")  # running/success/failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    meta: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    steps: Mapped[List["StepEvent"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    artifacts: Mapped[List["Artifact"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class StepEvent(Base):
    __tablename__ = "step_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    phase: Mapped[str] = mapped_column(String(32))  # intake/plan/act/verify/other
    level: Mapped[str] = mapped_column(String(16), default="info")  # info/warn/error
    status: Mapped[str] = mapped_column(String(16), default="ok")
    message: Mapped[str] = mapped_column(String(2000), default="")
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    run: Mapped[WorkflowRun] = relationship(back_populates="steps")


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(32))  # kb/recipe/webinar/message/file/incident/etc.
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    run: Mapped[WorkflowRun] = relationship(back_populates="artifacts")


class RunStore:
    """
    Persistent run log for workflows/agents.
      - Use `with store.workflow_run(...):` to wrap an execution
      - Call `rec.step(...)` and `rec.artifact(...)` inside the context
    """
    def __init__(self, db_path: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parents[1]  # <repo>/sma-av-streamlit
        self.db_path = Path(db_path) if db_path else base_dir / "avops.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.db_path}", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(self.engine, expire_on_commit=False)

    @contextlib.contextmanager
    def workflow_run(
        self,
        *,
        workflow_id: str,
        name: str,
        agent_id: Optional[int],
        recipe_id: Optional[int],
        trigger: str = "manual",
        meta: Optional[Dict[str, Any]] = None,
    ):
        start = time.perf_counter()
        with self.Session() as s:
            run = WorkflowRun(
                workflow_id=workflow_id,
                name=name,
                agent_id=agent_id,
                recipe_id=recipe_id,
                trigger=trigger,
                status="running",
                meta=meta or {},
            )
            s.add(run); s.commit(); s.refresh(run)
            run_id = run.id

        status, error = "success", None
        try:
            yield Recorder(self, run_id)
        except Exception as e:
            status, error = "failed", f"{type(e).__name__}: {e}"
            raise
        finally:
            dur_ms = (time.perf_counter() - start) * 1000.0
            with self.Session() as s:
                r = s.get(WorkflowRun, run_id)
                if r:
                    r.status = status
                    r.error = error
                    r.finished_at = datetime.now(UTC)
                    r.duration_ms = dur_ms
                    s.commit()

    # ---- Logging helpers ----------------------------------------------------
    def log_step(
        self,
        run_id: int,
        *,
        phase: str,
        message: str,
        level: str = "info",
        status: str = "ok",
        payload: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> int:
        with self.Session() as s:
            ev = StepEvent(
                run_id=run_id, phase=phase, level=level, status=status,
                message=message, payload=payload, result=result
            )
            s.add(ev); s.commit(); s.refresh(ev)
            return ev.id

    def log_artifact(
        self,
        run_id: int,
        *,
        kind: str,
        title: str,
        external_id: Optional[str] = None,
        url: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> int:
        with self.Session() as s:
            a = Artifact(
                run_id=run_id, kind=kind, title=title,
                external_id=external_id, url=url, data=data or {}
            )
            s.add(a); s.commit(); s.refresh(a)
            return a.id

    # ---- Queries ------------------------------------------------------------
    def latest_runs(
        self,
        *,
        limit: int = 50,
        status: Optional[List[str]] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        with self.Session() as s:
            q = select(WorkflowRun)
            if status:
                q = q.filter(WorkflowRun.status.in_(status))
            if since:
                q = q.filter(WorkflowRun.started_at >= since)
            rows = s.execute(q.order_by(WorkflowRun.id.desc()).limit(limit)).scalars().all()
            return [self._run_to_dict(r) for r in rows]

    def run_details(self, run_id: int) -> Dict[str, Any]:
        with self.Session() as s:
            r = s.get(WorkflowRun, run_id)
            if not r:
                return {}
            steps = s.execute(
                select(StepEvent).where(StepEvent.run_id == run_id).order_by(StepEvent.id)
            ).scalars().all()
            arts = s.execute(
                select(Artifact).where(Artifact.run_id == run_id).order_by(Artifact.id)
            ).scalars().all()
            d = self._run_to_dict(r)
            d["steps"] = [self._step_to_dict(x) for x in steps]
            d["artifacts"] = [self._artifact_to_dict(x) for x in arts]
            return d

    def stats(self, *, since: Optional[datetime] = None) -> Dict[str, Any]:
        with self.Session() as s:
            q = select(WorkflowRun)
            if since:
                q = q.filter(WorkflowRun.started_at >= since)
            rows = s.execute(q).scalars().all()
            n = len(rows)
            succ = sum(1 for r in rows if r.status == "success")
            durs = sorted([r.duration_ms or 0.0 for r in rows if r.duration_ms])
            p95 = _quantile(durs, 0.95) if durs else 0.0
            last_err = next((r.error for r in sorted(rows, key=lambda x: x.id, reverse=True) if r.error), "")
            return {"runs": n, "success_rate": (succ / n) * 100.0 if n else 0.0, "p95_ms": p95, "last_error": last_err or ""}

    def recipe_metrics(self, recipe_id: int, *, limit: int = 200) -> Dict[str, Any]:
        """Return recent success metrics for a specific recipe."""
        with self.Session() as s:
            rows = (
                s.execute(
                    select(WorkflowRun)
                    .where(WorkflowRun.recipe_id == recipe_id)
                    .order_by(WorkflowRun.id.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            total = len(rows)
            success = sum(1 for r in rows if r.status == "success")
            last_status = rows[0].status if rows else "unknown"
            avg_ms = sum(r.duration_ms or 0.0 for r in rows) / total if total else 0.0
            return {
                "runs": total,
                "success_rate": (success / total) * 100.0 if total else 0.0,
                "last_status": last_status,
                "avg_ms": avg_ms,
            }

    # ---- Dict helpers -------------------------------------------------------
    @staticmethod
    def _run_to_dict(r: WorkflowRun) -> Dict[str, Any]:
        return {
            "id": r.id, "workflow_id": r.workflow_id, "name": r.name,
            "agent_id": r.agent_id, "recipe_id": r.recipe_id, "trigger": r.trigger,
            "status": r.status, "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "duration_ms": r.duration_ms, "error": r.error, "meta": r.meta,
        }

    @staticmethod
    def _step_to_dict(sv: StepEvent) -> Dict[str, Any]:
        return {
            "id": sv.id, "run_id": sv.run_id, "ts": sv.ts.isoformat(),
            "phase": sv.phase, "level": sv.level, "status": sv.status,
            "message": sv.message, "payload": sv.payload, "result": sv.result,
        }

    @staticmethod
    def _artifact_to_dict(a: Artifact) -> Dict[str, Any]:
        return {
            "id": a.id, "run_id": a.run_id, "kind": a.kind, "external_id": a.external_id,
            "url": a.url, "title": a.title, "data": a.data,
        }


class Recorder:
    """Use inside the workflow_run() context manager."""
    def __init__(self, store: RunStore, run_id: int):
        self.store = store
        self.run_id = run_id

    def step(
        self,
        phase: str,
        message: str,
        *,
        level: str = "info",
        status: str = "ok",
        payload: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
    ):
        self.store.log_step(
            self.run_id, phase=phase, message=message, level=level,
            status=status, payload=payload, result=result
        )

    def artifact(
        self,
        kind: str,
        title: str,
        *,
        external_id: Optional[str] = None,
        url: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        self.store.log_artifact(
            self.run_id, kind=kind, title=title,
            external_id=external_id, url=url, data=data
        )


def _quantile(xs: List[float], q: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    if q <= 0:
        return xs[0]
    if q >= 1:
        return xs[-1]
    idx = (len(xs) - 1) * q
    lo, hi = int(idx), min(int(idx) + 1, len(xs) - 1)
    frac = idx - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac
