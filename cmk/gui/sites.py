#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, cast, Dict, Iterator, List, NamedTuple, NewType, Optional, Tuple, Union

from livestatus import (
    LivestatusOutputFormat,
    lqencode,
    MKLivestatusQueryError,
    MultiSiteConnection,
    SiteConfiguration,
    SiteConfigurations,
    SiteId,
)

from cmk.utils.paths import livestatus_unix_socket
from cmk.utils.site import omd_site
from cmk.utils.type_defs import UserId
from cmk.utils.version import is_managed_edition

from cmk.gui.globals import config, g, request
from cmk.gui.globals import user as global_user
from cmk.gui.i18n import _
from cmk.gui.log import logger

# This keeps the API compatible with previous versions where
# both modules were merged.
from cmk.gui.site_config import (  # pylint: disable=unused-import
    allsites,
    get_login_sites,
    get_login_slave_sites,
    get_site_config,
    has_wato_slave_sites,
    is_single_local_site,
    is_wato_slave_site,
    site_is_local,
    sitenames,
    wato_slave_sites,
)
from cmk.gui.utils.logged_in import LoggedInUser

#   .--API-----------------------------------------------------------------.
#   |                             _    ____ ___                            |
#   |                            / \  |  _ \_ _|                           |
#   |                           / _ \ | |_) | |                            |
#   |                          / ___ \|  __/| |                            |
#   |                         /_/   \_\_|  |___|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Functions und names for the public                                  |
#   '----------------------------------------------------------------------'


def live(
    user: Optional[LoggedInUser] = None, force_authuser: Optional[UserId] = None
) -> MultiSiteConnection:
    """Get Livestatus connection object matching the current site configuration
    and user settings. On the first call the actual connection is being made."""
    _ensure_connected(user, force_authuser)
    return g.live


SiteStatus = NewType("SiteStatus", Dict[str, Any])
SiteStates = NewType("SiteStates", Dict[SiteId, SiteStatus])


def states(
    user: Optional[LoggedInUser] = None, force_authuser: Optional[UserId] = None
) -> SiteStates:
    """Returns dictionary of all known site states."""
    _ensure_connected(user, force_authuser)
    return g.site_status


@contextmanager
def cleanup_connections() -> Iterator[None]:
    """Context-manager to cleanup livestatus connections"""
    try:
        yield
    finally:
        try:
            disconnect()
        except Exception:
            logger.exception("Error during livestatus cleanup")
            raise


# TODO: This is not really shutting down or closing connections. It only removes references to
# sockets and connection classes. This should really be cleaned up (context managers, ...)
def disconnect() -> None:
    """Actively closes all Livestatus connections."""
    if not g:
        return
    logger.debug("Disconnecing site connections")
    if "live" in g:
        g.live.disconnect()
    g.pop("live", None)
    g.pop("site_status", None)


# TODO: This should live somewhere else, it's just a random helper...
def all_groups(what: str) -> List[Tuple[str, str]]:
    """Returns a list of host/service/contact groups (pairs of name/alias)

    Groups are collected via livestatus from all sites. In case no alias is defined
    the name is used as second element. The list is sorted by lower case alias in the first place."""
    query = "GET %sgroups\nCache: reload\nColumns: name alias\n" % what
    groups = cast(List[Tuple[str, str]], live().query(query))
    # The dict() removes duplicate group names. Aliases don't need be deduplicated.
    return sorted(
        [(name, alias or name) for name, alias in dict(groups).items()], key=lambda e: e[1].lower()
    )


# TODO: this too does not really belong here...
def get_alias_of_host(site_id: Optional[SiteId], host_name: str) -> SiteId:
    query = (
        "GET hosts\n" "Cache: reload\n" "Columns: alias\n" "Filter: name = %s" % lqencode(host_name)
    )

    with only_sites(site_id):
        try:
            return live().query_value(query)
        except Exception as e:
            logger.warning(
                "Could not determine alias of host %s on site %s: %s",
                host_name,
                site_id,
                e,
            )
            if config.debug:
                raise
            return SiteId(host_name)


# .
#   .--Internal------------------------------------------------------------.
#   |                ___       _                        _                  |
#   |               |_ _|_ __ | |_ ___ _ __ _ __   __ _| |                 |
#   |                | || '_ \| __/ _ \ '__| '_ \ / _` | |                 |
#   |                | || | | | ||  __/ |  | | | | (_| | |                 |
#   |               |___|_| |_|\__\___|_|  |_| |_|\__,_|_|                 |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Internal functiions and variables                                   |
#   '----------------------------------------------------------------------'

# The global livestatus object lives in g.live. This is initialized
# automatically upon first access to the accessor function live()

# g.site_status keeps a dictionary for each site with the following keys:
# "state"              --> "online", "disabled", "down", "unreach", "dead" or "waiting"
# "exception"          --> An error exception in case of down, unreach, dead or waiting
# "status_host_state"  --> host state of status host (0, 1, 2 or None)
# "livestatus_version" --> Version of sites livestatus if "online"
# "program_version"    --> Version of Nagios if "online"


def _ensure_connected(user: Optional[LoggedInUser], force_authuser: Optional[UserId]) -> None:
    """Build up a connection to livestatus to either a single site or multiple sites."""
    if "live" in g:
        return

    if user is None:
        user = global_user

    if force_authuser is None:
        request_force_authuser = request.get_str_input("force_authuser")
        force_authuser = UserId(request_force_authuser) if request_force_authuser else None

    logger.debug(
        "Initializing livestatus connections as user %s (forced auth user: %s)",
        user.id,
        force_authuser,
    )

    g.site_status = {}
    _connect_multiple_sites(user)
    _set_livestatus_auth(user, force_authuser)

    logger.debug("Site states: %r", g.site_status)


def _connect_multiple_sites(user: LoggedInUser) -> None:
    enabled_sites, disabled_sites = _get_enabled_and_disabled_sites(user)
    _set_initial_site_states(enabled_sites, disabled_sites)

    if is_managed_edition():
        # Astroid 2.x bug prevents us from using NewType https://github.com/PyCQA/pylint/issues/2296
        import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module

        g.live = managed.CMEMultiSiteConnection(enabled_sites, disabled_sites)
    else:
        g.live = MultiSiteConnection(enabled_sites, disabled_sites)

    # Fetch status of sites by querying the version of Nagios and livestatus
    # This may be cached by a proxy for up to the next configuration reload.
    g.live.set_prepend_site(True)
    for response in g.live.query(
        "GET status\n"
        "Cache: reload\n"
        "Columns: livestatus_version program_version program_start num_hosts num_services "
        "core_pid"
    ):

        try:
            site_id, v1, v2, ps, num_hosts, num_services, pid = response
        except ValueError:
            e = MKLivestatusQueryError("Invalid response to status query: %s" % response)

            site_id = response[0]
            g.site_status[site_id].update(
                {
                    "exception": e,
                    "status_host_state": None,
                    "state": _status_host_state_name(None),
                }
            )
            continue

        g.site_status[site_id].update(
            {
                "state": "online",
                "livestatus_version": v1,
                "program_version": v2,
                "program_start": ps,
                "num_hosts": num_hosts,
                "num_services": num_services,
                "core": v2.startswith("Check_MK") and "cmc" or "nagios",
                "core_pid": pid,
            }
        )
    g.live.set_prepend_site(False)

    # TODO(lm): Find a better way to make the Livestatus object trigger the update
    # once self.deadsites is updated.
    update_site_states_from_dead_sites()


def _get_enabled_and_disabled_sites(
    user: LoggedInUser,
) -> Tuple[SiteConfigurations, SiteConfigurations]:
    enabled_sites: SiteConfigurations = SiteConfigurations({})
    disabled_sites: SiteConfigurations = SiteConfigurations({})

    for site_id, site_spec in user.authorized_sites().items():
        site_spec = _site_config_for_livestatus(site_id, site_spec)
        # Astroid 2.x bug prevents us from using NewType https://github.com/PyCQA/pylint/issues/2296
        # pylint: disable=unsupported-assignment-operation
        if user.is_site_disabled(site_id):
            disabled_sites[site_id] = site_spec
        else:
            enabled_sites[site_id] = site_spec

    return enabled_sites, disabled_sites


def _site_config_for_livestatus(site_id: SiteId, site_spec: SiteConfiguration) -> SiteConfiguration:
    """Prepares a site config specification for the livestatus module

    In case the GUI connects to the local livestatus proxy there are several
    special things to do:
    a) Tell livestatus not to strip away the cache header
    b) Connect in plain text to the sites local proxy unix socket
    """
    copied_site: SiteConfiguration = SiteConfiguration(site_spec.copy())

    # Astroid 2.x bug prevents us from using NewType https://github.com/PyCQA/pylint/issues/2296
    # pylint: disable=unsupported-assignment-operation
    if copied_site["proxy"] is not None:
        copied_site["cache"] = site_spec["proxy"].get("cache", True)
    else:
        if copied_site["socket"][0] in ["tcp", "tcp6"]:
            copied_site["tls"] = site_spec["socket"][1]["tls"]
    copied_site["socket"] = encode_socket_for_livestatus(site_id, site_spec)

    return copied_site


def encode_socket_for_livestatus(site_id: SiteId, site_spec: SiteConfiguration) -> str:
    socket_spec = site_spec["socket"]
    family_spec, address_spec = socket_spec

    if site_spec["proxy"] is not None:
        return "unix:%sproxy/%s" % (livestatus_unix_socket, site_id)

    if family_spec == "local":
        return "unix:%s" % livestatus_unix_socket

    if family_spec == "unix":
        return "%s:%s" % (family_spec, address_spec["path"])

    if family_spec in ["tcp", "tcp6"]:
        return "%s:%s:%d" % (family_spec, address_spec["address"][0], address_spec["address"][1])

    raise NotImplementedError()


def update_site_states_from_dead_sites() -> None:
    # Get exceptions in case of dead sites
    for site_id, deadinfo in live().dead_sites().items():
        status_host_state = cast(Optional[int], deadinfo.get("status_host_state"))
        g.site_status[site_id].update(
            {
                "exception": deadinfo["exception"],
                "status_host_state": status_host_state,
                "state": _status_host_state_name(status_host_state),
            }
        )


def _status_host_state_name(shs: Optional[int]) -> str:
    return _STATUS_NAMES.get(shs, "unknown")


_STATUS_NAMES = {
    None: "dead",
    1: "down",
    2: "unreach",
    3: "waiting",
}


def site_state_titles() -> Dict[str, str]:
    return {
        "online": _("This site is online."),
        "disabled": _("The connection to this site has been disabled."),
        "down": _("This site is currently down."),
        "unreach": _("This site is currently not reachable."),
        "dead": _("This site is not responding."),
        "waiting": _("The status of this site has not yet been determined."),
        "missing": _("This site does not exist."),
    }


def _set_initial_site_states(
    enabled_sites: SiteConfigurations, disabled_sites: SiteConfigurations
) -> None:
    for site_id, site_spec in enabled_sites.items():
        g.site_status[site_id] = {"state": "dead", "site": site_spec}

    for site_id, site_spec in disabled_sites.items():
        g.site_status[site_id] = {"state": "disabled", "site": site_spec}


# If Multisite is retricted to data the user is a contact for, we need to set an
# AuthUser: header for livestatus.
def _set_livestatus_auth(user: LoggedInUser, force_authuser: Optional[UserId]) -> None:
    user_id = _livestatus_auth_user(user, force_authuser)
    if user_id is not None:
        g.live.set_auth_user("read", user_id)
        g.live.set_auth_user("action", user_id)

    # May the user see all objects in BI aggregations or only some?
    if not user.may("bi.see_all"):
        g.live.set_auth_user("bi", user_id)

    # May the user see all Event Console events or only some?
    if not user.may("mkeventd.seeall"):
        g.live.set_auth_user("ec", user_id)

    # Default auth domain is read. Please set to None to switch off authorization
    g.live.set_auth_domain("read")


# Returns either None when no auth user shal be set or the name of the user
# to be used as livestatus auth user
def _livestatus_auth_user(user: LoggedInUser, force_authuser: Optional[UserId]) -> Optional[UserId]:
    if not user.may("general.see_all"):
        return user.id
    if force_authuser == UserId("1"):
        return user.id
    if force_authuser == UserId("0"):
        return None
    if force_authuser:
        return force_authuser  # set a different user
    if user.get_attribute("force_authuser"):
        return user.id
    return None


@contextmanager
def only_sites(sites: Union[None, List[SiteId], SiteId]) -> Iterator[None]:
    """Livestatus query over sites"""
    if not sites:
        sites = None
    elif not isinstance(sites, list):
        sites = [sites]

    live().set_only_sites(sites)

    try:
        yield
    finally:
        live().set_only_sites(None)


@contextmanager
def output_format(use_format: LivestatusOutputFormat) -> Iterator[None]:
    previous_format = live().get_output_format()
    try:
        live().set_output_format(use_format)
        yield
    finally:
        live().set_output_format(previous_format)


@contextmanager
def prepend_site() -> Iterator[None]:
    live().set_prepend_site(True)
    try:
        yield
    finally:
        live().set_prepend_site(False)


@contextmanager
def set_limit(limit: Optional[int]) -> Iterator[None]:
    if limit is not None:
        live().set_limit(limit + 1)  # + 1: We need to know, if limit is exceeded
    else:
        live().set_limit(None)

    try:
        yield
    finally:
        live().set_limit()  # removes limit


class GroupedSiteState(NamedTuple):
    readable: str
    site_ids: List[SiteId]


def get_grouped_site_states() -> Dict[str, GroupedSiteState]:
    grouped_states = {
        "ok": GroupedSiteState(
            readable=_("OK"),
            site_ids=[],
        ),
        "disabled": GroupedSiteState(
            readable=_("disabled"),
            site_ids=[],
        ),
        "error": GroupedSiteState(
            readable=_("disconnected"),
            site_ids=[],
        ),
    }
    for site_id, info in states().items():
        grouped_states[_map_site_state(info["state"])].site_ids.append(site_id)
    return grouped_states


def _map_site_state(state: str) -> str:
    if state in ("online", "waiting"):
        return "ok"
    if state == "disabled":
        return "disabled"
    return "error"


def filter_available_site_choices(choices: List[Tuple[SiteId, str]]) -> List[Tuple[SiteId, str]]:
    # Only add enabled sites to choices
    all_site_states = states()
    sites_enabled = []
    for entry in choices:
        site_id, _desc = entry
        site_state = all_site_states.get(site_id, SiteStatus({})).get("state")
        if site_state is None:
            continue
        sites_enabled.append(entry)
    return sites_enabled


def configured_sites() -> SiteConfigurations:
    return SiteConfigurations({site_id: get_site_config(site_id) for site_id in sitenames()})


def sorted_sites() -> List[Tuple[SiteId, str]]:
    return sorted(
        [(site_id, s["alias"]) for site_id, s in global_user.authorized_sites().items()],
        key=lambda k: k[1].lower(),
    )


def get_configured_site_choices() -> List[Tuple[SiteId, str]]:
    return site_choices(global_user.authorized_sites(unfiltered_sites=configured_sites()))


def site_attribute_default_value() -> Optional[SiteId]:
    site_id = omd_site()
    authorized_site_ids = global_user.authorized_sites(unfiltered_sites=configured_sites()).keys()
    if site_id in authorized_site_ids:
        return site_id
    return None


def site_choices(site_configs: SiteConfigurations) -> List[Tuple[SiteId, str]]:
    """Compute the choices to be used e.g. in dropdowns from a SiteConfigurations collection"""
    choices = []
    for site_id, site_spec in site_configs.items():
        title = site_id
        if site_spec.get("alias"):
            title += " - " + site_spec["alias"]

        choices.append((site_id, title))

    return sorted(choices, key=lambda s: s[1])


def get_event_console_site_choices() -> List[Tuple[SiteId, str]]:
    return site_choices(
        SiteConfigurations(
            {
                site_id: site
                for site_id, site in global_user.authorized_sites(
                    unfiltered_sites=configured_sites()
                ).items()
                if site_is_local(site_id) or site.get("replicate_ec", False)
            }
        )
    )


def get_activation_site_choices() -> List[Tuple[SiteId, str]]:
    return site_choices(activation_sites())


def activation_sites() -> SiteConfigurations:
    """Returns sites that are affected by WATO changes

    These sites are shown on activation page and get change entries
    added during WATO changes."""
    return SiteConfigurations(
        {
            site_id: site
            for site_id, site in global_user.authorized_sites(
                unfiltered_sites=configured_sites()
            ).items()
            if site_is_local(site_id) or site.get("replication")
        }
    )
