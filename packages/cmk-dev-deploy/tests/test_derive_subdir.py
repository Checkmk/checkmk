# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for _derive_subdirs_from_paths in manifest/update.py."""

from __future__ import annotations

from cmk.dev_deploy.manifest.update import _derive_subdirs_from_paths


def test_top_level_file() -> None:
    assert _derive_subdirs_from_paths(["cmk_update_agent.py"]) == {"cmk_update_agent.py"}


def test_depth2_namespace_file() -> None:
    assert _derive_subdirs_from_paths(["cmk/check_helper_protocol.py"]) == {
        "cmk/check_helper_protocol.py"
    }


def test_regular_package_with_init() -> None:
    """cmk/ccc/ has __init__.py -> depth 2 grouping."""
    paths = [
        "cmk/ccc/__init__.py",
        "cmk/ccc/foo.py",
        "cmk/ccc/bar.py",
    ]
    assert _derive_subdirs_from_paths(paths) == {"cmk/ccc/"}


def test_namespace_package_without_init() -> None:
    """cmk/plugins/ has no __init__.py -> depth 3 grouping."""
    paths = [
        "cmk/plugins/aws/__init__.py",
        "cmk/plugins/aws/foo.py",
        "cmk/plugins/aws/agent_based/bar.py",
        "cmk/plugins/logwatch/__init__.py",
        "cmk/plugins/logwatch/agent_based/check.py",
    ]
    assert _derive_subdirs_from_paths(paths) == {
        "cmk/plugins/aws/",
        "cmk/plugins/logwatch/",
    }


def test_bakery_namespace() -> None:
    """cmk/bakery/ has no __init__.py -> depth 3 grouping for base/, shared/, v1/."""
    paths = [
        "cmk/bakery/base/__init__.py",
        "cmk/bakery/base/config.py",
        "cmk/bakery/base/core_bakelets/agent_updater.py",
        "cmk/bakery/shared/__init__.py",
        "cmk/bakery/shared/config_processing.py",
        "cmk/bakery/v1/__init__.py",
        "cmk/bakery/v1/_constants.py",
    ]
    assert _derive_subdirs_from_paths(paths) == {
        "cmk/bakery/base/",
        "cmk/bakery/shared/",
        "cmk/bakery/v1/",
    }


def test_mixed_regular_and_namespace() -> None:
    """cmk/ccc/ (has init) stays depth 2, cmk/plugins/ (no init) goes depth 3."""
    paths = [
        "cmk/ccc/__init__.py",
        "cmk/ccc/foo.py",
        "cmk/plugins/aws/__init__.py",
        "cmk/plugins/aws/foo.py",
    ]
    assert _derive_subdirs_from_paths(paths) == {
        "cmk/ccc/",
        "cmk/plugins/aws/",
    }


def test_shallow_file_in_namespace() -> None:
    """A hypothetical cmk/plugins/utils.py stays at depth 2."""
    paths = ["cmk/plugins/utils.py"]
    assert _derive_subdirs_from_paths(paths) == {"cmk/plugins/"}


def test_notification_plugins_flat_files() -> None:
    """cmk/notification_plugins/ with only flat .py files (no subdirs, no init)."""
    paths = [
        "cmk/notification_plugins/jira_issues.py",
        "cmk/notification_plugins/servicenow.py",
    ]
    # No __init__.py at cmk/notification_plugins/ -> namespace, but files are
    # only depth 3 (3 parts), so they stay at depth 2
    assert _derive_subdirs_from_paths(paths) == {"cmk/notification_plugins/"}
