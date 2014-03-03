#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

# Environment macros are turned of due to Livestatus. So we
# need to go the hard (but efficient) way of using command line
# arguments. Fetching things via Livestatus would be possible
# but might introduce problems (for example race conditions).

# Specify a command that reads a mail body from stdin (an UTF-8
# encoded one) and can use any of the variables contact, email,
# hostname, servicedesc, hoststate, servicestate, output in
# the form %(variable)s

import pprint, urllib, select, subprocess, socket

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
notification_log        = notification_logdir + "/notify.log"
notification_logging    = 0
notification_backlog    = 10 # keep the last 10 notification contexts for reference

# Settings for new rule based notifications
enable_rulebased_notifications = False
notification_fallback_email    = ""
notification_rules             = []

# Notification Spooling
notification_spooling = False
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
       check_mk --notify fake-service <plugin>
       check_mk --notify fake-host <plugin>
       check_mk --notify spoolfile <filename>

Normally the notify module is called without arguments to send real
notification. But there are situations where this module is called with
COMMANDS to e.g. support development of notification plugins.

Available commands:
    fake-service <plugin>   Calls the given notification plugin with fake
                            notification data of a service notification.
    fake-host <plugin>      Calls the given notification plugin with fake
                            notification data of a host notification.
    spoolfile <filename>    Reads the given spoolfile and creates a
                            notification out of its data

    replay N                Uses the N'th recent notification from the backlog
                            and sends it again, counting from 0.
""")


def do_notify(args):
    global notify_mode
    try:
        if not os.path.exists(notification_logdir):
            os.makedirs(notification_logdir)
        if not os.path.exists(notification_spooldir):
            os.makedirs(notification_spooldir)

        notify_mode = 'notify'
        if args:
            notify_mode = args[0]
            if notify_mode not in [ 'fake-service', 'fake-host', 'spoolfile', 'replay' ]:
                sys.stderr.write("ERROR: Invalid call to check_mk --notify.\n\n")
                notify_usage()
                sys.exit(1)

            if len(args) != 2 and notify_mode != "replay":
                sys.stderr.write("ERROR: need an argument to --notify %s.\n\n" % notify_mode)
                sys.exit(1)

            if notify_mode in ['fake-service', 'fake-host']:
                global fake_plugin, g_interactive
                fake_plugin = args[1]
                g_interactive = True

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

        if opt_keepalive:
            notify_keepalive()

        elif notify_mode == 'replay':
            context = notification_context_from_backlog(replay_nr)
            notify_notify(context)

        else:
            notify_notify(notification_context_from_env())

    except Exception, e:
        if g_interactive:
            raise
        crash_dir = var_dir + "/notify"
        if not os.path.exists(crash_dir):
            os.makedirs(crash_dir)
        file(crash_dir + "/crash.log", "a").write("CRASH (%s):\n%s\n" %
            (time.strftime("%Y-%m-%d %H:%M:%S"), format_exception()))


def notification_replay_backlog(nr):
    global notify_mode
    notify_mode = "replay"
    context = notification_context_from_backlog(nr)
    return notify_notify(context)

def notification_analyse_backlog(nr):
    global notify_mode
    notify_mode = "replay"
    context = notification_context_from_backlog(nr)
    return notify_notify(context, analyse=True)


def process_context(context, write_into_spoolfile, analyse=False):
    # TODO: Do spooling right here, not on a per-plugin base
    contact = contacts.get(context["CONTACTNAME"])

    # If we have not CONTACTNAME, then rule based notifictions are
    # enabled in the Core. We do we not simply check enable_rulebased_notifications?
    # -> Because the core needs are restart in order to reflect this while the
    #    notification mode of Check_MK not. There are thus situations where the
    #    setting of the core is different from our global variable. The core must
    #    have precedence in this situation!
    if not contact or contact == "check-mk-notify":
        return notify_rulebased(context, analyse=analyse)

    # Get notification settings for the contact in question - if available.
    method = "email"
    try:
        if contact:
            method = contact.get("notification_method")
        else:
            method = 'email'

        if type(method) == tuple and method[0] == 'flexible':
            notify_log("Preparing flexible notifications for %s" % context["CONTACTNAME"])
            if analyse:
                return 0
            else:
                return notify_flexible(context, method[1], write_into_spoolfile)
        else:
            notify_log("Sending plain email to %s" % context["CONTACTNAME"])
            if not analyse:
                return notify_via_email(context, write_into_spoolfile)

    except Exception, e:
        notify_log("ERROR: %s\n%s" % (e, format_exception()))
        sys.stderr.write("ERROR: %s\n" % e)
        if notification_log:
            sys.stderr.write("Details have been logged to %s.\n" % notification_log)
        sys.exit(2)

def store_notification_backlog(context):
    path = notification_logdir + "/backlog.mk"
    if not notification_backlog:
        if os.path.exists(path):
            os.remove(path)
        return

    try:
        backlog = eval(file(path).read())[:notification_backlog-1]
    except:
        backlog = []

    backlog = [ context ] + backlog
    file(path, "w").write("%r\n" % backlog)


def notification_context_from_backlog(nr):
    try:
        backlog = eval(file(notification_logdir + "/backlog.mk").read())
    except:
        backlog = []

    if nr < 0 or nr >= len(backlog):
        sys.stderr.write("No notification number %d in backlog.\n" % nr)
        sys.exit(2)

    notify_log("Replaying notification %d from backlog...\n" % nr)
    return backlog[nr]


def notification_context_from_env():
    # Information about notification is excpected in the
    # environment in variables with the prefix NOTIFY_
    return dict([
        (var[7:], value)
        for (var, value)
        in os.environ.items()
        if var.startswith("NOTIFY_")
            and not dead_nagios_variable(value) ])


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


def notify_notify(context, analyse=False):
    if not analyse:
        store_notification_backlog(context)

    if notification_logging >= 2:
        notify_log("----------------------------------------------------------------------")
    if analyse:
        notify_log("Analysing notification context with %s variables" % len(context))
    else:
        notify_log("Got notification context with %s variables" % len(context))

    # Add a few further helper variables
    context["MONITORING_HOST"] = socket.gethostname()
    if omd_root:
        context["OMD_ROOT"] = omd_root
        context["OMD_SITE"] = os.getenv("OMD_SITE", "")

    context["WHAT"] = context.get("SERVICEDESC") and "SERVICE" or "HOST"
    context["MAIL_COMMAND"] = notification_mail_command

    # The Check_MK Micro Core sends the MICROTIME and now
    # other time stamps
    if "MICROTIME" in context:
        microtime = int(context["MICROTIME"])
        timestamp = float(microtime) / 1000000.0
        broken = time.localtime(timestamp)
        context["DATE"] = time.strftime("%Y-%m-%d", broken)
        context["SHORTDATETIME"] = time.strftime("%Y-%m-%d %H:%M:%S", broken)
        context["LONGDATETIME"] = time.strftime("%a %b %d %H:%M:%S %Z %Y", broken)

    # Handle interactive calls
    if notify_mode == 'fake-service':
        set_fake_env('service', context)
    elif notify_mode == 'fake-host':
        set_fake_env('host', context)

    context['HOSTURL'] = '/check_mk/index.py?start_url=%s' % \
                        urlencode('view.py?view_name=hoststatus&host=%s' % context['HOSTNAME'])
    if context['WHAT'] == 'SERVICE':
        context['SERVICEURL'] = '/check_mk/index.py?start_url=%s' % \
                                    urlencode('view.py?view_name=service&host=%s&service=%s' %
                                                 (context['HOSTNAME'], context['SERVICEDESC']))

    if notify_mode in [ 'fake-service', 'fake-host' ]:
        sys.exit(call_notification_script(fake_plugin, [], context, True))

    if 'LASTHOSTSTATECHANGE' in context:
        context['LASTHOSTSTATECHANGE_REL'] = get_readable_rel_date(context['LASTHOSTSTATECHANGE'])
    if context['WHAT'] != 'HOST' and 'LASTSERVICESTATECHANGE' in context:
        context['LASTSERVICESTATECHANGE_REL'] = get_readable_rel_date(context['LASTSERVICESTATECHANGE'])

    # Rule based notifications enabled? We might need to complete a few macros
    contact = context.get("CONTACTNAME")
    if not contact or contact == "check-mk-notify":
        add_rulebased_macros(context)

    convert_context_to_unicode(context)

    if notification_logging >= 2:
        notify_log("Notification context:\n"
                   + "\n".join(["%s=%s" % v for v in sorted(context.items())]))

    if not context:
        sys.stderr.write("check_mk --notify expects context data in environment variables "
                         "that are prefixed with NOTIFY_\n")
        sys.exit(1)

    if notification_spool_to:
        # Create spoolfile
        target_site = "%s:%s" % notification_spool_to[0:2]
        create_spoolfile({"context": context, "forward": target_site})
        if not notification_spool_to[2]:
            return 0

    return process_context(context, notification_spooling, analyse=analyse)



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


def call_notification_script(plugin, parameters, context, write_into_spoolfile=False):

    # Enter context into environment
    os.putenv("NOTIFY_PARAMETERS", " ".join(parameters))
    for nr, value in enumerate(parameters):
        os.putenv("NOTIFY_PARAMETER_%d" % (nr + 1), value)
    os.putenv("NOTIFY_LOGDIR", notification_logdir)

    # Export complete context to have all vars in environment.
    # Existing vars are replaced, some already existing might remain
    for key in context:
        if context['WHAT'] == 'SERVICE' or 'SERVICE' not in key:
            os.putenv('NOTIFY_' + key, context[key].encode('utf-8'))

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
        exitcode = 2

    else:
        # Create spoolfile or actually call the plugin
        if write_into_spoolfile:
            create_spoolfile({"context": context, "plugin": plugin})
            exitcode = 0
        else:
            notify_log("     executing %s" % path)
            out = os.popen(path + " 2>&1 </dev/null")
            for line in out:
                notify_log("Output: %s" % line.rstrip())
            exitcode = out.close()
            if exitcode:
                notify_log("Plugin exited with code %d" % (exitcode >> 8))
            else:
                exitcode = 0

    # Clear environment again
    for key in context:
        if context['WHAT'] == 'SERVICE' or 'SERVICE' not in key:
            os.unsetenv('NOTIFY_' + key)
        os.unsetenv("NOTIFY_PARAMETERS")
        for nr, value in enumerate(parameters):
            os.unsetenv("NOTIFY_PARAMETER_%d" % (nr + 1))
        os.unsetenv("NOTIFY_LOGDIR")
    return exitcode

def notify_via_email(context, write_into_spoolfile):
    if write_into_spoolfile:
        notify_log("Spooled this notification.")
        create_spoolfile({"context": context})
        return 0

    notify_log(substitute_context(notification_log_template, context))

    if "SERVICEDESC" in context and context['SERVICEDESC'].strip():
        subject_t = notification_service_subject
        body_t = notification_service_body
    else:
        subject_t = notification_host_subject
        body_t = notification_host_body

    subject = substitute_context(subject_t, context)
    context["SUBJECT"] = subject
    body = substitute_context(notification_common_body + body_t, context)
    command = substitute_context(notification_mail_command, context)
    command_utf8 = command.encode("utf-8")
    notify_log(body)

    # Make sure that mail(x) is using UTF-8. Otherwise we cannot send notifications
    # with non-ASCII characters. Unfortunately we do not know whether C.UTF-8 is
    # available. If e.g. nail detects a non-Ascii character in the mail body and
    # the specified encoding is not available, it will silently not send the mail!
    # Our resultion in future: use /usr/sbin/sendmail directly.
    # Our resultion in the present: look with locale -a for an existing UTF encoding
    # and use that.
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

    if notification_logging >= 2:
        file(var_dir + "/notify/body.log", "w").write(body.encode("utf-8"))

    # Important: we must not output anything on stdout or stderr. Data of stdout
    # goes back into the socket to the CMC in keepalive mode and garbles the
    # handshake signal.
    if notification_logging >= 2:
        notify_log("Executing command: %s" % command)

    p = subprocess.Popen(command_utf8, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    stdout_txt, stderr_txt = p.communicate(body.encode("utf-8"))
    exitcode = p.returncode
    if exitcode != 0:
        notify_log("ERROR: could not deliver mail. Exit code of command is %r" % exitcode)
        for line in (stdout_txt + stderr_txt).splitlines():
            notify_log("mail: %s" % line.rstrip())


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
    contactname = data["context"]["CONTACTNAME"]
    target_dir = "%s/%s" % (notification_spooldir, contactname)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    file_path = "%s/%0.8f" % (target_dir, time.time())
    notify_log("Creating spoolfile: %s" % file_path)
    file(file_path,"w").write(pprint.pformat(data))

def handle_spoolfile(spoolfile):
    if os.path.exists(spoolfile):
        try:
            data = eval(file(spoolfile).read())
            if not "context" in data.keys():
                return 2
            return process_context(data["context"], False)
        except Exception, e:
            notify_log("ERROR %s\n%s" % (e, format_exception()))
            return 2
        return 0


#.
#   .--Keepalive-----------------------------------------------------------.
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
                    context = notification_context_from_string(data.rstrip('\n'))
                    notify_notify(context)
                except Exception, e:
                    if opt_debug:
                        raise
                    notify_log("ERROR %s\n%s" % (e, format_exception()))

                # Signal that we are ready for the next notification
                sys.stdout.write("*")
                sys.stdout.flush()

        except Exception, e:
            if opt_debug:
                raise
            notify_log("ERROR %s\n%s" % (e, format_exception()))


def notify_data_available():
    readable, writeable, exceptionable = select.select([0], [], [], None)
    return not not readable

def notification_context_from_string(data):
    # Context is line-by-line in g_notify_readahead_buffer
    context = {}
    try:
        for line in data.split('\n'):
            varname, value = line.strip().split("=", 1)
            context[varname] = value
    except Exception, e: # line without '=' ignored or alerted
        if opt_debug:
            raise
    return context



#.
#   .--Flexible------------------------------------------------------------.
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

def notify_flexible(context, notification_table, write_into_spoolfile):
    should_retry = False
    for entry in notification_table:
        plugin = entry["plugin"]
        notify_log("Plugin: %s" % plugin)

        if not should_notify(context, entry):
            continue

        if plugin is None:
            result = notify_via_email(context, write_into_spoolfile)
        else:
            result = call_notification_script(plugin, entry.get("parameters", []), context, write_into_spoolfile)
        if result == 1:
            should_retry = True

    # The exit_code is only relevant when processing spoolfiles
    if should_retry:
        return 1
    else:
        return 0

# may return
# 0  : everything fine   -> proceed
# 1  : currently not OK  -> try to process later on
# >=2: invalid           -> discard
def should_notify(context, entry):
    # Check disabling
    if entry.get("disabled"):
        notify_log("- Skipping: it is disabled for this user")
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
#   .--Rulebased-----------------------------------------------------------.
#   |            ____        _      _                        _             |
#   |           |  _ \ _   _| | ___| |__   __ _ ___  ___  __| |            |
#   |           | |_) | | | | |/ _ \ '_ \ / _` / __|/ _ \/ _` |            |
#   |           |  _ <| |_| | |  __/ |_) | (_| \__ \  __/ (_| |            |
#   |           |_| \_\\__,_|_|\___|_.__/ \__,_|___/\___|\__,_|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Logic for rule based notifications                                  |
#   '----------------------------------------------------------------------'

def notify_rulebased(context, analyse=False):
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

        why_not = rbn_match_rule(rule, context) # also checks disabling
        if why_not:
            notify_log(" -> does not match: %s" % why_not)
            rule_info.append(("miss", rule, why_not))
        else:
            notify_log(" -> matches!")
            num_rule_matches += 1
            contacts = rbn_rule_contacts(rule, context)
            plugin = rule["notify_plugin"]
            method = rule["notify_method"] # None: do cancel, [ str ]: plugin parameters
            bulk   = rule.get("bulk")

            if method == None: # cancelling
                for contact in contacts:
                    key = contact, plugin
                    if key in notifications:
                        locked, method, bulk = notifications[key]
                        if locked and "contact" in rule:
                            notify_log("   - cannot cancel notification of %s via %s: it is locked" % key)
                        else:
                            notify_log("   - cancelling notification of %s via %s" % key)
                            del notifications[key]
            else:
                for contact in contacts:
                    key = contact, plugin
                    if key in notifications:
                        locked, method, bulk = notifications[key]
                        if locked and "contact" in rule:
                            notify_log("   - cannot modify notification of %s via %s: it is locked" % key)
                            continue
                        notify_log("   - modifying notification of %s via %s" % key)
                    else:
                        notify_log("   - adding notification of %s via %s" % key)
                    # Hint: method is the list of plugin parameters in this case
                    notifications[key] = ( not rule.get("allow_disable"), method, bulk )

            rule_info.append(("match", rule, ""))

    plugin_info = []

    if not notifications:
        if num_rule_matches:
            notify_log("%d rules matched, but no notification has been created." % num_rule_matches)
        else:
            if notification_fallback_email and not analyse:
                notify_log("No rule matched, falling back to email to %s" % notification_fallback_email)
                contact = rbn_fake_email_contact(notification_fallback_email)
                rbn_add_contact_information(context, contact)
                call_notification_script("mail", [], context)

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
            notify_log("  * %s %s via %s, parameters: %s" % (verb, contact, plugin, ", ".join(params)))
            plugin_info.append((contact, plugin, params, bulk))
            try:
                rbn_add_contact_information(context, contact)
                if not analyse:
                    if bulk:
                        do_bulk_notify(contact, plugin, params, context, bulk)
                    else:
                        call_notification_script(plugin, params, context)
            except Exception, e:
                if opt_debug:
                    raise
                fe = format_exception()
                notify_log("    ERROR: %s" % e)
                notify_log(fe)

    analysis_info = rule_info, plugin_info
    return analysis_info

def add_rulebased_macros(context):
    # For the rule based notifications we need the list of contacts
    # an object has. The CMC does send this in the macro "CONTACTS"
    if "CONTACTS" not in context:
        context["CONTACTS"] = livestatus_fetch_contacts(context["HOSTNAME"], context.get("SERVICEDESC"))

    # Add a pseudo contact name. This is needed for the correct creation
    # of spool files. Spool files are created on a per-contact-base, as in classical
    # notifications the core sends out one individual notification per contact.
    # In the case of rule based notifications we do not make distinctions between
    # the various contacts.
    context["CONTACTNAME"] = "check-mk-notify"


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
        "name"  : email.split("@")[0],
        "alias" : "Explicit email adress " + email,
        "email" : email,
        "pager" : "",
    }


def rbn_add_contact_information(context, contact):
    if type(contact) == dict:
        for what in [ "name", "alias", "email", "pager" ]:
            context["CONTACT" + what.upper()] = contact.get(what, "")
            for key in contact.keys():
                if key[0] == '_':
                    context["CONTACT" + key.upper()] = contact[key]
    else:
        contact_dict = contacts.get(contact, { "name" : contact, "alias" : contact })
        rbn_add_contact_information(context, contact_dict)


def livestatus_fetch_contacts(host, service):
    if service:
        query = "GET services\nFilter: host_name = %s\nFilter: service_description = %s\nColumns: contacts\n" % (
            host, service)
    else:
        query = "GET hosts\nFilter: host_name = %s\nColumns: contacts\n" % host

    return livestatus_fetch_query(query).strip()



def rbn_match_rule(rule, context):
    if rule.get("disabled"):
        return "This rule is disabled"

    return \
        rbn_match_folder(rule, context)           or \
        rbn_match_hosttags(rule, context)         or \
        rbn_match_hosts(rule, context)            or \
        rbn_match_exclude_hosts(rule, context)    or \
        rbn_match_services(rule, context)         or \
        rbn_match_exclude_services(rule, context) or \
        rbn_match_plugin_output(rule, context)    or \
        rbn_match_checktype(rule, context)        or \
        rbn_match_timeperiod(rule)                or \
        rbn_match_escalation(rule, context)       or \
        rbn_match_servicelevel(rule, context)     or \
        rbn_match_host_event(rule, context)       or \
        rbn_match_service_event(rule, context)

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
            if "match_host_event" not in rule:
                return "This is a service notification, but the rule just matches host events"
            else:
                return # Let this be handled by match_service_event
        allowed_events = rule["match_host_event"]
        state          = context["HOSTSTATE"]
        last_state     = context["LASTHOSTSTATE"]
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
        last_state     = context["LASTSERVICESTATE"]
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

    if event not in allowed_events:
        return "Event type '%s' not handled by this rule. Allowed are: %s" % (
                event, ", ".join(allowed_events))



def rbn_rule_contacts(rule, context):
    contacts = set([])
    if rule.get("contact_object"):
        contacts.update(rbn_object_contacts(context))
    if rule.get("contact_all"):
        contacts.update(rbn_all_contacts())
    if rule.get("contact_all_with_email"):
        contacts.update(rbn_all_contacts(with_email=True))
    if "contact_users" in rule:
        contacts.update(rule["contact_users"])
    if "contact_groups" in rule:
        contacts.update(rbn_groups_contacts(rule["contact_groups"]))
    if "contact_emails" in rule:
        contacts.update(rbn_emails_contacts(rule["contact_emails"]))
    return contacts


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
#   .--Bulk-Notifications--------------------------------------------------.
#   |                         ____        _ _                              |
#   |                        | __ ) _   _| | | __                          |
#   |                        |  _ \| | | | | |/ /                          |
#   |                        | |_) | |_| | |   <                           |
#   |                        |____/ \__,_|_|_|\_\                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Store postponed bulk notifications for the delivery via the noti-   |
#   |  cation spooler (mknotifyd).                                         |
#   '----------------------------------------------------------------------'

def do_bulk_notify(contact, plugin, params, context, bulk):
    # First identify the bulk. The following elements identify it:
    # 1. contact
    # 2. plugin
    # 3. time horizon (interval) in seconds
    # 4. max bulked notifications
    # 5. elements specified in bulk["groupby"]
    # We first create a bulk path constructed as a tuple of strings.
    # Later we convert that to a unique directory name.
    # Note: if you have separate bulk rules with exactly the same
    # bulking options, then they will use the same bulk.

    what = context["WHAT"]
    bulk_path = (contact, plugin, str(bulk["interval"]), str(bulk["count"]))
    bulkby = bulk["groupby"]
    if "host" in bulkby:
        bulk_path += ("host", context["HOSTNAME"])
    elif "folder" in bulkby:
        bulk_path += ("folder", find_wato_folder(context))
    if "service" in bulkby:
        bulk_path += ("service", context.get("SERVICEDESC", ""))
    if "sl" in bulkby:
        sl = context.get(what + "_SL", "")
        bulk_path += ("sl", sl)
    if "check_type" in bulkby:
        command = context.get(what + "CHECKCOMMAND", "").split("!")[0]
        bulk_path += ("check_type", command)
    if "state" in bulkby:
        state = context.get(what + "STATE", "")
        bulk_path += ("state", state)

    notify_log("    --> storing for bulk notification %s" % "|".join(bulk_path))
    bulk_dirname = create_bulk_dirname(bulk_path)
    uuid = bulk_uuid()
    filename = bulk_dirname + "/" + uuid
    file(filename, "w").write("%r\n" % ((params, context),))
    notify_log("        - stored in %s" % filename)


def find_wato_folder(context):
    for tag in context.get("HOSTTAGS", "").split():
        if tag.startswith("/wato/"):
            return tag[6:].rstrip("/")
    return ""

def create_bulk_dirname(bulk_path):
    dirname = notification_bulkdir + "/" + bulk_path[0] + "/" + bulk_path[1] + "/"
    dirname += ",".join([b.replace("/", "\\") for b in bulk_path[2:]])
    if not os.path.exists(dirname):
        os.makedirs(dirname)
        notify_log("        - created bulk directory %s" % dirname)
    return dirname

def bulk_uuid():
    try:
        return file('/proc/sys/kernel/random/uuid').read().strip()
    except IOError:
        # On platforms where the above file does not exist we try to
        # use the python uuid module which seems to be a good fallback
        # for those systems. Well, if got python < 2.5 you are lost for now.
        import uuid
        return str(uuid.uuid4())


#.
#   .--Fake-Notify---------------------------------------------------------.
#   |        _____     _              _   _       _   _  __                |
#   |       |  ___|_ _| | _____      | \ | | ___ | |_(_)/ _|_   _          |
#   |       | |_ / _` | |/ / _ \_____|  \| |/ _ \| __| | |_| | | |         |
#   |       |  _| (_| |   <  __/_____| |\  | (_) | |_| |  _| |_| |         |
#   |       |_|  \__,_|_|\_\___|     |_| \_|\___/ \__|_|_|  \__, |         |
#   |                                                       |___/          |
#   +----------------------------------------------------------------------+
#   |  Creation of faked notifications for testing                         |
#   '----------------------------------------------------------------------'

g_interactive = False

def set_fake_env(ty, context):
    os.environ.update(fake_notification_vars[ty])
    context.update(dict([(k[7:], v) for (k, v) in fake_notification_vars[ty].items()]))

fake_notification_vars = {
  'host': {
    'NOTIFY_CONTACTEMAIL': 'lm@mathias-kettner.de',
    'NOTIFY_CONTACTNAME': 'lm',
    'NOTIFY_CONTACTPAGER': '',
    'NOTIFY_DATE': '2013-01-17',
    'NOTIFY_HOSTADDRESS': '127.0.0.1',
    'NOTIFY_HOSTALIAS': 'localhost',
    'NOTIFY_HOSTCHECKCOMMAND': 'check-mk-ping',
    'NOTIFY_HOSTDOWNTIME': '0',
    'NOTIFY_HOSTNAME': 'localhost',
    'NOTIFY_HOSTNOTIFICATIONNUMBER': '1',
    'NOTIFY_HOSTOUTPUT': 'Manually set to Down by lm',
    'NOTIFY_HOSTPERFDATA': '',
    'NOTIFY_HOSTPROBLEMID': '136',
    'NOTIFY_HOSTSTATE': 'DOWN',
    'NOTIFY_HOSTSTATEID': '1',
    'NOTIFY_HOSTTAGS': 'cmk-agent prod lan tcp wato /wato/',
    'NOTIFY_LASTHOSTSTATE': 'UP',
    'NOTIFY_LASTHOSTSTATECHANGE': '1358761208',
    'NOTIFY_LASTHOSTSTATECHANGE_REL': '0d 00:11:38',
    'NOTIFY_LOGDIR': '/omd/sites/event/var/check_mk/notify',
    'NOTIFY_LONGDATETIME': 'Thu Jan 17 15:28:13 CET 2013',
    'NOTIFY_LONGHOSTOUTPUT': '',
    'NOTIFY_NOTIFICATIONTYPE': 'PROBLEM',
    'NOTIFY_PARAMETERS': '',
    'NOTIFY_SHORTDATETIME': '2013-01-17 15:28:13',
    'NOTIFY_WHAT': 'HOST',
    'NOTIFY_OMD_ROOT': '/omd/sites/event',
    'NOTIFY_OMD_SITE': 'event',
    'NOTIFY_MAIL_COMMAND': 'mail -s \'$SUBJECT$\' \'$CONTACTEMAIL$\'',
  },
  'service': {
    'NOTIFY_CONTACTEMAIL': 'lm@mathias-kettner.de',
    'NOTIFY_CONTACTNAME': 'lm',
    'NOTIFY_CONTACTPAGER': '',
    'NOTIFY_DATE': '2013-01-17',
    'NOTIFY_HOSTADDRESS': '127.0.0.1',
    'NOTIFY_HOSTALIAS': 'localhost',
    'NOTIFY_HOSTCHECKCOMMAND': 'check-mk-ping',
    'NOTIFY_HOSTDOWNTIME': '0',
    'NOTIFY_HOSTNAME': 'localhost',
    'NOTIFY_HOSTNOTIFICATIONNUMBER': '0',
    'NOTIFY_HOSTOUTPUT': 'OK - 127.0.0.1: rta 0.028ms, lost 0%',
    'NOTIFY_HOSTPERFDATA': 'rta=0.028ms;200.000;500.000;0; pl=0%;40;80;; rtmax=0.052ms;;;; rtmin=0.021ms;;;;',
    'NOTIFY_HOSTPROBLEMID': '0',
    'NOTIFY_HOSTSTATE': 'UP',
    'NOTIFY_HOSTSTATEID': '0',
    'NOTIFY_HOSTTAGS': 'cmk-agent prod lan tcp wato /wato/',
    'NOTIFY_LASTHOSTSTATE': 'UP',
    'NOTIFY_LASTHOSTSTATECHANGE': '1358761208',
    'NOTIFY_LASTHOSTSTATECHANGE_REL': '0d 00:11:38',
    'NOTIFY_LASTSERVICESTATE': 'OK',
    'NOTIFY_LASTSERVICESTATECHANGE': '1358761208',
    'NOTIFY_LASTSERVICESTATECHANGE_REL': '0d 00:00:01',
    'NOTIFY_LOGDIR': '/omd/sites/event/var/check_mk/notify',
    'NOTIFY_LONGDATETIME': 'Thu Jan 17 15:31:46 CET 2013',
    'NOTIFY_LONGHOSTOUTPUT': '',
    'NOTIFY_LONGSERVICEOUTPUT': '',
    'NOTIFY_NOTIFICATIONTYPE': 'PROBLEM',
    'NOTIFY_PARAMETERS': '',
    'NOTIFY_SERVICECHECKCOMMAND': 'check_mk-cpu.loads',
    'NOTIFY_SERVICEDESC': 'CPU load',
    'NOTIFY_SERVICENOTIFICATIONNUMBER': '1',
    'NOTIFY_SERVICEOUTPUT': 'CRIT - 15min load 1.29 at 2 CPUs (critical at 0.00)',
    'NOTIFY_SERVICEPERFDATA': 'load1=1.35;0;0;0;2 load5=1.33;0;0;0;2 load15=1.29;0;0;0;2',
    'NOTIFY_SERVICEPROBLEMID': '137',
    'NOTIFY_SERVICESTATE': 'CRITICAL',
    'NOTIFY_SERVICESTATEID': '2',
    'NOTIFY_SHORTDATETIME': '2013-01-17 15:31:46',
    'NOTIFY_WHAT': 'SERVICE',
    'NOTIFY_OMD_ROOT': '/omd/sites/event',
    'NOTIFY_OMD_SITE': 'event',
    'NOTIFY_MAIL_COMMAND': 'mail -s \'$SUBJECT$\' \'$CONTACTEMAIL$\'',
  },
}


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


def livestatus_fetch_query(query):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(livestatus_unix_socket)
    sock.send(query)
    sock.shutdown(socket.SHUT_WR)
    response = sock.recv(10000000)
    sock.close()
    return response


def format_exception():
    import traceback, StringIO, sys
    txt = StringIO.StringIO()
    t, v, tb = sys.exc_info()
    traceback.print_exception(t, v, tb, None, txt)
    return txt.getvalue()


def substitute_context(template, context):
    # First replace all known variables
    for varname, value in context.items():
        template = template.replace('$'+varname+'$', value)

    # Remove the rest of the variables and make them empty
    template = re.sub("\$[A-Z]+\$", "", template)
    return template


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
    if g_interactive or notification_logging >= 1:
        formatted = (u"[%d] " % int(time.time())) + message + "\n"
        if g_interactive:
            sys.stdout.write(formatted.encode("utf-8"))
        else:
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

