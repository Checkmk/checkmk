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

# Please have a look at doc/Notifications.png:
#
# There are two types of contexts:
# 1. Raw contexts (purple)
#    => These come right out of the monitoring core. They are not yet
#       assinged to a certain plugin. In case of rule based notifictions
#       they are not even assigned to a certain contact.
#
# 2. Plugin contexts (cyan)
#    => These already bear all information about the contact, the plugin
#       to call and its parameters.

import os
import re
import signal
import subprocess
import sys
import time

# suppress "Cannot find module" error from mypy
import livestatus  # type: ignore
import cmk.utils.debug
from cmk.utils.notify import (
    find_wato_folder,
    notification_message,
    notification_result_message,
)
from cmk.utils.regex import regex
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException

import cmk_base.utils
import cmk_base.config as config
import cmk_base.console as console
import cmk_base.core
import cmk_base.events as events

try:
    import cmk_base.cee.keepalive as keepalive
except ImportError:
    keepalive = None  # type: ignore

_log_to_stdout = False
notify_mode = "notify"

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
notification_logdir = cmk.utils.paths.var_dir + "/notify"
notification_spooldir = cmk.utils.paths.var_dir + "/notify/spool"
notification_bulkdir = cmk.utils.paths.var_dir + "/notify/bulk"
notification_core_log = cmk.utils.paths.var_dir + "/notify/nagios.log"  # Fallback for history if no CMC running
notification_log = cmk.utils.paths.log_dir + "/notify.log"

notification_log_template = \
    u"$CONTACTNAME$ - $NOTIFICATIONTYPE$ - " \
    u"$HOSTNAME$ $HOSTSTATE$ - " \
    u"$SERVICEDESC$ $SERVICESTATE$ "

notification_host_subject = u"Check_MK: $HOSTNAME$ - $NOTIFICATIONTYPE$"
notification_service_subject = u"Check_MK: $HOSTNAME$/$SERVICEDESC$ $NOTIFICATIONTYPE$"

notification_common_body = u"""Host:     $HOSTNAME$
Alias:    $HOSTALIAS$
Address:  $HOSTADDRESS$
"""

notification_host_body = u"""State:    $LASTHOSTSTATE$ -> $HOSTSTATE$ ($NOTIFICATIONTYPE$)
Command:  $HOSTCHECKCOMMAND$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
"""

notification_service_body = u"""Service:  $SERVICEDESC$
State:    $LASTSERVICESTATE$ -> $SERVICESTATE$ ($NOTIFICATIONTYPE$)
Command:  $SERVICECHECKCOMMAND$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
"""

#.
#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def _transform_user_disable_notifications_opts(contact):
    if "disable_notifications" in contact and isinstance(contact["disable_notifications"], bool):
        return {"disable": contact["disable_notifications"]}
    return contact.get("disable_notifications", {})


#.
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


def notify_usage():
    console.error("""Usage: check_mk --notify [--keepalive]
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
    send-bulks              Send out ripe bulk notifications
""")


# Main function called by cmk --notify. It either starts the
# keepalive mode (used by CMC), sends out one notifications from
# several possible sources or sends out all ripe bulk notifications.
def do_notify(options, args):
    global _log_to_stdout, notify_mode
    _log_to_stdout = options.get("log-to-stdout", _log_to_stdout)

    if keepalive and "keepalive" in options:
        keepalive.enable()

    convert_legacy_configuration()

    try:
        if not os.path.exists(notification_logdir):
            os.makedirs(notification_logdir)
        if not os.path.exists(notification_spooldir):
            os.makedirs(notification_spooldir)

        notify_mode = 'notify'
        if args:
            notify_mode = args[0]
            if notify_mode not in ['stdin', 'spoolfile', 'replay', 'send-bulks']:
                console.error("ERROR: Invalid call to check_mk --notify.\n\n")
                notify_usage()
                sys.exit(1)

            if len(args) != 2 and notify_mode not in ["stdin", "replay", "send-bulks"]:
                console.error("ERROR: need an argument to --notify %s.\n\n" % notify_mode)
                sys.exit(1)

            elif notify_mode == 'spoolfile':
                filename = args[1]

            elif notify_mode == 'replay':
                try:
                    replay_nr = int(args[1])
                except:
                    replay_nr = 0

        # If the notify_mode is set to 'spoolfile' we try to parse the given spoolfile
        # This spoolfile contains a python dictionary
        # { context: { Dictionary of environment variables }, plugin: "Plugin name" }
        # Any problems while reading the spoolfile results in returning 2
        # -> mknotifyd deletes this file
        if notify_mode == "spoolfile":
            return handle_spoolfile(filename)

        elif keepalive and keepalive.enabled():
            notify_keepalive()

        elif notify_mode == 'replay':
            raw_context = raw_context_from_backlog(replay_nr)
            notify_notify(raw_context)

        elif notify_mode == 'stdin':
            notify_notify(events.raw_context_from_stdin())

        elif notify_mode == "send-bulks":
            send_ripe_bulks()

        else:
            notify_notify(raw_context_from_env())

    except Exception:
        crash_dir = cmk.utils.paths.var_dir + "/notify"
        if not os.path.exists(crash_dir):
            os.makedirs(crash_dir)
        file(crash_dir + "/crash.log", "a").write(
            "CRASH (%s):\n%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), format_exception()))


def convert_legacy_configuration():
    # Convert legacy spooling configuration to new one (see above)
    if config.notification_spooling in (True, False):
        if config.notification_spool_to:
            also_local = config.notification_spool_to[2]
            if also_local:
                config.notification_spooling = "both"
            else:
                config.notification_spooling = "remote"
        elif config.notification_spooling:
            config.notification_spooling = "local"
        else:
            config.notification_spooling = "remote"

    # The former values 1 and 2 are mapped to the values 20 (default) and 10 (debug)
    # which agree with the values used in cmk/utils/log.py.
    # The decprecated value 0 is transformed to the default logging value.
    if config.notification_logging in [0, 1]:
        config.notification_logging = 20
    elif config.notification_logging == 2:
        config.notification_logging = 10


# This function processes one raw notification and decides wether it
# should be spooled or not. In the latter cased a local delivery
# is being done.
def notify_notify(raw_context, analyse=False):
    if not analyse:
        store_notification_backlog(raw_context)

    notify_log("----------------------------------------------------------------------")
    if analyse:
        notify_log("Analysing notification (%s) context with %s variables" %
                   (events.find_host_service_in_context(raw_context), len(raw_context)))
    else:
        notify_log("Got raw notification (%s) context with %s variables" %
                   (events.find_host_service_in_context(raw_context), len(raw_context)))

    # Add some further variable for the conveniance of the plugins

    notify_log_debug(events.render_context_dump(raw_context))

    raw_context["LOGDIR"] = notification_logdir
    events.complete_raw_context(raw_context,
                                with_dump=config.notification_logging <= 10,
                                log_func=notify_log)

    # Spool notification to remote host, if this is enabled
    if config.notification_spooling in ("remote", "both"):
        create_spoolfile({"context": raw_context, "forward": True})

    if config.notification_spooling != "remote":
        return locally_deliver_raw_context(raw_context, analyse=analyse)


# Here we decide which notification implementation we are using.
# Hopefully we can drop a couple of them some day
# 1. Rule Based Notifiations  (since 1.2.5i1)
# 2. Flexible Notifications   (since 1.2.2)
# 3. Plain email notification (refer to git log if you are really interested)
def locally_deliver_raw_context(raw_context, analyse=False):
    contactname = raw_context.get("CONTACTNAME")
    try:

        # If rule based notifications are enabled then the Micro Core does not set the
        # variable CONTACTNAME. In the other cores the CONTACTNAME is being set to
        # check-mk-notify.
        # We do we not simply check the config variable enable_rulebased_notifications?
        # -> Because the core needs are restart in order to reflect this while the
        #    notification mode of Check_MK not. There are thus situations where the
        #    setting of the core is different from our global variable. The core must
        #    have precedence in this situation!
        if not contactname or contactname == "check-mk-notify":
            # 1. RULE BASE NOTIFICATIONS
            notify_log_debug("Preparing rule based notifications")
            return notify_rulebased(raw_context, analyse=analyse)

        if analyse:
            return  # Analysis only possible when rule based notifications are enabled

        # Now fetch all configuration about that contact (it needs to be configure via
        # Check_MK for that purpose). If we do not know that contact then we cannot use
        # flexible notifications even if they are enabled.
        contact = config.contacts.get(contactname)

        disable_notifications_opts = _transform_user_disable_notifications_opts(contact)
        if disable_notifications_opts.get("disable", False):
            start, end = disable_notifications_opts.get("timerange", (None, None))
            if start is None or end is None:
                notify_log("Notifications for %s are disabled in personal settings. Skipping." %
                           contactname)
                return
            elif start <= time.time() <= end:
                notify_log(
                    "Notifications for %s are disabled in personal settings from %s to %s. Skipping."
                    % (contactname, start, end))
                return

        # Get notification settings for the contact in question - if available.
        if contact:
            method = contact.get("notification_method", "email")
        else:
            method = "email"

        if isinstance(method, tuple) and method[0] == 'flexible':
            # 2. FLEXIBLE NOTIFICATIONS
            notify_log("Preparing flexible notifications for %s" % contactname)
            notify_flexible(raw_context, method[1])

        else:
            # 3. PLAIN EMAIL NOTIFICATION
            notify_log("Preparing plain email notifications for %s" % contactname)
            notify_plain_email(raw_context)

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        notify_log("ERROR: %s\n%s" % (e, format_exception()))


def notification_replay_backlog(nr):
    global notify_mode
    notify_mode = "replay"
    raw_context = raw_context_from_backlog(nr)
    notify_notify(raw_context)


def notification_analyse_backlog(nr):
    global notify_mode
    notify_mode = "replay"
    raw_context = raw_context_from_backlog(nr)
    return notify_notify(raw_context, analyse=True)


#.
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
def notify_keepalive():
    cmk_base.utils.register_sigint_handler()
    events.event_keepalive(
        event_function=notify_notify,
        log_function=notify_log,
        call_every_loop=send_ripe_bulks,
        loop_interval=config.notification_bulk_interval,
    )


#.
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


def notify_rulebased(raw_context, analyse=False):
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

    notifications = {}
    num_rule_matches = 0
    rule_info = []

    for rule in config.notification_rules + user_notification_rules():
        if "contact" in rule:
            contact_info = "User %s's rule '%s'..." % (rule["contact"], rule["description"])
        else:
            contact_info = "Global rule '%s'..." % rule["description"]

        why_not = rbn_match_rule(rule, raw_context)  # also checks disabling
        if why_not:
            notify_log_verbose(contact_info)
            notify_log_verbose(" -> does not match: %s" % why_not)
            rule_info.append(("miss", rule, why_not))
        else:
            notify_log(contact_info)
            notify_log(" -> matches!")
            num_rule_matches += 1
            contacts = rbn_rule_contacts(rule, raw_context)
            contactstxt = ", ".join(contacts)

            # Handle old-style and new-style rules
            if "notify_method" in rule:  # old-style
                plugin = rule["notify_plugin"]
                plugin_parameters = rule[
                    "notify_method"]  # None: do cancel, [ str ]: plugin parameters
            else:
                plugin, plugin_parameters = rule["notify_plugin"]
            plugintxt = plugin or "plain email"

            key = contacts, plugin
            if plugin_parameters is None:  # cancelling
                # FIXME: In Python 2, notifications.keys() already produces a
                # copy of the keys, while in Python 3 it is only a view of the
                # underlying dict (modifications would result in an exception).
                # To be explicit and future-proof, we make this hack explicit.
                # Anyway, this is extremely ugly and an anti-patter, and it
                # should be rewritten to something more sane.
                for notify_key in list(notifications.keys()):
                    notify_contacts, notify_plugin = notify_key

                    overlap = notify_contacts.intersection(contacts)
                    if plugin != notify_plugin or not overlap:
                        continue

                    locked, plugin_parameters, bulk = notifications[notify_key]

                    if locked and "contact" in rule:
                        notify_log("   - cannot cancel notification of %s via %s: it is locked" %
                                   (contactstxt, plugintxt))
                        continue

                    notify_log("   - cancelling notification of %s via %s" %
                               (", ".join(overlap), plugintxt))

                    remaining = notify_contacts.difference(contacts)
                    if not remaining:
                        del notifications[notify_key]
                    else:
                        new_key = remaining, plugin
                        notifications[new_key] = notifications.pop(notify_key)
            elif contacts:
                if key in notifications:
                    locked = notifications[key][0]
                    if locked and "contact" in rule:
                        notify_log("   - cannot modify notification of %s via %s: it is locked" %
                                   (contactstxt, plugintxt))
                        continue
                    notify_log("   - modifying notification of %s via %s" %
                               (contactstxt, plugintxt))
                else:
                    notify_log("   - adding notification of %s via %s" % (contactstxt, plugintxt))
                bulk = rbn_get_bulk_params(rule)
                final_parameters = rbn_finalize_plugin_parameters(raw_context["HOSTNAME"], plugin,
                                                                  plugin_parameters)
                notifications[key] = (not rule.get("allow_disable"), final_parameters, bulk)

            rule_info.append(("match", rule, ""))

    plugin_info = []

    if not notifications:
        if num_rule_matches:
            notify_log("%d rules matched, but no notification has been created." % num_rule_matches)
        elif not analyse:
            fallback_contacts = rbn_fallback_contacts()
            if fallback_contacts:
                notify_log("No rule matched, notifying fallback contacts")
                fallback_emails = [fc["email"] for fc in fallback_contacts]
                notify_log("  Sending plain email to %s" % fallback_emails)

                plugin_context = create_plugin_context(raw_context, [])
                rbn_add_contact_information(plugin_context, fallback_contacts)
                notify_via_email(plugin_context)
            else:
                notify_log("No rule matched, would notify fallback contacts, but none configured")
    else:
        # Now do the actual notifications
        notify_log("Executing %d notifications:" % len(notifications))
        entries = notifications.items()
        entries.sort()
        for (contacts, plugin), (locked, params, bulk) in entries:
            verb = "would notify" if analyse else "notifying"
            contactstxt = ", ".join(contacts)
            plugintxt = plugin or "plain email"
            paramtxt = ", ".join(params) if params else "(no parameters)"
            bulktxt = "yes" if bulk else "no"
            notify_log("  * %s %s via %s, parameters: %s, bulk: %s" %
                       (verb, contactstxt, plugintxt, paramtxt, bulktxt))

            try:
                plugin_context = create_plugin_context(raw_context, params)
                rbn_add_contact_information(plugin_context, contacts)

                split_contexts = (
                    plugin not in ["", "mail", "asciimail", "slack"] or
                    # params can be a list (e.g. for custom notificatios)
                    params.get("disable_multiplexing") or bulk)
                if not split_contexts:
                    plugin_contexts = [plugin_context]
                else:
                    plugin_contexts = rbn_split_plugin_context(plugin_context)

                for context in plugin_contexts:
                    plugin_info.append((context["CONTACTNAME"], plugin, params, bulk))

                    if analyse:
                        continue
                    elif bulk:
                        do_bulk_notify(plugin, params, context, bulk)
                    elif config.notification_spooling in ("local", "both"):
                        create_spoolfile({"context": context, "plugin": plugin})
                    else:
                        call_notification_script(plugin, context)

            except Exception as e:
                if cmk.utils.debug.enabled():
                    raise
                fe = format_exception()
                notify_log("    ERROR: %s" % e)
                notify_log(fe)

    analysis_info = rule_info, plugin_info
    return analysis_info


def rbn_fallback_contacts():
    fallback_contacts = []
    if config.notification_fallback_email:
        fallback_contacts.append(rbn_fake_email_contact(config.notification_fallback_email))

    for contact_name, contact in config.contacts.items():
        if contact.get("fallback_contact", False) and contact.get("email"):
            fallback_contact = {
                "name": contact_name,
            }
            fallback_contact.update(contact)
            fallback_contacts.append(fallback_contact)

    return fallback_contacts


def rbn_finalize_plugin_parameters(hostname, plugin, rule_parameters):
    # Right now we are only able to finalize notification plugins with dict parameters..
    if isinstance(rule_parameters, dict):
        host_config = config.get_config_cache().get_host_config(hostname)
        parameters = host_config.notification_plugin_parameters(plugin).copy()
        parameters.update(rule_parameters)
        return parameters

    return rule_parameters


# Create a table of all user specific notification rules. Important:
# create deterministic order, so that rule analyses can depend on
# rule indices
def user_notification_rules():
    user_rules = []
    contactnames = config.contacts.keys()
    contactnames.sort()
    for contactname in contactnames:
        contact = config.contacts[contactname]
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

            if "authorized_sites" in config.contacts[contactname] and not "match_site" in rule:
                rule["match_site"] = config.contacts[contactname]["authorized_sites"]

    notify_log_debug("Found %d user specific rules" % len(user_rules))
    return user_rules


def rbn_fake_email_contact(email):
    return {
        "name": "mailto:" + email,
        "alias": "Explicit email adress " + email,
        "email": email,
        "pager": "",
    }


def rbn_add_contact_information(plugin_context, contacts):
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
                "pager": ""
            }
        else:
            contact_dict = config.contacts.get(contact, {"alias": contact})
            contact_dict["name"] = contact

        contact_dicts.append(contact_dict)
        keys.update([key for key in contact_dict.keys() if key.startswith("_")])

    for key in keys:
        context_key = "CONTACT" + key.upper()
        items = [contact.get(key, "") for contact in contact_dicts]
        plugin_context[context_key] = ",".join(items)


def rbn_split_plugin_context(plugin_context):
    """Takes a plugin_context containing multiple contacts and returns
    a list of plugin_contexts with a context for each contact"""
    num_contacts = len(plugin_context["CONTACTNAME"].split(","))
    if num_contacts <= 1:
        return [plugin_context]

    contexts = []
    keys_to_split = {"CONTACTNAME", "CONTACTALIAS", "CONTACTEMAIL", "CONTACTPAGER"}
    keys_to_split.update([key for key in plugin_context.keys() if key.startswith("CONTACT_")])

    for i in range(num_contacts):
        context = plugin_context.copy()
        for key in keys_to_split:
            context[key] = context[key].split(",")[i]
        contexts.append(context)

    return contexts


def rbn_get_bulk_params(rule):
    bulk = rule.get("bulk")

    if not bulk:
        return None
    elif isinstance(bulk, dict):  # old format: treat as "Always Bulk"
        method, params = "always", bulk
    else:
        method, params = bulk

    if method == "always":
        return params

    elif method == "timeperiod":
        try:
            active = cmk_base.core.timeperiod_active(params["timeperiod"])
        except:
            if cmk.utils.debug.enabled():
                raise
            # If a livestatus connection error appears we will bulk the
            # notification in the first place. When the connection is available
            # again and the period is not active the notifications will be sent.
            notify_log("   - Error checking activity of timeperiod %s: assuming active" %
                       params["timeperiod"])
            active = True

        if active:
            return params
        return params.get("bulk_outside")

    notify_log("   - Unknown bulking method: assuming bulking is disabled")
    return None


def rbn_match_rule(rule, context):
    if rule.get("disabled"):
        return "This rule is disabled"

    return (events.event_match_rule(rule, context) or rbn_match_escalation(rule, context) or
            rbn_match_escalation_throtte(rule, context) or rbn_match_host_event(rule, context) or
            rbn_match_service_event(rule, context) or
            rbn_match_notification_comment(rule, context) or rbn_match_event_console(rule, context))


def rbn_match_escalation(rule, context):
    if "match_escalation" in rule:
        from_number, to_number = rule["match_escalation"]
        if context["WHAT"] == "HOST":
            notification_number = int(context.get("HOSTNOTIFICATIONNUMBER", 1))
        else:
            notification_number = int(context.get("SERVICENOTIFICATIONNUMBER", 1))
        if not from_number <= notification_number <= to_number:
            return "The notification number %d does not lie in range %d ... %d" % (
                notification_number, from_number, to_number)


def rbn_match_escalation_throtte(rule, context):
    if "match_escalation_throttle" in rule:
        # We do not want to suppress recovery notifications.
        if (context["WHAT"] == "HOST" and context.get("HOSTSTATE", "UP") == "UP") or \
           (context["WHAT"] == "SERVICE" and context.get("SERVICESTATE", "OK") == "OK"):
            return
        from_number, rate = rule["match_escalation_throttle"]
        if context["WHAT"] == "HOST":
            notification_number = int(context.get("HOSTNOTIFICATIONNUMBER", 1))
        else:
            notification_number = int(context.get("SERVICENOTIFICATIONNUMBER", 1))
        if notification_number <= from_number:
            return
        if (notification_number - from_number) % rate != 0:
            return "This notification is being skipped due to throttling. The next number will be %d" % \
                (notification_number + rate - ((notification_number - from_number) % rate))


def rbn_match_host_event(rule, context):
    if "match_host_event" in rule:
        if context["WHAT"] != "HOST":
            if "match_service_event" not in rule:
                return "This is a service notification, but the rule just matches host events"
            return  # Let this be handled by match_service_event

        allowed_events = rule["match_host_event"]
        state = context["HOSTSTATE"]
        last_state = context["PREVIOUSHOSTHARDSTATE"]
        event_map = {"UP": 'r', "DOWN": 'd', "UNREACHABLE": 'u'}
        return rbn_match_event(context, state, last_state, event_map, allowed_events)


def rbn_match_service_event(rule, context):
    if "match_service_event" in rule:
        if context["WHAT"] != "SERVICE":
            if "match_host_event" not in rule:
                return "This is a host notification, but the rule just matches service events"
            return  # Let this be handled by match_host_event

        allowed_events = rule["match_service_event"]
        state = context["SERVICESTATE"]
        last_state = context["PREVIOUSSERVICEHARDSTATE"]
        event_map = {"OK": 'r', "WARNING": 'w', "CRITICAL": 'c', "UNKNOWN": 'u'}
        return rbn_match_event(context, state, last_state, event_map, allowed_events)


def rbn_match_event(context, state, last_state, event_map, allowed_events):
    notification_type = context["NOTIFICATIONTYPE"]

    if notification_type == "RECOVERY":
        event = event_map.get(last_state, '?') + 'r'
    elif notification_type in ["FLAPPINGSTART", "FLAPPINGSTOP", "FLAPPINGDISABLED"]:
        event = 'f'
    elif notification_type in ["DOWNTIMESTART", "DOWNTIMEEND", "DOWNTIMECANCELLED"]:
        event = 's'
    elif notification_type == "ACKNOWLEDGEMENT":
        event = 'x'
    elif notification_type.startswith("ALERTHANDLER ("):
        handler_state = notification_type[14:-1]
        if handler_state == "OK":
            event = 'as'
        else:
            event = 'af'
    else:
        event = event_map.get(last_state, '?') + event_map.get(state, '?')

    # Now go through the allowed events. Handle '?' has matching all types!
    for allowed in allowed_events:
        if event == allowed or \
           (allowed[0] == '?' and len(event) > 1 and event[1] == allowed[1]) or \
           (event[0] == '?' and len(allowed) > 1 and event[1] == allowed[1]):
            return

    return "Event type '%s' not handled by this rule. Allowed are: %s" % (event,
                                                                          ", ".join(allowed_events))


def rbn_rule_contacts(rule, context):
    the_contacts = set([])
    if rule.get("contact_object"):
        the_contacts.update(rbn_object_contact_names(context))
    if rule.get("contact_all"):
        the_contacts.update(rbn_all_contacts())
    if rule.get("contact_all_with_email"):
        the_contacts.update(rbn_all_contacts(with_email=True))
    if "contact_users" in rule:
        the_contacts.update(rule["contact_users"])
    if "contact_groups" in rule:
        the_contacts.update(rbn_groups_contacts(rule["contact_groups"]))
    if "contact_emails" in rule:
        the_contacts.update(rbn_emails_contacts(rule["contact_emails"]))

    all_enabled = []
    for contactname in the_contacts:
        if contactname == config.notification_fallback_email:
            contact = rbn_fake_email_contact(config.notification_fallback_email)
        else:
            contact = config.contacts.get(contactname)

        if contact:
            disable_notifications_opts = _transform_user_disable_notifications_opts(contact)
            if disable_notifications_opts.get("disable", False):
                start, end = disable_notifications_opts.get("timerange", (None, None))
                if start is None or end is None:
                    notify_log("   - skipping contact %s: he/she has disabled notifications" %
                               contactname)
                    continue
                elif start <= time.time() <= end:
                    notify_log(
                        "   - skipping contact %s: he/she has disabled notifications from %s to %s."
                        % (contactname, start, end))
                    continue

            reason = (rbn_match_contact_macros(rule, contactname, contact) or
                      rbn_match_contact_groups(rule, contactname, contact))

            if reason:
                notify_log("   - skipping contact %s: %s" % (contactname, reason))
                continue

        else:
            notify_log("Warning: cannot get information about contact %s: ignoring restrictions" %
                       contactname)

        all_enabled.append(contactname)

    return frozenset(all_enabled)  # has to be hashable


def rbn_match_contact_macros(rule, contactname, contact):
    if "contact_match_macros" in rule:
        for macro_name, regexp in rule["contact_match_macros"]:
            value = contact.get("_" + macro_name, "")
            if not regexp.endswith("$"):
                regexp = regexp + "$"
            if not regex(regexp).match(value):
                macro_overview = ", ".join([
                    "%s=%s" % (varname[1:], val)
                    for (varname, val) in contact.items()
                    if varname.startswith("_")
                ])
                return "value '%s' for macro '%s' does not match '%s'. His macros are: %s" % (
                    value, macro_name, regexp, macro_overview)


def rbn_match_contact_groups(rule, contactname, contact):
    if "contact_match_groups" in rule:
        if "contactgroups" not in contact:
            notify_log("Warning: cannot determine contact groups of %s: skipping restrictions" %
                       contactname)
            return
        for required_group in rule["contact_match_groups"]:
            if required_group not in contact["contactgroups"]:
                return "he/she is not member of the contact group %s (his groups are %s)" % (
                    required_group, ", ".join(contact["contactgroups"] or ["<None>"]))


def rbn_match_notification_comment(rule, context):
    if "match_notification_comment" in rule:
        r = regex(rule["match_notification_comment"])
        notification_comment = context.get("NOTIFICATIONCOMMENT", "")
        if not r.match(notification_comment):
            return "The beginning of the notification comment '%s' is not matched by the regex '%s'" % (
                notification_comment, rule["match_notification_comment"])


def rbn_match_event_console(rule, context):
    if "match_ec" in rule:
        match_ec = rule["match_ec"]
        is_ec_notification = "EC_ID" in context
        if match_ec is False and is_ec_notification:
            return "Notification has been created by the Event Console."
        elif match_ec is not False and not is_ec_notification:
            return "Notification has not been created by the Event Console."

        if match_ec is not False:

            # Match Event Console rule ID
            if "match_rule_id" in match_ec and context["EC_RULE_ID"] not in match_ec[
                    "match_rule_id"]:
                return "EC Event has rule ID '%s', but '%s' is required" % (
                    context["EC_RULE_ID"], match_ec["match_rule_id"])

            # Match syslog priority of event
            if "match_priority" in match_ec:
                prio_from, prio_to = match_ec["match_priority"]
                if prio_from > prio_to:
                    prio_to, prio_from = prio_from, prio_to
                    p = int(context["EC_PRIORITY"])
                    if p < prio_from or p > prio_to:
                        return "Event has priority %s, but matched range is %s .. %s" % (
                            p, prio_from, prio_to)

            # Match syslog facility of event
            if "match_facility" in match_ec:
                if match_ec["match_facility"] != int(context["EC_FACILITY"]):
                    return "Wrong syslog facility %s, required is %s" % (context["EC_FACILITY"],
                                                                         match_ec["match_facility"])

            # Match event comment
            if "match_comment" in match_ec:
                r = regex(match_ec["match_comment"])
                if not r.search(context["EC_COMMENT"]):
                    return "The event comment '%s' does not match the regular expression '%s'" % (
                        context["EC_COMMENT"], match_ec["match_comment"])


def rbn_object_contact_names(context):
    commasepped = context.get("CONTACTS")
    if commasepped == "?":
        notify_log("Warning: Contacts of %s cannot be determined. Using fallback contacts" %
                   events.find_host_service_in_context(context))
        return [contact["name"] for contact in rbn_fallback_contacts()]
    elif commasepped:
        return commasepped.split(",")

    return []


def rbn_all_contacts(with_email=None):
    if not with_email:
        return config.contacts.keys()  # We have that via our main.mk contact definitions!

    return [contact_id for (contact_id, contact) in config.contacts.items() if contact.get("email")]


def rbn_groups_contacts(groups):
    if not groups:
        return {}
    query = "GET contactgroups\nColumns: members\n"
    for group in groups:
        query += "Filter: name = %s\n" % group
    query += "Or: %d\n" % len(groups)

    try:
        contacts = set([])
        for contact_list in livestatus.LocalConnection().query_column(query):
            contacts.update(contact_list)
        return contacts

    except livestatus.MKLivestatusNotFoundError:
        return []

    except Exception:
        if cmk.utils.debug.enabled():
            raise
        return []


def rbn_emails_contacts(emails):
    return ["mailto:" + e for e in emails]


#.
#   .--Flexible-Notifications----------------------------------------------.
#   |                  _____ _           _ _     _                         |
#   |                 |  ___| | _____  _(_) |__ | | ___                    |
#   |                 | |_  | |/ _ \ \/ / | '_ \| |/ _ \                   |
#   |                 |  _| | |  __/>  <| | |_) | |  __/                   |
#   |                 |_|   |_|\___/_/\_\_|_.__/|_|\___|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Implementation of the pre 1.2.5, hopelessly outdated flexible       |
#   |  notifications.                                                      |
#   '----------------------------------------------------------------------'


def notify_flexible(raw_context, notification_table):

    for entry in notification_table:
        plugin = entry["plugin"]
        notify_log(" Notification channel with plugin %s" % (plugin or "plain email"))

        if not should_notify(raw_context, entry):
            continue

        plugin_context = create_plugin_context(raw_context, entry.get("parameters", []))

        if config.notification_spooling in ("local", "both"):
            create_spoolfile({"context": plugin_context, "plugin": plugin})
        else:
            call_notification_script(plugin, plugin_context)


# may return
# 0  : everything fine   -> proceed
# 1  : currently not OK  -> try to process later on
# >=2: invalid           -> discard
def should_notify(context, entry):
    # Check disabling
    if entry.get("disabled"):
        notify_log(" - Skipping: it is disabled for this user")
        return False

    # Check host, if configured
    if entry.get("only_hosts"):
        hostname = context.get("HOSTNAME")

        skip = True
        regex_match = False
        negate = False
        for h in entry["only_hosts"]:
            if h.startswith("!"):  # negate
                negate = True
                h = h[1:]
            elif h.startswith('~'):
                regex_match = True
                h = h[1:]

            if not regex_match and hostname == h:
                skip = negate
                break

            elif regex_match and re.match(h, hostname):
                skip = negate
                break
        if skip:
            notify_log(" - Skipping: host '%s' matches none of %s" %
                       (hostname, ", ".join(entry["only_hosts"])))
            return False

    # Check if the host has to be in a special service_level
    if "match_sl" in entry:
        from_sl, to_sl = entry['match_sl']
        if context['WHAT'] == "SERVICE" and context.get('SVC_SL', '').isdigit():
            sl = events.saveint(context.get('SVC_SL'))
        else:
            sl = events.saveint(context.get('HOST_SL'))

        if sl < from_sl or sl > to_sl:
            notify_log(" - Skipping: service level %d not between %d and %d" % (sl, from_sl, to_sl))
            return False

    # Skip blacklistet serivces
    if entry.get("service_blacklist"):
        servicedesc = context.get("SERVICEDESC")
        if not servicedesc:
            notify_log(" - Proceed: blacklist certain services, but this is a host notification")
        else:
            for s in entry["service_blacklist"]:
                if re.match(s, servicedesc):
                    notify_log(" - Skipping: service '%s' matches blacklist (%s)" %
                               (servicedesc, ", ".join(entry["service_blacklist"])))
                    return False

    # Check service, if configured
    if entry.get("only_services"):
        servicedesc = context.get("SERVICEDESC")
        if not servicedesc:
            notify_log(" - Proceed: limited to certain services, but this is a host notification")
        else:
            # Example
            # only_services = [ "!LOG foo", "LOG", BAR" ]
            # -> notify all services beginning with LOG or BAR, but not "LOG foo..."
            skip = True
            for s in entry["only_services"]:
                if s.startswith("!"):  # negate
                    negate = True
                    s = s[1:]
                else:
                    negate = False
                if re.match(s, servicedesc):
                    skip = negate
                    break
            if skip:
                notify_log(" - Skipping: service '%s' matches none of %s" %
                           (servicedesc, ", ".join(entry["only_services"])))
                return False

    # Check notification type
    event, allowed_events = check_notification_type(context, entry["host_events"],
                                                    entry["service_events"])
    if event not in allowed_events:
        notify_log(" - Skipping: wrong notification type %s (%s), only %s are allowed" %
                   (event, context["NOTIFICATIONTYPE"], ",".join(allowed_events)))
        return False

    # Check notification number (in case of repeated notifications/escalations)
    if "escalation" in entry:
        from_number, to_number = entry["escalation"]
        if context["WHAT"] == "HOST":
            notification_number = int(context.get("HOSTNOTIFICATIONNUMBER", 1))
        else:
            notification_number = int(context.get("SERVICENOTIFICATIONNUMBER", 1))
        if notification_number < from_number or notification_number > to_number:
            notify_log(" - Skipping: notification number %d does not lie in range %d ... %d" %
                       (notification_number, from_number, to_number))
            return False

    if "timeperiod" in entry:
        timeperiod = entry["timeperiod"]
        if timeperiod and timeperiod != "24X7":
            if not cmk_base.core.check_timeperiod(timeperiod):
                notify_log(" - Skipping: time period %s is currently not active" % timeperiod)
                return False
    return True


def check_notification_type(context, host_events, service_events):
    notification_type = context["NOTIFICATIONTYPE"]
    if context["WHAT"] == "HOST":
        allowed_events = host_events
        state = context["HOSTSTATE"]
        event_map = {"UP": 'r', "DOWN": 'd', "UNREACHABLE": 'u'}
    else:
        allowed_events = service_events
        state = context["SERVICESTATE"]
        event_map = {"OK": 'r', "WARNING": 'w', "CRITICAL": 'c', "UNKNOWN": 'u'}

    if notification_type == "RECOVERY":
        event = 'r'
    elif notification_type in ["FLAPPINGSTART", "FLAPPINGSTOP", "FLAPPINGDISABLED"]:
        event = 'f'
    elif notification_type in ["DOWNTIMESTART", "DOWNTIMEEND", "DOWNTIMECANCELLED"]:
        event = 's'
    elif notification_type == "ACKNOWLEDGEMENT":
        event = 'x'
    else:
        event = event_map.get(state, '?')

    return event, allowed_events


#.
#   .--Plain Email---------------------------------------------------------.
#   |          ____  _       _         _____                 _ _           |
#   |         |  _ \| | __ _(_)_ __   | ____|_ __ ___   __ _(_) |          |
#   |         | |_) | |/ _` | | '_ \  |  _| | '_ ` _ \ / _` | | |          |
#   |         |  __/| | (_| | | | | | | |___| | | | | | (_| | | |          |
#   |         |_|   |_|\__,_|_|_| |_| |_____|_| |_| |_|\__,_|_|_|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Plain Email notification, inline implemented. This is also being    |
#   |  used as a pseudo-plugin by Flexible Notification and RBN.           |
#   '----------------------------------------------------------------------'


def notify_plain_email(raw_context):
    plugin_context = create_plugin_context(raw_context, [])

    if config.notification_spooling in ("local", "both"):
        create_spoolfile({"context": plugin_context, "plugin": None})
    else:
        notify_log("Sending plain email to %s" % plugin_context["CONTACTNAME"])
        notify_via_email(plugin_context)


def notify_via_email(plugin_context):
    notify_log(substitute_context(notification_log_template, plugin_context))

    if plugin_context["WHAT"] == "SERVICE":
        subject_t = notification_service_subject
        body_t = notification_service_body
    else:
        subject_t = notification_host_subject
        body_t = notification_host_body

    subject = substitute_context(subject_t, plugin_context)
    plugin_context["SUBJECT"] = subject
    body = substitute_context(notification_common_body + body_t, plugin_context)
    command = [cmk.utils.paths.bin_dir + "/mail", "-s", subject, plugin_context["CONTACTEMAIL"]]

    # Make sure that mail(x) is using UTF-8. Otherwise we cannot send notifications
    # with non-ASCII characters. Unfortunately we do not know whether C.UTF-8 is
    # available. If e.g. mail detects a non-Ascii character in the mail body and
    # the specified encoding is not available, it will silently not send the mail!
    # Our resultion in future: use /usr/sbin/sendmail directly.
    # Our resultion in the present: look with locale -a for an existing UTF encoding
    # and use that.
    old_lang = os.getenv("LANG", "")
    for encoding in os.popen("locale -a 2>/dev/null"):
        l = encoding.lower()
        if "utf8" in l or "utf-8" in l or "utf.8" in l:
            encoding = encoding.strip()
            os.putenv("LANG", encoding)
            notify_log_debug("Setting locale for mail to %s." % encoding)
            break
    else:
        notify_log("No UTF-8 encoding found in your locale -a! Please provide C.UTF-8 encoding.")

    # Important: we must not output anything on stdout or stderr. Data of stdout
    # goes back into the socket to the CMC in keepalive mode and garbles the
    # handshake signal.
    notify_log_debug("Executing command: %s" % " ".join(command))

    p = subprocess.Popen(command,
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         close_fds=True)
    stdout_txt, stderr_txt = p.communicate(body.encode("utf-8"))
    exitcode = p.returncode
    os.putenv("LANG", old_lang)  # Important: do not destroy our environment
    if exitcode != 0:
        notify_log("ERROR: could not deliver mail. Exit code of command is %r" % exitcode)
        for line in (stdout_txt + stderr_txt).decode('utf-8').splitlines():
            notify_log("mail: %s" % line.rstrip())
        return 2

    return 0


#.
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


# Add the plugin parameters to the envinroment. We have two types of parameters:
# - list, the legacy style. This will lead to PARAMETERS_1, ...
# - dict, the new style for scripts with WATO rule. This will lead to
#         PARAMETER_FOO_BAR for a dict key named "foo_bar".
def create_plugin_context(raw_context, params):
    plugin_context = {}
    plugin_context.update(raw_context)  # Make a real copy
    events.add_to_event_context(plugin_context, "PARAMETER", params, log_function=notify_log)
    return plugin_context


def create_bulk_parameter_context(params):
    dict_context = create_plugin_context({}, params)
    return [
        "%s=%s\n" % (varname, value.replace("\r", "").replace("\n", "\1"))
        for (varname, value) in dict_context.items()
    ]


def path_to_notification_script(plugin):
    # Call actual script without any arguments
    if "/" in plugin:
        notify_log("Pluginname %r with slash. Raising exception...")
        raise MKGeneralException("Slashes in plugin_name are forbidden!")

    local_path = cmk.utils.paths.local_notifications_dir + "/" + plugin
    if os.path.exists(local_path):
        path = local_path
    else:
        path = cmk.utils.paths.notifications_dir + "/" + plugin

    if not os.path.exists(path):
        notify_log("Notification plugin '%s' not found" % plugin)
        notify_log("  not in %s" % cmk.utils.paths.notifications_dir)
        notify_log("  and not in %s" % cmk.utils.paths.local_notifications_dir)
        return None

    return path


# This is the function that finally sends the actual notification.
# It does this by calling an external script are creating a
# plain email and calling bin/mail.
#
# It also does the central logging of the notifications
# that are actually sent out.
#
# Note: this function is *not* being called for bulk notification.
def call_notification_script(plugin, plugin_context):
    _log_to_history(notification_message(plugin or "plain email", plugin_context))

    def plugin_log(s):
        notify_log("     %s" % s)

    # The "Pseudo"-Plugin None means builtin plain email
    if not plugin:
        return notify_via_email(plugin_context)

    # Call actual script without any arguments
    path = path_to_notification_script(plugin)
    if not path:
        return 2

    plugin_log("executing %s" % path)
    try:
        set_notification_timeout()
        p = subprocess.Popen([path],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             env=notification_script_env(plugin_context),
                             close_fds=True)

        while True:
            # read and output stdout linewise to ensure we don't force python to produce
            # one - potentially huge - memory buffer
            line = p.stdout.readline()
            if line != '':
                plugin_log("Output: %s" % line.decode('utf-8').rstrip())
                if _log_to_stdout:
                    console.output(line)
            else:
                break
        # the stdout is closed but the return code may not be available just yet - wait for the
        # process to actually finish
        exitcode = p.wait()
        clear_notification_timeout()
    except NotificationTimeout:
        plugin_log("Notification plugin did not finish within %d seconds. Terminating." %
                   config.notification_plugin_timeout)
        # p.kill() requires python 2.6!
        os.kill(p.pid, signal.SIGTERM)
        exitcode = 1

    if exitcode != 0:
        plugin_log("Plugin exited with code %d" % exitcode)

    return exitcode


# Construct the environment for the notification script
def notification_script_env(plugin_context):
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

    def format_(value):
        if len(value) > max_length:
            value = value[:max_length] + "...\nAttention: Removed remaining content because it was too long."
        return value.encode("utf-8")

    notify_env = os.environ.copy()
    notify_env.update(
        {"NOTIFY_" + variable: format_(value) for variable, value in plugin_context.iteritems()})

    return notify_env


class NotificationTimeout(Exception):
    pass


def handle_notification_timeout(signum, frame):
    raise NotificationTimeout()


def set_notification_timeout():
    signal.signal(signal.SIGALRM, handle_notification_timeout)
    signal.alarm(config.notification_plugin_timeout)


def clear_notification_timeout():
    signal.alarm(0)


#.
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


def create_spoolfile(data):
    if not os.path.exists(notification_spooldir):
        os.makedirs(notification_spooldir)
    file_path = "%s/%s" % (notification_spooldir, fresh_uuid())
    notify_log("Creating spoolfile: %s" % file_path)
    store.save_data_to_file(file_path, data, pretty=True)


# There are three types of spool files:
# 1. Notifications to be forwarded. Contain key "forward"
# 2. Notifications for async local delivery. Contain key "plugin"
# 3. Notifications that *were* forwarded (e.g. received from a slave). Contain neither of both.
# Spool files of type 1 are not handled here!
def handle_spoolfile(spoolfile):
    notif_uuid = spoolfile.rsplit("/", 1)[-1]
    notify_log("----------------------------------------------------------------------")
    try:
        data = store.load_data_from_file(spoolfile)
        if "plugin" in data:
            plugin_context = data["context"]
            plugin = data["plugin"]
            notify_log("Got spool file %s (%s) for local delivery via %s" %
                       (notif_uuid[:8], events.find_host_service_in_context(plugin_context),
                        (plugin or "plain mail")))
            return call_notification_script(plugin, plugin_context)

        # We received a forwarded raw notification. We need to process
        # this with our local notification rules in order to call one,
        # several or no actual plugins.
        raw_context = data["context"]
        notify_log("Got spool file %s (%s) from remote host for local delivery." %
                   (notif_uuid[:8], events.find_host_service_in_context(raw_context)))

        store_notification_backlog(data["context"])
        locally_deliver_raw_context(data["context"])
        return 0  # No error handling for async delivery

    except Exception as e:
        notify_log("ERROR %s\n%s" % (e, format_exception()))
        return 2


#.
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


def do_bulk_notify(plugin, params, plugin_context, bulk):
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

    if "/" in contact or "/" in plugin:
        notify_log("Tried to construct bulk dir with unsanitized attributes")
        raise MKGeneralException("Slashes in CONTACTNAME or plugin_name are forbidden!")

    if bulk.get("timeperiod"):
        bulk_path = (contact, plugin, 'timeperiod:' + bulk["timeperiod"], str(bulk["count"]))
    else:
        bulk_path = (contact, plugin, str(bulk["interval"]), str(bulk["count"]))
    bulkby = bulk["groupby"]

    if "bulk_subject" in bulk:
        plugin_context["PARAMETER_BULK_SUBJECT"] = bulk["bulk_subject"]

    if "host" in bulkby:
        bulk_path += ("host", plugin_context["HOSTNAME"])

    elif "folder" in bulkby:
        bulk_path += ("folder", find_wato_folder(plugin_context))

    if "service" in bulkby:
        bulk_path += ("service", plugin_context.get("SERVICEDESC", ""))

    if "sl" in bulkby:
        bulk_path += ("sl", plugin_context.get(what + "_SL", ""))

    if "check_type" in bulkby:
        bulk_path += ("check_type", plugin_context.get(what + "CHECKCOMMAND", "").split("!")[0])

    if "state" in bulkby:
        bulk_path += ("state", plugin_context.get(what + "STATE", ""))

    if "ec_contact" in bulkby:
        bulk_path += ("ec_contact", plugin_context.get("EC_CONTACT", ""))

    if "ec_comment" in bulkby:
        bulk_path += ("ec_comment", plugin_context.get("EC_COMMENT", ""))

    # User might have specified _FOO instead of FOO
    bulkby_custom = bulk.get("groupby_custom", [])
    for macroname in bulkby_custom:
        macroname = macroname.lstrip("_").upper()
        value = plugin_context.get(what + "_" + macroname, "")
        bulk_path += (macroname.lower(), value)

    notify_log("    --> storing for bulk notification %s" % "|".join(bulk_path))
    bulk_dirname = create_bulk_dirname(bulk_path)
    uuid = fresh_uuid()
    filename = bulk_dirname + "/" + uuid
    file(filename + ".new", "w").write("%r\n" % ((params, plugin_context),))
    os.rename(filename + ".new", filename)  # We need an atomic creation!
    notify_log("        - stored in %s" % filename)


def create_bulk_dirname(bulk_path):
    dirname = os.path.join(notification_bulkdir, bulk_path[0], bulk_path[1],
                           ",".join([b.replace("/", "\\") for b in bulk_path[2:]]))

    # Remove non-Ascii-characters by special %02x-syntax
    try:
        str(dirname)
    except:
        new_dirname = ""
        for char in dirname:
            if ord(char) <= 0 or ord(char) > 127:
                new_dirname += "%%%04x" % ord(char)
            else:
                new_dirname += char
        dirname = new_dirname

    if not os.path.exists(dirname):
        os.makedirs(dirname)
        notify_log("        - created bulk directory %s" % dirname)
    return dirname


def bulk_parts(method_dir, bulk):
    parts = bulk.split(',')

    try:
        interval, timeperiod = int(parts[0]), None
    except ValueError:
        entry = parts[0].split(':')
        if entry[0] == 'timeperiod' and len(entry) == 2:
            interval, timeperiod = None, entry[1]
        else:
            notify_log("Skipping invalid bulk directory %s" % method_dir)
            return None

    try:
        count = int(parts[1])
    except ValueError:
        notify_log("Skipping invalid bulk directory %s" % method_dir)
        return None

    return interval, timeperiod, count


def bulk_uuids(bulk_dir):
    uuids, oldest = [], time.time()
    for uuid in os.listdir(bulk_dir):  # 4ded0fa2-f0cd-4b6a-9812-54374a04069f
        if uuid.endswith(".new"):
            continue
        if len(uuid) != 36:
            notify_log("Skipping invalid notification file %s" % os.path.join(bulk_dir, uuid))
            continue

        mtime = os.stat(os.path.join(bulk_dir, uuid)).st_mtime
        uuids.append((mtime, uuid))
        oldest = min(oldest, mtime)
    uuids.sort()
    return uuids, oldest


def remove_if_orphaned(bulk_dir, max_age, ref_time=None):
    if not ref_time:
        ref_time = time.time()

    dirage = ref_time - os.stat(bulk_dir).st_mtime
    if dirage > max_age:
        notify_log("Warning: removing orphaned empty bulk directory %s" % bulk_dir)
        try:
            os.rmdir(bulk_dir)
        except Exception as e:
            notify_log("    -> Error removing it: %s" % e)


def find_bulks(only_ripe):
    if not os.path.exists(notification_bulkdir):
        return []

    def listdir_visible(path):
        return [x for x in os.listdir(path) if not x.startswith(".")]

    bulks, now = [], time.time()
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
                if not parts:
                    continue
                interval, timeperiod, count = parts

                if interval is not None:
                    if age >= interval:
                        notify_log("Bulk %s is ripe: age %d >= %d" % (bulk_dir, age, interval))
                    elif len(uuids) >= count:
                        notify_log("Bulk %s is ripe: count %d >= %d" %
                                   (bulk_dir, len(uuids), count))
                    else:
                        notify_log("Bulk %s is not ripe yet (age: %d, count: %d)!" %
                                   (bulk_dir, age, len(uuids)))
                        if only_ripe:
                            continue

                    bulks.append((bulk_dir, age, interval, 'n.a.', count, uuids))
                else:
                    try:
                        active = cmk_base.core.timeperiod_active(timeperiod)
                    except:
                        # This prevents sending bulk notifications if a
                        # livestatus connection error appears. It also implies
                        # that an ongoing connection error will hold back bulk
                        # notifications.
                        notify_log(
                            "Error while checking activity of timeperiod %s: assuming active" %
                            timeperiod)
                        active = True

                    if active is True and len(uuids) < count:
                        # Only add a log entry every 10 minutes since timeperiods
                        # can be very long (The default would be 10s).
                        if now % 600 <= config.notification_bulk_interval:
                            notify_log(
                                "Bulk %s is not ripe yet (timeperiod %s: active, count: %d)" %
                                (bulk_dir, timeperiod, len(uuids)))

                        if only_ripe:
                            continue
                    elif active is False:
                        notify_log("Bulk %s is ripe: timeperiod %s has ended" %
                                   (bulk_dir, timeperiod))
                    elif len(uuids) >= count:
                        notify_log("Bulk %s is ripe: count %d >= %d" %
                                   (bulk_dir, len(uuids), count))
                    else:
                        notify_log("Bulk %s is ripe: timeperiod %s is not known anymore" %
                                   (bulk_dir, timeperiod))

                    bulks.append((bulk_dir, age, 'n.a.', timeperiod, count, uuids))

    return bulks


def send_ripe_bulks():
    ripe = find_bulks(True)
    if ripe:
        notify_log("Sending out %d ripe bulk notifications" % len(ripe))
        for bulk in ripe:
            try:
                notify_bulk(bulk[0], bulk[-1])
            except Exception:
                if cmk.utils.debug.enabled():
                    raise
                notify_log("Error sending bulk %s: %s" % (bulk[0], format_exception()))


def notify_bulk(dirname, uuids):
    parts = dirname.split("/")
    contact = parts[-3]
    plugin = parts[-2]
    notify_log("   -> %s/%s %s" % (contact, plugin, dirname))
    # If new entries are created in this directory while we are working
    # on it, nothing bad happens. It's just that we cannot remove
    # the directory after our work. It will be the starting point for
    # the next bulk with the same ID, which is completely OK.
    bulk_context = []
    old_params = None
    unhandled_uuids = []
    for mtime, uuid in uuids:
        try:
            params, context = store.load_data_from_file(dirname + "/" + uuid)
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            notify_log("    Deleting corrupted or empty bulk file %s/%s: %s" % (dirname, uuid, e))
            continue

        if old_params is None:
            old_params = params
        elif params != old_params:
            notify_log("     Parameters are different from previous, postponing into separate bulk")
            unhandled_uuids.append((mtime, uuid))
            continue

        bulk_context.append(context)

    if bulk_context:  # otherwise: only corrupted files
        # Per default the uuids are sorted chronologically from oldest to newest
        # Therefore the notification plugin also shows the oldest entry first
        # The following configuration option allows to reverse the sorting
        if isinstance(old_params, dict) and old_params.get("bulk_sort_order") == "newest_first":
            bulk_context.reverse()

        context_lines = create_bulk_parameter_context(old_params)
        for context in bulk_context:
            # Do not forget to add this to the monitoring log. We create
            # a single entry for each notification contained in the bulk.
            # It is important later to have this precise information.
            plugin_name = "bulk " + (plugin or "plain email")
            _log_to_history(notification_message(plugin_name, context))

            context_lines.append("\n")
            for varname, value in context.iteritems():
                line = "%s=%s\n" % (varname, value.replace("\r", "").replace("\n", "\1"))
                context_lines.append(line)

        exitcode, output_lines = call_bulk_notification_script(plugin, context_lines)

        for context in bulk_context:
            _log_to_history(
                notification_result_message(
                    "bulk " + (plugin or "plain email"),
                    context,
                    exitcode,
                    output_lines,
                ))
    else:
        notify_log("No valid notification file left. Skipping this bulk.")

    # Remove sent notifications
    for mtime, uuid in uuids:
        if (mtime, uuid) not in unhandled_uuids:
            path = os.path.join(dirname, uuid)
            try:
                os.remove(path)
            except Exception as e:
                notify_log("Cannot remove %s: %s" % (path, e))

    # Repeat with unhandled uuids (due to different parameters)
    if unhandled_uuids:
        notify_bulk(dirname, unhandled_uuids)

    # Remove directory. Not neccessary if emtpy
    try:
        os.rmdir(dirname)
    except Exception as e:
        if not unhandled_uuids:
            notify_log("Warning: cannot remove directory %s: %s" % (dirname, e))


def call_bulk_notification_script(plugin, context_lines):
    path = path_to_notification_script(plugin)
    if not path:
        raise MKGeneralException("Notification plugin %s not found" % plugin)

    stdout_txt = stderr_txt = ""
    try:
        set_notification_timeout()

        # Protocol: The script gets the context on standard input and
        # read until that is closed. It is being called with the parameter
        # --bulk.
        p = subprocess.Popen([path, "--bulk"],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE,
                             close_fds=True)

        stdout_txt, stderr_txt = p.communicate("".join(context_lines).encode("utf-8"))
        exitcode = p.returncode

        clear_notification_timeout()
    except NotificationTimeout:
        notify_log("Notification plugin did not finish within %d seconds. Terminating." %
                   config.notification_plugin_timeout)
        # p.kill() requires python 2.6!
        os.kill(p.pid, signal.SIGTERM)
        exitcode = 1

    if exitcode:
        notify_log("ERROR: script %s --bulk returned with exit code %s" % (path, exitcode))

    output_lines = (stdout_txt + stderr_txt).decode('utf-8').splitlines()
    for line in output_lines:
        notify_log("%s: %s" % (plugin, line.rstrip()))

    return exitcode, output_lines


#.
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


# Be aware: The backlog.mk contains the raw context which has not been decoded
# to unicode yet. It contains raw encoded strings e.g. the plugin output provided
# by third party plugins which might be UTF-8 encoded but can also be encoded in
# other ways. Currently the context is converted later by bot, this module
# and the GUI. TODO Maybe we should centralize the encoding here and save the
# backlock already encoded.
def store_notification_backlog(raw_context):
    path = notification_logdir + "/backlog.mk"
    if not config.notification_backlog:
        if os.path.exists(path):
            os.remove(path)
        return

    backlog = store.load_data_from_file(path, default=[],
                                        lock=True)[:config.notification_backlog - 1]
    store.save_data_to_file(path, [raw_context] + backlog, pretty=False)


def raw_context_from_backlog(nr):
    backlog = store.load_data_from_file(notification_logdir + "/backlog.mk", default=[])

    if nr < 0 or nr >= len(backlog):
        console.error("No notification number %d in backlog.\n" % nr)
        sys.exit(2)

    notify_log("Replaying notification %d from backlog...\n" % nr)
    return backlog[nr]


def raw_context_from_env():
    # Information about notification is excpected in the
    # environment in variables with the prefix NOTIFY_
    raw_context = {
        var[7:]: value
        for var, value in os.environ.items()
        if var.startswith("NOTIFY_") and not dead_nagios_variable(value)
    }
    events.pipe_decode_raw_context(raw_context)
    return raw_context


def substitute_context(template, context):
    # First replace all known variables
    for varname, value in context.items():
        template = template.replace('$' + varname + '$', value)

    # Remove the rest of the variables and make them empty
    template = re.sub(r"\$[A-Z]+\$", "", template)
    return template


#.
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


def format_exception():
    import traceback
    import StringIO

    txt = StringIO.StringIO()
    t, v, tb = sys.exc_info()
    traceback.print_exception(t, v, tb, None, txt)
    return txt.getvalue()


def dead_nagios_variable(value):
    if len(value) < 3:
        return False
    if value[0] != '$' or value[-1] != '$':
        return False
    for c in value[1:-1]:
        if not c.isupper() and c != '_':
            return False
    return True


def notify_log(message):
    if config.notification_logging <= 20:
        events.event_log(notification_log, message)


def notify_log_verbose(message):
    if config.notification_logging <= 15:
        events.event_log(notification_log, message)


def notify_log_debug(message):
    if config.notification_logging <= 10:
        events.event_log(notification_log, message)


def fresh_uuid():
    try:
        return file('/proc/sys/kernel/random/uuid').read().strip()
    except IOError:
        # On platforms where the above file does not exist we try to
        # use the python uuid module which seems to be a good fallback
        # for those systems. Well, if got python < 2.5 you are lost for now.
        import uuid
        return str(uuid.uuid4())


def _log_to_history(message):
    _livestatus_cmd("LOG;%s" % message)


def _livestatus_cmd(command):
    try:
        livestatus.LocalConnection().command("[%d] %s" % (time.time(), command.encode("utf-8")))
    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        notify_log("WARNING: cannot send livestatus command: %s" % e)
        notify_log("Command was: %s" % command)
