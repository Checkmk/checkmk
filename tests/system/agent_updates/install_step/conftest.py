#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Fixtures for the cases of the privileged install step.

The suite installs the generic package, which uses the classic layout. The installer units exist
only in a package baked for the single directory deployment with the integrated updater, so these
cases install such a package for their own duration and put the generic one back afterwards.
"""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from cmk.ruleset_matcher.definition import RuleGroup
from tests.system.agent_updates.install_step._agent import (
    AGENT_USER,
    generate_signing_key,
    INSTALLATION_DIRECTORY,
    INSTALLER_SOCKET_UNIT,
    IntegratedUpdaterAgent,
    SigningKey,
)
from tests.system.agent_updates.install_step._installer import (
    build_marker_package,
    MarkerPackage,
    remove_marker_package,
)
from tests.system.agent_updates.install_step._units import reset_failed_instances
from tests.testlib.system.agent import (
    bake_agents,
    download_agent_package,
    get_package_type,
    install_agent_package,
    purge_agent_package,
)
from tests.testlib.system.host_under_test import HostUnderTest
from tests.testlib.system.site import Site
from tests.testlib.system.systemd import wait_for_unit_active

_SIGNATURE_KEY_ID = "cmk-40788"
_SIGNATURE_KEYS_FILE = Path("etc", "check_mk", "multisite.d", "wato", "agent_signature_keys.mk")


@contextmanager
def _rules(site: Site, rules: Iterable[tuple[str, object]]) -> Iterator[None]:
    """Create the given agent rules and activate them, then delete them again on exit.

    The site serves the whole suite. A rule left behind would change what any later bake on the
    site produces.
    """
    rule_ids = [site.openapi.rules.create(value, ruleset_name) for ruleset_name, value in rules]
    try:
        site.activate_changes_and_wait_for_core_reload()
        yield
    finally:
        for rule_id in rule_ids:
            site.openapi.rules.delete(rule_id)
        site.activate_changes_and_wait_for_core_reload()


@contextmanager
def _signature_key_on_site(site: Site, signing_key: SigningKey) -> Iterator[None]:
    """Make signing_key a signature key of the site, then delete the key file again on exit."""
    keys = {_SIGNATURE_KEY_ID: signing_key.key.model_dump()}
    site.write_file(_SIGNATURE_KEYS_FILE, f"agent_signature_keys.update({keys!r})\n")
    try:
        yield
    finally:
        site.delete_file(_SIGNATURE_KEYS_FILE)


def _bake_integrated_updater_package(
    site: Site, host: HostUnderTest, trusted_key: SigningKey, target_dir: Path
) -> Path:
    """Bake and download a package with the integrated updater, which trusts only trusted_key.

    The rules and the key are deleted again once the package is downloaded, so that every case
    starts from a site without them.
    """
    with (
        _signature_key_on_site(site, trusted_key),
        _rules(
            site,
            [
                (
                    RuleGroup.AgentConfig("customize_agent_package"),
                    {
                        "deployment_mode": (
                            "root",
                            {"user": AGENT_USER, "creation_options": "auto"},
                        ),
                        "directory": {"installation_directory": str(INSTALLATION_DIRECTORY)},
                        "agent_controller_arch": "x86",
                    },
                ),
                (
                    RuleGroup.AgentConfig("cmk_update_agent"),
                    {
                        "activated": "integrated_only",
                        "signature_keys": [trusted_key.certificate],
                    },
                ),
            ],
        ),
    ):
        bake_agents(site)
        return download_agent_package(site, get_package_type(host), target_dir)


def _remove_agent(host: HostUnderTest) -> None:
    """Remove the package together with the agent user and the installation directory.

    The two layouts disagree about the home directory of the agent user, and its maintainer
    scripts keep an existing user as it is. A switch between the layouts therefore has to start
    without the user.
    """
    purge_agent_package(host=host)
    # A process of the agent user that the purge did not stop keeps userdel from removing the user.
    host.run(["pkill", "-KILL", "-u", AGENT_USER], sudo=True, check=False)
    if host.run(["id", AGENT_USER], check=False).returncode == 0:
        host.run(["userdel", AGENT_USER], sudo=True)
    if host.run(["getent", "group", AGENT_USER], check=False).returncode == 0:
        host.run(["groupdel", AGENT_USER], sudo=True)
    host.run(["rm", "-rf", INSTALLATION_DIRECTORY.as_posix()], sudo=True)


@pytest.fixture(name="trusted_key", scope="package")
def _trusted_key() -> SigningKey:
    return generate_signing_key("trusted")


@pytest.fixture(name="integrated_updater_agent", scope="package")
def _integrated_updater_agent(
    systemd: None,  # noqa: ARG001
    host: HostUnderTest,
    site: Site,
    agent_package: Path,
    trusted_key: SigningKey,
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[IntegratedUpdaterAgent]:
    """Replace the generic agent package with one baked for the integrated updater, for the
    duration of the test package, and put the generic one back afterwards."""
    if site.edition.is_community_edition():
        pytest.skip("The integrated updater is baked, and the Community edition does not bake")
    package = _bake_integrated_updater_package(
        site, host, trusted_key, tmp_path_factory.mktemp("integrated_updater_package")
    )
    try:
        _remove_agent(host)
        install_agent_package(package, host)
        wait_for_unit_active(host, INSTALLER_SOCKET_UNIT, timeout=10)
        yield IntegratedUpdaterAgent(
            install_dir=INSTALLATION_DIRECTORY / "default", trusted_key=trusted_key
        )
    finally:
        try:
            _remove_agent(host)
        finally:
            install_agent_package(agent_package, host)


@pytest.fixture(name="marker_package")
def _marker_package(host: HostUnderTest, tmp_path: Path) -> Iterator[MarkerPackage]:
    reset_failed_instances(host)
    package = build_marker_package(host, tmp_path)
    yield package
    remove_marker_package(host, package)
    reset_failed_instances(host)
