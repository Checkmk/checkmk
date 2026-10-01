---
name: cmk-up
description: Writes executable cmk-up playbooks (YAML that builds Checkmk sites, hosts, services, rules, BI on local OMD) that reproduce a scenario - from a Jira ticket (SUP-/CMK-/...), a scenario described in prose, or a Checkmk crash report (tarball, crash dir, crash.info, crash.checkmk.com id). Use when asked to "reproduce", "write a playbook", "cmk-up", "repro for SUP-…", "playbook from crash".
---

# cmk-up playbooks

cmk-up (package `cmk-werk-zeug`) reads a YAML playbook, installs versions,
creates sites, fills them and reverts everything at the end unless `--keep`.
A playbook is attached to a ticket; a colleague runs `./X.yaml` and gets the
same setup.

Schema: [reference.md](reference.md). Patterns: [examples.md](examples.md).
Read both before writing a playbook.

`cmk-up` below means `uvx --from cmk-werk-zeug@latest cmk-up` (spell it out, no shell variable: zsh does not word-split).

## Rules for every playbook

- First lines, then `chmod +x`:
  ```
  #!/usr/bin/env -S uvx --from "cmk-werk-zeug@latest" cmk-up
  #
  # hint: to run the development version, change the shebang to
  #  #!/usr/bin/env -S uvx --from git+ssh://review.lan.tribe29.com:29418/cmk-werk-zeug@main cmk-up
  #
  ```
- Header comment: `<KEY> - <the problem in one line>`, how to run it
  (`./<KEY>.yaml --keep`, `--list-phases` when phased), per phase what should
  happen and where to look (GUI path, or `cmk -D <host>`, `cmk -vvI <host>`,
  `lq` query), then `Assumed (not in the ticket):` with every guess.
- Minimal: only what the reproduction needs. One host per case/answer, named
  after what it shows.
- Version as the ticket says: `versions: {"2.4": {spec: 2.4.0p35}}`, edition if
  it matters (`pro` default, `cee` below 2.5). Site name implies the branch:
  `v240`, `v250`, `v300`. Version keys are always quoted.
- Before/after (a rule changed, a host moved, a state flipped) → `phases:`,
  restating the same objects via YAML anchors (`&hosts` / `*hosts`, `<<:`),
  with `defaults: {on_conflict: overwrite}`. BI → `actions: [bi_state]`.
- Services: faked `services:` unless real check plugins matter. Agent output
  from the ticket → `agent_dump: |` inline; large or binary → side file
  `./<KEY>.<host>.agent_output` next to the playbook. Walks the same way.
- Rules: ruleset names must be real. When unsure, grep this checkout
  (`cmk/gui/plugins/wato`, `cmk/plugins/*/rulesets`, `name=` of the
  `CheckParameters`/`SpecialAgent` etc., REST name is `checkgroup_parameters:<name>`,
  `special_agents:<name>`, `active_checks:<name>`). Tuples → `value_raw`.
- Output: `<KEY>/<KEY>.yaml` in the current directory, side files in the same
  folder. Crash without ticket: `crash-<id8>/crash-<id8>.yaml`.

## A: from a Jira ticket or a description

1. Read the ticket with the `jira:jira-read-ticket` skill: description,
   comments, linked tickets, attachments (agent outputs, walks, crash
   reports, diagnostics dumps, screenshots). A crash report attached → also
   run B on it and merge.
2. Extract: version/edition/core, topology (remotes, clusters, parents),
   hosts and their data, rules and their values, users/roles/contact groups,
   BI, global settings, the steps to reproduce and the expected vs. observed
   behaviour. Steps → phases.
3. Write the playbook following the rules above.
4. Validate (below). Report the path, the run command, what to look at, and
   the assumptions.

## B: from a crash report

1. Source: a local tarball (`Checkmk_Crash_*.tar.gz`), a crash directory
   (`var/check_mk/crashes/<type>/<uuid>/`) or a `crash.info`. A
   crash.checkmk.com id or URL → fetch it with the `crash-report:crash-report`
   skill first.
2. Generate the base:
   `cmk-up --enroll crash-<id8>/crash-<id8>.yaml --from-crash <source>`
   It writes the site `crash_<id8>`, the core, side files
   (`<stem>.<host>.agent_output`, `<stem>.<host>.section.txt`), and a header
   with tier, exception, traceback, versions and a commented tail (check
   parameters, locals, form variables).
3. Refine by tier (it is in the header):
   - 1 (agent data present): mostly done. Check the crashing section really is
     in the dump.
   - 2 (section rebuilt from the string table): check the rebuilt
     `<<<section>>>` against the plugin's parse function in this checkout.
   - 3 (only the parsed section): reconstruct the raw agent section from
     `.section.txt` and the plugin's parse function, put it in the dump.
   - any check crash: replace `checkgroup_parameters:TODO` in the commented
     `rules:` with the plugin's real ruleset (`check_ruleset_name` of the
     `CheckPlugin`), uncomment it.
   - 4 (GUI/REST): add what the page needed (rule, host, folder, user rights)
     from the locals/form vars; the header says how to trigger it (URL).
   - 5: nothing reproducible; say so. Only a ticket can add more.

   Keep the generated header; add `Assumed:` lines for what was added.
   Replace the generated shebang (`>=0.4.5`) with the standard first lines.
   The crash's version may be old: look the plugin up at that version
   (`git show <tag>:<path>`, `git log --all -- '*/<plugin>.py'`), not only in
   master, where it may have moved or been rewritten.

4. Validate.

## Validate (always)

```
cmk-up <file> --list-phases                    # loads the playbook, needs no omd
cmk-up <file> --dry-run --no-tui --no-pause    # real probes, every write printed, nothing changed, no sudo
```

Exit code 1 = playbook error: fix and repeat. 2 = site/omd problem on this
machine, fine for a dry run on a machine without that version (say so).
Never run a playbook for real unless asked: it installs versions and needs sudo.
