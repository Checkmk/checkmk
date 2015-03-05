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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import pprint, urllib, select, subprocess, socket

# Please have a look at doc/Notifications.png:
#
# There are two types of contexts:
# 1. Raw contexts (purple)
#    -> These come out from the monitoring core. They are not yet
#       assinged to a certain plugin. In case of rule based notifictions
#       they are not even assigned to a certain contact.
#
# 2. Plugin contexts (cyan)
#    -> These already bear all information about the contact, the plugin
#       to call and its parameters.

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
notification_logdir     = var_dir + "/notify"
notification_spooldir   = var_dir + "/notify/spool"
notification_bulkdir    = var_dir + "/notify/bulk"
notification_core_log   = var_dir + "/notify/nagios.log" # Fallback for history if no CMC running
notification_log        = log_dir + "/notify.log"
notification_logging    = 1
notification_backlog    = 10 # keep the last 10 notification contexts for reference

# Settings for new rule based notifications
enable_rulebased_notifications = False
notification_fallback_email    = ""
notification_rules             = []
notification_bulk_interval     = 10 # Check every 10 seconds for ripe bulks

# Notification Spooling.

# Possible values for notification_spooling
# "off"    - Direct local delivery without spooling
# "local"  - Asynchronous local delivery by notification spooler
# "remote" - Forward to remote site by notification spooler
# "both"   - Asynchronous local delivery plus remote forwarding
# False    - legacy: sync delivery  (and notification_spool_to)
# True     - legacy: async delivery (and notification_spool_to)
notification_spooling = "off"

# Legacy setting. The spool target is now specified in the
# configuration of the spooler. notification_spool_to has
# the tuple format (remote_host, tcp_port, also_local)
notification_spool_to = None


notification_log_template = \
    u"$CONTACTNAME$ - $NOTIFICATIONTYPE$ - " \
    u"$HOSTNAME$ $HOSTSTATE$ - " \
    u"$SERVICEDESC$ $SERVICESTATE$ "

notification_mail_command = u"mail -s '$SUBJECT$' '$CONTACTEMAIL$'"
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
    sys.stderr.write("""Usage: check_mk --notify [--keepalive]
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
def do_notify(args):
    convert_legacy_configuration()

    global notify_mode, notification_logging
    if notification_logging == 0:
        notification_logging = 1 # transform deprecated value 0 to 1
    try:
        if not os.path.exists(notification_logdir):
            os.makedirs(notification_logdir)
        if not os.path.exists(notification_spooldir):
            os.makedirs(notification_spooldir)

        notify_mode = 'notify'
        if args:
            notify_mode = args[0]
            if notify_mode not in [ 'stdin', 'spoolfile', 'replay', 'send-bulks' ]:
                sys.stderr.write("ERROR: Invalid call to check_mk --notify.\n\n")
                notify_usage()
                sys.exit(1)

            if len(args) != 2 and notify_mode not in [ "stdin", "replay", "send-bulks" ]:
                sys.stderr.write("ERROR: need an argument to --notify %s.\n\n" % notify_mode)
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

        elif opt_keepalive:
            notify_keepalive()

        elif notify_mode == 'replay':
            raw_context = raw_context_from_backlog(replay_nr)
            notify_notify(raw_context)

        elif notify_mode == 'stdin':
            notify_notify(raw_context_from_stdin())

        elif notify_mode == "send-bulks":
            send_ripe_bulks()

        else:
            notify_notify(raw_context_from_env())

    except Exception, e:
        crash_dir = var_dir + "/notify"
        if not os.path.exists(crash_dir):
            os.makedirs(crash_dir)
        file(crash_dir + "/crash.log", "a").write("CRASH (%s):\n%s\n" %
            (time.strftime("%Y-%m-%d %H:%M:%S"), format_exception()))


def convert_legacy_configuration():
    global notification_spooling
    # Convert legacy spooling configuration to new one (see above)
    if notification_spooling in (True, False):
        if notification_spool_to:
            remote_host, tcp_port, also_local = notification_spool_to
            if also_local:
                notification_spooling = "both"
            else:
                notification_spooling = "remote"
        elif notification_spooling:
            notification_spooling = "local"
        else:
            notification_spooling = "remote"

# This function processes one raw notification and decides wether it
# should be spooled or not. In the latter cased a local delivery
# is being done.
def notify_notify(raw_context, analyse=False):
    if not analyse:
        store_notification_backlog(raw_context)

    notify_log("----------------------------------------------------------------------")
    if analyse:
        notify_log("Analysing notification (%s) context with %s variables" % (
            find_host_service(raw_context), len(raw_context)))
    else:
        notify_log("Got raw notification (%s) context with %s variables" % (
            find_host_service(raw_context), len(raw_context)))

    # Add some further variable for the conveniance of the plugins

    if notification_logging >= 2:
        encoded_context = dict(raw_context.items())
        convert_context_to_unicode(encoded_context)
        notify_log("Raw notification context:\n"
                   + "\n".join(["                    %s=%s" % v for v in sorted(encoded_context.items())]))

    raw_keys = list(raw_context.keys())
    try:
        complete_raw_context(raw_context)
    except Exception, e:
        notify_log("Error on completing raw context: %s" % e)

    if notification_logging >= 2:
        notify_log("Computed variables:\n"
                   + "\n".join(sorted(["                    %s=%s" % (k, raw_context[k]) for k in raw_context if k not in raw_keys])))

    # Spool notification to remote host, if this is enabled
    if notification_spooling in ("remote", "both"):
        create_spoolfile({"context": raw_context, "forward": True})

    if notification_spooling != "remote":
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
            notify_log("Preparing rule based notifications")
            return notify_rulebased(raw_context, analyse=analyse)

        if analyse:
            return # Analysis only possible when rule based notifications are enabled

        # Now fetch all configuration about that contact (it needs to be configure via
        # Check_MK for that purpose). If we do not know that contact then we cannot use
        # flexible notifications even if they are enabled.
        contact = contacts.get(contactname)

        if contact.get("disable_notifications", False):
            notify_log("Notifications for %s are disabled in personal settings. Skipping." % contactname)
            return

        # Get notification settings for the contact in question - if available.
        if contact:
            method = contact.get("notification_method", "email")
        else:
            method = "email"

        if type(method) == tuple and method[0] == 'flexible':
            # 2. FLEXIBLE NOTIFICATIONS
            notify_log("Preparing flexible notifications for %s" % contactname)
            notify_flexible(raw_context, method[1])

        else:
            # 3. PLAIN EMAIL NOTIFICATION
            notify_log("Preparing plain email notifications for %s" % contactname)
            notify_plain_email(raw_context)

    except Exception, e:
        if opt_debug:
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

def notify_keepalive():
    last_config_timestamp = config_timestamp()

    # Send signal that we are ready to receive the next notification, but
    # not after a config-reload-restart (see below)
    if os.getenv("CMK_NOTIFY_RESTART") != "1":
        notify_log("Starting in keepalive mode with PID %d" % os.getpid())
        sys.stdout.write("*")
        sys.stdout.flush()
    else:
        notify_log("We are back after a restart.")

    while True:
        try:
            # Invalidate timeperiod cache
            global g_inactive_timerperiods
            g_inactive_timerperiods = None

            # If the configuration has changed, we do a restart. But we do
            # this check just before the next notification arrives. We must
            # *not* read data from stdin, just peek! There is still one
            # problem: when restarting we must *not* send the initial '*'
            # byte, because that must be not no sooner then the notification
            # has been sent. We do this by setting the environment variable
            # CMK_NOTIFY_RESTART=1

            if notify_data_available():
                if last_config_timestamp != config_timestamp():
                    notify_log("Configuration has changed. Restarting myself.")
                    os.putenv("CMK_NOTIFY_RESTART", "1")
                    os.execvp("cmk", sys.argv)

                data = ""
                while not data.endswith("\n\n"):
                    try:
                        new_data = ""
                        new_data = os.read(0, 32768)
                    except IOError, e:
                        new_data = ""
                    except Exception, e:
                        if opt_debug:
                            raise
                        notify_log("Cannot read data from CMC: %s" % e)

                    if not new_data:
                        notify_log("CMC has closed the connection. Shutting down.")
                        sys.exit(0) # closed stdin, this is
                    data += new_data

                try:
                    context = raw_context_from_string(data.rstrip('\n'))
                    notify_notify(context)
                except Exception, e:
                    if opt_debug:
                        raise
                    notify_log("ERROR %s\n%s" % (e, format_exception()))

                # Signal that we are ready for the next notification
                sys.stdout.write("*")
                sys.stdout.flush()


	# Fix vor Python 2.4:
        except SystemExit, e:
            sys.exit(e)
        except Exception, e:
            if opt_debug:
                raise
            notify_log("ERROR %s\n%s" % (e, format_exception()))

        send_ripe_bulks()


def notify_data_available():
    readable, writeable, exceptionable = select.select([0], [], [], notification_bulk_interval)
    return not not readable

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
    # notification plugins to call. This is a dict from (user, plugin) to
    # a pair if (locked, parameters). If locked is True, then a user
    # cannot cancel this notification via his personal notification rules.
    # Example:
    # notifications = {
    #  ( "hh", "email" ) : ( False, [] ),
    #  ( "hh", "sms"   ) : ( True, [ "0171737337", "bar" ] ),
    # }

    notifications = {}
    num_rule_matches = 0
    rule_info = []

    for rule in notification_rules + user_notification_rules():
        if "contact" in rule:
            notify_log("User %s's rule '%s'..." % (rule["contact"], rule["description"]))
        else:
            notify_log("Global rule '%s'..." % rule["description"])

        why_not = rbn_match_rule(rule, raw_context) # also checks disabling
        if why_not:
            notify_log(" -> does not match: %s" % why_not)
            rule_info.append(("miss", rule, why_not))
        else:
            notify_log(" -> matches!")
            num_rule_matches += 1
            contacts = rbn_rule_contacts(rule, raw_context)

            # Handle old-style and new-style rules
            if "notify_method" in rule: # old-style
                plugin = rule["notify_plugin"]
                plugin_parameters = rule["notify_method"] # None: do cancel, [ str ]: plugin parameters
            else:
                plugin, plugin_parameters = rule["notify_plugin"]

            bulk   = rule.get("bulk")

            if plugin_parameters == None: # cancelling
                for contact in contacts:
                    key = contact, plugin
                    if key in notifications:
                        locked, plugin_parameters, bulk = notifications[key]
                        if locked and "contact" in rule:
                            notify_log("   - cannot cancel notification of %s via %s: it is locked" % key)
                        else:
                            notify_log("   - cancelling notification of %s via %s" % key)
                            del notifications[key]
            else:
                final_parameters = rbn_finalize_plugin_parameters(raw_context["HOSTNAME"], plugin, plugin_parameters)
                for contact in contacts:
                    key = contact, plugin
                    plugintxt = plugin or "plain email"
                    if key in notifications:
                        locked, previous_parameters, old_bulk = notifications[key]
                        if locked and "contact" in rule:
                            notify_log("   - cannot modify notification of %s via %s: it is locked" % (contact, plugintxt))
                            continue
                        notify_log("   - modifying notification of %s via %s" % (contact, plugintxt))
                    else:
                        notify_log("   - adding notification of %s via %s" % (contact, plugintxt))
                    notifications[key] = ( not rule.get("allow_disable"), final_parameters, bulk )

            rule_info.append(("match", rule, ""))

    plugin_info = []

    if not notifications:
        if num_rule_matches:
            notify_log("%d rules matched, but no notification has been created." % num_rule_matches)
        else:
            if notification_fallback_email and not analyse:
                notify_log("No rule matched, falling back to email to %s" % notification_fallback_email)
                plugin_context = create_plugin_context(raw_context, [])
                contact = rbn_fake_email_contact(notification_fallback_email)
                rbn_add_contact_information(plugin_context, contact)
                notify_via_email(plugin_context)

    else:
        # Now do the actual notifications
        notify_log("Executing %d notifications:" % len(notifications))
        entries = notifications.items()
        entries.sort()
        for (contact, plugin), (locked, params, bulk) in entries:
            if analyse:
                verb = "would notify"
            else:
                verb = "notifying"
            notify_log("  * %s %s via %s, parameters: %s, bulk: %s" % (
                  verb, contact, (plugin or "plain email"), params and ", ".join(params) or "(no parameters)",
                  bulk and "yes" or "no"))
            plugin_info.append((contact, plugin, params, bulk)) # for analysis
            try:
                plugin_context = create_plugin_context(raw_context, params)
                rbn_add_contact_information(plugin_context, contact)
                if not analyse:
                    if bulk:
                        do_bulk_notify(contact, plugin, params, plugin_context, bulk)
                    elif notification_spooling in ("local", "both"):
                        create_spoolfile({"context": plugin_context, "plugin": plugin})
                    else:
                        call_notification_script(plugin, plugin_context)

            except Exception, e:
                if opt_debug:
                    raise
                fe = format_exception()
                notify_log("    ERROR: %s" % e)
                notify_log(fe)

    analysis_info = rule_info, plugin_info
    return analysis_info

def rbn_finalize_plugin_parameters(hostname, plugin, rule_parameters):
    # Right now we are only able to finalize notification plugins with dict parameters..
    if type(rule_parameters) == dict:
        parameters = host_extra_conf_merged(hostname, notification_parameters.get(plugin, []))
        parameters.update(rule_parameters)
        return parameters
    else:
        return rule_parameters

def add_rulebased_macros(raw_context):
    # For the rule based notifications we need the list of contacts
    # an object has. The CMC does send this in the macro "CONTACTS"
    if "CONTACTS" not in raw_context:
        raw_context["CONTACTS"] = livestatus_fetch_contacts(raw_context["HOSTNAME"], raw_context.get("SERVICEDESC"))

    # Add a pseudo contact name. This is needed for the correct creation
    # of spool files. Spool files are created on a per-contact-base, as in classical
    # notifications the core sends out one individual notification per contact.
    # In the case of rule based notifications we do not make distinctions between
    # the various contacts.
    raw_context["CONTACTNAME"] = "check-mk-notify"


# Create a table of all user specific notification rules. Important:
# create deterministic order, so that rule analyses can depend on
# rule indices
def user_notification_rules():
    user_rules = []
    contactnames = contacts.keys()
    contactnames.sort()
    for contactname in contactnames:
        contact = contacts[contactname]
        for rule in contact.get("notification_rules", []):
            # Save the owner of the rule for later debugging
            rule["contact"] = contactname
            # We assume that the "contact_..." entries in the
            # rule are allowed and only contain one entry of the
            # type "contact_users" : [ contactname ]. This
            # is handled by WATO. Contact specific rules are a
            # WATO-only feature anyway...
            user_rules.append(rule)
    notify_log("Found %d user specific rules" % len(user_rules))
    return user_rules


def rbn_fake_email_contact(email):
    return {
        "name"  : email,
        "alias" : "Explicit email adress " + email,
        "email" : email,
        "pager" : "",
    }


def rbn_add_contact_information(plugin_context, contact):
    if type(contact) == dict:
        for what in [ "name", "alias", "email", "pager" ]:
            plugin_context["CONTACT" + what.upper()] = contact.get(what, "")
        for key in contact.keys():
            if key[0] == '_':
                plugin_context["CONTACT" + key.upper()] = unicode(contact[key])
    else:
        if contact.startswith("mailto:"): # Fake contact
            contact_dict = {
                "name"  : contact[7:],
                "alias" : "Email address " + contact,
                "email" : contact[7:],
                "pager" : "" }
        else:
            contact_dict = contacts.get(contact, { "alias" : contact })
            contact_dict["name"] = contact

        rbn_add_contact_information(plugin_context, contact_dict)


def livestatus_fetch_contacts(host, service):
    try:
        if service:
            query = "GET services\nFilter: host_name = %s\nFilter: service_description = %s\nColumns: contacts\n" % (
                host, service)
        else:
            query = "GET hosts\nFilter: host_name = %s\nColumns: contacts\n" % host

        commasepped = livestatus_fetch_query(query).strip()
        aslist = commasepped.split(",")
        if "check-mk-notify" in aslist: # Remove artifical contact used for rule based notifications
            aslist.remove("check-mk-notify")
        return ",".join(aslist)

    except:
        if opt_debug:
            raise
        return "" # We must allow notifications without Livestatus access



def rbn_match_rule(rule, context):
    if rule.get("disabled"):
        return "This rule is disabled"

    return \
        rbn_match_folder(rule, context)                or \
        rbn_match_hosttags(rule, context)              or \
        rbn_match_hostgroups(rule, context)            or \
        rbn_match_servicegroups(rule, context)         or \
        rbn_match_contactgroups(rule, context)         or \
        rbn_match_hosts(rule, context)                 or \
        rbn_match_exclude_hosts(rule, context)         or \
        rbn_match_services(rule, context)              or \
        rbn_match_exclude_services(rule, context)      or \
        rbn_match_plugin_output(rule, context)         or \
        rbn_match_checktype(rule, context)             or \
        rbn_match_timeperiod(rule)                     or \
        rbn_match_escalation(rule, context)            or \
        rbn_match_escalation_throtte(rule, context)    or \
        rbn_match_servicelevel(rule, context)          or \
        rbn_match_host_event(rule, context)            or \
        rbn_match_service_event(rule, context)         or \
        rbn_match_event_console(rule, context)


def rbn_match_folder(rule, context):
    if "match_folder" in rule:
        mustfolder = rule["match_folder"]
        mustpath = mustfolder.split("/")
        hasfolder = None
        for tag in context.get("HOSTTAGS", "").split():
            if tag.startswith("/wato/"):
                hasfolder = tag[6:].rstrip("/")
                haspath = hasfolder.split("/")
                if mustpath == ["",]:
                    return # Match is on main folder, always OK
                while mustpath:
                    if not haspath or mustpath[0] != haspath[0]:
                        return "The rule requires WATO folder '%s', but the host is in '%s'" % (
                            mustfolder, hasfolder)
                    mustpath = mustpath[1:]
                    haspath = haspath[1:]

        if hasfolder == None:
            return "The host is not managed via WATO, but the rule requires a WATO folder"


def rbn_match_hosttags(rule, context):
    required = rule.get("match_hosttags")
    if required:
        tags = context.get("HOSTTAGS", "").split()
        if not hosttags_match_taglist(tags, required):
            return "The host's tags %s do not match the required tags %s" % (
                "|".join(tags), "|".join(required))


def rbn_match_servicegroups(rule, context):
    if context["WHAT"] != "SERVICE":
        return
    required_groups = rule.get("match_servicegroups")
    if required_groups != None:
        sgn = context.get("SERVICEGROUPNAMES")
        if sgn == None:
            return "No information about service groups is in the context, but service " \
                   "must be in group %s" % ( " or ".join(required_groups))
        if sgn:
            servicegroups = sgn.split(",")
        else:
            return "The service is in no group, but %s is required" % (
                 " or ".join(required_groups))

        for group in required_groups:
            if group in servicegroups:
                return

        return "The service is only in the groups %s, but %s is required" % (
              sgn, " or ".join(required_groups))

def rbn_match_contactgroups(rule, context):
    required_groups = rule.get("match_contactgroups")
    if context["WHAT"] == "SERVICE":
        cgn = context.get("SERVICECONTACTGROUPNAMES")
    else:
        cgn = context.get("HOSTCONTACTGROUPNAMES")

    if required_groups != None:
        if cgn == None:
            notify_log("Warning: No information about contact groups in the context. " \
                       "Seams that you don't use the Check_MK Microcore. ")
            return
        if cgn:
            contactgroups = cgn.split(",")
        else:
            return "The object is in no group, but %s is required" % (
                 " or ".join(required_groups))

        for group in required_groups:
            if group in contactgroups:
                return

        return "The object is only in the groups %s, but %s is required" % (
              cgn, " or ".join(required_groups))


def rbn_match_hostgroups(rule, context):
    required_groups = rule.get("match_hostgroups")
    if required_groups != None:
        hgn = context.get("HOSTGROUPNAMES")
        if hgn == None:
            return "No information about host groups is in the context, but host " \
                   "must be in group %s" % ( " or ".join(required_groups))
        if hgn:
            hostgroups = hgn.split(",")
        else:
            return "The host is in no group, but %s is required" % (
                 " or ".join(required_groups))

        for group in required_groups:
            if group in hostgroups:
                return

        return "The host is only in the groups %s, but %s is required" % (
              hgn, " or ".join(required_groups))


def rbn_match_hosts(rule, context):
    if "match_hosts" in rule:
        hostlist = rule["match_hosts"]
        if context["HOSTNAME"] not in hostlist:
            return "The host's name '%s' is not on the list of allowed hosts (%s)" % (
                context["HOSTNAME"], ", ".join(hostlist))


def rbn_match_exclude_hosts(rule, context):
    if context["HOSTNAME"] in rule.get("match_exclude_hosts", []):
        return "The host's name '%s' is on the list of excluded hosts" % context["HOSTNAME"]


def rbn_match_services(rule, context):
    if "match_services" in rule:
        if context["WHAT"] != "SERVICE":
            return "The rule specifies a list of services, but this is a host notification."
        servicelist = rule["match_services"]
        service = context["SERVICEDESC"]
        if not in_extraconf_servicelist(servicelist, service):
            return "The service's description '%s' dows not match by the list of " \
                   "allowed services (%s)" % (service, ", ".join(servicelist))


def rbn_match_exclude_services(rule, context):
    if context["WHAT"] != "SERVICE":
        return
    excludelist = rule.get("match_exclude_services", [])
    service = context["SERVICEDESC"]
    if in_extraconf_servicelist(excludelist, service):
        return "The service's description '%s' matches the list of excluded services" \
          % context["SERVICEDESC"]


def rbn_match_plugin_output(rule, context):
    if "match_plugin_output" in rule:
        r = regex(rule["match_plugin_output"])

        if context["WHAT"] == "SERVICE":
            output = context["SERVICEOUTPUT"]
        else:
            output = context["HOSTOUTPUT"]
        if not r.search(output):
            return "The expression '%s' cannot be found in the plugin output '%s'" % \
                (rule["match_plugin_output"], output)


def rbn_match_checktype(rule, context):
    if "match_checktype" in rule:
        if context["WHAT"] != "SERVICE":
            return "The rule specifies a list of Check_MK plugins, but this is a host notification."
        command = context["SERVICECHECKCOMMAND"]
        if not command.startswith("check_mk-"):
            return "The rule specified a list of Check_MK plugins, but his is no Check_MK service."
        plugin = command[9:]
        allowed = rule["match_checktype"]
        if plugin not in allowed:
            return "The Check_MK plugin '%s' is not on the list of allowed plugins (%s)" % \
              (plugin, ", ".join(allowed))


def rbn_match_timeperiod(rule):
    if "match_timeperiod" in rule:
        timeperiod = rule["match_timeperiod"]
        if timeperiod != "24X7" and not check_timeperiod(timeperiod):
            return "The timeperiod '%s' is currently not active." % timeperiod


def rbn_match_escalation(rule, context):
    if "match_escalation" in rule:
        from_number, to_number = rule["match_escalation"]
        if context["WHAT"] == "HOST":
            notification_number = int(context.get("HOSTNOTIFICATIONNUMBER", 1))
        else:
            notification_number = int(context.get("SERVICENOTIFICATIONNUMBER", 1))
        if notification_number < from_number or notification_number > to_number:
            return "The notification number %d does not lie in range %d ... %d" % (
                    notification_number, from_number, to_number)

def rbn_match_escalation_throtte(rule, context):
    if "match_escalation_throttle" in rule:
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

def rbn_match_servicelevel(rule, context):
    if "match_sl" in rule:
        from_sl, to_sl = rule["match_sl"]
        if context['WHAT'] == "SERVICE" and context.get('SVC_SL','').isdigit():
            sl = saveint(context.get('SVC_SL'))
        else:
            sl = saveint(context.get('HOST_SL'))

        if sl < from_sl or sl > to_sl:
            return "The service level %d is not between %d and %d." % (sl, from_sl, to_sl)


def rbn_match_host_event(rule, context):
    if "match_host_event" in rule:
        if context["WHAT"] != "HOST":
            if "match_service_event" not in rule:
                return "This is a service notification, but the rule just matches host events"
            else:
                return # Let this be handled by match_service_event
        allowed_events = rule["match_host_event"]
        state          = context["HOSTSTATE"]
        last_state     = context["PREVIOUSHOSTHARDSTATE"]
        events         = { "UP" : 'r', "DOWN" : 'd', "UNREACHABLE" : 'u' }
        return rbn_match_event(context, state, last_state, events, allowed_events)


def rbn_match_service_event(rule, context):
    if "match_service_event" in rule:
        if context["WHAT"] != "SERVICE":
            if "match_host_event" not in rule:
                return "This is a host notification, but the rule just matches service events"
            else:
                return # Let this be handled by match_host_event
        allowed_events = rule["match_service_event"]
        state          = context["SERVICESTATE"]
        last_state     = context["PREVIOUSSERVICEHARDSTATE"]
        events         = { "OK" : 'r', "WARNING" : 'w', "CRITICAL" : 'c', "UNKNOWN" : 'u' }
        return rbn_match_event(context, state, last_state, events, allowed_events)


def rbn_match_event(context, state, last_state, events, allowed_events):
    notification_type = context["NOTIFICATIONTYPE"]

    if notification_type == "RECOVERY":
        event = events.get(last_state, '?') + 'r'
    elif notification_type in [ "FLAPPINGSTART", "FLAPPINGSTOP", "FLAPPINGDISABLED" ]:
        event = 'f'
    elif notification_type in [ "DOWNTIMESTART", "DOWNTIMEEND", "DOWNTIMECANCELLED"]:
        event = 's'
    elif notification_type == "ACKNOWLEDGEMENT":
        event = 'x'
    else:
        event = events.get(last_state, '?') + events.get(state, '?')

    notify_log("Event type is %s" % event)

    # Now go through the allowed events. Handle '?' has matching all types!
    for allowed in allowed_events:
        if event == allowed or \
            event[0] == '?' and event[1] == allowed[1]:
            return

    return "Event type '%s' not handled by this rule. Allowed are: %s" % (
            event, ", ".join(allowed_events))


def rbn_rule_contacts(rule, context):
    the_contacts = set([])
    if rule.get("contact_object"):
        the_contacts.update(rbn_object_contacts(context))
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
        contact = contacts.get(contactname)
        if contact and contact.get("disable_notifications", False):
            notify_log("   - skipping contact %s: he/she has disabled notifications" % contactname)
        else:
            all_enabled.append(contactname)

    return all_enabled


def rbn_match_event_console(rule, context):
    if "match_ec" in rule:
        match_ec = rule["match_ec"]
        is_ec_notification = "EC_ID" in context
        if match_ec == False and is_ec_notification:
            return "Notification has been created by the Event Console."
        elif match_ec != False and not is_ec_notification:
            return "Notification has not been created by the Event Console."

        if match_ec != False:

            # Match Event Console rule ID
            if "match_rule_id" in match_ec and context["EC_RULE_ID"] != match_ec["match_rule_id"]:
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
                    return "Wrong syslog facility %s, required is %s" % (context["EC_FACILITY"], match_ec["match_facility"])

            # Match event comment
            if "match_comment" in match_ec:
                r = regex(match_ec["match_comment"])
                if not r.search(context["EC_COMMENT"]):
                    return "The event comment '%s' does not match the regular expression '%s'" % (
                        context["EC_COMMENT"], match_ec["match_comment"])


def rbn_object_contacts(context):
    commasepped = context.get("CONTACTS")
    if commasepped:
        return commasepped.split(",")
    else:
        return []


def rbn_all_contacts(with_email=None):
    if not with_email:
        return contacts.keys() # We have that via our main.mk contact definitions!
    else:
        return [
          contact_id
          for (contact_id, contact)
          in contacts.items()
          if contact.get("email")]


def rbn_groups_contacts(groups):
    if not groups:
        return {}
    contacts = set([])
    query = "GET contactgroups\nColumns: members\n"
    for group in groups:
        query += "Filter: name = %s\n" % group
    query += "Or: %d\n" % len(groups)
    response = livestatus_fetch_query(query)
    for line in response.splitlines():
        line = line.strip()
        if line:
            contacts.update(line.split(","))
    return contacts


def rbn_emails_contacts(emails):
    return [ "mailto:" + e for e in emails ]


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

        if notification_spooling in ("local", "both"):
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
        regex = False
        negate = False
        for h in entry["only_hosts"]:
            if h.startswith("!"): # negate
                negate = True
                h = h[1:]
            elif h.startswith('~'):
                regex = True
                h = h[1:]

            if not regex and hostname == h:
                skip = negate
                break

            elif regex and re.match(h, hostname):
                skip = negate
                break
        if skip:
            notify_log(" - Skipping: host '%s' matches none of %s" % (hostname, ", ".join(entry["only_hosts"])))
            return False

    # Check if the host has to be in a special service_level
    if "match_sl" in entry:
        from_sl, to_sl = entry['match_sl']
        if context['WHAT'] == "SERVICE" and context.get('SVC_SL','').isdigit():
            sl = saveint(context.get('SVC_SL'))
        else:
            sl = saveint(context.get('HOST_SL'))

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
                    notify_log(" - Skipping: service '%s' matches blacklist (%s)" % (
                        servicedesc, ", ".join(entry["service_blacklist"])))
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
                if s.startswith("!"): # negate
                    negate = True
                    s = s[1:]
                else:
                    negate = False
                if re.match(s, servicedesc):
                    skip = negate
                    break
            if skip:
                notify_log(" - Skipping: service '%s' matches none of %s" % (
                    servicedesc, ", ".join(entry["only_services"])))
                return False

    # Check notification type
    event, allowed_events = check_notification_type(context, entry["host_events"], entry["service_events"])
    if event not in allowed_events:
        notify_log(" - Skipping: wrong notification type %s (%s), only %s are allowed" %
            (event, context["NOTIFICATIONTYPE"], ",".join(allowed_events)) )
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
            if not check_timeperiod(timeperiod):
                notify_log(" - Skipping: time period %s is currently not active" % timeperiod)
                return False
    return True

def check_notification_type(context, host_events, service_events):
    notification_type = context["NOTIFICATIONTYPE"]
    if context["WHAT"] == "HOST":
        allowed_events = host_events
        state = context["HOSTSTATE"]
        events = { "UP" : 'r', "DOWN" : 'd', "UNREACHABLE" : 'u' }
    else:
        allowed_events = service_events
        state = context["SERVICESTATE"]
        events = { "OK" : 'r', "WARNING" : 'w', "CRITICAL" : 'c', "UNKNOWN" : 'u' }

    if notification_type == "RECOVERY":
        event = 'r'
    elif notification_type in [ "FLAPPINGSTART", "FLAPPINGSTOP", "FLAPPINGDISABLED" ]:
        event = 'f'
    elif notification_type in [ "DOWNTIMESTART", "DOWNTIMEEND", "DOWNTIMECANCELLED"]:
        event = 's'
    elif notification_type == "ACKNOWLEDGEMENT":
        event = 'x'
    else:
        event = events.get(state, '?')

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

    if notification_spooling in ("local", "both"):
        create_spoolfile({"context": plugin_context, "plugin" : None})
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
    command = substitute_context(notification_mail_command, plugin_context)
    command_utf8 = command.encode("utf-8")

    # Make sure that mail(x) is using UTF-8. Otherwise we cannot send notifications
    # with non-ASCII characters. Unfortunately we do not know whether C.UTF-8 is
    # available. If e.g. nail detects a non-Ascii character in the mail body and
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
            if notification_logging >= 2:
                notify_log("Setting locale for mail to %s." % encoding)
            break
    else:
        notify_log("No UTF-8 encoding found in your locale -a! Please provide C.UTF-8 encoding.")

    # Important: we must not output anything on stdout or stderr. Data of stdout
    # goes back into the socket to the CMC in keepalive mode and garbles the
    # handshake signal.
    if notification_logging >= 2:
        notify_log("Executing command: %s" % command)

    p = subprocess.Popen(command_utf8, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    stdout_txt, stderr_txt = p.communicate(body.encode("utf-8"))
    exitcode = p.returncode
    os.putenv("LANG", old_lang) # Important: do not destroy our environment
    if exitcode != 0:
        notify_log("ERROR: could not deliver mail. Exit code of command is %r" % exitcode)
        for line in (stdout_txt + stderr_txt).splitlines():
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
    plugin_context.update(raw_context) # Make a real copy

    if type(params) == list:
        plugin_context["PARAMETERS"] = " ".join(params)
        for nr, param in enumerate(params):
            plugin_context["PARAMETER_%d" % (nr + 1)] = param
    else:
        for key, value in params.items():
            plugin_context["PARAMETER_" + key.upper()] = plugin_param_to_string(value)
    return plugin_context


def create_bulk_parameter_context(params):
    dict_context = create_plugin_context({}, params)
    return [ "%s=%s\n" % (varname, value.replace("\r", "").replace("\n", "\1"))
             for (varname, value) in dict_context.items() ]


def plugin_param_to_string(value):
    if type(value) in ( str, unicode ):
        return value
    elif type(value) in ( int, float ):
        return str(value)
    elif value == None:
        return ""
    elif value == True:
        return "yes"
    elif value == False:
        return ""
    elif type(value) in ( tuple, list ):
        return "\t".join(value)
    else:
        return repr(value) # Should never happen


def path_to_notification_script(plugin):
    # Call actual script without any arguments
    if local_notifications_dir:
        path = local_notifications_dir + "/" + plugin
        if not os.path.exists(path):
            path = notifications_dir + "/" + plugin
    else:
        path = notifications_dir + "/" + plugin

    if not os.path.exists(path):
        notify_log("Notification plugin '%s' not found" % plugin)
        notify_log("  not in %s" % notifications_dir)
        if local_notifications_dir:
            notify_log("  and not in %s" % local_notifications_dir)
        return None

    else:
        return path

# This is the function that finally sends the actual notificion.
# It does this by calling an external script are creating a
# plain email and calling bin/mail.
#
# It also does the central logging of the notifications
# that are actually sent out.
#
# Note: this function is *not* being called for bulk notification.
def call_notification_script(plugin, plugin_context):
    core_notification_log(plugin, plugin_context)

    # The "Pseudo"-Plugin None means builtin plain email
    if not plugin:
        return notify_via_email(plugin_context)

    # Call actual script without any arguments
    path = path_to_notification_script(plugin)
    if not path:
        return 2

    # Export complete context to have all vars in environment.
    # Existing vars are replaced, some already existing might remain
    for key in plugin_context:
        if type(plugin_context[key]) == bool:
            notify_log("INTERNAL ERROR: %s=%s is of type bool" % (key, plugin_context[key]))
        os.putenv('NOTIFY_' + key, plugin_context[key].encode('utf-8'))

    notify_log("     executing %s" % path)
    out = os.popen(path + " 2>&1 </dev/null")
    for line in out:
        notify_log("Output: %s" % line.rstrip().decode('utf-8'))
    exitcode = out.close()
    if exitcode:
        notify_log("Plugin exited with code %d" % (exitcode >> 8))
    else:
        exitcode = 0

    # Clear environment again. TODO: We could os process.Popen and specify
    # the environment without destroying it?
    for key in plugin_context:
        os.unsetenv('NOTIFY_' + key)

    return exitcode



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
    file(file_path,"w").write(pprint.pformat(data))


# There are three types of spool files:
# 1. Notifications to be forwarded. Contain key "forward"
# 2. Notifications for async local delivery. Contain key "plugin"
# 3. Notifications to *got* forwarded. Contain neither of both.
# Spool files of type 1 are not handled here!
def handle_spoolfile(spoolfile):
    notify_log("----------------------------------------------------------------------")
    try:
        data = eval(file(spoolfile).read())
        if "plugin" in data:
            plugin_context = data["context"]
            plugin = data["plugin"]
            notify_log("Got spool file (%s) for local delivery via %s" % (
                find_host_service(plugin_context), (plugin or "plain mail")))
            return call_notification_script(plugin, plugin_context)

        else:
            # We received a forwarded raw notification. We need to process
            # this with our local notification rules in order to call one,
            # several or no actual plugins.
            notify_log("Got spool file from remote host for local delivery.")
            raw_context = data["context"]
            locally_deliver_raw_context(data["context"])
            return 0 # No error handling for async delivery

    except Exception, e:
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

def do_bulk_notify(contact, plugin, params, plugin_context, bulk):
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
    bulk_path = (contact, plugin, str(bulk["interval"]), str(bulk["count"]))
    bulkby = bulk["groupby"]
    if "host" in bulkby:
        bulk_path += ("host", plugin_context["HOSTNAME"])
    elif "folder" in bulkby:
        bulk_path += ("folder", find_wato_folder(plugin_context))
    if "service" in bulkby:
        bulk_path += ("service", plugin_context.get("SERVICEDESC", ""))
    if "sl" in bulkby:
        sl = plugin_context.get(what + "_SL", "")
        bulk_path += ("sl", sl)
    if "check_type" in bulkby:
        command = plugin_context.get(what + "CHECKCOMMAND", "").split("!")[0]
        bulk_path += ("check_type", command)
    if "state" in bulkby:
        state = plugin_context.get(what + "STATE", "")
        bulk_path += ("state", state)

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
    os.rename(filename + ".new", filename) # We need an atomic creation!
    notify_log("        - stored in %s" % filename)


def find_wato_folder(context):
    for tag in context.get("HOSTTAGS", "").split():
        if tag.startswith("/wato/"):
            return tag[6:].rstrip("/")
    return ""


def create_bulk_dirname(bulk_path):
    dirname = notification_bulkdir + "/" + bulk_path[0] + "/" + bulk_path[1] + "/"
    dirname += ",".join([b.replace("/", "\\") for b in bulk_path[2:]])

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


def find_bulks(only_ripe):
    if not os.path.exists(notification_bulkdir):
        return []

    now = time.time()
    bulks = []

    dir_1 = notification_bulkdir
    for contact in os.listdir(dir_1):
        if contact.startswith("."):
            continue
        dir_2 = dir_1 + "/" + contact
        for method in os.listdir(dir_2):
            if method.startswith("."):
                continue
            dir_3 = dir_2 + "/" + method
            for bulk in os.listdir(dir_3):
                parts = bulk.split(',') # e.g. 60,10,host,localhost
                try:
                    interval = int(parts[0])
                    count = int(parts[1])
                except:
                    notify_log("Skipping invalid bulk directory %s" % dir_3)
                    continue
                dir_4 = dir_3 + "/" + bulk
                uuids = []
                oldest = time.time()
                for uuid in os.listdir(dir_4): # 4ded0fa2-f0cd-4b6a-9812-54374a04069f
                    if uuid.startswith(".") or uuid.endswith(".new"):
                        continue
                    if len(uuid) != 36:
                        notify_log("Skipping invalid notification file %s/%s" % (dir_4, uuid))
                        continue

                    mtime = os.stat(dir_4 + "/" + uuid).st_mtime
                    uuids.append((mtime, uuid))
                    oldest = min(oldest, mtime)

                uuids.sort()
                if not uuids:
                    dirage = now - os.stat(dir_4).st_mtime
                    if dirage > 60:
                        notify_log("Warning: removing orphaned empty bulk directory %s" % dir_4)
                        try:
                            os.rmdir(dir_4)
                        except Exception, e:
                            notify_log("    -> Error removing it: %s" % e)
                    continue

                age = now - oldest
                if age >= interval:
                    notify_log("Bulk %s is ripe: age %d >= %d" % (dir_4, age, interval))
                elif len(uuids) >= count:
                    notify_log("Bulk %s is ripe: count %d >= %d" % (dir_4, len(uuids), count))
                else:
                    notify_log("Bulk %s is not ripe yet (age: %d, count: %d)!" % (dir_4, age, len(uuids)))
                    if only_ripe:
                        continue

                bulks.append((dir_4, age, interval, count, uuids))

    return bulks

def send_ripe_bulks():
    ripe = find_bulks(True)
    if ripe:
        notify_log("Sending out %d ripe bulk notifications" % len(ripe))
        for bulk in ripe:
            try:
                notify_bulk(bulk[0], bulk[-1])
            except Exception, e:
                if opt_debug:
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
            params, context = eval(file(dirname + "/" + uuid).read())
        except Exception, e:
            if opt_debug:
                raise
            notify_log("    Deleting corrupted or empty bulk file %s/%s: %s" % (dirname, uuid, e))
            continue

        if old_params == None:
            old_params = params
        elif params != old_params:
            notify_log("     Parameters are different from previous, postponing into separate bulk")
            unhandled_uuids.append((mtime, uuid))
            continue

        bulk_context.append("\n")
        for varname, value in context.items():
            bulk_context.append("%s=%s\n" % (varname, value.replace("\r", "").replace("\n", "\1")))

        # Do not forget to add this to the monitoring log. We create
        # a single entry for each notification contained in the bulk.
        # It is important later to have this precise information.
        plugin_name = "bulk " + (plugin or "plain email")
        core_notification_log(plugin_name, context)

    if bulk_context: # otherwise: only corrupted files
        parameter_context = create_bulk_parameter_context(old_params)
        context_text = "".join(parameter_context + bulk_context)
        call_bulk_notification_script(plugin, context_text)
    else:
        notify_log("No valid notification file left. Skipping this bulk.")

    # Remove sent notifications
    for mtime, uuid in uuids:
        if (mtime, uuid) not in unhandled_uuids:
            path = dirname + "/" + uuid
            try:
                os.remove(path)
            except Exception, e:
                notify_log("Cannot remove %s: %s" % (path, e))

    # Repeat with unhandled uuids (due to different parameters)
    if unhandled_uuids:
        notify_bulk(dirname, unhandled_uuids)

    # Remove directory. Not neccessary if emtpy
    try:
        os.rmdir(dirname)
    except Exception, e:
        if not unhandled_uuids:
            notify_log("Warning: cannot remove directory %s: %s" % (dirname, e))


def call_bulk_notification_script(plugin, context_text):
    path = path_to_notification_script(plugin)
    if not path:
        raise MKGeneralException("Notification plugin %s not found" % plugin)

    # Protocol: The script gets the context on standard input and
    # read until that is closed. It is being called with the parameter
    # --bulk.
    p = subprocess.Popen([path, "--bulk"], shell=False,
                         stdout = subprocess.PIPE, stderr = subprocess.PIPE, stdin = subprocess.PIPE)
    stdout_txt, stderr_txt = p.communicate(context_text.encode("utf-8"))
    exitcode = p.returncode
    if exitcode:
        notify_log("ERROR: script %s --bulk returned with exit code %s" % (path, exitcode))
    for line in (stdout_txt + stderr_txt).splitlines():
        notify_log("%s: %s" % (plugin, line.rstrip()))

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

# Add a few further helper variables that are usefull in notification plugins
def complete_raw_context(raw_context):
    raw_context["WHAT"] = raw_context.get("SERVICEDESC") and "SERVICE" or "HOST"
    raw_context["MONITORING_HOST"] = socket.gethostname()
    raw_context["LOGDIR"] = notification_logdir
    if omd_root:
        raw_context["OMD_ROOT"] = omd_root
        raw_context["OMD_SITE"] = os.getenv("OMD_SITE", "")
    raw_context["MAIL_COMMAND"] = notification_mail_command

    # The Check_MK Micro Core sends the MICROTIME and no other time stamps. We add
    # a few Nagios-like variants in order to be compatible
    if "MICROTIME" in raw_context:
        microtime = int(raw_context["MICROTIME"])
        timestamp = float(microtime) / 1000000.0
        broken = time.localtime(timestamp)
        raw_context["DATE"] = time.strftime("%Y-%m-%d", broken)
        raw_context["SHORTDATETIME"] = time.strftime("%Y-%m-%d %H:%M:%S", broken)
        raw_context["LONGDATETIME"] = time.strftime("%a %b %d %H:%M:%S %Z %Y", broken)

    raw_context['HOSTURL'] = '/check_mk/index.py?start_url=%s' % \
                        urlencode('view.py?view_name=hoststatus&host=%s' % raw_context['HOSTNAME'])
    if raw_context['WHAT'] == 'SERVICE':
        raw_context['SERVICEURL'] = '/check_mk/index.py?start_url=%s' % \
                                    urlencode('view.py?view_name=service&host=%s&service=%s' %
                                                 (raw_context['HOSTNAME'], raw_context['SERVICEDESC']))

    # Relative Timestamps for several macros
    for macro in [ 'LASTHOSTSTATECHANGE', 'LASTSERVICESTATECHANGE', 'LASTHOSTUP', 'LASTSERVICEOK' ]:
        if macro in raw_context:
            raw_context[macro + '_REL'] = get_readable_rel_date(raw_context[macro])


    # Rule based notifications enabled? We might need to complete a few macros
    contact = raw_context.get("CONTACTNAME")
    if not contact or contact == "check-mk-notify":
        add_rulebased_macros(raw_context)

    # For custom notifications the number is set to 0 by the core (Nagios and CMC). We force at least
    # number 1 here, so that rules with conditions on numbers do not fail (the minimum is 1 here)
    for what in [ "HOST", "SERVICE" ]:
        key = what + "NOTIFICATIONNUMBER"
        if key in raw_context and  raw_context[key] == "0":
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
            notify_log("Previous host hard state not known. Allowing all states.")
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
            notify_log("Previous service hard state not known. Allowing all states.")
        raw_context["PREVIOUSSERVICEHARDSTATE"] = prev_state

    # Add short variants for state names (at most 4 characters)
    for key, value in raw_context.items():
        if key.endswith("STATE"):
            raw_context[key[:-5] + "SHORTSTATE"] = value[:4]

    if raw_context["WHAT"] == "SERVICE":
        raw_context['SERVICEFORURL'] = urllib.quote(raw_context['SERVICEDESC'])
    raw_context['HOSTFORURL'] = urllib.quote(raw_context['HOSTNAME'])

    convert_context_to_unicode(raw_context)


def store_notification_backlog(raw_context):
    path = notification_logdir + "/backlog.mk"
    if not notification_backlog:
        if os.path.exists(path):
            os.remove(path)
        return

    try:
        backlog = eval(file(path).read())[:notification_backlog-1]
    except:
        backlog = []

    backlog = [ raw_context ] + backlog
    file(path, "w").write("%r\n" % backlog)


def raw_context_from_backlog(nr):
    try:
        backlog = eval(file(notification_logdir + "/backlog.mk").read())
    except:
        backlog = []

    if nr < 0 or nr >= len(backlog):
        sys.stderr.write("No notification number %d in backlog.\n" % nr)
        sys.exit(2)

    notify_log("Replaying notification %d from backlog...\n" % nr)
    return backlog[nr]


def raw_context_from_env():
    # Information about notification is excpected in the
    # environment in variables with the prefix NOTIFY_
    return dict([
        (var[7:], value)
        for (var, value)
        in os.environ.items()
        if var.startswith("NOTIFY_")
            and not dead_nagios_variable(value) ])


def raw_context_from_stdin():
    context = {}
    for line in sys.stdin:
        varname, value = line.strip().split("=", 1)
        context[varname] = value.replace(r"\n", "\n").replace("\\\\", "\\")
    return context


def raw_context_from_string(data):
    # Context is line-by-line in g_notify_readahead_buffer
    context = {}
    try:
        for line in data.split('\n'):
            varname, value = line.strip().split("=", 1)
            context[varname] = value.replace(r"\n", "\n").replace("\\\\", "\\")
    except Exception, e: # line without '=' ignored or alerted
        if opt_debug:
            raise
    return context


def convert_context_to_unicode(context):
    # Convert all values to unicode
    for key, value in context.iteritems():
        if type(value) == str:
            try:
                value_unicode = value.decode("utf-8")
            except:
                try:
                    value_unicode = value.decode("latin-1")
                except:
                    value_unicode = u"(Invalid byte sequence)"
            context[key] = value_unicode


def substitute_context(template, context):
    # First replace all known variables
    for varname, value in context.items():
        template = template.replace('$'+varname+'$', value)

    # Remove the rest of the variables and make them empty
    template = re.sub("\$[A-Z]+\$", "", template)
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

def find_host_service(context):
    host = context.get("HOSTNAME", "UNKNOWN")
    service = context.get("SERVICEDESC")
    if service:
        return host + ";" + service
    else:
        return host

def livestatus_fetch_query(query):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(livestatus_unix_socket)
    sock.send(query)
    sock.shutdown(socket.SHUT_WR)
    response = sock.recv(10000000)
    sock.close()
    return response

def livestatus_send_command(command):
    try:
        message = "COMMAND [%d] %s\n" % (time.time(), command)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(livestatus_unix_socket)
        sock.send(message)
        sock.close()
    except Exception, e:
        if opt_debug:
            raise
        notify_log("WARNING: cannot send livestatus command: %s" % e)
        notify_log("Command was: %s" % command)


def format_exception():
    import traceback, StringIO, sys
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
    if notification_logging >= 1:
        formatted = u"%s %s\n" % (time.strftime("%F %T", time.localtime()), message)
        file(notification_log, "a").write(formatted.encode("utf-8"))

def get_readable_rel_date(timestamp):
    try:
        change = int(timestamp)
    except:
        change = 0
    rel_time = time.time() - change
    seconds = rel_time % 60
    rem = rel_time / 60
    minutes = rem % 60
    hours = (rem % 1440) / 60
    days = rem / 1440
    return '%dd %02d:%02d:%02d' % (days, hours, minutes, seconds)

def urlencode(s):
    return urllib.quote(s)

def fresh_uuid():
    try:
        return file('/proc/sys/kernel/random/uuid').read().strip()
    except IOError:
        # On platforms where the above file does not exist we try to
        # use the python uuid module which seems to be a good fallback
        # for those systems. Well, if got python < 2.5 you are lost for now.
        import uuid
        return str(uuid.uuid4())

def core_notification_log(plugin, plugin_context):
    what = plugin_context["WHAT"]
    contact = plugin_context["CONTACTNAME"]
    spec = plugin_context["HOSTNAME"]
    if what == "HOST":
        state = plugin_context["HOSTSTATE"]
        output = plugin_context["HOSTOUTPUT"]
    if what == "SERVICE":
        spec += ";" + plugin_context["SERVICEDESC"]
        state = plugin_context["SERVICESTATE"]
        output = plugin_context["SERVICEOUTPUT"]

    log_message = "%s NOTIFICATION: %s;%s;%s;%s;%s" % (
            what, contact, spec, state, plugin or "plain email", output)
    if monitoring_core == "cmc":
        livestatus_send_command("LOG;" + log_message.encode("utf-8"))
    else:
        # Nagios and friends do not support logging via an
        # external command. We write the files into a help file
        # in var/check_mk/notify. If the users likes he can
        # replace that file with a symbolic link to the nagios
        # log file. But note: Nagios logging might not atomic.
        file(notification_core_log, "a").write("[%d] %s\n" % (time.time(), log_message.encode("utf-8")))

