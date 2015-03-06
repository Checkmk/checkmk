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


#   .--Global Settings-----------------------------------------------------.
#   |  ____ _       _           _   ____       _   _   _                   |
#   | / ___| | ___ | |__   __ _| | / ___|  ___| |_| |_(_)_ __   __ _ ___   |
#   || |  _| |/ _ \| '_ \ / _` | | \___ \ / _ \ __| __| | '_ \ / _` / __|  |
#   || |_| | | (_) | |_) | (_| | |  ___) |  __/ |_| |_| | | | | (_| \__ \  |
#   | \____|_|\___/|_.__/ \__,_|_| |____/ \___|\__|\__|_|_| |_|\__, |___/  |
#   |                                                          |___/       |
#   +----------------------------------------------------------------------+
#   | Global configuration settings for main.mk and multisite.mk           |
#   '----------------------------------------------------------------------'

deprecated = _("Deprecated")

group = _("Status GUI (Multisite)")

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
    Checkbox(title = _("Enable sounds in views"),
             label = _("enable sounds"),
             help = _("If sounds are enabled then the user will be alarmed by problems shown "
                      "in a Multisite status view if that view has been configured for sounds. "
                      "From the views shipped in with Multisite all problem views have sounds "
                      "enabled."),
             default_value = False),
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
    "table_row_limit",
    Integer(title = _("Limit the number of rows shown in tables"),
            help = _("Several pages which use tables to show data in rows, like the "
                     "\"Users\" configuration page, can be configured to show "
                     "only a limited number of rows when accessing the pages."),
            minvalue = 1,
            default_value = 100,
            unit = _('rows')),
    domain = "multisite")

register_configvar(group,
    "start_url",
    TextAscii(title = _("Start-URL to display in main frame"),
              help = _("When you point your browser to the Multisite GUI, usually the dashboard "
                       "is shown in the main (right) frame. You can replace this with any other "
                       "URL you like here."),
              size = 80,
              default_value = "dashboard.py",
              attrencode = True),
    domain = "multisite")

register_configvar(group,
    "page_heading",
    TextUnicode(title = _("HTML-Title of HTML Multisite GUI"),
              help = _("This title will be displayed in your browser's title bar or tab. If you are "
                       "using OMD then you can embed a <tt>%s</tt>. This will be replaced by the name "
                       "of the OMD site."),
              size = 80,
              default_value = u"Check_MK %s",
              attrencode = True),
    domain = "multisite")

register_configvar(group,
    "pagetitle_date_format",
    DropdownChoice(
        title = _("Date format for page titles"),
        help = _("When enabled, the headline of each page also displays "\
                 "the date in addition the time."),
        choices = [
            (None,         _("Do not display a date")),
            ('yyyy-mm-dd', _("YYYY-MM-DD")),
            ('dd.mm.yyyy', _("DD.MM.YYYY")),
        ],
        default_value = None
    ),
    domain = "multisite")

register_configvar(group,
    "escape_plugin_output",
    Checkbox(title = _("Escape HTML codes in plugin output"),
             label = _("Prevent loading HTML from plugin output or log messages"),
             help = _("By default, for security reasons, Multisite does not interpret any HTML "
                      "code received from external sources, like plugin output or log messages. "
                      "If you are really sure what you are doing and need to have HTML codes, like "
                      "links rendered, disable this option. Be aware, you might open the way "
                      "for several injection attacks."),
            default_value = True),
    domain = "multisite")


register_configvar(group,
    "multisite_draw_ruleicon",
    Checkbox(title = _("Show icon linking to WATO parameter editor for services"),
             label = _("Show WATO icon"),
             help = _("When enabled a rule editor icon is displayed for each "
                      "service in the multisite views. It is only displayed if the user "
                      "does have the permission to edit rules."),
            default_value = True),
    domain = "multisite")


def wato_host_tag_group_choices():
    # We add to the choices:
    # 1. All host tag groups with their id
    # 2. All *topics* that:
    #  - consist only of checkbox tags
    #  - contain at least two entries
    choices = []
    by_topic = {}
    for entry in config.wato_host_tags:
        tgid = entry[0]
        topic, tit = parse_hosttag_title(entry[1])
        choices.append((tgid, tit))
        by_topic.setdefault(topic, []).append(entry)

    # Now search for checkbox-only-topics
    for topic, entries in by_topic.items():
        for entry in entries:
            tgid, title, tags = entry
            if len(tags) != 1:
                break
        else:
            if len(entries) > 1:
                choices.append(("topic:" + topic, _("Topic") + ": " + topic))

    return choices


register_configvar(group,
    "virtual_host_trees",
    ListOf(
        Tuple(
            elements = [
                TextUnicode(
                    title = _("Title of the tree"),
                    allow_empty = False,
                ),
                DualListChoice(
                    allow_empty = False,
                    custom_order = True,
                    choices = wato_host_tag_group_choices,
                )
            ]
        ),
        add_label = _("Create new virtual host tree configuration"),
        title = _("Virtual Host Trees"),
        help = _("Here you can define tree configurations for the snapin <i>Virtual Host-Trees</i>. "
                 "These trees organize your hosts based on their values in certain host tag groups. "
                 "Each host tag group you select will create one level in the tree."),
    ),
    domain = "multisite",
)



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
    "sidebar_notify_interval",
    Optional(
        Float(
            minvalue = 10.0,
            default_value = 60.0,
            unit = "sec",
            display_format = "%.1f"
        ),
        title = _("Interval of sidebar popup notification updates"),
        help = _("The sidebar can be configured to regularly check for pending popup notififcations. "
                 "This is disabled by default."),
        none_label = _('(disabled)'),
    ),
    domain = "multisite")

register_configvar(group,
    "adhoc_downtime",
    Optional(
        Dictionary(
            optional_keys = False,
            elements = [
                ("duration", Integer(
                    title = _("Duration"),
                    help  = _("The duration in minutes of the adhoc downtime."),
                    minvalue = 1,
                    unit  = _("minutes"),
                    default_value = 60,
                    )),
                ("comment", TextUnicode(
                    title = _("Adhoc comment"),
                    help    = _("The comment which is automatically sent with an adhoc downtime"),
                    size = 80,
                    allow_empty = False,
                    attrencode = True,
                    )),
            ],
        ),
        title = _("Adhoc downtime"),
        label = _("Enable adhoc downtime"),
        help  = _("This setting allows to set an adhoc downtime comment and its duration. "
                  "When enabled a new button <i>Adhoc downtime for __ minutes</i> will "
                  "be available in the command form."),
    ),
    domain = "multisite",
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

register_configvar(group,
    "auth_by_http_header",
    Optional(
        TextAscii(
            label   = _("HTTP Header Variable"),
            help    = _("Configure the name of the environment variable to read "
                        "from the incoming HTTP requests"),
            default_value = 'REMOTE_USER',
            attrencode = True,
        ),
        title = _("Authenticate users by incoming HTTP requests"),
        label = _("Activate HTTP header authentication (Warning: Only activate "
                  "in trusted environments, see help for details)"),
        help  = _("If this option is enabled, multisite reads the configured HTTP header "
                  "variable from the incoming HTTP request and simply takes the string "
                  "in this variable as name of the authenticated user. "
                  "Be warned: Only allow access from trusted ip addresses "
                  "(Apache <tt>Allow from</tt>), like proxy "
                  "servers, to this webpage. A user with access to this page could simply fake "
                  "the authentication information. This option can be useful to "
                  " realize authentication in reverse proxy environments.")
    ),
    domain = "multisite")

register_configvar(group,
    "staleness_threshold",
    Float(
        title = _('Staleness value to mark hosts / services stale'),
        help  = _('The staleness value of a host / service is calculated by measuring the '
                  'configured check intervals a check result is old. A value of 1.5 means the '
                  'current check result has been gathered one and a half check intervals of an object. '
                  'This would mean 90 seconds in case of a check which is checked each 60 seconds.'),
        minvalue = 1,
        default_value = 1.5,
    ),
    domain = "multisite",
)

register_configvar(group,
    "user_localizations",
    Transform(
        ListOf(
            Tuple(
                elements = [
                   TextUnicode(title = _("Original Text"), size = 40),
                    Dictionary(
                        title = _("Translations"),
                        elements = [
                            ( l or "en", TextUnicode(title = a, size = 32) )
                              for (l,a) in get_languages()
                        ],
                        columns = 2,
                    ),
                ],
            ),
            title = _("Custom localizations"),
            movable = False,
            totext = _("%d translations"),
            default_value = sorted(default_user_localizations.items()),
        ),
        forth = lambda d: sorted(d.items()),
        back = lambda l: dict(l),
    ),
    domain = "multisite",
)

# Helper that retrieves the list of hostgroups via Livestatus
# use alias by default but fallback to name if no alias defined
def list_hostgroups():
    groups = dict(html.live.query("GET hostgroups\nCache: reload\nColumns: name alias\n"))
    return [ (name, groups[name] or name) for name in groups.keys() ]

register_configvar(group,
    "topology_default_filter_group",
    Optional(DropdownChoice(
            choices = list_hostgroups,
            sorted = True,
        ),
        title = _("Network Topology: Default Filter Group"),
        help = _("By default the network topology view shows you the parent / child relations "
                 "of all hosts within your local site. The list can be filtered based on hostgroup "
                 "memberships by the users. You can define a default group to use for filtering "
                 "which is used when a user opens the network topology view."),
        none_label = _("Show all hosts when opening the network topology view"),
        default_value = None,
    ),
    domain = "multisite"
)

#.
#   .--WATO----------------------------------------------------------------.
#   |                     __        ___  _____ ___                         |
#   |                     \ \      / / \|_   _/ _ \                        |
#   |                      \ \ /\ / / _ \ | || | | |                       |
#   |                       \ V  V / ___ \| || |_| |                       |
#   |                        \_/\_/_/   \_\_| \___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Global Configuration for WATO                                        |
#   '----------------------------------------------------------------------'

group = _("Configuration GUI (WATO)")

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
    "wato_legacy_eval",
    Checkbox(
        title = _("Use unsafe legacy encoding for distributed WATO"),
        help = _("The current implementation of WATO uses a Python module called <tt>ast</tt> for the "
                 "communication between sites. Previous versions of Check_MK used an insecure encoding "
                 "named <tt>pickle</tt>. Even in the current version WATO falls back to <tt>pickle</tt> "
                 "if your Python version is not recent enough. This is at least the case for RedHat/CentOS 5.X "
                 "and Debian 5.0. In a mixed environment you can force using the legacy <tt>pickle</tt> format "
                 "in order to create compatibility."),
    ),
    domain = "multisite"
)


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
    "wato_upload_insecure_snapshots",
    Checkbox(title = _("Allow upload of insecure WATO snapshots"),
             label = _("upload insecure snapshots"),
             help = _("When enabled, insecure snapshots are allowed. Please keep in mind that the upload "
                      "of unverified snapshots represents a security risk, since the content of a snapshot is executed "
                      "during runtime. Any manipulations in the content - either willingly or unwillingly (XSS attack) "
                      "- pose a serious security risk."),
             default_value = False),
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
             help = _("When enabled, internal configuration variable names of Check_MK are hidden "
                      "from the user (for example in the rule editor)"),
             default_value = True),
    domain = "multisite")


register_configvar(group,
    "wato_hide_help_in_lists",
    Checkbox(title = _("Hide help text of rules in list views"),
             label = _("hide help text"),
             help = _("When disabled, WATO shows the help texts of rules also in the list views."),
             default_value = True),
    domain = "multisite")

register_configvar(group,
    "wato_use_git",
    Checkbox(title = _("Use GIT version control for WATO"),
             label = _("enable GIT version control"),
             help = _("When enabled, all changes of configuration files are tracked with the "
                      "version control system GIT. You need to make sure that git is installed "
                      "on your Nagios server. The version history currently cannot be viewed "
                      "via the web GUI. Please use git command line tools within your Check_MK "
                      "configuration directory."),
             default_value = False),
    domain = "multisite")

#.
#   .--User Management-----------------------------------------------------.
#   |          _   _                 __  __                 _              |
#   |         | | | |___  ___ _ __  |  \/  | __ _ _ __ ___ | |_            |
#   |         | | | / __|/ _ \ '__| | |\/| |/ _` | '_ ` _ \| __|           |
#   |         | |_| \__ \  __/ |    | |  | | (_| | | | | | | |_            |
#   |          \___/|___/\___|_|    |_|  |_|\__, |_| |_| |_|\__|           |
#   |                                       |___/                          |
#   +----------------------------------------------------------------------+
#   | Global settings for users and LDAP connector.                        |
#   '----------------------------------------------------------------------'

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
    "userdb_automatic_sync",
    ListChoice(
        title = _('Automatic User Synchronization'),
        help  = _('By default the users are synchronized automatically in several situations. '
                  'The sync is started when opening the "Users" page in configuration and '
                  'during each page rendering. Each connector can then specify if it wants to perform '
                  'any actions. For example the LDAP connector will start the sync once the cached user '
                  'information are too old.'),
        default_value = [ 'wato_users', 'page', 'wato_pre_activate_changes', 'wato_snapshot_pushed' ],
        choices       = [
            ('page',                      _('During regular page processing')),
            ('wato_users',                _('When opening the users\' configuration page')),
            ('wato_pre_activate_changes', _('Before activating the changed configuration')),
            ('wato_snapshot_pushed',      _('On a remote site, when it receives a new configuration')),
        ],
        allow_empty   = True,
    ),
    domain = "multisite",
)

register_configvar(group,
    "ldap_connection",
    Dictionary(
        title = _("LDAP Connection Settings"),
        help  = _("This section configures all LDAP specific connection options. These options "
                  "are used by the LDAP user connector."),
        elements = [
            ("server", TextAscii(
                title = _("LDAP Server"),
                help = _("Set the host address of the LDAP server. Might be an IP address or "
                         "resolvable hostname."),
                allow_empty = False,
                attrencode = True,
            )),
            ('failover_servers', ListOfStrings(
                title = _('Failover Servers'),
                help = _('When the connection to the first server fails with connect specific errors '
                         'like timeouts or some other network related problems, the connect mechanism '
                         'will try to use this server instead of the server configured above. If you '
                         'use persistent connections (default), the connection is being used until the '
                         'LDAP is not reachable or the local webserver is restarted.'),
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
                help   = _("Connect to the LDAP server with a SSL encrypted connection. You might need "
                           "to configure the OpenLDAP installation on your monitoring server to accept "
                           "the certificates of the LDAP server. This is normally done via system wide "
                           "configuration of the CA certificate which signed the certificate of the LDAP "
                           "server. Please refer to the <a target=\"_blank\" "
                           "href=\"http://mathias-kettner.de/checkmk_multisite_ldap_integration.html\">"
                           "documentation</a> for details."),
                value  = True,
                totext = _("Encrypt the network connection using SSL."),
            )),
            ("no_persistent", FixedValue(
                title  = _("No persistent connection"),
                help   = _("The connection to the LDAP server is not persisted."),
                value  = True,
                totext = _("Don't use persistent LDAP connections."),
            )),
            ("connect_timeout", Float(
                title = _("Connect Timeout (sec)"),
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
                    ("ad",                 _("Active Directory")),
                    ("openldap",           _("OpenLDAP")),
                    ("389directoryserver", _("389 Directory Server")),
                ],
            )),
            ("bind", Tuple(
                title = _("Bind Credentials"),
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
                                  "the LDAP directory, e. g. <tt>CN=ldap,OU=users,DC=example,DC=com</tt>"),
                        size = 63,
                    ),
                    Password(
                        title = _("Bind Password"),
                        help  = _("Specify the password to be used to bind to "
                                  "the LDAP directory."),
                    ),
                ],
            )),
            ("page_size", Integer(
                title = _("Page Size"),
                help = _("LDAP searches can be performed in paginated mode, for example to improve "
                         "the performance. This enables pagination and configures the size of the pages."),
                minvalue = 1,
                default_value = 1000,
            )),
            ("response_timeout", Integer(
                title = _("Response Timeout (sec)"),
                help = _("Timeout for LDAP query responses."),
                minvalue = 0,
                default_value = 5,
            )),
        ],
        optional_keys = ['no_persistent', 'use_ssl', 'bind', 'page_size', 'response_timeout', 'failover_servers'],
        default_keys = ['page_size']
    ),
    domain = "multisite",
    in_global_settings = False,
)

register_configvar(group,
    "ldap_userspec",
    Dictionary(
        title = _("LDAP User Settings"),
        help  = _("This section configures all user related LDAP options. These options "
                  "are used by the LDAP user connector to find the needed users in the LDAP directory."),
        elements = [
            ("dn", LDAPDistinguishedName(
                title = _("User Base DN"),
                help  = _("Give a base distinguished name here, e. g. <tt>OU=users,DC=example,DC=com</tt><br> "
                          "All user accounts to synchronize must be located below this one."),
                size = 80,
            )),
            ("scope", DropdownChoice(
                title = _("Search Scope"),
                help  = _("Scope to be used in LDAP searches. In most cases <i>Search whole subtree below "
                          "the base DN</i> is the best choice. "
                          "It searches for matching objects recursively."),
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
                         "base DN.<br><br>Some common examples:<br><br> "
                         "All user objects in LDAP:<br> "
                         "<tt>(&(objectclass=user)(objectcategory=person))</tt><br> "
                         "Members of a group:<br> "
                         "<tt>(&(objectclass=user)(objectcategory=person)(memberof=CN=cmk-users,OU=groups,DC=example,DC=com))</tt><br>"),
                size = 80,
                default_value = lambda: userdb.ldap_filter('users', False),
                attrencode = True,
            )),
            ("filter_group", LDAPDistinguishedName(
                title = _("Filter Group (Only use in special situations)"),
                help = _("Using this option you can define the DN of a group object which is used to filter the users. "
                         "Only members of this group will then be synchronized. This is a filter which can be "
                         "used to extend capabilities of the regular \"Search Filter\". Using the search filter "
                         "you can only define filters which directly apply to the user objects. To filter by "
                         "group memberships, you can use the <tt>memberOf</tt> attribute of the user objects in some "
                         "directories. But some directories do not have such attributes because the memberships "
                         "are stored in the group objects as e.g. <tt>member</tt> attributes. You should use the "
                         "regular search filter whenever possible and only use this filter when it is really "
                         "neccessary. Finally you can say, you should not use this option when using Active Directory. "
                         "This option is neccessary in OpenLDAP directories when you like to filter by group membership.<br><br>"
                         "If using, give a plain distinguished name of a group here, e. g. "
                         "<tt>CN=cmk-users,OU=groups,DC=example,DC=com</tt>"),
                size = 80,
            )),
            ("user_id", TextAscii(
                title = _("User-ID Attribute"),
                help  = _("The attribute used to identify the individual users. It must have "
                          "unique values to make an user identifyable by the value of this "
                          "attribute."),
                default_value = lambda: userdb.ldap_attr('user_id'),
                attrencode = True,
            )),
            ("lower_user_ids", FixedValue(
                title  = _("Lower Case User-IDs"),
                help   = _("Convert imported User-IDs to lower case during synchronisation."),
                value  = True,
                totext = _("Enforce lower case User-IDs."),
            )),
            ("user_id_umlauts", DropdownChoice(
                title = _("Umlauts in User-IDs"),
                help  = _("Multisite does not support umlauts in User-IDs at the moment. To deal "
                          "with LDAP users having umlauts in their User-IDs you have the following "
                          "choices."),
                choices = [
                    ("replace",  _("Replace umlauts like \"&uuml;\" with \"ue\"")),
                    ("skip",     _("Skip users with umlauts in their User-IDs")),
                ],
                default_value = "replace",
            )),
        ],
        optional_keys = ['filter', 'filter_group', 'user_id', 'lower_user_ids', ],
    ),
    domain = "multisite",
    in_global_settings = False,
)

register_configvar(group,
    "ldap_groupspec",
    Dictionary(
        title = _("LDAP Group Settings"),
        help  = _("This section configures all group related LDAP options. These options "
                  "are only needed when using group related attribute synchonisation plugins."),
        elements = [
            ("dn", LDAPDistinguishedName(
                title = _("Group Base DN"),
                help  = _("Give a base distinguished name here, e. g. <tt>OU=groups,DC=example,DC=com</tt><br> "
                          "All groups used must be located below this one."),
                size = 80,
            )),
            ("scope", DropdownChoice(
                title = _("Search Scope"),
                help  = _("Scope to be used in group related LDAP searches. In most cases "
                          "<i>Search whole subtree below the base DN</i> "
                          "is the best choice. It searches for matching objects in the given base "
                          "recursively."),
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
                         "subset of the groups below the given base DN.<br><br>"
                         "e.g. <tt>(objectclass=group)</tt>"),
                size = 80,
                default_value = lambda: userdb.ldap_filter('groups', False),
                attrencode = True,
            )),
            ("member", TextAscii(
                title = _("Member Attribute"),
                help  = _("The attribute used to identify users group memberships."),
                default_value = lambda: userdb.ldap_attr('member'),
                attrencode = True,
            )),
        ],
        optional_keys = ['filter', 'member'],
    ),
    domain = "multisite",
    in_global_settings = False,
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
        default_keys = ['email', 'alias', 'auth_expire' ],
    ),
    domain = "multisite",
    in_global_settings = False,
)

register_configvar(group,
    "ldap_cache_livetime",
    Age(
        title = _('LDAP Cache Livetime'),
        help  = _('This option defines the maximum age for using the cached LDAP data. The time of the '
                  'last LDAP synchronisation is saved and checked on every request to the multisite '
                  'interface. Once the cache gets outdated, a new synchronisation job is started.<br><br>'
                  'Please note: Passwords of the users are never stored in WATO and therefor never cached!'),
        minvalue = 1,
        default_value = 300,
    ),
    domain = "multisite",
    in_global_settings = False,
)

register_configvar(group,
    "ldap_debug_log",
    Optional(
        Filename(
            label = _("Absolute path to log file"),
            default = defaults.var_dir + '/web/ldap-debug.log',
            trans_func = userdb.ldap_replace_macros,
        ),
          title = _("LDAP connection diagnostics"),
          label = _("Activate logging of LDAP transactions into a logfile"),
          help = _("If this option is used and set to a filename, Check_MK will create a logfile "
                   "containing details about connecting to LDAP and the single transactions.")),
    domain = "multisite",
    in_global_settings = False,
)

register_configvar(group,
    "lock_on_logon_failures",
    Optional(
        Integer(
            label = _("Number of logon failures to lock the account"),
            default_value = 3,
            minvalue = 1,
        ),
        none_value = False,
        title = _("Lock user accounts after N logon failures"),
        label = _("Activate automatic locking of user accounts"),
        help = _("This options enables automatic locking of user account after "
                 "N logon failures. One successful login resets the failure counter.")
    ),
    domain = "multisite"
)

register_configvar(group,
    "password_policy",
    Dictionary(
        title = _('htpasswd: Password Policy'),
        help  = _('You can define some rules to which each user password ahers. By default '
                  'all passwords are accepted, even ones which are made of only a single character, '
                  'which is obviously a bad idea. Using this option you can enforce your users '
                  'to choose more secure passwords.'),
        elements = [
            ('min_length', Integer(
                title = _("Minimum password length"),
                minvalue = 1,
            )),
            ('num_groups', Integer(
                title = _("Number of character groups to use"),
                minvalue = 1,
                maxvalue = 4,
                help = _("Force the user to choose a password that contains characters from at least "
                         "this number of different character groups. "
                         "Character groups are: <ul>"
                         "<li>lowercase letters</li>"
                         "<li>uppercase letters</li>"
                         "<li>digits</li>"
                         "<li>special characters such as an underscore or dash</li>"
                         "</ul>"),
            )),
            ('max_age', Age(
                title = _("Maximum age of passwords"),
                minvalue = 1,
                display = ["days"],
            )),
        ],
    ),
    domain = "multisite",
)

def list_roles():
    roles = userdb.load_roles()
    return [ (i, r["alias"]) for i, r in roles.items() ]

def list_contactgroups():
    contact_groups = userdb.load_group_information().get("contact", {})
    entries = [ (c, g['alias']) for c, g in contact_groups.items() ]
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

register_configvar(group,
    "save_user_access_times",
    Checkbox(
        title = _("Save last access times of users"),
        label = _("Save the time of the latest user activity"),
        help = _("When enabled, the time of the last access is stored for each user. The last "
                 "activity is shown on the users page."),
        default_value = False
    ),
    domain = "multisite"
)


register_configvar(group,
    "export_folder_permissions",
    Checkbox(
        title = _("Export WATO folder permissions"),
        label = _("Make WATO folder permissions usable e.g. by NagVis"),
        help = _("It is possible to create maps representing the WATO folder hierarchy within "
                 "NagVis by naming the maps like the folders are named internally. To make the "
                 "restriction of access to the maps as comfortable as possible, the permissions "
                 "configured within WATO can be exported to NagVis."),
        default_value = False,
    ),
    domain = "multisite"
)

#.
#   .--Check_MK------------------------------------------------------------.
#   |              ____ _               _        __  __ _  __              |
#   |             / ___| |__   ___  ___| | __   |  \/  | |/ /              |
#   |            | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /               |
#   |            | |___| | | |  __/ (__|   <    | |  | | . \               |
#   |             \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\              |
#   |                                      |_____|                         |
#   +----------------------------------------------------------------------+
#   |  Operation mode of Check_MK                                          |
#   '----------------------------------------------------------------------'

group = _("Operation mode of Check_MK")


register_configvar(group,
    "use_new_descriptions_for",
    ListChoice(
        title = _("Use new service descriptions"),
        help = _("In order to make Check_MK more consistent, "
                 "the descriptions of several services have been renamed in newer "
                 "Check_MK versions. One example is the filesystem services that have "
                 "been renamed from <tt>fs_</tt> into <tt>Filesystem</tt>. But since renaming "
                 "of existing services has many implications - including existing rules, performance "
                 "data and availability history - these renamings are disabled per default for "
                 "existing installations. Here you can switch to the new descriptions for "
                 "selected check types"),
        choices = [
            ( "df",                               _("Used space in filesystems")),
            ( "df_netapp",                        _("NetApp Filers: Used Space in Filesystems")),
            ( "df_netapp32",                      _("NetApp Filers: Used space in Filesystem Using 32-Bit Counters")),
            ( "esx_vsphere_datastores",           _("VMWare ESX host systems: Used space")),
            ( "hr_fs",                            _("Used space in filesystems via SNMP")),
            ( "vms_diskstat.df",                  _("Disk space on OpenVMS")),
            ( "zfsget",                           _("Used space in ZFS pools and filesystems")),
            ( "ps",                               _("State and Count of Processes") ),
            ( "ps.perf",                          _("State and Count of Processes (with additional performance data)")),
            ( "wmic_process",                     _("Resource consumption of windows processes")),
            ( "services",                         _("Windows Services")),
            ( "logwatch",                         _("Check logfiles for relevant new messages")),
            ( "cmk-inventory",                    _("Monitor hosts for unchecked services (Check_MK Discovery)")),
            ( "hyperv_vms",                       _("Hyper-V Server: State of VMs")),
            ( "ibm_svc_mdiskgrp",                 _("IBM SVC / Storwize V3700 / V7000: Status and Usage of MDisksGrps")),
            ( "ibm_svc_system",                   _("IBM SVC / V7000: System Info")),
            ( "ibm_svc_systemstats.diskio",       _("IBM SVC / V7000: Disk Throughput for Drives/MDisks/VDisks in Total")),
            ( "ibm_svc_systemstats.iops",         _("IBM SVC / V7000: IO operations/sec for Drives/MDisks/VDisks in Total")),
            ( "ibm_svc_systemstats.disk_latency", _("IBM SVC / V7000: Latency for Drives/MDisks/VDisks in Total")),
            ( "ibm_svc_systemstats.cache",        _("IBM SVC / V7000: Cache Usage in Total")),
        ],
        render_orientation = "vertical",
    ),
    need_restart = True
)


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
            ('wait' , _("Wait until the other has finished") ),
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
    "piggyback_max_cachefile_age",
    Age(title = _("Maximum age for piggyback files"),
            help = _("The maximum age for piggy back data from another host to be valid for monitoring. "
                     "Older files are deleted before processing them. Please make sure that this age is "
                     "at least as large as you normal check interval for piggy hosts.")),
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

register_configvar(group,
    "use_dns_cache",
    Checkbox(
        title = _("Use DNS lookup cache"),
        label = _("Prevent DNS lookups by use of a cache file"),
        help = _("When this option is enabled (which is the default), then Check_MK tries to "
                 "prevent IP address lookups during the configuration generation. This can speed "
                 "up this process greatly when you have a larger number of hosts. The cache is stored "
                 "in a simple file. Note: when the cache is enabled then changes of the IP address "
                 "of a host in your name server will not be detected immediately. If you need an "
                 "immediate update then simply disable the cache once, activate the changes and "
                 "enabled it again. OMD based installations automatically update the cache once "
                 "a day."),
        default_value = True,
    ),
    need_restart = True
)

register_configvar(group,
    "use_inline_snmp",
    Checkbox(
        title = _("Use Inline SNMP"),
        label = _("Enable inline SNMP (directly use net-snmp libraries)"),
        help = _("By default Check_MK uses command line calls of Net-SNMP tools like snmpget or "
                 "snmpwalk to gather SNMP information. For each request a new command line "
                 "program is being executed. It is now possible to use the inline SNMP implementation "
                 "which calls the net-snmp libraries directly via its python bindings. This "
                 "should increase the performance of SNMP checks in a significant way. The inline "
                 "SNMP mode is a feature which improves the performance for large installations and "
                 "only available via our subscription."),
        default_value = False
    ),
    need_restart = True
)

register_configvar(group,
    "record_inline_snmp_stats",
    Checkbox(
        title = _("Record statistics of Inline SNMP"),
        label = _("Enable recording of Inline SNMP statistics"),
        help = _("When you have enabled Inline SNMP, you can use this flag to enable recording of "
                 "some performance related values. The recorded values are stored in a single file "
                 "at <tt>var/check_mk/snmp.stats</tt>.<br><br>"
                 "<i>Please note:</i> Only enable this for a short period, because it will "
                 "decrease the performance of your monitoring."),
        default_value = False
    ),
    need_restart = True
)

group = _("Service discovery")

register_configvar(group,
    "inventory_check_interval",
    Optional(
        Integer(title = _("Perform service discovery check every"),
                unit = _("minutes"),
                min_value = 1,
                default_value = 720),
        title = _("Enable regular service discovery checks"),
        help = _("If enabled, Check_MK will create one additional service per host "
                 "that does a regular check, if the service discovery would find new services "
                 "currently un-monitored.")),
    need_restart = True)

register_configvar(group,
    "inventory_check_severity",
    DropdownChoice(
        title = _("Severity of failed service discovery check"),
        help = _("Please select which alarm state the service discovery check services "
                 "shall assume in case that un-monitored services are found."),
        choices = [
            (0, _("OK - do not alert, just display")),
            (1, _("Warning") ),
            (2, _("Critical") ),
            (3, _("Unknown") ),
            ],
        default_value = 1))

register_configvar(group,
    "inventory_check_do_scan",
    DropdownChoice(
        title = _("Service discovery check for SNMP devices"),
        choices = [
           ( True, _("Perform full SNMP scan always, detect new check types") ),
           ( False, _("Just rely on existing check files, detect new items only") )
        ]
    ))

register_configvar(group,
    "inventory_check_autotrigger",
    Checkbox(
        title = _("Service discovery triggers service discovery check"),
        label = _("Automatically schedule service discovery check after service configuration changes"),
        help = _("When this option is enabled then after each change of the service "
                 "configuration of a host via WATO - may it be via manual changes or a bulk "
                 "discovery - the service discovery check is automatically rescheduled in order "
                 "to reflect the new service state correctly immediately."),
        default_value = True,
    ))



_if_portstate_choices = [
                        ( '1', 'up(1)'),
                        ( '2', 'down(2)'),
                        ( '3', 'testing(3)'),
                        ( '4', 'unknown(4)'),
                        ( '5', 'dormant(5)') ,
                        ( '6', 'notPresent(6)'),
                        ( '7', 'lowerLayerDown(7)'),
                        ]

_brocade_fcport_adm_choices = [
                        ( 1, 'online(1)'),
                        ( 2, 'offline(2)'),
                        ( 3, 'testing(3)'),
                        ( 4, 'faulty(4)'),
                        ]

_brocade_fcport_op_choices = [
                        ( 0, 'unkown(0)'),
                        ( 1, 'online(1)'),
                        ( 2, 'offline(2)'),
                        ( 3, 'testing(3)'),
                        ( 4, 'faulty(4)'),
                        ]

_brocade_fcport_phy_choices = [
                        ( 1, 'noCard(1)'),
                        ( 2, 'noTransceiver(2)'),
                        ( 3, 'laserFault(3)'),
                        ( 4, 'noLight(4)'),
                        ( 5, 'noSync(5)'),
                        ( 6, 'inSync(6)'),
                        ( 7, 'portFault(7)'),
                        ( 8, 'diagFault(8)'),
                        ( 9, 'lockRef(9)'),
                        ( 10, 'validating(10)'),
                        ( 11, 'invalidModule(11)'),
                        ( 14, 'noSigDet(14)'),
                        ( 255, 'unkown(255)'),
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

register_configvar(deprecated,
    "if_inventory_uses_description",
    Checkbox(title = _("Use description as service name for network interface checks"),
             label = _("use description"),
             help = _("This option lets Check_MK use the interface description as item instead "
                      "of the port number. If no description is available then the port number is "
                      "used anyway.")))

register_configvar(deprecated,
    "if_inventory_uses_alias",
    Checkbox(title = _("Use alias as service name for network interface checks"),
             label = _("use alias"),
             help = _("This option lets Check_MK use the alias of the port (ifAlias) as item instead "
                      "of the port number. If no alias is available then the port number is used "
                      "anyway.")))

register_configvar(deprecated,
   "if_inventory_portstates",
   ListChoice(title = _("Network interface port states to inventorize"),
              help = _("When doing inventory on switches or other devices with network interfaces "
                       "then only ports found in one of the configured port states will be added to the monitoring."),
              choices = _if_portstate_choices))

register_configvar(deprecated,
   "if_inventory_porttypes",
   ListChoice(title = _("Network interface port types to inventorize"),
              help = _("When doing inventory on switches or other devices with network interfaces "
                       "then only ports of the specified types will be created services for."),
              choices = _if_porttype_choices,
              columns = 3))

register_configvar(deprecated,
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

group = _("Check configuration")


register_configvar(deprecated,
    "if_inventory_monitor_state",
    Checkbox(title = _("Monitor port state of network interfaces"),
             label = _("monitor port state"),
             help = _("When this option is active then during inventory of networking interfaces "
                      "(and switch ports) the current operational state of the port will "
                      "automatically be coded as a check parameter into the check. That way the check "
                      "will get warning or critical when the state changes. This setting can later "
                      "by overridden on a per-host and per-port base by defining special check "
                      "parameters via a rule.")))

register_configvar(deprecated,
    "if_inventory_monitor_speed",
    Checkbox(title = _("Monitor port speed of network interfaces"),
             label = _("monitor port speed"),
             help = _("When this option is active then during inventory of networking interfaces "
                      "(and switch ports) the current speed setting of the port will "
                      "automatically be coded as a check parameter into the check. That way the check "
                      "will get warning or critical when speed later changes (for example from "
                      "100 Mbit/s to 10 Mbit/s). This setting can later "
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

register_configvar(deprecated,
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

#.
#   .--Rulesets------------------------------------------------------------.
#   |                ____        _                _                        |
#   |               |  _ \ _   _| | ___  ___  ___| |_ ___                  |
#   |               | |_) | | | | |/ _ \/ __|/ _ \ __/ __|                 |
#   |               |  _ <| |_| | |  __/\__ \  __/ |_\__ \                 |
#   |               |_| \_\\__,_|_|\___||___/\___|\__|___/                 |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Rulesets for hosts and services except check parameter rules.        |
#   '----------------------------------------------------------------------'

register_rulegroup("grouping", _("Grouping"),
   _("Assignment of host &amp; services to host, service and contacts groups. "))
group = "grouping"

register_rule(group,
    "host_groups",
    GroupSelection(
        "host",
        title = _("Assignment of hosts to host groups"),
        help = _("Hosts can be grouped together into host groups. The most common use case "
                 "is to put hosts which belong together in a host group to make it possible "
                 "to get them listed together in the status GUI.")),
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
    Transform(
        Age(minvalue=1, default_value=60),
        forth = lambda v: int(v * 60),
        back = lambda v: float(v) / 60.0,
        title = _("Normal check interval for service checks"),
        help = _("Check_MK usually uses an interval of one minute for the active Check_MK "
                 "check and for legacy checks. Here you can specify a larger interval. Please "
                 "note, that this setting only applies to active checks (those with the "
                 "%s reschedule button). If you want to change the check interval of "
                 "the Check_MK service only, specify <tt><b>Check_MK$</b></tt> in the list "
                 "of services.") % '<img class="icon docu" src="images/icon_reload.gif">'),
    itemtype = "service")

register_rule(group,
    "extra_service_conf:retry_interval",
    Transform(
        Age(minvalue=1, default_value=60),
        forth = lambda v: int(v * 60),
        back = lambda v: float(v) / 60.0,
        title = _("Retry check interval for service checks"),
        help = _("This setting is relevant if you have set the maximum number of check "
                 "attempts to a number greater than one. In case a service check is not OK "
                 "and the maximum number of check attempts is not yet reached, it will be "
                 "rescheduled with this interval. The retry interval is usually set to a smaller "
                 "value than the normal interval.<br><br>This setting only applies to "
                 "active checks.")),
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
        choices = [ ("1", _("Enable processing of passive check results")),
                    ("0", _("Disable processing of passive check results")) ],
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
    Transform(
        Age(minvalue=1, default_value=60),
        forth = lambda v: int(v * 60),
        back = lambda v: float(v) / 60.0,
        title = _("Normal check interval for host checks"),
        help = _("The default interval is set to one minute. Here you can specify a larger "
                 "interval. The host is contacted in this interval on a regular base. The host "
                 "check is also being executed when a problematic service state is detected to check "
                 "wether or not the service problem is resulting from a host problem.")
    )
)

register_rule(group,
    "extra_host_conf:retry_interval",
    Transform(
        Age(minvalue=1, default_value=60),
        forth = lambda v: int(v * 60),
        back = lambda v: float(v) / 60.0,
        title = _("Retry check interval for host checks"),
        help = _("This setting is relevant if you have set the maximum number of check "
                 "attempts to a number greater than one. In case a host check is not UP "
                 "and the maximum number of check attempts is not yet reached, it will be "
                 "rescheduled with this interval. The retry interval is usually set to a smaller "
                 "value than the normal interval."),
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

register_rule(
    group,
    "host_check_commands",
    CascadingDropdown(
        title = _("Host Check Command"),
        help = _("Usually Check_MK uses a series of PING (ICMP echo request) in order to determine "
                 "whether a host is up. In some cases this is not possible, however. With this rule "
                 "you can specify an alternative way of determining the host's state."),
        choices = [
          ( "ping",       _("PING (active check with ICMP echo request)") ),
          ( "smart",      _("Smart PING (only with Check_MK Micro Core)") ),
          ( "tcp" ,       _("TCP Connect"), Integer(label = _("to port:"), minvalue=1, maxvalue=65535, default_value=80 )),
          ( "ok",         _("Always assume host to be up") ),
          ( "agent",      _("Use the status of the Check_MK Agent") ),
          ( "service",    _("Use the status of the service..."),
            TextUnicode(
                label = ":",
                size = 45,
                allow_empty = False,
                attrencode = True,
            )),
          ( "custom",     _("Use a custom check plugin..."), PluginCommandLine() ),
        ],
        default_value = "ping",
        html_separator = " ",
    ),
    match = 'first'
)


register_rule(group,
    "extra_host_conf:check_command",
    TextAscii(
        title = _("Internal Command for Hosts Check"),
        label = _("Command:"),
        help = _("This ruleset is deprecated and will be removed soon: "
                 "it changes the default check_command for a host check. You need to "
                 "define that command manually in your monitoring configuration."),
        attrencode = True,
    ),
)

def get_snmp_checktypes():
   checks = check_mk_local_automation("get-check-information")
   types = [ (cn, (c['title'] != cn and '%s: ' % cn or '') + c['title'])
             for (cn, c) in checks.items() if c['snmp'] ]
   types.sort()
   return [ (None, _('All SNMP Checks')) ] + types

register_rule(group,
    "snmp_check_interval",
    Tuple(
        title = _('Check intervals for SNMP checks'),
        help = _('This rule can be used to customize the check interval of each SNMP based check. '
                 'With this option it is possible to configure a longer check interval for specific '
                 'checks, than then normal check interval.'),
        elements = [
            DropdownChoice(
                title = _("Checktype"),
                choices = get_snmp_checktypes,
            ),
            Integer(
                title = _("Do check every"),
                unit = _("minutes"),
                min_value = 1,
                default_value = 1,
            ),
        ]
    )
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
    itemtype = "service"
)

register_rule(group,
    "extra_host_conf:notification_options",
    Transform(
        ListChoice(
            choices = [
               ( "d",  _("Host goes down")),
               ( "u",  _("Host gets unreachble")),
               ( "r",  _("Host goes up again")),
               ( "f",  _("Start or end of flapping state")),
               ( "s",  _("Start or end of a scheduled downtime")),
            ],
            default_value = [ "d", "u", "r", "f", "s" ],
        ),
        title = _("Notified events for hosts"),
        help = _("This ruleset allows you to restrict notifications of host problems to certain "
               "states, e.g. only notify on DOWN, but not on UNREACHABLE. Please select the types "
               "of events that should initiate notifications. Please note that several other "
               "filters must also be passed in order for notifications to finally being sent out."),
        forth = lambda x: x != 'n' and x.split(",") or [],
        back = lambda x: ",".join(x) or "n",
    ),
)

register_rule(group,
    "extra_service_conf:notification_options",
    Transform(
        ListChoice(
            choices = [
                ("w", _("Service goes into warning state")),
                ("u", _("Service goes into unknown state")),
                ("c", _("Service goes into critical state")),
                ("r", _("Service recovers to OK")),
                ("f", _("Start or end of flapping state")),
                ("s", _("Start or end of a scheduled downtime")),
            ],
            default_value = [ "w", "u", "c", "r", "f", "s" ],
        ),
        title = _("Notified events for services"),
        help = _("This ruleset allows you to restrict notifications of service problems to certain "
               "states, e.g. only notify on CRIT, but not on WARN. Please select the types "
               "of events that should initiate notifications. Please note that several other "
               "filters must also be passed in order for notifications to finally being sent out."),
        forth = lambda x: x != 'n' and x.split(",") or [],
        back = lambda x: ",".join(x) or "n",
    ),
    itemtype = "service"
)

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
    ),
    factory_default = 0,
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
    factory_default = 0,
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
        label = _("URL:"),
        title = _("Notes URL for Services"),
        help = _("With this setting you can set links to documentations "
                 "for each service"),
        attrencode = True,
    ),
    itemtype = "service")

register_rule(group,
    "extra_host_conf:notes_url",
    TextAscii(
        label = _("URL:"),
        title = _("Notes URL for Hosts"),
        help = _("With this setting you can set links to documentations "
                 "for Hosts"),
        attrencode = True,
    ),
)

register_rule(group,
   "extra_service_conf:display_name",
   TextUnicode(
       title = _("Alternative display name for Services"),
       help = _("This rule set allows you to specify an alternative name "
                "to be displayed for certain services. This name is available as "
                "a column when creating new views or modifying existing ones. "
                "It is always visible in the details view of a service. In the "
                "availability reporting there is an option for using that name "
                "instead of the normal service description. It does <b>not</b> automatically "
                "replace the normal service name in all views.<br><br><b>Note</b>: The "
                "purpose of this rule set is to define unique names for several well-known "
                "services. It cannot rename services in general."),
       size = 64,
       attrencode = True,
   ),
   itemtype = "service")


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
    title = _("Disabled services"),
    help = _("Services that are declared as <u>disabled</u> by this rule set will not be added "
             "to a host during inventory (automatic service detection). Services that already "
             "exist will continued to be monitored but be marked as obsolete in the service "
             "list of a host."),
    itemtype = "service")

register_rule(group,
    "ignored_checks",
    CheckTypeSelection(
        title = _("Disabled checks"),
        help = _("This ruleset is similar to 'Disabled services', but selects checks to be disabled "
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

register_rule(group,
     "clustered_services_mapping",
     TextAscii(
        title = _("Clustered services for overlapping clusters"),
        label = _("Assign services to the following cluster:"),
        help = _("It's possible to have clusters that share nodes. You could say that "
                  "such clusters &quot;overlap&quot;. In such a case using the ruleset "
                  "<i>Clustered services</i> is not sufficient since it would not be clear "
                  "to which of the several possible clusters a service found on such a shared "
                  "node should be assigned to. With this ruleset you can assign services and "
                  "explicitely specify which cluster assign them to."),
     ),
     itemtype = "service",
     )

register_rule(group,
    "extra_host_conf:service_period",
    TimeperiodSelection(
        title = _("Service period for hosts"),
        help = _("When it comes to availability reporting, you might want the report "
                 "to cover only certain time periods, e.g. only Monday to Friday "
                 "from 8:00 to 17:00. You can do this by specifying a service period "
                 "for hosts or services. In the reporting you can then decide to "
                 "include, exclude or ignore such periods und thus e.g. create a report "
                 "of the availability just within or without these times. <b>Note</b>: Changes in the "
                 "actual <i>definition</i> of a time period will only be reflected in "
                 "times <i>after</i> that change. Selecting a different service period "
                 "will also be reflected in the past.")),
    )

register_rule(group,
    "extra_service_conf:service_period",
    TimeperiodSelection(
        title = _("Service period for services"),
        help = _("When it comes to availability reporting, you might want the report "
                 "to cover only certain time periods, e.g. only Monday to Friday "
                 "from 8:00 to 17:00. You can do this by specifying a service period "
                 "for hosts or services. In the reporting you can then decide to "
                 "include, exclude or ignore such periods und thus e.g. create a report "
                 "of the availability just within or without these times. <b>Note</b>: Changes in the "
                 "actual <i>definition</i> of a time period will only be reflected in "
                 "times <i>after</i> that change. Selecting a different service period "
                 "will also be reflected in the past.")),
    itemtype = "service")

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
        ValueSpec.custom_validate(self, value, varprefix)



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

_snmpv3_auth_elements = [
    DropdownChoice(
        choices = [
            ( "md5", _("MD5") ),
            ( "sha", _("SHA1") ),
        ],
        title = _("Authentication protocol")
    ),
    TextAscii(
        title = _("Security name"),
        attrencode = True
    ),
    Password(
        title = _("Authentication password"),
        minlen = 8,
    )
]

register_rule(group,
    "snmp_communities",
    Alternative(
        elements = [
            TextAscii(
                title = _("SNMP community (SNMP Versions 1 and 2c)"),
                allow_empty = False,
                attrencode = True,
            ),
            Tuple(
                title = _("Credentials for SNMPv3 without authentication and privacy (noAuthNoPriv)"),
                elements = [
                    FixedValue("noAuthNoPriv",
                        title = _("Security Level"),
                        totext = _("No authentication, no privacy"),
                    ),
                ]
            ),
            Tuple(
                title = _("Credentials for SNMPv3 with authentication but without privacy (authNoPriv)"),
                elements = [
                    FixedValue("authNoPriv",
                        title = _("Security Level"),
                        totext = _("authentication but no privacy"),
                    ),
                ] + _snmpv3_auth_elements
            ),
            Tuple(
                title = _("Credentials for SNMPv3 with authentication and privacy (authPriv)"),
                elements = [
                    FixedValue("authPriv",
                        title = _("Security Level"),
                        totext = _("authentication and encryption"),
                    ),
                ] + _snmpv3_auth_elements + [
                    DropdownChoice(
                        choices = [
                            ( "DES", _("DES") ),
                            ( "AES", _("AES") ),
                        ],
                        title = _("Privacy protocol")
                    ),
                    Password(
                        title = _("Privacy pass phrase"),
                        minlen = 8,
                    ),
                ]
            ),
        ],

        match = lambda x: type(x) == tuple and ( \
                          len(x) == 1 and 1 or \
                          len(x) == 4 and 2 or 3) or 0,

        style = "dropdown",
        default_value = "public",
        title = _("SNMP credentials of monitored hosts"),
        help = _("By default Check_MK uses the community \"public\" to contact hosts via SNMP v1/v2. This rule "
                 "can be used to customize the the credentials to be used when contacting hosts via SNMP.")))

register_rule(group,
    "snmp_character_encodings",
    DropdownChoice(
        title = _("Output text coding settings for SNMP devices"),
        help = _("Some devices send texts in non-ASCII characters. Check_MK"
                 " always assumes UTF-8 encoding. You can declare other "
                 " other encodings here"),
        choices = [
           ("utf-8", _("UTF-8") ),
           ("latin1" ,_("latin1")),
           ]
        )),

register_rule(group,
    "bulkwalk_hosts",
    title = _("Hosts using SNMP bulk walk (enforces SNMP v2c)"),
    help = _("Most SNMP hosts support SNMP version 2c. However, Check_MK defaults to version 1, "
             "in order to support as many devices as possible. Please use this ruleset in order "
             "to configure SNMP v2c for as many hosts as possible. That version has two advantages: "
             "it supports 64 bit counters, which avoids problems with wrapping counters at too "
             "much traffic. And it supports bulk walk, which saves much CPU and network resources. "
             "Please be aware, however, that there are some broken devices out there, that support "
             "bulk walk but behave very bad when it is used. When you want to enable v2c while not using "
             "bulk walk, please use the rule set snmpv2c_hosts instead."))

register_rule(group,
    "snmp_without_sys_descr",
    title = _("Hosts without system description OID"),
    help = _("Devices which do not publish the system description OID "
             ".1.3.6.1.2.1.1.1.0 are normally ignored by the SNMP inventory. "
             "Use this ruleset to select hosts which should nevertheless "
             "be checked."))

register_rule(group,
    "snmpv2c_hosts",
    title = _("Legacy SNMP devices using SNMP v2c"),
    help = _("There exist a few devices out there that behave very badly when using SNMP v2c and bulk walk. "
             "If you want to use SNMP v2c on those devices, nevertheless, you need to configure this device as "
             "legacy snmp device and upgrade it to SNMP v2c (without bulk walk) with this rule set. One reason is enabling 64 bit counters. "
             "Note: This rule won't apply if the device is already configured as SNMP v2c device."))

register_rule(group,
    "snmp_timing",
    Dictionary(
        title = _("Timing settings for SNMP access"),
        help = _("This rule decides about the number of retries and timeout values "
                 "for the SNMP access to devices."),
        elements = [
            ( "timeout",
              Float(
                  title = _("Timeout between retries"),
                  help = _("After a request is sent to the remote SNMP agent we will wait up to this "
                           "number of seconds until assuming the answer get lost and retrying."),
                  default_value = 1,
                  minvalue = 0.1,
                  maxvalue = 60,
                  allow_int = True,
                  unit = _("sec"),
                  size = 6,
              ),
            ),
            ( "retries",
              Integer(
                  title = _("Number of retries"),
                  default_value = 5,
                  minvalue = 0,
                  maxvalue = 50,
              )
            ),
       ]
    ),
    factory_default = { "timeout" : 1, "retries" : 5 },
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
            minvalue = 1,
            maxvalue = 65535,
            default_value = 6556),
    title = _("TCP port for connection to Check_MK agent"),
    help = _("This variable allows to specify the TCP port to "
             "be used to connect to the agent on a per-host-basis. "),
)

register_rule(group,
    "check_mk_exit_status",
    Dictionary(
        elements = [
            ( "connection",
              MonitoringState(
                default_value = 2,
                title = _("State in case of connection problems")),
            ),
            ( "timeout",
              MonitoringState(
                default_value = 2,
                title = _("State in case of a overall timeout")),
            ),
            ( "missing_sections",
              MonitoringState(
                default_value = 1,
                title = _("State if just <i>some</i> agent sections are missing")),
            ),
            ( "empty_output",
              MonitoringState(
                default_value = 2,
                title = _("State in case of empty agent output")),
            ),
            ( "wrong_version",
              MonitoringState(
                default_value = 1,
                title = _("State in case of wrong agent version")),
            ),
            ( "exception",
              MonitoringState(
                default_value = 3,
                title = _("State in case of unhandled exception")),
            ),
        ],
    ),
    factory_default = { "connection" : 2, "missing_sections" : 1, "empty_output" : 2, "wrong_version" : 1, "exception": 3 },
    title = _("Status of the Check_MK service"),
    help = _("This ruleset specifies the total status of the Check_MK service in "
             "case of various error situations. One use case is the monitoring "
             "of hosts that are not always up. You can have Check_MK an OK status "
             "here if the host is not reachable. Note: the <i>Timeout</i> setting only works "
             "when using the Check_MK Micro Core."),
    match = "dict",
)

register_rule(group,
    "check_mk_agent_target_versions",
    Transform(
        CascadingDropdown(
            title = _("Check for correct version of Check_MK agent"),
            help = _("Here you can make sure that all of your Check_MK agents are running"
                     " one specific version. Agents running "
                     " a different version return a non-OK state."),
            choices = [
                ("ignore",   _("Ignore the version")),
                ("site",     _("Same version as the monitoring site")),
                ("specific", _("Specific version"),
                    TextAscii(
                        allow_empty = False,
                    )
                ),
                ("at_least", _("At least"),
                    Dictionary(
                        elements = [
                            ('release', TextAscii(
                                title = _('Official Release version'),
                                allow_empty = False,
                            )),
                            ('daily_build', TextAscii(
                                title = _('Daily build'),
                                allow_empty = False,
                            )),
                        ]
                    ),
                ),
            ],
            default_value = "ignore",
        ),
        # In the past, this was a OptionalDropdownChoice() which values could be strings:
        # ignore, site or a custom string representing a version number.
        forth = lambda x: type(x) == str and x not in [ "ignore", "site" ] and ("specific", x) or x
    )
)

register_rule(group,
    "piggyback_translation",
    HostnameTranslation(
        title = _("Hostname translation for piggybacked hosts"),
        help = _("Some agents or agent plugins send data not only for the queried host but also "
                 "for other hosts &quot;piggyback&quot; with their own data. This is the case "
                 "for the vSphere special agent and the SAP R/3 plugin, for example. The hostnames "
                 "that these agents send must match your hostnames in your monitoring configuration. "
                 "If that is not the case, then with this rule you can define a hostname translation. "
                 "Note: This rule must be configured for the &quot;pig&quot; - i.e. the host that the "
                 "agent is running on. It is not applied to the translated piggybacked hosts."),
    ),
    match = "dict")
