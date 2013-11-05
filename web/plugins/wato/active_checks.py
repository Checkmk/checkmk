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

register_rulegroup("activechecks",
    _("Active checks (HTTP, TCP, etc.)"),
    _("Configure active networking checks like HTTP and TCP"))
group = "activechecks"

register_rule(group,
    "active_checks:dns",
    Tuple(
        title = _("Check DNS service"),
        help = _("Check the resultion of a hostname into an IP address by a DNS server. "
                 "This check uses <tt>check_dns</tt> from the standard Nagios plugins."),
        elements = [
           TextAscii(title = _("Hostname"), allow_empty = False,
                     help = _('The name or address you want to query')),
           Dictionary(
               title = _("Optional parameters"),
               elements = [
                   ( "server",
                     TextAscii(
                         title = _("DNS Server"),
                         allow_empty = False,
                         help = _("Optional DNS server you want to use for the lookup"))),
                   ( "expected_address",
                     TextAscii(
                         title = _("Expected Address"),
                         allow_empty = False,
                         help = _("Optional IP-ADDRESS you expect the DNS server to return. HOST"
                                  "must end with a dot (.) " )),
                   ),
                   ( "expected_authority",
                     FixedValue(
                         value  = True,
                         title  = _("Expect Authoritative DNS Server"),
                         totext = _("Expect Authoritative"),
                         help   = _("Optional expect the DNS server to be authoriative"
                                    "for the lookup ")),
                   ),
                   ( "response_time",
                     Tuple(
                         title = _("Expected response time"),
                         elements = [
                             Float(
                                 title = _("Warning at"),
                                 unit = "sec",
                                 default_value = 1),
                             Float(
                                 title = _("Critical at"),
                                 unit = "sec",
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
    match = 'all')


register_rule(group,
    "active_checks:tcp",
    Tuple(
        title = _("Check connecting to a TCP port"),
        help = _("This check test the connection to a TCP port. It uses "
                 "<tt>check_tcp</tt> from the standard Nagios plugins."),
        elements = [
           Integer(title = _("TCP Port"), minvalue=1, maxvalue=65535),
           Dictionary(
               title = _("Optional parameters"),
               elements = [
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
                                 title = _("Warning at"),
                                 unit = "ms",
                                 default_value = 100.0),
                             Float(
                                 title = _("Critical at"),
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
    match = 'all')


register_rule(group,
    "active_checks:http",
    Tuple(
        title = _("Check HTTP service"),
        help = _("Check HTTP/HTTPS service using the plugin <tt>check_http</tt> "
                 "from the standard Nagios Plugins. "
                 "This plugin tests the HTTP service on the specified host. "
                 "It can test normal (HTTP) and secure (HTTPS) servers, follow "
                 "redirects, search for strings and regular expressions, check "
                 "connection times, and report on certificate expiration times. "),
        elements = [
            TextUnicode(
                title = _("Name"),
                help = _("Will be used in the service description"),
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
                                    "virtual host for the query (using HTTP/1.1). When you "
                                    "leave this empty, then the IP address of the host "
                                    "will be used instead."),
                                   allow_empty = False),
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
                               default_value = "/")
                           ),
                           ( "port",
                             Integer(
                               title = _("TCP Port"),
                               minvalue = 1,
                               maxvalue = 65535,
                               default_value = 80)
                           ),
                           ( "ssl",
                             FixedValue(
                                 value = True,
                                 totext = _("use SSL/HTTPS"),
                                 title = _("Use SSL/HTTPS for the connection."))
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
                                         title = _("Warning at"),
                                         unit = "ms",
                                         default_value = 100.0),
                                     Float(
                                         title = _("Critical at"),
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
                                          allow_empty = False),
                                      TextAscii(
                                          title = _("Password"),
                                          size = 12,
                                          allow_empty = False),
                                  ])
                            ),
                            ( "proxy_auth",
                              Tuple(
                                  title = _("Proxy-Authorization"),
                                  help = _("Credentials for HTTP Proxy with basic authentication"),
                                  elements = [
                                      TextAscii(
                                          title = _("Username"),
                                          size = 12,
                                          allow_empty = False),
                                      TextAscii(
                                          title = _("Password"),
                                          size = 12,
                                          allow_empty = False),
                                  ])
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
                                  default_value = 'follow'),
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
                              Tuple(
                                  title = _("Regular expression to expect in content"),
                                  orientation = "vertical",
                                  show_titles = False,
                                  elements = [
                                      RegExp(label = _("Regular expression: ")),
                                      Checkbox(label = _("Case insensitive")),
                                      Checkbox(label = _("return CRITICAL if found, OK if not")),
                                  ])
                            ),
                            ( "post_data",
                              Tuple(
                                  title = _("Send HTTP POST data"),
                                  elements = [
                                      TextAscii(
                                          title = _("HTTP POST data"),
                                          help = _("Data to send via HTTP POST method. "
                                                   "Please make sure, that the data is URL-encoded."),
                                          size = 40,
                                      ),
                                      TextAscii(
                                          title = _("Content-Type"),
                                          default_value = "text/html"),
                                 ])
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
                                  ])
                            ),
                            ( "no_body",
                              FixedValue(
                                  value = True,
                                  title = _("Don't wait for document body"),
                                  help = _("Note: this still does an HTTP GET or POST, not a HEAD."),
                                  totext = _("dont wait for body"))
                            ),
                            ( "page_size",
                              Tuple(
                                  title = _("Page size to expect"),
                                  elements = [
                                      Integer(title = _("Minimum"), unit=_("Bytes")),
                                      Integer(title = _("Maximum"), unit=_("Bytes")),
                                  ])
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
                               Integer(
                                   title = _("Age"),
                                   help = _("Minimum number of days a certificate has to be valid. "
                                            "Port defaults to 443. When this option is used the URL "
                                            "is not checked."),
                                   unit = _("days"),
                               )
                            ),
                            ( "cert_host",
                                TextAscii(
                                    title = _("Check Cerficate on diffrent IP/ DNS Name"),
                                    help = _("For each SSL cerficate on a host, a diffrent IP address is needed. "
                                             "Here you can specify there address if it differs from the  "
                                             "address from the host primary address."),
                                )
                            ),
                            ("port",
                                Integer(
                                    title = _("TCP Port"),
                                    minvalue = 1,
                                    maxvalue = 65535,
                                    default_value = 443,
                                )
                            ),
                        ],
                        required_keys = [ "cert_days" ],
                    ),
                ]
            ),
        ]
    ),
    match = 'all')

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
                             TextAscii(
                                 title = _("Password"),
                                 help = _("Password for binding, if you server requires an authentication"),
                                 allow_empty = False,
                                 size = 20,
                             )
                        ]
                      )
                   ),
                   ( "port",
                     Integer(
                       title = _("TCP Port"),
                       help = _("Default is 389 for normal connetions and 636 for SSL connections."),
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
                                 title = _("Warning at"),
                                 unit = "ms",
                                 default_value = 1000.0),
                             Float(
                                 title = _("Critical at"),
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
                         help = _("You can specify a hostname or IP address different from IP address "
                                  "of the host as configured in your host properties."))),
                   ( "port",
                     TextAscii(
                         title = _("TCP Port to connect to"),
                         help = _("The TCP Port the SMTP server is listening on. "
                                  "The default is <tt>25</tt>."),
                         size = 5,
                         allow_empty = False,
                         default_value = "25",
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
                          totext = "STARTTLS enabled.",
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
                             TextAscii(
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
                                 title = _("Warning at"),
                                 unit = "sec"
                             ),
                             Integer(
                                 title = _("Critical at"),
                                 unit = "sec"
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
        ]),
    match = 'all'
)

register_rule(group,
    "custom_checks",
    Dictionary(
        title = _("Classical active and passive Nagios checks"),
        help = _("With this ruleset you can configure &quot;classical Nagios checks&quot; "
                 "to be executed directly on your monitoring server. These checks "
                 "will not use Check_MK. It is also possible to configure passive "
                 "checks that are fed with data from external sources via the Nagios "
                 "command pipe."),
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
              TextAscii(
                  title = _("Command line"),
                  help = _("Please enter the complete shell command including "
                           "path name and arguments to execute. You can use Nagios "
                           "macros here. The most important are:<ul>"
                           "<li><tt>$HOSTADDRESS$</tt>: The IP address of the host</li>"
                           "<li><tt>$HOSTNAME$</tt>: The name of the host</li>"
                           "<li><tt>$USER1$</tt>: user macro 1 (usually path to shipped plugins)</li>"
                           "<li><tt>$USER2$</tt>: user marco 2 (usually path to your own plugins)</li>"
                           "</ul>"
                           "If you are using OMD, then you can omit the path and just specify "
                           "the command (e.g. <tt>check_foobar</tt>). This command will be "
                           "searched first in the local plugins directory "
                           "(<tt>~/local/lib/nagios/plugins</tt>) and then in the shipped plugins "
                           "directory (<tt>~/lib/nagios/plugins</tt>) within your site directory.<br><br>"
                           "<b>Passive checks</b>: Do no specify a command line if you want "
                           "to define passive checks."),
                  size = 80,
               )
            ),
            ( "command_name",
              TextAscii(
                  title = _("Internal command name"),
                  help = _("If you want, then you can specify a name that will be used "
                           "in the <tt>define command</tt> section for these checks. This "
                           "allows you to a assign a customer PNP template for the performance "
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
                  help = _("Freshness checking is only useful for passive checks. It makes sure that passive "
                           "check results are submitted on a regular base. If not, the check is being set to "
                           "warning, critical or unknown."),
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
                            title = _("Plugin output in case of absent abdates"),
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

