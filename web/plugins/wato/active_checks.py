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
                          label = _("sec"),
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
                          label = _("sec"),
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
                          label = _("days"),
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



