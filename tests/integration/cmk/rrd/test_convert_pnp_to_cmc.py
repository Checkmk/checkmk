#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from tests.integration.linux_test_host import create_linux_test_host

from tests.testlib.site import Site

from cmk.ccc.hostaddress import HostAddress

_RELATIVE_PATH_PNP_RRDS = Path("var", "pnp4nagios", "perfdata")
_RELATIVE_PATH_CMC_RRDS = Path("var", "check_mk", "rrd")


@pytest.mark.skip_if_edition("raw", "saas")
def test_convert_pnp_to_cmc(request: pytest.FixtureRequest, site: Site) -> None:
    hostname = HostAddress("test-pnp-to-cmc")
    rule_id_host_rrd_config = rule_id_service_rrd_config = None

    try:
        create_linux_test_host(request, site, hostname)
        site.openapi.service_discovery.run_discovery_and_wait_for_completion("test-pnp-to-cmc")
        rule_id_host_rrd_config = site.openapi.rules.create(
            ruleset_name="cmc_host_rrd_config",
            value={
                "format": "cmc_single",
                "cfs": ["MIN", "MAX", "AVERAGE"],
                "step": 60,
                "rras": [(50.0, 1, 2880), (50.0, 5, 2880), (50.0, 30, 4320), (50.0, 360, 5840)],
            },
        )
        rule_id_service_rrd_config = site.openapi.rules.create(
            ruleset_name="cmc_service_rrd_config",
            value={
                "format": "cmc_single",
                "cfs": ["MIN", "MAX", "AVERAGE"],
                "step": 60,
                "rras": [(50.0, 1, 2880), (50.0, 5, 2880), (50.0, 30, 4320), (50.0, 360, 5840)],
            },
        )
        site.openapi.changes.activate_and_wait_for_completion()

        site.omd("stop")
        _deploy_pnp_temperature_zone_0_files(
            site,
            hostname,
            Path(__file__).parent,
        )
        site.delete_dir(_RELATIVE_PATH_CMC_RRDS / hostname)
        site.run(["cmk-convert-rrds"], check=True)

        assert (
            site.read_file(_RELATIVE_PATH_CMC_RRDS / hostname / "Temperature_Zone_0.info")
            == f"HOST {hostname}\nSERVICE Temperature Zone 0\nMETRICS temp\n"
        )
        assert site.read_file(
            _RELATIVE_PATH_CMC_RRDS / hostname / "Temperature_Zone_0.rrd", encoding=None
        )

    finally:
        site.delete_dir(_RELATIVE_PATH_PNP_RRDS / hostname)
        site.omd("start")
        if rule_id_host_rrd_config:
            site.openapi.rules.delete(rule_id_host_rrd_config)
        if rule_id_service_rrd_config:
            site.openapi.rules.delete(rule_id_service_rrd_config)
        site.openapi.changes.activate_and_wait_for_completion()


def _deploy_pnp_temperature_zone_0_files(
    site: Site,
    hostname: HostAddress,
    our_location: Path,
) -> None:
    filename_xml = "Temperature_Zone_0.xml"
    filename_rrd = "Temperature_Zone_0_temp.rrd"

    raw_xml = (
        (our_location / filename_xml)
        .read_text()
        .format(
            SITE=site.id,
            HOST=hostname,
        )
    )
    raw_rrd = (our_location / filename_rrd).read_bytes()

    site.makedirs(_RELATIVE_PATH_PNP_RRDS / hostname)
    site.write_file(_RELATIVE_PATH_PNP_RRDS / hostname / filename_xml, raw_xml)
    site.write_file(_RELATIVE_PATH_PNP_RRDS / hostname / filename_rrd, raw_rrd)
