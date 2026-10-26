#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from check_no_privileged_containers import find_problems, HELPER


def _write(root: Path, path: str, content: str) -> None:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text(content)


def test_unprivileged_scripts_pass(tmp_path: Path) -> None:
    _write(tmp_path, "buildscripts/scripts/job.groovy", "inside_container(privileged: false) {}\n")

    assert not find_problems(tmp_path, frozenset())


def test_privileged_script_in_subdirectory_is_reported(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "buildscripts/scripts/utils/x.groovy",
        "inside_container(\n    privileged: true,\n) {}\n",
    )

    assert find_problems(tmp_path, frozenset()) == [
        "buildscripts/scripts/utils/x.groovy: uses a privileged container (privileged: true)"
    ]


def test_allowed_script_is_not_reported(tmp_path: Path) -> None:
    _write(tmp_path, "buildscripts/scripts/job.groovy", "inside_container(privileged: true) {}\n")

    assert not find_problems(tmp_path, frozenset({"buildscripts/scripts/job.groovy"}))


def test_commented_out_privileged_is_ignored(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "buildscripts/scripts/job.groovy",
        "inside_container(\n    // privileged: true,\n) {}\n",
    )

    assert not find_problems(tmp_path, frozenset())


def test_docker_socket_mount_is_reported_even_if_allowed(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "buildscripts/scripts/job.groovy",
        'inside_container(args: ["-v /var/run/docker.sock:/var/run/docker.sock"]) {}\n',
    )

    assert find_problems(tmp_path, frozenset({"buildscripts/scripts/job.groovy"})) == [
        "buildscripts/scripts/job.groovy: mounts the docker socket"
    ]


def test_helper_may_mount_docker_socket_if_unprivileged_by_default(tmp_path: Path) -> None:
    _write(
        tmp_path,
        HELPER,
        'def privileged = args.get("privileged", false).asBoolean();\n'
        '+ (privileged ? ["-v /var/run/docker.sock:/var/run/docker.sock"] : [])\n',
    )

    assert not find_problems(tmp_path, frozenset())


def test_helper_privileged_by_default_is_reported(tmp_path: Path) -> None:
    _write(tmp_path, HELPER, 'def privileged = args.get("privileged", true).asBoolean();\n')

    assert find_problems(tmp_path, frozenset()) == [
        f'{HELPER}: privileged must default to false (args.get("privileged", false))'
    ]
