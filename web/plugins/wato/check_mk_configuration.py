#!/usr/bin/python
# encoding: utf-8

group = _("Networking")

register_configvar(group,
                   "tcp_connect_timeout", 
                   Float(title = _("Agent TCP connect timeout (sec)"),
                         help = _("Timeout for TCP connect to agent in seconds. If the agent does "
                                  "not respond within this time, it is considered to be unreachable. "
                                  "Note: This does <b>not</b> limit the time the agent needs to "
                                  "generate its output."),
                        minvalue = 1.0))


group = _("Internal Settings") 

register_configvar(group,
                   "debug_log",
                   Optional(Filename(),
                         title = _("Logfile for debugging errors in checks"),
                         help = _("If this option is used and set to a filename, Check_MK will create a debug logfile " 
                                  "containing details about failed checks (those which have state UNKNOWN " 
                                  "and the output UNKNOWN - invalid output from plugin.... Per default no "
                                  "logfile is written.")))

register_configvar(group,
                   "cluster_max_cachefile_age",
                   Integer(title = _("Maximum cache file age for clusters"),
                           help = _("The number of seconds a cache file may be old if check_mk should " 
                                    "use it instead of getting information from the target hosts while " 
                                    "checking a cluster. Per default this is enabled and set to 90 seconds. " 
                                    "If your check cycle is not set to a larger value then one minute then "
                                    "you should increase this accordingly.")))

register_configvar(group,
                   "always_cleanup_autochecks",
                   Checkbox(title = _("Always cleanup autochecks"),
                            help = _("When switched on, Check_MK will always cleanup the autochecks files "
                                     "after each inventory, i.e. create one file per host. This is the same "
                                     "as adding the option <tt>-u</tt> to each call of <tt>-I</tt> on the "
                                     "command line.")))

register_configvar(group,
                   "check_submission",
                   DropdownChoice(title = _("Check submission method"),
                        help = _("If you set this to <b>Nagios command pipe</b>, then Check_MK will write its "
                                 "check results into the Nagios command pipe. This is the classical way. "
                                 "Choosing <b>Create check files</b> "
                                 "skips one phase in the Nagios core and directly create Nagios check files. "
                                 "The reduces the overhead but might not be compatible with other monitoring "
                                 "cores."),
                        choices = [ ("pipe", _("Nagios command pipe")),
                                    ("file", _("Create check files")) ]))
