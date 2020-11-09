#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This file is being used by the rule based notifications and (CEE
# only) by the alert handling

import logging
import os
import sys
import select
import socket
import time
from urllib.parse import quote
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

from six import ensure_str

import livestatus
import cmk.utils.version as cmk_version
from cmk.utils.regex import regex
import cmk.utils.debug
import cmk.utils.daemon
from cmk.utils.type_defs import EventRule

import cmk.base.config as config
import cmk.base.core

from cmk.utils.type_defs import (
    HostName,
    ServiceName,
)

ContactList = List  # TODO Improve this
EventContext = Dict[str, Any]  # TODO Improve this
# We actually want to use Matcher for all our matchers, but mypy is too dumb to
# use that for function types, see https://github.com/python/mypy/issues/1641.
Matcher = Callable[[EventRule, EventContext], Optional[str]]

logger = logging.getLogger('cmk.base.events')


def event_keepalive(event_function: Callable,
                    call_every_loop: Optional[Callable] = None,
                    loop_interval: Optional[int] = None,
                    shutdown_function: Optional[Callable] = None) -> None:
    last_config_timestamp = config_timestamp()

    # Send signal that we are ready to receive the next event, but
    # not after a config-reload-restart (see below)
    if os.getenv("CMK_EVENT_RESTART") != "1":
        logger.info("Starting in keepalive mode with PID %d", os.getpid())
        sys.stdout.write("*")
        sys.stdout.flush()
    else:
        logger.info("We are back after a restart.")

    while True:
        try:
            # Invalidate timeperiod caches
            cmk.base.core.cleanup_timeperiod_caches()

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
                    cmk.utils.daemon.closefrom(3)

                    os.execvp("cmk", sys.argv)

                data = b""
                while not data.endswith(b"\n\n"):
                    try:
                        new_data = b""
                        new_data = os.read(0, 32768)
                    except IOError:
                        new_data = b""
                    except Exception as e:
                        if cmk.utils.debug.enabled():
                            raise
                        logger.info("Cannot read data from CMC: %s", e)

                    if not new_data:
                        logger.info("CMC has closed the connection. Shutting down.")
                        if shutdown_function:
                            shutdown_function()
                        sys.exit(0)  # closed stdin, this is
                    data += new_data

                try:
                    context = raw_context_from_string(data.rstrip(b'\n'))
                    event_function(context)
                except Exception:
                    if cmk.utils.debug.enabled():
                        raise
                    logger.exception("ERROR:")

                # Signal that we are ready for the next event
                sys.stdout.write("*")
                sys.stdout.flush()

        # Fix vor Python 2.4:
        except SystemExit as e:
            sys.exit(e)
        except Exception:
            if cmk.utils.debug.enabled():
                raise
            logger.exception("ERROR:")

        if call_every_loop:
            try:
                call_every_loop()
            except Exception:
                if cmk.utils.debug.enabled():
                    raise
                logger.exception("ERROR:")


def config_timestamp() -> float:
    mtime = 0.0
    for dirpath, _unused_dirnames, filenames in os.walk(cmk.utils.paths.check_mk_config_dir):
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


def event_data_available(loop_interval: Optional[int]) -> bool:
    return bool(select.select([0], [], [], loop_interval)[0])


def pipe_decode_raw_context(raw_context: EventContext) -> None:
    """
    cmk_base replaces all occurences of the pipe symbol in the infotext with
    the character "Light vertical bar" before a check result is submitted to
    the core. We remove this special encoding here since it may result in
    gibberish output when deliered via a notification plugin.
    """
    def _remove_pipe_encoding(value):
        return value.replace(u"\u2758", u"|")

    output = raw_context.get('SERVICEOUTPUT')
    if output:
        raw_context['SERVICEOUTPUT'] = _remove_pipe_encoding(output)
    long_output = raw_context.get('LONGSERVICEOUTPUT')
    if long_output:
        raw_context['LONGSERVICEOUTPUT'] = _remove_pipe_encoding(long_output)


def raw_context_from_string(data: bytes) -> EventContext:
    # Context is line-by-line in g_notify_readahead_buffer
    context: EventContext = {}
    try:
        for line in data.split(b'\n'):
            varname, value = ensure_str(line.strip()).split("=", 1)
            context[varname] = expand_backslashes(value)
    except Exception:  # line without '=' ignored or alerted
        if cmk.utils.debug.enabled():
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
    return "Raw context:\n" + "\n".join("                    %s=%s" % v  #
                                        for v in sorted(raw_context.items()))


def find_host_service_in_context(context: EventContext) -> str:
    host = context.get("HOSTNAME", "UNKNOWN")
    service = context.get("SERVICEDESC")
    if service:
        return host + ";" + service
    return host


# Fetch information about an objects contacts via Livestatus. This is
# neccessary for notifications from Nagios, which does not send this
# information in macros.
def livestatus_fetch_contacts(host: HostName,
                              service: Optional[ServiceName]) -> Optional[ContactList]:
    try:
        if service:
            query = "GET services\nFilter: host_name = %s\nFilter: service_description = %s\nColumns: contacts" % (
                host, service)
        else:
            query = "GET hosts\nFilter: host_name = %s\nColumns: contacts" % host

        contact_list = livestatus.LocalConnection().query_value(query)
        if "check-mk-notify" in contact_list:  # Remove artifical contact used for rule based notifications
            contact_list.remove("check-mk-notify")
        return contact_list

    except livestatus.MKLivestatusNotFoundError:
        if not service:
            return None

        # Service not found: try again with contacts of host!
        return livestatus_fetch_contacts(host, None)

    except Exception:
        if cmk.utils.debug.enabled():
            raise
        return None  # We must allow notifications without Livestatus access


def add_rulebased_macros(raw_context: EventContext) -> None:
    # For the rule based notifications we need the list of contacts
    # an object has. The CMC does send this in the macro "CONTACTS"
    if "CONTACTS" not in raw_context:
        contact_list = livestatus_fetch_contacts(raw_context["HOSTNAME"],
                                                 raw_context.get("SERVICEDESC"))
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


def complete_raw_context(raw_context: EventContext, with_dump: bool) -> None:
    """Extend the raw notification context

    This ensures that all raw contexts processed in the notification code has specific variables
    set. Add a few further helper variables that are useful in notification and alert plugins.

    Please not that this is not only executed on the source system. When notifications are
    forwarded to another site and the analysis is executed on that site, this function will be
    executed on the central site. So be sure not to overwrite site specific things.
    """

    raw_keys = list(raw_context)

    try:
        raw_context["WHAT"] = "SERVICE" if raw_context.get("SERVICEDESC") else "HOST"

        raw_context.setdefault("MONITORING_HOST", socket.gethostname())
        raw_context.setdefault("OMD_ROOT", cmk.utils.paths.omd_root)
        raw_context.setdefault("OMD_SITE", cmk_version.omd_site())

        # The Checkmk Micro Core sends the MICROTIME and no other time stamps. We add
        # a few Nagios-like variants in order to be compatible
        if "MICROTIME" in raw_context:
            microtime = int(raw_context["MICROTIME"])
            timestamp = float(microtime) / 1000000.0
            broken = time.localtime(timestamp)
            raw_context["DATE"] = time.strftime("%Y-%m-%d", broken)
            raw_context["SHORTDATETIME"] = time.strftime("%Y-%m-%d %H:%M:%S", broken)
            raw_context["LONGDATETIME"] = time.strftime("%a %b %d %H:%M:%S %Z %Y", broken)
        elif "MICROTIME" not in raw_context:
            # In case the microtime is not provided, e.g. when using Nagios, then set it here
            # from the current time. We could look for "LONGDATETIME" and calculate the timestamp
            # from that one, but we try to keep this simple here.
            raw_context["MICROTIME"] = "%d" % (time.time() * 1000000)

        url_host_view = 'view.py?view_name=hoststatus&host=%s&site=%s' % (raw_context['HOSTNAME'],
                                                                          raw_context['OMD_SITE'])
        raw_context['HOSTURL'] = '/check_mk/index.py?start_url=%s' % quote(url_host_view)

        if raw_context['WHAT'] == 'SERVICE':
            url_service_view = 'view.py?view_name=service&host=%s&service=%s&site=%s' % (
                raw_context['HOSTNAME'], raw_context['SERVICEDESC'], raw_context['OMD_SITE'])
            raw_context['SERVICEURL'] = '/check_mk/index.py?start_url=%s' % quote(url_service_view)

        # Relative Timestamps for several macros
        for macro in [
                'LASTHOSTSTATECHANGE', 'LASTSERVICESTATECHANGE', 'LASTHOSTUP', 'LASTSERVICEOK'
        ]:
            if macro in raw_context:
                raw_context[macro + '_REL'] = get_readable_rel_date(raw_context[macro])

        # Rule based notifications enabled? We might need to complete a few macros
        contact = raw_context.get("CONTACTNAME")
        if not contact or contact == "check-mk-notify":
            add_rulebased_macros(raw_context)

        # For custom notifications the number is set to 0 by the core (Nagios and CMC). We force at least
        # number 1 here, so that rules with conditions on numbers do not fail (the minimum is 1 here)
        for key in ["HOSTNOTIFICATIONNUMBER", "SERVICENOTIFICATIONNUMBER"]:
            if key in raw_context and raw_context[key] == "0":
                if with_dump:
                    logger.info("Setting %s for notification from '0' to '1'", key)
                raw_context[key] = "1"

        # Add the previous hard state. This is neccessary for notification rules that depend on certain transitions,
        # like OK -> WARN (but not CRIT -> WARN). The CMC sends PREVIOUSHOSTHARDSTATE and PREVIOUSSERVICEHARDSTATE.
        # Nagios does not have this information and we try to deduct this.
        if "PREVIOUSHOSTHARDSTATE" not in raw_context and "LASTHOSTSTATE" in raw_context:
            prev_state = raw_context["LASTHOSTSTATE"]
            # When the attempts are > 1 then the last state could be identical with
            # the current one, e.g. both critical. In that case we assume the
            # previous hard state to be OK.
            if prev_state == raw_context["HOSTSTATE"]:
                prev_state = "UP"
            elif "HOSTATTEMPT" not in raw_context or \
                ("HOSTATTEMPT" in raw_context and raw_context["HOSTATTEMPT"] != "1"):
                # Here We do not know. The transition might be OK -> WARN -> CRIT and
                # the initial OK is completely lost. We use the artificial state "?"
                # here, which matches all states and makes sure that when in doubt a
                # notification is being sent out. But when the new state is UP, then
                # we know that the previous state was a hard state (otherwise there
                # would not have been any notification)
                if raw_context["HOSTSTATE"] != "UP":
                    prev_state = "?"
                logger.info("Previous host hard state not known. Allowing all states.")
            raw_context["PREVIOUSHOSTHARDSTATE"] = prev_state

        # Same for services
        if raw_context["WHAT"] == "SERVICE" and "PREVIOUSSERVICEHARDSTATE" not in raw_context:
            prev_state = raw_context["LASTSERVICESTATE"]
            if prev_state == raw_context["SERVICESTATE"]:
                prev_state = "OK"
            elif "SERVICEATTEMPT" not in raw_context or \
                ("SERVICEATTEMPT" in raw_context and raw_context["SERVICEATTEMPT"] != "1"):
                if raw_context["SERVICESTATE"] != "OK":
                    prev_state = "?"
                logger.info("Previous service hard state not known. Allowing all states.")
            raw_context["PREVIOUSSERVICEHARDSTATE"] = prev_state

        # Add short variants for state names (at most 4 characters)
        for key, value in list(raw_context.items()):
            if key.endswith("STATE"):
                raw_context[key[:-5] + "SHORTSTATE"] = value[:4]

        if raw_context["WHAT"] == "SERVICE":
            raw_context['SERVICEFORURL'] = quote(raw_context['SERVICEDESC'])
        raw_context['HOSTFORURL'] = quote(raw_context['HOSTNAME'])

    except Exception as e:
        logger.info("Error on completing raw context: %s", e)

    if with_dump:
        log_context = "\n".join(
            sorted([
                "                    %s=%s" % (k, raw_context[k])
                for k in raw_context
                if k not in raw_keys
            ]))
        logger.info("Computed variables:\n%s", log_context)


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
    return '%dd %02d:%02d:%02d' % (days, hours, minutes, seconds)


# While the rest of the world increasingly embraces lambdas and folds, the
# Python world moves backwards in time. :-P So let's introduce this helper...
def apply_matchers(matchers: Iterable[Matcher], rule: EventRule,
                   context: EventContext) -> Optional[str]:
    for matcher in matchers:
        result = matcher(rule, context)
        if result is not None:
            return result
    return None


def event_match_rule(rule: EventRule, context: EventContext) -> Optional[str]:
    return apply_matchers([
        event_match_site,
        event_match_folder,
        event_match_hosttags,
        event_match_hostgroups,
        event_match_servicegroups_fixed,
        event_match_exclude_servicegroups_fixed,
        event_match_servicegroups_regex,
        event_match_exclude_servicegroups_regex,
        event_match_contacts,
        event_match_contactgroups,
        event_match_hosts,
        event_match_exclude_hosts,
        event_match_services,
        event_match_exclude_services,
        event_match_plugin_output,
        event_match_checktype,
        event_match_timeperiod,
        event_match_servicelevel,
    ], rule, context)


def event_match_site(rule: EventRule, context: EventContext) -> Optional[str]:
    if "match_site" not in rule:
        return None

    required_site_ids = rule["match_site"]

    # Fallback to local site ID in case there is none in the context
    site_id = context.get("OMD_SITE", cmk_version.omd_site())

    if site_id not in required_site_ids:
        return "The site '%s' is not in the required sites list: %s" % \
                        (site_id, ",".join(required_site_ids))
    return None


def event_match_folder(rule: EventRule, context: EventContext) -> Optional[str]:
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
                        return "The rule requires WATO folder '%s', but the host is in '%s'" % (
                            mustfolder, hasfolder)
                    mustpath = mustpath[1:]
                    haspath = haspath[1:]

        if hasfolder is None:
            return "The host is not managed via WATO, but the rule requires a WATO folder"
    return None


def event_match_hosttags(rule: EventRule, context: EventContext) -> Optional[str]:
    required = rule.get("match_hosttags")
    if required:
        tags = context.get("HOSTTAGS", "").split()
        if not config.hosttags_match_taglist(tags, required):
            return "The host's tags %s do not match the required tags %s" % ("|".join(tags),
                                                                             "|".join(required))
    return None


def event_match_servicegroups_fixed(rule: EventRule, context: EventContext) -> Optional[str]:
    return _event_match_servicegroups(rule, context, is_regex=False)


def event_match_servicegroups_regex(rule: EventRule, context: EventContext) -> Optional[str]:
    return _event_match_servicegroups(rule, context, is_regex=True)


def _event_match_servicegroups(rule: EventRule, context: EventContext,
                               is_regex: bool) -> Optional[str]:
    if is_regex:
        match_type, required_groups = rule.get("match_servicegroups_regex", (None, None))
    else:
        required_groups = rule.get("match_servicegroups")

    if context["WHAT"] != "SERVICE":
        if required_groups:
            return "This rule requires membership in a service group, but this is a host notification"
        return None

    if required_groups is not None:
        sgn = context.get("SERVICEGROUPNAMES")
        if sgn is None:
            return ("No information about service groups is in the context, but service "
                    "must be in group %s" % (" or ".join(required_groups)))
        if sgn:
            servicegroups = sgn.split(",")
        else:
            return "The service is in no service group, but %s%s is required" % (
                (is_regex and "regex " or ""), " or ".join(required_groups))

        for group in required_groups:
            if is_regex:
                r = regex(group)
                for sg in servicegroups:
                    if config.define_servicegroups is None:
                        continue
                    match_value = config.define_servicegroups[
                        sg] if match_type == "match_alias" else sg
                    if r.search(match_value):
                        return None
            elif group in servicegroups:
                return None

        if is_regex:
            if match_type == "match_alias":
                if config.define_servicegroups is None:
                    return "No service groups defined."
                return "The service is only in the groups %s. None of these patterns match: %s" % (
                    '"' + '", "'.join(config.define_servicegroups[x] for x in servicegroups) + '"',
                    '"' + '" or "'.join(required_groups)) + '"'

            return "The service is only in the groups %s. None of these patterns match: %s" % (
                '"' + '", "'.join(servicegroups) + '"', '"' + '" or "'.join(required_groups)) + '"'

        return "The service is only in the groups %s, but %s is required" % (
            sgn, " or ".join(required_groups))
    return None


def event_match_exclude_servicegroups_fixed(rule: EventRule,
                                            context: EventContext) -> Optional[str]:
    return _event_match_exclude_servicegroups(rule, context, is_regex=False)


def event_match_exclude_servicegroups_regex(rule: EventRule,
                                            context: EventContext) -> Optional[str]:
    return _event_match_exclude_servicegroups(rule, context, is_regex=True)


def _event_match_exclude_servicegroups(rule: EventRule, context: EventContext,
                                       is_regex: bool) -> Optional[str]:
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
                    if config.define_servicegroups is None:
                        continue
                    match_value = config.define_servicegroups[
                        sg] if match_type == "match_alias" else sg
                    match_value_inverse = sg if match_type == "match_alias" else config.define_servicegroups[
                        sg]

                    if r.search(match_value):
                        return "The service group \"%s\" (%s) is excluded per regex pattern: %s" %\
                             (match_value, match_value_inverse, group)
            elif group in servicegroups:
                return "The service group %s is excluded" % group
    return None


def event_match_contacts(rule: EventRule, context: EventContext) -> Optional[str]:
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

    return "The object has the contacts %s, but %s is required" % (contacts_text,
                                                                   " or ".join(required_contacts))


def event_match_contactgroups(rule: EventRule, context: EventContext) -> Optional[str]:
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

    return "The object is only in the groups %s, but %s is required" % (
        cgn, " or ".join(required_groups))


def event_match_hostgroups(rule: EventRule, context: EventContext) -> Optional[str]:
    required_groups = rule.get("match_hostgroups")
    if required_groups is not None:
        hgn = context.get("HOSTGROUPNAMES")
        if hgn is None:
            return ("No information about host groups is in the context, but host "
                    "must be in group %s" % (" or ".join(required_groups)))
        if hgn:
            hostgroups = hgn.split(",")
        else:
            return "The host is in no group, but %s is required" % (" or ".join(required_groups))

        for group in required_groups:
            if group in hostgroups:
                return None

        return "The host is only in the groups %s, but %s is required" % (
            hgn, " or ".join(required_groups))
    return None


def event_match_hosts(rule: EventRule, context: EventContext) -> Optional[str]:
    if "match_hosts" in rule:
        hostlist = rule["match_hosts"]
        if context["HOSTNAME"] not in hostlist:
            return "The host's name '%s' is not on the list of allowed hosts (%s)" % (
                context["HOSTNAME"], ", ".join(hostlist))
    return None


def event_match_exclude_hosts(rule: EventRule, context: EventContext) -> Optional[str]:
    if context["HOSTNAME"] in rule.get("match_exclude_hosts", []):
        return "The host's name '%s' is on the list of excluded hosts" % context["HOSTNAME"]
    return None


def event_match_services(rule: EventRule, context: EventContext) -> Optional[str]:
    if "match_services" in rule:
        if context["WHAT"] != "SERVICE":
            return "The rule specifies a list of services, but this is a host notification."
        servicelist = rule["match_services"]
        service = context["SERVICEDESC"]
        if not config.in_extraconf_servicelist(servicelist, service):
            return "The service's description '%s' does not match by the list of " \
                   "allowed services (%s)" % (service, ", ".join(servicelist))
    return None


def event_match_exclude_services(rule: EventRule, context: EventContext) -> Optional[str]:
    if context["WHAT"] != "SERVICE":
        return None
    excludelist = rule.get("match_exclude_services", [])
    service = context["SERVICEDESC"]
    if config.in_extraconf_servicelist(excludelist, service):
        return ("The service's description '%s' matches the list of excluded services" %
                context["SERVICEDESC"])
    return None


def event_match_plugin_output(rule: EventRule, context: EventContext) -> Optional[str]:
    if "match_plugin_output" in rule:
        r = regex(rule["match_plugin_output"])

        if context["WHAT"] == "SERVICE":
            output = context["SERVICEOUTPUT"]
        else:
            output = context["HOSTOUTPUT"]
        if not r.search(output):
            return "The expression '%s' cannot be found in the plugin output '%s'" % \
                (rule["match_plugin_output"], output)
    return None


def event_match_checktype(rule: EventRule, context: EventContext) -> Optional[str]:
    if "match_checktype" in rule:
        if context["WHAT"] != "SERVICE":
            return "The rule specifies a list of Check_MK plugins, but this is a host notification."
        command = context["SERVICECHECKCOMMAND"]
        if not command.startswith("check_mk-"):
            return "The rule specified a list of Check_MK plugins, but his is no Check_MK service."
        plugin = command[9:]
        allowed = rule["match_checktype"]
        if plugin not in allowed:
            return ("The Check_MK plugin '%s' is not on the list of allowed plugins (%s)" %
                    (plugin, ", ".join(allowed)))
    return None


def event_match_timeperiod(rule: EventRule, _context: EventContext) -> Optional[str]:
    if "match_timeperiod" in rule:
        timeperiod = rule["match_timeperiod"]
        if timeperiod != "24X7" and not cmk.base.core.check_timeperiod(timeperiod):
            return "The timeperiod '%s' is currently not active." % timeperiod
    return None


def event_match_servicelevel(rule: EventRule, context: EventContext) -> Optional[str]:
    if "match_sl" in rule:
        from_sl, to_sl = rule["match_sl"]
        if context['WHAT'] == "SERVICE" and context.get('SVC_SL', '').isdigit():
            sl = saveint(context.get('SVC_SL'))
        else:
            sl = saveint(context.get('HOST_SL'))

        if sl < from_sl or sl > to_sl:
            return "The service level %d is not between %d and %d." % (sl, from_sl, to_sl)
    return None


def add_context_to_environment(plugin_context: EventContext, prefix: str) -> None:
    for key in plugin_context:
        os.putenv(prefix + key, plugin_context[key].encode('utf-8'))


# recursively turns a python object (with lists, dictionaries and pods) containing parameters
#  into a flat contextlist for use as environment variables in plugins
#
# this: { "LVL1": [{"VALUE": 42}, {"VALUE": 13}] }
# would be added as:
#   PARAMETER_LVL1_1_VALUE = 42
#   PARAMETER_LVL1_2_VALUE = 13
def add_to_event_context(plugin_context: EventContext, prefix: str, param: Union[List,
                                                                                 Dict]) -> None:
    if isinstance(param, list):
        plugin_context[prefix + "S"] = " ".join(param)
        for nr, value in enumerate(param):
            add_to_event_context(plugin_context, "%s_%d" % (prefix, nr + 1), value)
    elif isinstance(param, dict):
        for key, value in param.items():
            varname = "%s_%s" % (prefix, key.upper())

            if varname == "PARAMETER_PROXY_URL":
                # Compatibility for 1.5 pushover explicitly configured proxy URL format
                if isinstance(value, str):
                    value = ("url", value)

                value = config.get_http_proxy(value)
                if value is None:
                    continue

            add_to_event_context(plugin_context, varname, value)
    else:
        plugin_context[prefix] = plugin_param_to_string(param)


def plugin_param_to_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return ""
    if value is True:
        return "yes"
    if value is False:
        return ""
    if isinstance(value, (tuple, list)):
        return "\t".join(value)
    return repr(value)  # Should never happen


# int() function that return 0 for strings the
# cannot be converted to a number
# TODO: Clean this up!
def saveint(i: Any) -> int:
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0
