#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Contract tests: the distributed monitoring collector agrees with the GUI on the site's role

The collector decides like the GUI's is_distributed_setup_remote_site(), but reads the files
itself. These tests let the GUI write the files of each role and compare both answers.
"""

from collections.abc import Callable

import pytest

import cmk.product_usage.collectors.distributed_monitoring as distributed_monitoring_collector
from cmk.ccc.site import omd_site, SiteId
from cmk.config.paths import BaseConfigurationMKFiles
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.watolib.config_sync import create_distributed_wato_files
from cmk.gui.watolib.sites import SitesConfigFile
from cmk.livestatus_client import NetworkSocketDetails, SiteConfiguration, SiteConfigurations
from cmk.utils import paths


def _standalone_site() -> None:
    SitesConfigFile().save(SiteConfigurations({omd_site(): _local_site()}), pprint_value=False)


def _central_site() -> None:
    SitesConfigFile().save(
        SiteConfigurations({omd_site(): _local_site(), SiteId("remote"): _remote_site()}),
        pprint_value=False,
    )
    create_distributed_wato_files(paths.omd_root, omd_site(), is_remote=False)


def _remote_setup_site() -> None:
    # The central site pushes the file, the remote site's own sites.mk lists only itself
    SitesConfigFile().save(SiteConfigurations({omd_site(): _local_site()}), pprint_value=False)
    create_distributed_wato_files(paths.omd_root, omd_site(), is_remote=True)


@pytest.mark.parametrize(
    "write_site_config, is_remote_setup_site",
    [
        pytest.param(_standalone_site, False, id="standalone"),
        pytest.param(_central_site, False, id="central"),
        pytest.param(_remote_setup_site, True, id="remote-setup"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_collector_reports_the_role_the_gui_derives_from_the_same_files(
    write_site_config: Callable[[], None], is_remote_setup_site: bool
) -> None:
    write_site_config()

    collected = distributed_monitoring_collector.collect(
        default_config_dir=paths.default_config_dir,
        cmk_config_dir=BaseConfigurationMKFiles.from_omd_root(paths.omd_root).conf_d,
    )

    assert (collected.is_remote_setup_site, is_remote_setup_site) == (
        is_distributed_setup_remote_site(SitesConfigFile().load_for_reading()),
        is_remote_setup_site,
    )


def _local_site() -> SiteConfiguration:
    return _site_config(omd_site(), remote=False)


def _remote_site() -> SiteConfiguration:
    return _site_config(SiteId("remote"), remote=True)


def _site_config(site_id: SiteId, *, remote: bool) -> SiteConfiguration:
    site_config = SiteConfiguration(
        alias=str(site_id),
        disable_wato=False,
        disabled=False,
        id=site_id,
        insecure=False,
        is_trusted=False,
        message_broker_port=5672,
        multisiteurl="http://127.0.0.1/remote/check_mk/" if remote else "",
        persist=False,
        proxy=None,
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave" if remote else None,
        socket=("local", None),
        status_host=None,
        timeout=5,
        url_prefix=f"/{site_id}/",
        user_login=True,
        user_attribute_sync_connections="all",
    )
    if remote:
        site_config["socket"] = (
            "tcp",
            NetworkSocketDetails(address=("127.0.0.1", 6557), tls=("plain_text", {})),
        )
    return site_config
