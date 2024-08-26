#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import glob
import logging
import os
import re
import shlex
import subprocess
import textwrap

# pylint: disable=redefined-outer-name
import time
from collections.abc import Callable
from pathlib import Path
from pprint import pformat
from typing import Any

import pexpect  # type: ignore[import-untyped]
import pytest

from tests.testlib.repo import branch_from_env, current_branch_name, repo_path

from cmk.ccc.version import Edition

LOGGER = logging.getLogger(__name__)


class UtilCalledProcessError(subprocess.CalledProcessError):
    def __str__(self) -> str:
        return (
            super().__str__()
            if self.stderr is None
            else f"{super().__str__()[:-1]} ({self.stderr!r})."
        )


@dataclasses.dataclass
class PExpectDialog:
    """An expected dialog for spawn_expect_message.

    Attributes:
    expect    The expected dialog message.
    send      The string/keys sent to the CLI.
    count     The expected number of occurrences (default: 1).
    optional  Specifies if the dialog message is optional.
    """

    expect: str
    send: str
    count: int = 1
    optional: bool = False


def is_containerized() -> bool:
    return (
        os.path.exists("/.dockerenv")
        or os.path.exists("/run/.containerenv")
        or os.environ.get("CMK_CONTAINERIZED") == "TRUE"
    )


def get_cmk_download_credentials() -> tuple[str, str]:
    credentials_file_path = Path("~").expanduser() / ".cmk-credentials"
    try:
        with open(credentials_file_path) as credentials_file:
            username, password = credentials_file.read().strip().split(":", maxsplit=1)
            return username, password
    except OSError:
        raise RuntimeError(
            f"Missing file: {credentials_file_path} (Create with content: USER:PASSWORD)"
        )


def get_standard_linux_agent_output() -> str:
    with (repo_path() / "tests/integration/cmk/base/test-files/linux-agent-output").open(
        encoding="utf-8"
    ) as f:
        return f.read()


def site_id() -> str:
    _site_id = os.environ.get("OMD_SITE")
    if _site_id is not None:
        return _site_id

    branch_name = branch_from_env(env_var="BRANCH", fallback=current_branch_name)

    # Split by / and get last element, remove unwanted chars
    branch_part = re.sub("[^a-zA-Z0-9_]", "", branch_name.split("/")[-1])
    _site_id = "int_%s" % branch_part

    os.putenv("OMD_SITE", _site_id)
    return _site_id


def package_hash_path(version: str, edition: Edition) -> Path:
    return Path(f"/tmp/cmk_package_hash_{version}_{edition.long}")


def version_spec_from_env(fallback: str | None = None) -> str:
    if version := os.environ.get("VERSION"):
        return version
    if fallback:
        return fallback
    raise RuntimeError("VERSION environment variable, e.g. 2016.12.22, is missing")


def parse_raw_edition(raw_edition: str) -> Edition:
    try:
        return Edition[raw_edition.upper()]
    except KeyError:
        for edition in Edition:
            if edition.long == raw_edition:
                return edition
    raise ValueError(f"Unknown edition: {raw_edition}")


def edition_from_env(fallback: Edition | None = None) -> Edition:
    if raw_editon := os.environ.get("EDITION"):
        return parse_raw_edition(raw_editon)
    if fallback:
        return fallback
    raise RuntimeError("EDITION environment variable, e.g. cre or enterprise, is missing")


def spawn_expect_process(
    args: list[str],
    dialogs: list[PExpectDialog],
    logfile_path: str | Path = "/tmp/sep.out",
    auto_wrap_length: int = 49,
    break_long_words: bool = False,
    timeout: int = 30,
) -> int:
    """Spawn an interactive CLI process via pexpect and process supplied expected dialogs
    "dialogs" must be a list of objects with the following format:
    {"expect": str, "send": str, "count": int, "optional": bool}

    By default, 'timeout' has a value of 30 seconds.

    Return codes:
    0: success
    1: unexpected EOF
    2: unexpected timeout
    3: any other exception
    """
    LOGGER.info("Executing: %s", subprocess.list2cmdline(args))
    with open(logfile_path, "w") as logfile:
        p = pexpect.spawn(" ".join(args), encoding="utf-8", logfile=logfile)
        try:
            for dialog in dialogs:
                counter = 0
                while True:
                    counter += 1
                    if auto_wrap_length > 0:
                        dialog.expect = r".*".join(
                            textwrap.wrap(
                                dialog.expect,
                                width=auto_wrap_length,
                                break_long_words=break_long_words,
                            )
                        )
                    LOGGER.info("Expecting: '%s'", dialog.expect)
                    rc = p.expect(
                        [
                            dialog.expect,  # rc=0
                            pexpect.EOF,  # rc=1
                            pexpect.TIMEOUT,  # rc=2
                        ],
                        timeout=timeout,
                    )
                    if rc == 0:
                        # msg found; sending input
                        LOGGER.info(
                            "%s; sending: %s",
                            (
                                "Optional message found"
                                if dialog.optional
                                else "Required message found"
                            ),
                            repr(dialog.send),
                        )
                        p.send(dialog.send)
                    elif dialog.optional:
                        LOGGER.info("Optional message not found; ignoring!")
                        break
                    else:
                        LOGGER.error(
                            "Required message not found. "
                            "The following has been found instead:\n"
                            "%s",
                            p.before,
                        )
                        break
                    if counter >= dialog.count >= 1:
                        # max count reached
                        break
            if p.isalive():
                rc = p.expect(pexpect.EOF, timeout=timeout)
            else:
                rc = p.status
        except Exception as e:
            LOGGER.exception(e)
            LOGGER.debug(p)
            rc = 3

    assert isinstance(rc, int)
    return rc


def run(
    args: list[str],
    check: bool = True,
    sudo: bool = False,
    substitute_user: str | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """Run a process and return a CompletedProcess object."""
    if sudo:
        args = ["sudo"] + args
    if substitute_user:
        args = ["su", "-l", substitute_user, "-c"] + args
    LOGGER.info("Executing: %s", subprocess.list2cmdline(args))
    try:
        proc = subprocess.run(
            args,
            encoding="utf-8",
            stdin=None if kwargs.get("input") else kwargs.get("stdin", subprocess.DEVNULL),
            capture_output=True,
            close_fds=True,
            check=check,
            **kwargs,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Subprocess terminated non-successfully. Stdout:\n{e.stdout}\nStderr:\n{e.stderr}"
        ) from e
    return proc


def execute(  # type: ignore[no-untyped-def]
    cmd: list[str],
    *args,
    preserve_env: list[str] | None = None,
    sudo: bool = False,
    substitute_user: str | None = None,
    **kwargs,
) -> subprocess.Popen:
    """Run a process as root or a different user and return a Popen object."""
    sudo_cmd = ["sudo"] if sudo else []
    su_cmd = ["su", "-l", substitute_user] if substitute_user else []
    if preserve_env:
        # Skip the test cases calling this for some distros
        if os.environ.get("DISTRO") == "centos-8":
            pytest.skip("preserve env not possible in this environment")
        if sudo:
            sudo_cmd += [f"--preserve-env={','.join(preserve_env)}"]
        if substitute_user:
            su_cmd += ["--whitelist-environment", ",".join(preserve_env)]

    kwargs.setdefault("encoding", "utf-8")
    cmd = sudo_cmd + (su_cmd + ["-c", shlex.quote(shlex.join(cmd))] if substitute_user else cmd)
    cmd_txt = " ".join(cmd)
    LOGGER.info("Executing: %s", cmd_txt)
    kwargs["shell"] = kwargs.get("shell", True)
    return subprocess.Popen(cmd_txt if kwargs.get("shell") else cmd, *args, **kwargs)


def check_output(
    cmd: list[str],
    input: str | None = None,  # pylint: disable=redefined-builtin
    sudo: bool = True,
    substitute_user: str | None = None,
) -> str:
    """Mimics subprocess.check_output while running a process as root or a different user.

    Returns the stdout of the process.
    """
    p = execute(
        cmd,
        sudo=sudo,
        substitute_user=substitute_user,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE if input else None,
    )
    stdout, stderr = p.communicate(input)
    if p.returncode != 0:
        raise UtilCalledProcessError(p.returncode, p.args, stdout, stderr)
    assert isinstance(stdout, str)
    return stdout


def write_file(
    path: str | Path,
    content: bytes | str,
    sudo: bool = True,
    substitute_user: str | None = None,
) -> None:
    """Write a file as root or another user."""
    with execute(
        ["tee", Path(path).as_posix()],
        sudo=sudo,
        substitute_user=substitute_user,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        encoding=(
            None
            if isinstance(
                content,
                bytes,
            )
            else "utf-8"
        ),
    ) as p:
        p.communicate(content)
    if p.returncode != 0:
        raise Exception(
            "Failed to write file %s. Exit-Code: %d"
            % (
                path,
                p.returncode,
            )
        )


def makedirs(path: str | Path, sudo: bool = True, substitute_user: str | None = None) -> bool:
    """Make directory path (including parents) as root or another user."""
    p = execute(["mkdir", "-p", Path(path).as_posix()], sudo=sudo, substitute_user=substitute_user)
    return p.wait() == 0


def restart_httpd() -> None:
    """Restart Apache manually on RHEL-based containers.

    On RHEL-based containers, such as CentOS and AlmaLinux, the system Apache is not running.
    OMD will not start Apache, if it is not running already.

    If a distro uses an `INIT_CMD`, which is not available inside of docker, then the system
    Apache won't be restarted either. For example, sles uses `systemctl restart apache2.service`.
    However, the docker container does not use systemd as in init process. Thus, this fails in the
    test environment, but not a real distribution.

    Before using this in your test, try an Apache reload instead. It is much more likely to work
    accross different distributions. If your test needs a system Apache, then run this command at
    the beginning of the test. This ensures consistency accross distributions.
    """

    # When executed locally and un-dockerized, DISTRO may not be set
    if os.environ.get("DISTRO") in {"centos-8", "almalinux-9"}:
        run(["httpd", "-k", "restart"], sudo=True)


@dataclasses.dataclass
class ServiceInfo:
    state: int
    summary: str


def get_services_with_status(
    host_data: dict[str, ServiceInfo],
    service_status: int,
    skipped_services: list[str] | tuple[str, ...] = (),
) -> set[str]:
    """Return a set of services in the given status which are not in the 'skipped' list."""
    services_by_state: dict[int, dict[str, ServiceInfo]] = {}
    for state in sorted({_.state for _ in host_data.values()}):
        services_by_state[state] = {
            service_name: service_info
            for service_name, service_info in host_data.items()
            if host_data[service_name].state == state
        }
    for state, services in services_by_state.items():
        LOGGER.debug(
            "%s service(s) found in state %s (%s):\n%s",
            len(services),
            state,
            {0: "OK", 1: "WARN", 2: "CRIT", 3: "UNKNOWN"}.get(state, "UNDEFINED"),
            pformat(services),
        )
    services_list = set(_ for _ in services_by_state[service_status] if _ not in skipped_services)
    return services_list


def wait_until(condition: Callable[[], bool], timeout: float = 1, interval: float = 0.1) -> None:
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return  # Success. Stop waiting...
        time.sleep(interval)

    raise TimeoutError("Timeout waiting for %r to finish (Timeout: %d sec)" % (condition, timeout))


def parse_files(pathname: Path, pattern: str, ignore_case: bool = True) -> dict[str, list[str]]:
    """Parse file(s) for a given pattern."""
    pattern_obj = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    LOGGER.info("Parsing logs for '%s' in %s", pattern, pathname)
    match_dict: dict[str, list[str]] = {}
    for file_path in glob.glob(str(pathname), recursive=True):
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                if pattern_obj.search(line):
                    LOGGER.info("Match found in %s: %s", file_path, line.strip())
                    match_dict[file_path] = match_dict.get(file_path, []) + [line]
    return match_dict
