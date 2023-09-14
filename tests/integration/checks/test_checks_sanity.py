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
from tests.testlib.site import Site
from tests.testlib.utils import get_services_with_status

from cmk.utils.hostaddress import HostName


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="function")
def _installed_agent_ctl_in_unknown_state(site: Site, tmp_path: Path) -> Path:
    return download_and_install_agent_package(site, tmp_path)


@pytest.fixture(name="agent_ctl", scope="function")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with (
        clean_agent_controller(installed_agent_ctl_in_unknown_state),
        agent_controller_daemon(installed_agent_ctl_in_unknown_state),
    ):
        yield installed_agent_ctl_in_unknown_state


@pytest.mark.skip(reason="Currently failing on Centos and Sles distros. Investigate.")
@pytest.mark.enable_socket
def test_checks_sanity(site: Site, agent_ctl: Path) -> None:
    """Assert sanity of the discovered checks."""
    hostname = HostName("host-0")
    site.openapi.create_host(hostname, attributes={"ipaddress": site.http_address, "site": site.id})
    site.activate_changes_and_wait_for_core_reload()
    register_controller(agent_ctl, site, hostname, site_address="127.0.0.1")
    wait_until_host_receives_data(site, hostname)
    site.openapi.bulk_discover_services([str(hostname)], wait_for_completion=True)
    site.openapi.activate_changes_and_wait_for_completion()
    site.reschedule_services(hostname)

    found_services = site.get_host_services(hostname)
    found_ok_services = get_services_with_status(found_services, 0)
    not_ok_services = [service for service in found_services if service not in found_ok_services]

    err_msg = f"The following services are not in state 0: {not_ok_services}"
    assert len(found_services) == len(get_services_with_status(found_services, 0)) > 0, err_msg
