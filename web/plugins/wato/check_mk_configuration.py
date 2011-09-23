#!/usr/bin/python
# encoding: utf-8

register_configvar(_("Networking"), 
                   "tcp_connect_timeout", 
                   Float(title = _("Agent TCP connect timeout (sec)"),
                         help = _("Timeout for TCP connect to agent in seconds. If the agent does "
                                  "not respond within this time, it is considered to be unreachable. "
                                  "Note: This does <b>not</b> limit the time the agent needs to "
                                  "generate its output."),
                        minvalue = 1.0))


register_configvar(_("Internal Settings"),
                   "cluster_max_cachefile_age",
                   Integer(title = _("Maximum cache file age for clusters"),
                           help = _("The number of seconds a cache file may be old if check_mk should " 
                                    "use it instead of getting information from the target hosts while " 
                                    "checking a cluster. Per default this is enabled and set to 90 seconds. " 
                                    "If your check cycle is not set to a larger value then one minute then "
                                    "you should increase this accordingly.")))

register_configvar(_("Internal Settings"),
                   "always_cleanup_autochecks",
                   Checkbox(title = _("Always cleanup autochecks"),
                            help = _("When switched on, Check_MK will always cleanup the autochecks files "
                                     "after each inventory, i.e. create one file per host. This is the same "
                                     "as adding the option <tt>-u</tt> to each call of <tt>-I</tt> on the "
                                     "command line.")))
