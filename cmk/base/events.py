#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

# This file is being used by the rule based notifications and (CEE
# only) by the alert handling

import logging
import os
import select
import socket
import sys
import time
import traceback
from collections.abc import Callable, Iterable, Mapping
from typing import Any, cast, Literal, Protocol
from urllib.parse import quote, urlencode

import livestatus

import cmk.ccc.daemon
import cmk.ccc.debug
from cmk.ccc.hostaddress import HostName
from cmk.ccc.regex import regex
from cmk.ccc.site import omd_site
from cmk.events.event_context import EnrichedEventContext, EventContext
from cmk.utils.http_proxy_config import HTTPProxyConfig
from cmk.utils.notify import read_notify_host_file
from cmk.utils.notify_types import EventRule
from cmk.utils.rulesets.ruleset_matcher import matches_host_tags
from cmk.utils.rulesets.tuple_rulesets import in_extraconf_servicelist
from cmk.utils.servicename import ServiceName
from cmk.utils.tags import TagGroupID, TagID
from cmk.utils.timeperiod import (
    TimeperiodActiveCoreLookup,
    TimeperiodSpecs,
)

ContactList = list  # TODO Improve this

# We actually want to use Matcher for all our matchers, but mypy is too dumb to
# use that for function types, see https://github.com/python/mypy/issues/1641.
Matcher = Callable[[EventRule, EventContext, bool, TimeperiodSpecs], str | None]

type _RulesetProxySpec = tuple[
    Literal["cmk_postprocessed"],
    Literal["environment_proxy", "no_proxy", "stored_proxy", "explicit_proxy"],
    str,
]
type ProxyGetter = Callable[[tuple[str, str | None] | _RulesetProxySpec], HTTPProxyConfig]

type CoreTimeperiodsActive = Mapping[str, bool]

logger = logging.getLogger("cmk.base.events")


def _send_reply_ready() -> None:
    sys.stdout.write("*\n")
    sys.stdout.flush()


class _EventFunction(Protocol):
    def __call__(
        self, context: EventContext, timeperiods_active: CoreTimeperiodsActive
    ) -> object: ...


class _LoopIntervalFunction(Protocol):
    def __call__(self, timeperiods_active: CoreTimeperiodsActive) -> object: ...


def event_keepalive(
    event_function: _EventFunction,
    call_every_loop: _LoopIntervalFunction | None = None,
    loop_interval: int | None = None,
    shutdown_function: Callable[[], object] | None = None,
) -> None:
    last_config_timestamp = config_timestamp()

    # Send signal that we are ready to receive the next event, but
    # not after a config-reload-restart (see below)
    if os.getenv("CMK_EVENT_RESTART") != "1":
        logger.info("Starting in keepalive mode with PID %d", os.getpid())
        _send_reply_ready()
    else:
        logger.info("We are back after a restart.")

    while True:
        try:
            timeperiods_active = TimeperiodActiveCoreLookup(
                livestatus.get_optional_timeperiods_active_map, logger.warning
            )

            # If the configuration has changed, we do a restart. But we do
            # this check just before the next event arrives. We must
            # *not* read data from stdin, just peek! There is still one
            # problem: when restarting we must *not* send the initial '*'
            # byte, because that must be not no sooner then the events
            # has been sent. We do this by setting the environment variable
            # CMK_EVENT_RESTART=1

            if event_data_available(loop_interval):
                if last_config_timestamp != config_timestamp():
                    logger.info("Configuration has changed. Restarting myself.")
                    if shutdown_function:
                        shutdown_function()

                    os.putenv("CMK_EVENT_RESTART", "1")

                    # Close all unexpected file descriptors before invoking
                    # execvp() to prevent inheritance of them. In CMK-1085 we
                    # had an issue related to os.urandom() which kept FDs open.
                    # This specific issue of Python 2.7.9 should've been fixed
                    # since Python 2.7.10. Just to be sure we keep cleaning up.
                    cmk.ccc.daemon.closefrom(3)

                    os.execvp("cmk", sys.argv)

                data = b""
                while not data.endswith(b"\n\n"):
                    try:
                        new_data = b""
                        new_data = os.read(0, 32768)
                    except OSError:
                        new_data = b""
                    except Exception as e:
                        if cmk.ccc.debug.enabled():
                            raise
                        logger.info("Cannot read data from CMC: %s", e)

                    if not new_data:
                        logger.info("CMC has closed the connection. Shutting down.")
                        if shutdown_function:
                            shutdown_function()
                        sys.exit(0)  # closed stdin, this is
                    data += new_data

                try:
                    context = raw_context_from_string(data.rstrip(b"\n").decode("utf-8"))
                    event_function(context, timeperiods_active)
                except Exception:
                    if cmk.ccc.debug.enabled():
                        raise
                    logger.exception("ERROR:")

                # Signal that we are ready for the next event
                _send_reply_ready()

        except Exception:
            if cmk.ccc.debug.enabled():
                raise
            logger.exception("ERROR:")

        if call_every_loop:
            try:
                call_every_loop(timeperiods_active)
            except Exception:
                if cmk.ccc.debug.enabled():
                    raise
                logger.exception("ERROR:")


def config_timestamp() -> float:
    mtime = 0.0
    for dirpath, _unused_dirnames, filenames in os.walk(str(cmk.utils.paths.check_mk_config_dir)):
        for f in filenames:
            mtime = max(mtime, os.stat(dirpath + "/" + f).st_mtime)

    for path in [
        cmk.utils.paths.main_config_file,
        cmk.utils.paths.final_config_file,
        cmk.utils.paths.local_config_file,
    ]:
        try:
            mtime = max(mtime, os.stat(path).st_mtime)
        except Exception:
            pass
    return mtime


def event_data_available(loop_interval: int | None) -> bool:
    return bool(select.select([0], [], [], loop_interval)[0])


def pipe_decode_raw_context(raw_context: EventContext) -> None:
    """
    cmk_base replaces all occurrences of the pipe symbol in the infotext with
    the character "Light vertical bar" before a check result is submitted to
    the core. We remove this special encoding here since it may result in
    gibberish output when deliered via a notification plug-in.
    """

    def _remove_pipe_encoding(value: str) -> str:
        return value.replace("\u2758", "|")

    output = raw_context.get("SERVICEOUTPUT")
    if output:
        raw_context["SERVICEOUTPUT"] = _remove_pipe_encoding(output)
    long_output = raw_context.get("LONGSERVICEOUTPUT")
    if long_output:
        raw_context["LONGSERVICEOUTPUT"] = _remove_pipe_encoding(long_output)


def raw_context_from_string(data: str) -> EventContext:
    # Context is line-by-line in g_notify_readahead_buffer
    context: EventContext = {}
    if not data:
        return context
    try:
        for line in data.split("\n"):
            varname, value = line.strip().split("=", 1)
            # Dynamically adding to TypedDict...
            context[varname] = expand_backslashes(value)  # type: ignore[literal-required]
    except Exception:  # line without '=' ignored or alerted
        if cmk.ccc.debug.enabled():
            raise
    pipe_decode_raw_context(context)
    return context


def expand_backslashes(value: str) -> str:
    # We cannot do the following:
    # value.replace(r"\n", "\n").replace("\\\\", "\\")
    # \\n would be exapnded to \<LF> instead of \n. This was a bug
    # in previous versions.
    return value.replace("\\\\", "\0").replace("\\n", "\n").replace("\0", "\\")


def render_context_dump(raw_context: EventContext) -> str:
    return "Raw context:\n" + "\n".join(
        "                    %s=%s" % v for v in sorted(raw_context.items())
    )


def find_host_service_in_context(context: EventContext) -> str:
    host = context.get("HOSTNAME", "UNKNOWN")
    service = context.get("SERVICEDESC")
    if service:
        return host + ";" + service
    return host


# Fetch information about an objects contacts via Livestatus. This is
# necessary for notifications from Nagios, which does not send this
# information in macros.
def livestatus_fetch_contacts(host: HostName, service: ServiceName | None) -> ContactList | None:
    try:
        if service:
            query = f"GET services\nFilter: host_name = {host}\nFilter: service_description = {service}\nColumns: contacts"
        else:
            query = "GET hosts\nFilter: host_name = %s\nColumns: contacts" % host

        contact_list = livestatus.LocalConnection().query_value(query)
        if (
            "check-mk-notify" in contact_list
        ):  # Remove artifical contact used for rule based notifications
            contact_list.remove("check-mk-notify")
        return contact_list

    except livestatus.MKLivestatusNotFoundError:
        if not service:
            return None

        # Service not found: try again with contacts of host!
        return livestatus_fetch_contacts(host, None)

    except Exception:
        if cmk.ccc.debug.enabled():
            raise
        return None  # We must allow notifications without Livestatus access


def add_rulebased_macros(
    raw_context: EventContext,
    ensure_nagios: Callable[[str], object],
    contacts_needed: bool,
) -> None:
    # For the rule based notifications we need the list of contacts
    # an object has. The CMC does send this in the macro "CONTACTS"
    if "CONTACTS" not in raw_context and contacts_needed:
        # Ensure that we don't reach this when the Micro Core is enabled. Triggering this logic
        # with the Micro Core might result in dead locks.
        ensure_nagios(
            "Missing 'CONTACTS' in raw notification context. It should always "
            "be available when using the Micro Core."
        )

        contact_list = livestatus_fetch_contacts(
            HostName(raw_context["HOSTNAME"]), raw_context.get("SERVICEDESC")
        )
        if contact_list is not None:
            raw_context["CONTACTS"] = ",".join(contact_list)
        else:
            raw_context["CONTACTS"] = "?"  # means: contacts could not be determined!

    # Add a pseudo contact name. This is needed for the correct creation
    # of spool files. Spool files are created on a per-contact-base, as in classical
    # notifications the core sends out one individual notification per contact.
    # In the case of rule based notifications we do not make distinctions between
    # the various contacts.
    raw_context["CONTACTNAME"] = "check-mk-notify"


def complete_raw_context(
    raw_context: EventContext,
    ensure_nagios: Callable[[str], object],
    with_dump: bool,
    contacts_needed: bool,
    analyse: bool,
) -> EnrichedEventContext:
    """Extend the raw notification context

    This ensures that all raw contexts processed in the notification code has specific variables
    set. Add a few further helper variables that are useful in notification and alert plugins.
    """
    raw_keys = list(raw_context)

    # If a remote site has send the spool file to the central site and the user
    # uses "Analyze ruleset", the key "OMD_SITE" is already present. So there is
    # no need to enrich the raw_context again. This also avoids overwriting
    # of sitespecific values.
    enriched_context = cast(EnrichedEventContext, raw_context.copy())
    if "OMD_SITE" in raw_context:
        return enriched_context

    try:
        # "SITEOFHOST" is only set in case of test notifications
        enriched_context["OMD_SITE"] = (
            raw_context["SITEOFHOST"] if analyse and "SITEOFHOST" in raw_context else omd_site()  # type: ignore[typeddict-item]
        )

        enriched_context["WHAT"] = "SERVICE" if enriched_context.get("SERVICEDESC") else "HOST"

        enriched_context.setdefault("MONITORING_HOST", socket.gethostname())
        enriched_context.setdefault("OMD_ROOT", str(cmk.utils.paths.omd_root))

        # The Checkmk Micro Core sends the MICROTIME and no other time stamps. We add
        # a few Nagios-like variants in order to be compatible
        if "MICROTIME" in enriched_context:
            microtime = int(enriched_context["MICROTIME"])
            timestamp = float(microtime) / 1000000.0
            broken = time.localtime(timestamp)
            enriched_context["DATE"] = time.strftime("%Y-%m-%d", broken)
            enriched_context["SHORTDATETIME"] = time.strftime("%Y-%m-%d %H:%M:%S", broken)
            enriched_context["LONGDATETIME"] = time.strftime("%a %b %d %H:%M:%S %Z %Y", broken)
        elif "MICROTIME" not in enriched_context:
            # In case the microtime is not provided, e.g. when using Nagios, then set it here
            # from the current time. We could look for "LONGDATETIME" and calculate the timestamp
            # from that one, but we try to keep this simple here.
            enriched_context["MICROTIME"] = "%d" % (time.time() * 1000000)

        enriched_context["HOSTURL"] = "/check_mk/index.py?start_url=view.py?%s" % quote(
            urlencode(
                [
                    ("view_name", "hoststatus"),
                    ("host", enriched_context["HOSTNAME"]),
                    ("site", enriched_context["OMD_SITE"]),
                ]
            )
        )
        if enriched_context["WHAT"] == "SERVICE":
            enriched_context["SERVICEURL"] = "/check_mk/index.py?start_url=view.py?%s" % quote(
                urlencode(
                    [
                        ("view_name", "service"),
                        ("host", enriched_context["HOSTNAME"]),
                        ("service", enriched_context["SERVICEDESC"]),
                        ("site", enriched_context["OMD_SITE"]),
                    ]
                )
            )

        # Relative Timestamps for several macros
        if (value := enriched_context.get("LASTHOSTSTATECHANGE")) is not None:
            enriched_context["LASTHOSTSTATECHANGE_REL"] = get_readable_rel_date(value)
        if (value := enriched_context.get("LASTSERVICESTATECHANGE")) is not None:
            enriched_context["LASTSERVICESTATECHANGE_REL"] = get_readable_rel_date(value)
        if (value := enriched_context.get("LASTHOSTUP")) is not None:
            enriched_context["LASTHOSTUP_REL"] = get_readable_rel_date(value)
        if (value := enriched_context.get("LASTSERVICEOK")) is not None:
            enriched_context["LASTSERVICEOK_REL"] = get_readable_rel_date(value)

        add_rulebased_macros(enriched_context, ensure_nagios, contacts_needed)

        # For custom notifications the number is set to 0 by the core (Nagios and CMC). We force at least
        # number 1 here, so that rules with conditions on numbers do not fail (the minimum is 1 here)
        if enriched_context.get("HOSTNOTIFICATIONNUMBER") == "0":
            if with_dump:
                logger.info("Setting HOSTNOTIFICATIONNUMBER for notification from '0' to '1'")
            enriched_context["HOSTNOTIFICATIONNUMBER"] = "1"
        if enriched_context.get("SERVICENOTIFICATIONNUMBER") == "0":
            if with_dump:
                logger.info("Setting SERVICENOTIFICATIONNUMBER for notification from '0' to '1'")
            enriched_context["SERVICENOTIFICATIONNUMBER"] = "1"

        # Add the previous hard state. This is necessary for notification rules that depend on certain transitions,
        # like OK -> WARN (but not CRIT -> WARN). The CMC sends PREVIOUSHOSTHARDSTATE and PREVIOUSSERVICEHARDSTATE.
        # Nagios does not have this information and we try to deduct this.
        if "PREVIOUSHOSTHARDSTATE" not in enriched_context and "LASTHOSTSTATE" in enriched_context:
            prev_state = enriched_context["LASTHOSTSTATE"]
            # When the attempts are > 1 then the last state could be identical with
            # the current one, e.g. both critical. In that case we assume the
            # previous hard state to be OK.
            if prev_state == enriched_context["HOSTSTATE"]:
                prev_state = "UP"
            elif "HOSTATTEMPT" not in enriched_context or (
                "HOSTATTEMPT" in enriched_context and enriched_context["HOSTATTEMPT"] != "1"
            ):
                # Here We do not know. The transition might be OK -> WARN -> CRIT and
                # the initial OK is completely lost. We use the artificial state "?"
                # here, which matches all states and makes sure that when in doubt a
                # notification is being sent out. But when the new state is UP, then
                # we know that the previous state was a hard state (otherwise there
                # would not have been any notification)
                if enriched_context["HOSTSTATE"] != "UP":
                    prev_state = "?"
                logger.info("Previous host hard state not known. Allowing all states.")
            enriched_context["PREVIOUSHOSTHARDSTATE"] = prev_state

        # Same for services
        if (
            enriched_context["WHAT"] == "SERVICE"
            and "PREVIOUSSERVICEHARDSTATE" not in enriched_context
        ):
            prev_state = enriched_context["LASTSERVICESTATE"]
            if prev_state == enriched_context["SERVICESTATE"]:
                prev_state = "OK"
            elif "SERVICEATTEMPT" not in enriched_context or (
                "SERVICEATTEMPT" in enriched_context and enriched_context["SERVICEATTEMPT"] != "1"
            ):
                if raw_context["SERVICESTATE"] != "OK":
                    prev_state = "?"
                logger.info("Previous service hard state not known. Allowing all states.")
            enriched_context["PREVIOUSSERVICEHARDSTATE"] = prev_state

        # Add short variants for state names (at most 4 characters)
        for ctx_key, ctx_value in list(enriched_context.items()):
            assert isinstance(ctx_value, str)
            if ctx_key.endswith("STATE"):
                # dynamical keys are bad...
                enriched_context[ctx_key[:-5] + "SHORTSTATE"] = ctx_value[:4]  # type: ignore[literal-required]

        if enriched_context["WHAT"] == "SERVICE":
            enriched_context["SERVICEFORURL"] = quote(enriched_context["SERVICEDESC"])
        enriched_context["HOSTFORURL"] = quote(enriched_context["HOSTNAME"])

        _update_enriched_context_from_notify_host_file(enriched_context)

    except Exception as e:
        logger.info("Error on completing raw context: %s", e)

    if with_dump:
        log_context = "\n".join(
            sorted(
                [
                    f"                    {key}={value}"
                    for key, value in enriched_context.items()
                    if key not in raw_keys
                ]
            )
        )
        logger.info("Computed variables:\n%s", log_context)

    return enriched_context


def _update_enriched_context_from_notify_host_file(enriched_context: EnrichedEventContext) -> None:
    notify_host_config = read_notify_host_file(HostName(enriched_context["HOSTNAME"]))
    for k, v in notify_host_config.host_labels.items():
        # Dynamically added keys...
        enriched_context["HOSTLABEL_" + k] = v  # type: ignore[literal-required]
    if enriched_context["WHAT"] == "SERVICE":
        for k, v in notify_host_config.service_labels.get(
            enriched_context["SERVICEDESC"], {}
        ).items():
            # Dynamically added keys...
            enriched_context["SERVICELABEL_" + k] = v  # type: ignore[literal-required]

    for k, v in notify_host_config.tags.items():
        enriched_context["HOSTTAG_" + k] = v  # type: ignore[literal-required]


# TODO: Use cmk.utils.render.*?
def get_readable_rel_date(timestamp: Any) -> str:
    try:
        change = int(timestamp)
    except ValueError:
        change = 0
    rel_time = time.time() - change
    seconds = rel_time % 60
    rem = rel_time / 60.0
    minutes = rem % 60
    hours = (rem % 1440) / 60.0
    days = rem / 1440.0
    return "%dd %02d:%02d:%02d" % (days, hours, minutes, seconds)


# While the rest of the world increasingly embraces lambdas and folds, the
# Python world moves backwards in time. :-P So let's introduce this helper...
def apply_matchers(
    matchers: Iterable[Matcher],
    rule: EventRule,
    context: EnrichedEventContext | EventContext,
    analyse: bool,
    all_timeperiods: TimeperiodSpecs,
) -> str | None:
    for matcher in matchers:
        try:
            result = matcher(rule, context, analyse, all_timeperiods)
        except Exception:
            return f"Error in matcher: {traceback.format_exc()}"
        if result is not None:
            return result
    return None


def event_match_rule(
    rule: EventRule,
    context: EventContext,
    define_servicegroups: Mapping[str, str],
    all_timeperiods: TimeperiodSpecs,
    analyse: bool,
    timeperiods_active: CoreTimeperiodsActive,
) -> str | None:
    return apply_matchers(
        [
            event_match_site,
            event_match_folder,
            event_match_hosttags,
            event_match_hostgroups,
            lambda rule, context, analyse, all_timeperiods: event_match_servicegroups_fixed(
                rule,
                context,
                define_servicegroups=define_servicegroups,
                _all_timeperiods=all_timeperiods,
                _analyse=analyse,
            ),
            lambda rule, context, analyse, all_timeperiods: event_match_exclude_servicegroups_fixed(
                rule,
                context,
                define_servicegroups=define_servicegroups,
                _all_timeperiods=all_timeperiods,
                _analyse=analyse,
            ),
            lambda rule, context, analyse, all_timeperiods: event_match_servicegroups_regex(
                rule,
                context,
                define_servicegroups=define_servicegroups,
                _all_timeperiods=all_timeperiods,
                _analyse=analyse,
            ),
            lambda rule, context, analyse, all_timeperiods: event_match_exclude_servicegroups_regex(
                rule,
                context,
                define_servicegroups=define_servicegroups,
            ),
            event_match_contacts,
            event_match_contactgroups,
            event_match_hosts,
            event_match_exclude_hosts,
            event_match_services,
            event_match_exclude_services,
            event_match_plugin_output,
            event_match_checktype,
            lambda rule, context, analyse, all_timeperiods: event_match_timeperiod(
                rule, analyse, timeperiods_active
            ),
            event_match_servicelevel,
            event_match_hostlabels,
            event_match_servicelabels,
        ],
        rule,
        context,
        analyse,
        all_timeperiods,
    )


def event_match_site(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_site" not in rule:
        return None

    required_site_ids = rule["match_site"]

    # Fallback to local site ID in case there is none in the context
    site_id = context.get("OMD_SITE", omd_site())

    if site_id not in required_site_ids:
        return "The site '{}' is not in the required sites list: {}".format(
            site_id,
            ",".join(required_site_ids),
        )
    return None


def event_match_folder(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_folder" in rule:
        mustfolder = rule["match_folder"]
        mustpath = mustfolder.split("/")
        hasfolder = None
        for tag in context.get("HOSTTAGS", "").split():
            if tag.startswith("/wato/"):
                hasfolder = tag[6:].rstrip("/")
                haspath = hasfolder.split("/")
                if mustpath == [
                    "",
                ]:
                    return None  # Match is on main folder, always OK
                while mustpath:
                    if not haspath or mustpath[0] != haspath[0]:
                        return f"The rule requires folder '{mustfolder}', but the host is in '{hasfolder}'"
                    mustpath = mustpath[1:]
                    haspath = haspath[1:]

        if hasfolder is None:
            return "The host is not managed in Setup, but the rule requires a folder"
    return None


def event_match_hosttags(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    required_tags = rule.get("match_hosttags")
    if required_tags:
        context_str = "HOSTTAG_"
        host_tags = {
            TagGroupID(variable.replace(context_str, "")): TagID(str(value))
            for variable, value in context.items()
            if variable.startswith(context_str)
        }
        if not matches_host_tags(set(host_tags.items()), required_tags):
            return f"The host's tags {host_tags} do not match the required tags {required_tags}"
    return None


def event_match_servicegroups_fixed(
    rule: EventRule,
    context: EventContext,
    define_servicegroups: Mapping[str, str],
    _all_timeperiods: TimeperiodSpecs,
    _analyse: bool,
) -> str | None:
    return _event_match_servicegroups(
        rule, context, define_servicegroups=define_servicegroups, is_regex=False
    )


def event_match_servicegroups_regex(
    rule: EventRule,
    context: EventContext,
    define_servicegroups: Mapping[str, str],
    _all_timeperiods: TimeperiodSpecs,
    _analyse: bool,
) -> str | None:
    return _event_match_servicegroups(
        rule, context, define_servicegroups=define_servicegroups, is_regex=True
    )


def _event_match_servicegroups(
    rule: EventRule,
    context: EventContext,
    define_servicegroups: Mapping[str, str],
    *,
    is_regex: bool,
) -> str | None:
    if is_regex:
        match_type, required_groups = rule.get("match_servicegroups_regex", (None, None))
    else:
        required_groups = rule.get("match_servicegroups")

    if context["WHAT"] != "SERVICE":
        if required_groups:
            return (
                "This rule requires membership in a service group, but this is a host notification"
            )
        return None

    if required_groups is not None:
        sgn = context.get("SERVICEGROUPNAMES")
        if sgn is None:
            return (
                "No information about service groups is in the context, but service "
                "must be in group %s" % (" or ".join(required_groups))
            )
        if sgn:
            servicegroups = sgn.split(",")
        else:
            return "The service is in no service group, but {}{} is required".format(
                (is_regex and "regex " or ""),
                " or ".join(required_groups),
            )

        for group in required_groups:
            if is_regex:
                r = regex(group)
                for sg in servicegroups:
                    match_value = define_servicegroups[sg] if match_type == "match_alias" else sg
                    if r.search(match_value):
                        return None
            elif group in servicegroups:
                return None

        if is_regex:
            if match_type == "match_alias":
                return (
                    "The service is only in the groups %s. None of these patterns match: %s"
                    % (
                        '"' + '", "'.join(define_servicegroups[x] for x in servicegroups) + '"',
                        '"' + '" or "'.join(required_groups),
                    )
                    + '"'
                )

            return (
                "The service is only in the groups {}. None of these patterns match: {}".format(
                    '"' + '", "'.join(servicegroups) + '"', '"' + '" or "'.join(required_groups)
                )
                + '"'
            )

        return "The service is only in the groups {}, but {} is required".format(
            sgn,
            " or ".join(required_groups),
        )
    return None


def event_match_exclude_servicegroups_fixed(
    rule: EventRule,
    context: EventContext,
    define_servicegroups: Mapping[str, str],
    _all_timeperiods: TimeperiodSpecs,
    _analyse: bool,
) -> str | None:
    return _event_match_exclude_servicegroups(
        rule, context, define_servicegroups=define_servicegroups, is_regex=False
    )


def event_match_exclude_servicegroups_regex(
    rule: EventRule,
    context: EventContext,
    define_servicegroups: Mapping[str, str],
) -> str | None:
    return _event_match_exclude_servicegroups(
        rule, context, define_servicegroups=define_servicegroups, is_regex=True
    )


def _event_match_exclude_servicegroups(
    rule: EventRule,
    context: EventContext,
    define_servicegroups: Mapping[str, str],
    *,
    is_regex: bool,
) -> str | None:
    if is_regex:
        match_type, excluded_groups = rule.get("match_exclude_servicegroups_regex", (None, None))
    else:
        excluded_groups = rule.get("match_exclude_servicegroups")

    if context["WHAT"] != "SERVICE":
        # excluded_groups do not apply to a host notification
        return None

    if excluded_groups is not None:
        context_sgn = context.get("SERVICEGROUPNAMES")
        if not context_sgn:
            # No actual groups means no possible negative match
            return None

        servicegroups = context_sgn.split(",")

        for group in excluded_groups:
            if is_regex:
                r = regex(group)
                for sg in servicegroups:
                    match_value = define_servicegroups[sg] if match_type == "match_alias" else sg
                    match_value_inverse = (
                        sg if match_type == "match_alias" else define_servicegroups[sg]
                    )

                    if r.search(match_value):
                        return f'The service group "{match_value}" ({match_value_inverse}) is excluded per regex pattern: {group}'
            elif group in servicegroups:
                return "The service group %s is excluded" % group
    return None


def event_match_contacts(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_contacts" not in rule:
        return None

    required_contacts = rule["match_contacts"]
    contacts_text = context["CONTACTS"]
    if not contacts_text:
        return "The object has no contact, but %s is required" % (" or ".join(required_contacts))

    contacts = contacts_text.split(",")
    for contact in required_contacts:
        if contact in contacts:
            return None

    return "The object has the contacts {}, but {} is required".format(
        contacts_text,
        " or ".join(required_contacts),
    )


def event_match_contactgroups(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    required_groups = rule.get("match_contactgroups")
    if required_groups is None:
        return None

    if context["WHAT"] == "SERVICE":
        cgn = context.get("SERVICECONTACTGROUPNAMES")
    else:
        cgn = context.get("HOSTCONTACTGROUPNAMES")

    if cgn is None:
        return None

    if not cgn:
        return "The object is in no group, but %s is required" % (" or ".join(required_groups))

    contactgroups = cgn.split(",")
    for group in required_groups:
        if group in contactgroups:
            return None

    return "The object is only in the groups {}, but {} is required".format(
        cgn,
        " or ".join(required_groups),
    )


def event_match_hostgroups(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    required_groups = rule.get("match_hostgroups")
    if required_groups is not None:
        hgn = context.get("HOSTGROUPNAMES")
        if hgn is None:
            return (
                "No information about host groups is in the context, but host "
                "must be in group %s" % (" or ".join(required_groups))
            )
        if hgn:
            hostgroups = hgn.split(",")
        else:
            return "The host is in no group, but %s is required" % (" or ".join(required_groups))

        for group in required_groups:
            if group in hostgroups:
                return None

        return "The host is only in the groups {}, but {} is required".format(
            hgn,
            " or ".join(required_groups),
        )
    return None


def event_match_hosts(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_hosts" in rule:
        hostlist = rule["match_hosts"]
        if context["HOSTNAME"] not in hostlist:
            return "The host's name '{}' is not on the list of allowed hosts ({})".format(
                context["HOSTNAME"],
                ", ".join(hostlist),
            )
    return None


def event_match_exclude_hosts(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if context["HOSTNAME"] in rule.get("match_exclude_hosts", []):
        return "The host's name '%s' is on the list of excluded hosts" % context["HOSTNAME"]
    return None


def event_match_services(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_services" in rule:
        if context["WHAT"] != "SERVICE":
            return "The rule specifies a list of services, but this is a host notification."
        servicelist = rule["match_services"]
        service = context["SERVICEDESC"]
        if not in_extraconf_servicelist(servicelist, service):
            return (
                "The service's description '%s' does not match by the list of "
                "allowed services (%s)" % (service, ", ".join(servicelist))
            )
    return None


def event_match_exclude_services(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if context["WHAT"] != "SERVICE":
        return None
    excludelist = rule.get("match_exclude_services", [])
    service = context["SERVICEDESC"]
    if in_extraconf_servicelist(excludelist, service):
        return (
            "The service's description '%s' matches the list of excluded services"
            % context["SERVICEDESC"]
        )
    return None


def event_match_plugin_output(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_plugin_output" in rule:
        r = regex(rule["match_plugin_output"])

        if context["WHAT"] == "SERVICE":
            output = context["SERVICEOUTPUT"]
        else:
            output = context["HOSTOUTPUT"]
        if not r.search(output):
            return "The expression '{}' cannot be found in the plug-in output '{}'".format(
                rule["match_plugin_output"],
                output,
            )
    return None


def event_match_checktype(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_checktype" in rule:
        if context["WHAT"] != "SERVICE":
            return "The rule specifies a list of Check_MK plugins, but this is a host notification."
        command = context["SERVICECHECKCOMMAND"]
        if not command.startswith("check_mk-"):
            return "The rule specified a list of Check_MK plugins, but his is no Check_MK service."
        plugin = command[9:]
        allowed = rule["match_checktype"]
        if plugin not in allowed:
            return "The Check_MK plug-in '{}' is not on the list of allowed plugins ({})".format(
                plugin,
                ", ".join(allowed),
            )
    return None


def event_match_timeperiod(
    rule: EventRule,
    analyse: bool,
    timeperiods_active: CoreTimeperiodsActive,
) -> str | None:
    # don't test on notification tests, in that case this is done within
    # notify.rbn_match_timeperiod
    if analyse:
        return None

    if "match_timeperiod" not in rule:
        return None

    timeperiod = rule["match_timeperiod"]
    if timeperiod == "24X7":
        return None

    if timeperiods_active.get(timeperiod, True):
        return None

    return "The timeperiod '%s' is currently not active." % timeperiod


def event_match_servicelevel(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_sl" in rule:
        from_sl, to_sl = rule["match_sl"]
        if context["WHAT"] == "SERVICE" and context.get("SVC_SL", "").isdigit():
            sl = saveint(context.get("SVC_SL"))
        else:
            sl = saveint(context.get("HOST_SL"))

        if sl < from_sl or sl > to_sl:
            return "The service level %d is not between %d and %d." % (sl, from_sl, to_sl)
    return None


def event_match_hostlabels(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_hostlabels" in rule:
        return _event_handle_labels(rule, context, "host")

    return None


def event_match_servicelabels(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_servicelabels" in rule:
        return _event_handle_labels(rule, context, "service")

    return None


def _event_handle_labels(
    rule: EventRule, context: EventContext, what: Literal["host", "service"]
) -> str | None:
    labels: dict[str, Any] = {}
    context_str = "%sLABEL" % what.upper()
    labels = {
        variable.replace("%s_" % context_str, ""): value
        for variable, value in context.items()
        if variable.startswith(context_str)
    }

    key: Literal["match_servicelabels", "match_hostlabels"] = (
        "match_servicelabels" if what == "service" else "match_hostlabels"
    )
    if not set(labels.items()).issuperset(set(rule[key].items())):
        return f"The {what} labels {rule[key]} did not match {labels}"

    return None


def add_context_to_environment(
    plugin_context: Mapping[str, str] | EventContext, prefix: str
) -> None:
    for key, value in plugin_context.items():
        assert isinstance(value, str)
        os.putenv(prefix + key, value.encode("utf-8"))


# recursively turns a python object (with lists, dictionaries and pods) containing parameters
#  into a flat contextlist for use as environment variables in plugins
#
# this: { "LVL1": [{"VALUE": 42}, {"VALUE": 13}] }
# would be added as:
#   PARAMETER_LVL1_1_VALUE = 42
#   PARAMETER_LVL1_2_VALUE = 13
def add_to_event_context(
    context: EventContext | dict[str, str],
    prefix: str,
    param: object,
    get_http_proxy: ProxyGetter,
) -> None:
    if isinstance(param, list | tuple):
        if all(isinstance(p, str) for p in param):
            # TODO: Why on earth do we have these arbitrary differences? Can we unify this?
            suffix, separator = ("S", " ") if isinstance(param, list) else ("", "\t")
            add_to_event_context(context, prefix + suffix, separator.join(param), get_http_proxy)
        for nr, value in enumerate(param, start=1):
            add_to_event_context(context, f"{prefix}_{nr}", value, get_http_proxy)
    elif isinstance(param, dict):  # NOTE: We only handle Dict[str, Any].
        for key, value in param.items():
            varname = f"{prefix}_{key.upper()}"
            if varname == "PARAMETER_PROXY_URL":
                # Compatibility for 1.5 pushover explicitly configured proxy URL format
                if isinstance(value, str):
                    value = ("url", value)
                value = get_http_proxy(value).serialize()
            add_to_event_context(context, varname, value, get_http_proxy)
    elif isinstance(param, str | int | float):  # NOTE: bool is a subclass of int!
        # Dynamically added keys...
        context[prefix] = str(param)  # type: ignore[literal-required]
    elif param is None:
        # Dynamically added keys...
        context[prefix] = ""  # type: ignore[literal-required]
    else:
        # Should never happen
        # Dynamically added keys...
        context[prefix] = repr(param)  # type: ignore[literal-required]


# int() function that return 0 for strings the
# cannot be converted to a number
# TODO: Clean this up!
def saveint(i: Any) -> int:
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0
