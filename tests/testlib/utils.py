#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
import os
import re
import shlex
import subprocess
import sys
import textwrap

# pylint: disable=redefined-outer-name
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from pprint import pformat
from urllib.parse import urlparse

import pexpect  # type: ignore[import-untyped]
import pytest

from cmk.utils.version import Edition

LOGGER = logging.getLogger()


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


def repo_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def qa_test_data_path() -> Path:
    return Path(__file__).parent.parent.resolve() / Path("qa-test-data")


def cmc_path() -> Path:
    return repo_path() / "enterprise"


def is_enterprise_repo() -> bool:
    return (repo_path() / "omd" / "packages" / "enterprise").exists()


def is_managed_repo() -> bool:
    return (repo_path() / "omd" / "packages" / "managed").exists()


def is_cloud_repo() -> bool:
    return (repo_path() / "omd" / "packages" / "cloud").exists()


def is_saas_repo() -> bool:
    return (repo_path() / "omd" / "packages" / "saas").exists()


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


def find_git_rm_mv_files(dirpath: Path) -> list[str]:
    del_files = []

    out = subprocess.check_output(
        [
            "git",
            "-C",
            str(dirpath),
            "status",
            str(dirpath),
        ],
        encoding="utf-8",
    ).split("\n")

    for line in out:
        if "deleted:" in line or "renamed:" in line:
            # Ignore files in subdirs of dirpath
            if line.split(dirpath.name)[1].count("/") > 1:
                continue

            filename = line.split("/")[-1]
            del_files.append(filename)
    return del_files


def current_branch_name() -> str:
    branch_name = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], encoding="utf-8"
    )
    return branch_name.split("\n", 1)[0]


def current_branch_version() -> str:
    return subprocess.check_output(
        [
            "make",
            "--no-print-directory",
            "-f",
            str(repo_path() / "defines.make"),
            "print-BRANCH_VERSION",
        ],
        encoding="utf-8",
    ).strip()


def current_base_branch_name() -> str:
    branch_name = current_branch_name()

    # Detect which other branch this one was created from. We do this by going back the
    # current branches git log one step by another and check which branches contain these
    # commits. Only search for our main (master + major-version) branches
    commits = subprocess.check_output(
        ["git", "rev-list", "--max-count=30", branch_name], encoding="utf-8"
    )
    for commit in commits.strip().split("\n"):
        # Asking for remote heads here, since the git repos checked out by jenkins do not create all
        # the branches locally

        # --format=%(refname): Is not supported by all distros :(
        #
        # heads = subprocess.check_output(
        #    ["git", "branch", "-r", "--format=%(refname)", "--contains", commit])
        # if not isinstance(heads, str):
        #    heads = heads.decode("utf-8")

        # for head in heads.strip().split("\n"):
        #    if head == "refs/remotes/origin/master":
        #        return "master"

        #    if re.match(r"^refs/remotes/origin/[0-9]+\.[0-9]+\.[0-9]+$", head):
        #        return head

        lines = subprocess.check_output(
            ["git", "branch", "-r", "--contains", commit], encoding="utf-8"
        )
        for line in lines.strip().split("\n"):
            if not line:
                continue
            head = line.split()[0]

            if head == "origin/master":
                return "master"

            if re.match(r"^origin/[0-9]+\.[0-9]+\.[0-9]+$", head):
                return head[7:]

    LOGGER.warning("Could not determine base branch, using %s", branch_name)
    return branch_name


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


def add_python_paths() -> None:
    sys.path.insert(0, str(repo_path()))
    if is_enterprise_repo():
        sys.path.insert(0, os.path.join(repo_path(), "non-free", "cmc-protocols"))
        sys.path.insert(0, os.path.join(repo_path(), "non-free", "cmk-update-agent"))
    sys.path.insert(0, os.path.join(repo_path(), "omd/packages/omd"))


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


def branch_from_env(*, env_var: str, fallback: str | Callable[[], str] | None = None) -> str:
    if branch := os.environ.get(env_var):
        return branch
    if fallback:
        return fallback() if callable(fallback) else fallback
    raise RuntimeError(f"{env_var} environment variable, e.g. master, is missing")


def spawn_expect_process(
    args: list[str],
    dialogs: list[PExpectDialog],
    logfile_path: str = "/tmp/sep.out",
    auto_wrap_length: int = 49,
    break_long_words: bool = False,
) -> int:
    """Spawn an interactive CLI process via pexpect and process supplied expected dialogs
    "dialogs" must be a list of objects with the following format:
    {"expect": str, "send": str, "count": int, "optional": bool}

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
                        ]
                    )
                    if rc == 0:
                        # msg found; sending input
                        LOGGER.info(
                            "%s; sending: %s",
                            "Optional message found"
                            if dialog.optional
                            else "Required message found",
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
                rc = p.expect(pexpect.EOF)
            else:
                rc = p.status
        except Exception as e:
            LOGGER.exception(e)
            LOGGER.debug(p)
            rc = 3

    assert isinstance(rc, int)
    return rc


def run(args: Sequence[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a process and return a CompletedProcess object."""
    LOGGER.info("Executing: %s", subprocess.list2cmdline(args))
    try:
        proc = subprocess.run(
            args,
            encoding="utf-8",
            stdin=subprocess.DEVNULL,
            capture_output=True,
            close_fds=True,
            check=check,
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
    sudo: bool = True,
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
    path: str,
    content: bytes | str,
    sudo: bool = True,
    substitute_user: str | None = None,
) -> None:
    """Write a file as root or another user."""
    with execute(
        ["tee", path],
        sudo=sudo,
        substitute_user=substitute_user,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        encoding=None
        if isinstance(
            content,
            bytes,
        )
        else "utf-8",
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


def makedirs(path: str, sudo: bool = True, substitute_user: str | None = None) -> bool:
    """Make directory path (including parents) as root or another user."""
    p = execute(["mkdir", "-p", path], sudo=sudo, substitute_user=substitute_user)
    return p.wait() == 0


def restart_httpd() -> None:
    """On RHEL-based distros, such as CentOS and AlmaLinux, we have to manually restart httpd after
    creating a new site. Otherwise, the site's REST API won't be reachable via port 80, preventing
    e.g. the controller from querying the agent receiver port.

    Note: the mere presence of httpd is not enough to determine whether we have to restart or not,
    see e.g. sles-15sp4.
    """

    # When executed locally and un-dockerized, DISTRO may not be set
    if os.environ.get("DISTRO") in {"centos-8", "almalinux-9"}:
        run(["sudo", "httpd", "-k", "restart"])


def get_services_with_status(
    host_data: dict, service_status: int, skipped_services: list | tuple = ()
) -> set:
    """Return a set of services in the given status which are not in the 'skipped' list."""
    services_list = set()
    for service in host_data:
        if host_data[service] == service_status and service not in skipped_services:
            services_list.add(service)

    LOGGER.debug(
        "%s service(s) found in state %s:\n%s",
        len(services_list),
        service_status,
        pformat(services_list),
    )
    return services_list


@contextmanager
def cse_openid_oauth_provider(site_url: str) -> Iterator[subprocess.Popen]:
    idp_url = "http://localhost:5551"
    makedirs("/etc/cse", sudo=True)
    assert os.path.exists("/etc/cse")

    cognito_config = "/etc/cse/cognito-cmk.json"
    write_cognito_config = not os.path.exists(cognito_config)
    global_config = "/etc/cse/global-config.json"
    write_global_config = not os.path.exists(global_config)
    if write_cognito_config:
        write_file(
            cognito_config,
            check_output(
                [f"{repo_path()}/scripts/create_cognito_config_cse.sh", idp_url, site_url]
            ),
            sudo=True,
        )
    else:
        LOGGER.warning('Skipped writing "%s": File exists!', cognito_config)
    assert os.path.exists(cognito_config)

    if write_global_config:
        with open(f"{repo_path()}/tests/etc/cse/global-config.json") as f:
            write_file(
                global_config,
                f.read(),
                sudo=True,
            )
    else:
        LOGGER.warning('Skipped writing "%s": File exists!', global_config)
    assert os.path.exists(global_config)

    idp = urlparse(idp_url)
    auth_provider_proc = execute(
        [
            f"{repo_path()}/scripts/run-pipenv",
            "run",
            "uvicorn",
            "tests.testlib.cse.openid_oauth_provider:application",
            "--host",
            f"{idp.hostname}",
            "--port",
            f"{idp.port}",
        ],
        sudo=False,
        cwd=repo_path(),
        env=dict(os.environ, URL=idp_url),
        shell=False,
    )
    assert (
        auth_provider_proc.poll() is None
    ), f"Error while starting auth provider! (RC: {auth_provider_proc.returncode})"
    try:
        yield auth_provider_proc
    finally:
        if auth_provider_proc:
            auth_provider_proc.kill()
        if write_cognito_config:
            execute(["rm", cognito_config])
        if write_global_config:
            execute(["rm", global_config])


def wait_until(condition: Callable[[], bool], timeout: float = 1, interval: float = 0.1) -> None:
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return  # Success. Stop waiting...
        time.sleep(interval)

    raise Exception("Timeout waiting for %r to finish (Timeout: %d sec)" % (condition, timeout))
