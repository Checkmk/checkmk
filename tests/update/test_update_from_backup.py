import logging
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.agent import (
    agent_controller_daemon,
    clean_agent_controller,
    download_and_install_agent_package,
    register_controller,
    wait_until_host_receives_data,
)
from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import (
    current_base_branch_name,
    get_services_with_status,
    qa_test_data_path,
)
from tests.testlib.version import CMKVersion
from tests.update.conftest import BaseVersions

from cmk.utils.version import Edition


logger = logging.getLogger(__name__)


@pytest.fixture(name="site_factory", scope="function")
def _site_factory() -> SiteFactory:
    base_version = CMKVersion("2.2.0", Edition.CEE, current_base_branch_name())
    return SiteFactory(version=base_version, prefix="")


@pytest.fixture(name="base_site", scope="function")
def _base_site(site_factory: SiteFactory) -> Iterator[Site]:
    site_name = "update_central"
    yield from site_factory.get_test_site(site_name, save_results=False)


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="function")
def _installed_agent_ctl_in_unknown_state(base_site: Site, tmp_path: Path) -> Path:
    return download_and_install_agent_package(base_site, tmp_path)


@pytest.fixture(name="agent_ctl", scope="function")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with (
        clean_agent_controller(installed_agent_ctl_in_unknown_state),
        agent_controller_daemon(installed_agent_ctl_in_unknown_state),
    ):
        yield installed_agent_ctl_in_unknown_state


@pytest.mark.skipif(
    os.environ.get("DISTRO") in ("sles-15sp4", "sles-15sp5"),
    reason="Test currently failing for missing `php7`. "
    "This will be fixed starting from base-version 2.2.0p8",
)
def test_update_from_backup(site_factory: SiteFactory, base_site: Site, agent_ctl: Path) -> None:
    backup_path = qa_test_data_path() / Path("update/backups/update_central_backup.tar.gz")
    assert backup_path.exists()
    
    base_site = site_factory.restore_site_from_backup(backup_path, base_site.id, reuse=True)
    hostnames = [_.get("id") for _ in base_site.openapi.get_hosts()]

    for hostname in hostnames:
        address = f"127.0.0.{hostnames.index(hostname) + 1}"
        register_controller(agent_ctl, base_site, hostname, site_address=address)
        wait_until_host_receives_data(base_site, hostname)

    logger.info("Discovering services and waiting for completion...")
    base_site.openapi.bulk_discover_services(
        [str(hostname) for hostname in hostnames], wait_for_completion=True
    )
    base_site.openapi.activate_changes_and_wait_for_completion()

    base_services = {}
    base_ok_services = {}
    for hostname in hostnames:
        base_site.schedule_check(hostname, "Check_MK")
        base_services[hostname] = base_site.get_host_services(hostname)
        base_ok_services[hostname] = get_services_with_status(base_services[hostname], 0)

        assert len(base_ok_services[hostname]) > 0

    target_version = CMKVersion(CMKVersion.DAILY, Edition.CEE, current_base_branch_name())
    min_version = CMKVersion(BaseVersions.MIN_VERSION, Edition.CEE, current_base_branch_name())
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
        )
        assert set(base_ok_services[hostname]).issubset(set(target_ok_services[hostname])), err_msg
