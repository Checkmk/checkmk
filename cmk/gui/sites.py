#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# pylint: disable=unused-import
from typing import (
    Any,
    cast,
    Dict,
    Iterator,
    List,
    NewType,
    Optional,
    Text,
    Tuple,
    TYPE_CHECKING,
    Union,
)
# pylint: enable=unused-import
from contextlib import contextmanager

from livestatus import (
    MultiSiteConnection,
    MKLivestatusQueryError,
    SiteId,
    SiteConfiguration,
    SiteConfigurations,
)
from cmk import is_managed_edition
from cmk.utils.paths import livestatus_unix_socket
import cmk.gui.config as config
from cmk.gui.globals import g, html

if TYPE_CHECKING:
    from werkzeug.local import LocalProxy
    from cmk.utils.type_defs import UserId  # pylint: disable=unused-import,ungrouped-imports
    UserType = LocalProxy

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


def live(user=None, force_authuser=None):
    # type: (Optional[UserType], Optional[UserId]) -> MultiSiteConnection
    """Get Livestatus connection object matching the current site configuration
       and user settings. On the first call the actual connection is being made."""
    _ensure_connected(user, force_authuser)
    return g.live


SiteStatus = NewType('SiteStatus', Dict[bytes, Any])
SiteStates = NewType('SiteStates', Dict[SiteId, SiteStatus])


def states(user=None, force_authuser=None):
    # type: (Optional[UserType], Optional[UserId]) -> SiteStates
    """Returns dictionary of all known site states."""
    _ensure_connected(user, force_authuser)
    return g.site_status


def disconnect():
    # type: () -> None
    """Actively closes all Livestatus connections."""
    g.pop('live', None)
    g.pop('site_status', None)


# TODO: This should live somewhere else, it's just a random helper...
def all_groups(what):
    # type: (bytes) -> List[Tuple[Text, Text]]
    """Returns a list of host/service/contact groups (pairs of name/alias)

    Groups are collected via livestatus from all sites. In case no alias is defined
    the name is used as second element. The list is sorted by lower case alias in the first place."""
    query = "GET %sgroups\nCache: reload\nColumns: name alias\n" % what
    groups = cast(List[Tuple[Text, Text]], live().query(query))
    # The dict() removes duplicate group names. Aliases don't need be deduplicated.
    return sorted([(name, alias or name) for name, alias in dict(groups).iteritems()],
                  key=lambda e: e[1].lower())


#.
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


# Build up a connection to livestatus to either a single site or multiple sites.
def _ensure_connected(user, force_authuser):
    # type: (Optional[UserType], Optional[UserId]) -> None
    if 'live' in g:
        return
    if user is None:
        _user = config.user
        user = config.user
    if force_authuser is None:
        force_authuser = html.request.var("force_authuser")
    g.site_status = {}
    _connect_multiple_sites(user)
    _set_livestatus_auth(user, force_authuser)


def _connect_multiple_sites(user):
    # type: (UserType) -> None
    enabled_sites, disabled_sites = _get_enabled_and_disabled_sites(user)
    _set_initial_site_states(enabled_sites, disabled_sites)

    if is_managed_edition():
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
            "Columns: livestatus_version program_version program_start num_hosts num_services"):

        try:
            site_id, v1, v2, ps, num_hosts, num_services = response
        except ValueError:
            e = MKLivestatusQueryError("Invalid response to status query: %s" % response)

            site_id = response[0]
            g.site_status[site_id].update({
                "exception": e,
                "status_host_state": None,
                "state": _status_host_state_name(None),
            })
            continue

        g.site_status[site_id].update({
            "state": "online",
            "livestatus_version": v1,
            "program_version": v2,
            "program_start": ps,
            "num_hosts": num_hosts,
            "num_services": num_services,
            "core": v2.startswith("Check_MK") and "cmc" or "nagios",
        })
    g.live.set_prepend_site(False)

    # TODO(lm): Find a better way to make the Livestatus object trigger the update
    # once self.deadsites is updated.
    update_site_states_from_dead_sites()


def _get_enabled_and_disabled_sites(user):
    # type: (UserType) -> Tuple[SiteConfigurations, SiteConfigurations]
    enabled_sites = SiteConfigurations({})
    disabled_sites = SiteConfigurations({})

    for site_id, site in user.authorized_sites().iteritems():
        site = _site_config_for_livestatus(site_id, site)

        if user.is_site_disabled(site_id):
            disabled_sites[site_id] = site
        else:
            enabled_sites[site_id] = site

    return enabled_sites, disabled_sites


def _site_config_for_livestatus(site_id, site):
    # type: (SiteId, SiteConfiguration) -> SiteConfiguration
    """Prepares a site config specification for the livestatus module

    In case the GUI connects to the local livestatus proxy there are several
    special things to do:
    a) Tell livestatus not to strip away the cache header
    b) Connect in plain text to the sites local proxy unix socket
    """
    site = SiteConfiguration(site.copy())

    if site["proxy"] is not None:
        site["cache"] = site["proxy"].get("cache", True)

    else:
        if site["socket"][0] in ["tcp", "tcp6"]:
            site["tls"] = site["socket"][1]["tls"]

    site["socket"] = encode_socket_for_livestatus(site_id, site)

    return site


def encode_socket_for_livestatus(site_id, site):
    # type: (SiteId, SiteConfiguration) -> bytes
    socket_spec = site["socket"]
    family_spec, address_spec = socket_spec

    if site["proxy"] is not None:
        return "unix:%sproxy/%s" % (livestatus_unix_socket, site_id)

    if family_spec == "local":
        return "unix:%s" % livestatus_unix_socket

    if family_spec == "unix":
        return "%s:%s" % (family_spec, address_spec["path"])

    if family_spec in ["tcp", "tcp6"]:
        return "%s:%s:%d" % (family_spec, address_spec["address"][0], address_spec["address"][1])

    raise NotImplementedError()


def update_site_states_from_dead_sites():
    # type: () -> None
    # Get exceptions in case of dead sites
    for site_id, deadinfo in live().dead_sites().items():
        status_host_state = cast(Optional[int], deadinfo.get("status_host_state"))
        g.site_status[site_id].update({
            "exception": deadinfo["exception"],
            "status_host_state": status_host_state,
            "state": _status_host_state_name(status_host_state),
        })


def _status_host_state_name(shs):
    # type: (Optional[int]) -> bytes
    return _STATUS_NAMES.get(shs, "unknown")


_STATUS_NAMES = {
    None: "dead",
    1: "down",
    2: "unreach",
    3: "waiting",
}


def _set_initial_site_states(enabled_sites, disabled_sites):
    # (SiteConfigurations, SiteConfigurations) -> None
    for site_id, site in enabled_sites.items():
        g.site_status[site_id] = {"state": "dead", "site": site}

    for site_id, site in disabled_sites.items():
        g.site_status[site_id] = {"state": "disabled", "site": site}


# If Multisite is retricted to data the user is a contact for, we need to set an
# AuthUser: header for livestatus.
def _set_livestatus_auth(user, force_authuser):
    # type: (UserType, UserId) -> None
    user_id = _livestatus_auth_user(user, force_authuser)
    if user_id is not None:
        g.live.set_auth_user('read', user_id)
        g.live.set_auth_user('action', user_id)

    # May the user see all objects in BI aggregations or only some?
    if not user.may("bi.see_all"):
        g.live.set_auth_user('bi', user_id)

    # May the user see all Event Console events or only some?
    if not user.may("mkeventd.seeall"):
        g.live.set_auth_user('ec', user_id)

    # Default auth domain is read. Please set to None to switch off authorization
    g.live.set_auth_domain('read')


# Returns either None when no auth user shal be set or the name of the user
# to be used as livestatus auth user
def _livestatus_auth_user(user, force_authuser):
    # type: (UserType, UserId) -> Optional[UserId]
    if not user.may("general.see_all"):
        return user.id
    if force_authuser == "1":
        return user.id
    if force_authuser == "0":
        return None
    if force_authuser:
        return force_authuser  # set a different user
    if user.get_attribute("force_authuser"):
        return user.id
    return None


@contextmanager
def only_sites(sites):
    # type: (Optional[Union[List[SiteId], SiteId]]) -> Iterator[None]
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
def prepend_site():
    # type: () -> Iterator[None]
    live().set_prepend_site(True)
    try:
        yield
    finally:
        live().set_prepend_site(False)
