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

# Configuration variables for the notification via cmk --notify

group = _("Notification")


register_configvar(group,
    "notification_logging",
    DropdownChoice(
        title = _("Debug notifications"),
        help = _("When notification debugging is on, then in the notification logfile "
                 "in <tt>%s</tt> additional information will be logged." %
                  (defaults.var_dir + "/notify/notify.log")),
        choices = [
            ( 0, _("No logging")),
            ( 1, _("One line per notification")),
            ( 2, _("Full dump of all variables and command"))]
        ),
    domain = "check_mk")

register_configvar(group,
    "notification_mail_command",
    TextUnicode(
        title = _("Email command line used for notifications"),
        help = _("This command will be executed whenever a notification should be done. "
                 "The command will receive the notification text body on standard input. "
                 "The macro <tt>$SUBJECT$</tt> will be replaced by a text configured "
                 "with "
                 "<a href=\"%s\"><tt>notification_host_subject</tt></a>"
                 " and "
                 "<a href=\"%s\"><tt>notification_service_subject</tt></a>. "
                 "You find a list of all remaining available variables in the help text of "
                 "<a href=\"%s\"><tt>notification_common_body</tt></a>." % (
                 "wato.py?mode=edit_configvar&varname=notification_host_subject",
                 "wato.py?mode=edit_configvar&varname=notification_service_subject",
                 "wato.py?mode=edit_configvar&varname=notification_common_body",
                 )),
        size = 50),
    domain = "check_mk")

register_configvar(group,
    "notification_host_subject",
    TextUnicode(
        title = _("Email subject to use for host notifications"),
        help = _("This template will be used as <tt>$SUBJECT$</tt> in email notifications "
                  "that deal with host alerts. The variable <tt>$SUBJECT$</tt> will then "
                  "be available in <a href=\"%s\"><tt>notification_common_body</tt></a>." % (
                 "wato.py?mode=edit_configvar&varname=notification_common_body",
                 )),
        size = 50),
    domain = "check_mk")

register_configvar(group,
    "notification_service_subject",
    TextUnicode(
        title = _("Email subject to use for service notifications"),
        help = _("This template will be used as <tt>$SUBJECT$</tt> in email notifications "
                  "that deal with service alerts. The variable <tt>$SUBJECT$</tt> will then "
                  "be available in <a href=\"%s\"><tt>notification_common_body</tt></a>." % (
                 "wato.py?mode=edit_configvar&varname=notification_common_body",
                 )),
        size = 50),
    domain = "check_mk")


register_configvar(group,
    "notification_common_body",
    TextAreaUnicode(
        title = _("Email body to use for both host and service notifications"),
        help = _("This template will be used as email body when sending notifications. "
                  "Appended to it will be a specific body for either host or service "
                  "notifications configured in two extra parameters. "
                  "The following macros are available in all templates:<br><br>"
                  "<tt><b>$CONTACTNAME$</b></tt>: login name of the contact person, "
                  "<tt><b>$CONTACTEMAIL$</b></tt>: email address of the contact person, "
                  "<tt><b>$CONTACTPAGER$</b></tt>: pager address of the contact person, "
                  "<tt><b>$NOTIFICATIONTYPE$</b></tt>: one of PROBLEM, RECOVERY, ACKNOWLEDGEMENT, FLAPPINGSTART, FLAPPINGSTOP, FLAPPINGDISABLED, DOWNTIMESTART, DOWNTIMEEND, or DOWNTIMECANCELLED, "
                  "<tt><b>$HOSTNAME$</b></tt>: the name of the host, "
                  "<tt><b>$HOSTALIAS$</b></tt>: the alias of the host, "
                  "<tt><b>$HOSTADDRESS$</b></tt>: the IP address or DNS name of the host, "
                  "<tt><b>$LASTHOSTSTATE$</b></tt>: the previous state of the host, "
                  "<tt><b>$HOSTSTATE$</b></tt>: the new state of the host, "
                  "<tt><b>$HOSTCHECKCOMMAND$</b></tt>: the name of the host check command, "
                  "<tt><b>$HOSTOUTPUT$</b></tt>: the output of the host check command, "
                  "<tt><b>$LONGHOSTOUTPUT$</b></tt>: the long output of the host check, "
                  "<tt><b>$HOSTPERFDATA$</b></tt>: the performance data of the host check, "
                  "<tt><b>$SERVICEDESC$</b></tt>: the name of the service, "
                  "<tt><b>$LASTSERVICESTATE$</b></tt>: the previous state of the service, "
                  "<tt><b>$SERVICESTATE$</b></tt>: the new state of the service, "
                  "<tt><b>$SERVICEOUTPUT$</b></tt>: the output of the check command , "
                  "<tt><b>$LONGSERVICEOUTPUT$</b></tt>: the long output of the check command, "
                  "<tt><b>$SERVICEPERFDATA$</b></tt>: the performance data of the check, "
                  "<tt><b>$SERVICECHECKCOMMAND$</b></tt>: the name of the service check command, "
                  "<tt><b>$HOSTPROBLEMID$</b></tt>: a unique ID of the host problem this notification is about, "
                  "<tt><b>$SERVICEPROBLEMID$</b></tt>: the same for service problems, "
                  "<tt><b>$HOSTNOTIFICATIONNUMBER$</b></tt>: the number of notification of this host problem (begins with 1), "
                  "<tt><b>$HOSTURL$</b></tt>: URL pointing to the host detail view (starting with /check_mk/...), "
                  "<tt><b>$SERVICEURL$</b></tt>: URL pointing to the service detail view (starting with /check_mk/...), "
                  "<br><br>"
                  "<tt><b>$MONITORING_HOST$</b></tt>: the host name of the monitoring server "
                  "<tt><b>$OMD_ROOT$</b></tt>: the home directory of the OMD site (only on OMD) "
                  "<tt><b>$OMD_SITE$</b></tt>: the name of the OMD site (only on OMD) "
                 ),
    ),
    domain = "check_mk")


register_configvar(group,
    "notification_host_body",
    TextAreaUnicode(
        title = _("Email body to use for host notifications"),
        help = _("This template will be appended to the <a href=\"%s\"><tt>"
                  "notification_common_body</tt></a> when host notifications are sent." %
                  "wato.py?mode=edit_configvar&varname=notification_common_body"
                 ),
    ),
    domain = "check_mk")

register_configvar(group,
    "notification_service_body",
    TextAreaUnicode(
        title = _("Email body to use for service notifications"),
        help = _("This template will be appended to the <a href=\"%s\"><tt>"
                  "notification_common_body</tt></a> when service notifications are sent." %
                  "wato.py?mode=edit_configvar&varname=notification_common_body"
                 ),
    ),
    domain = "check_mk")
