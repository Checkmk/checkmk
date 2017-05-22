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

def html_email_parameter_elements():
    elements = [
        ( "from",
            TextAscii(
                title = _("From: Address"),
                size = 40,
                allow_empty = False,
            )
        ),
        ( "reply_to",
            TextAscii(
                title = _("Reply-To: Address"),
                size = 40,
                allow_empty = False,
            )
        ),
        ( "host_subject",
            TextUnicode(
                title = _("Subject for host notifications"),
                help = _("Here you are allowed to use all macros that are defined in the "
                         "notification context."),
                default_value = "Check_MK: $HOSTNAME$ - $EVENT_TXT$",
                size = 64,
            )
        ),
        ( "service_subject",
            TextUnicode(
                title = _("Subject for service notifications"),
                help = _("Here you are allowed to use all macros that are defined in the "
                         "notification context."),
                default_value = "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
                size = 64,
            )
        ),
        ( "elements",
            ListChoice(
                title = _("Information to be displayed in the email body"),
                choices = [
                  ( "address",      _("IP Address of Host") ),
                  ( "abstime",      _("Absolute Time of Alert") ),
                  ( "reltime",      _("Relative Time of Alert") ),
                  ( "longoutput",   _("Additional Plugin Output") ),
                  ( "ack_author",   _("Acknowledgement Author") ),
                  ( "ack_comment",  _("Acknowledgement Comment") ),
                  ( "perfdata",     _("Performance Data") ),
                  ( "graph",        _("Performance Graphs") ),
                  ( "notesurl",     _("Custom Host/Service Notes URL") ),
                  ( "context",      _("Complete variable list (for testing)" ) ),
                ],
                default_value = [ "perfdata", "graph", "abstime", "address", "longoutput" ],
            )
        ),
        ( "insert_html_section",
            TextAreaUnicode(
                title = _("Insert HTML section between body and table"),
                default_value = "<HTMLTAG>CONTENT</HTMLTAG>",
                cols = 40,
                rows = "auto",
            ),
        ),
        ( "url_prefix",
            TextAscii(
                title = _("URL prefix for links to Check_MK"),
                help = _("If you specify an URL prefix here, then several parts of the "
                         "email body are armed with hyperlinks to your Check_MK GUI, so "
                         "that the recipient of the email can directly visit the host or "
                         "service in question in Check_MK. Specify an absolute URL including "
                         "the <tt>.../check_mk/</tt>"),
                regex = "^(http|https)://.*/check_mk/$",
                regex_error = _("The URL must begin with <tt>http</tt> or "
                                "<tt>https</tt> and end with <tt>/check_mk/</tt>."),
                size = 64,
                default_value = "http://" + socket.gethostname() + "/" + (
                    config.omd_site() and config.omd_site() + "/" or "") + "check_mk/",
            )
        ),
        ( "no_floating_graphs",
            FixedValue(
                True,
                title = _("Display graphs among each other"),
                totext = _("Graphs are shown among each other"),
                help = _("By default all multiple graphs in emails are displayed floating "
                         "nearby. You can enable this option to show the graphs among each "
                         "other."),
            )
        ),
        ('bulk_sort_order',
            DropdownChoice(
                choices = [
                    ('oldest_first', _('Oldest first')),
                    ('newest_first', _('Newest first')),
                ],
                help = _("With this option you can specify, whether the oldest (default) or "
                         "the newest notification should get shown at the top of the notification mail."),
                title = _("Notification sort order for bulk notifications"),
                default = "oldest_first"
            )
        ),
        ]

    try:
        return elements + cee_html_mail_smtp_sync_option
    except NameError:
        return elements


register_notification_parameters(
    "mail",
    Dictionary(
        elements = html_email_parameter_elements, # must be called at run time!!
    )
)


register_notification_parameters(
    "asciimail",
    Dictionary(
        elements = [
            ( "from",
                EmailAddress(
                    title = _("From: Address"),
                    size = 40,
                    allow_empty = False,
                )
            ),
            ( "reply_to",
                EmailAddress(
                    title = _("Reply-To: Address"),
                    size = 40,
                    allow_empty = False,
                )
            ),
            ( "host_subject",
                TextUnicode(
                    title = _("Subject for host notifications"),
                    help = _("Here you are allowed to use all macros that are defined in the "
                             "notification context."),
                    default_value = "Check_MK: $HOSTNAME$ - $EVENT_TXT$",
                    size = 64,
                )
            ),
            ( "service_subject",
                TextUnicode(
                    title = _("Subject for service notifications"),
                    help = _("Here you are allowed to use all macros that are defined in the "
                             "notification context."),
                    default_value = "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
                    size = 64,
                )
            ),
            ( "common_body",
                TextAreaUnicode(
                    title = _("Body head for both host and service notifications"),
                    rows = 7,
                    cols = 58,
                    monospaced = True,
                    default_value =
"""Host:     $HOSTNAME$
Alias:    $HOSTALIAS$
Address:  $HOSTADDRESS$
""",
                )
            ),
            ( "host_body",
                TextAreaUnicode(
                    title = _("Body tail for host notifications"),
                    rows = 9,
                    cols = 58,
                    monospaced = True,
                    default_value =
"""Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
""",
                )
            ),
            ( "service_body",
                TextAreaUnicode(
                    title = _("Body tail for service notifications"),
                    rows = 11,
                    cols = 58,
                    monospaced = True,
                    default_value =
"""Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
""",
                )
            ),
            ('bulk_sort_order',
                DropdownChoice(
                    choices = [
                        ('oldest_first', _('Oldest first')),
                        ('newest_first', _('Newest first')),
                    ],
                    help = _("With this option you can specify, whether the oldest (default) or "
                             "the newest notification should get shown at the top of the notification mail."),
                    title = _("Notification sort order for bulk notifications"),
                    default = "oldest_first"
                )
            )
        ]
    )
)

register_notification_parameters(
    "mkeventd",
    Dictionary(
        elements = [
            ( "facility",
                DropdownChoice(
                    title = _("Syslog Facility to use"),
                    help = _("The notifications will be converted into syslog messages with "
                             "the facility that you choose here. In the Event Console you can "
                             "later create a rule matching this facility."),
                    choices = syslog_facilities,
                )
            ),
            ( "remote",
                IPv4Address(
                    title = _("IP Address of remote Event Console"),
                    help = _("If you set this parameter then the notifications will be sent via "
                             "syslog/UDP (port 514) to a remote Event Console or syslog server."),
                )
            ),
        ]
    )
)

register_notification_parameters(
    "spectrum",
    Dictionary(
        optional_keys = None,
        elements = [
            ( "destination",
                IPv4Address(
                    title = _("Destination IP"),
                    help = _("IP Address of the Spectrum server receiving the SNMP trap")
                ),
            ),
            ( "community",
                Password(
                    title = _("SNMP Community"),
                    help = _("SNMP Community for the SNMP trap")
                )
            ),
            ( "baseoid",
                TextAscii(
                    title = _("Base OID"),
                    help = _("The base OID for the trap content"),
                    default_value = "1.3.6.1.4.1.1234"
                ),
            ),
        ]
    )
)

# We have to transform because 'add_to_event_context'
# in modules/events.py can't handle complex data structures
def transform_back_pushover_priority(params):
    if type(params) == tuple:
        return {"priority" : "2",
                "retry"    : params[1][0],
                "expire"   : params[1][1],
                "receipts" : params[1][2]}
    return params

def transform_forth_pushover_priority(params):
    if type(params) == dict:
        return (params['priority'], (params["retry"], params["expire"], params["receipts"]))
    return params

register_notification_parameters("pushover", Dictionary(
    optional_keys = ["url_prefix", "proxy_url", "priority", "sound"],
    elements = [
        ("api_key", TextAscii(
            title = _("API Key"),
            help = _("You need to provide a valid API key to be able to send push notifications "
                     "using Pushover. Register and login to <a href=\"https://www.pushover.net\" "
                     "target=\"_blank\">Pushover</a>, thn create your Check_MK installation as "
                     "application and obtain your API key."),
            size = 40,
            allow_empty = False,
            regex = "[a-zA-Z0-9]{30}",
        )),
        ("recipient_key", TextAscii(
            title = _("User / Group Key"),
            help = _("Configure the user or group to receive the notifications by providing "
                     "the user or group key here. The key can be obtained from the Pushover "
                     "website."),
            size = 40,
            allow_empty = False,
            regex = "[a-zA-Z0-9]{30}",
        )),
        ("url_prefix", TextAscii(
              title = _("URL prefix for links to Check_MK"),
              help = _("If you specify an URL prefix here, then several parts of the "
                       "email body are armed with hyperlinks to your Check_MK GUI, so "
                       "that the recipient of the email can directly visit the host or "
                       "service in question in Check_MK. Specify an absolute URL including "
                       "the <tt>.../check_mk/</tt>"),
              regex = "^(http|https)://.*/check_mk/$",
              regex_error = _("The URL must begin with <tt>http</tt> or "
                              "<tt>https</tt> and end with <tt>/check_mk/</tt>."),
              size = 64,
              default_value = "http://" + socket.gethostname() + "/" + (
                      config.omd_site() and config.omd_site() + "/" or "") + "check_mk/",
        )),
        ("proxy_url", TextAscii(
            title       = _("Proxy-URL"),
            size        = 64,
            regex       = "^(http|https)://.*",
            regex_error = _("The URL must begin with <tt>http</tt> or <tt>https</tt>."),
        )),
        ("priority", Transform(
            CascadingDropdown(
                title = _("Priority"),
                choices = [
                    ("2",  _("Emergency: Repeat push notification in intervalls till expire time."),
                        Tuple(elements = [
                            Age(title = _("Retry time")),
                            Age(title = _("Expire time")),
                            TextAscii(
                                title = _("Receipt"),
                                help  = _("The receipt can be used to periodically poll receipts API to get "
                                          "the status of the notification. "
                                          "See <a href=\"https://pushover.net/api#receipt\" target=\"_blank\">"
                                          "Pushover receipts and callbacks</a> for more information."),
                                size  = 40,
                                regex = "[a-zA-Z0-9]{0,30}"),
                        ]),
                    ),
                    ("1",  _("High: Push notification alerts bypass quiet hours")),
                    ("0",  _("Normal: Regular push notification (default)")),
                    ("-1", _("Low: No sound/vibration but show popup")),
                    ("-2", _("Lowest: No notification, update badge number")),
                ],
                default_value = "0",
            ),
            forth = transform_forth_pushover_priority,
            back  = transform_back_pushover_priority,
        )),
        ("sound", DropdownChoice(
            title   = _("Select sound"),
            help    = _("See <a href=\"https://pushover.net/api#sounds\" target=\"_blank\">"
                        "Pushover sounds</a> for more information and trying out available sounds."),
            choices = [
                ("none",         _("None (silent)")),
                ("alien",        _("Alien Alarm (long)")),
                ("bike",         _("Bike")),
                ("bugle",        _("Bugle")),
                ("cashregister", _("Cash Register")),
                ("classical",    _("Classical")),
                ("climb",        _("Climb (long)")),
                ("cosmic",       _("Cosmic")),
                ("echo",         _("Pushover Echo (long)")),
                ("falling",      _("Falling")),
                ("gamelan",      _("Gamelan")),
                ("incoming",     _("Incoming")),
                ("intermission", _("Intermission")),
                ("magic",        _("Magic")),
                ("mechanical",   _("Mechanical")),
                ("persistent",   _("Persistent (long)")),
                ("pianobar",     _("Piano Bar")),
                ("pushover",     _("Pushover")),
                ("siren",        _("Siren")),
                ("spacealarm",   _("Space Alarm")),
                ("tugboat",      _("Tug Boat")),
                ("updown",       _("Up Down (long)")),
            ],
            default_value = "none"
        )),
    ]
))
