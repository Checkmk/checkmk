#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides various utility functions and classes for managing processes,
handling file operations, and interacting with the system environment.
"""

import dataclasses
import enum
import logging
import os
import re
import shlex
import subprocess
import textwrap
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from pprint import pformat
from stat import filemode
from typing import Any, assert_never, overload

import pexpect
import psutil
import yaml
from bs4 import BeautifulSoup

from cmk import trace
from tests.testlib.common.repo import branch_from_env, current_branch_name, repo_path

logger = logging.getLogger(__name__)
tracer = trace.get_tracer()

DISTROS_MISSING_WHITELIST_ENVIRONMENT_FOR_SU = ["almalinux-8"]


def verbose_called_process_error(excp: subprocess.CalledProcessError) -> str:
    """Return a verbose message containing debug information of a `CalledProcessError` exception."""
    return f"STDOUT:\n{excp.stdout}\nSTDERR:\n{excp.stderr}\n"


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
    jenkins_credentials_file_path = Path("/home") / "jenkins" / ".cmk-credentials"
    etc_credentials_file_path = Path("/etc") / ".cmk-credentials"
    user_credentials_file_path = Path("~").expanduser() / ".cmk-credentials"
    credentials_file_path = (
        jenkins_credentials_file_path
        if jenkins_credentials_file_path.exists()
        else (
            user_credentials_file_path
            if user_credentials_file_path.exists()
            else etc_credentials_file_path
        )
    )
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


def version_spec_from_env(fallback: str | None = None) -> str:
    if version := os.environ.get("VERSION"):
        return version
    if fallback:
        return fallback
    raise RuntimeError("VERSION environment variable, e.g. 2016.12.22, is missing")


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
                            "Required message not found. The following has been found instead:\n%s",
                            p.before,
                        )
                        break
                    if counter >= dialog.count >= 1:
                        # max count reached
                        break
            if p.isalive():
                rc = p.expect(pexpect.EOF, timeout=timeout)
            else:
                rc = p.status  # type: ignore[assignment]
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
    input_: str | bytes | None = None,
    preserve_env: list[str] | None = None,
    sudo: bool = False,
    substitute_user: str | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Run a process and return a `subprocess.CompletedProcess` object."""
    preserve_env, kwargs = _add_trace_context(kwargs, preserve_env, sudo)
    args_ = _extend_command(args, substitute_user, None, sudo, preserve_env, kwargs)

    kwargs["capture_output"] = capture_output
    kwargs["encoding"] = encoding
    kwargs["input"] = input_

    with tracer.span("run", attributes={"cmk.command": repr(args_)}):
        return subprocess.run(args_, check=check, **kwargs)


def execute(
    cmd: list[str],
    encoding: str | None = "utf-8",
    preserve_env: list[str] | None = None,
    substitute_user: str | None = None,
    substitute_shell: str | None = None,
    sudo: bool = False,
    **kwargs: Any,
) -> subprocess.Popen[str]:
    """Run a process as root or a different user and return a `subprocess.Popen`.

    The method wraps `subprocess.Popen` and initializes some `kwargs` by default.
    NOTE: use it as a contextmanager; `with execute(...) as process: ...`
    """
    preserve_env, kwargs = _add_trace_context(kwargs, preserve_env, sudo)
    cmd_ = _extend_command(
        cmd,
        substitute_user,
        substitute_shell,
        sudo,
        preserve_env,
        kwargs,
    )

    kwargs["encoding"] = encoding

    with tracer.span("execute", attributes={"cmk.command": repr(cmd_)}):
        return subprocess.Popen(cmd_, **kwargs)


def get_processes_by_cmdline(cmdline_pattern: str) -> list[psutil.Process]:
    """Return a list of currently running processes matching the given command line pattern.

    NOTE: only processes with a non-empty command line are considered.

    Args:
        cmdline_pattern (str): some substring or regex pattern (via re.search) of the command line.
    Returns:
        list[psutil.Process]:
    """
    processes = []
    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        if not proc.info["cmdline"]:
            continue
        full_cmdline = " ".join(proc.info["cmdline"])
        if cmdline_pattern in full_cmdline or re.search(cmdline_pattern, full_cmdline):
            processes.append(proc)
    return processes


def _add_trace_context(
    kwargs: dict[str, Any], preserve_env: list[str] | None, sudo: bool
) -> tuple[list[str] | None, dict[str, Any]]:
    current_distro = os.environ.get("DISTRO")
    if current_distro in DISTROS_MISSING_WHITELIST_ENVIRONMENT_FOR_SU:
        logger.info(f"Don't add trace context for {current_distro}")
        return preserve_env, kwargs
    if trace_env := trace.context_for_environment():
        orig_env = kwargs["env"] if kwargs.get("env") else dict(os.environ)
        kwargs["env"] = {**orig_env, **trace_env}
        if sudo and preserve_env is not None:
            preserve_env.extend(trace_env.keys())
        elif sudo:
            preserve_env = list(trace_env.keys())
    return preserve_env, kwargs


def _extend_command(
    cmd: list[str],
    substitute_user: str | None,
    substitute_shell: str | None,
    sudo: bool,
    preserve_env: list[str] | None,
    kwargs: dict[str, Any],  # subprocess.<method> kwargs
) -> list[str]:
    """Return extended command by adding `sudo` or `su` usage."""

    methods = "`testlib.common.utils.check_output / execute / run`"
    # TODO: remove usage of kwargs & shell from methods `check_output / execute / run`.
    if kwargs.get("shell", False):
        raise NotImplementedError(
            f"`shell=True` is not supported by {methods}.\n"
            "Use desired `subprocess.<method>` directly for such cases."
        )
    if preserve_env and not (sudo or substitute_user):
        raise TypeError(
            f"'preserve_env' requires usage of 'sudo' or 'substitute_user' in {methods}!"
        )

    if substitute_shell and not substitute_user:
        raise TypeError(f"'substitute_shell' requires usage of 'substitute_user' in {methods}!")

    sudo_cmd = _cmd_as_sudo(preserve_env) if sudo else []
    user_cmd = (
        (
            _cmd_as_user(
                substitute_user,
                shell=substitute_shell,
                preserve_env=preserve_env,
            )
            + [shlex.join(cmd)]
        )
        if substitute_user
        else cmd
    )
    cmd_ = sudo_cmd + user_cmd
    logging.debug("Executing command: %s", shlex.join(cmd_))
    return cmd_


def _cmd_as_sudo(preserve_env: list[str] | None = None) -> list[str]:
    base_cmd = ["sudo"]
    if preserve_env:
        base_cmd += [f"--preserve-env={','.join(preserve_env)}"]
    return base_cmd


def _cmd_as_user(
    username: str,
    shell: str | None = None,
    preserve_env: list[str] | None = None,
) -> list[str]:
    """Extend commandline by adopting rol oe desired user."""
    base_cmd = ["su", "-l", username]
    if shell:
        base_cmd += ["--shell", shell]
    if preserve_env:
        current_distro = os.environ.get("DISTRO")
        if current_distro in DISTROS_MISSING_WHITELIST_ENVIRONMENT_FOR_SU:
            raise RuntimeError(
                f"Calling 'su' with '--whitelist-environment' is not supported under {current_distro}. "
                f"Fix the callsites."
            )
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
) -> Iterator[subprocess.Popen[str]]:
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
            stdout, _stderr = daemon_proc.communicate(timeout=5)
            logger.info("Output from %s daemon:\n%s", name_for_logging, stdout)
            assert daemon_rc is None, (
                f"{name_for_logging} daemon unexpectedly exited (RC={daemon_rc})!"
            )


def _terminate_daemon(
    daemon_proc: subprocess.Popen[str],
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
    input_: str | bytes | None = None,
    preserve_env: list[str] | None = None,
    sudo: bool = False,
    substitute_user: str | None = None,
    **kwargs: Any,
) -> str: ...


@overload
def check_output(
    cmd: list[str],
    encoding: None,
    input_: str | bytes | None = None,
    preserve_env: list[str] | None = None,
    sudo: bool = False,
    substitute_user: str | None = None,
    **kwargs: Any,
) -> bytes: ...


def check_output(
    cmd: list[str],
    encoding: str | None = "utf-8",
    input_: str | bytes | None = None,
    preserve_env: list[str] | None = None,
    sudo: bool = False,
    substitute_user: str | None = None,
    **kwargs: Any,
) -> str | bytes:
    """Mimics subprocess.check_output while running a process as root or a different user.

    Returns the stdout of the process.
    """
    preserve_env, kwargs = _add_trace_context(kwargs, preserve_env, sudo)
    cmd_ = _extend_command(cmd, substitute_user, None, sudo, preserve_env, kwargs)

    kwargs["encoding"] = encoding
    kwargs["input"] = input_

    with tracer.span("execute", attributes={"cmk.command": repr(cmd_)}):
        return subprocess.check_output(cmd_, **kwargs)  # type: ignore[no-any-return]


@overload
def read_file(
    path: str | Path,
    encoding: str = "utf-8",
    sudo: bool = True,
    substitute_user: str | None = None,
) -> str: ...


@overload
def read_file(
    path: str | Path,
    encoding: None,
    sudo: bool = True,
    substitute_user: str | None = None,
) -> bytes: ...


def read_file(
    path: str | Path,
    encoding: str | None = "utf-8",
    sudo: bool = True,
    substitute_user: str | None = None,
) -> str | bytes:
    """Read a file as root or another user."""
    try:
        return run(
            ["cat", Path(path).as_posix()],
            capture_output=True,
            encoding=encoding,
            sudo=sudo,
            substitute_user=substitute_user,
        ).stdout
    except subprocess.CalledProcessError as excp:
        excp.add_note(f"Failed to read file '{path}'!")
        raise excp


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
            input_=content,
            stdout=subprocess.DEVNULL,
            encoding=None if isinstance(content, bytes) else "utf-8",
            sudo=sudo,
            substitute_user=substitute_user,
        )
    except subprocess.CalledProcessError as excp:
        excp.add_note(f"Failed to write file '{path}'!")
        raise excp


def makedirs(path: str | Path, sudo: bool = True, substitute_user: str | None = None) -> None:
    """Make directory path (including parents) as root or another user."""
    _ = run(["mkdir", "-p", Path(path).as_posix()], sudo=sudo, substitute_user=substitute_user)


def restart_httpd() -> None:
    """Restart Apache manually on RHEL-based containers.

    On RHEL-based containers, such as AlmaLinux, the system Apache is not running.
    OMD will not start Apache, if it is not running already.

    If a distro uses an `INIT_CMD`, which is not available inside of docker, then the system
    Apache won't be restarted either. For example, sles uses `systemctl restart apache2.service`.
    However, the docker container does not use systemd as in init process. Thus, this fails in the
    test environment, but not a real distribution.

    Before using this in your test, try an Apache reload instead. It is much more likely to work
    across different distributions. If your test needs a system Apache, then run this command at
    the beginning of the test. This ensures consistency across distributions.
    """

    almalinux_prefix = "almalinux"
    assert any(
        distro for distro in get_supported_distros() if distro.startswith(almalinux_prefix)
    ), "We dropped support for almalinux, please adapt the code below."

    # When executed locally and un-dockerized, DISTRO may not be set
    if os.environ.get("DISTRO", "").startswith(almalinux_prefix):
        run(["httpd", "-k", "restart"], sudo=True)


@dataclasses.dataclass
class ServiceInfo:
    state: int
    summary: str
    extra_columns: dict[str, Any]


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
            if service_info.state == state
        }
    for state, services in services_by_state.items():
        logger.debug(
            "%s service(s) found in state %s (%s):\n%s",
            len(services),
            state,
            {0: "OK", 1: "WARN", 2: "CRIT", 3: "UNKNOWN"}.get(state, "UNDEFINED"),
            pformat(services),
        )
    services_list = {_ for _ in services_by_state[service_status] if _ not in skipped_services}
    return services_list


def parse_files(
    path_name: Path,
    files_name_pattern: str,
    content_pattern: str,
    sudo: bool = False,
    ignore_case: bool = True,
) -> dict[str, list[str]]:
    """Parse file(s) for a given pattern.

    Args:
        path_name:          The directory path where the files are located.
        files_name_pattern: The glob pattern to match file names.
        content_pattern:    The regex pattern to search for in the file contents.
        sudo:               Whether to run the command with sudo privileges.
        ignore_case:        Whether to ignore case when matching the content pattern.

    Returns:
        A dictionary where keys are file paths and values are lists of matching lines.
    """
    pattern_obj = re.compile(content_pattern, re.IGNORECASE if ignore_case else 0)
    logger.info("Parsing logs for '%s' in %s", content_pattern, path_name)
    match_dict: dict[str, list[str]] = {}
    files_paths = check_output(
        ["bash", "-c", f"find {path_name} -name '{files_name_pattern}' -type f"],
        sudo=sudo,
        encoding="utf-8",
    ).splitlines()
    for file_path in files_paths:
        file_content = read_file(file_path, sudo=sudo, encoding="utf-8").splitlines()
        for line in file_content:
            if pattern_obj.search(line):
                logger.warning("Match found in %s: %s", file_path, line.strip())
                match_dict[file_path] = match_dict.get(file_path, []) + [line]
    return match_dict


def get_supported_distros() -> list[str]:
    with open(repo_path() / "editions.yml") as stream:
        yaml_file = yaml.safe_load(stream)

    supported_distros: list[str] = yaml_file["common"]
    return supported_distros


def check_permissions(file_path: Path, expected_permissions: str) -> None:
    """Check if the file has the expected permissions."""
    actual_permissions = filemode(file_path.stat().st_mode)
    assert actual_permissions == expected_permissions, (
        f"Unexpected permissions for {file_path}: {actual_permissions}"
    )


def is_cleanup_enabled() -> bool:
    """Check if cleanup is enabled."""
    return os.getenv("CLEANUP", "1") == "1"


def html_find_text_nodes(
    html: str, tag_name: str, search_terms: str | tuple[str, ...]
) -> list[str]:
    """Find a tag_name enclosing a given search_text and return all text nodes within it."""
    soup = BeautifulSoup(html, "html.parser")
    if isinstance(search_terms, str):
        search_terms = (search_terms,)  # normalize to tuple
    matches = soup.find_all(string=lambda tag: all(tag and term in tag for term in search_terms))
    results = []
    for match in matches:
        parent = match.parent
        while parent:
            if parent.name == tag_name:
                # Collect all text nodes inside this tag
                results += list(parent.stripped_strings)
                break
            parent = parent.parent
    return results
