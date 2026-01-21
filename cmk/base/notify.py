#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="unreachable"
# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="redundant-expr"
# mypy: disable-error-code="type-arg"

# Please have a look at doc/Notifications.png:
#
# There are two types of contexts:
# 1. Raw contexts (purple)
#    => These come right out of the monitoring core. They are not yet
#       assinged to a certain plug-in. In case of rule based notifictions
#       they are not even assigned to a certain contact.
#
# 2. Plug-in contexts (cyan)
#    => These already bear all information about the contact, the plug-in
#       to call and its parameters.

import ast
import datetime
import io
import itertools
import json
import logging
import os
import re
import subprocess
import sys
import time
import traceback
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import suppress
from functools import partial
from pathlib import Path
from typing import cast, Literal

import livestatus
from livestatus import MKLivestatusException

import cmk.ccc.debug
import cmk.utils.paths
import cmk.utils.timeperiod
from cmk.automations.automation_helper import HelperExecutor
from cmk.automations.results import (
    NotificationAnalyseResult,
    NotificationGetBulksResult,
    NotificationReplayResult,
    NotificationTestResult,
)
from cmk.base import config, events
from cmk.base.automations.automations import (
    Automation,
    AutomationContext,
    load_config,
    load_plugins,
)
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.config import (
    ConfigCache,
)
from cmk.base.modes.modes import Mode, Option
from cmk.base.utils import register_sigint_handler
from cmk.ccc import store
from cmk.ccc.exceptions import (
    MKGeneralException,
    MKTimeout,
)
from cmk.ccc.hostaddress import HostName
from cmk.ccc.regex import regex
from cmk.ccc.timeout import Timeout
from cmk.ccc.version import Edition
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
)
from cmk.events.event_context import EnrichedEventContext, EventContext
from cmk.events.log_to_history import (
    log_to_history,
    notification_message,
    notification_result_message,
)
from cmk.events.notification_result import NotificationPluginName, NotificationResultCode
from cmk.events.notification_spool_file import (
    create_spool_file,
    NotificationForward,
    NotificationViaPlugin,
)
from cmk.utils import http_proxy_config, log, timeperiod
from cmk.utils.http_proxy_config import make_http_proxy_getter
from cmk.utils.log import console
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.notify import find_wato_folder
from cmk.utils.notify_types import (
    Contact,
    ContactName,
    EventRule,
    HostEventType,
    is_always_bulk,
    is_timeperiod_bulk,
    NotificationContext,
    NotificationParameterSpecs,
    NotificationPluginNameStr,
    NotifyAnalysisInfo,
    NotifyBulkParameters,
    NotifyBulks,
    NotifyPluginInfo,
    NotifyPluginParamsDict,
    NotifyRuleInfo,
    PluginNotificationContext,
    ServiceEventType,
    UUIDs,
)
from cmk.utils.timeperiod import (
    get_all_timeperiods,
    is_timeperiod_active,
    TimeperiodName,
    TimeperiodSpecs,
)

logger = logging.getLogger("cmk.base.notify")

_log_to_stdout = False
notify_mode = "notify"

_ContactgroupName = str

NotificationTableEntry = dict[str, NotificationPluginNameStr | list]
NotificationTable = list[NotificationTableEntry]

Event = str


Contacts = list[Contact]
ConfigContacts = dict[ContactName, Contact]
ContactNames = frozenset[ContactName]  # Must be hasable

NotificationKey = tuple[ContactNames, NotificationPluginNameStr]
NotificationValue = tuple[bool, NotifyPluginParamsDict, NotifyBulkParameters | None]
Notifications = dict[NotificationKey, NotificationValue]

_FallbackFormat = tuple[NotificationPluginNameStr, NotifyPluginParamsDict]


type _CoreTimeperiodsActive = Mapping[str, bool]


#   .--Configuration-------------------------------------------------------.
#   |    ____             __ _                       _   _                 |
#   |   / ___|___  _ __  / _(_) __ _ _   _ _ __ __ _| |_(_) ___  _ __      |
#   |  | |   / _ \| '_ \| |_| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \     |
#   |  | |__| (_) | | | |  _| | (_| | |_| | | | (_| | |_| | (_) | | | |    |
#   |   \____\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|    |
#   |                          |___/                                       |
#   +----------------------------------------------------------------------+
#   |  Default values of global configuration variables.                   |
#   '----------------------------------------------------------------------'

# Default settings
notification_logdir = cmk.utils.paths.var_dir / "notify"
notification_spooldir = cmk.utils.paths.var_dir / "notify/spool"
notification_bulkdir = str(cmk.utils.paths.var_dir / "notify/bulk")
notification_log = cmk.utils.paths.log_dir / "notify.log"

notification_log_template = (
    "$CONTACTNAME$ - $NOTIFICATIONTYPE$ - $HOSTNAME$ $HOSTSTATE$ - $SERVICEDESC$ $SERVICESTATE$ "
)

notification_host_subject = "Check_MK: $HOSTNAME$ - $NOTIFICATIONTYPE$"
notification_service_subject = "Check_MK: $HOSTNAME$/$SERVICEDESC$ $NOTIFICATIONTYPE$"

notification_common_body = """Host:     $HOSTNAME$
Alias:    $HOSTALIAS$
Address:  $HOSTADDRESS$
"""

notification_host_body = """State:    $LASTHOSTSTATE$ -> $HOSTSTATE$ ($NOTIFICATIONTYPE$)
Command:  $HOSTCHECKCOMMAND$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
"""

notification_service_body = """Service:  $SERVICEDESC$
State:    $LASTSERVICESTATE$ -> $SERVICESTATE$ ($NOTIFICATIONTYPE$)
Command:  $SERVICECHECKCOMMAND$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
"""

# .
#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def _initialize_logging(logging_level: int) -> None:
    log.logger.setLevel(logging_level)
    log.setup_watched_file_logging_handler(notification_log)


def make_ensure_nagios(monitoring_core: Literal["nagios", "cmc"]) -> Callable[[str], object]:
    """
    If the monitoring core is "nagios", return a no-op function.
    Otherwise, return a function that raises a RuntimeError with the given message.
    """
    if monitoring_core == "nagios":
        return lambda msg: None

    def ensure_nagios(msg: str) -> None:
        raise RuntimeError(msg)

    return ensure_nagios


# .
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Main code entry point.                                              |
#   '----------------------------------------------------------------------'


def mode_notify() -> Mode:
    return Mode(
        long_option="notify",
        handler_function=_mode_notify,
        argument=True,
        argument_descr="MODE",
        argument_optional=True,
        short_help="Used to send notifications from core",
        # TODO: Write long help
        sub_options=[
            Option(
                long_option="log-to-stdout",
                short_help="Also write log messages to console",
            ),
            Option(
                long_option="keepalive",
                short_help="Execute in keepalive mode (Commercial editions only)",
            ),
        ],
    )


def automations_notify() -> list[Automation]:
    return [
        Automation(
            ident="notification-replay",
            handler=_automation_notification_replay,
        ),
        Automation(
            ident="notification-analyse",
            handler=_automation_notification_analyse,
        ),
        Automation(
            ident="notification-test",
            handler=_automation_notification_test,
        ),
        Automation(
            ident="notification-get-bulks",
            handler=_automation_get_bulks,
        ),
    ]


def _mode_notify(app: CheckmkBaseApp, options: dict, args: list[str]) -> int | None:
    community_edition = app.edition is Edition.COMMUNITY
    if not community_edition and "spoolfile" in args:
        return _do_notify_via_automation(
            options=options,
            args=args,
        )

    if keepalive := not community_edition and "keepalive" in options:
        register_sigint_handler()

    with store.lock_checkmk_configuration(cmk.utils.paths.configuration_lockfile):
        loading_result = config.load(
            discovery_rulesets=(),
            get_builtin_host_labels=app.get_builtin_host_labels,
            with_conf_d=True,
            validate_hosts=False,
        )

    return do_notify(
        options,
        args,
        define_servicegroups=config.define_servicegroups,
        host_parameters_cb=lambda hostname,
        plugin: loading_result.config_cache.notification_plugin_parameters(hostname, plugin),
        rules=config.notification_rules,
        parameters=config.notification_parameter,
        get_http_proxy=make_http_proxy_getter(loading_result.loaded_config.http_proxies),
        ensure_nagios=make_ensure_nagios(loading_result.loaded_config.monitoring_core),
        bulk_interval=config.notification_bulk_interval,
        plugin_timeout=config.notification_plugin_timeout,
        config_contacts=config.contacts,
        fallback_email=config.notification_fallback_email,
        fallback_format=config.notification_fallback_format,
        spooling=config.ConfigCache.notification_spooling(),
        backlog_size=config.notification_backlog,
        logging_level=config.ConfigCache.notification_logging_level(),
        keepalive=keepalive,
        all_timeperiods=timeperiod.get_all_timeperiods(loading_result.loaded_config.timeperiods),
        timeperiods_active=timeperiod.TimeperiodActiveCoreLookup(
            livestatus.get_optional_timeperiods_active_map, logger.warning
        ),
    )


def _do_notify_via_automation(options: dict, args: list[str]) -> int | None:
    log_to_stdout = False
    if options.get("log-to-stdout"):
        args.insert(0, "--log-to-stdout")
        log_to_stdout = True

    try:
        result = HelperExecutor().execute(
            command="notify",
            args=args,
            stdin="",
            logger=logger,
            timeout=None,
        )
    except Exception as e:
        logger.error("Error running automation call 'notify': %s", e)
        return 1

    try:
        data = ast.literal_eval(result.output)
    except (SyntaxError, ValueError, TypeError) as e:
        logger.error("Could not parse automation result %r: %s", result.output, e)
        return 2

    if isinstance(data, dict):
        if log_to_stdout:
            sys.stdout.write(data["output"])
            sys.stdout.flush()
        return data.get("exit_code")

    logger.error("Unexpected automation result format: %r", data)
    return 2


def notify_usage() -> None:
    console.error(
        """Usage: check_mk --notify [--keepalive]
       check_mk --notify spoolfile <filename>

Normally the notify module is called without arguments to send real
notification. But there are situations where this module is called with
COMMANDS to e.g. support development of notification plugins.

Available commands:
    spoolfile <filename>    Reads the given spoolfile and creates a
                            notification out of its data
    stdin                   Read one notification context from stdin instead
                            of taking variables from environment
    replay N                Uses the N'th recent notification from the backlog
                            and sends it again, counting from 0.
    send-bulks              Send out ripe bulk notifications""",
        file=sys.stderr,
    )


# Main function called by cmk --notify. It either starts the
# keepalive mode (used by CMC), sends out one notifications from
# several possible sources or sends out all ripe bulk notifications.
def do_notify(
    options: dict[str, bool],
    args: list[str],
    *,
    rules: Iterable[EventRule],
    parameters: NotificationParameterSpecs,
    define_servicegroups: Mapping[str, str],
    get_http_proxy: events.ProxyGetter,
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    ensure_nagios: Callable[[str], object],
    config_contacts: ConfigContacts,
    fallback_email: str,
    fallback_format: _FallbackFormat,
    bulk_interval: int,
    plugin_timeout: int,
    spooling: Literal["local", "remote", "both", "off"],
    backlog_size: int,
    logging_level: int,
    keepalive: bool,
    all_timeperiods: TimeperiodSpecs,
    timeperiods_active: _CoreTimeperiodsActive,
) -> int | None:
    global _log_to_stdout, notify_mode
    _log_to_stdout = options.get("log-to-stdout", _log_to_stdout)

    notification_logdir.mkdir(parents=True, exist_ok=True)
    notification_spooldir.mkdir(parents=True, exist_ok=True)
    _initialize_logging(logging_level)

    try:
        notify_mode = "notify"
        if args:
            notify_mode = args[0]
            if notify_mode not in ["stdin", "spoolfile", "replay", "test", "send-bulks"]:
                console.error("ERROR: Invalid call to check_mk --notify.\n", file=sys.stderr)
                notify_usage()
                sys.exit(1)

            if notify_mode == "spoolfile" and len(args) != 2:
                console.error("ERROR: need an argument to --notify spoolfile.\n", file=sys.stderr)
                sys.exit(1)

        # If the notify_mode is set to 'spoolfile' we try to parse the given spoolfile
        # This spoolfile contains a python dictionary
        # { context: { Dictionary of environment variables }, plugin: "Plug-in name" }
        # Any problems while reading the spoolfile results in returning 2
        # -> mknotifyd deletes this file
        if notify_mode == "spoolfile":
            filename = args[1]
            return _handle_spoolfile(
                filename,
                host_parameters_cb,
                get_http_proxy,
                rules=rules,
                parameters=parameters,
                define_servicegroups=define_servicegroups,
                config_contacts=config_contacts,
                fallback_email=fallback_email,
                fallback_format=fallback_format,
                plugin_timeout=plugin_timeout,
                all_timeperiods=all_timeperiods,
                spooling=spooling,
                backlog_size=backlog_size,
                timeperiods_active=timeperiods_active,
            )

        if keepalive:
            _notify_keepalive(
                host_parameters_cb,
                get_http_proxy,
                ensure_nagios,
                rules=rules,
                parameters=parameters,
                define_servicegroups=define_servicegroups,
                bulk_interval=bulk_interval,
                fallback_email=fallback_email,
                fallback_format=fallback_format,
                plugin_timeout=plugin_timeout,
                config_contacts=config_contacts,
                spooling=spooling,
                backlog_size=backlog_size,
                logging_level=logging_level,
                all_timeperiods=all_timeperiods,
            )
        elif notify_mode == "replay":
            try:
                replay_nr = int(args[1])
            except (IndexError, ValueError):
                replay_nr = 0
            _notify_notify(
                raw_context_from_backlog(replay_nr),
                timeperiods_active,
                host_parameters_cb,
                get_http_proxy,
                ensure_nagios,
                rules=rules,
                parameters=parameters,
                define_servicegroups=define_servicegroups,
                config_contacts=config_contacts,
                fallback_email=fallback_email,
                fallback_format=fallback_format,
                plugin_timeout=plugin_timeout,
                spooling=spooling,
                backlog_size=backlog_size,
                logging_level=logging_level,
                all_timeperiods=all_timeperiods,
            )
        elif notify_mode == "test":
            assert isinstance(args[0], dict)
            _notify_notify(
                EventContext(args[0]),
                timeperiods_active,
                host_parameters_cb,
                get_http_proxy,
                ensure_nagios,
                rules=rules,
                parameters=parameters,
                define_servicegroups=define_servicegroups,
                config_contacts=config_contacts,
                fallback_email=fallback_email,
                fallback_format=fallback_format,
                plugin_timeout=plugin_timeout,
                spooling=spooling,
                backlog_size=backlog_size,
                logging_level=logging_level,
                all_timeperiods=all_timeperiods,
            )
        elif notify_mode == "stdin":
            _notify_notify(
                events.raw_context_from_string(sys.stdin.read()),
                timeperiods_active,
                host_parameters_cb,
                get_http_proxy,
                ensure_nagios,
                rules=rules,
                parameters=parameters,
                define_servicegroups=define_servicegroups,
                config_contacts=config_contacts,
                fallback_email=fallback_email,
                fallback_format=fallback_format,
                plugin_timeout=plugin_timeout,
                spooling=spooling,
                backlog_size=backlog_size,
                logging_level=logging_level,
                all_timeperiods=all_timeperiods,
            )
        elif notify_mode == "send-bulks":
            _send_ripe_bulks(
                get_http_proxy,
                timeperiods_active,
                bulk_interval=bulk_interval,
                plugin_timeout=plugin_timeout,
            )
        else:
            _notify_notify(
                raw_context_from_env(os.environ),
                timeperiods_active,
                host_parameters_cb,
                get_http_proxy,
                ensure_nagios,
                rules=rules,
                parameters=parameters,
                define_servicegroups=define_servicegroups,
                config_contacts=config_contacts,
                fallback_email=fallback_email,
                fallback_format=fallback_format,
                plugin_timeout=plugin_timeout,
                spooling=spooling,
                backlog_size=backlog_size,
                logging_level=logging_level,
                all_timeperiods=all_timeperiods,
            )

    except Exception:
        crash_dir = cmk.utils.paths.var_dir / "notify"
        if not crash_dir.exists():
            crash_dir.mkdir(parents=True)
        with (crash_dir / "crash.log").open(mode="a") as crash_file:
            crash_file.write(
                "CRASH ({}):\n{}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), format_exception())
            )
    return None


def _notify_notify(
    raw_context: EventContext,
    timeperiods_active: _CoreTimeperiodsActive,
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    get_http_proxy: events.ProxyGetter,
    ensure_nagios: Callable[[str], object],
    *,
    rules: Iterable[EventRule],
    parameters: NotificationParameterSpecs,
    define_servicegroups: Mapping[str, str],
    config_contacts: ConfigContacts,
    fallback_email: str,
    fallback_format: _FallbackFormat,
    spooling: Literal["local", "remote", "both", "off"],
    plugin_timeout: int,
    backlog_size: int,
    logging_level: int,
    all_timeperiods: TimeperiodSpecs,
    analyse: bool = False,
    dispatch: str = "",
) -> NotifyAnalysisInfo | None:
    """
    This function processes one raw notification and decides wether it should be spooled or not.
    In the latter cased a local delivery is being done.

    :param raw_context: This is the origin raw notification context as produced by the monitoring
        core before it is being processed by the the rule based notfication logic which may create
        multiple specific notification contexts out of the raw notification context and the matching
        notification rule.
    :param analyse:
    """
    enriched_context = events.complete_raw_context(
        raw_context,
        ensure_nagios,
        with_dump=logging_level <= 10,
        contacts_needed=True,
        analyse=analyse,
    )

    if not analyse:
        store_notification_backlog(enriched_context, backlog_size=backlog_size)

    logger.info("----------------------------------------------------------------------")
    if analyse:
        logger.info(
            "Analysing notification (%s) context with %s variables",
            events.find_host_service_in_context(enriched_context),
            len(enriched_context),
        )
    else:
        logger.info(
            "Got raw notification (%s) context with %s variables",
            events.find_host_service_in_context(enriched_context),
            len(enriched_context),
        )

    # Add some further variable for the conveniance of the plugins

    logger.debug(events.render_context_dump(enriched_context))

    enriched_context["LOGDIR"] = str(notification_logdir)

    # Spool notification to remote host, if this is enabled
    if spooling in ("remote", "both"):
        create_spool_file(
            logger,
            notification_spooldir,
            NotificationForward({"context": enriched_context, "forward": True}),
        )

    if spooling != "remote":
        return _locally_deliver_raw_context(
            enriched_context,
            host_parameters_cb,
            get_http_proxy,
            rules=rules,
            parameters=parameters,
            define_servicegroups=define_servicegroups,
            spooling=spooling,
            config_contacts=config_contacts,
            fallback_email=fallback_email,
            fallback_format=fallback_format,
            plugin_timeout=plugin_timeout,
            all_timeperiods=all_timeperiods,
            analyse=analyse,
            dispatch=dispatch,
            timeperiods_active=timeperiods_active,
        )
    return None


def _locally_deliver_raw_context(
    enriched_context: EnrichedEventContext,
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    get_http_proxy: events.ProxyGetter,
    *,
    rules: Iterable[EventRule],
    parameters: NotificationParameterSpecs,
    define_servicegroups: Mapping[str, str],
    spooling: Literal["local", "remote", "both", "off"],
    config_contacts: ConfigContacts,
    fallback_email: str,
    fallback_format: _FallbackFormat,
    plugin_timeout: int,
    all_timeperiods: TimeperiodSpecs,
    analyse: bool = False,
    dispatch: str = "",
    timeperiods_active: _CoreTimeperiodsActive,
) -> NotifyAnalysisInfo | None:
    try:
        logger.debug("Preparing rule based notifications")
        return _notify_rulebased(
            enriched_context,
            host_parameters_cb,
            get_http_proxy,
            define_servicegroups=define_servicegroups,
            spooling=spooling,
            config_contacts=config_contacts,
            fallback_email=fallback_email,
            fallback_format=fallback_format,
            plugin_timeout=plugin_timeout,
            rules=rules,
            parameters=parameters,
            all_timeperiods=all_timeperiods,
            analyse=analyse,
            dispatch=dispatch,
            timeperiods_active=timeperiods_active,
        )

    except Exception:
        if cmk.ccc.debug.enabled():
            raise
        logger.exception("ERROR:")

    return None


def _notification_replay_backlog(
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    get_http_proxy: events.ProxyGetter,
    ensure_nagios: Callable[[str], object],
    nr: int,
    *,
    rules: Iterable[EventRule],
    parameters: NotificationParameterSpecs,
    define_servicegroups: Mapping[str, str],
    config_contacts: ConfigContacts,
    fallback_email: str,
    fallback_format: _FallbackFormat,
    plugin_timeout: int,
    spooling: Literal["local", "remote", "both", "off"],
    backlog_size: int,
    logging_level: int,
    all_timeperiods: TimeperiodSpecs,
    timeperiods_active: _CoreTimeperiodsActive,
) -> None:
    global notify_mode
    notify_mode = "replay"
    _initialize_logging(logging_level)
    raw_context = raw_context_from_backlog(nr)
    _notify_notify(
        raw_context,
        timeperiods_active,
        host_parameters_cb,
        get_http_proxy,
        ensure_nagios,
        rules=rules,
        parameters=parameters,
        define_servicegroups=define_servicegroups,
        config_contacts=config_contacts,
        fallback_email=fallback_email,
        fallback_format=fallback_format,
        plugin_timeout=plugin_timeout,
        spooling=spooling,
        backlog_size=backlog_size,
        logging_level=logging_level,
        all_timeperiods=all_timeperiods,
    )


def _notification_analyse_backlog(
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    get_http_proxy: events.ProxyGetter,
    ensure_nagios: Callable[[str], object],
    nr: int,
    *,
    rules: Iterable[EventRule],
    parameters: NotificationParameterSpecs,
    define_servicegroups: Mapping[str, str],
    config_contacts: ConfigContacts,
    fallback_email: str,
    fallback_format: _FallbackFormat,
    plugin_timeout: int,
    spooling: Literal["local", "remote", "both", "off"],
    backlog_size: int,
    logging_level: int,
    all_timeperiods: TimeperiodSpecs,
    timeperiods_active: _CoreTimeperiodsActive,
) -> NotifyAnalysisInfo | None:
    global notify_mode
    notify_mode = "replay"
    _initialize_logging(logging_level)
    raw_context = raw_context_from_backlog(nr)
    return _notify_notify(
        raw_context,
        timeperiods_active,
        host_parameters_cb,
        get_http_proxy,
        ensure_nagios,
        rules=rules,
        parameters=parameters,
        define_servicegroups=define_servicegroups,
        config_contacts=config_contacts,
        fallback_email=fallback_email,
        fallback_format=fallback_format,
        plugin_timeout=plugin_timeout,
        spooling=spooling,
        backlog_size=backlog_size,
        logging_level=logging_level,
        all_timeperiods=all_timeperiods,
        analyse=True,
    )


def _notification_test(
    raw_context: NotificationContext,
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    get_http_proxy: events.ProxyGetter,
    ensure_nagios: Callable[[str], object],
    *,
    rules: Iterable[EventRule],
    parameters: NotificationParameterSpecs,
    define_servicegroups: Mapping[str, str],
    config_contacts: ConfigContacts,
    fallback_email: str,
    fallback_format: _FallbackFormat,
    plugin_timeout: int,
    spooling: Literal["local", "remote", "both", "off"],
    backlog_size: int,
    logging_level: int,
    all_timeperiods: TimeperiodSpecs,
    dispatch: str = "",
    timeperiods_active: _CoreTimeperiodsActive,
) -> NotifyAnalysisInfo | None:
    global notify_mode
    notify_mode = "test"
    _initialize_logging(logging_level)

    contact_list = raw_context["CONTACTS"].split(",")
    if "check-mk-notify" in contact_list:
        contact_list.remove("check-mk-notify")
    raw_context["CONTACTS"] = ",".join(contact_list) if contact_list else "?"

    plugin_context = EventContext({})
    plugin_context.update(cast(EventContext, raw_context))
    return _notify_notify(
        plugin_context,
        timeperiods_active,
        host_parameters_cb,
        get_http_proxy,
        ensure_nagios,
        rules=rules,
        parameters=parameters,
        define_servicegroups=define_servicegroups,
        config_contacts=config_contacts,
        fallback_email=fallback_email,
        fallback_format=fallback_format,
        plugin_timeout=plugin_timeout,
        spooling=spooling,
        backlog_size=backlog_size,
        logging_level=logging_level,
        all_timeperiods=all_timeperiods,
        analyse=True,
        dispatch=dispatch,
    )


# .
#   .--Keepalive-Mode (Used by CMC)----------------------------------------.
#   |               _  __                     _ _                          |
#   |              | |/ /___  ___ _ __   __ _| (_)_   _____                |
#   |              | ' // _ \/ _ \ '_ \ / _` | | \ \ / / _ \               |
#   |              | . \  __/  __/ |_) | (_| | | |\ V /  __/               |
#   |              |_|\_\___|\___| .__/ \__,_|_|_| \_/ \___|               |
#   |                            |_|                                       |
#   +----------------------------------------------------------------------+
#   |  Implementation of cmk --notify --keepalive, which is being used     |
#   |  by the Micro Core.                                                  |
#   '----------------------------------------------------------------------'


# TODO: Make use of the generic do_keepalive() mechanism?
def _notify_keepalive(
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    get_http_proxy: events.ProxyGetter,
    ensure_nagios: Callable[[str], object],
    *,
    rules: Iterable[EventRule],
    parameters: NotificationParameterSpecs,
    define_servicegroups: Mapping[str, str],
    fallback_email: str,
    fallback_format: _FallbackFormat,
    config_contacts: ConfigContacts,
    plugin_timeout: int,
    bulk_interval: int,
    spooling: Literal["local", "remote", "both", "off"],
    backlog_size: int,
    logging_level: int,
    all_timeperiods: TimeperiodSpecs,
) -> None:
    events.event_keepalive(
        event_function=partial(
            _notify_notify,
            define_servicegroups=define_servicegroups,
            host_parameters_cb=host_parameters_cb,
            get_http_proxy=get_http_proxy,
            ensure_nagios=ensure_nagios,
            rules=rules,
            parameters=parameters,
            fallback_email=fallback_email,
            fallback_format=fallback_format,
            config_contacts=config_contacts,
            plugin_timeout=plugin_timeout,
            spooling=spooling,
            backlog_size=backlog_size,
            logging_level=logging_level,
            all_timeperiods=all_timeperiods,
        ),
        call_every_loop=partial(
            _send_ripe_bulks,
            get_http_proxy,
            bulk_interval=bulk_interval,
            plugin_timeout=plugin_timeout,
        ),
        loop_interval=bulk_interval,
    )


def _automation_notification_replay(
    ctx: AutomationContext,
    args: list[str],
    plugins: AgentBasedPlugins | None,
    loading_result: config.LoadingResult | None,
) -> NotificationReplayResult:
    plugins = plugins or load_plugins()  # do we really still need this?
    loading_result = loading_result or load_config(
        discovery_rulesets=(),
        get_builtin_host_labels=ctx.get_builtin_host_labels,
    )
    logger = logging.getLogger("cmk.base.automations")  # this might go nowhere.

    nr = args[0]
    _notification_replay_backlog(
        lambda hostname, plugin: loading_result.config_cache.notification_plugin_parameters(
            hostname, plugin
        ),
        http_proxy_config.make_http_proxy_getter(loading_result.loaded_config.http_proxies),
        make_ensure_nagios(loading_result.loaded_config.monitoring_core),
        int(nr),
        rules=config.notification_rules,
        parameters=config.notification_parameter,
        define_servicegroups=config.define_servicegroups,
        config_contacts=config.contacts,
        fallback_email=config.notification_fallback_email,
        fallback_format=config.notification_fallback_format,
        plugin_timeout=config.notification_plugin_timeout,
        spooling=ConfigCache.notification_spooling(),
        backlog_size=config.notification_backlog,
        logging_level=ConfigCache.notification_logging_level(),
        all_timeperiods=get_all_timeperiods(loading_result.loaded_config.timeperiods),
        timeperiods_active=cmk.utils.timeperiod.TimeperiodActiveCoreLookup(
            livestatus.get_optional_timeperiods_active_map, log=logger.warning
        ),
    )
    return NotificationReplayResult()


def _automation_notification_analyse(
    ctx: AutomationContext,
    args: list[str],
    plugins: AgentBasedPlugins | None,
    loading_result: config.LoadingResult | None,
) -> NotificationAnalyseResult:
    plugins = plugins or load_plugins()  # do we really still need this?
    loading_result = loading_result or load_config(
        discovery_rulesets=(),
        get_builtin_host_labels=ctx.get_builtin_host_labels,
    )
    logger = logging.getLogger("cmk.base.automations")  # this might go nowhere.

    nr = args[0]
    return NotificationAnalyseResult(
        _notification_analyse_backlog(
            lambda hostname, plugin: loading_result.config_cache.notification_plugin_parameters(
                hostname, plugin
            ),
            http_proxy_config.make_http_proxy_getter(loading_result.loaded_config.http_proxies),
            make_ensure_nagios(loading_result.loaded_config.monitoring_core),
            int(nr),
            rules=config.notification_rules,
            parameters=config.notification_parameter,
            define_servicegroups=config.define_servicegroups,
            config_contacts=config.contacts,
            fallback_email=config.notification_fallback_email,
            fallback_format=config.notification_fallback_format,
            plugin_timeout=config.notification_plugin_timeout,
            spooling=ConfigCache.notification_spooling(),
            backlog_size=config.notification_backlog,
            logging_level=ConfigCache.notification_logging_level(),
            all_timeperiods=get_all_timeperiods(loading_result.loaded_config.timeperiods),
            timeperiods_active=cmk.utils.timeperiod.TimeperiodActiveCoreLookup(
                livestatus.get_optional_timeperiods_active_map, log=logger.warning
            ),
        )
    )


def _automation_notification_test(
    ctx: AutomationContext,
    args: list[str],
    plugins: AgentBasedPlugins | None,
    loading_result: config.LoadingResult | None,
) -> NotificationTestResult:
    context = json.loads(args[0])
    dispatch = args[1]

    plugins = plugins or load_plugins()  # do we really still need this?
    loading_result = loading_result or load_config(
        discovery_rulesets=(),
        get_builtin_host_labels=ctx.get_builtin_host_labels,
    )
    ensure_nagios = make_ensure_nagios(loading_result.loaded_config.monitoring_core)
    logger = logging.getLogger("cmk.base.automations")  # this might go nowhere.

    return NotificationTestResult(
        _notification_test(
            context,
            lambda hostname, plugin: loading_result.config_cache.notification_plugin_parameters(
                hostname, plugin
            ),
            http_proxy_config.make_http_proxy_getter(loading_result.loaded_config.http_proxies),
            ensure_nagios,
            rules=config.notification_rules,
            parameters=config.notification_parameter,
            define_servicegroups=config.define_servicegroups,
            config_contacts=config.contacts,
            fallback_email=config.notification_fallback_email,
            fallback_format=config.notification_fallback_format,
            plugin_timeout=config.notification_plugin_timeout,
            spooling=ConfigCache.notification_spooling(),
            backlog_size=config.notification_backlog,
            logging_level=ConfigCache.notification_logging_level(),
            all_timeperiods=get_all_timeperiods(loading_result.loaded_config.timeperiods),
            dispatch=dispatch,
            timeperiods_active=cmk.utils.timeperiod.TimeperiodActiveCoreLookup(
                livestatus.get_optional_timeperiods_active_map, log=logger.warning
            ),
        )
    )


def _automation_get_bulks(
    ctx: AutomationContext,
    args: list[str],
    plugins: AgentBasedPlugins | None,
    loading_result: config.LoadingResult | None,
) -> NotificationGetBulksResult:
    only_ripe = args[0] == "1"
    logger = logging.getLogger("cmk.base.automations")  # this might go nowhere.
    return NotificationGetBulksResult(
        _find_bulks(
            only_ripe,
            bulk_interval=config.notification_bulk_interval,
            timeperiods_active=cmk.utils.timeperiod.TimeperiodActiveCoreLookup(
                livestatus.get_optional_timeperiods_active_map, log=logger.warning
            ),
        )
    )


# .
#   .--Rule-Based-Notifications--------------------------------------------.
#   |            ____        _      _                        _             |
#   |           |  _ \ _   _| | ___| |__   __ _ ___  ___  __| |            |
#   |           | |_) | | | | |/ _ \ '_ \ / _` / __|/ _ \/ _` |            |
#   |           |  _ <| |_| | |  __/ |_) | (_| \__ \  __/ (_| |            |
#   |           |_| \_\\__,_|_|\___|_.__/ \__,_|___/\___|\__,_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Logic for rule based notifications                                  |
#   '----------------------------------------------------------------------'


def _notify_rulebased(
    enriched_context: EnrichedEventContext,
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    get_http_proxy: events.ProxyGetter,
    *,
    rules: Iterable[EventRule],
    parameters: NotificationParameterSpecs,
    define_servicegroups: Mapping[str, str],
    spooling: Literal["local", "remote", "both", "off"],
    config_contacts: ConfigContacts,
    fallback_email: str,
    fallback_format: _FallbackFormat,
    plugin_timeout: int,
    all_timeperiods: TimeperiodSpecs,
    analyse: bool = False,
    dispatch: str = "",
    timeperiods_active: _CoreTimeperiodsActive,
) -> NotifyAnalysisInfo:
    # First step: go through all rules and construct our table of
    # notification plugins to call. This is a dict from (users, plugin) to
    # a triple of (locked, parameters, bulk). If locked is True, then a user
    # cannot cancel this notification via his personal notification rules.
    # Example:
    # notifications = {
    #  ( frozenset({"aa", "hh", "ll"}), "email" ) : ( False, [], None ),
    #  ( frozenset({"hh"}), "sms"   ) : ( True, [ "0171737337", "bar", {
    #       'groupby': 'host', 'interval': 60} ] ),
    # }

    notifications: Notifications = {}
    num_rule_matches = 0
    rule_info = []

    for nr, rule in enumerate(
        itertools.chain(rules, user_notification_rules(config_contacts=config_contacts))
    ):
        contact_info = _get_contact_info_text(rule)

        why_not = _rbn_match_rule(
            rule,
            enriched_context,
            define_servicegroups=define_servicegroups,
            analyse=analyse,
            all_timeperiods=all_timeperiods,
            timeperiods_active=timeperiods_active,
        )
        if why_not:
            logger.log(log.VERBOSE, contact_info)
            logger.log(log.VERBOSE, " -> does not match: %s", why_not)
            rule_info.append(("miss", rule, why_not))
        else:
            logger.info(contact_info)
            logger.info(" -> matches!")
            num_rule_matches += 1

            notifications, rule_info = _create_notifications(
                enriched_context,
                rule,
                parameters,
                notifications,
                rule_info,
                host_parameters_cb,
                config_contacts=config_contacts,
                fallback_email=fallback_email,
                rule_nr=nr,
                timeperiods_active=timeperiods_active,
            )

    plugin_info = _process_notifications(
        enriched_context,
        notifications,
        parameters,
        num_rule_matches,
        host_parameters_cb,
        get_http_proxy,
        config_contacts=config_contacts,
        fallback_email=fallback_email,
        fallback_format=fallback_format,
        plugin_timeout=plugin_timeout,
        spooling=spooling,
        analyse=analyse,
        dispatch=dispatch,
    )

    return rule_info, plugin_info


def _get_contact_info_text(rule: EventRule) -> str:
    if "contact" in rule:
        return "User {}'s rule '{}'...".format(rule["contact"], rule["description"])
    return "Global rule '%s'..." % rule["description"]


def _create_notifications(
    enriched_context: EnrichedEventContext,
    rule: EventRule,
    parameters: NotificationParameterSpecs,
    notifications: Notifications,
    rule_info: list[NotifyRuleInfo],
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    *,
    config_contacts: ConfigContacts,
    fallback_email: str,
    rule_nr: int,
    timeperiods_active: _CoreTimeperiodsActive,
) -> tuple[Notifications, list[NotifyRuleInfo]]:
    contacts = rbn_rule_contacts(
        rule,
        enriched_context,
        config_contacts=config_contacts,
        fallback_email=fallback_email,
    )
    contactstxt = ", ".join(contacts)

    plugin_name, plugin_parameter_id = rule["notify_plugin"]

    plugintxt = plugin_name

    key = contacts, plugin_name
    if plugin_parameter_id is None:  # cancelling
        # FIXME: In Python 2, notifications.keys() already produces a
        # copy of the keys, while in Python 3 it is only a view of the
        # underlying dict (modifications would result in an exception).
        # To be explicit and future-proof, we make this hack explicit.
        # Anyway, this is extremely ugly and an anti-patter, and it
        # should be rewritten to something more sane.
        for notify_key in list(notifications):
            notify_contacts, notify_plugin = notify_key

            overlap = notify_contacts.intersection(contacts)
            if plugin_name != notify_plugin or not overlap:
                continue

            locked, _plugin_parameters, bulk = notifications[notify_key]

            if locked and "contact" in rule:
                logger.info(
                    "   - cannot cancel notification of %s via %s: it is locked",
                    contactstxt,
                    plugintxt,
                )
                continue

            logger.info("   - cancelling notification of %s via %s", ", ".join(overlap), plugintxt)

            remaining = notify_contacts.difference(contacts)
            if not remaining:
                del notifications[notify_key]
            else:
                new_key = remaining, plugin_name
                notifications[new_key] = notifications.pop(notify_key)
    elif contacts:
        if key in notifications:
            locked = notifications[key][0]
            if locked and "contact" in rule:
                logger.info(
                    "   - cannot modify notification of %s via %s: it is locked",
                    contactstxt,
                    plugintxt,
                )
                return notifications, rule_info
            logger.info("   - modifying notification of %s via %s", contactstxt, plugintxt)
        else:
            logger.info("   - adding notification of %s via %s", contactstxt, plugintxt)

        bulk = _rbn_get_bulk_params(rule, timeperiods_active)

        # TODO CMK-20135 use old format for user notifications for now
        plugin_parameters = (
            parameters[plugin_name][plugin_parameter_id]["parameter_properties"]
            if isinstance(plugin_parameter_id, str)
            else plugin_parameter_id
        )

        final_parameters: NotifyPluginParamsDict = _rbn_finalize_plugin_parameters(
            hostname=HostName(enriched_context["HOSTNAME"]),
            plugin_name=plugin_name,
            host_parameters_cb=host_parameters_cb,
            rule_parameters=plugin_parameters,
            rule_matching_nr=rule_nr,
            rule_matching_text=rule["description"],
        )
        notifications[key] = (not rule.get("allow_disable"), final_parameters, bulk)

    rule_info.append(("match", rule, ""))
    return notifications, rule_info


def _process_notifications(
    enriched_context: EnrichedEventContext,
    notifications: Notifications,
    parameters: NotificationParameterSpecs,
    num_rule_matches: int,
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    get_http_proxy: events.ProxyGetter,
    *,
    config_contacts: ConfigContacts,
    fallback_email: str,
    fallback_format: _FallbackFormat,
    plugin_timeout: int,
    spooling: Literal["local", "remote", "both", "off"],
    analyse: bool,
    dispatch: str = "",
) -> list[NotifyPluginInfo]:
    plugin_info: list[NotifyPluginInfo] = []

    if not notifications:
        if num_rule_matches:
            logger.info("%d rules matched, but no notification has been created.", num_rule_matches)
        elif not analyse:
            fallback_contacts = rbn_fallback_contacts(
                config_contacts=config_contacts, fallback_email=fallback_email
            )
            if fallback_contacts:
                logger.info("No rule matched, notifying fallback contacts")
                fallback_emails = [fc["email"] for fc in fallback_contacts]
                logger.info("  Sending email to %s", fallback_emails)

                plugin_name, fallback_params = fallback_format
                fallback_params = _rbn_finalize_plugin_parameters(
                    hostname=HostName(enriched_context["HOSTNAME"]),
                    plugin_name=plugin_name,
                    host_parameters_cb=host_parameters_cb,
                    rule_parameters=fallback_params,
                    rule_matching_nr=-1,
                    rule_matching_text="No rule matched",
                )
                plugin_context = create_plugin_context(
                    enriched_context, fallback_params, get_http_proxy
                )
                rbn_add_contact_information(plugin_context, fallback_contacts, config_contacts)
                plugin_contexts = (
                    [plugin_context]
                    if fallback_params.get("disable_multiplexing")
                    else rbn_split_plugin_context(plugin_context)
                )
                for context in plugin_contexts:
                    call_notification_script(plugin_name, context, plugin_timeout=plugin_timeout)
            else:
                logger.info("No rule matched, would notify fallback contacts, but none configured")
    else:
        # Now do the actual notifications
        logger.info("Executing %d notifications:", len(notifications))
        for (contacts, plugin_name), (_locked, params, bulk) in sorted(notifications.items()):
            would_notify = analyse and plugin_name != dispatch
            verb = "would notify" if would_notify else "notifying"
            contactstxt = ", ".join(contacts)
            plugintxt = plugin_name
            # Hack for "Call with the following..." find a better solution
            if (called_parameter := params.get("params")) is not None:
                params = called_parameter  # type: ignore[assignment]
            paramtxt = ", ".join(params) if params else "(no parameters)"
            bulktxt = "yes" if bulk else "no"
            logger.info(
                "  * %s %s via %s, parameters: %s, bulk: %s",
                verb,
                contactstxt,
                plugintxt,
                paramtxt,
                bulktxt,
            )

            try:
                plugin_context = create_plugin_context(enriched_context, params, get_http_proxy)
                rbn_add_contact_information(plugin_context, contacts, config_contacts)

                # params can be a list (e.g. for custom notificatios)
                split_contexts = (
                    plugin_name not in ["", "mail", "asciimail", "slack"]
                    or (isinstance(params, dict) and params.get("disable_multiplexing"))
                    or bulk
                )
                if not split_contexts:
                    plugin_contexts = [plugin_context]
                else:
                    plugin_contexts = rbn_split_plugin_context(plugin_context)

                for context in plugin_contexts:
                    plugin_info.append((context["CONTACTNAME"], plugin_name, params, bulk))

                    if analyse and would_notify:
                        continue
                    if bulk:
                        do_bulk_notify(plugin_name, params, context, bulk)
                    elif spooling in ("local", "both"):
                        create_spool_file(
                            logger,
                            notification_spooldir,
                            NotificationViaPlugin({"context": context, "plugin": plugin_name}),
                        )
                    else:
                        if dispatch and plugin_name != dispatch:
                            continue
                        call_notification_script(
                            plugin_name, context, plugin_timeout=plugin_timeout
                        )

            except Exception as e:
                if cmk.ccc.debug.enabled():
                    raise
                logger.exception("    ERROR:")
                log_to_history(
                    notification_result_message(
                        plugin=NotificationPluginName(plugin_name),
                        context=plugin_context,
                        exit_code=NotificationResultCode(2),
                        output=[str(e)],
                    )
                )

    return plugin_info


def rbn_fallback_contacts(*, config_contacts: ConfigContacts, fallback_email: str) -> Contacts:
    fallback_contacts: Contacts = []
    if fallback_email:
        fallback_contacts.append(rbn_fake_email_contact(fallback_email))

    for contact_name, contact in config_contacts.items():
        if contact.get("fallback_contact", False) and contact.get("email"):
            fallback_contact: Contact = {
                "name": contact_name,
            }
            fallback_contact.update(contact)
            fallback_contacts.append(fallback_contact)

    return fallback_contacts


def _rbn_finalize_plugin_parameters(
    hostname: HostName,
    plugin_name: NotificationPluginNameStr,
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    rule_parameters: NotifyPluginParamsDict,
    rule_matching_nr: int,
    rule_matching_text: str,
) -> NotifyPluginParamsDict:
    parameters = dict(host_parameters_cb(hostname, plugin_name)).copy()
    parameters.update(rule_parameters)

    # Added in 2.0.0b8. Applies if no value is set either in the notification rule
    # or the rule "Parameters for HTML Email".
    if plugin_name == "mail":
        parameters.setdefault("graphs_per_notification", 5)
        parameters.setdefault("notifications_with_graphs", 5)
        # Added in 2.4.0 for HTML Mail templates
        parameters.setdefault("matching_rule_nr", rule_matching_nr)
        parameters.setdefault("matching_rule_text", rule_matching_text)

    return parameters


# Create a table of all user specific notification rules. Important:
# create deterministic order, so that rule analyses can depend on
# rule indices
def user_notification_rules(config_contacts: ConfigContacts) -> list[EventRule]:
    user_rules = []
    for contactname in sorted(config_contacts):
        contact = config_contacts[contactname]
        for rule in contact.get("notification_rules", []):
            # User notification rules always use allow_disable
            # This line here is for legacy reasons. Newer versions
            # already set the allow_disable option in the rule configuration
            rule["allow_disable"] = True

            # Save the owner of the rule for later debugging
            rule["contact"] = contactname
            # We assume that the "contact_..." entries in the
            # rule are allowed and only contain one entry of the
            # type "contact_users" : [ contactname ]. This
            # is handled by WATO. Contact specific rules are a
            # WATO-only feature anyway...
            user_rules.append(rule)

            authorized_sites = contact.get("authorized_sites")
            if authorized_sites is not None and "match_site" not in rule:
                rule["match_site"] = authorized_sites

    logger.debug("Found %d user specific rules", len(user_rules))
    return user_rules


def rbn_fake_email_contact(email: str) -> Contact:
    return {
        "name": "mailto:" + email,
        "alias": "Explicit email adress " + email,
        "email": email,
        "pager": "",
    }


def rbn_add_contact_information(
    plugin_context: NotificationContext,
    contacts: Contacts | ContactNames,
    config_contacts: ConfigContacts,
) -> None:
    # TODO tb: Make contacts a reliable type. Righ now contacts can be
    # a list of dicts or a frozenset of strings.
    contact_dicts = []
    keys = {"name", "alias", "email", "pager"}

    for contact in contacts:
        if isinstance(contact, dict):
            contact_dict = contact
        elif contact.startswith("mailto:"):  # Fake contact
            contact_dict = {
                "name": contact[7:],
                "alias": "Email address " + contact,
                "email": contact[7:],
                "pager": "",
            }
        else:
            contact_dict = config_contacts.get(contact, {"alias": contact})
            contact_dict["name"] = contact

        contact_dicts.append(contact_dict)
        keys |= {key for key in contact_dict if key.startswith("_")}

    for key in keys:
        context_key = "CONTACT" + key.upper()
        items = [str(contact.get(key, "")) for contact in contact_dicts]
        plugin_context[context_key] = ",".join(items)


def rbn_split_plugin_context(plugin_context: NotificationContext) -> list[NotificationContext]:
    """Takes a plugin_context containing multiple contacts and returns
    a list of plugin_contexts with a context for each contact"""
    num_contacts = len(plugin_context["CONTACTNAME"].split(","))
    if num_contacts <= 1:
        return [plugin_context]

    contexts = []
    keys_to_split = {"CONTACTNAME", "CONTACTALIAS", "CONTACTEMAIL", "CONTACTPAGER"} | {
        key for key in plugin_context if key.startswith("CONTACT_")
    }

    for i in range(num_contacts):
        context = plugin_context.copy()
        for key in keys_to_split:
            context[key] = context[key].split(",")[i]
        contexts.append(NotificationContext(context))

    return contexts


def _rbn_get_bulk_params(
    rule: EventRule, timeperiods_active: _CoreTimeperiodsActive
) -> NotifyBulkParameters | None:
    bulk = rule.get("bulk")

    if not bulk:
        return None

    if isinstance(bulk, tuple):
        method, params = bulk
    else:
        method, params = (
            "always",
            bulk,
        )  # old format: treat as "Always Bulk" - typing says this can't ever be the case. Can it be removed?

    if is_always_bulk(params) or method == "always":
        return params

    if is_timeperiod_bulk(params):
        try:
            active = timeperiods_active.get(params["timeperiod"], False)
        except MKLivestatusException:
            if cmk.ccc.debug.enabled():
                raise
            # If a livestatus connection error appears we will bulk the
            # notification in the first place. When the connection is available
            # again and the period is not active the notifications will be sent.
            logger.info(
                "   - Error checking activity of time period %s: assuming active",
                params["timeperiod"],
            )
            active = True

        if active:
            return params
        return params.get("bulk_outside")

    logger.info("   - Unknown bulking method: assuming bulking is disabled")
    return None


def _rbn_match_rule(
    rule: EventRule,
    enriched_context: EnrichedEventContext,
    all_timeperiods: TimeperiodSpecs,
    *,
    define_servicegroups: Mapping[str, str],
    analyse: bool,
    timeperiods_active: _CoreTimeperiodsActive,
) -> str | None:
    return events.apply_matchers(
        [
            rbn_match_rule_disabled,
            lambda rule, context, analyse, all_timeperiods: events.event_match_rule(
                rule,
                context,
                define_servicegroups=define_servicegroups,
                all_timeperiods=all_timeperiods,
                analyse=analyse,
                timeperiods_active=timeperiods_active,
            ),
            rbn_match_escalation,
            rbn_match_escalation_throtte,
            rbn_match_host_event,
            rbn_match_service_event,
            rbn_match_notification_comment,
            rbn_match_event_console,
            rbn_match_timeperiod,
        ],
        rule,
        enriched_context,
        analyse,
        all_timeperiods,
    )


def rbn_match_timeperiod(
    rule: EventRule,
    context: EventContext,
    analyse: bool,
    all_timeperiods: TimeperiodSpecs,
) -> str | None:
    # This test is only done on notification tests, otherwise
    # events.event_match_timeperiod() is used
    if not analyse:
        return None

    if (timeperiod_name := rule.get("match_timeperiod")) is None:
        return None

    if timeperiod_name == "24X7":
        return None

    if "MICROTIME" in context:
        timestamp = float(context["MICROTIME"]) / 1000000.0
    else:
        timestamp = datetime.datetime.strptime(
            context["SHORTDATETIME"], "%Y-%m-%d %H:%M:%S"
        ).timestamp()

    if not is_timeperiod_active(
        timestamp=timestamp,
        timeperiod_name=timeperiod_name,
        all_timeperiods=all_timeperiods,
    ):
        return f"The notification does not match the timeperiod '{timeperiod_name}'"

    return None


def rbn_match_rule_disabled(
    rule: EventRule,
    _context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    return "This rule is disabled" if rule.get("disabled") else None


def rbn_match_escalation(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_escalation" in rule:
        from_number, to_number = rule["match_escalation"]
        if context["WHAT"] == "HOST":
            notification_number = int(context.get("HOSTNOTIFICATIONNUMBER", 1))
        else:
            notification_number = int(context.get("SERVICENOTIFICATIONNUMBER", 1))
        if not from_number <= notification_number <= to_number:
            return "The notification number %d does not lie in range %d ... %d" % (
                notification_number,
                from_number,
                to_number,
            )
    return None


def rbn_match_escalation_throtte(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_escalation_throttle" in rule:
        # We do not want to suppress recovery notifications.
        if (context["WHAT"] == "HOST" and context.get("HOSTSTATE", "UP") == "UP") or (
            context["WHAT"] == "SERVICE" and context.get("SERVICESTATE", "OK") == "OK"
        ):
            return None
        from_number, rate = rule["match_escalation_throttle"]
        if context["WHAT"] == "HOST":
            notification_number = int(context.get("HOSTNOTIFICATIONNUMBER", 1))
        else:
            notification_number = int(context.get("SERVICENOTIFICATIONNUMBER", 1))
        if notification_number <= from_number:
            return None
        if (notification_number - from_number) % rate != 0:
            return (
                "This notification is being skipped due to throttling. The next number will be %d"
                % (notification_number + rate - ((notification_number - from_number) % rate))
            )
    return None


def rbn_match_host_event(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_host_event" in rule:
        if context["WHAT"] != "HOST":
            if "EC_ID" in context:
                return None  # handled by rbn_match_event_console
            if "match_service_event" not in rule:
                return "This is a service notification, but the rule just matches host events"
            return None  # Let this be handled by match_service_event

        allowed_events = rule["match_host_event"]
        state = context["HOSTSTATE"]
        last_state = context["PREVIOUSHOSTHARDSTATE"]
        event_map = {"UP": "r", "DOWN": "d", "UNREACHABLE": "u"}
        return rbn_match_event(context, state, last_state, event_map, allowed_events)
    return None


def rbn_match_service_event(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_service_event" in rule:
        if context["WHAT"] != "SERVICE":
            if "match_host_event" not in rule:
                return "This is a host notification, but the rule just matches service events"
            return None  # Let this be handled by match_host_event

        allowed_events = rule["match_service_event"]
        state = context["SERVICESTATE"]
        last_state = context["PREVIOUSSERVICEHARDSTATE"]
        event_map = {"OK": "r", "WARNING": "w", "CRITICAL": "c", "UNKNOWN": "u"}
        return rbn_match_event(context, state, last_state, event_map, allowed_events)
    return None


def rbn_match_event(
    context: EventContext,
    state: str,
    last_state: str,
    event_map: dict[str, str],
    allowed_events: Sequence[ServiceEventType] | Sequence[HostEventType],
) -> str | None:
    notification_type = context["NOTIFICATIONTYPE"]

    if notification_type == "RECOVERY":
        event = event_map.get(last_state, "?") + "r"
    elif notification_type in ["FLAPPINGSTART", "FLAPPINGSTOP", "FLAPPINGDISABLED"]:
        event = "f"
    elif notification_type in ["DOWNTIMESTART", "DOWNTIMEEND", "DOWNTIMECANCELLED"]:
        event = "s"
    elif notification_type == "ACKNOWLEDGEMENT":
        event = "x"
    elif notification_type.startswith("ALERTHANDLER ("):
        handler_state = notification_type[14:-1]
        if handler_state == "OK":
            event = "as"
        else:
            event = "af"
    else:
        event = event_map.get(last_state, "?") + event_map.get(state, "?")

    # Now go through the allowed events. Handle '?' has matching all types!
    for allowed in allowed_events:
        if (
            event == allowed
            or (allowed[0] == "?" and len(event) > 1 and event[1] == allowed[1])
            or (event[0] == "?" and len(allowed) > 1 and event[1] == allowed[1])
        ):
            return None

    return "Event type '{}' not handled by this rule. Allowed are: {}".format(
        event,
        ", ".join(allowed_events),
    )


def rbn_rule_contacts(
    rule: EventRule,
    context: EventContext,
    *,
    fallback_email: str,
    config_contacts: ConfigContacts,
) -> ContactNames:
    the_contacts = set()
    if rule.get("contact_object"):
        the_contacts.update(
            rbn_object_contact_names(
                context, config_contacts=config_contacts, fallback_email=fallback_email
            )
        )
    if rule.get("contact_all"):
        the_contacts.update(rbn_all_contacts(config_contacts=config_contacts))
    if rule.get("contact_all_with_email"):
        the_contacts.update(rbn_all_contacts(config_contacts=config_contacts, with_email=True))
    if "contact_users" in rule:
        the_contacts.update(rule["contact_users"])
    if "contact_groups" in rule:
        the_contacts.update(
            rbn_groups_contacts(rule["contact_groups"], config_contacts=config_contacts)
        )
    if "contact_emails" in rule:
        the_contacts.update(rbn_emails_contacts(rule["contact_emails"]))

    all_enabled = []
    for contactname in the_contacts:
        if contactname == fallback_email:
            contact: Contact | None = rbn_fake_email_contact(fallback_email)
        else:
            contact = config_contacts.get(contactname)

        if contact:
            disable_notifications_opts = contact.get("disable_notifications", {})
            if disable_notifications_opts.get("disable", False):
                start, end = disable_notifications_opts.get("timerange", (None, None))
                if start is None or end is None:
                    logger.info(
                        "   - skipping contact %s: he/she has disabled notifications", contactname
                    )
                    continue
                if start <= time.time() <= end:
                    logger.info(
                        "   - skipping contact %s: he/she has disabled notifications from %s to %s.",
                        contactname,
                        start,
                        end,
                    )
                    continue

            reason = rbn_match_contact_macros(
                rule, contactname, contact
            ) or rbn_match_contact_groups(rule, contactname, contact)

            if reason:
                logger.info("   - skipping contact %s: %s", contactname, reason)
                continue

        else:
            logger.info(
                "Warning: cannot get information about contact %s: ignoring restrictions",
                contactname,
            )

        all_enabled.append(contactname)

    return frozenset(all_enabled)  # has to be hashable


def rbn_match_contact_macros(
    rule: EventRule, contactname: ContactName, contact: Contact
) -> str | None:
    if "contact_match_macros" in rule:
        for macro_name, regexp in rule["contact_match_macros"]:
            value = str(contact.get("_" + macro_name, ""))
            if not regexp.endswith("$"):
                regexp = regexp + "$"
            if not regex(regexp).match(value):
                macro_overview = ", ".join(
                    [
                        f"{varname[1:]}={val}"
                        for (varname, val) in contact.items()
                        if varname.startswith("_")
                    ]
                )
                return f"value '{value}' for macro '{macro_name}' does not match '{regexp}'. His macros are: {macro_overview}"
    return None


def rbn_match_contact_groups(
    rule: EventRule, contactname: ContactName, contact: Contact
) -> str | None:
    if "contact_match_groups" in rule:
        if "contactgroups" not in contact:
            logger.info(
                "Warning: cannot determine contact groups of %s: skipping restrictions", contactname
            )
            return None

        for required_group in rule["contact_match_groups"]:
            contactgroups = contact["contactgroups"]
            assert isinstance(contactgroups, tuple | list)

            if required_group not in contactgroups:
                return "he/she is not member of the contact group {} (his groups are {})".format(
                    required_group,
                    ", ".join(contactgroups or ["<None>"]),
                )
    return None


def rbn_match_notification_comment(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    if "match_notification_comment" in rule:
        r = regex(rule["match_notification_comment"])
        notification_comment = context.get("NOTIFICATIONCOMMENT", "")
        if not r.match(notification_comment):
            return "The beginning of the notification comment '{}' is not matched by the regex '{}'".format(
                notification_comment, rule["match_notification_comment"]
            )
    return None


def rbn_match_event_console(
    rule: EventRule,
    context: EventContext,
    _analyse: bool,
    _all_timeperiods: TimeperiodSpecs,
) -> str | None:
    """
    match_ec options:
    missing, without match_host_event and match_service_event -> match All events
    missing, with match_host_event and/or match_service_event -> do not match on Event Console notifications
    empty dict -> match on all Event Console notifications
    dict with keys -> match on specific Event Console notifications
    """
    # "Triggering events" - "All events"
    match_all_events = (
        "match_ec" not in rule
        and "match_host_event" not in rule
        and "match_service_event" not in rule
    )
    # "Triggering events" - "Event console alerts"
    match_ec_alerts_explicit = "match_ec" in rule

    # "Triggering events" - "Host events" or "Service events"
    match_host_or_service_events_explicit = (
        "match_host_event" in rule or "match_service_event" in rule
    )

    is_ec_notification = "EC_ID" in context
    match_ec = match_all_events or match_ec_alerts_explicit
    if not match_ec and is_ec_notification:
        return "Notification has been created by the Event Console."

    match_ec_options = rule.get("match_ec", False)

    match_only_ec_events = match_ec_options or (
        not match_all_events and not match_host_or_service_events_explicit
    )
    if not is_ec_notification and match_only_ec_events:
        return "Notification has not been created by the Event Console."

    if match_ec:
        if match_ec_options and is_ec_notification:
            # Match Event Console rule ID
            if (
                "match_rule_id" in match_ec_options
                and context["EC_RULE_ID"] not in match_ec_options["match_rule_id"]
            ):
                return "EC Event has rule ID '{}', but '{}' is required".format(
                    context["EC_RULE_ID"],
                    match_ec_options["match_rule_id"],
                )

            # Match syslog priority of event
            if "match_priority" in match_ec_options:
                prio_from, prio_to = match_ec_options["match_priority"]
                if prio_from > prio_to:
                    prio_to, prio_from = prio_from, prio_to
                    p = int(context["EC_PRIORITY"])
                    if p < prio_from or p > prio_to:
                        return (
                            f"Event has priority {p}, but matched range is {prio_from} .. {prio_to}"
                        )

            # Match syslog facility of event
            if "match_facility" in match_ec_options:
                if match_ec_options["match_facility"] != int(context["EC_FACILITY"]):
                    return "Wrong syslog facility {}, required is {}".format(
                        context["EC_FACILITY"],
                        match_ec_options["match_facility"],
                    )

            # Match event comment
            if "match_comment" in match_ec_options:
                r = regex(match_ec_options["match_comment"])
                if not r.search(context["EC_COMMENT"]):
                    return (
                        "The event comment '{}' does not match the regular expression '{}'".format(
                            context["EC_COMMENT"],
                            match_ec_options["match_comment"],
                        )
                    )
    return None


def rbn_object_contact_names(
    context: EventContext,
    *,
    config_contacts: ConfigContacts,
    fallback_email: str,
) -> list[ContactName]:
    commasepped = context.get("CONTACTS")
    if commasepped == "?":
        logger.info(
            "Warning: Contacts of %s cannot be determined. Using fallback contacts",
            events.find_host_service_in_context(context),
        )
        return [
            str(contact["name"])
            for contact in rbn_fallback_contacts(
                config_contacts=config_contacts, fallback_email=fallback_email
            )
        ]

    if commasepped:
        return commasepped.split(",")

    return []


def rbn_all_contacts(
    *, config_contacts: ConfigContacts, with_email: bool = False
) -> list[ContactName]:
    if not with_email:
        return list(config_contacts)  # We have that via our main.mk contact definitions!

    return [contact_id for (contact_id, contact) in config_contacts.items() if contact.get("email")]


def _contactgroup_members(
    *,
    config_contacts: ConfigContacts,
) -> Mapping[_ContactgroupName, set[ContactName]]:
    """Get the members of all contact groups

    Is computed once  for the process lifetime since it's either a short lived process or in case of
    the Micro Core notify helper, it is restarted once a new configuration is applied to the core.
    """
    members: dict[_ContactgroupName, set[ContactName]] = {}
    for name, contact in config_contacts.items():
        for group_name in contact.get("contactgroups", []):
            members.setdefault(group_name, set()).add(name)
    return members


def rbn_groups_contacts(groups: list[str], *, config_contacts: ConfigContacts) -> set[str]:
    """Return all members of the given groups"""
    if not groups:
        return set()  # optimization only

    members = _contactgroup_members(config_contacts=config_contacts)
    return {m for group in groups for m in members.get(group, [])}


def rbn_emails_contacts(emails: list[str]) -> list[str]:
    return ["mailto:" + e for e in emails]


# .
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   |  Code for the actuall calling of notification plugins (scripts).     |
#   '----------------------------------------------------------------------'

# Exit codes for plugins and also for our functions that call the plugins:
# 0: Notification successfully sent
# 1: Could not send now, please retry later
# 2: Cannot send, retry does not make sense


# Add the plug-in parameters to the envinroment. We have two types of parameters:
# - list, the legacy style. This will lead to PARAMETERS_1, ...
# - dict, the new style for scripts with WATO rule. This will lead to
#         PARAMETER_FOO_BAR for a dict key named "foo_bar".
def create_plugin_context(
    enriched_context: EnrichedEventContext,
    params: NotifyPluginParamsDict,
    get_http_proxy: events.ProxyGetter,
) -> NotificationContext:
    plugin_context = NotificationContext({})
    plugin_context.update(cast(Mapping[str, str], enriched_context))  # Make a real copy

    events.add_to_event_context(plugin_context, "PARAMETER", params, get_http_proxy)
    return plugin_context


def create_bulk_parameter_context(
    params: NotifyPluginParamsDict,
    get_http_proxy: events.ProxyGetter,
) -> list[str]:
    dict_context = create_plugin_context({}, params, get_http_proxy)
    return [
        "{}={}\n".format(varname, value.replace("\r", "").replace("\n", "\1"))
        for (varname, value) in dict_context.items()
    ]


def path_to_notification_script(plugin_name: NotificationPluginNameStr) -> str | None:
    if "/" in plugin_name:
        logger.error("Pluginname %r with slash. Raising exception...")
        raise MKGeneralException("Slashes in plugin_name are forbidden!")

    # Call actual script without any arguments
    local_path = cmk.utils.paths.local_notifications_dir / plugin_name
    if local_path.exists():
        path = local_path
    else:
        path = cmk.utils.paths.notifications_dir / plugin_name

    if not path.exists():
        logger.info("Notification plug-in '%s' not found", plugin_name)
        logger.info("  not in %s", cmk.utils.paths.notifications_dir)
        logger.info("  and not in %s", cmk.utils.paths.local_notifications_dir)
        return None

    return str(path)


# This is the function that finally sends the actual notification.
# It does this by calling an external script are creating a
# plain email and calling bin/mail.
#
# It also does the central logging of the notifications
# that are actually sent out.
#
# Note: this function is *not* being called for bulk notification.
def call_notification_script(
    plugin_name: NotificationPluginNameStr,
    plugin_context: NotificationContext,
    *,
    plugin_timeout: int,
    is_spoolfile: bool = False,
) -> int:
    log_to_history(
        notification_message(
            NotificationPluginName(plugin_name),
            plugin_context,
        )
    )

    def plugin_log(s: str) -> None:
        logger.info("     %s", s)

    # Call actual script without any arguments
    path = path_to_notification_script(plugin_name)
    if not path:
        return 2

    plugin_log("executing %s" % path)

    with subprocess.Popen(
        [path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=notification_script_env(plugin_context),
        encoding="utf-8",
        close_fds=True,
    ) as p:
        output_lines: list[str] = []
        assert p.stdout is not None

        with Timeout(
            plugin_timeout,
            message="Notification plug-in timed out",
        ) as timeout_guard:
            try:
                while True:
                    # read and output stdout linewise to ensure we don't force python to produce
                    # one - potentially huge - memory buffer
                    if not (line := p.stdout.readline()):
                        break
                    output = line.rstrip()
                    plugin_log("Output: %s" % output)
                    output_lines.append(output)
                    if _log_to_stdout:
                        with suppress(IOError):
                            sys.stdout.write(line)
                            sys.stdout.flush()
            except MKTimeout:
                plugin_log(
                    "Notification plug-in did not finish within %d seconds. Terminating."
                    % plugin_timeout
                )
                p.kill()

    if exitcode := 1 if timeout_guard.signaled else p.returncode:
        plugin_log("Plug-in exited with code %d" % exitcode)

    # Result is already logged to history for spoolfiles by
    # mknotifyd.spool_handler
    if not is_spoolfile:
        log_to_history(
            notification_result_message(
                plugin=NotificationPluginName(plugin_name),
                context=plugin_context,
                exit_code=NotificationResultCode(exitcode),
                output=output_lines,
            )
        )

    return exitcode


# Construct the environment for the notification script
def notification_script_env(plugin_context: NotificationContext) -> PluginNotificationContext:
    # Use half of the maximum allowed string length MAX_ARG_STRLEN
    # which is usually 32 pages on Linux (see "man execve").
    #
    # Assumption: We don't have to consider ARG_MAX, i.e. the maximum
    # size of argv + envp, because it is derived from RLIMIT_STACK
    # and large enough.
    try:
        max_length = 32 * os.sysconf("SC_PAGESIZE") // 2
    except ValueError:
        max_length = 32 * 4046 // 2

    def format_(value: str) -> str:
        if len(value) > max_length:
            return (
                value[:max_length]
                + "...\nAttention: Removed remaining content because it was too long."
            )
        return value

    notify_env = os.environ.copy()
    notify_env.update(
        {"NOTIFY_" + variable: format_(value) for variable, value in plugin_context.items()}
    )

    return notify_env


# .
#   .--Spooling------------------------------------------------------------.
#   |               ____                    _ _                            |
#   |              / ___| _ __   ___   ___ | (_)_ __   __ _                |
#   |              \___ \| '_ \ / _ \ / _ \| | | '_ \ / _` |               |
#   |               ___) | |_) | (_) | (_) | | | | | | (_| |               |
#   |              |____/| .__/ \___/ \___/|_|_|_| |_|\__, |               |
#   |                    |_|                          |___/                |
#   +----------------------------------------------------------------------+
#   |  Some functions dealing with the spooling of notifications.          |
#   '----------------------------------------------------------------------'


# There are three types of spool files:
# 1. Notifications to be forwarded. Contain key "forward"
# 2. Notifications for async local delivery. Contain key "plugin"
# 3. Notifications that *were* forwarded (e.g. received from a slave). Contain neither of both.
# Spool files of type 1 are not handled here!
def _handle_spoolfile(
    spoolfile: str,
    host_parameters_cb: Callable[[HostName, NotificationPluginNameStr], Mapping[str, object]],
    get_http_proxy: events.ProxyGetter,
    rules: Iterable[EventRule],
    parameters: NotificationParameterSpecs,
    define_servicegroups: Mapping[str, str],
    config_contacts: ConfigContacts,
    fallback_email: str,
    fallback_format: _FallbackFormat,
    plugin_timeout: int,
    all_timeperiods: TimeperiodSpecs,
    spooling: Literal["local", "remote", "both", "off"],
    backlog_size: int,
    timeperiods_active: _CoreTimeperiodsActive,
) -> int:
    notif_uuid = spoolfile.rsplit("/", 1)[-1]
    logger.info("----------------------------------------------------------------------")
    data = None
    spoolfile_path = Path(spoolfile)
    try:
        if not spoolfile_path.exists():
            logger.warning("Skipping missing spoolfile %s.", notif_uuid[:8])
            return 2

        with store.locked(spoolfile_path):
            data = store.load_object_from_file(spoolfile_path, default={})

        if not data:
            logger.warning("Skipping empty spool file %s", notif_uuid[:8])
            return 2

        if "plugin" in data:
            plugin_context = data["context"]
            plugin_name = data["plugin"]
            logger.info(
                "Got spool file %s (%s) for local delivery via %s",
                notif_uuid[:8],
                events.find_host_service_in_context(plugin_context),
                (plugin_name),
            )
            return call_notification_script(
                plugin_name=plugin_name,
                plugin_context=plugin_context,
                plugin_timeout=plugin_timeout,
                is_spoolfile=True,
            )

        # We received a forwarded raw notification. We need to process
        # this with our local notification rules in order to call one,
        # several or no actual plugins.
        raw_context = data["context"]
        logger.info(
            "Got spool file %s (%s) from remote host for local delivery.",
            notif_uuid[:8],
            events.find_host_service_in_context(raw_context),
        )

        store_notification_backlog(raw_context, backlog_size=backlog_size)
        _locally_deliver_raw_context(
            raw_context,
            host_parameters_cb,
            get_http_proxy,
            rules=rules,
            parameters=parameters,
            define_servicegroups=define_servicegroups,
            config_contacts=config_contacts,
            plugin_timeout=plugin_timeout,
            fallback_email=fallback_email,
            fallback_format=fallback_format,
            spooling=spooling,
            all_timeperiods=all_timeperiods,
            timeperiods_active=timeperiods_active,
        )
        # TODO: It is a bug that we don't transport result information and monitoring history
        # entries back to the origin site. The intermediate or final results should be sent back to
        # the origin site. Also log_to_history calls should not log the entries to the local
        # monitoring core of the destination site, but forward the log entries as messages to the
        # remote site just like the mknotifyd is doing with MessageResult. We could create spool
        # files holding NotificationResult messages which would then be forwarded to the origin site
        # by the mknotifyd. See CMK-10779.
        return 0  # No error handling for async delivery

    except Exception:
        logger.exception("ERROR while processing %s:", spoolfile)
        logger.error("Content: %r", data)
        return 2


# .
#   .--Bulk-Notifications--------------------------------------------------.
#   |                         ____        _ _                              |
#   |                        | __ ) _   _| | | __                          |
#   |                        |  _ \| | | | | |/ /                          |
#   |                        | |_) | |_| | |   <                           |
#   |                        |____/ \__,_|_|_|\_\                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Store postponed bulk notifications for later delivery. Deliver such |
#   |  notifications on cmk --notify bulk.                                 |
#   '----------------------------------------------------------------------'


def do_bulk_notify(
    plugin_name: NotificationPluginNameStr,
    params: NotifyPluginParamsDict,
    plugin_context: NotificationContext,
    bulk: NotifyBulkParameters,
) -> None:
    # First identify the bulk. The following elements identify it:
    # 1. contact
    # 2. plugin
    # 3. time horizon (interval) in seconds
    # 4. max bulked notifications
    # 5. elements specified in bulk["groupby"] and bulk["groupby_custom"]
    # We first create a bulk path constructed as a tuple of strings.
    # Later we convert that to a unique directory name.
    # Note: if you have separate bulk rules with exactly the same
    # bulking options, then they will use the same bulk.

    what = plugin_context["WHAT"]
    contact = plugin_context["CONTACTNAME"]
    if "/" in contact or "/" in plugin_name:
        logger.error("Tried to construct bulk dir with unsanitized attributes")
        raise MKGeneralException("Slashes in CONTACTNAME or plugin_name are forbidden!")
    if is_timeperiod_bulk(bulk):
        bulk_path: list[str] = [
            contact,
            plugin_name,
            "timeperiod:" + bulk["timeperiod"],
            str(bulk["count"]),
        ]
    elif is_always_bulk(bulk):
        bulk_path = [contact, plugin_name, str(bulk["interval"]), str(bulk["count"])]

    bulkby = bulk["groupby"]
    if "bulk_subject" in bulk:
        plugin_context["PARAMETER_BULK_SUBJECT"] = bulk["bulk_subject"]

    if "host" in bulkby:
        bulk_path.extend(
            [
                "host",
                plugin_context["HOSTNAME"],
            ]
        )

    elif "folder" in bulkby:
        bulk_path.extend(
            [
                "folder",
                str(find_wato_folder(NotificationContext(plugin_context))),
            ]
        )

    if "service" in bulkby:
        bulk_path.extend(
            [
                "service",
                plugin_context.get("SERVICEDESC", ""),
            ]
        )

    if "sl" in bulkby:
        bulk_path.extend(
            [
                "sl",
                plugin_context.get(what + "_SL", ""),
            ]
        )

    if "check_type" in bulkby:
        bulk_path.extend(
            [
                "check_type",
                plugin_context.get(what + "CHECKCOMMAND", "").split("!")[0],
            ]
        )

    if "state" in bulkby:
        bulk_path.extend(
            [
                "state",
                plugin_context.get(what + "STATE", ""),
            ]
        )

    if "ec_contact" in bulkby:
        bulk_path.extend(
            [
                "ec_contact",
                plugin_context.get("EC_CONTACT", ""),
            ]
        )

    if "ec_comment" in bulkby:
        bulk_path.extend(
            [
                "ec_comment",
                plugin_context.get("EC_COMMENT", ""),
            ]
        )

    # User might have specified _FOO instead of FOO
    bulkby_custom = bulk.get("groupby_custom", [])
    for macroname in bulkby_custom:
        macroname = macroname.lstrip("_").upper()
        value = plugin_context.get("SERVICE" + "_" + macroname, "") or plugin_context.get(
            "HOST" + "_" + macroname, ""
        )
        bulk_path.extend(
            [
                macroname.lower(),
                value,
            ]
        )

    logger.info("    --> storing for bulk notification %s", "|".join(bulk_path))
    bulk_dir = _create_bulk_dir(bulk_path)
    notify_uuid = str(uuid.uuid4())
    filename_new = bulk_dir / f"{notify_uuid}.new"
    filename_final = bulk_dir / notify_uuid
    filename_new.write_text(f"{(params, plugin_context)!r}\n")
    filename_new.rename(filename_final)  # We need an atomic creation!
    logger.info("        - stored in %s", filename_final)


def _create_bulk_dir(bulk_path: Sequence[str]) -> Path:
    bulk_dir = Path(
        notification_bulkdir,
        bulk_path[0],
        bulk_path[1],
        ",".join([b.replace("/", "\\") for b in bulk_path[2:]]),
    )
    if not bulk_dir.exists():
        bulk_dir.mkdir(parents=True)
        logger.info("        - created bulk directory %s", bulk_dir)
    return bulk_dir


def bulk_parts(method_dir: str, bulk: str) -> tuple[int | None, str | None, int] | None:
    parts = bulk.split(",")

    try:
        interval: int | None = int(parts[0])
        timeperiod: str | None = None
    except ValueError:
        entry = parts[0].split(":")
        if entry[0] == "timeperiod" and len(entry) == 2:
            interval, timeperiod = None, entry[1]
        else:
            logger.info("Skipping invalid bulk directory %s", method_dir)
            return None

    try:
        count = int(parts[1])
    except ValueError:
        logger.info("Skipping invalid bulk directory %s", method_dir)
        return None

    return interval, timeperiod, count


def bulk_uuids(bulk_dir: str) -> tuple[UUIDs, float]:
    uuids, oldest = [], time.time()
    for notify_uuid in os.listdir(bulk_dir):  # 4ded0fa2-f0cd-4b6a-9812-54374a04069f
        if notify_uuid.endswith(".new"):
            continue
        if len(notify_uuid) != 36:
            logger.info(
                "Skipping invalid notification file %s", os.path.join(bulk_dir, notify_uuid)
            )
            continue

        mtime = os.stat(os.path.join(bulk_dir, notify_uuid)).st_mtime
        uuids.append((mtime, notify_uuid))
        oldest = min(oldest, mtime)
    uuids.sort()
    return uuids, oldest


def remove_if_orphaned(bulk_dir: str, max_age: float, ref_time: float | None = None) -> None:
    if not ref_time:
        ref_time = time.time()

    dirage = ref_time - os.stat(bulk_dir).st_mtime
    if dirage > max_age:
        logger.info("Warning: removing orphaned empty bulk directory %s", bulk_dir)
        try:
            os.rmdir(bulk_dir)
        except Exception as e:
            logger.info("    -> Error removing it: %s", e)


def _find_bulks(
    only_ripe: bool,
    *,
    bulk_interval: int,
    timeperiods_active: _CoreTimeperiodsActive,
) -> NotifyBulks:
    if not os.path.exists(notification_bulkdir):
        return []

    def listdir_visible(path: str) -> list[str]:
        return [x for x in os.listdir(path) if not x.startswith(".")]

    bulks: NotifyBulks = []
    now = time.time()
    for contact in listdir_visible(notification_bulkdir):
        contact_dir = os.path.join(notification_bulkdir, contact)
        for method in listdir_visible(contact_dir):
            method_dir = os.path.join(contact_dir, method)
            for bulk in listdir_visible(method_dir):
                bulk_dir = os.path.join(method_dir, bulk)

                uuids, oldest = bulk_uuids(bulk_dir)
                if not uuids:
                    remove_if_orphaned(bulk_dir, max_age=60, ref_time=now)
                    continue
                age = now - oldest

                # e.g. 60,10,host,localhost OR timeperiod:late_night,1000,host,localhost
                parts = bulk_parts(method_dir, bulk)
                if parts is None:
                    continue
                interval, timeperiod, count = parts

                if interval is not None:
                    if age >= interval:
                        logger.info("Bulk %s is ripe: age %d >= %d", bulk_dir, age, interval)
                    elif len(uuids) >= count:
                        logger.info("Bulk %s is ripe: count %d >= %d", bulk_dir, len(uuids), count)
                    else:
                        logger.info(
                            "Bulk %s is not ripe yet (age: %d, count: %d)!",
                            bulk_dir,
                            age,
                            len(uuids),
                        )
                        if only_ripe:
                            continue

                    bulks.append((bulk_dir, age, interval, "n.a.", count, uuids))
                else:
                    assert timeperiod is not None  # TODO: Improve typing of bulk_parts()
                    try:
                        active = timeperiods_active.get(TimeperiodName(timeperiod))
                    except Exception:
                        # This prevents sending bulk notifications if a
                        # livestatus connection error appears. It also implies
                        # that an ongoing connection error will hold back bulk
                        # notifications.
                        logger.info(
                            "Error while checking activity of time period %s: assuming active",
                            timeperiod,
                        )
                        active = True

                    if active is True and len(uuids) < count:
                        # Only add a log entry every 10 minutes since timeperiods
                        # can be very long (The default would be 10s).
                        if now % 600 <= bulk_interval:
                            logger.info(
                                "Bulk %s is not ripe yet (time period %s: active, count: %d)",
                                bulk_dir,
                                timeperiod,
                                len(uuids),
                            )

                        if only_ripe:
                            continue
                    elif active is False:
                        logger.info(
                            "Bulk %s is ripe: time period %s has ended", bulk_dir, timeperiod
                        )
                    elif len(uuids) >= count:
                        logger.info("Bulk %s is ripe: count %d >= %d", bulk_dir, len(uuids), count)
                    else:
                        logger.info(
                            "Bulk %s is ripe: time period %s is not known anymore",
                            bulk_dir,
                            timeperiod,
                        )

                    bulks.append((bulk_dir, age, "n.a.", timeperiod, count, uuids))
    return bulks


def _send_ripe_bulks(
    get_http_proxy: events.ProxyGetter,
    timeperiods_active: _CoreTimeperiodsActive,
    *,
    bulk_interval: int,
    plugin_timeout: int,
) -> None:
    ripe = _find_bulks(True, bulk_interval=bulk_interval, timeperiods_active=timeperiods_active)
    if ripe:
        logger.info("Sending out %d ripe bulk notifications", len(ripe))
        for bulk in ripe:
            try:
                notify_bulk(bulk[0], bulk[-1], get_http_proxy, plugin_timeout=plugin_timeout)
            except Exception:
                if cmk.ccc.debug.enabled():
                    raise
                logger.exception("Error sending bulk %s:", bulk[0])


def notify_bulk(
    dirname: str,
    uuids: UUIDs,
    get_http_proxy: events.ProxyGetter,
    *,
    plugin_timeout: int,
) -> None:
    parts = dirname.split("/")
    contact = parts[-3]
    plugin_name = cast(NotificationPluginNameStr, parts[-2])
    logger.info("   -> %s/%s %s", contact, plugin_name, dirname)
    # If new entries are created in this directory while we are working
    # on it, nothing bad happens. It's just that we cannot remove
    # the directory after our work. It will be the starting point for
    # the next bulk with the same ID, which is completely OK.
    bulk_context = []
    old_params: NotifyPluginParamsDict | None = None
    unhandled_uuids: UUIDs = []
    for mtime, notify_uuid in uuids:
        try:
            params, context = store.load_object_from_file(Path(dirname) / notify_uuid, default=None)
        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            logger.info(
                "    Deleting corrupted or empty bulk file %s/%s: %s", dirname, notify_uuid, e
            )
            continue

        if old_params is None:
            old_params = params
        elif params != old_params:
            logger.info(
                "     Parameters are different from previous, postponing into separate bulk"
            )
            unhandled_uuids.append((mtime, notify_uuid))
            continue

        bulk_context.append(NotificationContext(context))

    if bulk_context:  # otherwise: only corrupted files
        # Per default the uuids are sorted chronologically from oldest to newest
        # Therefore the notification plug-in also shows the oldest entry first
        # The following configuration option allows to reverse the sorting
        if isinstance(old_params, dict) and old_params.get("bulk_sort_order") == "newest_first":
            bulk_context.reverse()

        assert old_params is not None
        plugin_text = NotificationPluginName("bulk " + (plugin_name))
        context_lines = create_bulk_parameter_context(old_params, get_http_proxy)
        for context in bulk_context:
            # Do not forget to add this to the monitoring log. We create
            # a single entry for each notification contained in the bulk.
            # It is important later to have this precise information.
            log_to_history(notification_message(plugin_text, context))

            context_lines.append("\n")
            for varname, value in context.items():
                line = "{}={}\n".format(varname, value.replace("\r", "").replace("\n", "\1"))
                context_lines.append(line)

        exitcode, output_lines = call_bulk_notification_script(
            plugin_name, context_lines, plugin_timeout=plugin_timeout
        )

        for context in bulk_context:
            log_to_history(
                notification_result_message(
                    plugin=plugin_text,
                    context=context,
                    exit_code=exitcode,
                    output=output_lines,
                )
            )
    else:
        logger.info("No valid notification file left. Skipping this bulk.")

    # Remove sent notifications
    for mtime, notify_uuid in uuids:
        if (mtime, notify_uuid) not in unhandled_uuids:
            path = os.path.join(dirname, notify_uuid)
            try:
                os.remove(path)
            except Exception as e:
                logger.info("Cannot remove %s: %s", path, e)

    # Repeat with unhandled uuids (due to different parameters)
    if unhandled_uuids:
        notify_bulk(dirname, unhandled_uuids, get_http_proxy, plugin_timeout=plugin_timeout)

    # Remove directory. Not necessary if emtpy
    try:
        os.rmdir(dirname)
    except Exception as e:
        if not unhandled_uuids:
            logger.info("Warning: cannot remove directory %s: %s", dirname, e)


def call_bulk_notification_script(
    plugin_name: NotificationPluginNameStr, context_lines: list[str], *, plugin_timeout: int
) -> tuple[NotificationResultCode, list[str]]:
    path = path_to_notification_script(plugin_name)
    if not path:
        raise MKGeneralException("Notification plug-in %s not found" % plugin_name)

    timed_out = False
    # Protocol: The script gets the context on standard input and
    # read until that is closed. It is being called with the parameter
    # --bulk.
    with subprocess.Popen(
        [path, "--bulk"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        close_fds=True,
        encoding="utf-8",
    ) as p:
        try:
            stdout, stderr = p.communicate(
                input="".join(context_lines),
                timeout=plugin_timeout,
            )
        except subprocess.TimeoutExpired:
            logger.info(
                "Notification plug-in did not finish within %d seconds. Terminating.",
                plugin_timeout,
            )
            p.kill()
            stdout, stderr = p.communicate()
            timed_out = True

    if exitcode := 1 if timed_out else p.returncode:
        logger.info(
            "ERROR: script %s --bulk returned with exit code %s",
            path,
            exitcode,
        )

    output_lines = (stdout + stderr).splitlines()
    for line in output_lines:
        logger.info("%s: %s", plugin_name, line.rstrip())

    return NotificationResultCode(exitcode), output_lines


# .
#   .--Contexts------------------------------------------------------------.
#   |                 ____            _            _                       |
#   |                / ___|___  _ __ | |_ _____  _| |_ ___                 |
#   |               | |   / _ \| '_ \| __/ _ \ \/ / __/ __|                |
#   |               | |__| (_) | | | | ||  __/>  <| |_\__ \                |
#   |                \____\___/|_| |_|\__\___/_/\_\\__|___/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Functions dealing with loading, storing and converting contexts.    |
#   '----------------------------------------------------------------------'


def store_notification_backlog(raw_context: EventContext, *, backlog_size: int) -> None:
    path = notification_logdir / "backlog.mk"
    if not backlog_size:
        if path.exists():
            path.unlink()
        return

    backlog = store.load_object_from_file(
        path,
        default=[],
        lock=True,
    )[: backlog_size - 1]
    store.save_object_to_file(path, [raw_context] + backlog, pprint_value=False)


def raw_context_from_backlog(nr: int) -> EventContext:
    backlog = store.load_object_from_file(notification_logdir / "backlog.mk", default=[])

    if nr < 0 or nr >= len(backlog):
        console.error(f"No notification number {nr} in backlog.", file=sys.stderr)
        sys.exit(2)

    logger.info("Replaying notification %d from backlog...\n", nr)
    return backlog[nr]


def raw_context_from_env(environ: Mapping[str, str]) -> EventContext:
    context = cast(
        EventContext,
        {
            var[7:]: value
            for (var, value) in environ.items()
            if var.startswith("NOTIFY_") and not dead_nagios_variable(value)
        },
    )
    events.pipe_decode_raw_context(context)
    return context


def substitute_context(template: str, context: NotificationContext) -> str:
    """
    Replace all known variables with values and all unknown variables with empty strings
    Example:
        >>> substitute_context("abc $A$ $B$ $C$", {"A": "A", "B": "B"})
        'abc A B '
    """
    return re.sub(
        r"\$[A-Z]+\$",
        "",
        replace_macros_in_str(template, {f"${k}$": v for k, v in context.items()}),
    )


# .
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Some generic helper functions                                       |
#   '----------------------------------------------------------------------'


def format_exception() -> str:
    txt = io.StringIO()
    t, v, tb = sys.exc_info()
    traceback.print_exception(t, v, tb, None, txt)
    return str(txt.getvalue())


def dead_nagios_variable(value: str) -> bool:
    """check if nagios var was not substitued

    >>> dead_nagios_variable("$SERVICEACKAUTHOR$")
    True
    >>> dead_nagios_variable("some value")
    False
    """
    if len(value) < 3:
        return False
    if value[0] != "$" or value[-1] != "$":
        return False
    for c in value[1:-1]:
        if not c.isupper() and c != "_":
            return False
    return True
