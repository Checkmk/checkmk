#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import cast, Literal, NamedTuple, NewType, TypedDict

from livestatus import (
    ConnectedSite,
    lqencode,
    MKLivestatusQueryError,
    MultiSiteConnection,
    NetworkSocketDetails,
    NetworkSocketInfo,
    sanitize_site_configuration,
    SiteConfiguration,
    SiteConfigurations,
    SiteId,
    UnixSocketInfo,
)

from cmk.ccc.site import omd_site
from cmk.ccc.version import __version__, Edition, edition, Version, VersionsIncompatible

from cmk.utils import paths
from cmk.utils.licensing.handler import LicenseState
from cmk.utils.licensing.registry import get_license_state
from cmk.utils.paths import livestatus_unix_socket
from cmk.utils.user import UserId

from cmk.gui.config import active_config
from cmk.gui.ctx_stack import g
from cmk.gui.flask_app import current_app
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.logged_in import user as global_user
from cmk.gui.site_config import get_site_config
from cmk.gui.utils.compatibility import (
    is_distributed_monitoring_compatible_for_licensing,
    LicensingCompatibility,
    LicensingCompatible,
    make_incompatible_info,
)

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
    user: LoggedInUser | None = None, force_authuser: UserId | None = None
) -> MultiSiteConnection:
    """Get Livestatus connection object matching the current site configuration
    and user settings. On the first call the actual connection is being made."""
    _ensure_connected(user, force_authuser)
    return g.live


class SiteStatus(TypedDict, total=False):
    """The status of a remote site

    Used to be: NewType("SiteStatus", Dict[str, Any]), feel free to add other
    attributes if you find them ;-)"""

    core_pid: int
    exception: MKLivestatusQueryError
    livestatus_version: str
    program_start: int
    program_version: str
    max_long_output_size: int
    state: Literal["online", "disabled", "down", "unreach", "dead", "waiting", "missing", "unknown"]


SiteStates = NewType("SiteStates", dict[SiteId, SiteStatus])


def states(user: LoggedInUser | None = None, force_authuser: UserId | None = None) -> SiteStates:
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
    # NOTE: g.__bool__() *can* return False due to the LocalProxy Kung Fu!
    if not g:  # type: ignore[truthy-bool]
        return
    logger.debug("Disconnecting site connections")
    if "live" in g:
        g.live.disconnect()
    g.pop("live", None)
    g.pop("site_status", None)


# TODO: this too does not really belong here...
def get_alias_of_host(site_id: SiteId | None, host_name: str) -> SiteId:
    query = "GET hosts\n" "Cache: reload\n" "Columns: alias\n" "Filter: name = %s" % lqencode(
        host_name
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
            if active_config.debug:
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


def _ensure_connected(user: LoggedInUser | None, force_authuser: UserId | None) -> None:
    """Build up a connection to livestatus to either a single site or multiple sites."""
    if "live" in g:
        return

    if user is None:
        user = global_user

    if force_authuser is None:
        # This makes also sure force_authuser is not the builtin user aka UserId("")
        force_authuser = (
            u if (u := request.get_validated_type_input(UserId, "force_authuser")) else None
        )

    logger.debug(
        "Initializing livestatus connections as user %s (forced auth user: %s)",
        user.id,
        force_authuser,
    )

    g.site_status = {}
    _connect_multiple_sites(user)
    _set_livestatus_auth(user, force_authuser)

    logger.debug(
        "Site states: %r",
        _redacted_site_states_for_logging(),
    )


def _redacted_site_states_for_logging() -> dict[SiteId, dict[str, object]]:
    return {
        site_id: {
            k: sanitize_site_configuration(v) if k == "site" else v for k, v in site_status.items()
        }
        for site_id, site_status in g.site_status.items()
    }


def _edition_from_livestatus(*, version_str: str, edition_str: str | None) -> Edition | None:
    version = Version.from_str(version_str)
    if version is None or version.base is None:
        return None
    if version.base.major > 2 or (version.base.major == 2 and version.base.minor >= 5):
        match edition_str:
            case "community":
                return Edition.CRE
            case "pro":
                return Edition.CEE
            case "ultimate":
                return Edition.CCE
            case "ultimatemt":
                return Edition.CME
            case "cloud":
                return Edition.CSE
            case _:
                return None
    match edition_str:
        case Edition.CRE.long:
            return Edition.CRE
        case Edition.CEE.long:
            return Edition.CEE
        case Edition.CCE.long:
            return Edition.CCE
        case Edition.CME.long:
            return Edition.CME
        case Edition.CSE.long:
            return Edition.CSE
        case _:
            return None


def _get_distributed_monitoring_compatibility(
    site_id: str,
    central_version: str,
    central_edition: Edition,
    central_license_state: LicenseState,
    remote_edition: Edition | None,
) -> LicensingCompatibility | VersionsIncompatible:
    if site_id == omd_site():
        return LicensingCompatible()

    if remote_edition is None:
        if Version.from_str(central_version) < Version.from_str("2.2.0"):
            return LicensingCompatible()
        return VersionsIncompatible(
            _(
                "Central site is version >= 2.2 while remote site is an older version, please "
                "update remote sites first"
            )
        )

    return is_distributed_monitoring_compatible_for_licensing(
        central_edition=central_edition,
        central_license_state=central_license_state,
        remote_edition=remote_edition,
    )


def _get_distributed_monitoring_connection_from_site_id(site_id: str) -> ConnectedSite | None:
    for connected_site in g.live.connections:
        if connected_site.id == site_id:
            return connected_site
    return None


def _inhibit_incompatible_site_connection(
    site_id: str,
    central_version: str,
    central_edition: Edition,
    central_license_state: LicenseState,
    remote_version: str,
    remote_edition: Edition | None,
    compatibility: LicensingCompatibility | VersionsIncompatible,
) -> None:
    if not (
        incompatible_connection := _get_distributed_monitoring_connection_from_site_id(site_id)
    ):
        return

    g.live.connections.remove(incompatible_connection)
    g.live.deadsites[site_id] = {
        "exception": make_incompatible_info(
            central_version=central_version,
            central_edition_short=central_edition.short,
            central_license_state=central_license_state,
            remote_version=remote_version.removeprefix("Check_MK "),
            remote_edition_short=remote_edition.short if remote_edition else None,
            remote_license_state=None,
            compatibility=compatibility,
        ),
        "site": incompatible_connection.config,
    }


def _connect_multiple_sites(user: LoggedInUser) -> None:
    enabled_sites, disabled_sites = _get_enabled_and_disabled_sites(user)
    _set_initial_site_states(enabled_sites, disabled_sites)

    g.live = MultiSiteConnection(
        sites=enabled_sites,
        disabled_sites=disabled_sites,
        only_sites_postprocess=current_app().features.livestatus_only_sites_postprocess,
    )

    # Fetch status of sites by querying the version of Nagios and livestatus
    # This may be cached by a proxy for up to the next configuration reload.
    g.live.set_prepend_site(True)
    for response in g.live.query(
        "GET status\n"
        "Cache: reload\n"
        "Columns: livestatus_version program_version program_start num_hosts num_services max_long_output_size "
        "core_pid edition"
    ):
        try:
            (
                site_id,
                livestatus_version,
                program_version,
                program_start,
                num_hosts,
                num_services,
                max_long_output_size,
                pid,
                remote_edition,
            ) = response
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

        central_edition = edition(paths.omd_root)
        central_version = __version__
        remote_edition = _edition_from_livestatus(
            version_str=livestatus_version, edition_str=remote_edition
        )
        central_license_state = get_license_state()

        compatibility = _get_distributed_monitoring_compatibility(
            site_id, central_version, central_edition, central_license_state, remote_edition
        )

        if not isinstance(compatibility, LicensingCompatible):
            _inhibit_incompatible_site_connection(
                site_id,
                central_version,
                central_edition,
                central_license_state,
                program_version,
                remote_edition,
                compatibility,
            )
        else:
            g.site_status[site_id].update(
                {
                    "state": "online",
                    "livestatus_version": livestatus_version,
                    "program_version": program_version,
                    "program_start": program_start,
                    "num_hosts": num_hosts,
                    "num_services": num_services,
                    "max_long_output_size": max_long_output_size,
                    "core": program_version.startswith("Check_MK") and "cmc" or "nagios",
                    "core_pid": pid,
                }
            )
    g.live.set_prepend_site(False)

    # TODO(lm): Find a better way to make the Livestatus object trigger the update
    # once self.deadsites is updated.
    update_site_states_from_dead_sites()


def _get_enabled_and_disabled_sites(
    user: LoggedInUser,
) -> tuple[SiteConfigurations, SiteConfigurations]:
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
    copied_site: SiteConfiguration = site_spec.copy()

    if site_spec.get("proxy") is not None:
        assert site_spec["proxy"] is not None
        copied_site["cache"] = site_spec["proxy"].get("cache", True)
    elif isinstance(site_spec["socket"], tuple) and site_spec["socket"][0] in ["tcp", "tcp6"]:
        copied_site["tls"] = cast(NetworkSocketDetails, site_spec["socket"][1])["tls"]
    copied_site["socket"] = encode_socket_for_livestatus(site_id, site_spec)

    return copied_site


def encode_socket_for_livestatus(site_id: SiteId, site_spec: SiteConfiguration) -> str:
    socket_spec = site_spec["socket"]

    if site_spec.get("proxy") is not None:
        return f"unix:{livestatus_unix_socket}proxy/{site_id}"

    if socket_spec[0] == "local":
        return "unix:%s" % livestatus_unix_socket

    if socket_spec[0] == "unix":
        unix_family_spec, unix_address_spec = cast(UnixSocketInfo, socket_spec)
        return "{}:{}".format(unix_family_spec, unix_address_spec["path"])

    if socket_spec[0] in ("tcp", "tcp6"):
        tcp_family_spec, tcp_address_spec = cast(NetworkSocketInfo, socket_spec)
        return "%s:%s:%d" % (
            tcp_family_spec,
            tcp_address_spec["address"][0],
            tcp_address_spec["address"][1],
        )

    raise NotImplementedError()


def update_site_states_from_dead_sites() -> None:
    # Get exceptions in case of dead sites
    for site_id, deadinfo in live().dead_sites().items():
        status_host_state = cast(int | None, deadinfo.get("status_host_state"))
        g.site_status[site_id].update(
            {
                "exception": deadinfo["exception"],
                "status_host_state": status_host_state,
                "state": _status_host_state_name(status_host_state),
            }
        )


def _status_host_state_name(shs: int | None) -> str:
    return _STATUS_NAMES.get(shs, "unknown")


_STATUS_NAMES = {
    None: "dead",
    1: "down",
    2: "unreach",
    3: "waiting",
}


def site_state_titles() -> (
    dict[
        Literal["online", "disabled", "down", "unreach", "dead", "waiting", "missing", "unknown"],
        str,
    ]
):
    return {
        "online": _("This site is online."),
        "disabled": _("The connection to this site has been disabled."),
        "down": _("This site is currently down."),
        "unreach": _("This site is currently not reachable."),
        "dead": _("This site is not responding."),
        "waiting": _("The status of this site has not yet been determined."),
        "missing": _("This site does not exist."),
        "unknown": _("The status of this site could not be determined."),
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
def _set_livestatus_auth(user: LoggedInUser, force_authuser: UserId | None) -> None:
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
def _livestatus_auth_user(user: LoggedInUser, force_authuser: UserId | None) -> UserId | None:
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
def only_sites(sites: None | list[SiteId] | SiteId) -> Iterator[None]:
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
def prepend_site() -> Iterator[None]:
    live().set_prepend_site(True)
    try:
        yield
    finally:
        live().set_prepend_site(False)


@contextmanager
def set_limit(limit: int | None) -> Iterator[None]:
    # + 1: We need to know, if limit is exceeded
    live().set_limit(limit if limit is None else limit + 1)
    try:
        yield
    finally:
        live().set_limit()  # removes limit


class GroupedSiteState(NamedTuple):
    readable: str
    site_ids: list[SiteId]


def get_grouped_site_states() -> dict[str, GroupedSiteState]:
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


def filter_available_site_choices(choices: list[tuple[SiteId, str]]) -> list[tuple[SiteId, str]]:
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


def site_choices() -> list[tuple[str, str]]:
    return sorted(
        [
            (sitename, get_site_config(active_config, sitename)["alias"])
            for sitename, state in states().items()
            if state["state"] == "online"
        ],
        key=lambda a: a[1].lower(),
    )
