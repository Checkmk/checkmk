#!/usr/bin/python
# encoding: utf-8

#   +----------------------------------------------------------------------+
#   |           ____             __ _                                      |
#   |          / ___|___  _ __  / _(_) __ ___   ____ _ _ __ ___            |
#   |         | |   / _ \| '_ \| |_| |/ _` \ \ / / _` | '__/ __|           |
#   |         | |__| (_) | | | |  _| | (_| |\ V / (_| | |  \__ \           |
#   |          \____\___/|_| |_|_| |_|\__, | \_/ \__,_|_|  |___/           |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   | Configuration variables for main.mk                                  |
#   +----------------------------------------------------------------------+

group = _("Configuration of Checks")

# ignored_checktypes --> Hier brauchen wir noch einen neuen Value-Typ

group = _("Operation mode of Check_MK") 

register_configvar(group,
    "tcp_connect_timeout", 
    Float(title = _("Agent TCP connect timeout (sec)"),
          help = _("Timeout for TCP connect to agent in seconds. If the agent does "
                   "not respond within this time, it is considered to be unreachable. "
                   "Note: This does <b>not</b> limit the time the agent needs to "
                   "generate its output."),
          minvalue = 1.0))


register_configvar(group,
    "simulation_mode",
    Checkbox(title = _("Simulation mode"),
             label = _("Run in simulation mode"),
             help = _("This boolean variable allows you to bring check_mk into a dry run mode. "
                      "No hosts will be contacted, no DNS lookups will take place and data is read "
                      "from cache files that have been created during normal operation or have "
                      "been copied here from another monitoring site.")))


register_configvar(group,
    "delay_precompile",
    Checkbox(title = _("Delay precompiling of host checks"),
             label = _("delay precompiling"),
             help = _("If you enable this option, then Check_MK will not directly Python-bytecompile "
                      "all host checks when activating the configuration and restarting Nagios. "
                      "Instead it will delay this to the first "
                      "time the host is actually checked being by Nagios.<p>This reduces the time needed "
                      "for the operation, but on the other hand will lead to a slightly higher load "
                      "of Nagios for the first couple of minutes after the restart. ")))


register_configvar(group,
    "debug_log",
    Optional(Filename(label = _("Absolute path to log file")),
          title = _("Logfile for debugging errors in checks"),
          label = _("Activate logging errors into a logfile"),
          help = _("If this option is used and set to a filename, Check_MK will create a debug logfile " 
                   "containing details about failed checks (those which have state UNKNOWN " 
                   "and the output UNKNOWN - invalid output from plugin.... Per default no "
                   "logfile is written.")))

register_configvar(group,
    "cluster_max_cachefile_age",
    Integer(title = _("Maximum cache file age for clusters"),
            label = _("seconds"),
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

#   +----------------------------------------------------------------------+
#   |                         ____        _                                |
#   |                        |  _ \ _   _| | ___                           |
#   |                        | |_) | | | | |/ _ \                          |
#   |                        |  _ <| |_| | |  __/                          |
#   |                        |_| \_\\__,_|_|\___|                          |
#   |                                                                      |
#   |       ____            _                 _   _                        |
#   |      |  _ \  ___  ___| | __ _ _ __ __ _| |_(_) ___  _ __  ___        |
#   |      | | | |/ _ \/ __| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |_| |  __/ (__| | (_| | | | (_| | |_| | (_) | | | \__ \       |
#   |      |____/ \___|\___|_|\__,_|_|  \__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Declaration of rules to be defined in main.mk or in folders          |
#   +----------------------------------------------------------------------+

group = _("Check Parameters")
register_rule(group, 
    "checkgroup_parameters:cpu_load",
    Tuple(title = _("Levels for CPU load (not utilization!)"), 
          help = _("The CPU load of a system is the number of processes currently being "
                   "in the state <u>running</u>, i.e. either they occupy a CPU or wait "
                   "for one. The <u>load average</u> is the averaged CPU load over the last 1, "
                   "5 or 15 minutes. The following levels will be applied on the average "
                   "load. On Linux system the 15-minute average load is used when applying "
                   "those levels."),
          elements = [
              Integer(title = _("Warning at a load of")),
              Integer(title = _("Critical at a load of"))]),
    )

group = _("Monitoring Configuration") 

register_rule(group, 
    "extra_host_conf:max_check_attempts",
    Integer(title = _("Maximum number of check attempts for host"), 
            help = _("The maximum number of failed host checks until the host will be considered "
                     "in a hard down state"),
            minvalue = 1))

register_rule(group, 
    "extra_service_conf:max_check_attempts",
    Integer(title = _("Maximum number of check attempts for service"), 
            help = _("The maximum number of failed checks until a service problem state will "
                     "be considered as <u>hard</u>. Only hard state trigger notifications. "),
            minvalue = 1),
    itemtype = "service")

register_rule(group,
    "ignored_services",
    title = _("Ignored services"),
    help = _("Services that are declared as <u>ignored</u> by this rule set will not be added "
             "to a host during inventory (automatic service detection). Services that already "
             "exist will continued to be monitored but be marked as obsolete in the service "
             "list of a host."),
    itemtype = "service")

group = _("SNMP")

register_rule(group,
    "snmp_communities",
    TextAscii(title = _("SNMP communities of monitored hosts"),
              help = _("Check_MK needs an SNMP <i>community</i> - a kind of password - for each "
                       "host to be monitored via SNMP. Please check the settings of your monitored "
                       "devices if you are unsure about the community."),
              allow_empty = False))

group = _("Operation mode of Check_MK") 

register_rule(group,
    "agent_ports",
    Integer(title = _("TCP port for connection to Check_MK agent"),
            help = _("This variable allows to specify the TCP port to " 
                     "be used to connect to the agent on a per-host-basis. "),
            min_value = 1,
            max_value = 65535))


register_rule(group,
    "dyndns_hosts",
    title = _("Hosts with dynamic DNS lookup during monitoring"),
    help = _("This ruleset selects host for dynamic DNS lookup during monitoring. Normally "
             "the IP addresses of hosts are statically configured or looked up when you "
             "activate the changes. In some rare cases DNS lookups must be done each time "
             "a host is connected to, e.g. when the IP address of the host is dynamic "
             "and can change."))
