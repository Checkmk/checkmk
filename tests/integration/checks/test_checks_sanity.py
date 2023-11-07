import logging
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

logger = logging.getLogger(__name__)


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="function")
def _installed_agent_ctl_in_unknown_state(site: Site, tmp_path: Path) -> Path:
    if site.version.is_raw_edition():
        pytest.skip("Downloading the agent in raw edition currently broken")  # TODO: investigate
    return download_and_install_agent_package(site, tmp_path)


@pytest.fixture(name="agent_ctl", scope="function")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with (
        clean_agent_controller(installed_agent_ctl_in_unknown_state),
        agent_controller_daemon(installed_agent_ctl_in_unknown_state),
    ):
        yield installed_agent_ctl_in_unknown_state


@pytest.fixture(name="host_services", scope="function")
def _host_services(site: Site, agent_ctl: Path) -> Iterator[dict]:
    hostname = HostName("host-0")
    site.openapi.create_host(hostname, attributes={"ipaddress": site.http_address, "site": site.id})
    site.activate_changes_and_wait_for_core_reload()

    try:
        register_controller(agent_ctl, site, hostname, site_address="127.0.0.1")
        wait_until_host_receives_data(site, hostname)
        site.openapi.bulk_discover_services([str(hostname)], wait_for_completion=True)
        site.openapi.activate_changes_and_wait_for_completion()
        site.reschedule_services(hostname)

        yield site.get_host_services(hostname)

    except Exception:
        logger.error("Failed to retrieve services from the host.")
        raise

    finally:
        site.openapi.delete_host(hostname)
        site.activate_changes_and_wait_for_core_reload()


def test_checks_sanity(host_services: dict) -> None:
    """Assert sanity of the discovered checks."""
    ok_services = get_services_with_status(host_services, 0)
    not_ok_services = [service for service in host_services if service not in ok_services]
    err_msg = f"The following services are not in state 0: {not_ok_services}"

    assert len(host_services) == len(get_services_with_status(host_services, 0)) > 0, err_msg
