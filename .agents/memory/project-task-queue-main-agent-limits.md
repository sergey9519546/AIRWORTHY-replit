---
name: Project-task queue main-agent limits
description: What the main agent can and cannot do to a project task that is queued for a task-agent but blocked/unstarted.
---

When a project task is `PENDING` with `blockedBy: CONCURRENCY_LIMIT` (queued for
an isolated task-agent Repl that hasn't spun up yet), the main agent cannot
force-claim it: `markTaskInProgress` errors (`TaskMan ReportProgress failed`)
because that call is only for resuming an already-`IMPLEMENTED` task, and
`markTaskComplete` errors with `"No active task to mark complete"` because no
task is bound to the main agent's session.

**Why:** the task-tracking state machine ties `IN_PROGRESS`/completion calls to
whichever agent instance was actually assigned the task; a PENDING task queued
for a not-yet-started task-agent was never assigned to the main agent, so there
is no session-bound "active task" to transition.

**How to apply:** when the user asks the main agent to just implement pending/
blocked task-queue items directly (bypassing the task-agent queue), do the code
work in the main Repl and verify it (restart, screenshot, logs) as usual, but
don't try to force the task's queue state — leave it for the user to cancel/
reconcile once they see the feature is already live, the same way an already-
superseded task gets cancelled elsewhere in this workflow.
