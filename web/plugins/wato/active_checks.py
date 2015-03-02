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

register_rulegroup("activechecks",
    _("Active checks (HTTP, TCP, etc.)"),
    _("Configure active networking checks like HTTP and TCP"))
group = "activechecks"

# This elements are also used in check_parameters.py
check_icmp_params = [
   ( "rta",
     Tuple(
         title = _("Round trip average"),
         elements = [
             Float(title = _("Warning if above"), unit = "ms", default_value = 200.0),
             Float(title = _("Critical if above"), unit = "ms", default_value = 500.0),
         ])),
   ( "loss",
     Tuple(
         title = _("Packet loss"),
         help = _("When the percentage of lost packets is equal or greater then "
                  "this level, then the according state is triggered. The default for critical "
                  "is 100%. That means that the check is only critical if <b>all</b> packets "
                  "are lost."),
         elements = [
             Percentage(title = _("Warning if above"), default_value = 80.0),
             Percentage(title = _("Critical if above"), default_value = 100.0),
         ])),

    ( "packets",
      Integer(
          title = _("Number of packets"),
          help = _("Number ICMP echo request packets to send to the target host on each "
                   "check execution. All packets are sent directly on check execution. Afterwards "
                   "the check waits for the incoming packets."),
          minvalue = 1,
          maxvalue = 20,
          default_value = 5,
       )),

     ( "timeout",
       Integer(
           title = _("Total timeout of check"),
           help = _("After this time (in seconds) the check is aborted, regardless "
                    "of how many packets have been received yet."),
           minvalue = 1,
       )),
]

mail_receiving_params = [
    ('fetch', CascadingDropdown(
        title = _('Mail Receiving'),
        choices = [
            ('IMAP', _('IMAP'), Dictionary(
                optional_keys = ['server'],
                elements = [
                    ('server', TextAscii(
                        title = _('IMAP Server'),
                        allow_empty = False,
                        help = _('You can specify a hostname or IP address different from the IP address '
                                 'of the host this check will be assigned to.')
                    )),
                    ('ssl', CascadingDropdown(
                        title = _('SSL Encryption'),
                        default_value = (False, 143),
                        choices = [
                            (False, _('Use no encryption'),
                                Optional(Integer(
                                    allow_empty = False,
                                    default_value = 143,
                                ),
                                title = _('TCP Port'),
                                help = _('By default the standard IMAP Port 143 is used.'),
                            )),
                            (True, _('Encrypt IMAP communication using SSL'),
                                Optional(Integer(
                                    allow_empty = False,
                                    default_value = 993,
                                ),
                                title = _('TCP Port'),
                                help = _('By default the standard IMAP/SSL Port 993 is used.'),
                            )),
                        ],
                    )),
                    ('auth', Tuple(
                        title = _('Authentication'),
                        elements = [
                            TextAscii(
                                title = _('Username'),
                                allow_empty = False,
                                size = 24
                            ),
                            Password(
                                title = _('Password'),
                                allow_empty = False,
                                size = 12
                            ),
                        ],
                    )),
                ],
            )),
            ('POP3', _('POP3'), Dictionary(
                optional_keys = ['server'],
                elements = [
                    ('server', TextAscii(
                        title = _('POP3 Server'),
                        allow_empty = False,
                        help = _('You can specify a hostname or IP address different from the IP address '
                                 'of the host this check will be assigned to.')
                    )),
                    ('ssl', CascadingDropdown(
                        title = _('SSL Encryption'),
                        default_value = (False, 110),
                        choices = [
                            (True, _('Use no encryption'),
                                Optional(Integer(
                                    allow_empty = False,
                                    default_value = 110,
                                ),
                                title = _('TCP Port'),
                                help = _('By default the standard POP3 Port 110 is used.'),
                            )),
                            (False, _('Encrypt POP3 communication using SSL'),
                                Optional(Integer(
                                    allow_empty = False,
                                    default_value = 995,
                                ),
                                title = _('TCP Port'),
                                help = _('By default the standard POP3/SSL Port 995 is used.'),
                            )),
                        ],
                    )),
                    ('auth', Tuple(
                        title = _('Authentication'),
                        elements = [
                            TextAscii(
                                title = _('Username'),
                                allow_empty = False,
                                size = 24
                            ),
                            Password(
                                title = _('Password'),
                                allow_empty = False,
                                size = 12
                            ),
                        ],
                    )),
                ],
            )),
        ]
    ))
]


register_rule(group,
    "active_checks:ssh",
    Dictionary(
        title = _("Check SSH service"),
        help = _("This rulset allow you to configure a SSH check for a host"),
        elements = [
            ("port",
               Integer(
                    title = _("TCP port number"),
                    default_value = 22),
            ),
            ("timeout",
                Integer(
                    title = _("Connect Timeout"),
                    help = _("Seconds before connection times out"),
                    default_value = 10),
            ),
            ("remote_version",
               TextAscii(
                    title = _("Version of Server"),
                    help = _("Warn if string doesn't match expected server version (ex: OpenSSH_3.9p1)"),
               )),
            ("remote_protocol",
                TextAscii(
                    title = _("Protocol of Server"),
                    help = _("Warn if protocol doesn't match expected protocol version (ex: 2.0)"),
                )),
        ]
    ),
    match="all")

register_rule(group,
    "active_checks:icmp",
    Dictionary(
        title = _("Check hosts with PING (ICMP Echo Request)"),
        help = _("This ruleset allows you to configure explicit PING monitoring of hosts. "
                 "Usually a PING is being used as a host check, so this is not neccessary. "
                 "There are some situations, however, where this can be useful. One of them "
                 "is when using the Check_MK Micro Core with SMART Ping and you want to "
                 "track performance data of the PING to some hosts, nevertheless."),
        elements = [
           ( "description",
             TextUnicode(
                 title = _("Service Description"),
                 allow_empty = False,
                 default_value = "PING",
           ))
        ] + check_icmp_params,
    ),
    match = "all",
)

register_rule(group,
    "active_checks:ftp",
    Transform(
        Dictionary(
            elements = [
                ("port",
                    Integer(
                        title = _("Portnumber"),
                        default_value = 21,
                        )
                ),
                ( "response_time",
                  Tuple(
                      title = _("Expected response time"),
                      elements = [
                          Float(
                              title = _("Warning if above"),
                              unit = "ms",
                              default_value = 100.0),
                          Float(
                              title = _("Critical if above"),
                              unit = "ms",
                              default_value = 200.0),
                      ])
                 ),
                 ( "timeout",
                   Integer(
                       title = _("Seconds before connection times out"),
                       unit = _("sec"),
                       default_value = 10,
                   )
                 ),
                 ( "refuse_state",
                   DropdownChoice(
                       title = _("State for connection refusal"),
                       choices = [ ('crit', _("CRITICAL")),
                                   ('warn', _("WARNING")),
                                   ('ok',   _("OK")),
                                 ])
                 ),

                 ( "send_string",
                   TextAscii(
                       title = _("String to send"),
                       size = 30)
                 ),
                 ( "expect",
                   ListOfStrings(
                       title = _("Strings to expect in response"),
                       orientation = "horizontal",
                       valuespec = TextAscii(size = 30),
                   )
                 ),

                 ( "ssl",
                   FixedValue(
                       value = True,
                       totext = _("use SSL"),
                       title = _("Use SSL for the connection."))

                 ),
                 ( "cert_days",
                   Integer(
                       title = _("SSL certificate validation"),
                       help = _("Minimum number of days a certificate has to be valid"),
                       unit = _("days"),
                       default_value = 30)
                 ),
            ]),
            forth = lambda x: type(x) == tuple and x[1] or x,
            title = _("Check FTP Service"),
    ),
    match = "all",
)


register_rule(group,
    "active_checks:dns",
    Tuple(
        title = _("Check DNS service"),
        help = _("Check the resolution of a hostname into an IP address by a DNS server. "
                 "This check uses <tt>check_dns</tt> from the standard Nagios plugins."),
        elements = [
           TextAscii(
               title = _("Queried Hostname or IP address"),
               allow_empty = False,
               help = _('The name or IPv4 address you want to query')),
           Dictionary(
               title = _("Optional parameters"),
               elements = [
                   ( "server",
                        Alternative(
                            title = _("DNS Server"),
                            elements = [
                                FixedValue( value=None, totext=_("use local configuration"),
                                            title = _("Use local DNS configuration of monitoring site")),
                                TextAscii(
                                    title = _("Specify DNS Server"),
                                    allow_empty = False,
                                    help = _("Optional DNS server you want to use for the lookup")),
                             ])
                   ),
                   ( "expected_address",
                     Transform(
                         ListOfStrings(
                             title = _("Expected answer (IP address or hostname)"),
                             help = _("List all allowed expected answers here. If query for an "
                                      "IP address then the answer will be host names, that end "
                                      "with a dot."),
                         ),
                         forth = lambda old: type(old) in (str, unicode) and [old] or old,
                     ),
                   ),
                   ( "expected_authority",
                     FixedValue(
                         value  = True,
                         title  = _("Expect Authoritative DNS Server"),
                         totext = _("Expect Authoritative"),
                     )
                   ),
                   ( "response_time",
                     Tuple(
                         title = _("Expected response time"),
                         elements = [
                             Float(
                                 title = _("Warning if above"),
                                 unit = _("sec"),
                                 default_value = 1),
                             Float(
                                 title = _("Critical if above"),
                                 unit = _("sec"),
                                 default_value = 2),
                         ])
                    ),
                   ( "timeout",
                      Integer(
                          title = _("Seconds before connection times out"),
                          unit = _("sec"),
                          default_value = 10,
                      )
                    ),
                ]),
        ]
    ),
    match = 'all'
)

register_rule(group,
    "active_checks:sql",
    Dictionary(
        title = _("Check SQL Database"),
        help = _("This check connects to the specified database, sends a custom SQL-statement "
                 "or starts a procedure, and checks that the result has a defined format "
                 "containing three columns, a number, a text, and performance data. Upper or "
                 "lower levels may be defined here.  If they are not defined the number is taken "
                 "as the state of the check.  If a procedure is used, input parameters of the "
                 "procedures may by given as comma separated list. "
                 "This check uses the active check <tt>check_sql</tt>."),
        optional_keys = [ "levels", "levels_low", "perfdata", "port", "procedure" ],
        elements = [
            ( "description",
              TextUnicode(title = _("Service Description"),
                 help = _("The name of this active service to be displayed."),
                 allow_empty = False,
            )),
            ( "dbms",
               DropdownChoice(
                   title = _("Type of Database"),
                   choices = [
                      ("mysql",    _("MySQL")),
                      ("postgres", _("PostgreSQL")),
                      ("mssql",    _("MSSQL")),
                      ("oracle",   _("Oracle")),
                      ("db2",      _("DB2")),
                   ],
                   default_value = "postgres",
               ),
            ),
            ( "port",
               Integer(title = _("Database Port"), allow_empty = True,
                      help = _('The port the DBMS listens to'))
            ),
            ( "name",
               TextAscii(title = _("Database Name"), allow_empty = False,
                      help = _('The name of the database on the DBMS'))
            ),
            ( "user",
               TextAscii(title = _("Database User"), allow_empty = False,
                      help = _('The username used to connect to the database'))
            ),
            ( "password",
               Password(title = _("Database Password"), allow_empty = False,
                      help = _('The password used to connect to the database'))
            ),
            ( "sql",
              TextAscii(title = _("SQL-statement or procedure name"), allow_empty = False,
                      help = _('The SQL-statement or procedure name which is executed on the DBMS'))
            ),
            ( "procedure",
            Dictionary(
                optional_keys = [ "input" ],
                title = _("Use procedure call instead of SQL statement"),
                help = _("If you activate this option, a name of a stored "
                    "procedure is used instead of an SQL statement. "
                    "The procedure should return one output variable, "
                    "which is evaluated in the check. If input parameters "
                    "are required, they may be specified below."),
                elements = [
                        ("useprocs",
                        FixedValue(
                            value = True,
                            totext = _("procedure call is used"),
                        )),
                        ("input",
                        TextAscii(
                            title = _("Input Parameters"),
                            allow_empty = True,
                            help = _("Input parameters, if required by the database procedure. "
                                     "If several parameters are required, use commas to separate them."),
                        )),
                    ]
                ),
            ),
            ( "levels",
            Tuple(
                title = _("Upper levels for first output item"),
                elements = [
                    Float( title = _("Warning if above")),
                    Float( title = _("Critical if above"))
                ])
            ),
            ( "levels_low",
            Tuple(
                title = _("Lower levels for first output item"),
                elements = [
                    Float( title = _("Warning if below")),
                    Float( title = _("Critical if below"))
                ])
            ),
            ( "perfdata",
              FixedValue(True, totext=_("Store output value into RRD database"), title = _("Performance Data"), ),
            )
        ]
    ),
    match = 'all'
)

register_rule(group,
    "active_checks:tcp",
    Tuple(
        title = _("Check connecting to a TCP port"),
        help = _("This check tests the connection to a TCP port. It uses "
                 "<tt>check_tcp</tt> from the standard Nagios plugins."),
        elements = [
           Integer(title = _("TCP Port"), minvalue=1, maxvalue=65535),
           Dictionary(
               title = _("Optional parameters"),
               elements = [
                   ( "svc_description",
                     TextUnicode(
                         title = _("Service description"),
                         allow_empty = False,
                         help = _("Here you can specify a service description. "
                                  "If this parameter is not set, the service is named <tt>TCP Port {Portnumber}</tt>"))),
                   ( "hostname",
                     TextAscii(
                         title = _("DNS Hostname"),
                         allow_empty = False,
                         help = _("If you specify a hostname here, then a dynamic DNS lookup "
                                  "will be done instead of using the IP address of the host "
                                  "as configured in your host properties."))),
                   ( "response_time",
                     Tuple(
                         title = _("Expected response time"),
                         elements = [
                             Float(
                                 title = _("Warning if above"),
                                 unit = "ms",
                                 default_value = 100.0),
                             Float(
                                 title = _("Critical if above"),
                                 unit = "ms",
                                 default_value = 200.0),
                         ])
                    ),
                    ( "timeout",
                      Integer(
                          title = _("Seconds before connection times out"),
                          unit = _("sec"),
                          default_value = 10,
                      )
                    ),
                    ( "refuse_state",
                      DropdownChoice(
                          title = _("State for connection refusal"),
                          choices = [ ('crit', _("CRITICAL")),
                                      ('warn', _("WARNING")),
                                      ('ok',   _("OK")),
                                    ])
                    ),

                    ( "send_string",
                      TextAscii(
                          title = _("String to send"),
                          size = 30)
                    ),
                    ( "escape_send_string",
                      FixedValue(
                          value = True,
                          title = _("Expand <tt>\\n</tt>, <tt>\\r</tt> and <tt>\\t</tt> in the sent string"),
                          totext = _("expand escapes"))
                    ),
                    ( "expect",
                      ListOfStrings(
                          title = _("Strings to expect in response"),
                          orientation = "horizontal",
                          valuespec = TextAscii(size = 30),
                      )
                    ),
                    ( "expect_all",
                      FixedValue(
                          value = True,
                          totext = _("expect all"),
                          title = _("Expect <b>all</b> of those strings in the response"))
                    ),
                    ( "jail",
                      FixedValue(
                          value = True,
                          title = _("Hide response from socket"),
                          help = _("As soon as you configure expected strings in "
                                   "the response the check will output the response - "
                                   "as long as you do not hide it with this option"),
                          totext = _("hide response"))
                    ),
                    ( "mismatch_state",
                      DropdownChoice(
                          title = _("State for expected string mismatch"),
                          choices = [ ('crit', _("CRITICAL")),
                                      ('warn', _("WARNING")),
                                      ('ok',   _("OK")),
                                    ])
                    ),
                    ( "delay",
                      Integer(
                          title = _("Seconds to wait before polling"),
                          help = _("Seconds to wait between sending string and polling for response"),
                          unit = _("sec"),
                          default_value = 0,
                      )
                    ),
                    ( "maxbytes",
                      Integer(
                          title = _("Maximum number of bytes to receive"),
                          help = _("Close connection once more than this number of "
                                   "bytes are received. Per default the number of "
                                   "read bytes is not limited. This setting is only "
                                   "used if you expect strings in the response."),
                          default_value = 1024,
                      ),
                    ),

                    ( "ssl",
                      FixedValue(
                          value = True,
                          totext = _("use SSL"),
                          title = _("Use SSL for the connection."))

                    ),
                    ( "cert_days",
                      Integer(
                          title = _("SSL certificate validation"),
                          help = _("Minimum number of days a certificate has to be valid"),
                          unit = _("days"),
                          default_value = 30)
                    ),

                    ( "quit_string",
                      TextAscii(
                          title = _("Final string to send"),
                          help = _("String to send server to initiate a clean close of "
                                   "the connection"),
                          size = 30)
                    ),
                ]),
        ]
    ),
    match = 'all'
)

register_rule(group,
    "active_checks:uniserv", Dictionary(
        title = _("Check uniserv service"), optional_keys = False, elements = [
            ("port",
                Integer(title = _("Port") )),
            ("service",
              TextAscii(
                  title = _("Service Name"),
                  help = _("Enter the uniserve service name here (has nothing to do with service description).")
            )),
            ("job",
                CascadingDropdown(
                    title = _("Mode of the Check"),
                    help = _("Choose, whether you just want to query the version number,"
                             " or if you want to check the response to an address query."),
                    choices = [
                        ("version", _("Check for Version")),
                        ("address", _("Check for an Address"),
                            Dictionary(
                                title = _("Address Check mode"),
                                optional_keys = False,
                                elements = [
                                    ( "street",
                                        TextAscii( title = _("Street name"))),
                                    ( "street_no",
                                        Integer( title = _("Street number"))),
                                    ( "city",
                                        TextAscii( title = _("City name"))),
                                    ( "search_regex",
                                        TextAscii( title = _("Check City against Regex"),
                                        help = _( "The city name from the response will be checked against "
                                                  "the regular expression specified here"),
                                        )),
                                ]
                        )),
                    ]
                )),

        ]))

# cert_days was only an integer for warning level until version 1.2.7
def transform_check_http_cert_days(cert_days):
    if type(cert_days) != tuple:
        cert_days = (cert_days, 0)
    return cert_days

register_rule(group,
    "active_checks:http",
    Tuple(
        title = _("Check HTTP service"),
        help = _("Check HTTP/HTTPS service using the plugin <tt>check_http</tt> "
                 "from the standard Monitoring Plugins. "
                 "This plugin tests the HTTP service on the specified host. "
                 "It can test normal (HTTP) and secure (HTTPS) servers, follow "
                 "redirects, search for strings and regular expressions, check "
                 "connection times, and report on certificate expiration times."),
        elements = [
            TextUnicode(
                title = _("Name"),
                help = _("Will be used in the service description. If the name starts with "
                         "a caret (<tt>^</tt>), the service description will not be prefixed with <tt>HTTP</tt>." ),
                allow_empty = False),
            Alternative(
                title = _("Mode of the Check"),
                help = _("Perform a check of the URL or the certificate expiration."),
                elements = [
                    Dictionary(
                        title = _("Check the URL"),
                        elements = [
                            ( "virthost",
                                Tuple(
                                    title = _("Virtual host"),
                                    elements = [
                                        TextAscii(
                                            title = _("Name of the virtual host"),
                                            help = _("Set this in order to specify the name of the "
                                                     "virtual host for the query (using HTTP/1.1). If you "
                                                     "leave this empty, then the IP address of the host "
                                                     "will be used instead."),
                                            allow_empty = False
                                        ),
                                        Checkbox(
                                            label = _("Omit specifying an IP address"),
                                            help = _("Usually Check_MK will nail this check to the "
                                                     "IP address of the host it is attached to. With this "
                                                     "option you can have the check use the name of the "
                                                     "virtual host instead and do a dynamic DNS lookup."),
                                            true_label = _("omit IP address"),
                                            false_label = _("specify IP address"),
                                        ),
                                    ]
                                )
                            ),
                            ( "uri",
                                TextAscii(
                                    title = _("URI to fetch (default is <tt>/</tt>)"),
                                    allow_empty = False,
                                    default_value = "/"
                                )
                            ),
                            ( "port",
                                Integer(
                                    title = _("TCP Port"),
                                    minvalue = 1,
                                    maxvalue = 65535,
                                    default_value = 80
                                )
                            ),
                            ( "ssl",
                                FixedValue(
                                    value = True,
                                    totext = _("use SSL/HTTPS"),
                                    title = _("Use SSL/HTTPS for the connection.")
                                )
                            ),
                            ( "sni",
                                FixedValue(
                                    value = True,
                                    totext = _("enable SNI"),
                                    title = _("Enable SSL/TLS hostname extension support (SNI)"),
                                )
                            ),
                            ( "response_time",
                                Tuple(
                                    title = _("Expected response time"),
                                    elements = [
                                        Float(
                                            title = _("Warning if above"),
                                            unit = "ms",
                                            default_value = 100.0
                                        ),
                                        Float(
                                            title = _("Critical if above"),
                                            unit = "ms",
                                            default_value = 200.0
                                        ),
                                    ]
                                )
                            ),
                            ( "timeout",
                                Integer(
                                    title = _("Seconds before connection times out"),
                                    unit = _("sec"),
                                    default_value = 10,
                                )
                            ),
                            ( "user_agent",
                                TextAscii(
                                    title = _("User Agent"),
                                    help = _("String to be sent in http header as \"User Agent\""),
                                    allow_empty = False,
                                ),
                            ),
                            ( "add_headers",
                                ListOfStrings(
                                    title = _("Additional header lines"),
                                    orientation = "vertical",
                                    valuespec = TextAscii(size = 40),
                                ),
                            ),
                            ( "auth",
                                Tuple(
                                    title = _("Authorization"),
                                    help = _("Credentials for HTTP Basic Authentication"),
                                    elements = [
                                        TextAscii(
                                            title = _("Username"),
                                            size = 12,
                                            allow_empty = False
                                        ),
                                        Password(
                                            title = _("Password"),
                                            size = 12,
                                            allow_empty = False
                                        ),
                                    ]
                                )
                            ),
                            ( "proxy_auth",
                                Tuple(
                                    title = _("Proxy-Authorization"),
                                    help = _("Credentials for HTTP Proxy with basic authentication"),
                                    elements = [
                                        TextAscii(
                                            title = _("Username"),
                                            size = 12,
                                            allow_empty = False
                                        ),
                                        Password(
                                            title = _("Password"),
                                            size = 12,
                                            allow_empty = False
                                        ),
                                    ]
                                )
                            ),
                            ( "onredirect",
                                DropdownChoice(
                                    title = _("How to handle redirect"),
                                    choices = [
                                        ( 'ok',         _("Make check OK") ),
                                        ( 'warning',    _("Make check WARNING") ),
                                        ( 'critical',   _("Make check CRITICAL") ),
                                        ( 'follow',     _("Follow the redirection") ),
                                        ( 'sticky',     _("Follow, but stay to same IP address") ),
                                        ( 'stickyport', _("Follow, but stay to same IP-address and port") ),
                                    ],
                                    default_value = 'follow'
                                ),
                            ),
                            ( "expect_response_header",
                                TextAscii(
                                    title = _("String to expect in response headers"),
                                )
                            ),
                            ( "expect_response",
                                ListOfStrings(
                                    title = _("Strings to expect in server response"),
                                    help = _("At least one of these strings is expected in "
                                             "the first (status) line of the server response "
                                             "(default: <tt>HTTP/1.</tt>). If specified skips "
                                             "all other status line logic (ex: 3xx, 4xx, 5xx "
                                             "processing)"),
                                )
                            ),
                            ( "expect_string",
                                TextAscii(
                                    title = _("Fixed string to expect in the content"),
                                    allow_empty = False,
                                )
                            ),
                            ( "expect_regex",
                                Transform(
                                    Tuple(
                                        orientation = "vertical",
                                        show_titles = False,
                                        elements = [
                                            RegExp(label = _("Regular expression: ")),
                                            Checkbox(label = _("Case insensitive")),
                                            Checkbox(label = _("return CRITICAL if found, OK if not")),
                                            Checkbox(label = _("Multiline string matching")),
                                        ]
                                    ),
                                    forth = lambda x: len(x) == 3 and tuple(list(x) + [False]) or x,
                                    title = _("Regular expression to expect in content"),
                                ),
                            ),
                            ( "post_data",
                                Tuple(
                                    title = _("Send HTTP POST data"),
                                    elements = [
                                        TextUnicode(
                                            title = _("HTTP POST data"),
                                            help = _("Data to send via HTTP POST method. "
                                                     "Please make sure, that the data is URL-encoded."),
                                            size = 40,
                                        ),
                                        TextAscii(
                                            title = _("Content-Type"),
                                            default_value = "text/html"),
                                    ]
                                )
                            ),
                            ( "method",
                                DropdownChoice(
                                    title = _("HTTP Method"),
                                    default_value = "GET",
                                    choices = [
                                        ( "GET", "GET" ),
                                        ( "POST", "POST" ),
                                        ( "OPTIONS", "OPTIONS" ),
                                        ( "TRACE", "TRACE" ),
                                        ( "PUT", "PUT" ),
                                        ( "DELETE", "DELETE" ),
                                        ( "HEAD", "HEAD" ),
                                        ( "CONNECT", "CONNECT" ),
                                    ]
                                )
                            ),
                            ( "no_body",
                                FixedValue(
                                    value = True,
                                    title = _("Don't wait for document body"),
                                    help = _("Note: this still does an HTTP GET or POST, not a HEAD."),
                                    totext = _("don't wait for body")
                                )
                            ),
                            ( "page_size",
                                Tuple(
                                    title = _("Page size to expect"),
                                    elements = [
                                        Integer(title = _("Minimum"), unit=_("Bytes")),
                                        Integer(title = _("Maximum"), unit=_("Bytes")),
                                    ]
                                )
                            ),
                            ( "max_age",
                                Age(
                                    title = _("Maximum age"),
                                    help = _("Warn, if the age of the page is older than this"),
                                    default_value = 3600 * 24,
                                )
                            ),
                            ( "urlize",
                                FixedValue(
                                    value = True,
                                    title = _("Clickable URLs"),
                                    totext = _("Format check output as hyperlink"),
                                    help = _("With this option the check produces an output that is a valid hyperlink "
                                             "to the checked URL and this clickable."),
                                )
                            ),
                        ]
                    ),

                    Dictionary(
                        title = _("Check SSL Certificate Age"),
                        elements = [
                            ( "cert_days",
                                Transform(
                                    Tuple(
                                        title = _("Age"),
                                        help = _("Minimum number of days a certificate has to be valid. "
                                                 "Port defaults to 443. When this option is used the URL "
                                                 "is not checked."),
                                        elements = [
                                            Integer(title = _("Warning at or below"), minvalue = 0, unit = _("days")),
                                            Integer(title = _("Critical at or below"), minvalue = 0, unit = _("days")),
                                        ],
                                    ),
                                    forth = transform_check_http_cert_days,
                                ),
                            ),
                            ( "cert_host",
                                TextAscii(
                                    title = _("Check Cerficate of different IP / DNS Name"),
                                    help = _("For each SSL cerficate on a host, a different IP address is needed. "
                                             "Here, you can specify the address if it differs from the  "
                                             "address from the host primary address."),
                                ),
                            ),
                            ( "port",
                                Integer(
                                    title = _("TCP Port"),
                                    minvalue = 1,
                                    maxvalue = 65535,
                                    default_value = 443,
                                ),
                            ),
                            ( "sni",
                                FixedValue(
                                    value = True,
                                    totext = _("enable SNI"),
                                    title = _("Enable SSL/TLS hostname extension support (SNI)"),
                                ),
                            ),
                        ],
                        required_keys = [ "cert_days" ],
                    ),
                ]
            ),
        ]
    ),
    match = 'all'
)

register_rule(group,
    "active_checks:ldap",
    Tuple(
        title = _("Check access to LDAP service"),
        help = _("This check uses <tt>check_ldap</tt> from the standard "
                "Nagios plugins in order to try the response of an LDAP "
                "server."),
        elements = [
            TextUnicode(
                title = _("Name"),
                help = _("The service description will be <b>LDAP</b> plus this name"),
                allow_empty = False),
            TextAscii(
                title = _("Base DN"),
                help = _("LDAP base, e.g. ou=Development, o=Mathias Kettner GmbH, c=de"),
                allow_empty = False,
                size = 60),
            Dictionary(
               title = _("Optional parameters"),
               elements = [
                   ( "attribute",
                     TextAscii(
                         title = _("Attribute to search"),
                         help = _("LDAP attribute to search, "
                                  "The default is <tt>(objectclass=*)</tt>."),
                         size = 40,
                         allow_empty = False,
                         default_value = "(objectclass=*)",
                     )
                   ),
                   ( "authentication",
                     Tuple(
                         title = _("Authentication"),
                         elements = [
                             TextAscii(
                                 title = _("Bind DN"),
                                 help = _("Distinguished name for binding"),
                                 allow_empty = False,
                                 size = 60,
                             ),
                             Password(
                                 title = _("Password"),
                                 help = _("Password for binding, if your server requires an authentication"),
                                 allow_empty = False,
                                 size = 20,
                             )
                        ]
                      )
                   ),
                   ( "port",
                     Integer(
                       title = _("TCP Port"),
                       help = _("Default is 389 for normal connections and 636 for SSL connections."),
                       minvalue = 1,
                       maxvalue = 65535,
                       default_value = 389)
                   ),
                   ( "ssl",
                      FixedValue(
                          value = True,
                          totext = _("Use SSL"),
                          title = _("Use LDAPS (SSL)"),
                          help = _("Use LDAPS (LDAP SSLv2 method). This sets the default port number to 636"))

                   ),
                   ( "version",
                     DropdownChoice(
                        title = _("LDAP Version"),
                        help = _("The default is to use version 2"),
                        choices = [
                            ( "v2", _("Version 2") ),
                            ( "v3", _("Version 3") ),
                            ( "v3tls", _("Version 3 and TLS") ),
                        ],
                        default_value = "v2",
                      )
                   ),
                   ( "response_time",
                     Tuple(
                         title = _("Expected response time"),
                         elements = [
                             Float(
                                 title = _("Warning if above"),
                                 unit = "ms",
                                 default_value = 1000.0),
                             Float(
                                 title = _("Critical if above"),
                                 unit = "ms",
                                 default_value = 2000.0),
                         ])
                    ),
                    ( "timeout",
                      Integer(
                          title = _("Seconds before connection times out"),
                          unit = _("sec"),
                          default_value = 10,
                      )
                    ),
                ])
        ]),
    match = 'all'
)

register_rule(group,
    "active_checks:smtp",
    Tuple(
        title = _("Check access to SMTP services"),
        help = _("This check uses <tt>check_smtp</tt> from the standard "
                "Nagios plugins in order to try the response of an SMTP "
                "server."),
        elements = [
            TextUnicode(
                title = _("Name"),
                help = _("The service description will be <b>SMTP</b> plus this name"),
                allow_empty = False),
            Dictionary(
               title = _("Optional parameters"),
               elements = [
                   ( "hostname",
                     TextAscii(
                         title = _("DNS Hostname or IP address"),
                         allow_empty = False,
                         help = _("You can specify a hostname or IP address different from the IP address "
                                  "of the host as configured in your host properties."))),
                   ( "port",
                     Transform(
                         Integer(
                             title = _("TCP Port to connect to"),
                             help = _("The TCP Port the SMTP server is listening on. "
                                      "The default is <tt>25</tt>."),
                             size = 5,
                             minvalue = 1,
                             maxvalue = 65535,
                             default_value = "25",
                         ),
                         forth = int,
                      )
                   ),
                   ( "ip_version",
                     Alternative(
                         title = _("IP-Version"),
                         elements = [
                            FixedValue(
                                "ipv4",
                                totext = "",
                                title = _("IPv4")
                            ),
                            FixedValue(
                                "ipv6",
                                totext = "",
                                title = _("IPv6")
                            ),
                         ],
                     ),
                   ),
                   ( "expect",
                     TextAscii(
                         title = _("Expected String"),
                         help = _("String to expect in first line of server response. "
                                  "The default is <tt>220</tt>."),
                         size = 8,
                         allow_empty = False,
                         default_value = "220",
                     )
                   ),
                   ('commands',
                     ListOfStrings(
                         title = _("SMTP Commands"),
                         help = _("SMTP commands to execute."),
                     )
                   ),
                   ('command_responses',
                     ListOfStrings(
                         title = _("SMTP Responses"),
                         help = _("Expected responses to the given SMTP commands."),
                     )
                   ),
                   ("from",
                     TextAscii(
                         title = _("FROM-Address"),
                         help = _("FROM-address to include in MAIL command, required by Exchange 2000"),
                         size = 20,
                         allow_empty = True,
                         default_value = "",
                     )
                   ),
                   ("fqdn",
                     TextAscii(
                         title = _("FQDN"),
                         help = _("FQDN used for HELO"),
                         size = 20,
                         allow_empty = True,
                         default_value = "",
                     )
                   ),
                   ("cert_days",
                      Integer(
                          title = _("Minimum Certificate Age"),
                          help = _("Minimum number of days a certificate has to be valid."),
                          unit = _("days"),
                      )
                   ),
                   ("starttls",
                      FixedValue(
                          True,
                          totext = _("STARTTLS enabled."),
                          title = _("Use STARTTLS for the connection.")
                      )
                   ),
                   ( "auth",
                     Tuple(
                         title = _("Enable SMTP AUTH (LOGIN)"),
                         help = _("SMTP AUTH type to check (default none, only LOGIN supported)"),
                         elements = [
                             TextAscii(
                                 title = _("Username"),
                                 size = 12,
                                 allow_empty = False),
                             Password(
                                 title = _("Password"),
                                 size = 12,
                                 allow_empty = False),
                         ]
                     )
                   ),
                   ("response_time",
                     Tuple(
                         title = _("Expected response time"),
                         elements = [
                             Integer(
                                 title = _("Warning if above"),
                                 unit = _("sec")
                             ),
                             Integer(
                                 title = _("Critical if above"),
                                 unit = _("sec")
                             ),
                         ])
                    ),
                    ( "timeout",
                      Integer(
                          title = _("Seconds before connection times out"),
                          unit = _("sec"),
                          default_value = 10,
                      )
                    ),
                ])
        ]
    ),
    match = 'all'
)

register_rule(group,
    "active_checks:disk_smb",
    Dictionary(
        title = _("Check access to SMB share"),
        help = _("This ruleset helps you to configure the classical Nagios "
                 "plugin <tt>check_disk_smb</tt> that checks the access to "
                 "filesystem shares that are exported via SMB/CIFS."),
        elements = [
            ( "share",
              TextUnicode(
                  title = _("SMB share to check"),
                  help = _("Enter the plain name of the share only, e. g. <tt>iso</tt>, <b>not</b> "
                           "the full UNC like <tt>\\\\servername\\iso</tt>"),
                  size = 32,
                  allow_empty = False,
            )),
            ( "workgroup",
              TextUnicode(
                  title = _("Workgroup"),
                  help = _("Workgroup or domain used (defaults to <tt>WORKGROUP</tt>)"),
                  size = 32,
                  allow_empty = False,
            )),
            ( "host",
              TextAscii(
                  title = _("NetBIOS name of the server"),
                  help = _("If omitted then the IP address is being used."),
                  size = 32,
                  allow_empty = False,
            )),
            ( "port",
              Integer(
                  title = _("TCP Port"),
                  help = _("TCP port number to connect to. Usually either 139 or 445."),
                  default_value = 445,
                  minvalue = 1,
                  maxvalue = 65535,
            )),
            ( "levels",
              Tuple(
                  title = _("Levels for used disk space"),
                  elements = [
                      Percentage(title = _("Warning if above"), default_value = 85,  allow_int = True),
                      Percentage(title = _("Critical if above"), default_value = 95, allow_int = True),
                  ]
            )),
            ( "auth",
              Tuple(
                  title = _("Authorization"),
                  elements = [
                      TextAscii(
                          title = _("Username"),
                          allow_empty = False,
                          size = 24),
                      Password(
                          title = _("Password"),
                          allow_empty = False,
                          size = 12),
                  ],
            )),
        ],
        required_keys = [ "share", "levels" ],
    ),
    match = 'all'
)

def PluginCommandLine(addhelp = ""):
    return TextAscii(
          title = _("Command line"),
          help = _("Please enter the complete shell command including "
                   "path name and arguments to execute. You can use monitoring "
                   "macros here. The most important are:<ul>"
                   "<li><tt>$HOSTADDRESS$</tt>: The IP address of the host</li>"
                   "<li><tt>$HOSTNAME$</tt>: The name of the host</li>"
                   "<li><tt>$USER1$</tt>: user macro 1 (usually path to shipped plugins)</li>"
                   "<li><tt>$USER2$</tt>: user marco 2 (usually path to your own plugins)</li>"
                   "</ul>"
                   "If you are using OMD, you can omit the path and just specify "
                   "the command (e.g. <tt>check_foobar</tt>). This command will be "
                   "searched first in the local plugins directory "
                   "(<tt>~/local/lib/nagios/plugins</tt>) and then in the shipped plugins "
                   "directory (<tt>~/lib/nagios/plugins</tt>) within your site directory."),
          size = "max",
       )

register_rule(group,
    "custom_checks",
    Dictionary(
        title = _("Classical active and passive Monitoring checks"),
        help = _("With this ruleset you can configure &quot;classical Monitoring checks&quot; "
                 "to be executed directly on your monitoring server. These checks "
                 "will not use Check_MK. It is also possible to configure passive "
                 "checks that are fed with data from external sources via the "
                 "command pipe of the monitoring core."),
        elements = [
            ( "service_description",
              TextUnicode(
                  title = _("Service description"),
                  help = _("Please make sure that this is unique per host "
                         "and does not collide with other services."),
                  allow_empty = False,
                  default_value = _("Customcheck"))
            ),
            ( "command_line",
              PluginCommandLine(addhelp = _("<br><br>"
                   "<b>Passive checks</b>: Do no specify a command line if you want "
                   "to define passive checks.")),
            ),
            ( "command_name",
              TextAscii(
                  title = _("Internal command name"),
                  help = _("If you want, you can specify a name that will be used "
                           "in the <tt>define command</tt> section for these checks. This "
                           "allows you to a assign a custom PNP template for the performance "
                           "data of the checks. If you omit this, then <tt>check-mk-custom</tt> "
                           "will be used."),
                  size = 32)
            ),
            ( "has_perfdata",
              FixedValue(
                  title = _("Performance data"),
                  value = True,
                  totext = _("process performance data"),
              )
            ),
            ( "freshness",
              Dictionary(
                  title = _("Check freshness"),
                  help = _("Freshness checking is only useful for passive checks when the staleness feature "
                           "is not enough for you. It changes the state of a check to a configurable other state "
                           "when the check results are not arriving in time. Staleness will still grey out the "
                           "test after the corrsponding interval. If you don't want that, you might want to adjust "
                           "the staleness interval as well. The staleness interval is calculated from the normal "
                           "check interval multiplied by the staleness value in the <tt>Global Settings</tt>. "
                           "The normal check interval can be configured in a separate rule for your check."),
                  optional_keys = False,
                  elements = [
                      ( "interval",
                        Integer(
                            title = _("Expected update interval"),
                            label = _("Updates are expected at least every"),
                            unit = _("minutes"),
                            minvalue = 1,
                            default_value = 10,
                      )),
                      ( "state",
                        DropdownChoice(
                            title = _("State in case of absent updates"),
                            choices =  [
                               ( 1, _("WARN") ),
                               ( 2, _("CRIT") ),
                               ( 3, _("UNKNOWN") ),
                            ],
                            default_value = 3,
                      )),
                      ( "output",
                        TextUnicode(
                            title = _("Plugin output in case of absent updates"),
                            size = 40,
                            allow_empty = False,
                            default_value = _("Check result did not arrive in time")
                      )),
                  ],
               )
            ),

        ],
        required_keys = [ "service_description" ],
    ),
    match = 'all'
)

register_rule(group,
    "active_checks:bi_aggr",
    Tuple(
        title = _("Check State of BI Aggregation"),
        help = _("Connect to the local or a remote monitoring host, which uses Check_MK BI to aggregate "
                 "several states to a single BI aggregation, which you want to show up as a single "
                 "service."),
        elements = [
            TextAscii(
                title = _("Base URL (OMD Site)"),
                help = _("The base URL to the monitoring instance. For example <tt>http://mycheckmk01/mysite</tt>. You can use "
                         "macros like <tt>$HOSTADDRESS$</tt> and <tt>$HOSTNAME$</tt> within this URL to make them be replaced by "
                         "the hosts values."),
                size = 60,
                allow_empty = False
            ),
            TextAscii(
                title = _("Aggregation Name"),
                help = _("The name of the aggregation to fetch. It will be added to the service description. You can use "
                         "macros like <tt>$HOSTADDRESS$</tt> and <tt>$HOSTNAME$</tt> within this parameter to make them be replaced by "
                         "the hosts values."),
                allow_empty = False
            ),
            TextAscii(
                title = _("Username"),
                help = _("The name of the user account to use for fetching the BI aggregation via HTTP. When "
                         "using the cookie based authentication mode (default), this must be a user where "
                         "authentication is set to \"Automation Secret\" based authentication."),
                allow_empty = False
            ),
            Password(
                title = _("Password"),
                help = _("Valid automation secret or password for the user, depending on the choosen "
                         "authentication mode."),
                allow_empty = False
            ),
            Dictionary(
                title = _("Optional parameters"),
                elements = [
                    ("auth_mode", DropdownChoice(
                        title = _('Authentication Mode'),
                        default_value = 'cookie',
                        choices = [
                            ('cookie', _('Form (Cookie) based')),
                            ('basic',  _('HTTP Basic')),
                            ('digest', _('HTTP Digest')),
                        ],
                    )),
                    ("timeout", Integer(
                        title = _("Seconds before connection times out"),
                        unit = _("sec"),
                        default_value = 60,
                    )),
                ]
            ),
        ]
    ),
    match = 'all'
)

register_rule(group,
    "active_checks:form_submit",
    Tuple(
        title = _("Check HTML Form Submit"),
        help = _("Check submission of HTML forms via HTTP/HTTPS using the plugin <tt>check_form_submit</tt> "
                 "provided with Check_MK. This plugin provides more functionality as <tt>check_http</tt>, "
                 "as it automatically follows HTTP redirect, accepts and uses cookies, parses forms "
                 "from the requested pages, changes vars and submits them to check the response "
                 "afterwards."),
        elements = [
            TextUnicode(
                title = _("Name"),
                help = _("The name will be used in the service description"),
                allow_empty = False
            ),
            Dictionary(
                title = _("Check the URL"),
                elements = [
                    ("hosts", ListOfStrings(
                        title = _('Check specific host(s)'),
                        help = _('By default, if you do not specify any host addresses here, '
                                 'the host address of the host this service is assigned to will '
                                 'be used. But by specifying one or several host addresses here, '
                                 'it is possible to let the check monitor one or multiple hosts.')
                    )),
                    ("virthost", TextAscii(
                        title = _("Virtual host"),
                        help = _("Set this in order to specify the name of the "
                         "virtual host for the query (using HTTP/1.1). When you "
                         "leave this empty, then the IP address of the host "
                         "will be used instead."),
                        allow_empty = False,
                    )),
                    ("uri", TextAscii(
                        title = _("URI to fetch (default is <tt>/</tt>)"),
                        allow_empty = False,
                        default_value = "/",
                        regex = '^/.*',
                    )),
                    ("port", Integer(
                        title = _("TCP Port"),
                        minvalue = 1,
                        maxvalue = 65535,
                        default_value = 80,
                    )),
                    ("ssl", FixedValue(
                        value = True,
                        totext = _("use SSL/HTTPS"),
                        title = _("Use SSL/HTTPS for the connection."))
                    ),
                    ("timeout", Integer(
                        title = _("Seconds before connection times out"),
                        unit = _("sec"),
                        default_value = 10,
                    )),
                    ("expect_regex", RegExp(
                        title = _("Regular expression to expect in content"),
                    )),
                    ("form_name", TextAscii(
                        title = _("Name of the form to populate and submit"),
                        help = _("If there is only one form element on the requested page, you "
                                 "do not need to provide the name of that form here. But if you "
                                 "have several forms on that page, you need to provide the name "
                                 "of the form here, to enable the check to identify the correct "
                                 "form element."),
                        allow_empty = True,
                    )),
                    ("query", TextAscii(
                        title = _("Send HTTP POST data"),
                        help = _("Data to send via HTTP POST method. Please make sure, that the data "
                                 "is URL-encoded (for example \"key1=val1&key2=val2\")."),
                        size = 40,
                    )),
                    ("num_succeeded", Tuple(
                        title = _("Multiple Hosts: Number of successful results"),
                        elements = [
                            Integer(title = _("Warning if equal or below")),
                            Integer(title = _("Critical if equal or below")),
                        ]
                    )),
                ]
            ),
        ]
    ),
    match = 'all'
)

register_rule(group,
    "active_checks:notify_count",
    Tuple(
        title = _("Check Number of Notifications per Contact"),
        help = _("Check the number of sent notifications per contact using the plugin <tt>check_notify_count</tt> "
                 "provided with Check_MK. This plugin counts the total number of notifications sent by the local "
                 "monitoring core and creates graphs for each individual contact. You can configure thresholds "
                 "on the number of notifications per contact in a defined time interval. "
                 "This plugin queries livestatus to extract the notification related log entries from the "
                 "log file of your monitoring core."),
        elements = [
            TextUnicode(
                title = _("Service Description"),
                help = _("The name that will be used in the service description"),
                allow_empty = False
            ),
            Integer(
                title = _("Interval to monitor"),
                label = _("notifications within last"),
                unit = _("minutes"),
                minvalue = 1,
                default_value = 60,
            ),
            Dictionary(
                title = _("Optional parameters"),
                elements = [
                    ("num_per_contact", Tuple(
                        title = _("Thresholds for Notifications per Contact"),
                        elements = [
                            Integer(title = _("Warning if above"), default_value = 20),
                            Integer(title = _("Critical if above"), default_value = 50),
                        ]
                    )),
                ]
            ),
        ]
    ),
    match = 'all'
)

register_rule(group,
    "active_checks:traceroute",
    Dictionary(
        title = _("Check current routing (uses <tt>traceroute</tt>)"),
        help = _("This active check uses <tt>traceroute</tt> in order to determine the current "
                 "routing from the monitoring host to the target host. You can specify any number "
                 "of missing or expected routes in that way detect e.g. an (unintended) failover "
                 "to a secondary route."),
        elements = [
            ( "dns",
              Checkbox(
                  title = _("Name resolution"),
                  label = _("Use DNS to convert IP addresses into hostnames"),
                  help = _("If you use this option, then <tt>traceroute</tt> is <b>not</b> being "
                           "called with the option <tt>-n</tt>. That means that all IP addresses "
                           "are tried to be converted into names. This usually adds additional "
                           "execution time. Also DNS resolution might fail for some addresses."),
            )),
            ( "routers",
              ListOf(
                  Tuple(
                      elements = [
                          TextAscii(
                              title = _("Router (FQDN, IP-Address)"),
                              allow_empty = False,
                          ),
                          DropdownChoice(
                              title = _("How"),
                              choices = [
                                 ( 'W', _("WARN - if this router is not being used") ),
                                 ( 'C', _("CRIT - if this router is not being used") ),
                                 ( 'w', _("WARN - if this router is being used") ),
                                 ( 'c', _("CRIT - if this router is being used") ),
                              ]
                         ),
                      ]
                  ),
                  title = _("Router that must or must not be used"),
                  add_label = _("Add Condition"),
              )
            ),
            ( "method",
              DropdownChoice(
                  title = _("Method of probing"),
                  choices = [
                      ( None,   _("UDP (default behaviour of tcpdump)") ),
                      ( "icmp", _("ICMP Echo Request") ),
                      ( "tcp",  _("TCP SYN") ),
                  ]
              )
            ),
        ],
        optional_keys = False,
    ),
    match = 'all'
)

register_rule(group,
    'active_checks:mail_loop',
    Dictionary(
        title = _('Check Email Delivery'),
        help = _('This active check sends out special E-Mails to a defined mail address using '
                 'the SMTP protocol and then tries to receive these mails back by querying the '
                 'inbox of a IMAP or POP3 mailbox. With this check you can verify that your whole '
                 'mail delivery progress is working.'),
        optional_keys = ['smtp_server', 'smtp_tls', 'smtp_port', 'smtp_auth', 'connect_timeout', 'delete_messages', 'duration'],
        elements = [
            ('item', TextUnicode(
                title = _('Name'),
                help = _('The service description will be <b>Mail Loop</b> plus this name'),
                allow_empty = False
            )),
            ('smtp_server', TextAscii(
                title = _('SMTP Server'),
                allow_empty = False,
                help = _('You can specify a hostname or IP address different from the IP address '
                         'of the host this check will be assigned to.')
            )),
            ('smtp_tls', FixedValue(True,
                title = _('Use TLS over SMTP'),
                totext = _('Encrypt SMTP communication using TLS'),
            )),
            ('smtp_port', Integer(
                title = _('SMTP TCP Port to connect to'),
                help = _('The TCP Port the SMTP server is listening on. Defaulting to <tt>25</tt>.'),
                allow_empty = False,
                default_value = 25,
            )),
            ('smtp_auth', Tuple(
                title = _('SMTP Authentication'),
                elements = [
                    TextAscii(
                        title = _('Username'),
                        allow_empty = False,
                        size = 24
                    ),
                    Password(
                        title = _('Password'),
                        allow_empty = False,
                        size = 12
                    ),
                ],
            )),
        ] + mail_receiving_params + [
            ('mail_from', EmailAddress(
                title = _('From: email address'),
            )),
            ('mail_to', EmailAddress(
                title = _('Destination email address'),
            )),
            ('connect_timeout', Integer(
                title = _('Connect Timeout'),
                minvalue = 1,
                default_value = 10,
                unit = _('sec'),
            )),
            ("duration", Tuple(
                title = _("Loop duration"),
                elements = [
                    Age(title = _("Warning at")),
                    Age(title = _("Critical at")),
                ])
            ),
            ('delete_messages', FixedValue(True,
                title = _('Delete processed messages'),
                totext = _('Delete all processed message belonging to this check'),
                help = _('Delete all messages identified as being related to this '
                         'check. This is disabled by default, which will make '
                         'your mailbox grow when you not clean it up on your own.'),
            )),
        ]
    ),
    match = 'all'
)

register_rule(group,
    'active_checks:mail',
    Dictionary(
        title = _('Check Email'),
        help = _('The basic function of this check is to log in into an IMAP or POP3 mailbox to '
                 'monitor whether or not the login is possible. A extended feature is, that the '
                 'check can fetch all (or just some) from the mailbox and forward them as events '
                 'to the Event Console.'),
        required_keys = [ 'service_description', 'fetch' ],
        elements = [
            ('service_description',
              TextUnicode(
                  title = _('Service description'),
                  help = _('Please make sure that this is unique per host '
                           'and does not collide with other services.'),
                  allow_empty = False,
                  default_value = "Email")
            )
        ] + mail_receiving_params + [
            ('connect_timeout', Integer(
                title = _('Connect Timeout'),
                minvalue = 1,
                default_value = 10,
                unit = _('sec'),
            )),
            ('forward', Dictionary(
                title = _("Forward mails as events to Event Console"),
                elements = [
                    ('method', Alternative(
                        title = _("Forwarding Method"),
                        elements = [
                            Alternative(
                                title = _("Send events to local event console"),
                                elements = [
                                    FixedValue(
                                        "",
                                        totext = _("Directly forward to event console"),
                                        title = _("Send events to local event console in same OMD site"),
                                    ),
                                    TextAscii(
                                        title = _("Send events to local event console into unix socket"),
                                        allow_empty = False,
                                    ),

                                    FixedValue(
                                        "spool:",
                                        totext = _("Spool to event console"),
                                        title = _("Spooling: Send events to local event console in same OMD site"),
                                    ),
                                    Transform(
                                        TextAscii(),
                                        title = _("Spooling: Send events to local event console into given spool directory"),
                                        allow_empty = False,
                                        forth = lambda x: x[6:],        # remove prefix
                                        back  = lambda x: "spool:" + x, # add prefix
                                    ),
                                ],
                                match = lambda x: x and (x == 'spool:' and 2 or x.startswith('spool:') and 3 or 1) or 0
                            ),
                            Tuple(
                                title = _("Send events to remote syslog host"),
                                elements = [
                                    DropdownChoice(
                                        choices = [
                                            ('udp', _('UDP')),
                                            ('tcp', _('TCP')),
                                        ],
                                        title = _("Protocol"),
                                    ),
                                    TextAscii(
                                        title = _("Address"),
                                        allow_empty = False,
                                    ),
                                    Integer(
                                        title = _("Port"),
                                        allow_empty = False,
                                        default_value = 514,
                                        minvalue = 1,
                                        maxvalue = 65535,
                                        size = 6,
                                    ),
                                ]
                            ),
                        ],
                    )),
                    ('match_subject', RegExpUnicode(
                        title = _('Only process mails with matching subject'),
                        help = _('Use this option to not process all messages found in the inbox, '
                                 'but only the those whose subject matches the given regular expression.'),
                    )),
                    ('facility', DropdownChoice(
                        title = _("Events: Syslog facility"),
                        help = _("Use this syslog facility for all created events"),
                        choices = syslog_facilities,
                        default_value = 2, # mail
                    )),
                    ('application', Alternative(
                        title = _("Events: Syslog application"),
                        help = _("Use this syslog application for all created events"),
                        elements = [
                            FixedValue(None,
                                title = _("Use the mail subject"),
                                totext = _("The mail subject is used as syslog appliaction"),
                            ),
                            TextUnicode(
                                title = _("Specify the application"),
                                help = _("Use this text as application. You can use macros like <tt>\\1</tt>, <tt>\\2</tt>, ... "
                                         "here when you configured <i>subject matching</i> in this rule with a regular expression "
                                         "that declares match groups (using braces)."),
                                allow_empty = False,
                            ),
                        ]
                    )),
                    ('host', TextAscii(
                        title = _('Events: Hostname'),
                        help = _('Use this hostname for all created events instead of the name of the mailserver'),
                    )),
                    ('body_limit', Integer(
                        title = _('Limit length of mail body'),
                        help = _('When forwarding mails from the mailbox to the event console, the '
                                 'body of the mail is limited to the given number of characters.'),
                        default_value = 1000,
                    )),
                    ('cleanup', Alternative(
                        title = _("Cleanup messages"),
                        help = _("The handled messages (see <i>subject matching</i>) can be cleaned up by either "
                                 "deleting them or moving them to a subfolder. By default nothing is cleaned up."),
                        elements = [
                            FixedValue(True,
                                title = _('Delete messages'),
                                totext = _('Delete all processed message belonging to this check'),
                            ),
                            TextUnicode(
                                title = _("Move to subfolder"),
                                help = _("Specify the destination path in the format <tt>Path/To/Folder</tt>, for example"
                                         "<tt>INBOX/Processed_Mails</tt>."),
                                allow_empty = False,
                            ),
                        ]
                    )),
                ]
            )),
        ]
    ),
    match = 'all'
)
