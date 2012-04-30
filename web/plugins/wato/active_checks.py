register_rulegroup("activechecks",
    _("Active checks (HTTP, TCP, etc.)"),
    _("These rules are used for configuring agent-less networking checks like "
      "checking HTTP servers or TCP ports."))
group = "activechecks"

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
                   ( "response_time",
                     Tuple(
                         title = _("Expected response time"),
                         elements = [
                             Float(title = _("Warning at"), unit = "ms"),
                             Float(title = _("Critical at"), unit = "ms"),
                         ])
                    ),
                    ( "refuse_state",
                      DropdownChoice(
                          title = _("State for connection refusal"),
                          choices = [ ('crit', _("CRITICAL")),
                                      ('warn', _("WARNING")),
                                      ('ok',   _("OK")),
                                    ])
                    ),
# Das hier fehlt noch:
#  -m, --maxbytes=INTEGER
#     Close connection once more than this number of bytes are received
#  -d, --delay=INTEGER
#     Seconds to wait between sending string and polling for response
#  -D, --certificate=INTEGER
#     Minimum number of days a certificate has to be valid.
#  -S, --ssl
#     Use SSL for the connection.
#  -t, --timeout=INTEGER
#     Seconds before connection times out (default: 10)
# Und dann fehlt noch bei den meisten die Umseztung in Parameter


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
                    ( "quit_string",
                      TextAscii(
                          title = _("Final string to send"),
                          help = _("String to send server to initiate a clean close of "
                                   "the connection"),
                          size = 30)
                    ),
                    ( "mismatch_state",
                      DropdownChoice(
                          title = _("State for expected string mismatch"),
                          choices = [ ('crit', _("CRITICAL")),
                                      ('warn', _("WARNING")),
                                      ('ok',   _("OK")),
                                    ])
                    ),
                ]),
        ]
    ),
    match = 'all')



