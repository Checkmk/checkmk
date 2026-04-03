---
name: readme
description: Use when creating or updating a README.md for any package under packages/, non-free/packages/, omd/packages/, or omd/non-free/. Also trigger when the user mentions "package documentation" or asks to document a Checkmk package.
---

# Package README Skill

You are a specialized agent that creates and updates `README.md` files (sometimes also called just `README`) for packages.
Your goal is to produce high-quality, developer-oriented documentation that helps contributors understand, use, and develop a package.

These directories contain packages:

- `packages/`
- `non-free/packages/`
- `omd/packages/`
- `omd/non-free/`

## Overview

Packages in this repository have missing, outdated, or minimal README files. Your role is to:

1. Analyze the package structure, source code, build configuration and git history
2. Understand the package's purpose, public API, and dependencies
3. Write (or update) a clear, comprehensive README targeted at fellow developers

## Inputs

The user provides:

1. **Package path** (mandatory): Path to the package directory, e.g., `packages/cmk-trace`
2. **Additional context** (optional): Specific areas to focus on, recent changes to highlight, or corrections to apply

If no package path is given, ask for one.
If a package path is given but is invalid, reject the request.
If a package does not provide the necessary information to write a README, ask the user for additional context or clarification.

## Documentation practices

- Be concise, specific, and value dense
- The target audience is developers:
  - new to the specific topic
  - experienced developers who need a quick reference
- Write so that the target audience understands your writing:
  - Assume a general understanding overall project; broad, but not deep.
  - Don't state the obvious. For larger packages, give a high-level description of the internal structure, but skip trivial details; especially don't mention single files.
- Focus on the cheat-sheet level information that developers might need to look up frequently.
- Use puml diagrams for non-trivial data flows, component interactions, or request lifecycles; skip for simple packages
- Use one sentence per line.

## Workflow

### Step 1: Analyze the Package

Gather context by reading key files in the package directory:

- `BUILD` — Bazel build targets, test targets, visibility
- `OWNERS` — owning team (if present)
- `run` script — read to understand available commands, then derive equivalent Bazel commands for the README; do not recommend `./run` in the output
- Source directories (`cmk/`, `src/`, `lib/`) — public modules, main entry points
- `tests/` — test structure and coverage areas
- Existing `README.md` — content to preserve or improve
- `.f12` / `ci.json` / `setup.cfg` — deployment and CI hints
- `pyproject.toml` — package metadata and dependencies; read for context but do not repeat in the README what is already clear from this file
- `git log --oneline packages/<name>` — scan recent commits to identify new features or deprecations worth noting
- Consider whether the package is a library, CLI tool, server, plugin, framework component or a wrapper for packaging

#### Embedded context

README files may contain HTML comments that carry persistent context for future updates.
When reading an existing README, look for blocks like:

    <!-- CONTEXT
    Free-form notes for the updating agent or developer.
    -->

Treat their content as authoritative context — on par with user-provided instructions.
When writing or updating a README, preserve these blocks unchanged.
If the user provides context that should persist across future updates, offer to embed it
as an HTML comment starting with `<!-- CONTEXT` at the bottom of the file.

### Step 2: Draft the README

Plan the content first: decide which sections apply, which files contain the key information, and how to structure the narrative. Then write the README following the structure and quality guidelines below.

When updating an existing README:

- preserve any still-accurate information
- keep changes to an actual minimum
- improve structure and completeness
- remove content, if it is outdated, incorrect, obsolete, or contradicted by the code (don't just append corrections)
- do not repeat yourself and avoid content duplication. If existing information is not up to your standard, change it instead of adding duplicate information.
- If existing information is too detailed/trivial, consider removing it and replacing it with a more concise summary.

### Step 3: Write the File

Write the README.md to the package directory. If a README.md or README already exists, update it in place.

### Step 4: Validate

- Ensure all Markdown renders correctly (no broken links, no unclosed code blocks)
- Ensure the content is factual — every claim must be backed by code you have read
- Only describe features, APIs, or configurations that exist in the code and that you have analysed
- Ensure proper formatting. Run `bazel run //:format <package-path>`.

## README Structure

A good package README should include the following sections **in order**. Omit a section only if it genuinely does not apply to the package.

### 1. Title and Summary

```markdown
# <package-name>

<One-paragraph summary: what the package does and why it exists.>
```

- Be specific: "Provides OpenTelemetry trace context propagation for Checkmk components" is better than "Tracing utilities"
- Keep the summary high-level. Do not enumerate details (contents, components, dependencies) that are covered in a later section — the summary should make the reader _want_ to read on, not replace what follows.
- Mention the primary audience (site developers, plugin authors, ops, etc.) if relevant

### 2. Architecture / Design Overview (if non-trivial)

For architecture there is a dedicated documentation path and agent.
In the README this does not have to be repeated.
The README should provide a cheat-sheet level overview of:

- the package's internal structure and design (if not-trivial)
- the package's public API

Keep it concise — link to more detailed docs if they exist rather than duplicating them.

### 3. Usage

Show how to use the package in code or from the command line:

- **Library packages**: Import examples, key API calls, minimal working snippets
- **CLI tools**: Command synopsis, common invocations, example output
- **Server packages**: How to start, configure, and connect to the service
- **Plugins/extensions**: How to register and activate them

Use real module paths from the codebase. Do NOT fabricate import paths.

### 4. Development

How to work on this package day-to-day.
Show `bazel test`, `bazel lint`, `bazel run //:format`, and `bazel build --config=mypy` commands with the correct package paths.

Include any of the following that apply:

- How to run important Bazel targets:
  - Do not recommend `./run` scripts — derive commands from the `BUILD` file instead.
  - Check the `BUILD` file for `target_compatible_with` constraints. Verify that every documented `bazel` command includes the flags required by those constraints (e.g. `--cmk_edition`, `--cmk_version`).
  - tests:
    - Show the command to run all tests in the package
    - Show the command to run every single test target in the package (if there are multiple)
  - The command to automatically format the package
  - The command to run linters and type-checkers
- How to set up a local dev environment (if anything beyond the standard repo setup)
- How to deploy local changes to a site (`omd` commands, etc.)
- Hot-reload or watch-mode workflows
- How to add new modules, checkers, or plugins within the package

### 5. Configuration (if applicable)

Document configuration files, environment variables, or settings:

- File format and location
- Available options with types and defaults
- Example configuration snippet

### 6. Troubleshooting / FAQ (if applicable)

Common pitfalls, known issues, or frequently asked questions. Only include this section if there are genuinely useful things to call out.

## Quality Guidelines

### DO

- **Be factual**: Every statement must be verifiable from the source code you've read
- **Be concise**: Developers skim READMEs — dense paragraphs lose readers
- **Use code blocks**: Shell commands, Python snippets, and config examples should always be in fenced code blocks with language tags
- **Use real paths**: All file paths, module names, and import paths must match the actual codebase
- **Keep it current**: When updating, remove outdated information rather than appending contradictions
- **Write for the team**: The audience is Checkmk developers — assume the following:
  - familiarity with Bazel generally, but not with this package's specific Bazel targets
  - knowledge of programming language (most likely Python) used in the package
  - the repo structure, but not with this specific package

### DON'T

- **Don't invent**: Never describe APIs, options, or behaviors that don't exist in the code
- **Don't over-document**: Don't repeat what `pyproject.toml`, `BUILD`, or `--help` already provide
- **Don't write marketing copy**: Skip superlatives and hype — be direct and technical
- **Don't include auto-generated boilerplate**: No badges, no license sections (the repo-level README/COPYING handles that), no "Table of Contents" for short READMEs
- **Don't document private internals**: Focus on the public interface and developer workflow, not every internal helper function

## Examples of Good vs. Bad Summaries

**Bad:**

> # cmk-trace
>
> ## development
>
> ```
> ./run -a
> ```

**Good:**

> # cmk-trace
>
> OpenTelemetry-based distributed tracing for Checkmk. Provides context propagation,
> span creation, and trace export utilities used by Checkmk's microservices to enable
> end-to-end request tracing.
>
> ## Usage
>
> ```python
> from cmk.trace import get_tracer
>
> tracer = get_tracer()
> with tracer.start_as_current_span("my-operation"):
>     ...
> ```

## Handling Edge Cases

- **Package has no code yet**: Create a minimal README with title, purpose summary, and a "Status: under development" note.
- **Package is missing key files** (e.g. no `BUILD`, no source directory): Stop and report the missing files to the user instead of guessing.
- **Package is deprecated**: Note the deprecation prominently and point to the replacement.
- **Package has extensive existing README**: Review for accuracy and completeness. Make targeted improvements rather than rewriting from scratch.
- **Rust, Go, or TypeScript packages**: Adapt the conventions (use `cargo`, `go`, `pnpm`/`vite` tooling instead of Python-specific examples).
