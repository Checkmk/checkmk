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

group = _("Multisite & WATO")

register_configvar(group,
    "debug",
    Checkbox(title = _("Debug mode"),
             label = _("enable debug mode"),
             help = _("When Multisite is running in debug mode, internal Python error messages "
                      "are being displayed and various debug information in other places is "
                      "also available."),
            default_value = False),
    domain = "multisite")

register_configvar(group,
    "profile",
    Checkbox(
        title = _("Profile requests"),
        label = _("enable profile mode"),
        help = _("It is possible to profile the rendering process of Multisite pages. This "
                 "Is done using the Python module cProfile. When enabled two files are placed "
                 "into the Multisite var directory named <code>multisite.profile</code> and "
                 "<code>multisite.profile.py</code>. By executing the later file you can get "
                 "runtime statistics about the last processed page."),
       default_value = False
    ),
    domain = "multisite"
)

register_configvar(group,
    "debug_livestatus_queries",
    Checkbox(title = _("Debug Livestatus queries"),
             label = _("enable debug of Livestatus queries"),
             help = _("With this option turned on all Livestatus queries made by Multisite "
                      "in order to render views are being displayed."),
            default_value = False),
    domain = "multisite")

register_configvar(group,
    "buffered_http_stream",
    Checkbox(title = _("Buffered HTTP stream"),
             label = _("enable buffering"),
             help = _("When buffering the HTTP stream is enabled, then Multisite "
                      "will not send single TCP segments for each particle of HTML "
                      "output but try to make larger segments. This saves bandwidth "
                      "especially when using HTTPS. On the backside there might be "
                      "a higher latency for the beginning of pages being displayed."),
            default_value = True),
    domain = "multisite")

register_configvar(group,
    "selection_livetime",
    Integer(
        title = _('Checkbox Selection Livetime'),
        help  = _('This option defines the maximum age of unmodified checkbox selections stored for users. '
                  'If a user modifies the selection in a view, these selections are persisted for the currently '
                  'open view. When a view is re-opened a new selection is used. The old one remains on the '
                  'server until the livetime is exceeded.'),
        minvalue = 1,
        default_value = 3600,
    ),
    domain = "multisite",
)

register_configvar(group,
    "show_livestatus_errors",
    Checkbox(title = _("Show MK Livestatus error messages"),
             label = _("show errors"),
             help = _("This option controls whether error messages from unreachable sites are shown in the output of "
                      "views. Those error messages shall alert you that not all data from all sites has been shown. "
                      "Other people - however - find those messages distracting. "),
             default_value = True),
    domain = "multisite")

register_configvar(group,
    "enable_sounds",
    Checkbox(title = _("Enabled sounds in views"),
             label = _("enable sounds"),
             help = _("If sounds are enabled then the user will be alarmed by problems shown "
                      "in a Multisite status view if that view has been configured for sounds. "
                      "From the views shipped in with Multisite all problem views have sounds "
                      "enabled."),
             default_value = True),
    domain = "multisite")

register_configvar(group,
    "context_buttons_to_show",
    Optional(
        Integer(
            title = _("show"),
            label = _("buttons"),
            minvalue = 1,
            maxvalue = 100,
            size = 2),
        default_value = 5,
        title = _("Number of context buttons to show"),
        label = _("Show only most frequently used buttons"),
        help = _("If this option is enabled, then Multisite only show the most "
                 "used context buttons and hides the rest. Which buttons are used "
                 "how often is computed separately per user.")),
    domain = "multisite")


register_configvar(group,
    "soft_query_limit",
    Integer(title = _("Soft query limit"),
            help = _("Whenever the number of returned datasets of a view would exceed this "
                     "limit, a warning is being displayed and no further data is being shown. "
                     "A normal user can override this limit with one mouse click."),
            minvalue = 1,
            default_value = 1000),
    domain = "multisite")

register_configvar(group,
    "hard_query_limit",
    Integer(title = _("Hard query limit"),
            help = _("Whenever the number of returned datasets of a view would exceed this "
                     "limit, an error message is shown. The normal user cannot override "
                     "the hard limit. The purpose of the hard limit is to secure the server "
                     "against useless queries with huge result sets."),
            minvalue = 1,
            default_value = 5000),
    domain = "multisite")

register_configvar(group,
    "quicksearch_dropdown_limit",
    Integer(title = _("Number of elements to show in Quicksearch"),
            help = _("When typing a texts in the Quicksearch snapin, a dropdown will "
                     "appear listing all matching host names containing that text. "
                     "That list is limited in size so that the dropdown will not get "
                     "too large when you have a huge number of lists. "),
            minvalue = 1,
            default_value = 80),
    domain = "multisite")

register_configvar(group,
    "start_url",
    TextAscii(title = _("Start-URL to display in main frame"),
              help = _("When you point your browser to the Multisite GUI, usually the dashboard "
                       "is shown in the main (right) frame. You can replace this with any other "
                       "URL you like here."),
              size = 80,
              default_value = "dashboard.py"),
    domain = "multisite")

register_configvar(group,
    "page_heading",
    TextUnicode(title = _("HTML-Title of HTML Multisite GUI"),
              help = _("This title will be displayed in your browser's title bar or tab. If you are "
                       "using OMD then you can embed a <tt>%s</tt>. This will be replaced by the name "
                       "of the OMD site."),
              size = 80,
              default_value = u"Check_MK %s"),
    domain = "multisite")

register_configvar(group,
    "wato_hide_filenames",
    Checkbox(title = _("Hide internal folder names in WATO"),
             label = _("hide folder names"),
             help = _("When enabled, then the internal names of WATO folder in the filesystem "
                      "are not shown. They will automatically be derived from the name of the folder "
                      "when a new folder is being created. Disable this option if you want to see and "
                      "set the filenames manually."),
             default_value = True),
    domain = "multisite")

register_configvar(group,
    "wato_hide_hosttags",
    Checkbox(title = _("Hide hosttags in WATO folder view"),
             label = _("hide hosttags"),
             help = _("When enabled, hosttags are no longer shown within the WATO folder view"),
             default_value = False),
    domain = "multisite")

register_configvar(group,
    "wato_hide_varnames",
    Checkbox(title = _("Hide names of configuration variables"),
             label = _("hide variable names"),
             help = _("When enabled, internal configuration variable names of Check_MK are hidded "
                      "from the user (for example in the rule editor)"),
             default_value = True),
    domain = "multisite")

register_configvar(group,
    "wato_max_snapshots",
    Integer(title = _("Number of configuration snapshots to keep"),
            help = _("Whenever you successfully activate changes a snapshot of the configuration "
                     "will be created. You can also create snapshots manually. WATO will delete old "
                     "snapshots when the maximum number of snapshots is reached."),
             minvalue = 1,
             default_value = 50),
    domain = "multisite")

register_configvar(group,
    "reschedule_timeout",
    Float(title = _("Timeout for rescheduling checks in Multisite"),
          help = _("When you reschedule a check by clicking on the &quot;arrow&quot;-icon "
                   "then Multisite will use this number of seconds as a timeout. If the "
                   "monitoring core has not executed the check within this time, an error "
                   "will be displayed and the page not reloaded."),
          minvalue = 1.0,
          default_value = 10.0,
          unit = "sec",
          display_format = "%.1f"),
    domain = "multisite")

register_configvar(group,
    "sidebar_update_interval",
    Float(title = _("Interval of sidebar status updates"),
          help = _("The information provided by the sidebar snapins is refreshed in a regular "
                   "interval. You can change the refresh interval to fit your needs here. This "
                   "value means that all snapnis which request a regular refresh are updated "
                   "in this interval."),
          minvalue = 10.0,
          default_value = 30.0,
          unit = "sec",
          display_format = "%.1f"),
    domain = "multisite")

register_configvar(group,
    "wato_activation_method",
    DropdownChoice(
        title = _("WATO restart mode for Nagios"),
        help = _("Should WATO restart or reload Nagios when activating changes"),
        choices = [
            ('restart', _("Restart")),
            ('reload' , _("Reload") ),
            ]),
    domain = "multisite"
    )


register_configvar(group,
    "bi_precompile_on_demand",
    Checkbox(title = _("Precompile aggregations on demand"),
             label = _("Only precompile on demand"),
             help = _(
                "By default all aggregations in Check_MK BI are precompiled on first "
                "usage of a BI or host/service related dialog in the status GUI. "
                "In case of large environments with many BI aggregations this complete "
                "precompilation might take too much time (several seconds). It is now possible "
                "to change the precompilation to be executed on demand. BI only precompiles the "
                "aggregations which are really requested by the users."
             ),
             default_value = False),
    domain = "multisite")

register_configvar(group,
    "bi_compile_log",
    Optional(
        Filename(
            label = _("Absolute path to log file"),
            default = defaults.var_dir + '/web/bi-compile.log',
        ),
          title = _("Logfile for BI compilation diagnostics"),
          label = _("Activate logging of BI compilations into a logfile"),
          help = _("If this option is used and set to a filename, Check_MK BI will create a logfile "
                   "containing details about compiling BI aggregations. This includes statistics and "
                   "details for each executed compilation.")),
    domain = "multisite")

#   .----------------------------------------------------------------------.
#   |          _   _                 __  __                 _              |
#   |         | | | |___  ___ _ __  |  \/  | __ _ _ __ ___ | |_            |
#   |         | | | / __|/ _ \ '__| | |\/| |/ _` | '_ ` _ \| __|           |
#   |         | |_| \__ \  __/ |    | |  | | (_| | | | | | | |_            |
#   |          \___/|___/\___|_|    |_|  |_|\__, |_| |_| |_|\__|           |
#   |                                       |___/                          |
#   +----------------------------------------------------------------------+

group = _("User Management")

register_configvar(group,
    "user_connectors",
    ListChoice(
        title = _('Enabled User Connectors'),
        help  = _('The Multisite User Management code is modularized, the modules '
                  'are called user connectors. A user connector can hook into multisite '
                  'at several places where users are handled. Examples are the authentication '
                  'or saving of user accounts. Here you can enable one or several connectors '
                  'to extend or replace the default authentication mechanism (htpasswd) e.g. '
                  'with ldap based mechanism.'),
        default_value = [ 'htpasswd' ],
        choices       = userdb.list_user_connectors,
        allow_empty   = False,
    ),
    domain = "multisite",
)

register_configvar(group,
    "ldap_connection",
    Dictionary(
        title = _("LDAP Connection Settings"),
        help  = _("This option configures all LDAP specific connection options. These options "
                  "are used by the LDAP user connector."),
        elements = [
            ("server", TextAscii(
                title = _("LDAP Server"),
                help = _("Set the host address of the LDAP server. Might be an IP address or "
                         "resolvable hostname."),
                allow_empty = False,
            )),
            ("port", Integer(
                title = _("TCP Port"),
                help  = _("This variable allows to specify the TCP port to "
                          "be used to connect to the LDAP server. "),
                minvalue = 1,
                maxvalue = 65535,
                default_value = 389,
            )),
            ("use_ssl", FixedValue(
                title  = _("Use SSL"),
                help   = _("Connect to the LDAP server with a SSL encrypted connection."),
                value  = True,
                totext = _("Encrypt the network connection using SSL."),
            )),
            ("connect_timeout", Float(
                title = _("LDAP Connect Timeout (sec)"),
                help = _("Timeout for the initial connection to the LDAP server in seconds."),
                minvalue = 1.0,
                default_value = 2.0,
            )),
            ("version", DropdownChoice(
                title = _("LDAP Version"),
                help  = _("Select the LDAP version the LDAP server is serving. Most modern "
                          "servers use LDAP version 3."),
                choices = [ (2, "2"), (3, "3") ],
                default_value = 3,
            )),
            ("type", DropdownChoice(
                title = _("Directory Type"),
                help  = _("Select the software the LDAP directory is based on. Depending on "
                          "the selection e.g. the attribute names used in LDAP queries will "
                          "be altered."),
                choices = [
                    ("ad",       _("Active Directory")),
                    ("openldap", _("OpenLDAP")),
                ],
            )),
            ("bind", Tuple(
                title = _("LDAP Bind Credentials"),
                help  = _("Set the credentials to be used to connect to the LDAP server. The "
                          "used account must not be allowed to do any changes in the directory "
                          "the whole connection is read only. "
                          "In some environment an anonymous connect/bind is allowed, in this "
                          "case you don't have to configure anything here."
                          "It must be possible to list all needed user and group objects from the "
                          "directory."),
                elements = [
                    LDAPDistinguishedName(
                        title = _("Bind DN"),
                        help  = _("Specify the distinguished name to be used to bind to "
                                  "the LDAP directory."),
                        size = 80,
                    ),
                    Password(
                        title = _("Bind Password"),
                        help  = _("Specify the password to be used to bind to "
                                  "the LDAP directory."),
                    ),
                ],
            )),
        ],
        optional_keys = ['use_ssl', 'bind', ],
    ),
    domain = "multisite",
)

register_configvar(group,
    "ldap_userspec",
    Dictionary(
        title = _("LDAP User Settings"),
        help  = _("This option configures all user related LDAP options. These options "
                  "are used by the LDAP user connector to find the needed users in the LDAP directory."),
        elements = [
            ("dn", LDAPDistinguishedName(
                title = _("User Base DN"),
                help  = _("The base distinguished name to be used when performing user account "
                          "related queries to the LDAP server."),
                size = 80,
            )),
            ("scope", DropdownChoice(
                title = _("Search Scope"),
                help  = _("Scope to be used in LDAP searches. In most cases \"sub\" is the best choice. "
                          "It searches for matching objects in the given base and the whole subtree."),
                choices = [
                    ("sub",  _("Search whole subtree below the base DN")),
                    ("base", _("Search only the entry at the base DN")),
                    ("one",  _("Search all entries one level below the base DN")),
                ],
                default_value = "sub",
            )),
            ("filter", TextAscii(
                title = _("Search Filter"),
                help = _("Using this option you can define an optional LDAP filter which is used during "
                         "LDAP searches. It can be used to only handle a subset of the users below the given "
                         "base DN."),
                size = 80,
                default_value = lambda: userdb.ldap_filter('users', False),
            )),
            ("user_id", TextAscii(
                title = _("User-ID Attribute"),
                help  = _("The attribute used to identify the individual users. It must have "
                          "unique values to make an user identifyable by the value of this "
                          "attribute."),
                default_value = lambda: userdb.ldap_attr('user_id'),
            )),
            ("lower_user_ids", FixedValue(
                title  = _("Lower Case User-IDs"),
                help   = _("Convert imported User-IDs to lower case during synchronisation."),
                value  = True,
                totext = _("Enforce lower case User-IDs."),
            )),
        ],
        optional_keys = ['scope', 'filter', 'user_id', 'lower_user_ids'],
    ),
    domain = "multisite",
)

register_configvar(group,
    "ldap_groupspec",
    Dictionary(
        title = _("LDAP Group Settings"),
        help  = _("This option configures all group related LDAP options. These options "
                  "are only needed when using group related attribute synchonisation plugins."),
        elements = [
            ("dn", LDAPDistinguishedName(
                title = _("Group Base DN"),
                help  = _("The base distinguished name to be used when performing group account "
                          "related queries to the LDAP server."),
                size = 80,
            )),
            ("scope", DropdownChoice(
                title = _("Search Scope"),
                help  = _("Scope to be used in group related LDAP searches. In most cases \"sub\" "
                          "is the best choice. It searches for matching objects in the given base "
                          "and the whole subtree."),
                choices = [
                    ("sub",  _("Search whole subtree below the base DN")),
                    ("base", _("Search only the entry at the base DN")),
                    ("one",  _("Search all entries one level below the base DN")),
                ],
                default_value = "sub",
            )),
            ("filter", TextAscii(
                title = _("Search Filter"),
                help = _("Using this option you can define an optional LDAP filter which is used "
                         "during group related LDAP searches. It can be used to only handle a "
                         "subset of the groups below the given base DN."),
                size = 80,
                default_value = lambda: userdb.ldap_filter('groups', False),
            )),
            ("member", TextAscii(
                title = _("Member Attribute"),
                help  = _("The attribute used to identify users group memberships."),
                default_value = lambda: userdb.ldap_attr('member'),
            )),
        ],
        optional_keys = ['scope', 'filter', 'member'],
    ),
    domain = "multisite",
)

register_configvar(group,
    "ldap_active_plugins",
    Dictionary(
        title = _('LDAP Attribute Sync Plugins'),
        help  = _('It is possible to fetch several attributes of users, like Email or full names, '
                  'from the LDAP directory. This is done by plugins which can individually enabled '
                  'or disabled. When enabling a plugin, it is used upon the next synchonisation of '
                  'user accounts for gathering their attributes. The user options which get imported '
                  'into Check_MK from LDAP will be locked in WATO.'),
        elements = userdb.ldap_attribute_plugins_elements,
    ),
    domain = "multisite",
)

register_configvar(group,
    "ldap_cache_livetime",
    Integer(
        title = _('LDAP Cache Livetime'),
        help  = _('This option defines the maximum age for using the cached LDAP data. The time of the '
                  'last LDAP synchronisation is saved and checked on every request to the multisite '
                  'interface. Once the cache gets outdated, a new synchronisation job is started.'),
        minvalue = 1,
        default_value = 300,
    ),
    domain = "multisite",
)

register_configvar(group,
    "ldap_debug_log",
    Optional(
        Filename(
            label = _("Absolute path to log file"),
            default = defaults.var_dir + '/web/ldap-debug.log',
        ),
          title = _("LDAP connection diagnostics"),
          label = _("Activate logging of LDAP transactions into a logfile"),
          help = _("If this option is used and set to a filename, Check_MK will create a logfile "
                   "containing details about connecting to LDAP and the single transactions.")),
    domain = "multisite")


def list_roles():
    roles = userdb.load_roles()
    return [ (i, r["alias"]) for i, r in roles.items() ]

def list_contactgroups():
    contact_groups = userdb.load_group_information().get("contact", {})
    entries = [ (c, contact_groups[c]) for c in contact_groups ]
    entries.sort()
    return entries

register_configvar(group,
    "default_user_profile",
    Dictionary(
        title = _("Default User Profile"),
        help  = _("With this option you can specify the attributes a user which is created during "
                  "its initial login gets added. For example, the default is to add the role \"user\" "
                  "to all automatically created users."),
        elements = [
            ('roles', ListChoice(
                title = _('User Roles'),
                help  = _('Specify the initial roles of an automatically created user.'),
                default_value = [ 'user' ],
                choices = list_roles,
            )),
            ('contactgroups', ListChoice(
                title = _('Contact groups'),
                help  = _('Specify the initial contact groups of an automatically created user.'),
                default_value = [],
                choices = list_contactgroups,
            )),
        ],
        optional_keys = [],
    ),
    domain = "multisite",
)

#   .----------------------------------------------------------------------.
#   |                   _                                      _           |
#   |     ___ _ __ ___ | | __   ___  _ __  _ __ ___   ___   __| | ___      |
#   |    / __| '_ ` _ \| |/ /  / _ \| '_ \| '_ ` _ \ / _ \ / _` |/ _ \     |
#   |   | (__| | | | | |   <  | (_) | |_) | | | | | | (_) | (_| |  __/     |
#   |    \___|_| |_| |_|_|\_\  \___/| .__/|_| |_| |_|\___/ \__,_|\___|     |
#   |                               |_|                                    |
#   +----------------------------------------------------------------------+

group = _("Operation mode of Check_MK")

register_configvar(group,
    "tcp_connect_timeout",
    Float(title = _("Agent TCP connect timeout (sec)"),
          help = _("Timeout for TCP connect to agent in seconds. If the agent does "
                   "not respond within this time, it is considered to be unreachable. "
                   "Note: This does <b>not</b> limit the time the agent needs to "
                   "generate its output."),
          minvalue = 1.0),
    need_restart = True)


register_configvar(group,
    "simulation_mode",
    Checkbox(title = _("Simulation mode"),
             label = _("Run in simulation mode"),
             help = _("This boolean variable allows you to bring check_mk into a dry run mode. "
                      "No hosts will be contacted, no DNS lookups will take place and data is read "
                      "from cache files that have been created during normal operation or have "
                      "been copied here from another monitoring site.")),
    need_restart = True)

register_configvar(group,
    "restart_locking",
    DropdownChoice(
        title = _("Simultanous activation of changes"),
        help = _("When two users simultanously try to activate the changes then "
                 "you can decide to abort with an error (default) or have the requests "
                 "serialized. It is also possible - but not recommended - to turn "
                 "off locking altogether."),
        choices = [
            ('abort', _("Abort with an error")),
            ('ait' ,  _("Wait until the other has finished") ),
            (None ,   _("Disable locking") ),
            ]),
    need_restart = False
    )

register_configvar(group,
    "agent_simulator",
    Checkbox(title = _("SNMP Agent Simulator"),
             label = _("Process stored SNMP walks with agent simulator"),
             help = _("When using stored SNMP walks you can place inline code generating "
                      "dynamic simulation data. This feature can be activated here. There "
                      "is a big chance that you will never need this feature...")),
    need_restart = True)


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
                   "logfile is written.")),
    need_restart = True)

register_configvar(group,
    "cluster_max_cachefile_age",
    Integer(title = _("Maximum cache file age for clusters"),
            label = _("seconds"),
            help = _("The number of seconds a cache file may be old if check_mk should "
                     "use it instead of getting information from the target hosts while "
                     "checking a cluster. Per default this is enabled and set to 90 seconds. "
                     "If your check cycle is not set to a larger value than one minute then "
                     "you should increase this accordingly.")),
    need_restart = True)

register_configvar(group,
    "check_submission",
    DropdownChoice(
        title = _("Check submission method"),
        help = _("If you set this to <b>Nagios command pipe</b>, then Check_MK will write its "
                  "check results into the Nagios command pipe. This is the classical way. "
                  "Choosing <b>Create check files</b> "
                  "skips one phase in the Nagios core and directly creates Nagios check files. "
                  "This reduces the overhead but might not be compatible with other monitoring "
                  "cores."),
        choices = [ ("pipe", _("Nagios command pipe")),
                     ("file", _("Create check files")) ]),
    need_restart = True)

register_configvar(group,
    "check_mk_perfdata_with_times",
    Checkbox(title = _("Check_MK with times performance data"),
             label = _("Return process times within performance data"),
             help = _("Enabling this option results in additional performance data "
                      "for the Check_MK output, giving information regarding the process times. "
                      "It provides the following fields: user_time, system_time, children_user_time "
                      "and children_system_time")),
    need_restart = True)

group = _("Inventory - automatic service detection")

register_configvar(group,
    "inventory_check_interval",
    Optional(
        Integer(title = _("Do inventory check every"),
                label = _("minutes"),
                min_value = 1),
        title = _("Enable regular inventory checks"),
        help = _("If enabled, Check_MK will create one additional check per host "
                 "that does a regular check, if the inventory would find new services "
                 "currently un-monitored.")),
    need_restart = True)

register_configvar(group,
    "inventory_check_severity",
    DropdownChoice(
        title = _("Severity of failed inventory check"),
        help = _("Please select which alarm state the inventory check services "
                 "shall assume in case that un-monitored services are found."),
        choices = [
            (0, _("OK - do not alert, just display")),
            (1, _("Warning") ),
            (2, _("Critical") ),
            (3, _("Unknown") ),
            ]))

_if_portstate_choices = [
                        ( '1', 'up(1)'),
                        ( '2', 'down(2)'),
                        ( '3', 'testing(3)'),
                        ( '4', 'unknown(4)'),
                        ( '5', 'dormant(5)') ,
                        ( '6', 'notPresent(6)'),
                        ( '7', 'lowerLayerDown(7)'),
                        ]

_if_porttype_choices = [
  ("1", "other(1)" ), ("2", "regular1822(2)" ), ("3", "hdh1822(3)" ), ("4", "ddnX25(4)" ),
  ("5", "rfc877x25(5)" ), ("6", "ethernetCsmacd(6)" ), ("7", "iso88023Csmacd(7)" ), ("8",
  "iso88024TokenBus(8)" ), ("9", "iso88025TokenRing(9)" ), ("10", "iso88026Man(10)" ),
  ("11", "starLan(11)" ), ("12", "proteon10Mbit(12)" ), ("13", "proteon80Mbit(13)" ), ("14",
  "hyperchannel(14)" ), ("15", "fddi(15)" ), ("16", "lapb(16)" ), ("17", "sdlc(17)" ), ("18",
  "ds1(18)" ), ("19", "e1(19)" ), ("20", "basicISDN(20)" ), ("21", "primaryISDN(21)" ), ("22",
  "propPointToPointSerial(22)" ), ("23", "ppp(23)" ), ("24", "softwareLoopback(24)" ), ("25",
  "eon(25)" ), ("26", "ethernet3Mbit(26)" ), ("27", "nsip(27)" ), ("28", "slip(28)" ), ("29",
  "ultra(29)" ), ("30", "ds3(30)" ), ("31", "sip(31)" ), ("32", "frameRelay(32)" ), ("33",
  "rs232(33)" ), ("34", "para(34)" ), ("35", "arcnet(35)" ), ("36", "arcnetPlus(36)" ),
  ("37", "atm(37)" ), ("38", "miox25(38)" ), ("39", "sonet(39)" ), ("40", "x25ple(40)" ),
  ("41", "iso88022llc(41)" ), ("42", "localTalk(42)" ), ("43", "smdsDxi(43)" ), ("44",
  "frameRelayService(44)" ), ("45", "v35(45)" ), ("46", "hssi(46)" ), ("47", "hippi(47)" ),
  ("48", "modem(48)" ), ("49", "aal5(49)" ), ("50", "sonetPath(50)" ), ("51", "sonetVT(51)"
  ), ("52", "smdsIcip(52)" ), ("53", "propVirtual(53)" ), ("54", "propMultiplexor(54)" ),
  ("55", "ieee80212(55)" ), ("56", "fibreChannel(56)" ), ("57", "hippiInterface(57)" ), ("58",
  "frameRelayInterconnect(58)" ), ("59", "aflane8023(59)" ), ("60", "aflane8025(60)" ), ("61",
  "cctEmul(61)" ), ("62", "fastEther(62)" ), ("63", "isdn(63)" ), ("64", "v11(64)" ), ("65",
  "v36(65)" ), ("66", "g703at64k(66)" ), ("67", "g703at2mb(67)" ), ("68", "qllc(68)" ), ("69",
  "fastEtherFX(69)" ), ("70", "channel(70)" ), ("71", "ieee80211(71)" ), ("72", "ibm370parChan(72)"
  ), ("73", "escon(73)" ), ("74", "dlsw(74)" ), ("75", "isdns(75)" ), ("76", "isdnu(76)" ),
  ("77", "lapd(77)" ), ("78", "ipSwitch(78)" ), ("79", "rsrb(79)" ), ("80", "atmLogical(80)" ),
  ("81", "ds0(81)" ), ("82", "ds0Bundle(82)" ), ("83", "bsc(83)" ), ("84", "async(84)" ), ("85",
  "cnr(85)" ), ("86", "iso88025Dtr(86)" ), ("87", "eplrs(87)" ), ("88", "arap(88)" ), ("89",
  "propCnls(89)" ), ("90", "hostPad(90)" ), ("91", "termPad(91)" ), ("92", "frameRelayMPI(92)" ),
  ("93", "x213(93)" ), ("94", "adsl(94)" ), ("95", "radsl(95)" ), ("96", "sdsl(96)" ), ("97",
  "vdsl(97)" ), ("98", "iso88025CRFPInt(98)" ), ("99", "myrinet(99)" ), ("100", "voiceEM(100)"
  ), ("101", "voiceFXO(101)" ), ("102", "voiceFXS(102)" ), ("103", "voiceEncap(103)" ), ("104",
  "voiceOverIp(104)" ), ("105", "atmDxi(105)" ), ("106", "atmFuni(106)" ), ("107", "atmIma(107)"
  ), ("108", "pppMultilinkBundle(108)" ), ("109", "ipOverCdlc(109)" ), ("110", "ipOverClaw(110)"
  ), ("111", "stackToStack(111)" ), ("112", "virtualIpAddress(112)" ), ("113", "mpc(113)" ),
  ("114", "ipOverAtm(114)" ), ("115", "iso88025Fiber(115)" ), ("116", "tdlc(116)" ), ("117",
  "gigabitEthernet(117)" ), ("118", "hdlc(118)" ), ("119", "lapf(119)" ), ("120", "v37(120)" ),
  ("121", "x25mlp(121)" ), ("122", "x25huntGroup(122)" ), ("123", "trasnpHdlc(123)" ), ("124",
  "interleave(124)" ), ("125", "fast(125)" ), ("126", "ip(126)" ), ("127", "docsCableMaclayer(127)"
  ), ( "128", "docsCableDownstream(128)" ), ("129", "docsCableUpstream(129)" ), ("130",
  "a12MppSwitch(130)" ), ("131", "tunnel(131)" ), ("132", "coffee(132)" ), ("133", "ces(133)" ),
  ("134", "atmSubInterface(134)" ), ("135", "l2vlan(135)" ), ("136", "l3ipvlan(136)" ), ("137",
  "l3ipxvlan(137)" ), ("138", "digitalPowerline(138)" ), ("139", "mediaMailOverIp(139)" ),
  ("140", "dtm(140)" ), ("141", "dcn(141)" ), ("142", "ipForward(142)" ), ("143", "msdsl(143)" ),
  ("144", "ieee1394(144)" ), ( "145", "if-gsn(145)" ), ("146", "dvbRccMacLayer(146)" ), ("147",
  "dvbRccDownstream(147)" ), ("148", "dvbRccUpstream(148)" ), ("149", "atmVirtual(149)" ),
  ("150", "mplsTunnel(150)" ), ("151", "srp(151)" ), ("152", "voiceOverAtm(152)" ), ("153",
  "voiceOverFrameRelay(153)" ), ("154", "idsl(154)" ), ( "155", "compositeLink(155)" ),
  ("156", "ss7SigLink(156)" ), ("157", "propWirelessP2P(157)" ), ("158", "frForward(158)" ),
  ("159", "rfc1483(159)" ), ("160", "usb(160)" ), ("161", "ieee8023adLag(161)" ), ("162",
  "bgppolicyaccounting(162)" ), ("163", "frf16MfrBundle(163)" ), ("164", "h323Gatekeeper(164)"
  ), ("165", "h323Proxy(165)" ), ("166", "mpls(166)" ), ("167", "mfSigLink(167)" ), ("168",
  "hdsl2(168)" ), ("169", "shdsl(169)" ), ("170", "ds1FDL(170)" ), ("171", "pos(171)" ), ("172",
  "dvbAsiIn(172)" ), ("173", "dvbAsiOut(173)" ), ("174", "plc(174)" ), ("175", "nfas(175)" ), (
  "176", "tr008(176)" ), ("177", "gr303RDT(177)" ), ("178", "gr303IDT(178)" ), ("179", "isup(179)" ),
  ("180", "propDocsWirelessMaclayer(180)" ), ("181", "propDocsWirelessDownstream(181)" ), ("182",
  "propDocsWirelessUpstream(182)" ), ("183", "hiperlan2(183)" ), ("184", "propBWAp2Mp(184)" ),
  ("185", "sonetOverheadChannel(185)" ), ("186", "digitalWrapperOverheadChannel(186)" ), ("187",
  "aal2(187)" ), ("188", "radioMAC(188)" ), ("189", "atmRadio(189)" ), ("190", "imt(190)" ), ("191",
  "mvl(191)" ), ("192", "reachDSL(192)" ), ("193", "frDlciEndPt(193)" ), ("194", "atmVciEndPt(194)"
  ), ("195", "opticalChannel(195)" ), ("196", "opticalTransport(196)" ), ("197", "propAtm(197)" ),
  ("198", "voiceOverCable(198)" ), ("199", "infiniband(199)" ), ("200", "teLink(200)" ), ("201",
  "q2931(201)" ), ("202", "virtualTg(202)" ), ("203", "sipTg(203)" ), ("204", "sipSig(204)" ), (
  "205", "docsCableUpstreamChannel(205)" ), ("206", "econet(206)" ), ("207", "pon155(207)" ), ("208",
  "pon622(208)" ), ("209", "bridge(209)" ), ("210", "linegroup(210)" ), ("211", "voiceEMFGD(211)"
  ), ("212", "voiceFGDEANA(212)" ), ("213", "voiceDID(213)" ), ("214", "mpegTransport(214)" ),
  ("215", "sixToFour(215)" ), ("216", "gtp(216)" ), ("217", "pdnEtherLoop1(217)" ), ("218",
  "pdnEtherLoop2(218)" ), ("219", "opticalChannelGroup(219)" ), ("220", "homepna(220)" ),
  ("221", "gfp(221)" ), ("222", "ciscoISLvlan(222)" ), ("223", "actelisMetaLOOP(223)" ), ("224",
  "fcipLink(224)" ), ("225", "rpr(225)" ), ("226", "qam(226)" ), ("227", "lmp(227)" ), ("228",
  "cblVectaStar(228)" ), ("229", "docsCableMCmtsDownstream(229)" ), ("230", "adsl2(230)" ), ]
register_configvar(group,
    "if_inventory_pad_portnumbers",
    Checkbox(title = _("Pad port numbers with zeroes"),
             label = _("pad port numbers"),
             help = _("If this option is activated then Check_MK will pad port numbers of "
                      "network interfaces with zeroes so that all port descriptions from "
                      "all ports of a host or switch have the same length and thus sort "
                      "currectly in the GUI. In versions prior to 1.1.13i3 there was no "
                      "padding. You can switch back to the old behaviour by disabling this "
                      "option. This will retain the old service descriptions and the old "
                      "performance data.")))

register_configvar(group,
    "if_inventory_uses_description",
    Checkbox(title = _("Use description as service name for network interface checks"),
             label = _("use description"),
             help = _("This option lets Check_MK use the interface description as item instead "
                      "of the port number. If no description is available then the port number is "
                      "used anyway.")))

register_configvar(group,
    "if_inventory_uses_alias",
    Checkbox(title = _("Use alias as service name for network interface checks"),
             label = _("use alias"),
             help = _("This option lets Check_MK use the alias of the port (ifAlias) as item instead "
                      "of the port number. If no alias is available then the port number is used "
                      "anyway.")))

register_configvar(group,
   "if_inventory_portstates",
   ListChoice(title = _("Network interface port states to inventorize"),
              help = _("When doing inventory on switches or other devices with network interfaces "
                       "then only ports found in one of the configured port states will be added to the monitoring."),
              choices = _if_portstate_choices))

register_configvar(group,
   "if_inventory_porttypes",
   ListChoice(title = _("Network interface port types to inventorize"),
              help = _("When doing inventory on switches or other devices with network interfaces "
                       "then only ports of the specified types will be created services for."),
              choices = _if_porttype_choices,
              columns = 3))

register_configvar(group,
    "diskstat_inventory_mode",
    DropdownChoice(
        title = _("Inventory mode for disk IO checks"),
        help = _("When doing inventory the various disk IO checks can either create "
                 "a single check per host, one check per device or a separate check "
                 "for read and written bytes."),
        choices = [
            ('rule'   , _("controlled by ruleset Inventory mode for Disk IO check") ),
            ('summary', _("one summary check per host")),
            ('single' , _("one check per individual disk/LUN") ),
            ('legacy' , _("one check for read, one for write") ),
            ],
        default_value = 'rule',
        ),
    )

register_configvar(group,
    "win_dhcp_pools_inventorize_empty",
    Checkbox(
        title = _("Inventorize empty windows dhcp pools"),
        help = _("You can activate the inventorization of "
                 "dhcp pools, which have no ip addresses in it"),
        ),
    need_restart = True
    )

register_configvar(group,
    "always_cleanup_autochecks",
    Checkbox(title = _("Always cleanup autochecks"),
             help = _("When switched on, Check_MK will always cleanup the autochecks files "
                      "after each inventory, i.e. create one file per host. This is the same "
                      "as adding the option <tt>-u</tt> to each call of <tt>-I</tt> on the "
                      "command line.")))


group = _("Check configuration")


register_configvar(group,
    "if_inventory_monitor_state",
    Checkbox(title = _("Monitor port state of network interfaces"),
             label = _("monitor port state"),
             help = _("When this option is active then during inventory of networking interfaces "
                      "(and switch ports) the current operational state of the port will "
                      "automatically be coded as a check parameter into the check. That way the check "
                      "will get warning or critical when the state changes. This setting can later "
                      "by overridden on a per-host and per-port base by defining special check "
                      "parameters via a rule.")))

register_configvar(group,
    "if_inventory_monitor_speed",
    Checkbox(title = _("Monitor port speed of network interfaces"),
             label = _("monitor port speed"),
             help = _("When this option is active then during inventory of networking interfaces "
                      "(and switch ports) the current speed setting of the port will "
                      "automatically be coded as a check parameter into the check. That way the check "
                      "will get warning or critical when speed later changes (for example from "
                      "100 MBit/s to 10 MBit/s). This setting can later "
                      "by overridden on a per-host and per-port base by defining special check "
                      "parameters via a rule.")))

register_configvar(group,
    "logwatch_service_output",
    DropdownChoice(
        title = _("Service output for logwatch"),
        help = _("You can change the plugin output of logwatch "
                 "to show only the count of messages or also "
                 "to show the last worst message"),
        choices = [
            ( 'default' , _("Show count and last message") ),
            ( 'count', _("Show only count")),
            ],
        default_value = 'default',
        ),
    need_restart = True
    )

register_configvar(group,
    "logwatch_forward_to_ec",
    Checkbox(
        title = _("Forward logwatch messages to event console"),
        label = _("forward to event console"),
        help  = _("Instead of using the regular logwatch check all lines received by logwatch can "
                  "be forwarded to a Check_MK event console daemon to be processed. The target event "
                  "console can be configured for each host in a separate rule."),
    ),
)

register_configvar(group,
    "printer_supply_some_remaining_status",
    DropdownChoice(
        title = _("Printer supply some remaining status"),
        help = _("Set the reported nagios state when the fill state "
                 "is something between empty and small "
                 "remaining capacity"),
        choices = [
            ( 0, _("OK") ),
            ( 1, _("Warning")),
            ( 2, _("Critical")),
            ],
        default_value = 2,
        ),
    )

register_configvar(group,
    "printer_supply_default_levels",
    Tuple(
        title = _("Printer supply default levels"),
        help = _("Set global default levels for warning and critical. "),
        elements = [
           Integer(
                title = _("Warning at"),
                minvalue = 1,
           ),
           Integer(
                 title = _("Critical at"),
                 minvalue = 1,
           ),
         ],
        ))

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

register_rulegroup("grouping", _("Grouping"),
   _("Assignment of host &amp; services to host, service and contacts groups. "))
group = "grouping"

register_rule(group,
    "host_groups",
    GroupSelection(
        "host",
        title = _("Assignment of hosts to host groups")),
    match = "all")

register_rule(group,
    "service_groups",
    GroupSelection(
        "service",
        title = _("Assignment of services to service groups")),
    match = "all",
    itemtype = "service")

register_rule(group,
    "host_contactgroups",
    GroupSelection(
        "contact",
        title = _("Assignment of hosts to contact groups")),
    match = "all")

register_rule(group,
    "service_contactgroups",
    GroupSelection(
        "contact",
        title = _("Assignment of services to contact groups")),
    match = "all",
    itemtype = "service")


register_rulegroup("monconf", _("Monitoring Configuration"),
    _("Intervals for checking, retries, clustering, configuration for inventory and similar"))

group = "monconf/" + _("Service Checks")

register_rule(group,
    "extra_service_conf:max_check_attempts",
    Integer(title = _("Maximum number of check attempts for service"),
            help = _("The maximum number of failed checks until a service problem state will "
                     "be considered as <u>hard</u>. Only hard state trigger notifications. "),
            minvalue = 1),
    itemtype = "service")

register_rule(group,
    "extra_service_conf:check_interval",
    Integer(title = _("Normal check interval for service checks"),
            help = _("Check_MK usually uses an interval of one minute for the active Check_MK "
                     "check and for legacy checks. Here you can specify a larger interval. Please "
                     "note, that this setting only applies to active checks (those with the "
                     "%s reschedule button). If you want to change the check interval of "
                     "the Check_MK service only, specify <tt><b>Check_MK$</b></tt> in the list "
                     "of services.") % '<img class="icon docu" src="images/icon_reload.gif">',
            minvalue = 1,
            label = _("minutes")),
    itemtype = "service")

register_rule(group,
    "extra_service_conf:retry_interval",
    Integer(title = _("Retry check interval for service checks"),
            help = _("This setting is relevant if you have set the maximum number of check "
                     "attempts to a number greater than one. In case a service check is not OK "
                     "and the maximum number of check attempts is not yet reached, it will be "
                     "rescheduled with this interval. The retry interval is usually set to a smaller "
                     "value than the normal interval.<br><br>This setting only applies to "
                     "active checks."),
            minvalue = 1,
            label = _("minutes")),
    itemtype = "service")

register_rule(group,
    "extra_service_conf:check_period",
    TimeperiodSelection(
        title = _("Check period for active services"),
        help = _("If you specify a notification period for a service then active checks "
                 "of that service will only be done in that period. Please note, that the "
                 "checks driven by Check_MK are passive checks and are not affected by this "
                 "rule. You can use the rule for the active Check_MK check, however.")),
    itemtype = "service")

register_rule(group,
    "check_periods",
    TimeperiodSelection(
        title = _("Check period for passive Check_MK services"),
        help = _("If you specify a notification period for a Check_MK service then "
                 "results will be processed only within this period.")),
    itemtype = "service")

register_rule(group,
    "extra_service_conf:process_perf_data",
    DropdownChoice(
        title = _("Enable/disable processing of perfdata for services"),
        help = _("This setting allows you to disable the processing of perfdata for a "
                 "service completely."),
        choices = [ ("1", _("Enable processing of perfdata")),
                    ("0", _("Disable processing of perfdata")) ],
        ),
        itemtype = "service")

register_rule(group,
    "extra_service_conf:passive_checks_enabled",
    DropdownChoice(
        title = _("Enable/disable passive checks for services"),
        help = _("This setting allows you to disable the processing of passiv check results for a "
                 "service."),
        choices = [ ("1", _("Enable processing of passiv check results")),
                    ("0", _("Disable processing of passiv check results")) ],
        ),
        itemtype = "service")

register_rule(group,
    "extra_service_conf:active_checks_enabled",
    DropdownChoice(
        title = _("Enable/disable active checks for services"),
        help = _("This setting allows you to disable or enable "
                 "active checks for a service."),
        choices = [ ("1", _("Enable active checks")),
                    ("0", _("Disable active checks")) ],
        ),
        itemtype = "service")

group = "monconf/" + _("Host Checks")

register_rule(group,
    "extra_host_conf:max_check_attempts",
    Integer(title = _("Maximum number of check attempts for host"),
            help = _("The maximum number of failed host checks until the host will be considered "
                     "in a hard down state"),
            minvalue = 1))

register_rule(group,
    "extra_host_conf:check_interval",
    Integer(
        title = _("Normal check interval for host checks"),
        help = _("The default interval is set to one minute. Here you can specify a larger "
                 "interval. The host is contacted in this interval on a regular base. The host "
                 "check is also being executed when a problematic service state is detected to check "
                 "wether or not the service problem is resulting from a host problem."),
        minvalue = 1,
        label = _("minutes")
    )
)

register_rule(group,
    "extra_host_conf:retry_interval",
    Integer(title = _("Retry check interval for host checks"),
        help = _("This setting is relevant if you have set the maximum number of check "
                 "attempts to a number greater than one. In case a host check is not UP "
                 "and the maximum number of check attempts is not yet reached, it will be "
                 "rescheduled with this interval. The retry interval is usually set to a smaller "
                 "value than the normal interval."),
        minvalue = 1,
        label = _("minutes")
    )
)

register_rule(group,
    "extra_host_conf:check_period",
    TimeperiodSelection(
        title = _("Check period for hosts"),
        help = _("If you specify a check period for a host then active checks of that "
                 "host will only take place within that period. In the rest of the time "
                 "the state of the host will stay at its last status.")),
    )

register_rule(group,
    "extra_host_conf:check_command",
    TextAscii(
        label = _("Command:"),
        title = _("Check Command for Hosts Check"),
        help = _("This parameter changes the default check_command for "
                 "a host check"),
        ),
    )

group = "monconf/" + _("Notifications")
register_rule(group,
    "extra_host_conf:notifications_enabled",
    DropdownChoice(
        title = _("Enable/disable notifications for hosts"),
        help = _("This setting allows you to disable notifications about problems of a "
                 "host completely. Per default all notifications are enabled. Sometimes "
                 "it is more convenient to just disable notifications then to remove a "
                 "host completely from the monitoring. Note: this setting has no effect "
                 "on the notifications of service problems of a host."),
        choices = [ ("1", _("Enable host notifications")),
                    ("0", _("Disable host notifications")) ],
        ))

register_rule(group,
    "extra_service_conf:notifications_enabled",
    DropdownChoice(
        title = _("Enable/disable notifications for services"),
        help = _("This setting allows you to disable notifications about problems of a "
                 "service completely. Per default all notifications are enabled."),
        choices = [ ("1", _("Enable service notifications")),
                    ("0", _("Disable service notifications")) ],
        ),
        itemtype = "service")

register_rule(group,
    "extra_host_conf:notification_period",
    TimeperiodSelection(
        title = _("Notification period for hosts"),
        help = _("If you specify a notification period for a host then notifications "
                 "about problems of that host (not of its services!) will only be sent "
                 "if those problems occur within the notification period. Also you can "
                 "filter out problems in the problems views for objects not being in "
                 "their notification period (you can think of the notification period "
                 "as the 'service time'.")),
    )

register_rule(group,
    "extra_service_conf:notification_period",
    TimeperiodSelection(
        title = _("Notification period for services"),
        help = _("If you specify a notification period for a service then notifications "
                 "about that service will only be sent "
                 "if those problems occur within the notification period. Also you can "
                 "filter out problems in the problems views for objects not being in "
                 "their notification period (you can think of the notification period "
                 "as the 'service time'.")),
    itemtype = "service")

register_rule(group,
    "extra_host_conf:first_notification_delay",
    Integer(
        minvalue = 0,
        default_value = 60,
        label = _("Delay:"),
        unit = _("minutes"),
        title = _("Delay host notifications"),
        help = _("This setting delays notifications about host problems by the "
                 "specified amount of time. If the host is up again within that "
                 "time, no notification will be sent out."),
        )
    )

register_rule(group,
    "extra_service_conf:first_notification_delay",
    Integer(
        minvalue = 0,
        default_value = 60,
        label = _("Delay:"),
        unit = _("minutes"),
        title = _("Delay service notifications"),
        help = _("This setting delays notifications about service problems by the "
                 "specified amount of time. If the service is OK again within that "
                 "time, no notification will be sent out."),
        ),
    itemtype = "service")

register_rule(group,
    "extra_host_conf:notification_interval",
    Optional(
        Integer(
            minvalue = 1,
            default_value = 120,
            label = _("Interval:"),
            unit = _("minutes")),
        title = _("Periodic notifications during host problems"),
        help = _("If you enable periodic notifications, then during a problem state "
               "of the host notifications will be sent out in regular intervals "
               "until the problem is acknowledged."),
        label = _("Enable periodic notifications"),
        none_label = _("disabled"),
        none_value = 0,
        )
    )



register_rule(group,
    "extra_service_conf:notification_interval",
    Optional(
        Integer(
            minvalue = 1,
            default_value = 120,
            label = _("Interval:"),
            unit = _("minutes")),
        title = _("Periodic notifications during service problems"),
        help = _("If you enable periodic notifications, then during a problem state "
               "of the service notifications will be sent out in regular intervals "
               "until the problem is acknowledged."),
        label = _("Enable periodic notifications"),
        none_label = _("disabled"),
        none_value = 0,
        ),

    itemtype = "service")

register_rule(group,
    "extra_host_conf:flap_detection_enabled",
    DropdownChoice(
        title = _("Enable/disable flapping detection for hosts"),
        help = _("This setting allows you to disable the flapping detection for a "
                 "host completely."),
        choices = [ ("1", _("Enable flap detection")),
                    ("0", _("Disable flap detection")) ],
        ))

register_rule(group,
    "extra_service_conf:flap_detection_enabled",
    DropdownChoice(
        title = _("Enable/disable flapping detection for services"),
        help = _("This setting allows you to disable the flapping detection for a "
                 "service completely."),
        choices = [ ("1", _("Enable flap detection")),
                    ("0", _("Disable flap detection")) ],
        ),
        itemtype = "service")


register_rule(group,
    "extra_service_conf:notes_url",
    TextAscii(
        label = _("Url:"),
        title = _("Notes url for Services"),
        help = _("With this setting you can set links to documentations "
                 "for each service"),
        ),
    itemtype = "service")

register_rule(group,
    "extra_host_conf:notes_url",
    TextAscii(
        label = _("Url:"),
        title = _("Notes url for Hosts"),
        help = _("With this setting you can set links to documentations "
                 "for Hosts"),
        ),
    )

group = "monconf/" + _("Inventory and Check_MK settings")

register_rule(group,
    "only_hosts",
    title = _("Hosts to be monitored"),
    help = _("By adding rules to this ruleset you can define a subset of your hosts "
             "to be actually monitored. As long as the rule set is empty "
             "all configured hosts will be monitored. As soon as you add at least one "
             "rule, only hosts with a matching rule will be monitored."),
    optional = True, # only_hosts is None per default
    )

register_rule(group,
    "ignored_services",
    title = _("Ignored services"),
    help = _("Services that are declared as <u>ignored</u> by this rule set will not be added "
             "to a host during inventory (automatic service detection). Services that already "
             "exist will continued to be monitored but be marked as obsolete in the service "
             "list of a host."),
    itemtype = "service")

register_rule(group,
    "ignored_checks",
    CheckTypeSelection(
        title = _("Ignored checks"),
        help = _("This ruleset is similar to 'Ignored services', but selects checks to be ignored "
                 "by their <b>type</b>. This allows you to disable certain technical implementations "
                 "such as filesystem checks via SNMP on hosts that also have the Check_MK agent "
                 "installed."),
    ))

register_rule(group,
    "clustered_services",
    title = _("Clustered services"),
    help = _("When you define HA clusters in WATO then you also have to specify "
             "which services of a node should be assigned to the cluster and "
             "which services to the physical node. This is done by this ruleset. "
             "Please note that the rule will be applied to the <i>nodes</i>, not "
             "to the cluster.<br><br>Please make sure that you re-inventorize the "
             "cluster and the physical nodes after changing this ruleset."),
    itemtype = "service")
group = "monconf/" + _("Various")

class MonitoringIcon(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)

    def available_icons(self):
        if defaults.omd_root:
            dirs = [ defaults.omd_root + "/local/share/check_mk/web/htdocs/images/icons",
                     defaults.omd_root + "/share/check_mk/web/htdocs/images/icons" ]
        else:
            dirs = [ defaults.web_dir + "/htdocs/images/icons" ]

        icons = []
        for dir in dirs:
            if os.path.exists(dir):
                icons += [ i for i in os.listdir(dir)
                           if '.' in i and os.path.isfile(dir + "/" + i) ]
        icons.sort()
        return icons

    def render_input(self, varprefix, value):
        if value is None:
            value = ""
        num_columns = 12
        html.write("<table>")
        for nr, filename in enumerate([""] + self.available_icons()):
            if nr % num_columns == 0:
                html.write("<tr>")
            html.write("<td>")
            html.radiobutton(varprefix, str(nr), value == filename,
                            self.value_to_text(filename))
            html.write("&nbsp; </td>")
            if nr % num_columns == num_columns - 1:
                html.write("</tr>")
        if nr != num_columns - 1:
            html.write("</tr>")
        html.write("</table>")

    def value_to_text(self, value):
        if value:
            return '<img align=middle title="%s" class=icon src="images/icons/%s">' % \
                (value, value)
        else:
            return _("none")

    def from_html_vars(self, varprefix):
        nr = int(html.var(varprefix))
        if nr == 0:
            return None
        else:
            return self.available_icons()[nr-1]

    def validate_datatype(self, value, varprefix):
        if value is not None and type(value) != str:
            raise MKUserError(varprefix, _("The type is %s, but should be str") %
                type(value))

    def validate_value(self, value, varprefix):
        if value and value not in self.available_icons():
            raise MKUserError(varprefix, _("The selected icon image does not exist."))



register_rule(group,
    "extra_host_conf:icon_image",
    MonitoringIcon(
        title = _("Icon image for hosts in status GUI"),
        help = _("You can assign icons to hosts for the status GUI. "
                 "Put your images into <tt>%s</tt>. ") %
                ( defaults.omd_root
                   and defaults.omd_root + "/local/share/check_mk/web/htdocs/images/icons"
                   or defaults.web_dir + "/htdocs/images/icons" ),
        ))

register_rule(group,
    "extra_service_conf:icon_image",
    MonitoringIcon(
        title = _("Icon image for services in status GUI"),
        help = _("You can assign icons to services for the status GUI. "
                 "Put your images into <tt>%s</tt>. ") %
                ( defaults.omd_root
                   and defaults.omd_root + "/local/share/check_mk/web/htdocs/images/icons"
                   or defaults.web_dir + "/htdocs/images/icons" ),
        ),
    itemtype = "service")




register_rulegroup("agent", _("Access to Agents"),
   _("Settings concerning the connection to the Check_MK and SNMP agents"))

group = "agent/" + _("General Settings")
register_rule(group,
    "dyndns_hosts",
    title = _("Hosts with dynamic DNS lookup during monitoring"),
    help = _("This ruleset selects host for dynamic DNS lookup during monitoring. Normally "
             "the IP addresses of hosts are statically configured or looked up when you "
             "activate the changes. In some rare cases DNS lookups must be done each time "
             "a host is connected to, e.g. when the IP address of the host is dynamic "
             "and can change."))
group = "agent/" + _("SNMP")

_snmpv3_basic_elements = [
     DropdownChoice(
         choices = [
             ( "authPriv",     _("authPriv")),
             ( "authNoPriv",   _("authNoPriv")),
             ( "noAuthNoPriv", _("noAuthNoPriv")),
             ],
         title = _("Security level")),
      DropdownChoice(
          choices = [
             ( "md5", _("MD5") ),
             ( "sha", _("SHA1") ),
          ],
          title = _("Authentication protocol")),
     TextAscii(title = _("Security name")),
     TextAscii(title = _("Authentication password"))]

register_rule(group,
    "snmp_communities",
    Alternative(
       elements = [
           TextAscii(
               title = _("SNMP community (SNMP Versions 1 and 2c)"),
               allow_empty = False),
           Tuple(
               title = _("Credentials for SNMPv3"),
               elements = _snmpv3_basic_elements),
           Tuple(
               title = _("Credentials for SNMPv3 including privacy options"),
               elements = _snmpv3_basic_elements + [
                  DropdownChoice(
                      choices = [
                         ( "DES", _("DES") ),
                         ( "AES", _("AES") ),
                      ],
                      title = _("Privacy protocol")),
                 TextAscii(title = _("Privacy pass phrase")),
                   ])],
        title = _("SNMP communities of monitored hosts")))

register_rule(group,
    "snmp_character_encodings",
    DropdownChoice(
        title = _("Output text coding settings for SNMP devices"),
        help = _("Some devices send texts in non-ASCII characters. Check_MK"
                 " always assumes UTF-8 encoding. You can declare other "
                 " other encodings here"),
        choices = [
           ("utf-8", _("UTF-8 (default)") ),
           ("latin1" ,_("latin1")),
           ]
        )),

register_rule(group,
    "bulkwalk_hosts",
    title = _("Hosts using bulk walk (and SNMP v2c)"),
    help = _("Most SNMP hosts support SNMP version 2c. However, Check_MK defaults to version 1, "
             "in order to support as many devices as possible. Please use this ruleset in order "
             "to configure SNMP v2c for as many hosts as possible. That version has two advantages: "
             "it supports 64 bit counters, which avoids problems with wrapping counters at too "
             "much traffic. And it supports bulk walk, which saves much CPU and network resources. "
             "Please be aware, however, that there are some broken devices out there, that support "
             "bulk walk but behave very bad when it is used. When you want to enable v2c while not using "
             "bulk walk, please use the rule set snmpv2c_hosts instead."))

register_rule(group,
    "snmpv2c_hosts",
    title = _("Hosts using SNMP v2c (and no bulk walk)"),
    help = _("There exist a few devices out there that behave very badly when using SNMP bulk walk. "
             "If you want to use SNMP v2c on those devices, nevertheless, then use this rule set. "
             "One reason is enabling 64 bit counters."))

register_rule(group,
    "snmp_timing",
    Dictionary(
        title = _("Timing settings for SNMP access"),
        help = _("This rule decides about the number of retries and timeout values "
                 "for the SNMP access to devices."),
        elements = [
            ( "timeout",
              Integer(
                  title = _("Timeout between retries"),
                  help = _("The default is 1 sec."),
                  default_value = 1,
                  minvalue = 1,
                  maxvalue = 60,
                  unit = _("sec"),
              ),
            ),
            ( "retries",
              Integer(
                  title = _("Number of retries"),
                  help = _("The default is 5."),
                  default_value = 5,
                  minvalue = 1,
                  maxvalue = 50,
              )
            ),
       ]),
    match = "dict")



register_rule(group,
    "usewalk_hosts",
    title = _("Simulating SNMP by using a stored SNMP walk"),
    help = _("This ruleset helps in test and development. You can create stored SNMP "
             "walks on the command line with cmk --snmpwalk HOSTNAME. A host that "
             "is configured with this ruleset will then use the information from that "
             "file instead of using real SNMP. "))

group = "agent/" + _("Check_MK Agent")

register_rule(group,
    "agent_ports",
    Integer(
            help = _("This variable allows to specify the TCP port to "
                     "be used to connect to the agent on a per-host-basis. "),
            minvalue = 1,
            maxvalue = 65535,
            default_value = 6556),
    title = _("TCP port for connection to Check_MK agent")
)



register_rule(group,
    "datasource_programs",
    TextAscii(
        title = _("Individual program call instead of agent access"),
        help = _("For agent based checks Check_MK allows you to specify an alternative "
                 "program that should be called by Check_MK instead of connecting the agent "
                 "via TCP. That program must output the agent's data on standard output in "
                 "the same format the agent would do. This is for example useful for monitoring "
                 "via SSH. The command line may contain the placeholders <tt>&lt;IP&gt;</tt> and "
                 "<tt>&lt;HOST&gt;</tt>."),
        label = _("Command line to execute"),
        size = 80,
        attrencode = True))

