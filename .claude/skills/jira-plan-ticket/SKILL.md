---
name: jira-plan-ticket
description: Fetches Jira ticket context, creates a branch, and drafts an implementation plan
---

# Jira Ticket Workflow

This skill automates the "start working on a Jira ticket" workflow.

> **Note:** This skill is limited to the CMK project to avoid interfering with sensitive customer data. Only `CMK-` prefixed tickets are supported.

## Arguments

The user provides a Jira ticket key as the argument (e.g., `/jira-plan-ticket CMK-12345`).

## Workflow

### 1. Fetch ticket context

Run the helper script to retrieve the full ticket context:

```bash
.venv/bin/python3 .claude/skills/jira-plan-ticket/fetch_jira_context.py <TICKET_KEY>
```

This fetches the ticket's description, comments, linked tickets, and metadata from Jira.

If the script fails, report the error to the user and stop.

### 2. Check for uncommitted changes

Before switching branches, check whether the working tree is dirty:

```bash
git status --porcelain
```

If there are uncommitted changes, **warn the user** and ask whether to:

- **Stash** them (`git stash push -m "auto-stash before <TICKET_KEY>"`)
- **Commit** them first
- **Abort** the workflow

Do not proceed to branch creation until the working tree is clean or the user has chosen an option.

### 3. Create a working branch

Derive a short branch name from the ticket key and summary: `<TICKET_KEY>-<very_short_summary>` (e.g., `CMK-12345-fix-login-crash`). Use lowercase, hyphens, and at most 3-4 words for the summary part.

**Determine the base branch** from the ticket's "Affects Versions" field:

- If the script output contains an "Affects Versions" section, use it to determine the base branch:
  - Version `2.4.0bX` / `2.4.0pX` / `2.4.0` → base branch `2.4.0`
  - Version `2.5.0bX` / `2.5.0pX` / `2.5.0` → base branch `2.5.0`
  - If multiple versions are listed, use the **oldest** (lowest) version branch.
- If no affects version is set, ask the user which base branch to use. Present curated choices via `AskUserQuestion`:
  - `master` (development branch)
  - `2.5.0` (latest stable)
  - `2.4.0` (previous stable)

Create and switch to the branch based on the determined base branch:

```bash
git fetch origin <BASE_BRANCH> && git checkout -b <TICKET_KEY>-<very_short_summary> origin/<BASE_BRANCH>
```

If the branch already exists, switch to it instead:

```bash
git checkout <TICKET_KEY>-<very_short_summary>
```

### 4. Review attachments

Skip this step entirely if the script output contains no attachment sections.

If there are attachments, launch **at most 2 Task agents** (subagent_type: `general-purpose`) in parallel:

- **Images agent** (only if there are image attachments): One agent receives ALL image file paths. It should read each image with the Read tool and describe what it shows (UI state, error messages, annotations, etc.). Return a concise summary per image.
- **Other files agent** (only if there are non-image attachments): One agent receives ALL other file paths. For text-based files (logs, configs, CSVs), read and summarize key findings. For archives (tar, zip, gz), extract via Bash and summarize structure. Return a concise summary per file.

Incorporate the returned summaries into your understanding of the ticket.

### 5. Clarify uncertainties

Before planning, review the gathered context (ticket description, comments, attachments, linked tickets) and identify any uncertainties or gaps:

- **Ambiguous requirements**: If the ticket description is vague, contradictory, or open to multiple interpretations, ask the user to clarify the intended behavior.
- **Missing context**: If the ticket lacks sufficient detail to determine the scope, affected components, or expected outcome, ask the user for the missing information.
- **Conflicting information**: If comments or linked tickets contradict the description, surface the conflict and ask which version is correct.
- **Implementation choices**: If there are multiple reasonable approaches and the ticket doesn't indicate a preference, present the options to the user.

Use the `AskUserQuestion` tool to present your questions. Only proceed to planning once the uncertainties are resolved or the user explicitly tells you to proceed with your best judgment.

Skip this step if the ticket context is clear and complete.

### 6. Draft an implementation plan

Enter plan mode and create an implementation plan based on the Jira ticket context. The plan should:

- Summarize the ticket's requirements from the description and comments
- Identify relevant files and components in the codebase
- Outline the implementation steps
- Note any open questions or blockers from linked tickets
- **If the ticket is a bug**: Explore options for easily reproducing the bug using unit tests. This helps verify the fix and prevents regressions.
- **If the ticket is a feature**: Explore adding sufficient unit test coverage for the new functionality.

Present the plan for user approval before proceeding with implementation.
