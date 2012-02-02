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
notification_log = var_dir + "/notify/notify.log"
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

notification_host_body = u"""State:    $LASTHOSTSTATE$ -> $HOSTSTATE$
Command:  $HOSTCHECKCOMMAND$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
"""

notification_service_body = u"""Service:  $SERVICEDESC$
State:    $LASTSERVICESTATE$ -> $SERVICESTATE$
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
        dir = os.path.dirname(notification_log)
        if not os.path.exists(dir):
            os.makedirs(dir)
        formatted = (u"[%d] " % int(time.time())) + message + "\n"
        file(notification_log, "a").write(formatted.encode("utf-8"))

def do_notify(args):
    try:
        if len(args) > 0:
            sys.stderr.write("check_mk --notify does not take any arguments.\n")
            sys.exit(1)

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

        try:
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

def format_exception():
    import traceback, StringIO, sys
    txt = StringIO.StringIO()
    t, v, tb = sys.exc_info()
    traceback.print_exception(t, v, tb, None, txt)
    return txt.getvalue()
