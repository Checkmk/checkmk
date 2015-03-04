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

# Configuration variables for the notification via cmk --notify

# TODO: Remove all configuration for legacy-Email to deprecated, or completely
# remove from WATO.

group = _("Notification")

register_configvar(group,
    "enable_rulebased_notifications",
    Checkbox(
        title = _("Rule based notifications"),
        label = _("Enable new rule based notifications"),
        help = _("If you enable the new rule based notifications then the current plain text email and "
                 "&quot;flexible notifications&quot; will become inactive. Instead notificatios will "
                 "be configured with the WATO module <i>Notifications</i> on a global base."),
        default_value = False,
    ),
    domain = "check_mk",
    need_restart = True)

register_configvar(group,
    "notification_fallback_email",
    EmailAddress(
        title = _("Fallback email address for rule based notifications"),
        help = _("If you work with rule based notifications then you should configure an email "
                 "address here. In case of a hole in your notification rules a notification "
                 "will be sent to this address. This makes sure that in any case <i>someone</i> gets "
                 "notified."),
        empty_text = _("<i>(No fallback email address configured!)</i>"),
        make_clickable = False,
   ),
   domain = "check_mk")

register_configvar(group,
    "notification_backlog",
    Integer(
        title = _("Store notifications for rule analysis"),
        help = _("If this option is set to a non-zero number, then Check_MK "
                 "keeps the last <i>X</i> notifications for later reference. "
                 "You can replay these notifications and analyse your set of "
                 "notifications rules. This only works with rulebased notiications. Note: "
                 "only notifications sent out by the local notification system can be "
                 "tracked. If you have a distributed environment you need to do the analysis "
                 "directly on the remote sites - unless you use a central spooling."),
        default_value = 10,
    ),
    domain = "check_mk")

register_configvar(group,
    "notification_bulk_interval",
    Age(
        title = _("Interval for checking for ripe bulk notifications"),
        help = _("If you are using rule based notifications with and <i>Bulk Notifications</i> "
                 "then Check_MK will check for ripe notification bulks to be sent out "
                 "at latest every this interval."),
        default_value = 10,
        minvalue = 1,
    ),
    domain = "check_mk",
    need_restart = True)

register_configvar(group,
    "notification_logging",
    Transform(
        DropdownChoice(
            choices = [
                ( 1, _("Normal logging")),
                ( 2, _("Full dump of all variables and command"))
            ],
            default_value = 1,
        ),
        forth = lambda x: x == 0 and 1 or x, # transform deprecated value 0 (no logging) to 1
        title = _("Notification log level"),
        help = _("You can configure the notification mechanism to log more details about "
                 "the notifications into the notification log. These information are logged "
                 "into the file <tt>%s</tt>") % site_neutral_path(defaults.log_dir + "/notify.log"),
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
        size = 50,
        attrencode = True,
    ),
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
        size = 50,
        attrencode = True,
    ),
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
        size = 50,
        attrencode = True,
    ),
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
        attrencode = True,
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
        attrencode = True,
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
        attrencode = True,
    ),
    domain = "check_mk")


register_configvar(group,
    "mkeventd_service_levels",
    ListOf(
        Tuple(
            elements = [
                Integer(
                    title = _("internal ID"),
                    minvalue = 0,
                    maxvalue = 100,
                ),
                TextUnicode(
                    title = _("Name / Description"),
                    allow_empty = False,
                    attrencode = True,
                ),
            ],
            orientation = "horizontal",
        ),
        title = _("Service Levels"),
        help = _("Here you can configure the list of possible service levels for hosts, services and "
                 "events. A service level can be assigned to a host or service by configuration. "
                 "The event console can configure each created event to have a specific service level. "
                 "Internally the level is represented as an integer number. Note: a higher number represents "
                 "a higher service level. This is important when filtering views "
                 "by the service level.<p>You can also attach service levels to hosts "
                 "and services in the monitoring. These levels will then be sent to the "
                 "Event Console when you forward notifications to it and will override the "
                 "setting of the matching rule."),
        allow_empty = False,
        default_value = [
                (0,  _("(no Service level)")),
                (10, _("Silver")),
                (20, _("Gold")),
                (30, _("Platinum")),
        ],
    ),
    domain = "multisite",
    allow_reset = False,
)

