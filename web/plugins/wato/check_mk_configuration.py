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

import re

import cmk
import cmk.paths

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

group = _("User Interface")
configvar_order()[group] = 20

def web_log_level_elements():
    import logging

    elements = []
    for level_id, title, help_text in [
        ("cmk.web",          _("Web"),
         _("The log level for all log entries not assigned to the other "
           "log categories on this page.")),
        ("cmk.web.auth",     _("Authentication"),
         _("The log level for user authentication related log entries.")),
        ("cmk.web.ldap",     _("LDAP"),
         _("The log level for LDAP related log entries.")),
        ("cmk.web.bi.compilation", _("BI compilation"),
         _("If this option is enabled, Check_MK BI will create a log with details "
           "about compiling BI aggregations. This includes statistics and "
           "details for each executed compilation.")),
        ]:
        elements.append(
            (level_id, DropdownChoice(
                title = title,
                help = help_text,
                choices = [
                        (logging.CRITICAL, _("Critical") ),
                        (logging.ERROR,    _("Error") ),
                        (logging.WARNING,  _("Warning") ),
                        (logging.INFO,     _("Informational") ),
                        (logging.DEBUG,    _("Debug") ),
                ],
                default_value = logging.WARNING,
            ))
        )

    return elements


register_configvar(group,
    "bulk_discovery_default_settings",
    ModeBulkDiscovery.vs_bulk_discovery(),
    domain = "multisite"
)

register_configvar(
    group,
    "log_levels",
    Dictionary(
        title = _("Logging"),
        help = _("This setting decides which types of messages to log into "
                 "the web log <tt>%s</tt>.") % site_neutral_path(cmk.paths.log_dir + "/web.log"),
        elements = web_log_level_elements,
        optional_keys = [],
    ),
    domain = "multisite",
)


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
                 "into the Multisite var directory named <tt>multisite.profile</tt> and "
                 "<tt>multisite.profile.py</tt>. By executing the later file you can get "
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
    "quicksearch_search_order",
    ListOf(
        Tuple(
            elements = [
                DropdownChoice(
                    title = _("Search filter"),
                    choices = [
                        ("h",  _("Hostname")),
                        ("al", _("Hostalias")),
                        ("ad", _("Hostaddress")),
                        ("tg", _("Hosttag")),
                        ("hg", _("Hostgroup")),
                        ("sg", _("Servicegroup")),
                        ("s",  _("Service Description")),
                    ],
                ),
                DropdownChoice(
                    title = _("Match behaviour"),
                    choices = [
                        ("continue",          _("Continue search")),
                        ("finished",          _("Search finished: Also show all results of previous filters")),
                        ("finished_distinct", _("Search finished: Only show results of this filter")),
                    ],
                ),
            ],
        ),
        title = _("Quicksearch search order"),
        default_value = [("h", "continue"), ("al", "continue"), ("ad", "continue"), ("s", "continue")],
        add_label = _("Add search filter")
    ),
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
    "crash_report_target",
    TextAscii(title = _("Mail Address for Crash reports"),
              help = _("This Address will be used as default receiver address for crash reports"),
              size = 80,
              default_value = "feedback@check-mk.org",
              attrencode = True),
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


def virtual_host_tree_choices():
    return \
        wato_host_tag_group_choices() \
        + [ ("foldertree:", _("WATO folder tree")) ] \
        + [ ( "folder:%d" % l, _("WATO folder level %d") % l) for l in range(1, 7) ]


def transform_virtual_host_trees(trees):
    def id_from_title(title):
        return re.sub("[^-a-zA-Z0-9_]+", "", title.lower())

    for index, tree in enumerate(trees):
        if type(tree) == tuple:
            trees[index] = {
                "id"         : id_from_title(tree[0]),
                "title"      : tree[0],
                "tag_groups" : tree[1],
            }
        else:
            # Transform existing dicts with old key "tag_groups"
            if "tag_groups" in tree:
                tree["tree_spec"] = tree.pop("tag_groups")

    return sorted(trees, key = lambda x: x["title"])


def validate_virtual_host_trees(value, varprefix):
    tree_ids = set()
    for tree in value:
        if tree["id"] in tree_ids:
            raise MKUserError(varprefix, _("The ID needs to be unique."))
        tree_ids.add(tree["id"])

        # Validate that each element is selected once
        seen = set()
        for element in tree["tree_spec"]:
            if element in seen:
                raise MKUserError(varprefix,
                    _("Found '%s' a second time in tree '%s'. Each element can only be "
                      "choosen once.") % (element, tree["id"]))

            seen.add(element)



register_configvar(group,
    "virtual_host_trees",
    Transform(
        ListOf(
            Dictionary(
                elements = [
                    ("id", ID(
                        title = _("ID"),
                        allow_empty = False,
                    )),
                    ("title", TextUnicode(
                        title = _("Title of the tree"),
                        allow_empty = False,
                    )),
                    ("exclude_empty_tag_choices", Checkbox(
                        title = _("Exclude empty tag choices"),
                        default_value = False,
                    )),
                    ("tree_spec", ListOf(
                        DropdownChoice(
                            choices = virtual_host_tree_choices,
                        ),
                        title = _("Tree levels"),
                        allow_empty = False,
                        magic = "#!#",
                    )),
                ],
                optional_keys = [],
            ),
            add_label = _("Create new virtual host tree configuration"),
            title = _("Virtual Host Trees"),
            help = _("Here you can define tree configurations for the snapin <i>Virtual Host-Trees</i>. "
                     "These trees organize your hosts based on their values in certain host tag groups. "
                     "Each host tag group you select will create one level in the tree."),
            validate = validate_virtual_host_trees,
            movable = False,
        ),
        forth = transform_virtual_host_trees,
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
    "bi_use_legacy_compilation",
    Checkbox(title = _("Use legacy compilation for BI aggregations (slower)"),
             label = _("Use legacy BI compilation"),
             default_value = False),
    domain = "multisite")

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
             default_value = True),
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
                              for (l,a) in i18n.get_languages()
                        ],
                        columns = 2,
                    ),
                ],
            ),
            title = _("Custom localizations"),
            movable = False,
            totext = _("%d translations"),
            default_value = sorted(config.user_localizations.items()),
        ),
        forth = lambda d: sorted(d.items()),
        back = lambda l: dict(l),
    ),
    domain = "multisite",
)

register_configvar(group,
    "user_icons_and_actions",
    Transform(
        ListOf(
            Tuple(
                elements = [
                    ID(title = _("ID")),
                    Dictionary(
                        elements = [
                            ('icon', IconSelector(
                                title = _('Icon'),
                                allow_empty = False
                            )),
                            ('title', TextUnicode(title = _('Title'))),
                            ('url', Transform(
                                Tuple(
                                    title = _('Action'),
                                    elements = [
                                        TextAscii(
                                            title = _('URL'),
                                            help = _('This URL is opened when clicking on the action / icon. You '
                                                     'can use some macros within the URL which are dynamically '
                                                     'replaced for each object. These are:<br>'
                                                     '<ul><li>$HOSTNAME$: Contains the name of the host</li>'
                                                     '<li>$SERVICEDESC$: Contains the service description '
                                                     '(in case this is a service)</li>'
                                                     '<li>$HOSTADDRESS$: Contains the network address of the host</li></ul>'),
                                            size = 80,
                                        ),
                                        DropdownChoice(
                                            title = _("Open in"),
                                            choices = [
                                                ("_blank",  _("Load in a new window / tab")),
                                                ("_self",   _("Load in current content area (keep sidebar)")),
                                                ("_top",    _("Load as new page (hide sidebar)")),
                                            ],
                                        ),
                                    ],
                                ),
                                forth = lambda x: type(x) != tuple and (x, "_self") or x,
                            )),
                            ('toplevel', FixedValue(True,
                                title = _('Show in column'),
                                totext = _('Directly show the action icon in the column'),
                                help = _('Makes the icon appear in the column instead '
                                         'of the dropdown menu.'),
                            )),
                            ('sort_index', Integer(
                                title = _('Sort index'),
                                help = _('You can use the sort index to control the order of the '
                                         'elements in the column and the menu. The elements are sorted '
                                         'from smaller to higher numbers. The action menu icon '
                                         'has a sort index of <tt>10</tt>, the graph icon a sort index '
                                         'of <tt>20</tt>. All other default icons have a sort index of '
                                         '<tt>30</tt> configured.'),
                                min_value = 0,
                                default_value = 15,
                            )),
                        ],
                        optional_keys = ['title', 'url', 'toplevel', 'sort_index'],
                    ),
                ],
            ),
            title = _("Custom icons and actions"),
            movable = False,
            totext = _("%d icons and actions"),
        ),
        forth = lambda d: sorted(d.items()),
        back = lambda l: dict(l),
    ),
    domain = "multisite",
)

register_configvar(group,
    "user_downtime_timeranges",
    ListOf(
        Dictionary(
            elements = [
                ('title', TextUnicode(title = _('Title'))),
                ('end', Alternative(
                    title = _("To"),
                    elements = [
                        Age(
                            title = _("Duration"),
                            display = [ "minutes", "hours", "days" ]
                        ),
                        DropdownChoice(
                            title = _("Until"),
                            choices = [
                                ('next_day', _("Start of next day")),
                                ('next_week', _("Start of next week")),
                                ('next_month', _("Start of next month")),
                                ('next_year', _("Start of next year")),
                            ],
                            default_value = "next_day"
                        )
                    ],
                    style = "dropdown",
                    default_value = 24 *60 * 60,
                ))
            ],
            optional_keys = [],
        ),
        title = _("Custom Downtime Timeranges"),
        movable = True,
        totext = _("%d timeranges"),
        default_value = [
            {'title': _("2 hours"),    'end': 2 * 60 * 60},
            {'title': _("Today"),      'end': 'next_day'},
            {'title': _("This week"),  'end': 'next_week'},
            {'title': _("This month"), 'end': 'next_month'},
            {'title': _("This year"),  'end': 'next_year'},
        ]
    ),
    domain = "multisite",
)


def get_builtin_icons():
    import views
    return [ (id, id) for id in views.get_multisite_icons().keys() ]

register_configvar(group,
    "builtin_icon_visibility",
    Transform(
        ListOf(
            Tuple(
                elements = [
                    DropdownChoice(
                        title = _("Icon"),
                        choices = get_builtin_icons,
                        sorted = True,
                    ),
                    Dictionary(
                        elements = [
                            ('toplevel', Checkbox(
                                title = _('Show in column'),
                                label = _('Directly show the action icon in the column'),
                                help = _('Makes the icon appear in the column instead '
                                         'of the dropdown menu.'),
                                default_value = True,
                            )),
                            ('sort_index', Integer(
                                title = _('Sort index'),
                                help = _('You can use the sort index to control the order of the '
                                         'elements in the column and the menu. The elements are sorted '
                                         'from smaller to higher numbers. The action menu icon '
                                         'has a sort index of <tt>10</tt>, the graph icon a sort index '
                                         'of <tt>20</tt>. All other default icons have a sort index of '
                                         '<tt>30</tt> configured.'),
                                min_value = 0,
                            )),
                        ],
                        optional_keys = ['toplevel', 'sort_index'],
                    ),
                ],
            ),
            title = _("Builtin icon visibility"),
            movable = False,
            totext = _("%d icons customized"),
            help = _("You can use this option to change the default visibility "
                     "options of the builtin icons. You can change whether or not "
                     "the icons are shown in the popup menu or on top level and "
                     "change the sorting of the icons."),
        ),
        forth = lambda d: sorted(d.items()),
        back = lambda l: dict(l),
    ),
    domain = "multisite",
)


register_configvar(group,
    "service_view_grouping",
    ListOf(
        Dictionary(
            elements = [
                ('title', TextUnicode(
                    title = _('Title to show for the group'),
                )),
                ('pattern', RegExpUnicode(
                    title = _('Grouping expression'),
                    help = _('This regular expression is used to match the services to be put '
                             'into this group. This is a prefix match regular expression.'),
                    mode = RegExpUnicode.prefix,
                )),
                ('min_items', Integer(
                    title = _('Minimum number of items to create a group'),
                    help = _('When less than these items are found for a group, the services '
                             'are not shown grouped together.'),
                    min_value = 2,
                    default_value = 2,
                )),
            ],
            optional_keys = [],
        ),
        title = _("Grouping of services in table views"),
        help = _("You can use this option to make the service table views fold services matching "
                 "the given patterns into groups. Only services in state <i>OK</i> will be folded "
                 "together. Groups of only one service will not be rendered. If multiple patterns "
                 "match a service, the service will be added to the first matching group."),
        add_label = _("Add new grouping definition"),
    ),
    domain = "multisite",
)

# Helper that retrieves the list of hostgroups via Livestatus
# use alias by default but fallback to name if no alias defined
def list_hostgroups():
    groups = dict(sites.live().query("GET hostgroups\nCache: reload\nColumns: name alias\n"))
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

register_configvar(group,
    "view_action_defaults",
    Dictionary(
        title    = _("View action defaults"),
        elements = [
            ("ack_sticky", Checkbox(
                title = _("Sticky"), label = _("Enable"), default_value = True,
            )),
            ("ack_notify", Checkbox(
                title = _("Send notification"), label = _("Enable"), default_value = True,
            )),
            ("ack_persistent", Checkbox(
                title = _("Persistent comment"), label = _("Enable"), default_value = False,
            )),
        ],
        optional_keys = [],
    ),
    domain = "multisite"
)


register_configvar(_("Site Management"),
    "trusted_certificate_authorities",
    Dictionary(
        title = _("Trusted certificate authorities for SSL"),
        help = _("Whenever a server component of Check_MK opens a SSL connection it uses the "
                 "certificate authorities configured here for verifying the SSL certificate of "
                 "the destination server. This is used for example when performing WATO "
                 "replication to slave sites or when special agents are communicating via HTTPS. "
                 "The CA certificates configured here will be written to the CA bundle %s.") %
                    site_neutral_path(ConfigDomainCACertificates.trusted_cas_file),
        elements = [
            ("use_system_wide_cas", Checkbox(
                title = _("Use system wide CAs"),
                help = _("All supported linux distributions provide a mechanism of managing "
                         "trusted CAs. Depending on your linux distributions the paths where "
                         "these CAs are stored and the commands to manage the CAs differ. "
                         "Please checko out the documentation of your linux distribution "
                         "in case you want to customize trusted CAs system wide. You can "
                         "choose here to trust the system wide CAs here. Check_MK will search "
                         "these directories for system wide CAs: %s") %
                            ", ".join(ConfigDomainCACertificates.system_wide_trusted_ca_search_paths),
                label = _("Trust system wide configured CAs"),
                default_value = True,
            )),
            ("trusted_cas", ListOfCAs(
                title = _("Check_MK specific"),
                allow_empty = True,
                default_value = [],
            )),
        ],
        optional_keys = False,
    ),
    domain = ConfigDomainCACertificates,
    need_restart = True,
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

group = _("Administration Tool (WATO)")
configvar_order()[group] = 25

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

register_configvar(group,
    "wato_hide_folders_without_read_permissions",
    Checkbox(title = _("Hide folders without read permissions"),
             label = _("hide folders without read permissions"),
             help = _("When enabled, a subfolder is not shown, when the user does not have sufficient "
                      "permissions to this folder and all of its subfolders. However, the subfolder is "
                      "shown if the user has permissions to any of its subfolder."),
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
configvar_order()[group] = 40

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
        help = _("This options enables automatic locking of user accounts after "
                 "the configured number of consecutive invalid login attempts. "
                 "Once the account is locked only an admin user can unlock it. "
                 "Beware: Also the admin users will be locked that way. You need "
                 "to manually edit <tt>etc/htpasswd</tt> and remove the <tt>!</tt> "
                 "in case you are locked out completely."),
    ),
    domain = "multisite"
)

register_configvar(group,
    "password_policy",
    Dictionary(
        title = _('Password policy for local accounts'),
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
                default_value = 365 * 86400,
            )),
        ],
    ),
    domain = "multisite",
)

register_configvar(group,
    "user_idle_timeout",
    Optional(
        Age(
            title = None,
            display = [ "minutes", "hours", "days" ],
            minvalue = 60,
            default_value = 3600,
        ),
        title = _("Login session idle timeout"),
        label = _("Enable a login session idle timeout"),
        help = _("Normally a user login session is valid until the password is changed or "
                 "the user is locked. By enabling this option, you can apply a time limit "
                 "to login sessions which is applied when the user stops interacting with "
                 "the GUI for a given amount of time. When a user is exceeding the configured "
                 "maximum idle time, the user will be logged out and redirected to the login "
                 "screen to renew the login session. This setting can be overriden for each "
                 "user individually in the profile of the users."),
    ),
    domain = "multisite"
)

register_configvar(group,
    "single_user_session",
    Optional(
        Age(
            title = None,
            display = [ "minutes", "hours" ],
            label = _("Session timeout:"),
            minvalue = 30,
            default_value = 60,
        ),
        title = _("Limit login to single session at a time"),
        label = _("Users can only login from one client at a time"),
        help = _("Normally a user can login to the GUI from unlimited number of clients at "
                 "the same time. If you want to enforce your users to be able to login only once "
                 " (from one client which means device and browser), you can enable this option. "
                 "When the user logs out or is inactive for the configured amount of time, the "
                 "session is invalidated automatically and the user has to log in again from the "
                 "current or another device."),
    ),
    domain = "multisite"
)

def list_roles():
    roles = userdb.load_roles()
    return [ (i, r["alias"]) for i, r in roles.items() ]

def list_contactgroups():
    contact_groups = userdb.load_group_information().get("contact", {})
    entries = [ (c, g['alias']) for c, g in contact_groups.items() ]
    entries.sort()
    return entries


def default_user_profile_elements():
    elements = []

    if cmk.is_managed_edition():
        elements += managed.customer_choice_element()

    return elements + [
            ('roles', ListChoice(
                title = _('User roles'),
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
        ]


register_configvar(group,
    "default_user_profile",
    Dictionary(
        title = _("Default user profile"),
        help  = _("With this option you can specify the attributes a user which is created during "
                  "its initial login gets added. For example, the default is to add the role \"user\" "
                  "to all automatically created users."),
        elements = default_user_profile_elements,
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

group = _("Execution of checks")
configvar_order()[group] = 10


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
            ( "logwatch.groups",                  _("Check logfile groups")),
            ( "cmk-inventory",                    _("Monitor hosts for unchecked services (Check_MK Discovery)")),
            ( "hyperv_vms",                       _("Hyper-V Server: State of VMs")),
            ( "ibm_svc_mdiskgrp",                 _("IBM SVC / Storwize V3700 / V7000: Status and Usage of MDisksGrps")),
            ( "ibm_svc_system",                   _("IBM SVC / V7000: System Info")),
            ( "ibm_svc_systemstats.diskio",       _("IBM SVC / V7000: Disk Throughput for Drives/MDisks/VDisks in Total")),
            ( "ibm_svc_systemstats.iops",         _("IBM SVC / V7000: IO operations/sec for Drives/MDisks/VDisks in Total")),
            ( "ibm_svc_systemstats.disk_latency", _("IBM SVC / V7000: Latency for Drives/MDisks/VDisks in Total")),
            ( "ibm_svc_systemstats.cache",        _("IBM SVC / V7000: Cache Usage in Total")),
            ( "casa_cpu_temp",                    _("Casa module: CPU temperature")),
            ( "cmciii.temp",                      _("Rittal CMC-III Units: Temperatures")),
            ( "cmciii.psm_current",               _("Rittal CMC-III Units: Current")),
            ( "cmciii_lcp_airin",                 _("Rittal CMC-III LCP: Air In and Temperature")),
            ( "cmciii_lcp_airout",                _("Rittal CMC-III LCP: Air Out Temperature")),
            ( "cmciii_lcp_water",                 _("Rittal CMC-III LCP: Water In/Out Temperature")),
            ( "etherbox.temp",                    _("Etherbox / MessPC: Sensor Temperature")),
            ( "liebert_bat_temp",                 _("Liebert UPS Device: Temperature sensor")),
            ( "nvidia.temp",                      _("Temperatures of NVIDIA graphics card")),
            ( "ups_bat_temp",                     _("Generic UPS Device: Temperature sensor")),
            ( "innovaphone_temp",                 _("Innovaphone Gateway: Current Temperature")),
            ( "enterasys_temp",                   _("Enterasys Switch: Temperature")),
            ( "raritan_emx",                      _("Raritan EMX Rack: Temperature")),
            ( "raritan_pdu_inlet",                _("Raritan PDU: Input Phases")),
            ( "mknotifyd",                        _("Notification Spooler")),
            ( "mknotifyd.connection",             _("Notification Spooler Connection")),
            ( "postfix_mailq",                    _("Postfix: Mail Queue")),
            ( "nullmailer_mailq",                 _("Nullmailer: Mail Queue")),
            ( "barracuda_mailqueues",             _("Barracuda: Mail Queue")),
            ( "qmail_stats",                      _("Qmail: Mail Queue")),
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
                     "If your check cycle is set to a larger value than one minute then "
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
configvar_order()[group] = 4

register_configvar(group,
    "inventory_check_interval",
    Optional(
        Integer(title = _("Perform service discovery check every"),
                unit = _("minutes"),
                min_value = 1,
                default_value = 720),
        title = _("Enable regular service discovery checks (deprecated)"),
        help = _("If enabled, Check_MK will create one additional service per host "
                 "that does a regular check, if the service discovery would find new services "
                 "currently un-monitored. <b>Note:</b> This option is deprecated and has been "
                 "replaced by the rule set <a href='%s'>Periodic Service Discovery</a>, "
                 "which allows a per-host configuration and additional features such as "
                 "automatic rediscovery. Rules in that rule set will override the global "
                 "settings done here.") % "wato.py?mode=edit_ruleset&varname=periodic_discovery",
    ),
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
   _("Assignment of host & services to host, service and contacts groups. "))
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
                 "of services.") % html.render_icon("reload"),
    ),
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


def _host_check_command_choices():
    if config.user.may('wato.add_or_modify_executables'):
        custom_choice = [
            ( "custom",     _("Use a custom check plugin..."), PluginCommandLine() ),
        ]
    else:
        custom_choice = []

    return [
          ( "ping",       _("PING (active check with ICMP echo request)") ),
          ( "smart",      _("Smart PING (only with Check_MK Micro Core)") ),
          ( "tcp" ,       _("TCP Connect"), Integer(label = _("to port:"), minvalue=1, maxvalue=65535, default_value=80 )),
          ( "ok",         _("Always assume host to be up") ),
          ( "agent",      _("Use the status of the Check_MK Agent") ),
          ( "service",    _("Use the status of the service..."),
            TextUnicode(
                size = 45,
                allow_empty = False,
                attrencode = True,
                help = _("You can use the macro <tt>$HOSTNAME$</tt> here. It will be replaced "
                         "with the name of the current host."),
            )),
        ] + custom_choice



register_rule(
    group,
    "host_check_commands",
    CascadingDropdown(
        title = _("Host Check Command"),
        help = _("Usually Check_MK uses a series of PING (ICMP echo request) in order to determine "
                 "whether a host is up. In some cases this is not possible, however. With this rule "
                 "you can specify an alternative way of determining the host's state."),
        choices = _host_check_command_choices,
        default_value = "ping",
        orientation = "horizontal",
    ),
    match = 'first'
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


def transform_float_minutes_to_age(float_minutes):
    return int(float_minutes * 60)

def transform_age_to_float_minutes(age):
    return float(age) / 60.0

register_rule(group,
    "extra_host_conf:first_notification_delay",
    Transform(
        Age(
            minvalue = 0,
            default_value = 300,
            label = _("Delay:"),
            title = _("Delay host notifications"),
            help = _("This setting delays notifications about host problems by the "
                     "specified amount of time. If the host is up again within that "
                     "time, no notification will be sent out."),
        ),
        forth = transform_float_minutes_to_age,
        back = transform_age_to_float_minutes,
    ),
    factory_default = 0.0,
)

register_rule(group,
    "extra_service_conf:first_notification_delay",
    Transform(
        Age(
            minvalue = 0,
            default_value = 300,
            label = _("Delay:"),
            unit = _("minutes"),
            title = _("Delay service notifications"),
            help = _("This setting delays notifications about service problems by the "
                     "specified amount of time. If the service is OK again within that "
                     "time, no notification will be sent out."),
        ),
        forth = transform_float_minutes_to_age,
        back = transform_age_to_float_minutes,
    ),
    factory_default = 0.0,
    itemtype = "service")


register_rule(group,
    "extra_host_conf:notification_interval",
    Optional(
        Transform(
            Float(
                minvalue = 0.05,
                default_value = 120.0,
                label = _("Interval:"),
                unit = _("minutes")),
            forth = lambda x: float(x),
        ),
        title = _("Periodic notifications during host problems"),
        help = _("If you enable periodic notifications, then during a problem state "
               "of the host notifications will be sent out in regular intervals "
               "until the problem is acknowledged."),
        label = _("Enable periodic notifications"),
        none_label = _("disabled"),
        none_value = 0.0,
        )
    )



register_rule(group,
    "extra_service_conf:notification_interval",
    Optional(
        Transform(
            Float(
                minvalue = 0.05,
                default_value = 120.0,
                label = _("Interval:"),
                unit = _("minutes")),
            forth = lambda x: float(x),
        ),
        title = _("Periodic notifications during service problems"),
        help = _("If you enable periodic notifications, then during a problem state "
               "of the service notifications will be sent out in regular intervals "
               "until the problem is acknowledged."),
        label = _("Enable periodic notifications"),
        none_label = _("disabled"),
        none_value = 0.0,
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
             "to a host during discovery (automatic service detection). Services that already "
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


register_rule(group,
    "periodic_discovery",
    Alternative(
        title = _("Periodic service discovery"),
        style = "dropdown",
        default_value = {
            "check_interval"          : 2 * 60,
            "severity_unmonitored"    : 1,
            "severity_vanished"       : 0,
            "inventory_check_do_scan" : True,
        },
        elements = [
            FixedValue(
                None,
                title = _("Do not perform periodic service discovery check"),
                totext = _("no discovery check"),
            ),
            Dictionary(
                title = _("Perform periodic service discovery check"),
                help = _("If enabled, Check_MK will create one additional service per host "
                        "that does a periodic check, if the service discovery would find new services "
                        "that are currently not monitored."),
                elements = [
                    ( "check_interval",
                        Transform(
                            Age(
                                minvalue=1,
                                display = [ "days", "hours", "minutes" ]
                            ),
                            forth = lambda v: int(v * 60),
                            back = lambda v: float(v) / 60.0,
                            title = _("Perform service discovery every"),
                        ),
                    ),
                    ( "severity_unmonitored",
                      DropdownChoice(
                         title = _("Severity of unmonitored services"),
                         help = _("Please select which alarm state the service discovery check services "
                                  "shall assume in case that un-monitored services are found."),
                         choices = [
                             (0, _("OK - do not alert, just display")),
                             (1, _("Warning") ),
                             (2, _("Critical") ),
                             (3, _("Unknown") ),
                         ],
                    )),
                    ( "severity_vanished",
                      DropdownChoice(
                         title = _("Severity of vanished services"),
                         help = _("Please select which alarm state the service discovery check services "
                                  "shall assume in case that non-existing services are being monitored."),
                         choices = [
                             (0, _("OK - do not alert, just display")),
                             (1, _("Warning") ),
                             (2, _("Critical") ),
                             (3, _("Unknown") ),
                         ],
                    )),
                    ( "inventory_check_do_scan",
                      DropdownChoice(
                         title = _("Service discovery check for SNMP devices"),
                         choices = [
                             ( True, _("Perform full SNMP scan always, detect new check types") ),
                             ( False, _("Just rely on existing check files, detect new items only") )
                         ]
                    )),
                    ( "inventory_rediscovery",
                      Dictionary(
                         title = _("Automatically update service configuration"),
                         help = _("If active the check will not only notify about un-monitored services, "
                                  "it will also automatically add/remove them as neccessary."),
                         elements = [
                             ( "mode",
                               DropdownChoice(
                                    title = _("Mode"),
                                    choices = [
                                        (0, _("Add unmonitored services")),
                                        (1, _("Remove vanished services")),
                                        (2, _("Add unmonitored & remove vanished services")),
                                        (3, _("Refresh all services (tabula rasa)"))
                                    ],
                                    orientation = "vertical",
                                    default_value = 0,
                             )),
                             ( "group_time",
                                Age(
                                    title = _("Group discovery and activation for up to"),
                                    help = _("A delay can be configured here so that multiple "
                                             "discoveries can be activated in one go. This avoids frequent core "
                                             "restarts in situations with frequent services changes."),
                                    default_value = 15 * 60,
                                    display = [ "hours", "minutes" ]
                             )),
                             ( "excluded_time",
                               TimeofdayRanges(
                                   title = _("Never do discovery or activate changes in the following time ranges"),
                                   help = _("This avoids automatic changes during these times so "
                                            "that the automatic system doesn't interfere with "
                                            "user activity."),
                                   count = 3,
                             )),
                             ("activation",
                              DropdownChoice(
                                  title = _("Automatic activation"),
                                  choices = [
                                      ( True,  _("Automatically activate changes") ),
                                      ( False, _("Do not activate changes") ),
                                  ],
                                  default_value = True,
                                  help = _("Here you can have the changes activated whenever services "
                                           "have been added or removed."),
                              )),
                             ( "service_whitelist",
                              ListOfStrings(
                                  title = _("Activate only services matching"),
                                  allow_empty = False,
                                  help = _("Set service names or regular expression patterns here to "
                                           "allow only matching services to be activated automatically. "
                                           "If you set both this and \'Don't activate services matching\', "
                                           "both rules have to apply for a service to be activated."),
                              )),
                             ( "service_blacklist",
                              ListOfStrings(
                                  title = _("Don't activate services matching"),
                                  allow_empty = False,
                                  help = _("Set service names or regular expression patterns here to "
                                           "prevent matching services from being activated automatically. "
                                           "If you set both this and \'Activate only services matching\', "
                                           "both rules have to apply for a service to be activated."),
                              )),
                         ],
                         optional_keys = ["service_whitelist", "service_blacklist"],
                     )),
                ],
                optional_keys = ["inventory_rediscovery"],
            )
        ]
    )
)


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


register_rule(group,
    "extra_host_conf:icon_image",
    Transform(
        IconSelector(
            title = _("Icon image for hosts in status GUI"),
            help = _("You can assign icons to hosts for the status GUI. "
                     "Put your images into <tt>%s</tt>. ") %
                    ( cmk.paths.omd_root + "/local/share/check_mk/web/htdocs/images/icons"),
        ),
        forth = lambda v: v and (v.endswith('.png') and v[:-4]) or v,
    ))


register_rule(group,
    "extra_service_conf:icon_image",
    Transform(
        IconSelector(
            title = _("Icon image for services in status GUI"),
            help = _("You can assign icons to services for the status GUI. "
                     "Put your images into <tt>%s</tt>. ") %
                    (cmk.paths.omd_root + "/local/share/check_mk/web/htdocs/images/icons"),
        ),
        forth = lambda v: v and (v.endswith('.png') and v[:-4]) or v,
    ),
    itemtype = "service")

register_rule(group,
    "host_icons_and_actions",
    UserIconOrAction(
        title = _("Custom icons or actions for hosts in status GUI"),
        help = _("You can assign icons or actions to hosts for the status GUI.")
    ),
    match = "all",
)

register_rule(group,
    "service_icons_and_actions",
    UserIconOrAction(
        title = _("Custom icons or actions for services in status GUI"),
        help = _("You can assign icons or actions to services for the status GUI."),
    ),
    match = "all",
    itemtype = "service",
)


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

register_rule(group,
    "primary_address_family",
    DropdownChoice(
        choices = [
            ("ipv4", _("IPv4")),
            ("ipv6", _("IPv6")),
        ],
        title = _("Primary IP address family of dual-stack hosts"),
        help = _("When you configure dual-stack host (IPv4 + IPv6) monitoring in Check_MK, "
                 "normally IPv4 is used as primary address family to communicate with this "
                 "host. The other family, IPv6, is just being pinged. You can use this rule "
                 "to invert this behaviour to use IPv6 as primary address family.")))

group = "agent/" + _("SNMP")



register_rule(group,
    "snmp_communities",
    SNMPCredentials(
        title = _("SNMP credentials of monitored hosts"),
        help = _("By default Check_MK uses the community \"public\" to contact hosts via SNMP v1/v2. This rule "
                 "can be used to customize the the credentials to be used when contacting hosts via SNMP."),
    )
)

register_rule(group,
    "snmp_character_encodings",
    DropdownChoice(
        title = _("Output text encoding settings for SNMP devices"),
        help = _("Some devices send texts in non-ASCII characters. Check_MK"
                 " always assumes UTF-8 encoding. You can declare other "
                 " other encodings here"),
        choices = [
           ("utf-8",  _("UTF-8") ),
           ("latin1", _("latin1")),
           ("cp437",  _("cp437")),
        ]
    )
)

register_rule(group,
    "bulkwalk_hosts",
    title = _("Bulk walk: Hosts using bulk walk (enforces SNMP v2c)"),
    help = _("Most SNMP hosts support SNMP version 2c. However, Check_MK defaults to version 1, "
             "in order to support as many devices as possible. Please use this ruleset in order "
             "to configure SNMP v2c for as many hosts as possible. That version has two advantages: "
             "it supports 64 bit counters, which avoids problems with wrapping counters at too "
             "much traffic. And it supports bulk walk, which saves much CPU and network resources. "
             "Please be aware, however, that there are some broken devices out there, that support "
             "bulk walk but behave very bad when it is used. When you want to enable v2c while not using "
             "bulk walk, please use the rule set snmpv2c_hosts instead."))


register_rule(group,
    "snmp_bulk_size",
    Integer(
        title = _("Bulk walk: Number of OIDs per bulk"),
        label = _("Number of OIDs to request per bulk: "),
        minvalue = 10,
        maxvalue = 100,
        default_value = 10,
    ),
    help = _("This variable allows you to configure the numbr of OIDs Check_MK should request "
             "at once. This rule only applies to SNMP hosts that are configured to be bulk walk "
             "hosts."
             "You may want to use this rule to tune SNMP performance. Be aware: A higher value "
             "is not always better. It may decrease the transactions between Check_MK and the "
             "target system, but may increase the OID overhead in case you only need a small "
             "amount of OIDs."),
)

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
                  title = _("Response timeout for a single query"),
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
    "non_inline_snmp_hosts",
    title = _("Hosts not using Inline-SNMP"),
    help = _("Check_MK has an efficient SNMP implementation called Inline SNMP which reduces the "
             "load produced by SNMP monitoring on the monitoring host significantly. This option is "
             "enabled by default for all SNMP hosts and it is a good idea to keep this default "
             "setting. However, there are SNMP devices which have problems with this SNMP "
             "implementation. You can use this rule to disable Inline SNMP for these hosts."))


register_rule(group,
    "usewalk_hosts",
    title = _("Simulating SNMP by using a stored SNMP walk"),
    help = _("This ruleset helps in test and development. You can create stored SNMP "
             "walks on the command line with cmk --snmpwalk HOSTNAME. A host that "
             "is configured with this ruleset will then use the information from that "
             "file instead of using real SNMP. "))

register_rule(group,
    "snmp_ports",
    Integer(
        minvalue = 1,
        maxvalue = 65535,
        default_value = 161
    ),
    title = _("UDP port used for SNMP"),
    help = _("This variable allows you to customize the UDP port to "
             "be used to communicate via SNMP on a per-host-basis."),
)

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
    "agent_encryption",
    Dictionary(
        elements = [
            ( "passphrase", PasswordSpec(title = _("Encryption secret"), allow_empty = False, hidden = True) ),
            ( "use_regular", DropdownChoice(title = _("Encryption for Agent"),
                    help = _("Choose if the agent agents encrypt packages. This controls whether "
                             "baked agents encrypt their output and whether check_mk expects "
                             "encrypted output. "
                             "Please note: If you opt to enforce encryption, "
                             "agents that don't support encryption will not work any more. "
                             "Further note: This only affects regular agents, not special agents "
                             "aka datasource programs."),
                    default_value = "disable",
                    choices = [
                        ( "enforce", _("Enforce (drop unencrypted data)") ),
                        ( "allow",   _("Enable  (accept encrypted and unencrypted data)") ),
                        ( "disable", _("Disable (drop encrypted data)") )
                    ])
            ),
            ( "use_realtime", DropdownChoice(title = _("Encryption for Realtime Updates"),
                    help = _("Choose if realtime updates are sent/expected encrypted"),
                    default_value = "enforce",
                    choices = [
                        ( "enforce", _("Enforce (drop unencrypted data)") ),
                        ( "allow",   _("Enable  (accept encrypted and unencrypted data)") ),
                        ( "disable", _("Disable (drop encrypted data)") )
                    ])
            ),
        ],
        optional_keys = []
    ),
    title = _("Encryption"),
    help = _("Control encryption of data sent from agent to host."),
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

register_rule(group,
    "snmpv3_contexts",
    Tuple(
        title = _('SNMPv3 contexts to use in requests'),
        help = _('By default Check_MK does not use a specific context during SNMPv3 queries, '
                 'but some devices are offering their information in different SNMPv3 contexts. '
                 'This rule can be used to configure, based on hosts and check type, which SNMPv3 '
                 'contexts Check_MK should ask for when getting information via SNMPv3.'),
        elements = [
            DropdownChoice(
                title = _("Checktype"),
                choices = get_snmp_checktypes,
            ),
            ListOfStrings(
                title = _("SNMP Context IDs"),
                allow_empty = False,
            ),
        ]
    )
)
