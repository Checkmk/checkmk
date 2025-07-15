#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
import time
from collections.abc import Iterable
from logging import Logger

from cmk.utils.log import VERBOSE
from cmk.utils.statename import service_state_name

from cmk.events import event_context

from .config import Action, Config, EMailActionConfig, Rule, ScriptActionConfig
from .core_queries import query_contactgroups_members, query_status_enable_notifications
from .event import Event
from .history import History
from .host_config import HostConfig
from .settings import Settings


class ECEventContext(event_context.EventContext, total=False):
    """The keys "found" in cmk.ec

    Not sure if subclassing EventContext is the right call...
    Feel free to merge if you feel like doing it.
    """

    EC_CONTACT: str
    EC_CONTACT_GROUPS: str
    EC_ID: str
    EC_MATCH_GROUPS: str
    EC_ORIG_HOST: str
    EC_OWNER: str
    EC_PHASE: str
    EC_PID: str
    HOSTADDRESS: str
    HOSTALIAS: str
    HOSTDOWNTIME: str
    LASTSERVICESTATEID: str
    NOTIFICATIONAUTHOR: str
    NOTIFICATIONAUTHORALIAS: str
    NOTIFICATIONAUTHORNAME: str
    SERVICEACKAUTHOR: str
    SERVICEACKCOMMENT: str
    SERVICEPERFDATA: str
    SERVICEPROBLEMID: str
    SERVICESTATEID: str
    SERVICE_EC_CONTACT: str
    SERVICE_SL: str

    # Dynamically added:
    # HOST_*: str  #  custom_variables


# .
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

_ContactgroupName = str


def event_has_opened(
    history: History,
    settings: Settings,
    config: Config,
    logger: Logger,
    host_config: HostConfig,
    event_columns: Iterable[tuple[str, object]],
    rule: Rule,
    event: Event,
) -> None:
    """
    Prepare for events with a limited lifetime. This time starts
    when the event enters the open state or acked state.
    """
    if "livetime" in rule:
        livetime, phases = rule["livetime"]
        event["live_until"] = time.time() + livetime
        event["live_until_phases"] = phases

    if rule.get("actions_in_downtime", True) is False and event["host_in_downtime"]:
        logger.info("Skip actions for event %d: Host is in downtime", event["id"])
        return

    do_event_actions(
        history,
        settings,
        config,
        logger,
        host_config,
        event_columns,
        rule.get("actions", []),
        event,
        is_cancelling=False,
    )


def do_event_actions(
    history: History,
    settings: Settings,
    config: Config,
    logger: Logger,
    host_config: HostConfig,
    event_columns: Iterable[tuple[str, object]],
    actions: Iterable[str],
    event: Event,
    is_cancelling: bool,
) -> None:
    """Execute a list of actions on an event that has just been opened or cancelled."""
    table = config["action"]
    for aname in actions:
        if aname == "@NOTIFY":
            do_notify(host_config, logger, event, is_cancelling=is_cancelling)
        elif action := table.get(aname):
            logger.info('executing action "%s" on event %s', action["title"], event["id"])
            do_event_action(history, settings, config, logger, event_columns, action, event, "")
        else:
            logger.info(
                'undefined action "%s", must be one of %s',
                aname,
                ", ".join(table.keys()),
            )


# Rule actions are currently done synchronously. Actions should
# not hang for more than a couple of ms.


def do_event_action(
    history: History,
    settings: Settings,
    config: Config,
    logger: Logger,
    event_columns: Iterable[tuple[str, object]],
    action: Action,
    event: Event,
    user: str,
) -> None:
    action_id = action["id"]
    if action["disabled"]:
        logger.info("Skipping disabled action %s.", action_id)
        return
    try:
        act = action["action"]
        if act[0] == "email":
            _do_email_action(history, config, logger, event_columns, act[1], event, user)
        elif act[0] == "script":
            _do_script_action(history, logger, event_columns, act[1], action_id, event, user)
        else:
            # TODO: Really parse the config, then this can't happen
            logger.error("Cannot execute action %s: invalid action type %s", action_id, act[0])  # type: ignore[unreachable]
    except Exception:
        if settings.options.debug:
            raise
        logger.exception("Error during execution of action %s", action_id)


def _do_email_action(
    history: History,
    config: Config,
    logger: Logger,
    event_columns: Iterable[tuple[str, object]],
    action_config: EMailActionConfig,
    event: Event,
    user: str,
) -> None:
    to = _prepare_text(action_config["to"], event_columns, event)
    subject = _prepare_text(action_config["subject"], event_columns, event)
    body = _prepare_text(action_config["body"], event_columns, event)
    _send_email(config, to, subject, body, logger)
    history.add(event, "EMAIL", user, f"{to}|{subject}")


def _do_script_action(
    history: History,
    logger: Logger,
    event_columns: Iterable[tuple[str, object]],
    action_config: ScriptActionConfig,
    action_id: str,
    event: Event,
    user: str,
) -> None:
    _execute_script(
        event_columns,
        _escape_null_bytes(action_config["script"]),
        event,
        logger,
    )
    history.add(event, "SCRIPT", user, action_id)


def _prepare_text(text: str, event_columns: Iterable[tuple[str, object]], event: Event) -> str:
    return _escape_null_bytes(_substitute_event_tags(text, event_columns, event))


def _escape_null_bytes(s: str) -> str:
    return s.replace("\000", "\\000")


def _substitute_event_tags(
    text: str, event_columns: Iterable[tuple[str, object]], event: Event
) -> str:
    for key, value in _get_event_tags(event_columns, event).items():
        text = text.replace(f"${key.upper()}$", value)
    return text


def _send_email(config: Config, to: str, subject: str, body: str, logger: Logger) -> bool:
    command_utf8 = [
        b"mail",
        b"-S",
        b"sendcharsets=utf-8",
        b"-s",
        subject.encode("utf-8"),
        to.encode("utf-8"),
    ]

    if config["debug_rules"]:
        logger.info("  Executing: %s", " ".join(x.decode("utf-8") for x in command_utf8))

    # FIXME: This may lock on too large buffer. We should move all "mail sending" code
    # to a general place and fix this for all our components (notification plugins,
    # notify.py, this one, ...)
    completed_process = subprocess.run(
        command_utf8,
        close_fds=True,
        capture_output=True,
        encoding="utf-8",
        input=body,
        check=False,
    )

    logger.info("  Exitcode: %d", completed_process.returncode)
    if completed_process.returncode:
        logger.info("  Error: Failed to send the mail.")
        for line in (completed_process.stdout + completed_process.stderr).splitlines():
            logger.info("  Output: %s", line.rstrip())
        return False

    return True


def _execute_script(
    event_columns: Iterable[tuple[str, object]], body: str, event: Event, logger: Logger
) -> None:
    script_env = os.environ.copy()
    for key, value in _get_event_tags(event_columns, event).items():
        script_env["CMK_" + key.upper()] = value

    # Traps can contain 0-Bytes. We need to remove this from the script
    # body. Otherwise subprocess.Popen will crash.
    completed_process = subprocess.run(
        ["/bin/bash"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        env=script_env,
        encoding="utf-8",
        input=body,
        check=False,
    )
    logger.info("  Exit code: %d", completed_process.returncode)
    if completed_process.stdout:
        logger.info("  Output: '%s'", completed_process.stdout)


def _get_event_tags(
    event_columns: Iterable[tuple[str, object]],
    event: Event,
) -> dict[str, str]:
    substs: list[tuple[str, object]] = [
        (f"match_group_{nr + 1}", g) for nr, g in enumerate(event.get("match_groups", ()))
    ]

    for key, defaultvalue in event_columns:
        varname = key[6:]
        substs.append((varname, event.get(varname, defaultvalue)))

    def to_string(v: object) -> str:
        return v if isinstance(v, str) else str(v)

    tags: dict[str, str] = {}
    for key, value in substs:
        value = " ".join(map(to_string, value)) if isinstance(value, tuple) else to_string(value)

        tags[key] = value

    return tags


# .
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


def do_notify(
    host_config: HostConfig,
    logger: Logger,
    event: Event,
    username: str | None = None,
    is_cancelling: bool = False,
) -> None:
    """
    Creates a Checkmk Notification for a locally running Checkmk.

    We simulate a *service* notification.
    """
    if not _core_has_notifications_enabled(logger):
        logger.info(
            "Notifications are currently disabled. Skipped notification for event %d", event["id"]
        )
        return

    context = _create_notification_context(host_config, event, username, is_cancelling, logger)

    if logger.isEnabledFor(VERBOSE):
        logger.log(VERBOSE, "Sending notification via Check_MK with the following context:")
        for varname, value in sorted(context.items()):
            logger.log(VERBOSE, "  %-25s: %s", varname, value)

    if context["HOSTDOWNTIME"] != "0":
        logger.info(
            "Host %s is currently in scheduled downtime. Skipping notification of event %s.",
            context["HOSTNAME"],
            event["id"],
        )
        return

    # Send notification context via stdin.
    context_string = "".join(
        "{}={}\n".format(varname, value.replace("\\", "\\\\").replace("\n", "\\n"))
        for (varname, value) in context.items()
        if isinstance(
            value, str
        )  # context is TypedDict which is dict[str, object], in fact it is dict[str, str]
    )

    completed_process = subprocess.run(
        ["cmk", "--notify", "stdin"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        encoding="utf-8",
        input=context_string,
        check=False,
    )
    if completed_process.returncode:
        logger.error("Error notifying via Check_MK: %s", completed_process.stdout.strip())
    else:
        logger.info("Successfully forwarded notification for event %d to Check_MK", event["id"])


def _create_notification_context(
    host_config: HostConfig,
    event: Event,
    username: str | None,
    is_cancelling: bool,
    logger: Logger,
) -> ECEventContext:
    context = _base_notification_context(event, username, is_cancelling)
    _add_infos_from_monitoring_host(host_config, context, event)  # involves Livestatus query
    _add_contacts_from_rule(context, event, logger)
    return context


def _base_notification_context(
    event: Event, username: str | None, is_cancelling: bool
) -> ECEventContext:
    rule_id = event["rule_id"]
    return ECEventContext(
        WHAT="SERVICE",
        CONTACTNAME="check-mk-notify",
        DATE=str(int(event["last"])),  # -> Event: Time
        MICROTIME=str(int(event["last"] * 1000000)),
        LASTSERVICESTATE=is_cancelling
        and "CRITICAL"
        or "OK",  # better assume OK, we have no transition information
        LASTSERVICESTATEID="2" if is_cancelling else "0",  # -> immer OK
        LASTSERVICEOK="0",  # 1.1.1970
        LASTSERVICESTATECHANGE=str(int(event["last"])),
        LONGSERVICEOUTPUT="",
        NOTIFICATIONAUTHOR="" if username is None else username,
        NOTIFICATIONAUTHORALIAS="" if username is None else username,
        NOTIFICATIONAUTHORNAME="" if username is None else username,
        NOTIFICATIONCOMMENT="",
        NOTIFICATIONTYPE="RECOVERY" if is_cancelling else "PROBLEM",
        SERVICEACKAUTHOR="",
        SERVICEACKCOMMENT="",
        SERVICEATTEMPT="1",
        SERVICECHECKCOMMAND="ec-internal" if rule_id is None else "ec-rule-" + rule_id,
        SERVICEDESC=event["application"] or "Event Console",
        SERVICENOTIFICATIONNUMBER="1",
        SERVICEOUTPUT=event["text"],
        SERVICEPERFDATA="",
        SERVICEPROBLEMID="ec-id-" + str(event["id"]),
        SERVICESTATE=service_state_name(event["state"]),
        SERVICESTATEID=str(event["state"]),
        SERVICE_EC_CONTACT=event.get("owner", ""),
        SERVICE_SL=str(event["sl"]),
        SVC_SL=str(event["sl"]),
        # Some fields only found in EC notifications
        EC_ID=str(event["id"]),
        EC_RULE_ID="" if rule_id is None else rule_id,
        EC_PRIORITY=str(event["priority"]),
        EC_FACILITY=str(event["facility"]),
        EC_PHASE=event["phase"],
        EC_COMMENT=event.get("comment", ""),
        EC_OWNER=event.get("owner", ""),
        EC_CONTACT=event.get("contact", ""),
        EC_PID=str(event.get("pid", 0)),
        EC_MATCH_GROUPS="\t".join(event["match_groups"]),
        EC_CONTACT_GROUPS=" ".join(event.get("contact_groups") or []),
        EC_ORIG_HOST=event.get("orig_host", event["host"]),
    )


def _add_infos_from_monitoring_host(
    host_config: HostConfig, context: ECEventContext, event: Event
) -> None:
    """
    Note: "CONTACTS" is allowed to be missing in the context, cmk --notify will
    add the fallback contacts then.
    """

    def _add_artificial_context_info() -> None:
        context.update(
            {
                "HOSTNAME": event_context.HostName(event["host"]),
                "HOSTALIAS": event["host"],
                "HOSTADDRESS": event["ipaddress"],
                "HOSTTAGS": "",
                "HOSTDOWNTIME": "0",  # Non existing host cannot be in scheduled downtime ;-)
                "CONTACTS": "?",  # Will trigger using fallback contacts
                "SERVICECONTACTGROUPNAMES": "",
            }
        )

    core_host = event["core_host"]
    if not core_host:
        # Host not known in active monitoring. Create artificial host context
        # as good as possible.
        _add_artificial_context_info()
        return

    config = host_config.get_config_for_host(core_host)
    if config is None:
        _add_artificial_context_info()  # No config found - Host has vanished?
        return

    context.update(
        {
            "HOSTNAME": event_context.HostName(config.name),
            "HOSTALIAS": config.alias,
            "HOSTADDRESS": config.address,
            "HOSTTAGS": config.custom_variables.get("TAGS", ""),
            "CONTACTS": ",".join(config.contacts),
            "SERVICECONTACTGROUPNAMES": ",".join(config.contact_groups),
            "HOSTGROUPNAMES": ",".join(config.host_groups),
        }
    )

    # Add custom variables to the notification context
    for key, val in config.custom_variables.items():
        # TypedDict with dynamic keys... The typing we have is worth the suppression
        context[f"HOST_{key}"] = val  # type: ignore[literal-required]

    context["HOSTDOWNTIME"] = "1" if event["host_in_downtime"] else "0"


def _add_contacts_from_rule(context: ECEventContext, event: Event, logger: Logger) -> None:
    """
    Add contact information from the rule, but only if the
    host is unknown or if contact groups in rule have precedence.
    """
    contact_groups = event.get("contact_groups")
    if (
        contact_groups is not None
        and event.get("contact_groups_notify")
        and (
            "CONTACTS" not in context
            or event.get("contact_groups_precedence", "host") != "host"
            or not event["core_host"]
        )
    ):
        _add_contact_information_to_context(context, contact_groups, logger)


def _add_contact_information_to_context(
    context: ECEventContext, contact_groups: Iterable[_ContactgroupName], logger: Logger
) -> None:
    try:
        contact_names = query_contactgroups_members(contact_groups)
    except Exception:
        logger.exception("Cannot get contact group members, assuming none:")
        contact_names = set()
    context["CONTACTS"] = ",".join(contact_names)
    context["SERVICECONTACTGROUPNAMES"] = ",".join(contact_groups)
    logger.log(
        VERBOSE,
        "Setting %d contacts %s resulting from rule contact groups %s",
        len(contact_names),
        ",".join(contact_names),
        ",".join(contact_groups),
    )


def _core_has_notifications_enabled(logger: Logger) -> bool:
    try:
        return query_status_enable_notifications()
    except Exception:
        logger.exception(
            "Cannot determine whether notifications are enabled in core, assuming YES."
        )
        return True
