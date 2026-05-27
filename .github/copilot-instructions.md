# Copilot instructions for check_mk

Project conventions are documented in `CLAUDE.md` at the repository root —
apply those when suggesting changes.

## AI tooling lives elsewhere

Reusable AI workflows for this project (code review, werk authoring,
Gerrit/Jenkins/Jira/crash-report helpers, backports, etc.) are maintained
as Claude Code plugins in a separate, internal repository:

    https://github.com/Checkmk/checkmk-claude-marketplace

Copilot cannot execute these plugins, but their `SKILL.md` files describe
the workflows in plain markdown and are useful as reference when answering
"how do I …" questions.

## Do not recreate them here

`.github/{agents,skills}/` and `.claude/{agents,skills}/` are intentionally
empty in this repo. Do not add files there — the canonical sources are in
the marketplace repository above.
