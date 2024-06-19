#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.pytest_helpers.marks import skip_if_not_cloud_edition
from tests.testlib.repo import current_base_branch_name, qa_test_data_path
from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import get_services_with_status
from tests.testlib.version import CMKVersion, get_min_version, version_from_env

from tests.update.conftest import DUMPS_DIR, inject_dumps

from cmk.utils.version import Edition

logger = logging.getLogger(__name__)


@pytest.fixture(name="site_factory", scope="function")
def _site_factory() -> SiteFactory:
    base_version = CMKVersion("2.3.0p4", Edition.CEE)
    return SiteFactory(version=base_version, prefix="")


@pytest.fixture(name="base_site", scope="function")
def _base_site(site_factory: SiteFactory) -> Iterator[Site]:
    site_name = "update_central"
    yield from site_factory.get_test_site(site_name, save_results=False)


@pytest.fixture(name="site_factory_demo", scope="function")
def _site_factory_demo():
    base_version = CMKVersion("2.3.0p4", Edition.CCE)
    return SiteFactory(version=base_version, prefix="")


@pytest.fixture(name="base_site_demo", scope="function")
def _base_site_demo(site_factory_demo):
    # Note: to access the UI of the "play" site go to http://localhost/play/check_mk/login.py?_admin
    site_name = "play"
    yield from site_factory_demo.get_test_site(site_name, save_results=False)


@pytest.mark.cee
def test_update_from_backup(site_factory: SiteFactory, base_site: Site) -> None:
    backup_path = qa_test_data_path() / Path("update/backups/update_central_2.3.0p4_backup.tar.gz")
    assert backup_path.exists()

    base_site = site_factory.restore_site_from_backup(backup_path, base_site.id, reuse=True)
    hostnames = [_.get("id") for _ in base_site.openapi.get_hosts()]
    inject_dumps(base_site, DUMPS_DIR)

    logger.info("Discovering services and waiting for completion...")
    base_site.openapi.bulk_discover_services_and_wait_for_completion(
        [str(hostname) for hostname in hostnames]
    )
    base_site.openapi.activate_changes_and_wait_for_completion()

    base_services = {}
    base_ok_services = {}
    for hostname in hostnames:
        base_site.schedule_check(hostname, "Check_MK")
        base_services[hostname] = base_site.get_host_services(hostname)
        base_ok_services[hostname] = get_services_with_status(base_services[hostname], 0)

        assert len(base_ok_services[hostname]) > 0

    target_version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_base_branch_name(),
    )
    assert target_version.edition == Edition.CEE, "This test works with CEE only"

    min_version = get_min_version()
    target_site = site_factory.interactive_update(base_site, target_version, min_version)

    target_services = {}
    target_ok_services = {}
    for hostname in hostnames:
        target_site.schedule_check(hostname, "Check_MK")
        target_services[hostname] = target_site.get_host_services(hostname)
        target_ok_services[hostname] = get_services_with_status(base_services[hostname], 0)

        not_found_services = [
            service
            for service in base_services[hostname]
            if service not in target_services[hostname]
        ]

        err_msg = (
            f"In the {hostname} host the following services were found in base-version but not in "
            f"target-version: "
            f"{not_found_services}"
        )
        assert len(target_services[hostname]) >= len(base_services[hostname]), err_msg

        not_ok_services = [
            service
            for service in base_ok_services[hostname]
            if service not in target_ok_services[hostname]
        ]
        err_msg = (
            f"In the {hostname} host the following services were `OK` in base-version but not in "
            f"target-version: "
            f"{not_ok_services}"
            f"\nDetails: {[(s, target_services[hostname][s].summary) for s in not_ok_services]})"
        )
        assert base_ok_services[hostname].issubset(target_ok_services[hostname]), err_msg


@pytest.mark.cce
@skip_if_not_cloud_edition
@pytest.mark.skip("Update process currently broken. See CMK-17449.")
def test_update_from_backup_demo(
    site_factory_demo: SiteFactory, base_site_demo: Site, request: pytest.FixtureRequest
) -> None:
    store_lost_services = request.config.getoption(name="--store-lost-services")
    lost_services_path = Path(__file__).parent.resolve() / Path("lost_services_demo.json")

    # MKPs broken: disabled in the demo site via: 'mkp disable play_checkmk 0.0.1' TODO: investigate
    backup_path = qa_test_data_path() / Path("update/backups/play_2.3.0p4_backup.tar.gz")
    assert backup_path.exists()

    base_site = site_factory_demo.restore_site_from_backup(
        backup_path, base_site_demo.id, reuse=True
    )

    base_hostnames = [_.get("id") for _ in base_site.openapi.get_hosts()]

    base_services = {}
    for hostname in base_hostnames:
        base_services[hostname] = base_site.get_host_services(hostname)

        assert len(base_services[hostname]) > 0, f"No services found in host {hostname}"

    target_version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CCE,
        fallback_branch=current_base_branch_name(),
    )
    assert target_version.edition == Edition.CCE, "This test works with CCE only"

    site_factory_demo = SiteFactory(
        version=target_version,
        prefix="",
        update=True,
        update_conflict_mode="keepold",
        enforce_english_gui=False,
    )

    base_site.stop()
    target_site = site_factory_demo.get_site(  # perform update via CLI
        base_site.id, init_livestatus=False, activate_changes=False
    )
    target_site.openapi.activate_changes_and_wait_for_completion()

    assert target_site.is_running()
    assert target_site.version.version == target_version.version, "Version mismatch during update!"

    target_hostnames = [_.get("id") for _ in base_site.openapi.get_hosts()]

    target_services = {}
    current_lost_services = {}
    missed_services = {}

    with open(lost_services_path) as json_file:
        known_lost_services = json.load(json_file)

    for hostname in target_hostnames:
        target_services[hostname] = target_site.get_host_services(hostname)

        current_lost_services[hostname] = [
            service
            for service in base_services[hostname]
            if service not in target_services[hostname]
        ]

        if current_lost_services[hostname]:
            logger.warning(
                "In the %s host the following services were found in base-version "
                "but not in target-version: %s",
                hostname,
                current_lost_services[hostname],
            )

        if store_lost_services:
            # skip assertion if flag given
            continue

        missed_services[hostname] = [
            service
            for service in current_lost_services[hostname]
            if service not in known_lost_services[hostname]
        ]

        err_msg = (
            f"In the {hostname} host the following services were not expected to be missing "
            f"{missed_services[hostname]}"
        )
        assert not missed_services[hostname], err_msg

    if store_lost_services:
        logger.info("Storing lost services as JSON reference...")
        with open(lost_services_path, "w") as file:
            json.dump(current_lost_services, file, indent=4)
