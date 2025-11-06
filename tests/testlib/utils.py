#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import enum
import glob
import logging
import os
import re
import shlex
import subprocess
import textwrap

# pylint: disable=redefined-outer-name
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from pprint import pformat
from typing import Any, assert_never, overload

import pexpect  # type: ignore[import-untyped]
import pytest

from tests.testlib.repo import branch_from_env, current_branch_name, repo_path

from cmk.utils.version import Edition

logger = logging.getLogger(__name__)


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


def virtualenv_path() -> Path:
    venv = subprocess.check_output(
        [repo_path() / "scripts/run-pipenv", "--bare", "--venv"], encoding="utf-8"
    )
    return Path(venv.rstrip("\n"))


def get_cmk_download_credentials_file() -> str:
    return "%s/.cmk-credentials" % os.environ["HOME"]


def get_cmk_download_credentials() -> tuple[str, str]:
    credentials_file_path = get_cmk_download_credentials_file()
    try:
        with open(credentials_file_path) as credentials_file:
            username, password = credentials_file.read().strip().split(":", maxsplit=1)
            return username, password
    except OSError:
        raise Exception("Missing %s file (Create with content: USER:PASSWORD)" % credentials_file)


def get_standard_linux_agent_output() -> str:
    with (repo_path() / "tests/integration/cmk/base/test-files/linux-agent-output").open(
        encoding="utf-8"
    ) as f:
        return f.read()


def site_id() -> str:
    site_id = os.environ.get("OMD_SITE")
    if site_id is not None:
        return site_id

    branch_name = branch_from_env(env_var="BRANCH", fallback=current_branch_name)

    # Split by / and get last element, remove unwanted chars
    branch_part = re.sub("[^a-zA-Z0-9_]", "", branch_name.split("/")[-1])
    site_id = "int_%s" % branch_part

    os.putenv("OMD_SITE", site_id)
    return site_id


def package_hash_path(version: str, edition: Edition) -> Path:
    return Path(f"/tmp/cmk_package_hash_{version}_{edition.long}")


def version_spec_from_env(fallback: str | None = None) -> str:
    if version := os.environ.get("VERSION"):
        return version
    if fallback:
        return fallback
    raise RuntimeError("VERSION environment variable, e.g. 2016.12.22, is missing")


def _parse_raw_edition(raw_edition: str) -> Edition:
    try:
        return Edition[raw_edition.upper()]
    except KeyError:
        for edition in Edition:
            if edition.long == raw_edition:
                return edition
    raise ValueError(f"Unknown edition: {raw_edition}")


def edition_from_env(fallback: Edition | None = None) -> Edition:
    if raw_editon := os.environ.get("EDITION"):
        return _parse_raw_edition(raw_editon)
    if fallback:
        return fallback
    raise RuntimeError("EDITION environment variable, e.g. cre or enterprise, is missing")


def spawn_expect_process(
    args: list[str],
    dialogs: list[PExpectDialog],
    logfile_path: str = "/tmp/sep.out",
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
    logger.info("Executing: %s", subprocess.list2cmdline(args))
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
                    logger.info("Expecting: '%s'", dialog.expect)
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
                        logger.info(
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
                        logger.info("Optional message not found; ignoring!")
                        break
                    else:
                        logger.error(
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
            logger.exception(e)
            logger.debug(p)
            rc = 3

    assert isinstance(rc, int)
    return rc


def run(
    args: list[str],
    capture_output: bool = True,
    check: bool = True,
    encoding: str | None = "utf-8",
    input: str | bytes | None = None,  # pylint: disable=redefined-builtin
    preserve_env: list[str] | None = None,
    sudo: bool = False,
    substitute_user: str | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """Run a process and return a `subprocess.CompletedProcess` object."""
    args_ = _extend_command(args, substitute_user, sudo, preserve_env, kwargs)

    kwargs["capture_output"] = capture_output
    kwargs["encoding"] = encoding
    kwargs["input"] = input
    return subprocess.run(args_, check=check, **kwargs)


def execute(
    cmd: list[str],
    encoding: str | None = "utf-8",
    preserve_env: list[str] | None = None,
    substitute_user: str | None = None,
    sudo: bool = False,
    **kwargs: Any,
) -> subprocess.Popen:
    """Run a process as root or a different user and return a `subprocess.Popen`.

    The method wraps `subprocess.Popen` and initializes some `kwargs` by default.
    NOTE: use it as a contextmanager; `with execute(...) as process: ...`
    """
    cmd_ = _extend_command(cmd, substitute_user, sudo, preserve_env, kwargs)

    kwargs["encoding"] = encoding
    return subprocess.Popen(cmd_, **kwargs)


def _extend_command(
    cmd: list[str],
    substitute_user: str | None,
    sudo: bool,
    preserve_env: list[str] | None,
    kwargs: dict,  # subprocess.<method> kwargs
) -> list[str]:
    """Return extended command by adding `sudo` or `su` usage."""

    methods = "`testlib.utils.check_output / execute / run`"
    # TODO: remove usage of kwargs & shell from methods `check_output / execute / run`.
    if kwargs.get("shell", False):
        raise NotImplementedError(
            f"`shell=True` is not supported by {methods}.\n"
            "Use desired `subprocess.<method>` directly for such cases."
        )
    if preserve_env:
        # Skip the test cases calling this for some distros
        if os.environ.get("DISTRO") == "centos-8":
            pytest.skip("preserve env not possible in this environment")
        if not (sudo or substitute_user):
            raise TypeError(
                f"'preserve_env' requires usage of 'sudo' or 'substitute_user' in {methods}!"
            )
    sudo_cmd = _cmd_as_sudo(preserve_env) if sudo else []
    user_cmd = (
        (_cmd_as_user(substitute_user, preserve_env) + [shlex.join(cmd)])
        if substitute_user
        else cmd
    )
    cmd_ = sudo_cmd + user_cmd
    logging.info("Executing command: %s", shlex.join(cmd_))
    return cmd_


def _cmd_as_sudo(preserve_env: list[str] | None = None) -> list[str]:
    base_cmd = ["sudo"]
    if preserve_env:
        base_cmd += [f"--preserve-env={','.join(preserve_env)}"]
    return base_cmd


def _cmd_as_user(username: str, preserve_env: list[str] | None = None) -> list[str]:
    """Extend commandline by adopting rol oe desired user."""
    base_cmd = ["su", "-l", username]
    if preserve_env:
        base_cmd += ["--whitelist-environment", ",".join(preserve_env)]
    base_cmd += ["-c"]
    return base_cmd


class DaemonTerminationMode(enum.Enum):
    PROCESS = enum.auto()
    GROUP = enum.auto()


@contextmanager
def daemon(
    cmd: list[str],
    name_for_logging: str,
    termination_mode: DaemonTerminationMode,
    sudo: bool,
) -> Iterator[subprocess.Popen]:
    with execute(
        cmd,
        sudo=sudo,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    ) as daemon_proc:
        try:
            yield daemon_proc
        finally:
            daemon_rc = daemon_proc.returncode
            if daemon_rc is None:
                logger.info("Terminating %s daemon...", name_for_logging)
                _terminate_daemon(daemon_proc, termination_mode, sudo)
            stdout, stderr = daemon_proc.communicate(timeout=5)
            logger.info("Stdout from %s daemon:\n%s", name_for_logging, stdout)
            logger.info("Stderr from %s daemon:\n%s", name_for_logging, stderr)
            assert (
                daemon_rc is None
            ), f"{name_for_logging} daemon unexpectedly exited (RC={daemon_rc})!"


def _terminate_daemon(
    daemon_proc: subprocess.Popen,
    termination_mode: DaemonTerminationMode,
    sudo: bool,
) -> None:
    match termination_mode:
        case DaemonTerminationMode.PROCESS:
            run(
                ["kill", "--", str(daemon_proc.pid)],
                sudo=sudo,
            )
        case DaemonTerminationMode.GROUP:
            run(
                ["kill", "--", f"-{os.getpgid(daemon_proc.pid)}"],
                sudo=sudo,
            )
        case _:
            assert_never(termination_mode)


@overload
def check_output(
    cmd: list[str],
    encoding: str = "utf-8",
    input: str | bytes | None = None,  # pylint: disable=redefined-builtin
    preserve_env: list[str] | None = None,
    sudo: bool = False,
    substitute_user: str | None = None,
    **kwargs: Any,
) -> str: ...


@overload
def check_output(
    cmd: list[str],
    encoding: None,
    input: str | bytes | None = None,  # pylint: disable=redefined-builtin
    preserve_env: list[str] | None = None,
    sudo: bool = False,
    substitute_user: str | None = None,
    **kwargs: Any,
) -> bytes: ...


def check_output(
    cmd: list[str],
    encoding: str | None = "utf-8",
    input: str | bytes | None = None,  # pylint: disable=redefined-builtin
    preserve_env: list[str] | None = None,
    sudo: bool = False,
    substitute_user: str | None = None,
    **kwargs: Any,
) -> str | bytes:
    """Mimics subprocess.check_output while running a process as root or a different user.

    Returns the stdout of the process.
    """
    cmd_ = _extend_command(cmd, substitute_user, sudo, preserve_env, kwargs)

    kwargs["encoding"] = encoding
    kwargs["input"] = input
    return str(subprocess.check_output(cmd_, **kwargs))


def write_file(
    path: str | Path,
    content: bytes | str,
    sudo: bool = True,
    substitute_user: str | None = None,
) -> None:
    """Write a file as root or another user."""
    try:
        _ = run(
            ["tee", Path(path).as_posix()],
            capture_output=False,
            input=content,
            stdout=subprocess.DEVNULL,
            encoding=None if isinstance(content, bytes) else "utf-8",
            sudo=sudo,
            substitute_user=substitute_user,
        )
    except subprocess.CalledProcessError as excp:
        excp.add_note(f"Failed to write file '{path}'!")
        raise excp


def makedirs(path: str, sudo: bool = True, substitute_user: str | None = None) -> bool:
    """Make directory path (including parents) as root or another user."""
    p = execute(["mkdir", "-p", path], sudo=sudo, substitute_user=substitute_user)
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
    if os.environ.get("DISTRO") in {"centos-8", "almalinux-9", "almalinux-10"}:
        run(["sudo", "httpd", "-k", "restart"])


@dataclasses.dataclass
class ServiceInfo:
    state: int
    summary: str


def get_services_with_status(
    host_data: dict[str, ServiceInfo],
    service_status: int,
    skipped_services: list[str] | tuple[str, ...] = (),
) -> set:
    """Return a set of services in the given status which are not in the 'skipped' list."""
    services_list = set()
    for service in host_data:
        if host_data[service].state == service_status and service not in skipped_services:
            services_list.add(service)

    logger.debug(
        "%s service(s) found in state %s:\n%s",
        len(services_list),
        service_status,
        pformat(services_list),
    )
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
    logger.info("Parsing logs for '%s' in %s", pattern, pathname)
    match_dict: dict[str, list[str]] = {}
    for file_path in glob.glob(str(pathname), recursive=True):
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                if pattern_obj.search(line):
                    logger.info("Match found in %s: %s", file_path, line.strip())
                    match_dict[file_path] = match_dict.get(file_path, []) + [line]
    return match_dict
