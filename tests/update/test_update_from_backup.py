import logging
import os
from pathlib import Path

import pytest

from tests.testlib.site import SiteFactory
from tests.testlib.utils import current_base_branch_name
from tests.testlib.version import CMKVersion
from tests.update.conftest import (
    BaseVersions,
    get_host_services,
    get_services_with_status,
)

from cmk.utils.version import Edition

logger = logging.getLogger(__name__)


@pytest.mark.skipif(
    os.environ.get("DISTRO") in ("sles-15sp4", "sles-15sp5"),
    reason="Test currently failing for missing `php7`. "
    "This will be fixed starting from base-version 2.2.0p8",
)
def test_update_from_backup() -> None:
    site_name = "update_central"
    backup_path = Path(__file__).parent.resolve() / Path("backups/update_central_backup.tar.gz")
    base_version = CMKVersion("2.2.0", Edition.CEE, current_base_branch_name())
    target_version = CMKVersion(CMKVersion.DAILY, Edition.CEE, current_base_branch_name())
    min_version = CMKVersion(BaseVersions.MIN_VERSION, Edition.CEE, current_base_branch_name())

    sf = SiteFactory(version=base_version, prefix="")
    base_site = sf.restore_site_from_backup(backup_path, site_name)

    assert base_site.is_running()

    hostnames = [_.get("id") for _ in base_site.openapi.get_hosts()]

    # TODO: introduce agent installation and hosts registration

    base_services = {}
    base_ok_services = {}
    for hostname in hostnames:
        base_site.schedule_check(hostname, "Check_MK")
        base_services[hostname] = get_host_services(base_site, hostname)
        base_ok_services[hostname] = get_services_with_status(base_services[hostname], 0)

    target_site = sf.interactive_update(base_site, target_version, min_version)

    target_services = {}
    target_ok_services = {}
    for hostname in hostnames:
        target_site.schedule_check(hostname, "Check_MK")
        target_services[hostname] = get_host_services(target_site, hostname)
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
