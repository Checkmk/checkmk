#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""This module provides functionality to execute tests within a Docker container.

It handles the preparation of the Docker environment, executing specified test commands within
the container, and collecting and storing the test results.
"""

import logging
import os
import re
import shlex
import subprocess
import sys
import tarfile
import textwrap
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, TypedDict, Unpack

import docker
import docker.errors
import docker.models.containers
import docker.models.images
import docker.types
import requests

from tests.testlib.common.repo import git_commit_id, git_essential_directories, repo_path
from tests.testlib.common.utils2 import get_cmk_download_credentials, is_cleanup_enabled
from tests.testlib.common.version import CMKPackageInfo, CMKVersion, package_hash_path
from tests.testlib.system.package_manager import DISTRO_CODES

_DOCKER_REGISTRY = "artifacts.lan.tribe29.com:4000"
_DOCKER_REGISTRY_URL = "https://%s/v2/" % _DOCKER_REGISTRY
# Increase this to enforce invalidation of all existing images
_DOCKER_BUILD_ID = 1
_TESTUSER = "testuser"

# Docker mounts /sys/fs/cgroup read-only in every container that is not privileged. systemd
# cannot create its own cgroup tree under such a mount and exits immediately without writing
# anything to the container log. Remounting read-write is refused, so mount a fresh cgroup2
# filesystem over it instead. That needs CAP_SYS_ADMIN and an AppArmor exception, both of
# which the host config below already grants.
_BOOT_SYSTEMD = (
    "umount /sys/fs/cgroup 2>/dev/null || true; "
    "mount -t cgroup2 none /sys/fs/cgroup || "
    "{ echo 'failed to mount cgroup2 over /sys/fs/cgroup' >&2; exit 1; }; "
    # cgroupfs never allows creating plain files, so probing with touch reports a false failure
    "{ mkdir /sys/fs/cgroup/probe.slice && rmdir /sys/fs/cgroup/probe.slice; } || "
    "{ echo 'cgroup2 at /sys/fs/cgroup is not writable' >&2; exit 1; }; "
    "exec /sbin/init"
)
_SYSTEMD_PACKAGES_APT = ["systemd", "systemd-sysv", "dbus", "dbus-user-session"]
_SYSTEMD_PACKAGES_DNF = ["systemd", "dbus"]
# Units that either cannot work in a container or serve no purpose in one. tmp.mount would
# replace /tmp by a fresh tmpfs and thereby change the size of the directory the package
# downloads and pytest's tmp_path use.
_SYSTEMD_UNITS_TO_MASK = [
    "console-getty.service",
    "getty-static.service",
    "getty.target",
    "sys-kernel-config.mount",
    "systemd-firstboot.service",
    "systemd-journald-audit.socket",
    "systemd-modules-load.service",
    "systemd-resolved.service",
    "systemd-udev-trigger.service",
    "systemd-udevd-control.socket",
    "systemd-udevd-kernel.socket",
    "systemd-udevd.service",
    "tmp.mount",
]

logger = logging.getLogger()


def execute_tests_in_container(
    distro_name: str,
    docker_tag: str,
    package_info: CMKPackageInfo,
    result_path: Path,
    command: list[str],
    interactive: bool,
    systemd: bool = False,
) -> int:
    client: docker.DockerClient = _docker_client()
    info = client.info()
    logger.info("Docker version: %s", info["ServerVersion"])

    container_env = _container_env(package_info)
    image_name_with_tag = _create_cmk_image(
        client, distro_name, docker_tag, package_info, container_env, systemd
    )

    host_config_args: dict[str, object] = {
        "cap_add": ["SYS_ADMIN"],
        # Why unconfined? see https://github.com/moby/moby/issues/16429
        "security_opt": ["apparmor:unconfined"],
        # Important to workaround really high default of docker which results
        # in problems when trying to close all FDs in Python 2.
        "ulimits": [docker.types.Ulimit(name="nofile", soft=8192, hard=8192)],
        "binds": _runtime_binds(),
    }
    start_args: CreateContainerKwargs
    if systemd:
        host_config_args |= {
            # systemd needs a private cgroup namespace and a writable /run of its own
            "cgroupns": "private",
            "tmpfs": {"/run": "", "/run/lock": ""},
        }
        start_args = {
            # Docker's own init would occupy PID 1, and systemd refuses to run as anything else
            "entrypoint": ["/bin/bash", "-c"],
            "command": [_BOOT_SYSTEMD],
            # systemd reads SIGTERM as a request to re-execute itself, so stopping the container
            # with the default signal would block until the timeout and then end in SIGKILL
            "stop_signal": "SIGRTMIN+3",
            "stop_timeout": 60,
        }
    else:
        host_config_args |= {"init": True}
        start_args = {"command": "/bin/bash", "stdin_open": True, "tty": True}

    start_args["host_config"] = client.api.create_host_config(**host_config_args)  # type: ignore[arg-type]

    # Start the container
    container: docker.models.containers.Container
    with _start(
        client,
        image=image_name_with_tag,
        # TODO: Re-enable using dedicated container names, the following causes name conflicts:
        # name=f"test-{container_name_suffix(distro_name, docker_tag)}",
        **start_args,
    ) as container:
        if systemd:
            _await_systemd(container)
        _prepare_git_overlay(container, "/git-lowerdir", "/git", _TESTUSER)
        _cleanup_previous_virtual_environment(container, container_env)
        _reuse_persisted_virtual_environment(container, container_env, _TESTUSER)

        if interactive:
            print(  # noqa: T201  # It's OK for test/script helpers to print()
                textwrap.dedent("""
                Next steps: Start the test of your choice, for example:

                Run all single site system tests:
                    tests/run_tests.sh test-system-singlesite

                Run all single site system tests in a module:
                    pytest tests/system/singlesite/livestatus/test_livestatus.py

                Run a specific test in a module:
                    pytest tests/system/singlesite/livestatus/test_livestatus.py -k test_service_custom_variables

                NOTE:
                * The version of Checkmk you test against is set using the VERSION environment variable
                    and defaults to the current daily build of your branch.
                * If you want to test a patched version, you need to patch it before running tests.
                * If you install a site manually and want to access the UI, you need to run this:
                    sudo apache2ctl start
                """)
                if not systemd
                else textwrap.dedent("""
                This container runs systemd as PID 1. Start the test of your choice, for example:

                Run the agent update system tests:
                    tests/run_tests.sh test-system-agent-updates

                Inspect the units the agent package deploys:
                    systemctl status cmk-agent-ctl-daemon.service check-mk-agent.socket
                    journalctl -u cmk-agent-ctl-daemon -b --no-pager

                NOTE:
                * The version of Checkmk you test against is set using the VERSION environment variable
                    and defaults to the current daily build of your branch.
                * If you install a site manually and want to access the UI, you need to run this:
                    sudo systemctl start apache2
                """)
            )

            if command:
                _exec_interactive(
                    container, ["sudo", "-u", _TESTUSER, "/git/scripts/run-uvenv"] + command
                )

            _exec_interactive(
                container,
                [
                    "sudo",
                    "su",
                    "--pty",
                    "-",
                    _TESTUSER,
                    "-c",
                    "cd /git; source /git/.venv/bin/activate; bash",
                ],
            )

            return 0

        # Now execute the real test in the container context
        exit_code = _exec_run(
            container,
            command,
            check=False,
            user=_TESTUSER,
            environment=container_env,
            workdir="/git",
            stream=True,
            tty=True,  # NOTE: Some tests require a tty (e.g. test-system-update)!
        )

        if systemd:
            _dump_systemd_state(container, Path("/results/systemd"))

        # Collect the test results located in /results of the container. The
        # CI job will make it available as artifact later
        _copy_directory(container, Path("/results"), result_path)

        return exit_code


def _await_systemd(container: docker.models.containers.Container, timeout: float = 60.0) -> None:
    """Block until systemd finished booting inside the container.

    A "degraded" system is accepted. Masking every unit that cannot work in a container is not
    realistic, and a single masked-away failure must not fail the whole run.
    """
    deadline = time.time() + timeout
    state = "unknown"
    while time.time() < deadline:
        container.reload()
        if container.status != "running":
            state = f"the container itself is {container.status}"
            break
        try:
            _rc, output = container.exec_run(["systemctl", "is-system-running"])
        except docker.errors.APIError:
            # The container died between the status check and the exec.
            continue
        assert isinstance(output, bytes)  # stream/socket/demux not used above
        state = output.decode("utf-8", errors="replace").strip()
        if state in ("running", "degraded"):
            logger.info("systemd finished booting, state: %s", state)
            return
        time.sleep(1)

    _log_systemd_boot_failure(container)
    raise RuntimeError(
        f"systemd did not finish booting within {timeout}s (last state: {state!r}). A container "
        "that exits without a log message usually failed to mount cgroup2 over /sys/fs/cgroup."
    )


def _log_systemd_boot_failure(container: docker.models.containers.Container) -> None:
    logger.error(
        "Container log:\n%s",
        container.logs().decode("utf-8", errors="replace"),
    )
    container.reload()
    if container.status != "running":
        return
    for cmd in (
        ["systemctl", "list-units", "--failed"],
        ["journalctl", "-b", "--no-pager", "-n", "200"],
    ):
        try:
            _rc, output = container.exec_run(cmd)
        except docker.errors.APIError:
            logger.exception("Could not run %s", subprocess.list2cmdline(cmd))
            continue
        assert isinstance(output, bytes)  # stream/socket/demux not used above
        logger.error(
            "%s:\n%s",
            subprocess.list2cmdline(cmd),
            output.decode("utf-8", errors="replace"),
        )


def _dump_systemd_state(container: docker.models.containers.Container, target: Path) -> None:
    """Write systemd diagnostics into the results directory, so CI archives them."""
    _exec_run(container, ["mkdir", "-p", target.as_posix()], check=False)
    for name, cmd in (
        ("failed-units.txt", "systemctl list-units --failed --no-pager"),
        ("journal.txt", "journalctl -b --no-pager"),
    ):
        _exec_run(container, ["sh", "-c", f"{cmd} > {target / name} 2>&1"], check=False)


def _prepare_systemd(container: docker.models.containers.Container, distro_name: str) -> None:
    """Install systemd and mask the units that cannot work in a container.

    systemctl mask works without a running systemd, because it only symlinks the unit to
    /dev/null.
    """
    if distro_name.startswith(("debian-", "ubuntu-")):
        logger.info("Installing systemd: %s", " ".join(_SYSTEMD_PACKAGES_APT))
        _exec_run(container, ["apt-get", "update"], stream=True)
        _exec_run(
            container,
            ["apt-get", "install", "-y", "--no-install-recommends"] + _SYSTEMD_PACKAGES_APT,
            environment={"DEBIAN_FRONTEND": "noninteractive"},
            stream=True,
        )
    elif distro_name.startswith("almalinux-"):
        logger.info("Installing systemd: %s", " ".join(_SYSTEMD_PACKAGES_DNF))
        _exec_run(
            container,
            ["dnf", "install", "-y", "--setopt=install_weak_deps=False"] + _SYSTEMD_PACKAGES_DNF,
            stream=True,
        )
    else:
        raise NotImplementedError(
            f"Preparing systemd for {distro_name} is not implemented yet. Only the apt and dnf "
            "based distributions are supported so far."
        )
    logger.info("Masking %d systemd units", len(_SYSTEMD_UNITS_TO_MASK))
    _exec_run(container, ["systemctl", "mask"] + _SYSTEMD_UNITS_TO_MASK)


def _restore_systemctl(container: docker.models.containers.Container) -> None:
    """Undo what shadow_systemctl() did during the Checkmk installation."""
    _exec_run(
        container,
        [
            "scripts/run-uvenv",
            "python3",
            "-c",
            "from tests.testlib.system.systemctl_stub import unshadow_systemctl; unshadow_systemctl()",
        ],
        workdir="/git",
    )
    _exec_run(container, ["sh", "-c", "systemctl --version | grep -q '^systemd '"])


def _docker_client() -> docker.DockerClient:
    return docker.from_env(timeout=1200)


def _exec_interactive(container: docker.models.containers.Container, command: list[str]) -> None:
    # Use the docker CLI instead of the docker API: it attaches our terminal and keeps the
    # container's PTY size in sync with it (initially and on resize).
    subprocess.run(["docker", "exec", "-it", container.short_id] + command, check=False)


def _get_or_load_image(
    client: docker.DockerClient, image_name_with_tag: str
) -> docker.models.images.Image | None:
    try:
        image = client.images.get(image_name_with_tag)
        logger.info("  Available locally (%s)", image.short_id)

        # Verify that this is in sync with remote version
        registry_data = _get_registry_data(client, image_name_with_tag)
        if not registry_data:
            logger.info("  Registry state is unknown, using local image")
            return image

        if registry_data.short_id == image.short_id:
            logger.info("  Is in sync with registry, using local image")
            return image

        logger.info("  Not in sync with registry (%s), trying to pull", registry_data.short_id)
    except docker.errors.ImageNotFound:
        logger.info(
            "  Not available locally, trying to pull (May take some time. Grab a coffee or two...)"
        )

    try:
        image = client.images.pull(image_name_with_tag)
        logger.info("  Downloaded (%s)", image.short_id)
        return image
    except docker.errors.NotFound:
        logger.info("  Not available from registry")
    except docker.errors.APIError as exc:
        _handle_api_error(exc)

    return None


def _get_registry_data(
    client: docker.DockerClient, image_name_with_tag: str
) -> docker.models.images.Image | None:
    try:
        registry_data = client.images.get_registry_data(image_name_with_tag)
        logger.info("  pull '%s'", image_name_with_tag)
        return registry_data.pull()
    except docker.errors.NotFound:
        logger.info("  Not available from registry")
        return None
    except docker.errors.APIError as exc:
        _handle_api_error(exc)
        return None


def _handle_api_error(exc: docker.errors.APIError) -> None:
    if exc.status_code == HTTPStatus.UNAUTHORIZED or (
        exc.status_code == HTTPStatus.INTERNAL_SERVER_ERROR and "no basic auth" in f"{exc}"
    ):
        raise RuntimeError(
            'Could not authenticate against "%s". You will have to login to the '
            'registry using "docker login %s" to be able to execute the tests.'
            % (_DOCKER_REGISTRY, _DOCKER_REGISTRY_URL)
        ) from exc
    if "request canceled while waiting for connection" in "%s" % exc:
        return
    if "dial tcp: lookup " in "%s" % exc:
        # May happen when offline on ubuntu
        return
    raise exc


def check_for_local_package(package_info: CMKPackageInfo, distro_name: str) -> bool:
    """Checks package_download folder for a Checkmk package and returns True if
    exactly one package is available and meets some requirements. If there are
    invalid packages, the application terminates."""
    packages_dir = repo_path() / "package_download"
    if available_packages := [
        p for p in packages_dir.glob("*") if re.match("^.*check-mk.*(rpm|deb)$", p.name)
    ]:
        if len(available_packages) > 1:
            logger.error(
                "Error: There must be exactly one Checkmk package in %s, but there are %d:",
                packages_dir,
                len(available_packages),
            )
            for path in available_packages:
                logger.error("Error:   %s", path)
            raise SystemExit(1)

        package_name = available_packages[0].name
        os_name = DISTRO_CODES.get(distro_name, f"UNKNOWN DISTRO: {distro_name}")
        pkg_pattern = (
            rf"check-mk-{package_info.edition.long}-{package_info.version.version}"
            rf".*{os_name}.*\.(deb|rpm)"
        )
        if not re.match(f"^{pkg_pattern}$", package_name):
            logger.error("Error: '%s' does not match version=%s", package_name, package_info)
            logger.error("Error:  (must be '%s')", pkg_pattern)
            raise SystemExit(1)

        logger.info("found %s", available_packages[0])
        return True
    return False


def container_name_suffix(distro_name: str, docker_tag: str) -> str:
    """Container names are (currently) not needed at all but help with finding the context.
    However they need to be informative but unique to avoid conflicts.
    In order to be able to use the same naming scheme for incremental test-image builds soon,
    we put everything in that qualifies a container for a certain scenario (distro, docker_tag,
    runtime-requirements.txt) but make it 'unique' for now by adding a timestamp"""
    return (
        f"{distro_name}-{docker_tag}"
        f"-{git_commit_id('runtime-requirements.txt')[:10]}"
        f"-{time.strftime('%Y%m%d%H%M%S')}"
    )


def _create_cmk_image(
    client: docker.DockerClient,
    distro_name: str,
    docker_tag: str,
    package_info: CMKPackageInfo,
    container_env: dict[str, str],
    systemd: bool = False,
) -> str:
    base_image_name_with_tag = f"{_DOCKER_REGISTRY}/{distro_name}:{docker_tag}"
    logger.info("Prepare distro-specific base image [%s]", base_image_name_with_tag)
    if not (base_image := _get_or_load_image(client, base_image_name_with_tag)):
        raise RuntimeError(
            'Image [%s] is not available locally and the registry "%s" is not reachable. It is '
            "not implemented yet to build the image locally. Terminating."
            % (base_image_name_with_tag, _DOCKER_REGISTRY_URL)
        )

    # This installs the requested Checkmk Edition+Version into the new image, for this reason we add
    # these parts to the target image name. The tag is equal to the origin image.
    # The two flavours must not share a tag. Neither _is_based_on_current_base_image nor
    # _is_using_current_cmk_package would notice that one overwrote the other, because both
    # compare only the base image and the Checkmk package.
    flavour = "-systemd" if systemd else ""
    image_name_with_tag = (
        f"{_DOCKER_REGISTRY}/"
        f"{distro_name}{flavour}-{package_info.edition.short}"
        f"-{package_info.version.version_rc_aware}"
        f":{docker_tag}"
    )
    if use_local_package := check_for_local_package(package_info, distro_name):
        logger.info("+====================================================================+")
        logger.info("| Use locally available package (i.e. don't try to fetch test-image) |")
        logger.info("+====================================================================+")
    else:
        logger.info("+====================================+")
        logger.info("| No locally available package found |")
        logger.info("+====================================+")

        logger.info("Check for available test-image [%s]", image_name_with_tag)
        # First try to get the pre-built image from the local or remote registry
        if (
            (image := _get_or_load_image(client, image_name_with_tag))
            and _is_based_on_current_base_image(image, base_image)
            and _is_using_current_cmk_package(image, package_info.version)
        ):
            # We found something locally or remote and ensured it's available locally.
            # Only use it when it's based on the latest available base image. Otherwise
            # skip it. The following code will re-build one based on the current base image
            return image_name_with_tag  # already found, nothing to do.

    logger.info("Build test image [%s] from [%s]", image_name_with_tag, base_image_name_with_tag)

    container_label = {
        "com.checkmk.build_time": f"{int(time.time()):d}",
        "com.checkmk.build_id": base_image.short_id,
        "com.checkmk.base_image": base_image_name_with_tag,
        "com.checkmk.base_image_hash": base_image.short_id,
        "com.checkmk.cmk_edition_short": package_info.edition.short,
        "com.checkmk.cmk_version": package_info.version.version,
        "com.checkmk.cmk_version_rc_aware": package_info.version.version_rc_aware,
        "com.checkmk.cmk_branch": package_info.version.branch,
        # override the base image label
        "com.checkmk.image_type": "cmk-systemd-image" if systemd else "cmk-image",
    }
    # Add information about CI jobs creating these images for easier debugging
    for env_info_key in ("CI_JOB_NAME", "CI_BUILD_NUMBER", "CI_BUILD_URL"):
        if env_info_value := os.environ.get(env_info_key):
            container_label[f"com.checkmk.{env_info_key.lower()}"] = env_info_value

    with _start(
        client,
        # TODO: Re-enable using dedicated container names, the following causes name conflicts:
        # name=f"testbase-{container_name_suffix(distro_name, docker_tag)}",
        image=base_image_name_with_tag,
        labels=container_label,
        command=["tail", "-f", "/dev/null"],  # keep running
        host_config=client.api.create_host_config(
            cap_add=["SYS_ADMIN"],
            # Why unconfined? see https://github.com/moby/moby/issues/16429
            security_opt=["apparmor:unconfined"],
            binds=_image_build_binds(),
        ),
    ) as container:
        logger.info(
            "Building in container %s (from [%s])",
            container.short_id,
            base_image_name_with_tag,
        )
        _prepare_testuser(container, _TESTUSER)
        # Ensure we can make changes to the git directory (not persisting it outside of the container)
        _prepare_git_overlay(container, "/git-lowerdir", "/git", username=_TESTUSER)
        _prepare_virtual_environment(container, container_env, username=_TESTUSER)
        _persist_virtual_environment(container, container_env)
        if systemd:
            _prepare_systemd(container, distro_name)
        logger.info("Install Checkmk version")
        _exec_run(
            container,
            ["scripts/run-uvenv", "/git/tests/scripts/install-cmk.py"],
            workdir="/git",
            environment={**container_env, "SKIP_MAKEFILE_CALL": "1"},
            stream=True,
        )
        if systemd:
            # install-cmk.py replaced systemctl by /bin/true, because this build container
            # runs no systemd. The image is meant to boot one, so put the binary back.
            _restore_systemctl(container)

        logger.info("Check whether or not installation was OK")
        _exec_run(container, ["ls", "/omd/versions/default"], workdir="/")

        # Now get the hash of the used Checkmk package from the container image and add it to the
        # image labels.
        logger.info("Get Checkmk package hash")
        _exit_code, output = container.exec_run(
            [
                "cat",
                str(package_hash_path(package_info.version.version, package_info.edition)),
            ],
        )
        assert isinstance(output, bytes)  # stream/socket/demux not used above
        hash_entry = output.decode("ascii").strip()
        logger.info("Checkmk package hash entry: %s", hash_entry)

        logger.info("Stopping build container")
        container.stop()
        tmp_image = container.commit()

        new_labels = container.labels.copy()
        new_labels["com.checkmk.cmk_hash"] = hash_entry

        logger.info("Finalizing image")
        labeled_container = client.containers.run(tmp_image, labels=new_labels, detach=True)
        image = labeled_container.commit(image_name_with_tag)
        labeled_container.remove(v=True, force=True)

        logger.info("Commited image [%s] (%s)", image_name_with_tag, image.short_id)
        if not use_local_package and not package_info.version.is_release_candidate():
            try:
                logger.info(
                    "Uploading [%s] to registry (%s)",
                    image_name_with_tag,
                    image.short_id,
                )
                client.images.push(image_name_with_tag)
                logger.info("  Upload complete")
            except docker.errors.APIError as exc:
                logger.warning("  An error occurred")
                _handle_api_error(exc)
        else:
            logger.info("Skipping upload to registry (%s)", image.short_id)

    return image_name_with_tag


def _is_based_on_current_base_image(
    image: docker.models.images.Image, base_image: docker.models.images.Image | None
) -> bool:
    logger.info("  Check whether or not image is based on the current base image")
    if base_image is None:
        logger.info("  Base image not available, assuming it's up-to-date")
        return False

    image_base_hash = image.labels.get("com.checkmk.base_image_hash")
    if base_image.short_id != image_base_hash:
        logger.info(
            "  Is based on an outdated base image (%s), current is (%s)",
            image_base_hash,
            base_image.short_id,
        )
        return False

    logger.info("  Is based on current base image (%s)", base_image.short_id)
    return True


def _is_using_current_cmk_package(image: docker.models.images.Image, version: CMKVersion) -> bool:
    logger.info("  Check whether or not image is using the current Checkmk package")

    cmk_hash_entry = image.labels.get("com.checkmk.cmk_hash")
    if not cmk_hash_entry:
        logger.info("  Checkmk package hash label missing (com.checkmk.cmk_hash). Trigger rebuild.")
        return False

    cmk_hash_image, package_name_image = cmk_hash_entry.split()
    logger.info(
        "  CMK hash of image (%s): %s (%s)",
        image.short_id,
        cmk_hash_image,
        package_name_image,
    )
    cmk_hash_current = get_current_cmk_hash_for_artifact(version, package_name_image)
    logger.info("  Current CMK Hash of artifact: %s (%s)", cmk_hash_current, package_name_image)
    if cmk_hash_current != cmk_hash_image:
        logger.info("  Hashes of docker image and artifact do not match.")
        return False

    logger.info(
        "  Used package hash of image (%s) matches the current one: %s",
        package_name_image,
        cmk_hash_image,
    )
    return True


def get_current_cmk_hash_for_artifact(version: CMKVersion, package_name: str) -> str:
    hash_file_name = f"{package_name}.hash"
    r = requests.get(
        f"https://tstbuilds-artifacts.lan.tribe29.com/{version.version_rc_aware}/{hash_file_name}",
        auth=get_cmk_download_credentials(),
        timeout=30,
    )
    r.raise_for_status()
    hash_name = r.text.split()
    if len(hash_name) != 2:
        raise RuntimeError(f"Received multiple entries in hash file for {package_name}: \n{r.text}")
    _hash, package_name_from_hash_file = hash_name
    if package_name_from_hash_file != package_name:
        raise RuntimeError(
            f"The hash file {hash_file_name}'s content ({package_name_from_hash_file}) does not "
            f"match the expected package name ({package_name})"
        )
    return _hash


def _image_build_binds() -> dict[str, Mapping[str, str]]:
    """This function is left here in case we need different handling for
    image builds. Currently we don't"""
    if "WORKSPACE" in os.environ:
        logger.info("WORKSPACE set to %s", os.environ["WORKSPACE"])
    else:
        logger.info("WORKSPACE not set")
    return _runtime_binds()


def _git_repos() -> dict[str, Mapping[str, str]]:
    checkout_dir = repo_path()
    return {
        # This ensures that we can also work with git-worktrees.
        # For this, the original git repository needs to be mapped into the container as well.
        **{path: {"bind": path, "mode": "ro"} for path in git_essential_directories(checkout_dir)},
        # To get access to the test scripts and for updating the version from
        # the current git checkout. Will also be used for updating the image with
        # the current git state
        checkout_dir.as_posix(): {"bind": "/git-lowerdir", "mode": "ro"},
    }


def _runtime_binds() -> dict[str, Mapping[str, str]]:
    return {
        **_git_repos(),
        # Credentials file for fetching the package from the download server. Used by
        # testlib/common/version.py in case the version package needs to be downloaded
        # For whatever reason the image can not be started when nothing is mounted
        # at the file mount that was used while building the image. This is not
        # really needed during runtime of the test. We could mount any file.
        (Path(os.environ["HOME"]) / ".cmk-credentials").as_posix(): {
            "bind": "/etc/.cmk-credentials",
            "mode": "ro",
        },
    }


def _container_env(package_info: CMKPackageInfo) -> dict[str, str]:
    # In addition to the ones defined here, some environment vars, like "DISTRO" are added through
    # the docker image
    env = {
        "LANG": "C",
        "VERSION": package_info.version.version_spec,
        "EDITION": package_info.edition.short,
        "BRANCH": package_info.version.branch,
        "TEST_FILTER": os.environ.get("TEST_FILTER", ""),
        "FAKED_ARTIFACTS": os.environ.get("FAKED_ARTIFACTS", ""),
        "RESULT_PATH": "/results",
        "CI": os.environ.get("CI", ""),
        "CI_NODE_NAME": os.environ.get("CI_NODE_NAME", ""),
        "CI_WORKSPACE": os.environ.get("CI_WORKSPACE", ""),
        "CI_JOB_NAME": os.environ.get("CI_JOB_NAME", ""),
        "CI_BUILD_NUMBER": os.environ.get("CI_BUILD_NUMBER", ""),
        "CI_BUILD_URL": os.environ.get("CI_BUILD_URL", ""),
        # Write to this result path by default (may be overridden e.g. by integration tests)
        "PYTEST_ADDOPTS": os.environ.get("PYTEST_ADDOPTS", "") + " --junitxml=/results/junit.xml",
        "OTEL_SDK_DISABLED": os.environ.get("OTEL_SDK_DISABLED", "true"),
        "OTEL_EXPORTER_OTLP_ENDPOINT": os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
    }
    # Add all variables prefixed with QA_
    env.update({var: val for var, val in os.environ.items() if var.startswith("QA_")})
    return env


class CreateContainerKwargs(TypedDict, total=False):
    command: str | list[str]
    hostname: str
    user: str | int
    detach: bool
    stdin_open: bool
    tty: bool
    ports: list[int]
    environment: dict[str, str] | list[str]
    volumes: str | list[str]
    network_disabled: bool
    name: str
    entrypoint: str | list[str]
    working_dir: str
    domainname: str
    host_config: dict[str, object]
    mac_address: str
    labels: dict[str, str] | list[str]
    stop_signal: str
    networking_config: dict[str, object]
    healthcheck: dict[str, object]
    stop_timeout: int
    runtime: str
    use_config_proxy: bool
    platform: str


@contextmanager
def _start(
    client: docker.DockerClient, image: str, **kwargs: Unpack[CreateContainerKwargs]
) -> Iterator[docker.models.containers.Container]:
    logger.info("Start new container from [%s] (Args: %s)", image, kwargs)

    try:
        client.images.get(image)
    except docker.errors.ImageNotFound:
        raise Exception("Image [%s] could not be found locally" % image)

    # Start the container with lowlevel API to be able to attach with a debug shell
    # after initialization
    container_id = client.api.create_container(image=image, **kwargs)["Id"]
    client.api.start(container_id)
    c = client.containers.get(container_id)

    logger.info("Container ID: %s", c.short_id)

    logger.info("Container is ready")

    try:
        yield c
    finally:
        # Do not leave inactive containers and anonymous volumes behind
        if is_cleanup_enabled():
            c.stop()
            c.remove(v=True, force=True)


class ContainerExecKwargs(TypedDict, total=False):
    stdout: bool
    stderr: bool
    stdin: bool
    tty: bool
    privileged: bool
    environment: dict[str, str] | list[str]
    workdir: str
    stream: bool


def _exec_run(
    c: docker.models.containers.Container,
    cmd: str | Sequence[str],
    check: bool = True,
    user: str = "",
    **kwargs: Unpack[ContainerExecKwargs],
) -> int:
    cmd_list = shlex.split(cmd) if isinstance(cmd, str) else cmd
    cmd_str = subprocess.list2cmdline(cmd_list)

    if kwargs:
        logger.info("Execute in container %s: %r (kwargs: %r)", c.short_id, cmd_str, kwargs)
    else:
        logger.info("Execute in container %s: %r", c.short_id, cmd_str)

    result = container_exec(c, cmd_list, user=user, **kwargs)

    if kwargs.get("stream"):
        returncode = result.communicate(line_prefix=b"%s: " % c.short_id.encode("ascii"))
    else:
        returncode = result.poll()
    if check and returncode != 0:
        raise RuntimeError(f"Command `{cmd_str}` returned with nonzero exit code")
    return returncode


def container_exec(
    container: docker.models.containers.Container,
    cmd: str | Sequence[str],
    user: str = "",
    stdout: bool = True,
    stderr: bool = True,
    stdin: bool = False,
    tty: bool = False,
    privileged: bool = False,
    environment: dict[str, str] | list[str] | None = None,
    workdir: str | None = None,
    stream: Literal[True, False] = False,
) -> ContainerExec:
    """
    An enhanced version of #docker.Container.exec_run() which returns an object
    that can be properly inspected for the status of the executed commands.

    Taken from https://github.com/docker/docker-py/issues/1989. Thanks!
    """

    assert container.client is not None, "Container has no associated client"

    exec_id: str = container.client.api.exec_create(
        container.id,
        cmd,
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        tty=tty,
        privileged=privileged,
        user=user,
        environment=environment,
        workdir=workdir,
    )["Id"]

    output = container.client.api.exec_start(
        exec_id, tty=tty, stream=stream, detach=False, socket=False, demux=False
    )

    return ContainerExec(container.client, exec_id, output)


class ContainerExec:
    def __init__(
        self, client: docker.DockerClient, container_id: str, output: Iterable[bytes] | bytes
    ) -> None:
        self.client = client
        self.id = container_id
        self.output = output

    def inspect(self) -> Mapping[str, Any]:
        return self.client.api.exec_inspect(self.id)

    def poll(self) -> int:
        return int(self.inspect()["ExitCode"])

    def communicate(self, line_prefix: bytes = b"") -> int:
        assert not isinstance(self.output, bytes), "Output is not iterable"

        for data in self.output:
            if not data:
                continue

            offset = 0
            while offset < len(data):
                nl = data.find(b"\n", offset)
                if nl >= 0:
                    slce = data[offset : nl + 1]
                    offset = nl + 1
                    sys.stdout.buffer.write(slce)
                    sys.stdout.buffer.write(line_prefix)
                else:
                    slce = data[offset:]
                    offset += len(slce)
                    sys.stdout.buffer.write(slce)
            sys.stdout.flush()
        return self.poll()


def _copy_directory(
    container: docker.models.containers.Container, src_path: Path, dest_path: Path
) -> None:
    logger.info("Copying %s from container to %s", src_path, dest_path)

    tar_stream = BytesIO()
    bits, _stat = container.get_archive(str(src_path))
    for chunk in bits:
        tar_stream.write(chunk)
    tar_stream.seek(0)

    with tarfile.TarFile(fileobj=tar_stream) as tar:
        tar.extractall(str(dest_path), filter="data")


def _prepare_git_overlay(
    container: docker.models.containers.Container,
    lower_path: str,
    target_path: str,
    username: str | None = None,
) -> None:
    """Prevent modification of git checkout volume contents

    Create some tmpfs that is mounted as rw layer over the git checkout
    at /git. All modifications to the git will be lost after the container is
    removed.
    """
    logger.info("Preparing overlay filesystem for %s at %s", lower_path, target_path)
    tmpfs_path = "/git-rw"
    upperdir_path = "%s/upperdir" % tmpfs_path
    workdir_path = "%s/workdir" % tmpfs_path

    # Create mountpoints
    _exec_run(container, ["mkdir", "-p", tmpfs_path, target_path])

    # Prepare the tmpfs as base for the rw-overlay and workdir
    _exec_run(container, ["mount", "-t", "tmpfs", "tmpfs", tmpfs_path])

    # Create directory structure for the overlay
    _exec_run(container, ["mkdir", "-p", upperdir_path, workdir_path])

    # Finally add the overlay mount
    _exec_run(
        container,
        [
            "mount",
            "-t",
            "overlay",
            "overlay",
            "-o",
            f"lowerdir={lower_path},upperdir={upperdir_path},workdir={workdir_path}",
            target_path,
        ],
    )

    # remove any broken links in the repository (e.g. invalid bazel cache references)
    _exec_run(container, ["find", target_path, "-maxdepth", "1", "-xtype", "l", "-delete"])

    # target_path belongs to root, but its content belong to testuser. Newer git versions don't like
    # that by default, so we explicitly say that this is ok.
    _exec_run(
        container,
        [
            "git",
            "config",
            "--global",
            "--add",
            "safe.directory",
            target_path,
        ],
    )

    if username:
        _exec_run(container, ["chown", f"{username}:{username}", target_path])


def _prepare_testuser(container: docker.models.containers.Container, username: str) -> None:
    """Setup the environment for use with the testuser

    Make sure all relevant files are owned by testuser and allow passwordless sudo, which is
    required for tests that need to install packages or modify the system configuration.
    """
    uid = str(os.getuid())
    gid = str(os.getgid())

    # On RHEL-based distros (AlmaLinux, etc.), the default PAM config includes pam_sss.so,
    # which is currently failing with the following error (see CMK-27940):
    # "PAM account management error: Authentication service cannot retrieve authentication info".
    # This is due to the usage of 'apparmor=unconfined' security option when running the container.
    # Here we insert a permissive PAM account rule in the affected PAM config files so the account
    # check passes before reaching pam_sss.so. This covers both sudo and crontab (crond).
    _exec_run(
        container,
        [
            "bash",
            "-c",
            (
                "for f in /etc/pam.d/sudo /etc/pam.d/crond; do"
                ' if [ -f "$f" ]; then'
                " sed -i '1 a account sufficient pam_permit.so' \"$f\";"
                " fi;"
                " done"
            ),
        ],
        check=False,
    )

    # Ubuntu 24.04+ base images ship with a pre-created 'ubuntu' user at UID/GID 1000.
    # If the host user runs at that UID/GID, groupadd/useradd would silently fail (check=False),
    # leaving testuser uncreated and causing the subsequent chown to fail.
    # Remove any conflicting user/group before proceeding.
    _exec_run(
        container,
        [
            "bash",
            "-c",
            (
                f"existing=$(getent passwd {uid} | cut -d: -f1); "
                f'[ -n "$existing" ] && userdel -f "$existing" || true'
            ),
        ],
        check=True,
    )
    _exec_run(
        container,
        [
            "bash",
            "-c",
            (
                f"existing=$(getent group {gid} | cut -d: -f1); "
                f'[ -n "$existing" ] && groupdel "$existing" || true'
            ),
        ],
        check=True,
    )
    _exec_run(container, ["groupadd", "-g", gid, username], check=True)
    _exec_run(
        container,
        ["useradd", "-m", "-u", uid, "-g", gid, "-s", "/bin/bash", username],
        check=False,
    )
    _exec_run(
        container,
        ["bash", "-c", f'echo "{username} ALL=(ALL) NOPASSWD: ALL">>/etc/sudoers.d/{username}'],
    )

    _exec_run(container, ["mkdir", "-p", f"/home/{username}/.cache"])
    _exec_run(container, ["chown", "-R", f"{username}:{username}", f"/home/{username}"])

    _exec_run(container, ["mkdir", "-p", "/results"])
    _exec_run(container, ["chown", "-R", f"{username}:{username}", "/results"])


def _prepare_virtual_environment(
    container: docker.models.containers.Container,
    container_env: dict[str, str],
    username: str = "",
) -> None:
    """Ensure the virtual environment is ready for use

    Because the virtual environment are in the /git path (which is not persisted),
    the initialized virtual environment will be copied to /.venv, which is
    persisted with the image. The test containers may use them.
    """
    _cleanup_previous_virtual_environment(container, container_env)
    _setup_virtual_environment(container, container_env, username)


def _setup_virtual_environment(
    container: docker.models.containers.Container,
    container_env: dict[str, str],
    user: str = "",
    check: bool = True,
) -> None:
    logger.info("Prepare virtual environment")
    returncode = _exec_run(
        container,
        ["make", ".venv"],
        check=check,
        user=user,
        workdir="/git",
        environment=container_env,
        stream=True,
    )
    if returncode != 0:
        logger.warning("make .venv exited with %d, keeping the existing venv", returncode)

    _exec_run(container, ["test", "-d", "/git/.venv"])


def _cleanup_previous_virtual_environment(
    container: docker.models.containers.Container, container_env: dict[str, str]
) -> None:
    """Delete existing .venv

    When the git is mounted to the test container for a node which already created it's virtual
    environments in the git directory, the venv may be incompatible with the containers OS. Clean
    up, just to be sure.

    The copied .venv will be used by _reuse_persisted_virtual_environment().
    """
    logger.info("Cleanup previous virtual environments")
    _exec_run(
        container,
        ["rm", "-rf", ".venv"],
        workdir="/git",
        environment=container_env,
        stream=True,
    )

    _exec_run(container, ["test", "-n", "/.venv"])


def _persist_virtual_environment(
    container: docker.models.containers.Container, container_env: dict[str, str]
) -> None:
    """Persist the used venv in container image

    Copy the virtual environment that was used during image creation from /git/.venv (not persisted)
    to /.venv (persisted in image). This will be reused later during test executions.
    """
    logger.info("Persisting virtual environments for later use")
    _exec_run(
        container,
        ["rsync", "-aR", ".venv", "/"],
        workdir="/git",
        environment=container_env,
        stream=True,
    )

    _exec_run(container, ["test", "-d", "/.venv"])


def _reuse_persisted_virtual_environment(
    container: docker.models.containers.Container, container_env: dict[str, str], test_user: str
) -> None:
    """Copy /.venv to /git/.venv to reuse previous venv during testing"""
    if (
        _exec_run(
            container,
            ["test", "-d", "/.venv"],
            workdir="/git",
            environment=container_env,
            check=False,
        )
        == 0
    ):
        logger.info("Restore previously created virtual environment")
        _exec_run(
            container,
            ["rsync", "-a", f"--chown={test_user}:{test_user}", "/.venv", "/git"],
            workdir="/git",
            environment=container_env,
            stream=True,
        )

    if _mirror_reachable():
        #  Only try to update when the mirror is available, otherwise continue with the current
        #  state, which is good for the most of the time.
        _setup_virtual_environment(container, container_env, test_user, check=False)


def _mirror_reachable() -> bool:
    try:
        requests.get(_DOCKER_REGISTRY_URL, timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        return False
