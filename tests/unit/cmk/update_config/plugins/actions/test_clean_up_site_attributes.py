#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from livestatus import SiteConfiguration, SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.gui.watolib.sites import site_management_registry
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.clean_up_site_attributes import (
    CleanUpSiteAttributes,
)


@pytest.mark.usefixtures("load_config")
def test_clean_up_missing_alias() -> None:
    site_mgmt = site_management_registry["site_management"]
    site_mgmt.save_sites(
        SiteConfigurations(
            {
                SiteId("abc"): SiteConfiguration(  # type: ignore[typeddict-item]
                    {
                        "id": SiteId("abc"),
                        "socket": ("local", None),
                        "disable_wato": True,
                        "disabled": False,
                        "insecure": False,
                        "url_prefix": "/abc/",
                        "multisiteurl": "",
                        "persist": False,
                        "replicate_ec": False,
                        "replication": None,
                        "timeout": 5,
                        "user_login": True,
                        "proxy": None,
                    }
                )
            }
        ),
        activate=False,
        pprint_value=True,
    )

    CleanUpSiteAttributes(
        name="clean_up_site_attributes",
        title="Clean up site connections",
        sort_index=30,
        expiry_version=ExpiryVersion.CMK_300,
    )(logging.getLogger())

    assert site_mgmt.load_sites()[SiteId("abc")]["alias"] == "abc"


@pytest.mark.usefixtures("load_config")
def test_clean_up_missing_socket() -> None:
    site_mgmt = site_management_registry["site_management"]
    site_mgmt.save_sites(
        SiteConfigurations(
            {
                SiteId("abc"): SiteConfiguration(  # type: ignore[typeddict-item]
                    {
                        "id": SiteId("abc"),
                        "alias": "abc",
                        "disable_wato": True,
                        "disabled": False,
                        "insecure": False,
                        "url_prefix": "/abc/",
                        "multisiteurl": "",
                        "persist": False,
                        "replicate_ec": False,
                        "replication": None,
                        "timeout": 5,
                        "user_login": True,
                        "proxy": None,
                    }
                )
            }
        ),
        activate=False,
        pprint_value=True,
    )

    CleanUpSiteAttributes(
        name="clean_up_site_attributes",
        title="Clean up site connections",
        sort_index=30,
        expiry_version=ExpiryVersion.CMK_300,
    )(logging.getLogger())

    assert site_mgmt.load_sites()[SiteId("abc")]["socket"] == ("local", None)


@pytest.mark.usefixtures("load_config")
def test_clean_up_missing_url_prefix() -> None:
    site_mgmt = site_management_registry["site_management"]
    site_mgmt.save_sites(
        SiteConfigurations(
            {
                SiteId("abc"): SiteConfiguration(  # type: ignore[typeddict-item]
                    {
                        "id": SiteId("abc"),
                        "alias": "abc",
                        "socket": ("local", None),
                        "disable_wato": True,
                        "disabled": False,
                        "insecure": False,
                        "multisiteurl": "",
                        "persist": False,
                        "replicate_ec": False,
                        "replication": None,
                        "timeout": 5,
                        "user_login": True,
                        "proxy": None,
                    }
                )
            }
        ),
        activate=False,
        pprint_value=True,
    )

    CleanUpSiteAttributes(
        name="clean_up_site_attributes",
        title="Clean up site connections",
        sort_index=30,
        expiry_version=ExpiryVersion.CMK_300,
    )(logging.getLogger())

    assert site_mgmt.load_sites()[SiteId("abc")]["url_prefix"] == "../"


@pytest.mark.usefixtures("load_config")
def test_clean_up_missing_id() -> None:
    site_mgmt = site_management_registry["site_management"]
    site_mgmt.save_sites(
        SiteConfigurations(
            {
                SiteId("abc"): SiteConfiguration(  # type: ignore[typeddict-item]
                    {
                        "alias": "abc",
                        "socket": ("local", None),
                        "disable_wato": True,
                        "disabled": False,
                        "insecure": False,
                        "multisiteurl": "",
                        "persist": False,
                        "replicate_ec": False,
                        "replication": None,
                        "timeout": 5,
                        "user_login": True,
                        "proxy": None,
                    }
                )
            }
        ),
        activate=False,
        pprint_value=True,
    )

    CleanUpSiteAttributes(
        name="clean_up_site_attributes",
        title="Clean up site connections",
        sort_index=30,
        expiry_version=ExpiryVersion.CMK_300,
    )(logging.getLogger())

    assert site_mgmt.load_sites()[SiteId("abc")]["id"] == "abc"
