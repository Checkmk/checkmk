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


RUN_IN_DOCKER = (
    'docker run \\\n    -v "/var/run/docker.sock:/var/run/docker.sock" \\\n    "$IMAGE"\n'
)

RUN_TESTS = """\
_wrapped() {
    "$REPO_PATH/scripts/run-in-docker.sh" tests/run_tests.sh $1
}

test-unit() {
    bazel test //tests/unit/...
}

test-unit-docker() {
    "$REPO_PATH/scripts/run-in-docker.sh" tests/run_tests.sh test-unit
}

test-format-docker() { _wrapped test-format; }
"""


def _with_socket_scripts(root: Path) -> None:
    _write(root, "scripts/run-in-docker.sh", RUN_IN_DOCKER)
    _write(root, "tests/run_tests.sh", RUN_TESTS)


def test_running_socket_mounting_script_is_reported(tmp_path: Path) -> None:
    _with_socket_scripts(tmp_path)
    _write(tmp_path, "buildscripts/scripts/job.groovy", 'sh("scripts/run-in-docker.sh make")\n')

    assert find_problems(tmp_path, frozenset()) == [
        "buildscripts/scripts/job.groovy: runs run-in-docker.sh, which mounts the docker socket"
    ]


def test_running_target_calling_socket_mounting_script_is_reported(tmp_path: Path) -> None:
    _with_socket_scripts(tmp_path)
    _write(
        tmp_path, "buildscripts/scripts/job.groovy", 'sh("tests/run_tests.sh test-unit-docker")\n'
    )

    assert find_problems(tmp_path, frozenset()) == [
        "buildscripts/scripts/job.groovy: runs test-unit-docker, which mounts the docker socket"
    ]


def test_running_target_through_helper_function_is_reported(tmp_path: Path) -> None:
    _with_socket_scripts(tmp_path)
    _write(tmp_path, "buildscripts/scripts/job.groovy", 'def target = "test-format-docker";\n')

    assert find_problems(tmp_path, frozenset()) == [
        "buildscripts/scripts/job.groovy: runs test-format-docker, which mounts the docker socket"
    ]


def test_interpolated_target_name_is_reported(tmp_path: Path) -> None:
    _with_socket_scripts(tmp_path)
    _write(tmp_path, "buildscripts/scripts/job.groovy", 'def target = "test-${suite}-docker";\n')

    assert find_problems(tmp_path, frozenset()) == [
        "buildscripts/scripts/job.groovy: runs test-format-docker, which mounts the docker socket",
        "buildscripts/scripts/job.groovy: runs test-unit-docker, which mounts the docker socket",
    ]


def test_target_without_socket_and_unrelated_interpolation_pass(tmp_path: Path) -> None:
    _with_socket_scripts(tmp_path)
    _write(
        tmp_path,
        "buildscripts/scripts/job.groovy",
        'sh("tests/run_tests.sh test-unit")\ndef tag = "${build_date}-${branch_name}";\n',
    )

    assert not find_problems(tmp_path, frozenset())


def test_commented_out_socket_mount_in_shell_script_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "scripts/run-in-docker.sh", "# -v /var/run/docker.sock:/var/run/docker.sock\n")
    _write(tmp_path, "buildscripts/scripts/job.groovy", 'sh("scripts/run-in-docker.sh make")\n')

    assert not find_problems(tmp_path, frozenset())


def test_stage_running_socket_mounting_target_is_reported(tmp_path: Path) -> None:
    _with_socket_scripts(tmp_path)
    _write(
        tmp_path,
        "buildscripts/scripts/stages.yml",
        'STAGES:\n    - NAME: "Unit"\n      COMMAND: "tests/run_tests.sh test-unit-docker"\n',
    )

    assert find_problems(tmp_path, frozenset()) == [
        "buildscripts/scripts/stages.yml: runs test-unit-docker, which mounts the docker socket"
    ]
