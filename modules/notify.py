#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

# Default settings
notification_logdir = var_dir + "/notify"
notification_log = notification_logdir + "/notify.log"
notification_logging = 0
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

def substitute_context(template, context):
    # First replace all known variables
    for varname, value in context.items():
        template = template.replace('$'+varname+'$', value)

    # Remove the rest of the variables and make them empty
    template = re.sub("\$[A-Z]+\$", "", template)
    return template

def notify_log(message):
    if notification_logging >= 1:
        formatted = (u"[%d] " % int(time.time())) + message + "\n"
        file(notification_log, "a").write(formatted.encode("utf-8"))

def do_notify(args):
    try:
        if len(args) > 0:
            sys.stderr.write("check_mk --notify does not take any arguments.\n")
            sys.exit(1)

        if not os.path.exists(notification_logdir):
            os.makedirs(notification_logdir)

        # Hier müssen wir erstmal rausfinden, an wen die Notifikation gehen soll.
        # Das sollte hoffentlich als Env-Variable da sein. Wenn nicht in check_mk_templates.cfg
        # einbauen. Dann können wir in den Kontaktdefinitionen nachschauen. Diese sollten
        # ja in main.mk/conf.d vorhanden sein. Die neue Notifikationstabelle muss auf jeden
        # fall da rein. Für den Benutzer rufen also diese Tabelle auf. Wenn es die
        # nicht gibt (garkein Eintrag), verfahren wir nach dem alten Verfahren und
        # senden direkt eine Email. Wenn es die Tabelle aber gibt, werten wir
        # Zeile für Zeile aus:
        # - Bestimmen, ob die Zeile aktiv ist. Dazu ist evtl. eine Livestatus-Rückanfrage
        #   notwendig. Das ist nicht optimal, aber zumindest wegen der Timeperiods notwendig.
        # - Wenn aktiv, dann rufen wir das Plugin dazu auf. Dieses hat sich mit einer
        #   Python-Funktion registriert. Wo werden diese definiert? Im precompiled-Fall
        #   brauchen wir das *nicht*. Man könnte die Plugins also einfach nur bei --notify
        #   einlesen. Zeitkritisch ist das nicht sehr, denn Notifikationen sind selten.

        # Information about notification is excpected in the
        # environment in variables with the prefix NOTIFY_
        context = dict([
            (var[7:], value.decode("utf-8"))
            for (var, value)
            in os.environ.items()
            if var.startswith("NOTIFY_")
                and not re.match('^\$[A-Z]+\$$', value)])
    
        # Add a few further helper variables
        import socket
        context["MONITORING_HOST"] = socket.gethostname()
        if omd_root:
            context["OMD_ROOT"] = omd_root
            context["OMD_SITE"] = os.getenv("OMD_SITE", "")


        if notification_logging >= 2:
            notify_log("Notification context:\n"
                       + "\n".join(["%s=%s" % v for v in sorted(context.items())]))

        if not context:
            sys.stderr.write("check_mk --notify expects context data in environment variables "
                             "that are prefixed with NOTIFY_\n")
            sys.exit(1)

        # Get notification settings for the contact in question - if available.
        method = "email"
        contact = contacts.get(context["CONTACTNAME"])

        try:
            if contact:
                method = contact.get("notification_method")
            else:
                method = 'email'
            if type(method) == tuple and method[0] == 'flexible':
                notify_flexible(contact, context, method[1])
            else:
                notify_via_email(context)

        except Exception, e:
            notify_log("ERROR: %s\n%s" % (e, format_exception()))
            sys.stderr.write("ERROR: %s\n" % e)
            if notification_log:
                sys.stderr.write("Details have been logged to %s.\n" % notification_log)
            sys.exit(1)

    except Exception, e:
        crash_dir = var_dir + "/notify"
        if not os.path.exists(crash_dir):
            os.makedirs(crash_dir)
        file(crash_dir + "/crash.log", "a").write("CRASH:\n%s\n\n" % format_exception())


def notify_via_email(context):
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
    command = substitute_context(notification_mail_command, context)
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
    os.popen(command_utf8, "w").write(body.encode("utf-8"))


def notify_flexible(contact, context, notification_table):
    notify_log("Flexible notification for %s" % context["CONTACTNAME"])
    is_host = "SERVICEDESC" in context
    for entry in notification_table:
        plugin = entry["plugin"]
        notify_log("Plugin: %s" % plugin)

        # Check disabling
        if entry.get("disabled"):
            notify_log("- Skipping: it is disabled for this user")
            continue

        # Check service, if configured
        if entry.get("only_services"):
            servicedesc = context.get("SERVICEDESC")
            if not servicedesc:
                notify_log(" - Skipping: limited to certain services, but this is a host notification")
            for s in entry["only_services"]:
                if re.match(s, servicedesc):
                    break
            else:
                notify_log(" - Skipping: service '%s' matches non of %s" % (
                    servicedesc, ", ".join(entry["only_services"])))
                continue

        # Check notification type
        event, allowed_events = check_notification_type(context, entry["host_events"], entry["service_events"])
        if event not in allowed_events:
            notify_log(" - Skipping: wrong notification type %s, only %s are allowed" % 
                (event, ",".join(allowed_events)) )
            continue

        # Check notification number (in case of repeated notifications/escalations)
        if "escalation" in entry:
            from_number, to_number = entry["escalation"]
            if is_host:
                notification_number = int(context.get("HOSTNOTIFICATIONNUMBER", 1))
            else:
                notification_number = int(context.get("SERVICENOTIFICATIONNUMBER", 1))
            if notification_number < from_number or notification_number > to_number:
                notify_log(" - Skipping: notification number %d does not lie in range %d ... %d" %
                    (notification_number, from_number, to_number))
                continue

        if "timeperiod" in entry:
            timeperiod = entry["timeperiod"]
            if timeperiod and timeperiod != "24X7":
                if not check_timeperiod(timeperiod):
                    notify_log(" - Skipping: time period %s is currently not active" % timeperiod)
                    continue

        call_notification_script(plugin, entry.get("parameters", []))


def call_notification_script(plugin, parameters):
    # Prepare environment
    os.putenv("NOTIFY_PARAMETERS", " ".join(parameters))
    for nr, value in enumerate(parameters):
        os.putenv("NOTIFY_PARAMETER_%d" % (nr + 1), value)
    os.putenv("NOTIFY_LOGDIR", notification_logdir)

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
        return

    notify_log("Executing %s" % path)
    out = os.popen(path + " 2>&1 </dev/null")
    for line in out:
        notify_log("Output: %s" % line.rstrip())
    exitcode = out.close()
    if exitcode: 
        notify_log("Plugin exited with code %d" % (exitcode >> 8))




def check_notification_type(context, host_events, service_events):
    notification_type = context["NOTIFICATIONTYPE"]
    is_host = "SERVICEDESC" not in context
    if is_host:
        allowed_events = host_events
        state = context["HOSTSTATE"]
        events = { "UP" : 'u', "DOWN" : 'd' }
    else:
        allowed_events = service_events
        state = context["SERVICESTATE"]
        events = { "WARNING" : 'w', "CRITICAL" : 'c', "UNKNOWN" : 'u' }

    if notification_type == "PROBLEM":
        event = events[state]
    elif notification_type == "RECOVERY":
        event = 'r'
    elif notification_type in [ "FLAPPINGSTART", "FLAPPINGSTOP", "FLAPPINGDISABLED" ]: 
        event = 'f'
    elif notification_type in [ "DOWNTIMESTART", "DOWNTIMEEND", "DOWNTIMECANCELLED"]:
        event = 's'
    elif notification_type == "ACKNOWLEDGEMENT":
        event = 'x'
    else:
        event = '?'

    return event, allowed_events

def format_exception():
    import traceback, StringIO, sys
    txt = StringIO.StringIO()
    t, v, tb = sys.exc_info()
    traceback.print_exception(t, v, tb, None, txt)
    return txt.getvalue()
