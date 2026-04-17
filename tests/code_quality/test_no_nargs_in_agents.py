#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Ensure active checks and special agents do not use argparse nargs for multi-value arguments.

Using ``nargs`` (``"*"``, ``"+"``, or an integer > 1) to consume multiple values
after a single flag enables argument injection: a user-controlled value like
``--malicious`` is silently swallowed by argparse as a positional token.

The safe alternative is ``action="append"`` (one ``--flag`` per value) on the
agent side and ``repeated_flag()`` on the server-side-calls side.

Allowed exceptions:
* ``nargs=1`` combined with ``action="append"`` — exactly one value per flag.
"""

import ast
from pathlib import Path

import pytest

from tests.testlib.common.repo import repo_path

# Directories that contain agent argparse code
_SCAN_DIRS = [
    "cmk/plugins/*/active_check",
    "cmk/plugins/*/special_agent",
    "cmk/plugins/*/special_agents",
]


def _is_positional_arg(node: ast.Call) -> bool:
    """Return True if this is a positional (not flag) argument.

    Positional args don't start with ``-`` and are safe when preceded by
    ``"--"`` on the command line.
    """
    if not node.args:
        return False
    first_arg = node.args[0]
    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
        return not first_arg.value.startswith("-")
    return False


def _is_safe_nargs(node: ast.Call) -> bool:
    """Return True if the nargs usage is safe.

    Safe patterns:
    * nargs=1 with action="append" — single value appended to a list
    * positional arguments — safe when server emits ``"--"`` before them
    """
    if _is_positional_arg(node):
        return True

    nargs_value = None
    action_value = None

    for kw in node.keywords:
        if kw.arg == "nargs":
            if isinstance(kw.value, ast.Constant):
                nargs_value = kw.value.value
            elif isinstance(kw.value, ast.UnaryOp):
                # e.g. nargs=-1 (unlikely but handle gracefully)
                nargs_value = "unknown"
        if kw.arg == "action":
            if isinstance(kw.value, ast.Constant):
                action_value = kw.value.value

    if nargs_value == 1 and action_value == "append":
        return True
    return False


def _find_nargs_violations(file_path: Path) -> list[tuple[int, str]]:
    """Find unsafe nargs= usages in add_argument() calls."""
    source = file_path.read_text()
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Match *.add_argument(...) calls
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "add_argument"):
            continue

        # Check if nargs= keyword is present
        has_nargs = any(kw.arg == "nargs" for kw in node.keywords)
        if not has_nargs:
            continue

        if _is_safe_nargs(node):
            continue

        # Extract the argument name from the first positional arg
        arg_name = "?"
        if node.args and isinstance(node.args[0], ast.Constant):
            arg_name = str(node.args[0].value)

        violations.append((node.lineno, arg_name))

    return violations


# Known violations that have not yet been migrated.
# Do NOT add new entries — fix the code instead.
# Each entry is (relative_path, arg_name).
_KNOWN_VIOLATIONS: set[tuple[str, str]] = {
    ("cmk/plugins/form_submit/active_check/check_form_submit.py", "--levels"),
    ("cmk/plugins/traceroute/active_check/check_traceroute.py", "--routers_missing_warn"),
    ("cmk/plugins/traceroute/active_check/check_traceroute.py", "--routers_missing_crit"),
    ("cmk/plugins/traceroute/active_check/check_traceroute.py", "--routers_found_warn"),
    ("cmk/plugins/traceroute/active_check/check_traceroute.py", "--routers_found_crit"),
    ("cmk/plugins/azure_deprecated/special_agent/agent_azure.py", "--require-tag-value"),
    ("cmk/plugins/azure_deprecated/special_agent/agent_azure.py", "--explicit-config"),
    ("cmk/plugins/azure_deprecated/special_agent/agent_azure.py", "--services"),
    ("cmk/plugins/azure_v2/special_agent/agent_azure_v2.py", "--subscriptions-require-tag-value"),
    ("cmk/plugins/azure_v2/special_agent/agent_azure_v2.py", "--require-tag-value"),
    ("cmk/plugins/jira/special_agent/agent_jira.py", "--project-workflows-workflows"),
    ("cmk/plugins/smb/special_agent/agent_smb_share.py", "--patterns"),
    ("cmk/plugins/checkmk/special_agents/agent_bi.py", "--secrets"),
    ("cmk/plugins/checkmk/special_agents/agent_bi.py", "--configs"),
    ("cmk/plugins/gcp/special_agents/agent_gcp.py", "--services"),
}


def _collect_agent_files() -> list[Path]:
    """Collect all Python files in agent directories."""
    root = repo_path()
    files = []
    for pattern in _SCAN_DIRS:
        files.extend(sorted(root.glob(f"{pattern}/*.py")))
    return files


def test_no_unsafe_nargs_in_agents() -> None:
    """Verify no active check or special agent uses unsafe nargs patterns."""
    new_violations: list[str] = []

    for file_path in _collect_agent_files():
        rel = str(file_path.relative_to(repo_path()))
        violations = _find_nargs_violations(file_path)
        for lineno, arg_name in violations:
            if (rel, arg_name) in _KNOWN_VIOLATIONS:
                continue
            new_violations.append(f"  {rel}:{lineno} — {arg_name} uses unsafe nargs")

    if new_violations:
        msg = (
            f"Found {len(new_violations)} NEW unsafe nargs usage(s) in agent argparse code.\n"
            "Use action='append' instead of nargs='*'/'+'/N (N>1).\n"
            "See repeated_flag() in cmk.server_side_calls.v1 for the server-side pattern.\n\n"
            + "\n".join(new_violations)
        )
        pytest.fail(msg)
