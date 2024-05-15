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
from contextlib import contextmanager, suppress
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
    """Returns the checkout/worktree path (in contrast to the 'git-dir')
    same as result of `git rev-parse --show-toplevel`, but repo_path is being executed
    quite often, so we take the not-so-portable-but-more-efficient approach.
    """
    return Path(__file__).resolve().parent.parent.parent


def git_essential_directories(checkout_dir: Path) -> Iterator[str]:
    """Yields paths to all directories needed to be accessible in order to run git operations
    Note that if a directory is a subdirectory of checkout_dir it will be skipped"""

    # path to the 'real git repository directory', i.e. the common dir when dealing with work trees
    common_dir = (
        (
            checkout_dir
            / subprocess.check_output(
                ["git", "rev-parse", "--git-common-dir"], cwd=checkout_dir, text=True
            ).rstrip("\n")
        )
        .resolve()
        .absolute()
    )

    if not common_dir.is_relative_to(checkout_dir):
        yield common_dir.as_posix()

    # In case of reference clones we also need to access them.
    # Not sure if 'objects/info/alternates' can contain more than one line and if we really need
    # the parent, but at least this one is working for us
    with suppress(FileNotFoundError):
        with (common_dir / "objects/info/alternates").open() as alternates:
            for alternate in (Path(line).parent for line in alternates):
                if not alternate.is_relative_to(checkout_dir):
                    yield alternate.as_posix()


def git_commit_id(path: Path | str) -> str:
    """Returns the git hash for given @path."""
    return subprocess.check_output(
        # use the full hash - short hashes cannot be checked out and they are not
        # unique among machines
        ["git", "log", "--pretty=tformat:%H", "-n1"] + [str(path)],
        cwd=repo_path(),
        text=True,
    ).strip("\n")


def qa_test_data_path() -> Path:
    return Path(__file__).parent.parent.resolve() / Path("qa-test-data")


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
        # Asking for remote heads here, since the git repos checked out in CI
        # do not create all branches locally

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
    if os.environ.get("DISTRO") in {"centos-8", "almalinux-9"}:
        run(["sudo", "httpd", "-k", "restart"])


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


@contextmanager
def _cse_config(config: Path, content: bytes | str) -> Iterator[None]:
    write_config = not os.path.exists(config)
    if write_config:
        write_file(config.as_posix(), content, sudo=True)
    else:
        LOGGER.warning('Skipped writing "%s": File exists!', config)
    assert config.exists()
    yield
    if write_config:
        execute(["rm", config.as_posix()])


@contextmanager
def cse_openid_oauth_provider(site_url: str) -> Iterator[subprocess.Popen]:
    from cmk.gui.cse.userdb.cognito import oauth2

    idp_url = "http://localhost:5551"
    makedirs("/etc/cse", sudo=True)
    assert os.path.exists("/etc/cse")

    cognito_config = Path("/etc/cse/cognito-cmk.json")
    cognito_content = check_output(
        [f"{repo_path()}/scripts/create_cognito_config_cse.sh", idp_url, site_url]
    )

    global_config = Path("/etc/cse/global-config.json")
    with open(f"{repo_path()}/tests/etc/cse/global-config.json") as f:
        global_content = f.read()

    uap_config = Path("/etc/cse/admin_panel_url.json")
    uap_content = oauth2.AdminPanelUrl(uap_url="https://some.test.url/uap").model_dump_json()

    with (
        _cse_config(cognito_config, cognito_content),
        _cse_config(global_config, global_content),
        _cse_config(uap_config, uap_content),
    ):
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


def cse_create_onboarding_dummies(root: str) -> None:
    onboarding_dir = os.path.join(root, "share/check_mk/web/htdocs/onboarding")
    if os.path.exists(onboarding_dir):
        return
    LOGGER.warning("SaaS edition onboarding files not found; creating dummy files...")
    makedirs(onboarding_dir)
    write_file(f"{onboarding_dir}/search.css", "/* cse dummy file */")
    write_file(f"{onboarding_dir}/search.js", "/* cse dummy file */")


def wait_until(condition: Callable[[], bool], timeout: float = 1, interval: float = 0.1) -> None:
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return  # Success. Stop waiting...
        time.sleep(interval)

    raise TimeoutError("Timeout waiting for %r to finish (Timeout: %d sec)" % (condition, timeout))
