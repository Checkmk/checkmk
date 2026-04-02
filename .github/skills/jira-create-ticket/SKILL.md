---
name: jira-create-ticket
description: Create a Jira ticket in CMK with component, team, and epic matched from compass and roadmap data
---

# Create a Jira Ticket

Creates a Jira ticket in the CMK project. Guesses the component and developer team by querying the compass JSON endpoint. Searches for a matching roadmap epic to link to.

## Required environment variables

- `JIRA_API_TOKEN` - Jira API token

## Arguments

The user provides a rough description of what the ticket should be about. This can be free-form text.

## Workflow

### 1. Determine issue type

Analyze the user's input and automatically infer the issue type:

- **Bug**: The input describes broken behavior, a defect, a crash, an error, a regression, or something that "doesn't work" / "stopped working". Look for words like: bug, broken, crash, error, fail, regression, wrong, incorrect, not working, fix.
- **Task**: Everything else — new features, enhancements, upgrades, refactoring, maintenance, tooling, cleanup, migrations.

Never create Stories. If ambiguous, default to **Task**.

### 2. Gather ticket details

From the user's rough description, draft the following fields:

- **Summary**: A concise one-line title (max ~80 chars)
- **Description**: Use the appropriate template below based on issue type
- **Issue type**: As determined in step 1
- **Project**: Default `CMK`
- **Priority**: Optional — only set if user explicitly requests it (omit to use Jira default)
- **Parent**: Optional parent issue key (e.g. `CMK-12345`)

### Description templates

Choose the template based on the inferred issue type. Rules that apply to ALL templates:

- **Acceptance Criteria are MANDATORY** — always draft concrete acceptance criteria.
- **Optional sections** should be included when you can enrich the ticket with useful info (e.g. links the user provided, technical context). Omit sections entirely rather than writing "n/a" or placeholder text.

#### Template for Bug tickets

```
{panel:title=Acceptance Criteria|titleBGColor=#15d1a0}
 * <criterion 1>
 * <criterion 2>
 * <criterion 3>{panel}
h3. Steps to reproduce
 # <step 1>
 # <step 2>

h3. Observed behavior

<describe the behavior that is observed>
h3. Expected behavior

<describe the behavior that is expected>
h3. Root cause

Currently the root cause is unknown.
h3. Additional resource / Screenshots

<links, screenshots, or other resources if helpful>
```

#### Template for Task tickets

```
{panel:title=What needs to be done?|titleBGColor=#77bce4}
*As a* <role>
*I want to* <goal>
*so that* <benefit>
{panel}
{panel:title=Acceptance Criteria|titleBGColor=#15d1a0}
 * <criterion 1>
 * <criterion 2>
 * <criterion 3>{panel}
h3. In-Depth Description

<detailed description of what needs to be done>
h3. Design Information

<screenshots, design mockups, Figma links>
h3. Technical Information

<links to relevant technical information>
h3. Additional information

<misc info, e.g. who could be consulted>
```

Rules specific to Task:

- **User story** (As a / I want to / so that) is appreciated but optional. Include it when the context makes it natural; omit the panel entirely if it would be forced.

### 3. Pick component and team from compass data

Fetch the full component list from the compass endpoint:

```bash
.venv/bin/python .github/skills/jira-create-ticket/create_ticket.py \
  --summary "<drafted summary>" \
  --guess
```

This returns a JSON array of all ~220 components, each with `name`, `teams`, and optionally `description`. Review the list and pick the component that best matches the ticket's topic. Use the first team listed for that component as the developer team. If no component is a clear match, leave both empty and let the user decide.

### 4. Search for a matching roadmap epic

Fetch all open roadmap epics:

```bash
.venv/bin/python .github/skills/jira-create-ticket/create_ticket.py \
  --find-epics \
  --summary "<drafted summary>"
```

This returns a JSON array of all open epics in the roadmap hierarchy (rooted at CMK-24875: Roadmap Ticket -> Business Goal -> Initiative -> Epic), each with `key`, `summary`, `status`, `components`, `team`. Review the list and pick the epic that best matches the ticket's topic.

**Roadmap vs Component work:** Checkmk uses a roadmap hierarchy: Roadmap Ticket -> Business Goal -> Initiative -> Epic -> Task/Bug. Tickets that belong to ongoing roadmap work should be linked to their epic. However, many tickets are standalone "component work" (bug fixes, small improvements, tech debt) that do NOT belong to any roadmap epic. **No link is a perfectly valid choice.**

Evaluate the results:

- If an epic clearly matches the ticket's topic, suggest linking to it.
- If no epic is a good match, or the ticket is clearly standalone component work (small bug fix, minor maintenance, tech debt), recommend no epic link.
- When in doubt, lean towards no link — it's easier to add a link later than to remove a wrong one.

### 5. MANDATORY: Verify with the user before creating

Present a summary of ALL fields to the user using AskUserQuestion and ask for confirmation. The user MUST approve the ticket content before creation. Show:

- Summary
- Issue type (note if auto-inferred)
- Description (abbreviated if long)
- Project
- Component (note if auto-guessed)
- Developer Team (note if auto-guessed)
- Epic link (show the epic key + summary if suggested, or "None — standalone component work" if no link)
- Priority (if set)
- Parent (if set)

If the user wants changes, incorporate them and verify again.

### 6. Create the ticket

Once confirmed, run:

```bash
.venv/bin/python .github/skills/jira-create-ticket/create_ticket.py \
  --summary "<summary>" \
  --description "<description>" \
  --issue-type "<type>" \
  --project "<project>" \
  [--component "<component>"] \
  [--developer-team "<team>"] \
  [--link-epic "<epic key>"] \
  [--priority "<priority>"] \
  [--parent "<parent>"]
```

The script outputs a line like `Created: CMK-32430 — https://jira.lan.tribe29.com/browse/CMK-32430`. Parse the issue key and URL from it and present a clickable markdown link to the user:

```
Created [CMK-32430](https://jira.lan.tribe29.com/browse/CMK-32430)
```

If an epic was linked, also mention it.

## Notes

- The `--dry-run` flag prints the payload without creating the ticket.
- The script is self-contained (only depends on `jira` library). Configure it via `JIRA_API_TOKEN` environment variable.
- `--link-epic` sets the Epic Link field on the new ticket, making it a child of the specified epic.
- `--find-epics` searches open epics filtered by component and ranked by keyword match against the summary.
