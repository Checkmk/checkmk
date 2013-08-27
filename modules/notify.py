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

import pprint, urllib, select

# Default settings
notification_logdir   = var_dir + "/notify"
notification_spooldir = var_dir + "/notify/spool"
notification_log = notification_logdir + "/notify.log"
notification_logging    = 0

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

test_vars = {
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

g_interactive = False

def set_fake_env(ty, context):
    os.environ.update(test_vars[ty])
    context.update(dict([(k[7:], v) for (k, v) in test_vars[ty].items()]))

def substitute_context(template, context):
    # First replace all known variables
    for varname, value in context.items():
        template = template.replace('$'+varname+'$', value)

    # Remove the rest of the variables and make them empty
    template = re.sub("\$[A-Z]+\$", "", template)
    return template

def notify_log(message):
    if g_interactive or notification_logging >= 1:
        formatted = (u"[%d] " % int(time.time())) + message + "\n"
        if g_interactive:
            sys.stdout.write(formatted.encode("utf-8"))
        else:
            file(notification_log, "a").write(formatted.encode("utf-8"))

def notify_usage():
    sys.stderr.write("""Usage: check_mk --notify [--keepalive]
       check_mk --notify fake-service <plugin>
       check_mk --notify fake-host <plugin>
       check_mk --notify spoolfile <filename>

Normally the notify module is called without arguments to send real
notification. But there are situations where this module is called with
COMMANDS to e.g. support development of notification plugins.

Available commands:
    fake-service <plugin>       ... Calls the given notification plugin with fake
                                    notification data of a service notification.
    fake-host <plugin>          ... Calls the given notification plugin with fake
                                    notification data of a host notification.
    spoolfile <filename>        ... Reads the given spoolfile and creates a
                                    notification out of its data
""")


def create_spoolfile(data):
    contactname = data["context"]["CONTACTNAME"]
    target_dir = "%s/%s" % (notification_spooldir, contactname)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    file_path = "%s/%0.8f" % (target_dir, time.time())
    notify_log("Creating spoolfile: %s" % file_path)
    file(file_path,"w").write(pprint.pformat(data))

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

def process_context(context, write_into_spoolfile, use_method = None):
    # Get notification settings for the contact in question - if available.
    method = "email"
    contact = contacts.get(context["CONTACTNAME"])
    try:
        if contact:
            method = contact.get("notification_method")
        else:
            method = 'email'

        if use_method:
            if use_method == "email":
                method = "email"
            elif method == "email":
                # We are searching for a specific
                # but this contact does not offer any
                notify_log("ERROR: contact %r do not have any plugins (required: %s)" % (contact, use_method))
                return 2
            else:
                found_plugin = {}
                for item in method[1]:
                    if item["plugin"] == use_method:
                        found_plugin = item
                        break
                if not found_plugin:
                    # Required plugin was not found for this contact
                    notify_log("ERROR: contact %r do not have plugin %s" % (contact, use_method))
                    return 2
                method = ('flexible', [found_plugin])

        if type(method) == tuple and method[0] == 'flexible':
            return notify_flexible(context, method[1], write_into_spoolfile)
        else:
            return notify_via_email(context, write_into_spoolfile)
    except Exception, e:
        notify_log("ERROR: %s\n%s" % (e, format_exception()))
        sys.stderr.write("ERROR: %s\n" % e)
        if notification_log:
            sys.stderr.write("Details have been logged to %s.\n" % notification_log)
        sys.exit(2)

def urlencode(s):
    return urllib.quote(s)

def do_notify(args):
    global notify_mode
    try:
        notify_mode = 'notify'
        if args:
            if len(args) != 2 or args[0] not in ['fake-service', 'fake-host', 'spoolfile']:
                sys.stderr.write("ERROR: Invalid call to check_mk --notify.\n\n")
                notify_usage()
                sys.exit(1)

            notify_mode, argument = args
            if notify_mode in ['fake-service', 'fake-host']:
                plugin = argument
            if notify_mode in ['spoolfile']:
               filename = argument

            if notify_mode in ['fake-service', 'fake-host']:
                global g_interactive
                g_interactive = True

        if not os.path.exists(notification_logdir):
            os.makedirs(notification_logdir)
        if not os.path.exists(notification_spooldir):
            os.makedirs(notification_spooldir)

        # If the notify_mode is set to 'spoolfile' we try to parse the given spoolfile
        # This spoolfile contains a python dictionary
        # { context: { Dictionary of environment variables }, plugin: "Plugin name" }
        # Any problems while reading the spoolfile results in returning 2
        # -> mknotifyd deletes this file
        if notify_mode == "spoolfile":
            return handle_spoolfile(filename)

        if opt_keepalive:
            notify_keepalive()

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


def notify_data_available():
    readable, writeable, exceptionable = select.select([0], [], [], None)
    return not not readable

def notify_config_timestamp():
    mtime = 0
    for dirpath, dirnames, filenames in os.walk(check_mk_configdir):
        for f in filenames:
            mtime = max(mtime, os.stat(dirpath + "/" + f).st_mtime)
    mtime = max(mtime, os.stat(default_config_dir + "/main.mk").st_mtime)
    try:
        mtime = max(mtime, os.stat(default_config_dir + "/final.mk").st_mtime)
    except:
        pass
    try:
        mtime = max(mtime, os.stat(default_config_dir + "/local.mk").st_mtime)
    except:
        pass
    return mtime



def notify_keepalive():
    config_timestamp = notify_config_timestamp()

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

            # If the configuration has changed, we do a restart. But we do
            # this check just before the next notification arrives. We must
            # *not* read data from stdin, just peek! There is still one
            # problem: when restarting we must *not* send the initial '*'
            # byte, because that must be not no sooner then the notification
            # has been sent. We do this by setting the environment variable
            # CMK_NOTIFY_RESTART=1

            if notify_data_available():
                current_config_timestamp = notify_config_timestamp()
                if current_config_timestamp > config_timestamp:
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

def notification_context_from_env():
    # Information about notification is excpected in the
    # environment in variables with the prefix NOTIFY_
    return dict([
        (var[7:], value)
        for (var, value)
        in os.environ.items()
        if var.startswith("NOTIFY_")
            and not dead_nagios_variable(value) ])

def dead_nagios_variable(value):
    if len(value) < 3:
        return False
    if value[0] != '$' or value[-1] != '$':
        return False
    for c in value[1:-1]:
        if not c.isupper() and c != '_':
            return False
    return True


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

def notify_notify(context):
    notify_log("Got notification context with %s variables" % len(context))

    # Add a few further helper variables
    import socket
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
        sys.exit(call_notification_script(plugin, [], context, True))

    if 'LASTHOSTSTATECHANGE' in context:
        context['LASTHOSTSTATECHANGE_REL'] = get_readable_rel_date(context['LASTHOSTSTATECHANGE'])
    if context['WHAT'] != 'HOST' and 'LASTSERVICESTATECHANGE' in context:
        context['LASTSERVICESTATECHANGE_REL'] = get_readable_rel_date(context['LASTSERVICESTATECHANGE'])

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

    process_context(context, notification_spooling)


def notify_via_email(context, write_into_spoolfile):
    if write_into_spoolfile:
        create_spoolfile({"context": context})
        return 0

    notify_log(substitute_context(notification_log_template, context))

    if "SERVICEDESC" in context:
        subject_t = notification_service_subject
        body_t = notification_service_body
    else:
        subject_t = notification_host_subject
        body_t = notification_host_body

    subject = substitute_context(subject_t, context)
    context["SUBJECT"] = subject
    body = substitute_context(notification_common_body + body_t, context)
    command = substitute_context(notification_mail_command, context) + " >/dev/null 2>&1"
    command_utf8 = command.encode("utf-8")
    if notification_logging >= 2:
        notify_log("Executing command: %s" % command)
    notify_log(body)
    # Make sure that mail(x) is using UTF-8. More then
    # setting the locale cannot be done here. We hope that
    # C.UTF-8 is always available. Please check the output
    # of 'locale -a' on your system if you are curious.
    os.putenv("LANG", "C.UTF-8")
    if notification_logging >= 2:
        file(var_dir + "/notify/body.log", "w").write(body.encode("utf-8"))

    # Important: we must not output anything on stdout or stderr. Data of stdout
    # goes back into the socket to the CMC in keepalive mode and garbles the
    # handshake signal.
    return os.popen(command_utf8, "w").write(body.encode("utf-8"))




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
        if hostname not in entry["only_hosts"]:
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



def call_notification_script(plugin, parameters, context, write_into_spoolfile):
    # Prepare environment
    os.putenv("NOTIFY_PARAMETERS", " ".join(parameters))
    for nr, value in enumerate(parameters):
        os.putenv("NOTIFY_PARAMETER_%d" % (nr + 1), value)
    os.putenv("NOTIFY_LOGDIR", notification_logdir)

    # Export complete context to have all vars in environment.
    # Existing vars are replaced, some already existing might remain
    for key in context:
        os.putenv('NOTIFY_' + key, context[key].encode('utf-8'))

    # Remove service macros for host notifications
    if context['WHAT'] == 'HOST':
        for key in context.keys():
            if 'SERVICE' in key:
                os.unsetenv('NOTIFY_%s' % key)

    # Remove exceeding arguments from previous plugin calls
    for nr in range(len(parameters)+1, 101):
        name = "NOTIFY_PARAMETER_%d" % nr
        if name in os.environ:
            os.putenv(name, "")

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
        return 2

    # Create spoolfile or actually call the plugin
    if write_into_spoolfile:
        create_spoolfile({"context": context, "plugin": plugin})
    else:
        notify_log("Executing %s" % path)
        out = os.popen(path + " 2>&1 </dev/null")
        for line in out:
            notify_log("Output: %s" % line.rstrip())
        exitcode = out.close()
        if exitcode:
            notify_log("Plugin exited with code %d" % (exitcode >> 8))
            return exitcode
    return 0


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

def format_exception():
    import traceback, StringIO, sys
    txt = StringIO.StringIO()
    t, v, tb = sys.exc_info()
    traceback.print_exception(t, v, tb, None, txt)
    return txt.getvalue()
