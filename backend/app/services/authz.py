"""Authorization helpers for task status / gates (lean Phase 3)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import Actor
from app.exceptions import ForbiddenError
from app.models import Task


def assert_actor_may_mark_done(db: Session, task: Task, actor: Actor) -> None:
    """Reject agent callers marking a gated / blocked step as done (403).

    Human/operator may still mark done (subject to prior-step gate elsewhere).
    Agent is denied when:
    - task.approval_gate is True (human approval required), or
    - task has an unmet depends_on (prior step not done).
    """
    if not actor.is_agent:
        return

    if task.depends_on_task_id is not None:
        prior = db.get(Task, task.depends_on_task_id)
        if prior is None or prior.status != "done":
            prior_status = getattr(prior, "status", None) if prior else "missing"
            raise ForbiddenError(
                f"Agent cannot mark task #{task.id} done: unmet dependency "
                f"(depends_on=#{task.depends_on_task_id}, status={prior_status!r}); "
                "human must clear the prior step first"
            )

    if task.approval_gate:
        raise ForbiddenError(
            f"Agent cannot mark approval-gated task #{task.id} done; "
            "human/operator required"
        )
