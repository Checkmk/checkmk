import re

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import get_services_with_status

from tests.plugins_integration.checks import (
    get_host_names,
    get_piggyback_hosts,
    read_cmk_dump,
    read_disk_dump,
    setup_source_host,
)


def _read_piggyback_hosts_from_dump(dump: str) -> set[str]:
    piggyback_hosts: set[str] = set()
    pattern = r"<<<<(.*?)>>>>"
    matches = re.findall(pattern, dump)
    piggyback_hosts.update(matches)
    piggyback_hosts.discard("")  # '<<<<>>>>' pattern will match an empty string
    return piggyback_hosts


@pytest.mark.skip(reason="Test still WIP.")
@pytest.mark.parametrize("source_host_name", get_host_names())
def test_plugin_piggyback(test_site: Site, source_host_name: str, dcd_connector: None) -> None:
    with setup_source_host(test_site, source_host_name):
        disk_dump = read_disk_dump(source_host_name)
        cmk_dump = read_cmk_dump(source_host_name, test_site, "agent")
        assert disk_dump == cmk_dump != "", "Raw data mismatch!"

        piggyback_hostnames = get_piggyback_hosts(test_site, source_host_name)
        assert set(piggyback_hostnames) == _read_piggyback_hosts_from_dump(disk_dump)

        for hostname in piggyback_hostnames:
            host_services = test_site.get_host_services(hostname)
            ok_services = get_services_with_status(host_services, 0)
            not_ok_services = [service for service in host_services if service not in ok_services]
            err_msg = (
                f"The following services are not in state 0: {not_ok_services} "
                f"(Details: {[host_services[s] for s in not_ok_services]})"
            )
            assert len(host_services) == len(ok_services), err_msg
