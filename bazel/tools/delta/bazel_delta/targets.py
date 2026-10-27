# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The Bazel targets that hold the changed files."""

import json
import re
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired, TypedDict

from bazel_delta.errors import DeltaError

# Runs `bazel query` on an expression with an --output format and returns its stdout.
type Query = Callable[[str, str], str]


_NO_TARGET = re.compile(r"^ERROR: Skipping '.*': no such target '")


def query_errors(stderr: str) -> str:
    """The errors of a `bazel query --keep_going` that exited with 3, other than
    the skipped files that are no target, such as a package that fails to load."""
    return "\n".join(
        line
        for line in stderr.splitlines()
        if line.startswith("ERROR: ") and not _NO_TARGET.match(line)
    )


def query_in(workspace: Path, *options: str) -> Query:
    """Runs `bazel query` in the workspace, with the options for every query."""

    def query(expression: str, output: str) -> str:
        # A query file, as the expression lists every changed file. With
        # --keep_going, exit code 3 means it left out the files that are no target,
        # or the packages that fail to load.
        with tempfile.NamedTemporaryFile("w", suffix=".query") as query_file:
            query_file.write(expression)
            query_file.flush()
            result = subprocess.run(
                [
                    "bazel",
                    "query",
                    "--keep_going",
                    *options,
                    f"--output={output}",
                    f"--query_file={query_file.name}",
                ],
                check=False,
                cwd=workspace,
                capture_output=True,
                text=True,
            )
        if result.returncode not in (0, 3):
            raise DeltaError(f"bazel query failed:\n{result.stderr}")
        if result.returncode == 3 and (errors := query_errors(result.stderr)):
            raise DeltaError(f"bazel query failed:\n{errors}")
        return result.stdout

    return query


@dataclass(frozen=True)
class OwningRule:
    label: str
    kind: str
    tags: frozenset[str]


@dataclass(frozen=True)
class OwningTargets:
    targets: list[str]
    """The targets that list any of the files in their srcs or hdrs, sorted."""
    rules: dict[str, list[OwningRule]]
    """The files those targets list, each with the kinds and tags of the targets listing it."""


def _label_path(label: str) -> str:
    package, name = label.removeprefix("//").split(":", 1)
    return f"{package}/{name}" if package else name


# The parts of a rule in `bazel query --output=streamed_jsonproto` that are read here
class _Attribute(TypedDict):
    name: str
    stringListValue: NotRequired[list[str]]


class _Rule(TypedDict):
    name: str
    ruleClass: str
    attribute: NotRequired[list[_Attribute]]


def _string_lists(rule: _Rule, *names: str) -> list[str]:
    return [
        value
        for attribute in rule.get("attribute", [])
        if attribute["name"] in names
        for value in attribute.get("stringListValue", [])
    ]


def _listed_files(rule: _Rule) -> list[str]:
    """The srcs and hdrs of the rule. clang-tidy reports findings in the hdrs of
    the target it lints."""
    return _string_lists(rule, "srcs", "hdrs")


def file_labels(query: Query, files: Sequence[str]) -> set[str]:
    """The labels of the files that are targets, i.e. that a package declares."""
    if not files:
        return set()
    # Without escapes for non-ASCII characters, which bazel query does not decode
    file_set = " ".join(json.dumps(file, ensure_ascii=False) for file in files)
    return set(query(f"set({file_set})", "label").splitlines())


def _rules(streamed_jsonproto: str) -> list[_Rule]:
    """The rules of a `bazel query --output=streamed_jsonproto`."""
    return [
        rule
        for line in streamed_jsonproto.splitlines()
        if (rule := json.loads(line).get("rule")) is not None
    ]


def owning_targets(query: Query, files: Sequence[str]) -> OwningTargets:
    """The targets in the files' packages that list them in their srcs or hdrs,
    also through a filegroup in srcs, as rules_lint lints the files of those
    too. Files in no package are left out."""
    if not (labels := file_labels(query, files)):
        return OwningTargets([], {})
    owners: dict[str, OwningRule] = {}
    owner_names: dict[str, set[str]] = {}

    def own(rule: _Rule, owned: set[str]) -> None:
        owners[rule["name"]] = OwningRule(
            rule["name"], rule["ruleClass"], frozenset(_string_lists(rule, "tags"))
        )
        for label in owned:
            owner_names.setdefault(label, set()).add(rule["name"])

    label_set = " ".join(json.dumps(label, ensure_ascii=False) for label in sorted(labels))
    filegroups: dict[str, set[str]] = {}
    for rule in _rules(query(f"same_pkg_direct_rdeps(set({label_set}))", "streamed_jsonproto")):
        if owned := labels.intersection(_listed_files(rule)):
            own(rule, owned)
            if rule["ruleClass"] == "filegroup":
                filegroups[rule["name"]] = owned
    if filegroups:
        filegroup_set = " ".join(
            json.dumps(label, ensure_ascii=False) for label in sorted(filegroups)
        )
        for rule in _rules(
            query(f"same_pkg_direct_rdeps(set({filegroup_set}))", "streamed_jsonproto")
        ):
            for filegroup in filegroups.keys() & set(_string_lists(rule, "srcs")):
                own(rule, filegroups[filegroup])
    return OwningTargets(
        sorted(owners),
        {
            _label_path(label): [owners[name] for name in sorted(names)]
            for label, names in owner_names.items()
        },
    )
