#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping

from livestatus import SiteConfiguration, SiteConfigurations

import cmk.utils.paths
from cmk.ccc.site import omd_site, SiteId


# TODO: Cleanup: Make clear that this function is used by the status GUI (and not WATO)
# and only returns the currently enabled sites. Or should we redeclare the "disabled" state
# to disable the sites at all?
def enabled_sites(site_configs: SiteConfigurations) -> SiteConfigurations:
    return SiteConfigurations(
        {
            site_id: site_config
            for site_id, site_config in site_configs.items()
            if not site_config["disabled"]
        }
    )


def has_distributed_setup_remote_sites(site_configs: SiteConfigurations) -> bool:
    return bool(wato_slave_sites(site_configs))


def is_distributed_setup_remote_site(site_configs: SiteConfigurations) -> bool:
    return _has_distributed_wato_file() and not has_distributed_setup_remote_sites(site_configs)


def _has_distributed_wato_file() -> bool:
    path = cmk.utils.paths.check_mk_config_dir / "distributed_wato.mk"
    return path.exists() and path.stat().st_size != 0


def get_login_sites(site_configs: SiteConfigurations) -> list[SiteId]:
    """Returns the Setup slave sites a user may login and the local site"""
    return get_login_slave_sites(site_configs) + [omd_site()]


# TODO: All site listing functions should return the same data structure, e.g. a list of
#       pairs (site_id, site)
def get_login_slave_sites(site_configs: SiteConfigurations) -> list[SiteId]:
    """Returns a list of site ids which are Setup slave sites and users can login"""
    login_sites = []
    for site_id, site_spec in wato_slave_sites(site_configs).items():
        if site_spec.get("user_login", True) and not site_is_local(site_spec):
            login_sites.append(site_id)
    return login_sites


def is_replication_enabled(site_config: SiteConfiguration) -> bool:
    return bool(site_config.get("replication"))


def wato_slave_sites(site_configs: SiteConfigurations) -> SiteConfigurations:
    return SiteConfigurations(
        {site_id: s for site_id, s in site_configs.items() if is_replication_enabled(s)}
    )


def site_is_local(site_config: SiteConfiguration) -> bool:
    socket_info = site_config["socket"]
    if isinstance(socket_info, str):
        # Should be unreachable
        return False

    if socket_info[0] == "local":
        return True

    if socket_info[0] == "unix":
        return socket_info[1]["path"] == str(cmk.utils.paths.livestatus_unix_socket)

    return False


def is_single_local_site(sites: Mapping[SiteId, SiteConfiguration]) -> bool:
    if len(sites) > 1:
        return False
    if not sites:
        return True

    return site_is_local(list(sites.values())[0])


def wato_site_ids(site_configs: SiteConfigurations) -> list[SiteId]:
    return [omd_site(), *wato_slave_sites(site_configs)]
