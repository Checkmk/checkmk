#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.agent_hosts import piggyback_host_from_dummy_generator
from tests.testlib.site import Site, SiteFactory


@pytest.mark.skip_if_edition("raw")
def test_locked_host_attributes_after_site_copy(site: Site, site_factory: SiteFactory) -> None:
    """Test that locked host attributes are locked after site copy.

    Steps:
    1. Create a site with piggyback hosts using a dummy generator.
    2. Delete the DCD connector and datasource rule to ensure piggyback hosts are copied.
    3. Copy the site to a new site.
    4. Verify that the piggyback hosts in the copied site have the expected locked attributes.
    """
    host_name = "test-copy-site"
    pb_host_count = 5

    with piggyback_host_from_dummy_generator(
        site, host_name, pb_host_count=pb_host_count
    ) as piggyback_info:
        # Delete the original DCD connector and datasource rule before copying the site
        # to ensure that piggyback hosts are copied from the original site
        # instead of discovered again in the copied site.
        site.openapi.dcd.delete(piggyback_info.dcd_id)
        site.openapi.rules.delete(piggyback_info.datasource_id)
        site.openapi.changes.activate_and_wait_for_completion()

        with site_factory.copy_site(site, "copy") as copied_site:
            expected_locked_attributes = (
                "site",
                "tag_address_family",
                "tag_agent",
                "tag_piggyback",
                "tag_snmp_ds",
            )

            for host_name in piggyback_info.piggybacked_hosts:
                host = copied_site.openapi.hosts.get(host_name)

                assert host is not None, f"Host '{host_name}' not found in site '{copied_site.id}'"

                host_attributes = host[0].get("attributes", {})

                locked_attributes = host_attributes.get("locked_attributes", [])
                locked_by = host_attributes.get("locked_by", {})

                assert locked_by.get("site_id", "") == copied_site.id, (
                    f"Expected host attributes to be locked by site: '{copied_site.id}'!"
                )

                for attr in expected_locked_attributes:
                    assert attr in locked_attributes, (
                        f"Attribute '{attr}' not locked for host '{host_name}'. "
                        f"Actual locked attributes: {locked_attributes}"
                    )
