import logging
from pathlib import Path
from pprint import pformat

from tests.testlib.site import SiteFactory
from tests.testlib.utils import current_base_branch_name
from tests.testlib.version import CMKVersion

from cmk.utils.version import Edition

from tests.plugins_integration.checks import get_host_names

logger = logging.getLogger(__name__)


def test_update_from_backup() -> None:
    site_name = "update_central"
    backup_path = Path(__file__).parent.resolve() / Path("backups/update_central_backup.tar.gz")
    base_version = CMKVersion("2.2.0", Edition.CEE, current_base_branch_name())
    target_version = CMKVersion(CMKVersion.DAILY, Edition.CEE, current_base_branch_name())

    sf = SiteFactory(version=base_version, prefix="")
    base_site = sf.restore_site_from_backup(backup_path, site_name)

    assert base_site.is_running()

    hostnames = get_host_names(base_site)

    # TODO: introduce agent installation and hosts registration

    # TODO: unify data retrieval with test_update.py
    base_services = {}
    for hostname in hostnames:
        logger.info("Retrieving services from %s host...", hostname)
        services = []
        for service in base_site.openapi.get_host_services(hostname, columns=["state"]):
            services.append(service["title"])

        base_services[hostname] = services
        logger.debug("Found services: %s", pformat(base_services[hostname]))

    target_site = sf.update_site(base_site, target_version)

    # TODO: unify data retrieval with test_update.py
    target_services = {}
    for hostname in hostnames:
        logger.info("Retrieving services from %s host...", hostname)
        services = []
        for service in target_site.openapi.get_host_services(hostname, columns=["state"]):
            services.append(service["title"])

        target_services[hostname] = services
        logger.debug("Found services: %s", pformat(base_services[hostname]))

    for hostname in hostnames:
        assert base_services[hostname].sort() == target_services[hostname].sort()

    logger.info("Removing test-site...")
    target_site.rm()
