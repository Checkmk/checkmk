#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
import os
import subprocess
import time
from typing import Any, Dict, Iterable, Optional, Set, Tuple

import cmk.utils.debug
import cmk.utils.defines
from cmk.utils.log import VERBOSE
import livestatus

from .host_config import HostConfig
from .settings import Settings

#.
#   .--Actions-------------------------------------------------------------.
#   |                     _        _   _                                   |
#   |                    / \   ___| |_(_) ___  _ __  ___                   |
#   |                   / _ \ / __| __| |/ _ \| '_ \/ __|                  |
#   |                  / ___ \ (__| |_| | (_) | | | \__ \                  |
#   |                 /_/   \_\___|\__|_|\___/|_| |_|___/                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Global functions for executing rule actions like sending emails and  |
#   | executing scripts.                                                   |
#   '----------------------------------------------------------------------'


def event_has_opened(history: Any, settings: Settings, config: Dict[str, Any], logger: Logger,
                     host_config: HostConfig, event_columns: Any, rule: Any, event: Any) -> None:
    # Prepare for events with a limited livetime. This time starts
    # when the event enters the open state or acked state
    if "livetime" in rule:
        livetime, phases = rule["livetime"]
        event["live_until"] = time.time() + livetime
        event["live_until_phases"] = phases

    if rule.get("actions_in_downtime", True) is False and event["host_in_downtime"]:
        logger.info("Skip actions for event %d: Host is in downtime" % event["id"])
        return

    do_event_actions(history,
                     settings,
                     config,
                     logger,
                     host_config,
                     event_columns,
                     rule.get("actions", []),
                     event,
                     is_cancelling=False)


# Execute a list of actions on an event that has just been
# opened or cancelled.
def do_event_actions(history: Any, settings: Settings, config: Dict[str, Any], logger: Logger,
                     host_config: HostConfig, event_columns: Any, actions: Any, event: Any,
                     is_cancelling: bool) -> None:
    for aname in actions:
        if aname == "@NOTIFY":
            do_notify(host_config, logger, event, is_cancelling=is_cancelling)
        else:
            action = config["action"].get(aname)
            if not action:
                logger.info("Cannot execute undefined action '%s'" % aname)
                logger.info("We have to following actions: %s" % ", ".join(config["action"].keys()))
            else:
                logger.info("Going to execute action '%s' on event %d" %
                            (action["title"], event["id"]))
                do_event_action(history, settings, config, logger, event_columns, action, event, "")


# Rule actions are currently done synchronously. Actions should
# not hang for more than a couple of ms.


def do_event_action(history: Any, settings: Settings, config: Dict[str, Any], logger: Logger,
                    event_columns: Any, action: Any, event: Any, user: Any) -> None:
    if action["disabled"]:
        logger.info("Skipping disabled action %s." % action["id"])
        return

    try:
        action_type, action_settings = action["action"]
        if action_type == 'email':
            to = _escape_null_bytes(
                _substitute_event_tags(event_columns, action_settings["to"], event))
            subject = _escape_null_bytes(
                _substitute_event_tags(event_columns, action_settings["subject"], event))
            body = _escape_null_bytes(
                _substitute_event_tags(event_columns, action_settings["body"], event))

            _send_email(config, to, subject, body, logger)
            history.add(event, "EMAIL", user, "%s|%s" % (to, subject))
        elif action_type == 'script':
            _execute_script(event_columns, _escape_null_bytes(action_settings["script"]), event,
                            logger)
            history.add(event, "SCRIPT", user, action['id'])
        else:
            logger.error("Cannot execute action %s: invalid action type %s" %
                         (action["id"], action_type))
    except Exception:
        if settings.options.debug:
            raise
        logger.exception("Error during execution of action %s" % action["id"])


def _escape_null_bytes(s: Any) -> Any:
    return s.replace("\000", "\\000")


def _get_quoted_event(event: Any, logger: Logger) -> Any:
    new_event: Dict[str, Any] = {}
    fields_to_quote = ["application", "match_groups", "text", "comment", "contact"]
    for key, value in event.items():
        if key not in fields_to_quote:
            new_event[key] = value
        else:
            try:
                new_value: Any = None
                if isinstance(value, list):
                    new_value = list(map(quote_shell_string, value))
                elif isinstance(value, tuple):
                    new_value = value
                else:
                    new_value = quote_shell_string(value)
                new_event[key] = new_value
            except Exception as e:
                # If anything unforeseen happens, we use the intial value
                new_event[key] = value
                logger.exception("Unable to quote event text %r: %r, %r" % (key, value, e))

    return new_event


def _substitute_event_tags(event_columns: Any, text: Any, event: Any) -> Any:
    for key, value in _get_event_tags(event_columns, event).items():
        text = text.replace('$%s$' % key.upper(), value)
    return text


def quote_shell_string(s: Any) -> Any:
    return "'" + s.replace("'", "'\"'\"'") + "'"


def _send_email(config: Dict[str, Any], to: str, subject: str, body: str, logger: Logger) -> bool:
    command_utf8 = [
        b"mail",
        b"-S",
        b"sendcharsets=utf-8",
        b"-s",
        subject.encode("utf-8"),
        to.encode("utf-8"),
    ]

    if config["debug_rules"]:
        logger.info("  Executing: %s" % " ".join(x.decode("utf-8") for x in command_utf8))

    # FIXME: This may lock on too large buffer. We should move all "mail sending" code
    # to a general place and fix this for all our components (notification plugins,
    # notify.py, this one, ...)
    completed_process = subprocess.run(
        command_utf8,
        close_fds=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        input=body,
        check=False,
    )

    logger.info("  Exitcode: %d" % completed_process.returncode)
    if completed_process.returncode:
        logger.info("  Error: Failed to send the mail.")
        for line in (completed_process.stdout + completed_process.stderr).splitlines():
            logger.info("  Output: %s" % line.rstrip())
        return False

    return True


def _execute_script(event_columns: Any, body: Any, event: Any, logger: Any) -> None:
    script_env = os.environ.copy()

    for key, value in _get_event_tags(event_columns, event).items():
        script_env["CMK_" + key.upper()] = value

    # Traps can contain 0-Bytes. We need to remove this from the script
    # body. Otherwise suprocess.Popen will crash.
    p = subprocess.Popen(
        ['/bin/bash'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        env=script_env,
        encoding="utf-8",
    )
    stdout, _stderr = p.communicate(input=body)
    logger.info('  Exit code: %d' % p.returncode)
    if stdout:
        logger.info('  Output: \'%s\'' % stdout)


def _get_event_tags(event_columns: Iterable[Tuple[str, Any]], event: Dict[str,
                                                                          Any]) -> Dict[str, str]:
    substs = [
        ("match_group_%d" % (nr + 1), g) for (nr, g) in enumerate(event.get("match_groups", ()))
    ]

    for key, defaultvalue in event_columns:
        varname = key[6:]
        substs.append((varname, event.get(varname, defaultvalue)))

    def to_string(v: Any) -> str:
        if isinstance(v, str):
            return v
        return "%s" % v

    tags = {}
    for key, value in substs:
        if isinstance(value, tuple):
            value = " ".join(map(to_string, value))
        else:
            value = to_string(value)

        tags[key] = value

    return tags


#.
#   .--Notification--------------------------------------------------------.
#   |         _   _       _   _  __ _           _   _                      |
#   |        | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __           |
#   |        |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \          |
#   |        | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | |         |
#   |        |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  EC create Checkmk native notifications via cmk --notify.           |
#   '----------------------------------------------------------------------'

# Es fehlt:
# - Wenn CONTACTS fehlen, dann müssen in notify.py die Fallbackadressen
#   genommen werden.
# - Was ist mit Nagios als Core. Sendet der CONTACTS? Nein!!
#
# - Das muss sich in den Hilfetexten wiederspiegeln


# This function creates a Checkmk Notification for a locally running Checkmk.
# We simulate a *service* notification.
def do_notify(host_config: HostConfig,
              logger: Logger,
              event: Any,
              username: Optional[bool] = None,
              is_cancelling: bool = False) -> None:
    if _core_has_notifications_disabled(event, logger):
        return

    context = _create_notification_context(host_config, event, username, is_cancelling, logger)

    if logger.isEnabledFor(VERBOSE):
        logger.log(VERBOSE, "Sending notification via Check_MK with the following context:")
        for varname, value in sorted(context.items()):
            logger.log(VERBOSE, "  %-25s: %s", varname, value)

    if context["HOSTDOWNTIME"] != "0":
        logger.info("Host %s is currently in scheduled downtime. "
                    "Skipping notification of event %s." % (context["HOSTNAME"], event["id"]))
        return

    # Send notification context via stdin.
    context_string = "".join(
        ["%s=%s\n" % (varname, value.replace("\n", "\\n")) for (varname, value) in context.items()])

    p = subprocess.Popen(
        ["cmk", "--notify", "stdin"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        encoding="utf-8",
    )
    stdout, _stderr = p.communicate(input=context_string)
    status = p.returncode
    if status:
        logger.error("Error notifying via Check_MK: %s" % stdout.strip())
    else:
        logger.info("Successfully forwarded notification for event %d to Check_MK" % event["id"])


def _create_notification_context(host_config: HostConfig, event: Any, username: Any,
                                 is_cancelling: bool, logger: Logger) -> Any:
    context = _base_notification_context(event, username, is_cancelling)
    _add_infos_from_monitoring_host(host_config, context, event)  # involves Livestatus query
    _add_contacts_from_rule(context, event, logger)
    return context


def _base_notification_context(event: Any, username: Any, is_cancelling: bool) -> Dict[str, Any]:
    return {
        "WHAT": "SERVICE",
        "CONTACTNAME": "check-mk-notify",
        "DATE": str(int(event["last"])),  # -> Event: Time
        "MICROTIME": str(int(event["last"] * 1000000)),
        "LASTSERVICESTATE": is_cancelling and "CRITICAL"
                            or "OK",  # better assume OK, we have no transition information
        "LASTSERVICESTATEID": is_cancelling and "2" or "0",  # -> immer OK
        "LASTSERVICEOK": "0",  # 1.1.1970
        "LASTSERVICESTATECHANGE": str(int(event["last"])),
        "LONGSERVICEOUTPUT": "",
        "NOTIFICATIONAUTHOR": username or "",
        "NOTIFICATIONAUTHORALIAS": username or "",
        "NOTIFICATIONAUTHORNAME": username or "",
        "NOTIFICATIONCOMMENT": "",
        "NOTIFICATIONTYPE": is_cancelling and "RECOVERY" or "PROBLEM",
        "SERVICEACKAUTHOR": "",
        "SERVICEACKCOMMENT": "",
        "SERVICEATTEMPT": "1",
        "SERVICECHECKCOMMAND": event["rule_id"] is None and "ec-internal"
                               or "ec-rule-" + event["rule_id"],
        "SERVICEDESC": event["application"] or "Event Console",
        "SERVICENOTIFICATIONNUMBER": "1",
        "SERVICEOUTPUT": event["text"],
        "SERVICEPERFDATA": "",
        "SERVICEPROBLEMID": "ec-id-" + str(event["id"]),
        "SERVICESTATE": cmk.utils.defines.service_state_name(event["state"]),
        "SERVICESTATEID": str(event["state"]),
        "SERVICE_EC_CONTACT": event.get("owner", ""),
        "SERVICE_SL": str(event["sl"]),
        "SVC_SL": str(event["sl"]),

        # Some fields only found in EC notifications
        "EC_ID": str(event["id"]),
        "EC_RULE_ID": event["rule_id"] or "",
        "EC_PRIORITY": str(event["priority"]),
        "EC_FACILITY": str(event["facility"]),
        "EC_PHASE": event["phase"],
        "EC_COMMENT": event.get("comment", ""),
        "EC_OWNER": event.get("owner", ""),
        "EC_CONTACT": event.get("contact", ""),
        "EC_PID": str(event.get("pid", 0)),
        "EC_MATCH_GROUPS": "\t".join(event["match_groups"]),
        "EC_CONTACT_GROUPS": " ".join(event.get("contact_groups") or []),
        "EC_ORIG_HOST": event.get("orig_host", event["host"]),
    }


# "CONTACTS" is allowed to be missing in the context, cmk --notify will
# add the fallback contacts then.
def _add_infos_from_monitoring_host(host_config: HostConfig, context: Any, event: Any) -> None:
    def _add_artificial_context_info() -> None:
        context.update({
            "HOSTNAME": event["host"],
            "HOSTALIAS": event["host"],
            "HOSTADDRESS": event["ipaddress"],
            "HOSTTAGS": "",
            "HOSTDOWNTIME": "0",  # Non existing host cannot be in scheduled downtime ;-)
            "CONTACTS": "?",  # Will trigger using fallback contacts
            "SERVICECONTACTGROUPNAMES": "",
        })

    if not event["core_host"]:
        # Host not known in active monitoring. Create artificial host context
        # as good as possible.
        _add_artificial_context_info()
        return

    config = host_config.get_config_for_host(event["core_host"])
    if config is None:
        _add_artificial_context_info()  # No config found - Host has vanished?
        return

    context.update({
        "HOSTNAME": config["name"],
        "HOSTALIAS": config["alias"],
        "HOSTADDRESS": config["address"],
        "HOSTTAGS": config["custom_variables"].get("TAGS", ""),
        "CONTACTS": ",".join(config["contacts"]),
        "SERVICECONTACTGROUPNAMES": ",".join(config["contact_groups"]),
    })

    # Add custom variables to the notification context
    for key, val in config["custom_variables"].items():
        context["HOST_%s" % key] = val

    context["HOSTDOWNTIME"] = "1" if event["host_in_downtime"] else "0"


def _add_contacts_from_rule(context: Any, event: Any, logger: Logger) -> None:
    # Add contact information from the rule, but only if the
    # host is unknown or if contact groups in rule have precedence

    if event.get("contact_groups") is not None and \
       event.get("contact_groups_notify") and (
           "CONTACTS" not in context or
           event.get("contact_groups_precedence", "host") != "host" or
           not event['core_host']):
        _add_contact_information_to_context(context, event["contact_groups"], logger)


def _add_contact_information_to_context(context: Any, contact_groups: Any, logger: Any) -> None:
    contact_names = _rbn_groups_contacts(contact_groups)
    context["CONTACTS"] = ",".join(contact_names)
    context["SERVICECONTACTGROUPNAMES"] = ",".join(contact_groups)
    logger.log(VERBOSE, "Setting %d contacts %s resulting from rule contact groups %s",
               len(contact_names), ",".join(contact_names), ",".join(contact_groups))


# NOTE: This function is an exact copy from modules/notify.py. We need
# to move all this Checkmk-specific livestatus query stuff to a helper
# module in lib some day.
# NOTE: Typing chaos ahead!
def _rbn_groups_contacts(groups: Any) -> Any:
    if not groups:
        return {}
    query = "GET contactgroups\nColumns: members\n"
    for group in groups:
        query += "Filter: name = %s\n" % group
    query += "Or: %d\n" % len(groups)

    try:
        contacts: Set[str] = set()
        for contact_list in livestatus.LocalConnection().query_column(query):
            contacts.update(contact_list)
        return contacts

    except livestatus.MKLivestatusNotFoundError:
        return []

    except Exception:
        if cmk.utils.debug.enabled():
            raise
        return []


def _core_has_notifications_disabled(event: Any, logger: Logger) -> bool:
    try:
        notifications_enabled = livestatus.LocalConnection().query_value(
            "GET status\nColumns: enable_notifications")
        if not notifications_enabled:
            logger.info("Notifications are currently disabled. Skipped notification for event %d" %
                        event["id"])
            return True
    except Exception as e:
        logger.info("Cannot determine whether notifcations are enabled in core: %s. Assuming YES." %
                    e)
    return False
