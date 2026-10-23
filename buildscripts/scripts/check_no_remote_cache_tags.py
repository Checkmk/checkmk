#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Check that every target with a per-build unique output is tagged no-remote-cache.

A rule with stamp = 1 reads volatile-status.txt, whose BUILD_TIMESTAMP changes
with every invocation, so its action key is unique per build. The same holds
for every rule consuming such an output. The remote cache can never serve
these results; uploading them (the packages are several GB) only evicts
entries other builds still need. //bazel/rules:pkg.bzl tags stamped archives,
this finds the consumers that still lack the tag.

Only a literal stamp = 1 is seen: a stamp given as select(), or a rule reading
ctx.version_file without a stamp attribute, is not detected.
"""

# ruff: noqa: T201  # It's OK for scripts to print()

import json
import os
import subprocess
import sys
from argparse import ArgumentParser
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

TAG = "no-remote-cache"

# Rules without actions: their outputs are their inputs, so their consumers
# need the tag, they themselves do not.
PASS_THROUGH = frozenset(
    {
        "alias",
        "filegroup",
        "pkg_filegroup",
        "pkg_files",
        "pkg_mkdirs_impl",
        "pkg_mklink_impl",
    }
)

# Rules that only read providers of their inputs, never the output files.
EXEMPT = frozenset(
    {
        "sbom",  # walks the dependency graph with an aspect
    }
)


@dataclass(frozen=True)
class Rule:
    label: str
    rule_class: str
    stamp: int
    tags: frozenset[str]
    inputs: frozenset[str]


def parse_rules(lines: Iterable[str]) -> list[Rule]:
    """Parse the output of `bazel query --output=streamed_jsonproto`."""
    rules = []
    for line in lines:
        if not (rule := json.loads(line).get("rule")):
            continue
        attributes = {a["name"]: a for a in rule.get("attribute", [])}
        rules.append(
            Rule(
                label=rule["name"],
                rule_class=rule["ruleClass"],
                stamp=attributes.get("stamp", {}).get("intValue", 0),
                tags=frozenset(attributes.get("tags", {}).get("stringListValue", [])),
                inputs=frozenset(rule.get("ruleInput", [])),
            )
        )
    return rules


def find_problems(rules: Iterable[Rule]) -> list[str]:
    rules = list(rules)
    # Why each rule's output is unique per build, for the report.
    reasons = {r.label: "stamp = 1" for r in rules if r.stamp == 1}
    changed = True
    while changed:
        changed = False
        for rule in rules:
            if rule.label in reasons or rule.rule_class in EXEMPT:
                continue
            if tainted := sorted(rule.inputs & reasons.keys()):
                reasons[rule.label] = f"consumes {tainted[0]}"
                changed = True
    return [
        f"{r.label} ({r.rule_class}): {reasons[r.label]}, but is not tagged {TAG}"
        for r in sorted(rules, key=lambda r: r.label)
        if r.label in reasons and r.rule_class not in PASS_THROUGH and TAG not in r.tags
    ]


def _query_rules() -> list[Rule]:
    output = subprocess.run(
        [
            "bazel",
            "query",
            "--ui_event_filters=-info,-progress",
            "--noshow_progress",
            "kind(rule, //...)",
            "--output=streamed_jsonproto",
        ],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout
    return parse_rules(output.splitlines())


def main(argv: Sequence[str]) -> int:
    ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)

    if workspace := os.environ.get("BUILD_WORKSPACE_DIRECTORY"):
        os.chdir(workspace)

    problems = find_problems(_query_rules())
    for problem in problems:
        print(problem)
    if problems:
        print(f'Add tags = ["{TAG}"] to these targets.')
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
