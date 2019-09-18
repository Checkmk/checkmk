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
import logging

import cmk
import cmk.utils.paths

import cmk.gui.sites as sites
import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.utils as utils
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _

from cmk.gui.valuespec import (
    Dictionary,
    TextAscii,
    TextUnicode,
    DropdownChoice,
    Tuple,
    ListOf,
    Integer,
    Float,
    Transform,
    ListOfStrings,
    IPNetwork,
    CascadingDropdown,
    MonitoringState,
    RegExpUnicode,
    IconSelector,
    PasswordSpec,
    ListOfTimeRanges,
    Age,
    FixedValue,
    Optional,
    Alternative,
    ListChoice,
    Checkbox,
    ID,
    ListOfCAs,
    LogLevelChoice,
    Labels,
)

from cmk.gui.plugins.wato import (
    config_variable_group_registry,
    ConfigVariableGroup,
    config_variable_registry,
    ConfigVariable,
    ConfigDomainGUI,
    ConfigDomainCore,
    ConfigDomainCACertificates,
    site_neutral_path,
    rulespec_registry,
    HostRulespec,
    ServiceRulespec,
    BinaryHostRulespec,
    BinaryServiceRulespec,
    rulespec_group_registry,
    RulespecGroup,
    RulespecSubGroup,
    PluginCommandLine,
    UserIconOrAction,
    SNMPCredentials,
    IPMIParameters,
    HostnameTranslation,
    ServiceDescriptionTranslation,
    ContactGroupSelection,
    HostGroupSelection,
    ServiceGroupSelection,
    CheckTypeSelection,
    TimeperiodSelection,
    HTTPProxyInput,
    get_check_information,
)

from cmk.gui.plugins.wato.omd_configuration import ConfigVariableGroupSiteManagement
from cmk.gui.plugins.views.icons import icon_and_action_registry
from cmk.gui.watolib.bulk_discovery import vs_bulk_discovery
from cmk.gui.watolib.groups import load_contact_group_information

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


@config_variable_group_registry.register
class ConfigVariableGroupUserInterface(ConfigVariableGroup):
    def title(self):
        return _("User Interface")

    def sort_index(self):
        return 20


@config_variable_registry.register
class ConfigVariableUITheme(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "ui_theme"

    def valuespec(self):
        return DropdownChoice(
            title=_("User interface theme"),
            help=_("Change the default user interface theme of your Check_MK installation"),
            choices=config.theme_choices(),
        )


@config_variable_registry.register
class ConfigVariableBulkDiscoveryDefaultSettings(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "bulk_discovery_default_settings"

    def valuespec(self):
        return vs_bulk_discovery()


@config_variable_registry.register
class ConfigVariableLogLevels(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "log_levels"

    def valuespec(self):
        return Dictionary(
            title=_("Logging"),
            help=_("This setting decides which types of messages to log into "
                   "the web log <tt>%s</tt>.") %
            site_neutral_path(cmk.utils.paths.log_dir + "/web.log"),
            elements=self._web_log_level_elements(),
            optional_keys=[],
        )

    def _web_log_level_elements(self):
        elements = []
        for level_id, title, help_text in [
            ("cmk.web", _("Web"),
             _("The log level for all log entries not assigned to the other "
               "log categories on this page.")),
            ("cmk.web.auth", _("Authentication"),
             _("The log level for user authentication related log entries.")),
            ("cmk.web.ldap", _("LDAP"), _("The log level for LDAP related log entries.")),
            ("cmk.web.bi.compilation", _("BI compilation"),
             _("If this option is enabled, Check_MK BI will create a log with details "
               "about compiling BI aggregations. This includes statistics and "
               "details for each executed compilation.")),
            ("cmk.web.automations", _("Automation calls"),
             _("Communication between different components of Check_MK (e.g. GUI and check engine) "
               "will be logged in this log level."))
        ]:
            elements.append((level_id,
                             LogLevelChoice(
                                 title=title,
                                 help=help_text,
                                 default_value=logging.WARNING,
                             )))

        return elements


@config_variable_registry.register
class ConfigVariableDebug(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "debug"

    def valuespec(self):
        return Checkbox(
            title=_("Debug mode"),
            label=_("enable debug mode"),
            help=_("When Multisite is running in debug mode, internal Python error messages "
                   "are being displayed and various debug information in other places is "
                   "also available."),
        )


@config_variable_registry.register
class ConfigVariableGUIProfile(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "profile"

    def valuespec(self):
        return DropdownChoice(
            title=_("Profile requests"),
            help=_("It is possible to profile the rendering process of Multisite pages. This "
                   "Is done using the Python module cProfile. When profiling is performed "
                   "two files are created <tt>%s</tt> and <tt>%s</tt>. By executing the later "
                   "file you can get runtime statistics about the last processed page. When "
                   "enabled by request the profiling mode is enabled by providing the HTTP "
                   "variable <tt>_profile</tt>.") %
            (site_neutral_path(cmk.utils.paths.var_dir + "/multisite.profile"),
             site_neutral_path(cmk.utils.paths.var_dir + "/multisite.profile.py")),
            choices=[
                (False, _("Disable profiling")),
                ("enable_by_var", _("Enable profiling by request")),
                (True, _("Enable profiling for all requests")),
            ],
        )


@config_variable_registry.register
class ConfigVariableDebugLivestatusQueries(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "debug_livestatus_queries"

    def valuespec(self):
        return Checkbox(
            title=_("Debug Livestatus queries"),
            label=_("enable debug of Livestatus queries"),
            help=_("With this option turned on all Livestatus queries made by Multisite "
                   "in order to render views are being displayed."),
        )


@config_variable_registry.register
class ConfigVariableSelectionLivetime(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "selection_livetime"

    def valuespec(self):
        return Integer(
            title=_('Checkbox Selection Livetime'),
            help=
            _('This option defines the maximum age of unmodified checkbox selections stored for users. '
              'If a user modifies the selection in a view, these selections are persisted for the currently '
              'open view. When a view is re-opened a new selection is used. The old one remains on the '
              'server until the livetime is exceeded.'),
            minvalue=1,
        )


@config_variable_registry.register
class ConfigVariableShowLivestatusErrors(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "show_livestatus_errors"

    def valuespec(self):
        return Checkbox(
            title=_("Show MK Livestatus error messages"),
            label=_("show errors"),
            help=
            _("This option controls whether error messages from unreachable sites are shown in the output of "
              "views. Those error messages shall alert you that not all data from all sites has been shown. "
              "Other people - however - find those messages distracting. "),
        )


@config_variable_registry.register
class ConfigVariableEnableSounds(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "enable_sounds"

    def valuespec(self):
        return Checkbox(
            title=_("Enable sounds in views"),
            label=_("enable sounds"),
            help=_("If sounds are enabled then the user will be alarmed by problems shown "
                   "in a Multisite status view if that view has been configured for sounds. "
                   "From the views shipped in with Multisite all problem views have sounds "
                   "enabled."),
        )


@config_variable_registry.register
class ConfigVariableContextButtonsToShow(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "context_buttons_to_show"

    def valuespec(self):
        return Optional(
            Integer(
                title=_("show"),
                label=_("buttons"),
                minvalue=1,
                maxvalue=100,
                size=2,
            ),
            title=_("Number of context buttons to show"),
            label=_("Show only most frequently used buttons"),
            help=_("If this option is enabled, then Multisite only show the most "
                   "used context buttons and hides the rest. Which buttons are used "
                   "how often is computed separately per user."),
        )


@config_variable_registry.register
class ConfigVariableSoftQueryLimit(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "soft_query_limit"

    def valuespec(self):
        return Integer(
            title=_("Soft query limit"),
            help=_("Whenever the number of returned datasets of a view would exceed this "
                   "limit, a warning is being displayed and no further data is being shown. "
                   "A normal user can override this limit with one mouse click."),
            minvalue=1,
        )


@config_variable_registry.register
class ConfigVariableHardQueryLimit(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "hard_query_limit"

    def valuespec(self):
        return Integer(
            title=_("Hard query limit"),
            help=_("Whenever the number of returned datasets of a view would exceed this "
                   "limit, an error message is shown. The normal user cannot override "
                   "the hard limit. The purpose of the hard limit is to secure the server "
                   "against useless queries with huge result sets."),
            minvalue=1,
        )


@config_variable_registry.register
class ConfigVariableQuicksearchDropdownLimit(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "quicksearch_dropdown_limit"

    def valuespec(self):
        return Integer(
            title=_("Number of elements to show in Quicksearch"),
            help=_("When typing a texts in the Quicksearch snapin, a dropdown will "
                   "appear listing all matching host names containing that text. "
                   "That list is limited in size so that the dropdown will not get "
                   "too large when you have a huge number of lists. "),
            minvalue=1,
        )


@config_variable_registry.register
class ConfigVariableQuicksearchSearchOrder(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "quicksearch_search_order"

    def valuespec(self):
        return ListOf(
            Tuple(elements=[
                DropdownChoice(
                    title=_("Search filter"),
                    choices=[
                        ("h", _("Hostname")),
                        ("al", _("Hostalias")),
                        ("ad", _("Hostaddress")),
                        ("tg", _("Hosttag")),
                        ("hg", _("Hostgroup")),
                        ("sg", _("Servicegroup")),
                        ("s", _("Service Description")),
                    ],
                ),
                DropdownChoice(
                    title=_("Match behaviour"),
                    choices=[
                        ("continue", _("Continue search")),
                        ("finished",
                         _("Search finished: Also show all results of previous filters")),
                        ("finished_distinct",
                         _("Search finished: Only show results of this filter")),
                    ],
                ),
            ],),
            title=_("Quicksearch search order"),
            add_label=_("Add search filter"),
        )


@config_variable_registry.register
class ConfigVariableTableRowLimit(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "table_row_limit"

    def valuespec(self):
        return Integer(
            title=_("Limit the number of rows shown in tables"),
            help=_("Several pages which use tables to show data in rows, like the "
                   "\"Users\" configuration page, can be configured to show "
                   "only a limited number of rows when accessing the pages."),
            minvalue=1,
            unit=_('rows'),
        )


@config_variable_registry.register
class ConfigVariableStartURL(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "start_url"

    def valuespec(self):
        return TextAscii(
            title=_("Start URL to display in main frame"),
            help=_("When you point your browser to the Check_MK GUI, usually the dashboard "
                   "is shown in the main (right) frame. You can replace this with any other "
                   "URL you like here."),
            size=80,
            allow_empty=False,
            validate=utils.validate_start_url,
        )


@config_variable_registry.register
class ConfigVariablePageHeading(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "page_heading"

    def valuespec(self):
        return TextUnicode(
            title=_("Page title"),
            help=_("This title will be displayed in your browser's title bar or tab. You can use "
                   "a <tt>%s</tt> to insert the alias of your monitoring site to the title."),
            size=80,
        )


@config_variable_registry.register
class ConfigVariableBIDefaultLayout(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "default_bi_layout"

    def valuespec(self):
        return Dictionary(
            title=_("Default BI Visualization Settings"),
            elements=[
                ("node_style",
                 DropdownChoice(title=_("Default layout"),
                                help=_(
                                    "Specifies the default layout to be used when an aggregation "
                                    "has no explict layout assinged"),
                                choices=self.get_layout_style_choices())),
                ("line_style",
                 DropdownChoice(title=_("Default line style"),
                                help=_("Specifies the default line style"),
                                choices=self.get_line_style_choices())),
            ],
            optional_keys=[])

    @classmethod
    def get_layout_style_choices(cls):
        return [("builtin_force", _("Force layout")),
                ("builtin_hierarchy", _("Hierarchical layout")),
                ('builtin_radial', _("Radial layout"))]

    @classmethod
    def get_line_style_choices(cls):
        return [("round", _("Round")), ("straight", _("Straight")), ('elbow', _("Elbow"))]


@config_variable_registry.register
class ConfigVariablePagetitleDateFormat(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "pagetitle_date_format"

    def valuespec(self):
        return DropdownChoice(
            title=_("Date format for page titles"),
            help=_("When enabled, the headline of each page also displays "
                   "the date in addition the time."),
            choices=[
                (None, _("Do not display a date")),
                ('yyyy-mm-dd', _("YYYY-MM-DD")),
                ('dd.mm.yyyy', _("DD.MM.YYYY")),
            ],
        )


@config_variable_registry.register
class ConfigVariableEscapePluginOutput(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "escape_plugin_output"

    def valuespec(self):
        return Checkbox(
            title=_("Escape HTML codes in plugin output"),
            help=_("By default, for security reasons, the GUI does not interpret any HTML "
                   "code received from external sources, like plugin output or log messages. "
                   "If you are really sure what you are doing and need to have HTML codes, like "
                   "links rendered, disable this option. Be aware, you might open the way "
                   "for several injection attacks.") +
            _("This setting can either be set globally or individually for selected hosts "
              "or services using the host or service rulesets."),
            label=_("Prevent loading HTML from plugin output or log messages"),
        )


@config_variable_registry.register
class ConfigVariableCrashReportTarget(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "crash_report_target"

    def valuespec(self):
        return TextAscii(
            title=_("Fallback mail address for crash reports"),
            help=_("By default crash reports will be sent to our crash reporting server. In case "
                   "this fails for some reason, the crash reports can be sent by mail to the "
                   "address configured here."),
            size=80,
            attrencode=True,
        )


@config_variable_registry.register
class ConfigVariableDrawRuleIcon(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "multisite_draw_ruleicon"

    def valuespec(self):
        return Checkbox(
            title=_("Show icon linking to WATO parameter editor for services"),
            label=_("Show WATO icon"),
            help=_("When enabled a rule editor icon is displayed for each "
                   "service in the multisite views. It is only displayed if the user "
                   "does have the permission to edit rules."),
        )


def transform_virtual_host_trees(trees):
    def id_from_title(title):
        return re.sub("[^-a-zA-Z0-9_]+", "", title.lower())

    for index, tree in enumerate(trees):
        if isinstance(tree, tuple):
            trees[index] = {
                "id": id_from_title(tree[0]),
                "title": tree[0],
                "tree_spec": tree[1],
            }
        else:
            # Transform existing dicts with old key "tag_groups"
            if "tag_groups" in tree:
                tree["tree_spec"] = tree.pop("tag_groups")

    return sorted(trees, key=lambda x: x["title"])


@config_variable_registry.register
class ConfigVariableVirtualHostTrees(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "virtual_host_trees"

    def valuespec(self):
        return Transform(
            ListOf(
                Dictionary(
                    elements=[
                        ("id", ID(
                            title=_("ID"),
                            allow_empty=False,
                        )),
                        ("title", TextUnicode(
                            title=_("Title of the tree"),
                            allow_empty=False,
                        )),
                        ("exclude_empty_tag_choices",
                         Checkbox(
                             title=_("Exclude empty tag choices"),
                             default_value=False,
                         )),
                        ("tree_spec",
                         ListOf(
                             DropdownChoice(choices=self._virtual_host_tree_choices,),
                             title=_("Tree levels"),
                             allow_empty=False,
                             magic="#!#",
                         )),
                    ],
                    optional_keys=[],
                ),
                add_label=_("Create new virtual host tree configuration"),
                title=_("Virtual Host Trees"),
                help=
                _("Here you can define tree configurations for the snapin <i>Virtual Host-Trees</i>. "
                  "These trees organize your hosts based on their values in certain host tag groups. "
                  "Each host tag group you select will create one level in the tree."),
                validate=self._validate_virtual_host_trees,
                movable=False,
            ),
            forth=transform_virtual_host_trees,
        )

    def _virtual_host_tree_choices(self):
        return self._wato_host_tag_group_choices() + [("foldertree:", _("WATO folder tree"))] + [
            ("folder:%d" % l, _("WATO folder level %d") % l) for l in range(1, 7)
        ]

    def _wato_host_tag_group_choices(self):
        # We add to the choices:
        # 1. All host tag groups with their id
        # 2. All *topics* that:
        #  - consist only of checkbox tags
        #  - contain at least two entries
        choices = []
        by_topic = {}
        for tag_group in config.tags.tag_groups:
            choices.append((tag_group.id, tag_group.title))
            by_topic.setdefault(tag_group.topic, []).append(tag_group)

        # Now search for checkbox-only-topics
        for topic, tag_groups in by_topic.items():
            for tag_group in tag_groups:
                if len(tag_group.tags) != 1:
                    break
            else:
                if len(tag_groups) > 1:
                    choices.append((
                        "topic:" + topic,
                        _("Topic") + ": " + topic,
                    ))

        return choices

    def _validate_virtual_host_trees(self, value, varprefix):
        tree_ids = set()
        for tree in value:
            if tree["id"] in tree_ids:
                raise MKUserError(varprefix, _("The ID needs to be unique."))
            tree_ids.add(tree["id"])

            # Validate that each element is selected once
            seen = set()
            for element in tree["tree_spec"]:
                if element in seen:
                    raise MKUserError(
                        varprefix,
                        _("Found '%s' a second time in tree '%s'. Each element can only be "
                          "choosen once.") % (element, tree["id"]))

                seen.add(element)


@config_variable_registry.register
class ConfigVariableRescheduleTimeout(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "reschedule_timeout"

    def valuespec(self):
        return Float(
            title=_("Timeout for rescheduling checks in Multisite"),
            help=_("When you reschedule a check by clicking on the &quot;arrow&quot;-icon "
                   "then Multisite will use this number of seconds as a timeout. If the "
                   "monitoring core has not executed the check within this time, an error "
                   "will be displayed and the page not reloaded."),
            minvalue=1.0,
            unit="sec",
            display_format="%.1f",
        )


@config_variable_registry.register
class ConfigVariableSidebarShowVersionInSidebar(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "sidebar_show_version_in_sidebar"

    def valuespec(self):
        return Checkbox(
            title=_("Show Check_MK edition & version in sidebar"),
            label=_("Show the edition ad version"),
            help=_("Use this option to hide the Check_MK edition and version information from "
                   "the header of the sidebar."),
        )


@config_variable_registry.register
class ConfigVariableSidebarUpdateInterval(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "sidebar_update_interval"

    def valuespec(self):
        return Float(
            title=_("Interval of sidebar status updates"),
            help=_("The information provided by the sidebar snapins is refreshed in a regular "
                   "interval. You can change the refresh interval to fit your needs here. This "
                   "value means that all snapnis which request a regular refresh are updated "
                   "in this interval."),
            minvalue=10.0,
            unit="sec",
            display_format="%.1f",
        )


@config_variable_registry.register
class ConfigVariableSidebarNotifyInterval(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "sidebar_notify_interval"

    def valuespec(self):
        return Optional(
            Float(
                minvalue=10.0,
                unit="sec",
                display_format="%.1f",
            ),
            title=_("Interval of sidebar popup notification updates"),
            help=_(
                "The sidebar can be configured to regularly check for pending popup notififcations. "
                "This is disabled by default."),
            none_label=_('(disabled)'),
        )


@config_variable_registry.register
class ConfigVariableiAdHocDowntime(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "adhoc_downtime"

    def valuespec(self):
        return Optional(
            Dictionary(
                optional_keys=False,
                elements=[
                    ("duration",
                     Integer(
                         title=_("Duration"),
                         help=_("The duration in minutes of the adhoc downtime."),
                         minvalue=1,
                         unit=_("minutes"),
                         default_value=60,
                     )),
                    ("comment",
                     TextUnicode(
                         title=_("Adhoc comment"),
                         help=_("The comment which is automatically sent with an adhoc downtime"),
                         size=80,
                         allow_empty=False,
                         attrencode=True,
                     )),
                ],
            ),
            title=_("Adhoc downtime"),
            label=_("Enable adhoc downtime"),
            help=_("This setting allows to set an adhoc downtime comment and its duration. "
                   "When enabled a new button <i>Adhoc downtime for __ minutes</i> will "
                   "be available in the command form."),
        )


@config_variable_registry.register
class ConfigVariableAuthByHTTPHeader(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "auth_by_http_header"

    def valuespec(self):
        return Optional(
            TextAscii(
                label=_("HTTP request header variable"),
                help=_("Configure the name of the HTTP request header variable to read "
                       "from the incoming HTTP requests"),
                default_value="X-Remote-User",
                regex=re.compile('^[A-Za-z0-9-]+$'),
                regex_error=_("Only A-Z, a-z, 0-9 and minus (-) are allowed."),
                attrencode=True,
            ),
            title=_("Authenticate users by incoming HTTP requests"),
            label=_("Activate HTTP header authentication (Warning: Only activate "
                    "in trusted environments, see help for details)"),
            help=_("If this option is enabled, the GUI reads the configured HTTP header "
                   "variable from the incoming HTTP request and simply takes the string "
                   "in this variable as name of the authenticated user. "
                   "Be warned: Only allow access from trusted ip addresses "
                   "(Apache <tt>Allow from</tt>), like proxy "
                   "servers, to this webpage. A user with access to this page could simply fake "
                   "the authentication information. This option can be useful to "
                   "realize authentication in reverse proxy environments. As of version 1.6 and "
                   "on all platforms using Apache 2.4+ only A-Z, a-z, 0-9 and minus (-) are "
                   "to be used for the variable name."),
            none_value=False,
            none_label=_("Don't use HTTP header authentication"),
            indent=False,
        )


@config_variable_registry.register
class ConfigVariableStalenessThreshold(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "staleness_threshold"

    def valuespec(self):
        return Float(
            title=_('Staleness value to mark hosts / services stale'),
            help=_(
                'The staleness value of a host / service is calculated by measuring the '
                'configured check intervals a check result is old. A value of 1.5 means the '
                'current check result has been gathered one and a half check intervals of an object. '
                'This would mean 90 seconds in case of a check which is checked each 60 seconds.'),
            minvalue=1,
        )


@config_variable_registry.register
class ConfigVariableLoginScreen(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "login_screen"

    def valuespec(self):
        return Dictionary(
            title=_("Customize login screen"),
            elements=[
                ("hide_version",
                 FixedValue(
                     True,
                     title=_("Hide Check_MK version"),
                     totext=_("Hide the Check_MK version from the login box"),
                 )),
                ("login_message",
                 TextUnicode(
                     title=_("Show a login message"),
                     help=
                     _("You may use this option to give your users an informational text before logging in."
                      ),
                     size=80,
                 )),
                ("footer_links",
                 ListOf(
                     Tuple(
                         elements=[
                             TextUnicode(title=_("Title"),),
                             TextAscii(
                                 title=_('URL'),
                                 size=80,
                             ),
                             DropdownChoice(
                                 title=_("Open in"),
                                 choices=[
                                     ("_blank", _("Load in a new window / tab")),
                                     ("_top", _("Load in current window / tab")),
                                 ],
                             ),
                         ],
                         orientation="horizontal",
                     ),
                     totext=_("%d links"),
                     title=_("Custom footer links"),
                 )),
            ],
            required_keys=[],
        )


@config_variable_registry.register
class ConfigVariableUserLocalizations(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "user_localizations"

    def valuespec(self):
        return Transform(
            ListOf(
                Tuple(elements=[
                    TextUnicode(title=_("Original Text"), size=40),
                    Dictionary(
                        title=_("Translations"),
                        elements=lambda: [(l or "en", TextUnicode(title=a, size=32))
                                          for (l, a) in cmk.gui.i18n.get_languages()],
                        columns=2,
                    ),
                ],),
                title=_("Custom localizations"),
                movable=False,
                totext=_("%d translations"),
            ),
            forth=lambda d: sorted(d.items()),
            back=dict,
        )


@config_variable_registry.register
class ConfigVariableUserIconsAndActions(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "user_icons_and_actions"

    def valuespec(self):
        return Transform(
            ListOf(
                Tuple(elements=[
                    ID(title=_("ID")),
                    Dictionary(
                        elements=[
                            ('icon', IconSelector(
                                title=_('Icon'),
                                allow_empty=False,
                            )),
                            ('title', TextUnicode(title=_('Title'),)),
                            ('url',
                             Transform(
                                 Tuple(
                                     title=_('Action'),
                                     elements=[
                                         TextAscii(
                                             title=_('URL'),
                                             help=
                                             _('This URL is opened when clicking on the action / icon. You '
                                               'can use some macros within the URL which are dynamically '
                                               'replaced for each object. These are:<br>'
                                               '<ul>'
                                               '<li>$HOSTNAME$: Contains the name of the host</li>'
                                               '<li>$HOSTNAME_URL_ENCODED$: Same as above but URL encoded</li>'
                                               '<li>$SERVICEDESC$: Contains the service description '
                                               '(in case this is a service)</li>'
                                               '<li>$SERVICEDESC_URL_ENCODED$: Same as above but URL encoded</li>'
                                               '<li>$HOSTADDRESS$: Contains the network address of the host</li>'
                                               '<li>$HOSTADDRESS_URL_ENCODED$: Same as above but URL encoded</li>'
                                               '<li>$USER_ID$: The user ID of the currently active user</li>'
                                               '</ul>'),
                                             size=80,
                                         ),
                                         DropdownChoice(
                                             title=_("Open in"),
                                             choices=[
                                                 ("_blank", _("Load in a new window / tab")),
                                                 ("_self",
                                                  _("Load in current content area (keep sidebar)")),
                                                 ("_top", _("Load as new page (hide sidebar)")),
                                             ],
                                         ),
                                     ],
                                 ),
                                 forth=lambda x: not isinstance(x, tuple) and (x, "_self") or x,
                             )),
                            ('toplevel',
                             FixedValue(
                                 True,
                                 title=_('Show in column'),
                                 totext=_('Directly show the action icon in the column'),
                                 help=_('Makes the icon appear in the column instead '
                                        'of the dropdown menu.'),
                             )),
                            ('sort_index',
                             Integer(
                                 title=_('Sort index'),
                                 help=_(
                                     'You can use the sort index to control the order of the '
                                     'elements in the column and the menu. The elements are sorted '
                                     'from smaller to higher numbers. The action menu icon '
                                     'has a sort index of <tt>10</tt>, the graph icon a sort index '
                                     'of <tt>20</tt>. All other default icons have a sort index of '
                                     '<tt>30</tt> configured.'),
                                 min_value=0,
                                 default_value=15,
                             )),
                        ],
                        optional_keys=['title', 'url', 'toplevel', 'sort_index'],
                    ),
                ],),
                title=_("Custom icons and actions"),
                movable=False,
                totext=_("%d icons and actions"),
            ),
            forth=lambda d: sorted(d.items()),
            back=dict,
        )


@config_variable_registry.register
class ConfigVariableCustomServiceAttributes(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "custom_service_attributes"

    def valuespec(self):
        return Transform(
            ListOf(
                Dictionary(
                    elements=[
                        ("ident",
                         TextAscii(
                             title=_("ID"),
                             help=_("The ID will be used as internal identifier and the custom "
                                    "service attribute will be computed based on the ID. The "
                                    "custom service attribute will be named <tt>_[ID]</tt> in "
                                    "the core configuration and can be gathered using the "
                                    "Livestatus column <tt>custom_variables</tt> using the "
                                    "<tt>[ID]</tt>. The custom service attributes are available "
                                    "to notification scripts as environment variable named "
                                    "<tt>SERVICE_[ID]</tt>."),
                             validate=self._validate_id,
                             regex=re.compile('^[A-Z_][-A-Z0-9_]*$'),
                             regex_error=_(
                                 "An identifier must only consist of letters, digits, dash and "
                                 "underscore and it must start with a letter or underscore.") +
                             " " + _("Only upper case letters are allowed"))),
                        ('title', TextUnicode(title=_('Title'),)),
                        ("type",
                         DropdownChoice(
                             title=_("Data type"),
                             choices=[
                                 ('TextAscii', _('Simple Text')),
                             ],
                         )),
                    ],
                    optional_keys=[],
                ),
                title=_("Custom service attributes"),
                help=_("These custom service attributes can be assigned to services "
                       "using the ruleset <a href=\"%s\">%s</a>.") %
                ("wato.py?mode=edit_ruleset&varname=custom_service_attributes",
                 _("Custom service attributes")),
                movable=False,
                totext=_("%d custom service attributes"),
                allow_empty=False,
                # Unique IDs are ensured by the transform below. The Transform is executed
                # before the validation function has the chance to validate it and print a
                # custom error message.
                validate=self._validate_unique_entries,
            ),
            forth=lambda v: v.values(),
            back=lambda v: {p["ident"]: p for p in v},
        )

    def _validate_id(self, value, varprefix):
        internal_ids = [
            "ESCAPE_PLUGIN_OUTPUT",
            "EC_SL",
            "EC_CONTACT",
            "SERVICE_PERIOD",
            "ACTIONS",
        ]
        if value.upper() in internal_ids:
            raise MKUserError(varprefix, _("This ID can not be used as custom attribute"))

    def _validate_unique_entries(self, value, varprefix):
        seen_titles = []
        for entry in value:
            if entry["title"] in seen_titles:
                raise MKUserError(varprefix,
                                  _("Found multiple entries using the title '%s'") % entry["title"])
            seen_titles.append(entry["title"])


@rulespec_group_registry.register
class RulespecGroupMonitoringConfiguration(RulespecGroup):
    @property
    def name(self):
        return "monconf"

    @property
    def title(self):
        return _("Monitoring Configuration")

    @property
    def help(self):
        return _(
            "Intervals for checking, retries, clustering, configuration for inventory and similar")


@rulespec_group_registry.register
class RulespecGroupMonitoringConfigurationServiceChecks(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "service_checks"

    @property
    def title(self):
        return _("Service Checks")


def _custom_service_attributes_validate_unique_entries(value, varprefix):
    seen_ids = []
    for entry in value:
        if entry[0] in seen_ids:
            raise MKUserError(varprefix, _("Found multiple entries using for '%s'") % entry[0])
        seen_ids.append(entry[0])


def _custom_service_attributes_custom_service_attribute_choices():
    choices = []
    for ident, attr_spec in config.custom_service_attributes.items():
        if attr_spec["type"] == "TextAscii":
            vs = TextAscii()
        else:
            raise NotImplementedError()
        choices.append((ident, attr_spec["title"], vs))
    return sorted(choices, key=lambda x: x[1])


def _valuespec_custom_service_attributes():
    return ListOf(
        CascadingDropdown(
            choices=_custom_service_attributes_custom_service_attribute_choices(),
            orientation="horizontal",
        ),
        title=_("Custom service attributes"),
        help=_("Use this ruleset to assign <a href=\"%s\">%s</a> to services.") %
        ("wato.py?mode=edit_configvar&varname=custom_service_attributes",
         _("Custom service attributes")),
        allow_empty=False,
        validate=_custom_service_attributes_validate_unique_entries,
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationServiceChecks,
        item_type="service",
        match_type="all",
        name="custom_service_attributes",
        valuespec=_valuespec_custom_service_attributes,
    ))


def _service_tag_rules_validate_unique_entries(value, varprefix):
    seen_ids = []
    for entry in value:
        if entry[0] in seen_ids:
            raise MKUserError(varprefix, _("Found multiple entries using for '%s'") % entry[0])
        seen_ids.append(entry[0])


def _service_tag_rules_tag_group_choices():
    choices = []
    for tag_group in config.tags.tag_groups:
        choices.append(
            (tag_group.id, tag_group.title, DropdownChoice(choices=tag_group.get_tag_choices(),)))
    return sorted(choices, key=lambda x: x[1])


def _valuespec_service_tag_rules():
    return ListOf(
        CascadingDropdown(
            choices=_service_tag_rules_tag_group_choices(),
            orientation="horizontal",
        ),
        title=_("Service tags"),
        help=_("Use this ruleset to assign <a href=\"%s\">%s</a> to services.") %
        ("wato.py?mode=tags", _("Tags")),
        allow_empty=False,
        validate=_service_tag_rules_validate_unique_entries,
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationServiceChecks,
        item_type="service",
        match_type="all",
        name="service_tag_rules",
        valuespec=_valuespec_service_tag_rules,
    ))


def _valuespec_service_label_rules():
    return Labels(
        world=Labels.World.CONFIG,
        label_source=Labels.Source.RULESET,
        title=_("Service labels"),
        help=_("Use this ruleset to assign labels to service of your choice."),
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationServiceChecks,
        item_type="service",
        match_type="dict",
        name="service_label_rules",
        valuespec=_valuespec_service_label_rules,
    ))


@rulespec_group_registry.register
class RulespecGroupMonitoringConfigurationHostChecks(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "host_checks"

    @property
    def title(self):
        return _("Host Checks")


def _valuespec_host_label_rules():
    return Labels(
        world=Labels.World.CONFIG,
        label_source=Labels.Source.RULESET,
        title=_("Host labels"),
        help=_("Use this ruleset to assign labels to hosts of your choice."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationHostChecks,
        match_type="dict",
        name="host_label_rules",
        valuespec=_valuespec_host_label_rules,
    ))


@config_variable_registry.register
class ConfigVariableUserDowntimeTimeranges(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "user_downtime_timeranges"

    def valuespec(self):
        return ListOf(
            Dictionary(
                elements=[('title', TextUnicode(title=_('Title'),)),
                          ('end',
                           Alternative(
                               title=_("To"),
                               elements=[
                                   Age(
                                       title=_("Duration"),
                                       display=["minutes", "hours", "days"],
                                   ),
                                   DropdownChoice(
                                       title=_("Until"),
                                       choices=[
                                           ('next_day', _("Start of next day")),
                                           ('next_week', _("Start of next week")),
                                           ('next_month', _("Start of next month")),
                                           ('next_year', _("Start of next year")),
                                       ],
                                       default_value="next_day",
                                   )
                               ],
                               style="dropdown",
                               default_value=24 * 60 * 60,
                           ))],
                optional_keys=[],
            ),
            title=_("Custom Downtime Timeranges"),
            movable=True,
            totext=_("%d timeranges"),
        )


@config_variable_registry.register
class ConfigVariableBuiltinIconVisibility(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "builtin_icon_visibility"

    def valuespec(self):
        return Transform(
            ListOf(
                Tuple(elements=[
                    DropdownChoice(
                        title=_("Icon"),
                        choices=self._get_builtin_icons,
                        sorted=True,
                    ),
                    Dictionary(
                        elements=[
                            ('toplevel',
                             Checkbox(
                                 title=_('Show in column'),
                                 label=_('Directly show the action icon in the column'),
                                 help=_('Makes the icon appear in the column instead '
                                        'of the dropdown menu.'),
                                 default_value=True,
                             )),
                            ('sort_index',
                             Integer(
                                 title=_('Sort index'),
                                 help=_(
                                     'You can use the sort index to control the order of the '
                                     'elements in the column and the menu. The elements are sorted '
                                     'from smaller to higher numbers. The action menu icon '
                                     'has a sort index of <tt>10</tt>, the graph icon a sort index '
                                     'of <tt>20</tt>. All other default icons have a sort index of '
                                     '<tt>30</tt> configured.'),
                                 min_value=0,
                             )),
                        ],
                        optional_keys=['toplevel', 'sort_index'],
                    ),
                ],),
                title=_("Builtin icon visibility"),
                movable=False,
                totext=_("%d icons customized"),
                help=_("You can use this option to change the default visibility "
                       "options of the builtin icons. You can change whether or not "
                       "the icons are shown in the popup menu or on top level and "
                       "change the sorting of the icons."),
            ),
            forth=lambda d: sorted(d.items()),
            back=dict,
        )

    def _get_builtin_icons(self):
        return [(id_, id_) for id_ in icon_and_action_registry.keys()]


@config_variable_registry.register
class ConfigVariableServiceViewGrouping(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "service_view_grouping"

    def valuespec(self):
        return ListOf(
            Dictionary(
                elements=[
                    ('title', TextUnicode(title=_('Title to show for the group'),)),
                    ('pattern',
                     RegExpUnicode(
                         title=_('Grouping expression'),
                         help=_('This regular expression is used to match the services to be put '
                                'into this group. This is a prefix match regular expression.'),
                         mode=RegExpUnicode.prefix,
                     )),
                    ('min_items',
                     Integer(
                         title=_('Minimum number of items to create a group'),
                         help=_('When less than these items are found for a group, the services '
                                'are not shown grouped together.'),
                         min_value=2,
                         default_value=2,
                     )),
                ],
                optional_keys=[],
            ),
            title=_("Grouping of services in table views"),
            help=_(
                "You can use this option to make the service table views fold services matching "
                "the given patterns into groups. Only services in state <i>OK</i> will be folded "
                "together. Groups of only one service will not be rendered. If multiple patterns "
                "match a service, the service will be added to the first matching group."),
            add_label=_("Add new grouping definition"),
        )


@config_variable_registry.register
class ConfigVariableTopologyDefaultFilterGroup(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "topology_default_filter_group"

    def valuespec(self):
        return Optional(
            DropdownChoice(
                choices=lambda: sites.all_groups("host"),
                sorted=True,
            ),
            title=_("Network Topology: Default Filter Group"),
            help=_(
                "By default the network topology view shows you the parent / child relations "
                "of all hosts within your local site. The list can be filtered based on hostgroup "
                "memberships by the users. You can define a default group to use for filtering "
                "which is used when a user opens the network topology view."),
            none_label=_("Show all hosts when opening the network topology view"),
        )


@config_variable_registry.register
class ConfigVariableViewActionDefaults(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "view_action_defaults"

    def valuespec(self):
        return Dictionary(
            title=_("View action defaults"),
            elements=[
                ("ack_sticky", Checkbox(
                    title=_("Sticky"),
                    label=_("Enable"),
                    default_value=True,
                )),
                ("ack_notify",
                 Checkbox(
                     title=_("Send notification"),
                     label=_("Enable"),
                     default_value=True,
                 )),
                ("ack_persistent",
                 Checkbox(
                     title=_("Persistent comment"),
                     label=_("Enable"),
                     default_value=False,
                 )),
                ("ack_expire",
                 Age(
                     title=_("Expire acknowledgement after"),
                     display=["days", "hours", "minutes"],
                     default_value=0,
                 )),
            ],
            optional_keys=[],
        )


@config_variable_registry.register
class ConfigVariableTrustedCertificateAuthorities(ConfigVariable):
    def group(self):
        return ConfigVariableGroupSiteManagement

    def domain(self):
        return ConfigDomainCACertificates

    def ident(self):
        return "trusted_certificate_authorities"

    def valuespec(self):
        return Dictionary(
            title=_("Trusted certificate authorities for SSL"),
            help=_("Whenever a server component of Check_MK opens a SSL connection it uses the "
                   "certificate authorities configured here for verifying the SSL certificate of "
                   "the destination server. This is used for example when performing WATO "
                   "replication to slave sites or when special agents are communicating via HTTPS. "
                   "The CA certificates configured here will be written to the CA bundle %s.") %
            site_neutral_path(ConfigDomainCACertificates.trusted_cas_file),
            elements=[
                ("use_system_wide_cas",
                 Checkbox(
                     title=_("Use system wide CAs"),
                     help=_("All supported linux distributions provide a mechanism of managing "
                            "trusted CAs. Depending on your linux distributions the paths where "
                            "these CAs are stored and the commands to manage the CAs differ. "
                            "Please checko out the documentation of your linux distribution "
                            "in case you want to customize trusted CAs system wide. You can "
                            "choose here to trust the system wide CAs here. Check_MK will search "
                            "these directories for system wide CAs: %s") %
                     ", ".join(ConfigDomainCACertificates.system_wide_trusted_ca_search_paths),
                     label=_("Trust system wide configured CAs"),
                 )),
                ("trusted_cas", ListOfCAs(
                    title=_("Check_MK specific"),
                    allow_empty=True,
                )),
            ],
            optional_keys=False,
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


@config_variable_group_registry.register
class ConfigVariableGroupWATO(ConfigVariableGroup):
    def title(self):
        return _("Administration Tool (WATO)")

    def sort_index(self):
        return 25


@config_variable_registry.register
class ConfigVariableWATOMaxSnapshots(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_max_snapshots"

    def valuespec(self):
        return Integer(
            title=_("Number of configuration snapshots to keep"),
            help=_("Whenever you successfully activate changes a snapshot of the configuration "
                   "will be created. You can also create snapshots manually. WATO will delete old "
                   "snapshots when the maximum number of snapshots is reached."),
            minvalue=1,
        )


@config_variable_registry.register
class ConfigVariableWATOActivationMethod(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_activation_method"

    def valuespec(self):
        return DropdownChoice(
            title=_("WATO restart mode for Nagios"),
            help=_("Should WATO restart or reload Nagios when activating changes"),
            choices=[
                ('restart', _("Restart")),
                ('reload', _("Reload")),
            ],
        )


@config_variable_registry.register
class ConfigVariableWATOLegacyEval(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_legacy_eval"

    def valuespec(self):
        return Checkbox(
            title=_("Use unsafe legacy encoding for distributed WATO"),
            help=
            _("The current implementation of WATO uses a Python module called <tt>ast</tt> for the "
              "communication between sites. Previous versions of Check_MK used an insecure encoding "
              "named <tt>pickle</tt>. Even in the current version WATO falls back to <tt>pickle</tt> "
              "if your Python version is not recent enough. This is at least the case for RedHat/CentOS 5.X "
              "and Debian 5.0. In a mixed environment you can force using the legacy <tt>pickle</tt> format "
              "in order to create compatibility."),
        )


@config_variable_registry.register
class ConfigVariableWATOHideFilenames(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_hide_filenames"

    def valuespec(self):
        return Checkbox(
            title=_("Hide internal folder names in WATO"),
            label=_("hide folder names"),
            help=_("When enabled, then the internal names of WATO folder in the filesystem "
                   "are not shown. They will automatically be derived from the name of the folder "
                   "when a new folder is being created. Disable this option if you want to see and "
                   "set the filenames manually."),
        )


@config_variable_registry.register
class ConfigVariableWATOUploadInsecureSnapshots(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_upload_insecure_snapshots"

    def valuespec(self):
        return Checkbox(
            title=_("Allow upload of insecure WATO snapshots"),
            label=_("upload insecure snapshots"),
            help=
            _("When enabled, insecure snapshots are allowed. Please keep in mind that the upload "
              "of unverified snapshots represents a security risk, since the content of a snapshot is executed "
              "during runtime. Any manipulations in the content - either willingly or unwillingly (XSS attack) "
              "- pose a serious security risk."),
        )


@config_variable_registry.register
class ConfigVariableWATOHideHosttags(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_hide_hosttags"

    def valuespec(self):
        return Checkbox(
            title=_("Hide hosttags in WATO folder view"),
            label=_("hide hosttags"),
            help=_("When enabled, hosttags are no longer shown within the WATO folder view"),
        )


@config_variable_registry.register
class ConfigVariableWATOHideVarnames(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_hide_varnames"

    def valuespec(self):
        return Checkbox(
            title=_("Hide names of configuration variables"),
            label=_("hide variable names"),
            help=_("When enabled, internal configuration variable names of Check_MK are hidden "
                   "from the user (for example in the rule editor)"),
        )


@config_variable_registry.register
class ConfigVariableHideHelpInLists(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_hide_help_in_lists"

    def valuespec(self):
        return Checkbox(
            title=_("Hide help text of rules in list views"),
            label=_("hide help text"),
            help=_("When disabled, WATO shows the help texts of rules also in the list views."),
        )


@config_variable_registry.register
class ConfigVariableWATOUseGit(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_use_git"

    def valuespec(self):
        return Checkbox(
            title=_("Use GIT version control for WATO"),
            label=_("enable GIT version control"),
            help=_(
                "When enabled, all changes of configuration files are tracked with the "
                "version control system GIT. You need to make sure that git is installed "
                "on your monitoring server. The version history currently cannot be viewed "
                "via the web GUI. Please use git command line tools within your Check_MK "
                "configuration directory. If you want easier tracking of configuration file changes "
                "simply enable the global settings option <tt>Pretty print configuration files</tt>"
            ),
        )


@config_variable_registry.register
class ConfigVariableWATOPrettyPrintConfig(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_pprint_config"

    def valuespec(self):
        return Checkbox(
            title=_("Pretty-Print configuration files"),
            label=_("pretty-print configuration files"),
            help=
            _("When enabled, most of the configuration files are pretty printed and easier to read. "
              "On the downside, however, pretty printing bigger configurations can be quite slow - "
              "so the overall WATO GUI performance will decrease."),
        )


@config_variable_registry.register
class ConfigVariableWATOHideFoldersWithoutReadPermissions(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_hide_folders_without_read_permissions"

    def valuespec(self):
        return Checkbox(
            title=_("Hide folders without read permissions"),
            label=_("hide folders without read permissions"),
            help=_(
                "When enabled, a subfolder is not shown, when the user does not have sufficient "
                "permissions to this folder and all of its subfolders. However, the subfolder is "
                "shown if the user has permissions to any of its subfolder."),
        )


@config_variable_registry.register
class ConfigVariableWATOIconCategories(ConfigVariable):
    def group(self):
        return ConfigVariableGroupWATO

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "wato_icon_categories"

    def valuespec(self):
        return ListOf(
            Tuple(
                elements=[
                    ID(title=_("ID"),),
                    TextUnicode(title=_("Title"),),
                ],
                orientation="horizontal",
            ),
            title=_("Icon categories"),
            help=_("You can customize the list of icon categories to be able to assign "
                   "your <a href=\"?mode=icons\">custom icons</a> to these categories. "
                   "They will then be shown under this category in the icon selector."),
        )


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


@config_variable_group_registry.register
class ConfigVariableGroupUserManagement(ConfigVariableGroup):
    def title(self):
        return _("User Management")

    def sort_index(self):
        return 40


@config_variable_registry.register
class ConfigVariableLockOnLogonFailures(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserManagement

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "lock_on_logon_failures"

    def valuespec(self):
        return Optional(
            Integer(
                label=_("Number of logon failures to lock the account"),
                default_value=3,
                minvalue=1,
            ),
            none_value=False,
            title=_("Lock user accounts after N logon failures"),
            label=_("Activate automatic locking of user accounts"),
            help=_("This options enables automatic locking of user accounts after "
                   "the configured number of consecutive invalid login attempts. "
                   "Once the account is locked only an admin user can unlock it. "
                   "Beware: Also the admin users will be locked that way. You need "
                   "to manually edit <tt>etc/htpasswd</tt> and remove the <tt>!</tt> "
                   "in case you are locked out completely."),
        )


@config_variable_registry.register
class ConfigVariablePasswordPolicy(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserManagement

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "password_policy"

    def valuespec(self):
        return Dictionary(
            title=_('Password policy for local accounts'),
            help=_(
                'You can define some rules to which each user password ahers. By default '
                'all passwords are accepted, even ones which are made of only a single character, '
                'which is obviously a bad idea. Using this option you can enforce your users '
                'to choose more secure passwords.'),
            elements=[
                ('min_length', Integer(
                    title=_("Minimum password length"),
                    minvalue=1,
                )),
                ('num_groups',
                 Integer(
                     title=_("Number of character groups to use"),
                     minvalue=1,
                     maxvalue=4,
                     help=_(
                         "Force the user to choose a password that contains characters from at least "
                         "this number of different character groups. "
                         "Character groups are: <ul>"
                         "<li>lowercase letters</li>"
                         "<li>uppercase letters</li>"
                         "<li>digits</li>"
                         "<li>special characters such as an underscore or dash</li>"
                         "</ul>"),
                 )),
                ('max_age',
                 Age(
                     title=_("Maximum age of passwords"),
                     minvalue=1,
                     display=["days"],
                     default_value=365 * 86400,
                 )),
            ],
        )


@config_variable_registry.register
class ConfigVariableUserIdleTimeout(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserManagement

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "user_idle_timeout"

    def valuespec(self):
        return Optional(
            Age(
                title=None,
                display=["minutes", "hours", "days"],
                minvalue=60,
                default_value=3600,
            ),
            title=_("Login session idle timeout"),
            label=_("Enable a login session idle timeout"),
            help=_("Normally a user login session is valid until the password is changed or "
                   "the user is locked. By enabling this option, you can apply a time limit "
                   "to login sessions which is applied when the user stops interacting with "
                   "the GUI for a given amount of time. When a user is exceeding the configured "
                   "maximum idle time, the user will be logged out and redirected to the login "
                   "screen to renew the login session. This setting can be overriden for each "
                   "user individually in the profile of the users."),
        )


@config_variable_registry.register
class ConfigVariableSingleUserSession(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserManagement

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "single_user_session"

    def valuespec(self):
        return Optional(
            Age(
                title=None,
                display=["minutes", "hours"],
                label=_("Session timeout:"),
                minvalue=30,
                default_value=60,
            ),
            title=_("Limit login to single session at a time"),
            label=_("Users can only login from one client at a time"),
            help=_("Normally a user can login to the GUI from unlimited number of clients at "
                   "the same time. If you want to enforce your users to be able to login only once "
                   " (from one client which means device and browser), you can enable this option. "
                   "When the user logs out or is inactive for the configured amount of time, the "
                   "session is invalidated automatically and the user has to log in again from the "
                   "current or another device."),
        )


@config_variable_registry.register
class ConfigVariableDefaultUserProfile(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserManagement

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "default_user_profile"

    def valuespec(self):
        return Dictionary(
            title=_("Default user profile"),
            help=_(
                "With this option you can specify the attributes a user which is created during "
                "its initial login gets added. For example, the default is to add the role \"user\" "
                "to all automatically created users."),
            elements=self._default_user_profile_elements,
            optional_keys=[],
        )

    def _default_user_profile_elements(self):
        elements = []

        if cmk.is_managed_edition():
            import cmk.gui.cme.managed as managed
            elements += managed.customer_choice_element()

        return elements + [
            ('roles',
             ListChoice(
                 title=_('User roles'),
                 help=_('Specify the initial roles of an automatically created user.'),
                 default_value=['user'],
                 choices=self._list_roles,
             )),
            ('contactgroups',
             ListChoice(
                 title=_('Contact groups'),
                 help=_('Specify the initial contact groups of an automatically created user.'),
                 default_value=[],
                 choices=self._list_contactgroups,
             )),
            ("force_authuser",
             Checkbox(
                 title=_("Visibility of Hosts/Services"),
                 label=_("Only show hosts and services the user is a contact for"),
                 help=_("Specifiy the initial setting for an automatically created user."),
                 default_value=False,
             ))
        ]

    def _list_roles(self):
        roles = userdb.load_roles()
        return [(i, r["alias"]) for i, r in roles.items()]

    def _list_contactgroups(self):
        contact_groups = load_contact_group_information()
        entries = [(c, g['alias']) for c, g in contact_groups.items()]
        return sorted(entries)


@config_variable_registry.register
class ConfigVariableSaveUserAccessTimes(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserManagement

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "save_user_access_times"

    def valuespec(self):
        return Checkbox(
            title=_("Save last access times of users"),
            label=_("Save the time of the latest user activity"),
            help=_("When enabled, the time of the last access is stored for each user. The last "
                   "activity is shown on the users page."),
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


@config_variable_group_registry.register
class ConfigVariableGroupCheckExecution(ConfigVariableGroup):
    def title(self):
        return _("Execution of checks")

    def sort_index(self):
        return 10


@config_variable_registry.register
class ConfigVariableUseNewDescriptionsFor(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "use_new_descriptions_for"

    def valuespec(self):
        return ListChoice(
            title=_("Use new service descriptions"),
            help=_(
                "In order to make Check_MK more consistent, "
                "the descriptions of several services have been renamed in newer "
                "Check_MK versions. One example is the filesystem services that have "
                "been renamed from <tt>fs_</tt> into <tt>Filesystem</tt>. But since renaming "
                "of existing services has many implications - including existing rules, performance "
                "data and availability history - these renamings are disabled per default for "
                "existing installations. Here you can switch to the new descriptions for "
                "selected check types"),
            choices=[
                ("df", _("Used space in filesystems")),
                ("df_netapp", _("NetApp Filers: Used Space in Filesystems")),
                ("df_netapp32", _("NetApp Filers: Used space in Filesystem Using 32-Bit Counters")),
                ("esx_vsphere_datastores", _("VMWare ESX host systems: Used space")),
                ("hr_fs", _("Used space in filesystems via SNMP")),
                ("vms_diskstat.df", _("Disk space on OpenVMS")),
                ("zfsget", _("Used space in ZFS pools and filesystems")),
                ("ps", _("State and Count of Processes")),
                ("ps.perf", _("State and Count of Processes (with additional performance data)")),
                ("wmic_process", _("Resource consumption of windows processes")),
                ("services", _("Windows Services")),
                ("logwatch", _("Check logfiles for relevant new messages")),
                ("logwatch.groups", _("Check logfile groups")),
                ("cmk-inventory", _("Monitor hosts for unchecked services (Check_MK Discovery)")),
                ("hyperv_vms", _("Hyper-V Server: State of VMs")),
                ("ibm_svc_mdiskgrp",
                 _("IBM SVC / Storwize V3700 / V7000: Status and Usage of MDisksGrps")),
                ("ibm_svc_system", _("IBM SVC / V7000: System Info")),
                ("ibm_svc_systemstats.diskio",
                 _("IBM SVC / V7000: Disk Throughput for Drives/MDisks/VDisks in Total")),
                ("ibm_svc_systemstats.iops",
                 _("IBM SVC / V7000: IO operations/sec for Drives/MDisks/VDisks in Total")),
                ("ibm_svc_systemstats.disk_latency",
                 _("IBM SVC / V7000: Latency for Drives/MDisks/VDisks in Total")),
                ("ibm_svc_systemstats.cache", _("IBM SVC / V7000: Cache Usage in Total")),
                ("casa_cpu_temp", _("Casa module: CPU temperature")),
                ("cmciii.temp", _("Rittal CMC-III Units: Temperatures")),
                ("cmciii.psm_current", _("Rittal CMC-III Units: Current")),
                ("cmciii_lcp_airin", _("Rittal CMC-III LCP: Air In and Temperature")),
                ("cmciii_lcp_airout", _("Rittal CMC-III LCP: Air Out Temperature")),
                ("cmciii_lcp_water", _("Rittal CMC-III LCP: Water In/Out Temperature")),
                ("etherbox.temp", _("Etherbox / MessPC: Sensor Temperature")),
                ("liebert_bat_temp", _("Liebert UPS Device: Temperature sensor")),
                ("nvidia.temp", _("Temperatures of NVIDIA graphics card")),
                ("ups_bat_temp", _("Generic UPS Device: Temperature sensor")),
                ("innovaphone_temp", _("Innovaphone Gateway: Current Temperature")),
                ("enterasys_temp", _("Enterasys Switch: Temperature")),
                ("raritan_emx", _("Raritan EMX Rack: Temperature")),
                ("raritan_pdu_inlet", _("Raritan PDU: Input Phases")),
                ("mknotifyd", _("Notification Spooler")),
                ("mknotifyd.connection", _("Notification Spooler Connection")),
                ("postfix_mailq", _("Postfix: Mail Queue")),
                ("nullmailer_mailq", _("Nullmailer: Mail Queue")),
                ("barracuda_mailqueues", _("Barracuda: Mail Queue")),
                ("qmail_stats", _("Qmail: Mail Queue")),
                ("http", _("Check HTTP: Use HTTPS instead of HTTP for SSL/TLS connections")),
                ("mssql_backup", _("MSSQL Backup")),
                ("mssql_counters.cache_hits", _("MSSQL Cache Hits")),
                ("mssql_counters.transactions", _("MSSQL Transactions")),
                ("mssql_counters.locks", _("MSSQL Locks")),
                ("mssql_counters.sqlstats", _("MSSQL SQL Stats")),
                ("mssql_counters.pageactivity", _("MSSQL Page Activity")),
                ("mssql_counters.locks_per_batch", _("MSSQL Locks per Batch")),
                ("mssql_counters.file_sizes", _("MSSQL File Sizes")),
                ("mssql_databases", _("MSSQL Database")),
                ("mssql_datafiles", _("MSSQL Datafile")),
                ("mssql_tablespaces", _("MSSQL Tablespace")),
                ("mssql_transactionlogs", _("MSSQL Transactionlog")),
                ("mssql_versions", _("MSSQL Version")),
                ("mssql_blocked_sessions", _("MSSQL Blocked Sessions")),
            ],
            render_orientation="vertical",
        )


@config_variable_registry.register
class ConfigVariableTCPConnectTimeout(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "tcp_connect_timeout"

    def valuespec(self):
        return Float(
            title=_("Agent TCP connect timeout"),
            help=_(
                "Timeout for TCP connect to agent in seconds. If the connection "
                "to the agent cannot be established within this time, it is considered to be unreachable. "
                "Note: This does <b>not</b> limit the time the agent needs to "
                "generate its output."),
            minvalue=1.0,
            unit="sec",
        )


@config_variable_registry.register
class ConfigVariableSimulationMode(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "simulation_mode"

    def valuespec(self):
        return Checkbox(
            title=_("Simulation mode"),
            label=_("Run in simulation mode"),
            help=_("This boolean variable allows you to bring check_mk into a dry run mode. "
                   "No hosts will be contacted, no DNS lookups will take place and data is read "
                   "from cache files that have been created during normal operation or have "
                   "been copied here from another monitoring site."),
        )


@config_variable_registry.register
class ConfigVariableRestartLocking(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "restart_locking"

    def valuespec(self):
        return DropdownChoice(
            title=_("Simultanous activation of changes"),
            help=_("When two users simultanously try to activate the changes then "
                   "you can decide to abort with an error (default) or have the requests "
                   "serialized. It is also possible - but not recommended - to turn "
                   "off locking altogether."),
            choices=[
                ('abort', _("Abort with an error")),
                ('wait', _("Wait until the other has finished")),
                (None, _("Disable locking")),
            ],
        )


@config_variable_registry.register
class ConfigVariableAgentSimulator(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "agent_simulator"

    def valuespec(self):
        return Checkbox(
            title=_("SNMP Agent Simulator"),
            label=_("Process stored SNMP walks with agent simulator"),
            help=_("When using stored SNMP walks you can place inline code generating "
                   "dynamic simulation data. This feature can be activated here. There "
                   "is a big chance that you will never need this feature..."),
        )


@config_variable_registry.register
class ConfigVariableDelayPrecompile(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "delay_precompile"

    def valuespec(self):
        return Checkbox(
            title=_("Delay precompiling of host checks"),
            label=_("delay precompiling"),
            help=_(
                "If you enable this option, then Check_MK will not directly Python-bytecompile "
                "all host checks when activating the configuration and restarting Nagios. "
                "Instead it will delay this to the first "
                "time the host is actually checked being by Nagios.<p>This reduces the time needed "
                "for the operation, but on the other hand will lead to a slightly higher load "
                "of Nagios for the first couple of minutes after the restart. "),
        )


@config_variable_registry.register
class ConfigVariableClusterMaxCachefileAge(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "cluster_max_cachefile_age"

    def valuespec(self):
        return Integer(
            title=_("Maximum cache file age for clusters"),
            label=_("seconds"),
            help=_("The number of seconds a cache file may be old if check_mk should "
                   "use it instead of getting information from the target hosts while "
                   "checking a cluster. Per default this is enabled and set to 90 seconds. "
                   "If your check cycle is set to a larger value than one minute then "
                   "you should increase this accordingly."),
        )


@config_variable_registry.register
class ConfigVariablePiggybackMaxCachefileAge(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "piggyback_max_cachefile_age"

    def valuespec(self):
        return Age(
            title=_("Maximum age for piggyback files"),
            help=_(
                "The maximum age for piggy back data from another host to be valid for monitoring. "
                "Older files are deleted before processing them. Please make sure that this age is "
                "at least as large as you normal check interval for piggy hosts."),
        )


@config_variable_registry.register
class ConfigVariableCheckMKPerfdataWithTimes(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "check_mk_perfdata_with_times"

    def valuespec(self):
        return Checkbox(
            title=_("Check_MK with times performance data"),
            label=_("Return process times within performance data"),
            help=_("Enabling this option results in additional performance data "
                   "for the Check_MK output, giving information regarding the process times. "
                   "It provides the following fields: user_time, system_time, children_user_time "
                   "and children_system_time"),
        )


@config_variable_registry.register
class ConfigVariableUseDNSCache(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "use_dns_cache"

    def valuespec(self):
        return Checkbox(
            title=_("Use DNS lookup cache"),
            label=_("Prevent DNS lookups by use of a cache file"),
            help=_(
                "When this option is enabled (which is the default), then Check_MK tries to "
                "prevent IP address lookups during the configuration generation. This can speed "
                "up this process greatly when you have a larger number of hosts. The cache is stored "
                "in a simple file. Note: when the cache is enabled then changes of the IP address "
                "of a host in your name server will not be detected immediately. If you need an "
                "immediate update then simply disable the cache once, activate the changes and "
                "enabled it again. OMD based installations automatically update the cache once "
                "a day."),
        )


@config_variable_registry.register
class ConfigVariableUseInlineSNMP(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "use_inline_snmp"

    def valuespec(self):
        return Checkbox(
            title=_("Use Inline SNMP"),
            label=_("Enable inline SNMP (directly use net-snmp libraries)"),
            help=_(
                "By default Check_MK uses command line calls of Net-SNMP tools like snmpget or "
                "snmpwalk to gather SNMP information. For each request a new command line "
                "program is being executed. It is now possible to use the inline SNMP implementation "
                "which calls the net-snmp libraries directly via its python bindings. This "
                "should increase the performance of SNMP checks in a significant way. The inline "
                "SNMP mode is a feature which improves the performance for large installations and "
                "only available via our subscription."),
        )


@config_variable_registry.register
class ConfigVariableRecordInlineSNMPStats(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "record_inline_snmp_stats"

    def valuespec(self):
        return Checkbox(
            title=_("Record statistics of Inline SNMP"),
            label=_("Enable recording of Inline SNMP statistics"),
            help=_(
                "When you have enabled Inline SNMP, you can use this flag to enable recording of "
                "some performance related values. The recorded values are stored in a single file "
                "at <tt>var/check_mk/snmp.stats</tt>.<br><br>"
                "<i>Please note:</i> Only enable this for a short period, because it will "
                "decrease the performance of your monitoring."),
        )


@config_variable_registry.register
class ConfigVariableHTTPProxies(ConfigVariable):
    def group(self):
        return ConfigVariableGroupCheckExecution

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "http_proxies"

    def valuespec(self):
        return Transform(
            ListOf(
                Dictionary(
                    title=_("HTTP proxy"),
                    elements=[
                        ("ident",
                         ID(
                             title=_("Unique ID"),
                             help=_(
                                 "The ID must be a unique text. It will be used as an internal key "
                                 "when objects refer to this object."),
                             allow_empty=False,
                         )),
                        ("title",
                         TextUnicode(
                             title=_("Title"),
                             help=_("The title of the %s. It will be used as display name.") %
                             _("HTTP proxy"),
                             allow_empty=False,
                             size=80,
                         )),
                        ("proxy_url", HTTPProxyInput()),
                    ],
                    optional_keys=None,
                ),
                title=_("HTTP proxies"),
                movable=False,
                totext=_("%d HTTP proxy servers configured"),
                help=_("Use this option to configure one or several proxy servers that can then be "
                       "used in different places to establish connections to services using these "
                       "HTTP proxies."),
                validate=self._validate_proxies,
            ),
            forth=lambda v: v.values(),
            back=lambda v: {p["ident"]: p for p in v},
        )

    def _validate_proxies(self, value, varprefix):
        seen_idents, seen_titles = [], []
        for http_proxy in value:
            if http_proxy["ident"] in seen_idents:
                raise MKUserError(
                    varprefix,
                    _("Found multiple proxies using the ID '%s'") % http_proxy["ident"])
            seen_idents.append(http_proxy["ident"])

            if http_proxy["title"] in seen_titles:
                raise MKUserError(
                    varprefix,
                    _("Found multiple proxies using the title '%s'") % http_proxy["title"])
            seen_titles.append(http_proxy["title"])


@config_variable_group_registry.register
class ConfigVariableGroupServiceDiscovery(ConfigVariableGroup):
    def title(self):
        return _("Service discovery")

    def sort_index(self):
        return 4


@config_variable_registry.register
class ConfigVariableInventoryCheckInterval(ConfigVariable):
    def group(self):
        return ConfigVariableGroupServiceDiscovery

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "inventory_check_interval"

    def valuespec(self):
        return Optional(
            Integer(title=_("Perform service discovery check every"),
                    unit=_("minutes"),
                    min_value=1,
                    default_value=720),
            title=_("Enable regular service discovery checks (deprecated)"),
            help=_("If enabled, Check_MK will create one additional service per host "
                   "that does a regular check, if the service discovery would find new services "
                   "currently un-monitored. <b>Note:</b> This option is deprecated and has been "
                   "replaced by the rule set <a href='%s'>Periodic Service Discovery</a>, "
                   "which allows a per-host configuration and additional features such as "
                   "automatic rediscovery. Rules in that rule set will override the global "
                   "settings done here.") % "wato.py?mode=edit_ruleset&varname=periodic_discovery",
        )


@config_variable_registry.register
class ConfigVariableInventoryCheckSeverity(ConfigVariable):
    def group(self):
        return ConfigVariableGroupServiceDiscovery

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "inventory_check_severity"

    def valuespec(self):
        return DropdownChoice(
            title=_("Severity of failed service discovery check"),
            help=_("Please select which alarm state the service discovery check services "
                   "shall assume in case that un-monitored services are found."),
            choices=[
                (0, _("OK - do not alert, just display")),
                (1, _("Warning")),
                (2, _("Critical")),
                (3, _("Unknown")),
            ],
        )


@config_variable_registry.register
class ConfigVariableInventoryCheckDoScan(ConfigVariable):
    def group(self):
        return ConfigVariableGroupServiceDiscovery

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "inventory_check_do_scan"

    def valuespec(self):
        return DropdownChoice(
            title=_("Service discovery check for SNMP devices"),
            choices=[
                (True, _("Perform full SNMP scan always, detect new check types")),
                (False, _("Just rely on existing check files, detect new items only")),
            ],
        )


@config_variable_registry.register
class ConfigVariableInventoryCheckAutotrigger(ConfigVariable):
    def group(self):
        return ConfigVariableGroupServiceDiscovery

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "inventory_check_autotrigger"

    def valuespec(self):
        return Checkbox(
            title=_("Service discovery triggers service discovery check"),
            label=_(
                "Automatically schedule service discovery check after service configuration changes"
            ),
            help=_("When this option is enabled then after each change of the service "
                   "configuration of a host via WATO - may it be via manual changes or a bulk "
                   "discovery - the service discovery check is automatically rescheduled in order "
                   "to reflect the new service state correctly immediately."),
        )


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


@rulespec_group_registry.register
class RulespecGroupGrouping(RulespecGroup):
    @property
    def name(self):
        return "grouping"

    @property
    def title(self):
        return _("Grouping")

    @property
    def help(self):
        return _("Assignment of host & services to host, service and contacts groups.")


def _valuespec_host_groups():
    return HostGroupSelection(
        title=_("Assignment of hosts to host groups"),
        help=_("Hosts can be grouped together into host groups. The most common use case "
               "is to put hosts which belong together in a host group to make it possible "
               "to get them listed together in the status GUI."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupGrouping,
        match_type="all",
        name="host_groups",
        valuespec=_valuespec_host_groups,
    ))


def _valuespec_service_groups():
    return ServiceGroupSelection(title=_("Assignment of services to service groups"),)


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupGrouping,
        item_type="service",
        match_type="all",
        name="service_groups",
        valuespec=_valuespec_service_groups,
    ))


def _valuespec_host_contactgroups():
    return ContactGroupSelection(title=_("Assignment of hosts to contact groups"),)


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupGrouping,
        match_type="all",
        name="host_contactgroups",
        valuespec=_valuespec_host_contactgroups,
    ))


def _valuespec_service_contactgroups():
    return ContactGroupSelection(title=_("Assignment of services to contact groups"),)


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupGrouping,
        item_type="service",
        match_type="all",
        name="service_contactgroups",
        valuespec=_valuespec_service_contactgroups,
    ))


def _valuespec_extra_service_conf_max_check_attempts():
    return Integer(
        title=_("Maximum number of check attempts for service"),
        help=_("The maximum number of failed checks until a service problem state will "
               "be considered as <u>hard</u>. Only hard state trigger notifications. "),
        minvalue=1,
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationServiceChecks,
        item_type="service",
        name="extra_service_conf:max_check_attempts",
        valuespec=_valuespec_extra_service_conf_max_check_attempts,
    ))


def _valuespec_extra_service_conf_check_interval():
    return Transform(
        Age(minvalue=1, default_value=60),
        forth=lambda v: int(v * 60),
        back=lambda v: float(v) / 60.0,
        title=_("Normal check interval for service checks"),
        help=_("Check_MK usually uses an interval of one minute for the active Check_MK "
               "check and for legacy checks. Here you can specify a larger interval. Please "
               "note, that this setting only applies to active checks (those with the "
               "reschedule button). If you want to change the check interval of "
               "the Check_MK service only, specify <tt><b>Check_MK$</b></tt> in the list "
               "of services."),
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationServiceChecks,
        item_type="service",
        name="extra_service_conf:check_interval",
        valuespec=_valuespec_extra_service_conf_check_interval,
    ))


def _valuespec_extra_service_conf_retry_interval():
    return Transform(
        Age(minvalue=1, default_value=60),
        forth=lambda v: int(v * 60),
        back=lambda v: float(v) / 60.0,
        title=_("Retry check interval for service checks"),
        help=_("This setting is relevant if you have set the maximum number of check "
               "attempts to a number greater than one. In case a service check is not OK "
               "and the maximum number of check attempts is not yet reached, it will be "
               "rescheduled with this interval. The retry interval is usually set to a smaller "
               "value than the normal interval.<br><br>This setting only applies to "
               "active checks."),
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationServiceChecks,
        item_type="service",
        name="extra_service_conf:retry_interval",
        valuespec=_valuespec_extra_service_conf_retry_interval,
    ))


def _valuespec_extra_service_conf_check_period():
    return TimeperiodSelection(
        title=_("Check period for active services"),
        help=_("If you specify a notification period for a service then active checks "
               "of that service will only be done in that period. Please note, that the "
               "checks driven by Check_MK are passive checks and are not affected by this "
               "rule. You can use the rule for the active Check_MK check, however."),
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationServiceChecks,
        item_type="service",
        name="extra_service_conf:check_period",
        valuespec=_valuespec_extra_service_conf_check_period,
    ))


def _valuespec_check_periods():
    return TimeperiodSelection(
        title=_("Check period for passive Check_MK services"),
        help=_("If you specify a notification period for a Check_MK service then "
               "results will be processed only within this period."),
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationServiceChecks,
        item_type="service",
        name="check_periods",
        valuespec=_valuespec_check_periods,
    ))


def _valuespec_extra_service_conf_process_perf_data():
    return DropdownChoice(
        title=_("Enable/disable processing of perfdata for services"),
        help=_("This setting allows you to disable the processing of perfdata for a "
               "service completely."),
        choices=[("1", _("Enable processing of perfdata")),
                 ("0", _("Disable processing of perfdata"))],
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationServiceChecks,
        item_type="service",
        name="extra_service_conf:process_perf_data",
        valuespec=_valuespec_extra_service_conf_process_perf_data,
    ))


def _valuespec_extra_service_conf_passive_checks_enabled():
    return DropdownChoice(
        title=_("Enable/disable passive checks for services"),
        help=_("This setting allows you to disable the processing of passiv check results for a "
               "service."),
        choices=[("1", _("Enable processing of passive check results")),
                 ("0", _("Disable processing of passive check results"))],
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationServiceChecks,
        item_type="service",
        name="extra_service_conf:passive_checks_enabled",
        valuespec=_valuespec_extra_service_conf_passive_checks_enabled,
    ))


def _valuespec_extra_service_conf_active_checks_enabled():
    return DropdownChoice(
        title=_("Enable/disable active checks for services"),
        help=_("This setting allows you to disable or enable "
               "active checks for a service."),
        choices=[("1", _("Enable active checks")), ("0", _("Disable active checks"))],
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationServiceChecks,
        item_type="service",
        name="extra_service_conf:active_checks_enabled",
        valuespec=_valuespec_extra_service_conf_active_checks_enabled,
    ))


def _valuespec_extra_host_conf_max_check_attempts():
    return Integer(
        title=_("Maximum number of check attempts for host"),
        help=_("The maximum number of failed host checks until the host will be considered "
               "in a hard down state"),
        minvalue=1,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationHostChecks,
        name="extra_host_conf:max_check_attempts",
        valuespec=_valuespec_extra_host_conf_max_check_attempts,
    ))


def _valuespec_extra_host_conf_check_interval():
    return Transform(
        Age(minvalue=1, default_value=60),
        forth=lambda v: int(v * 60),
        back=lambda v: float(v) / 60.0,
        title=_("Normal check interval for host checks"),
        help=_(
            "The default interval is set to 6 seconds for smart ping and one minute for all other. Here you can specify a larger "
            "interval. The host is contacted in this interval on a regular base. The host "
            "check is also being executed when a problematic service state is detected to check "
            "wether or not the service problem is resulting from a host problem."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationHostChecks,
        name="extra_host_conf:check_interval",
        valuespec=_valuespec_extra_host_conf_check_interval,
    ))


def _valuespec_extra_host_conf_retry_interval():
    return Transform(
        Age(minvalue=1, default_value=60),
        forth=lambda v: int(v * 60),
        back=lambda v: float(v) / 60.0,
        title=_("Retry check interval for host checks"),
        help=_(
            "This setting is relevant if you have set the maximum number of check "
            "attempts to a number greater than one. In case a host check is not UP "
            "and the maximum number of check attempts is not yet reached, it will be "
            "rescheduled with this interval. The retry interval is usually set to a smaller "
            "value than the normal interval. The default is 6 seconds for smart ping and 60 seconds for all other."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationHostChecks,
        name="extra_host_conf:retry_interval",
        valuespec=_valuespec_extra_host_conf_retry_interval,
    ))


def _valuespec_extra_host_conf_check_period():
    return TimeperiodSelection(
        title=_("Check period for hosts"),
        help=_("If you specify a check period for a host then active checks of that "
               "host will only take place within that period. In the rest of the time "
               "the state of the host will stay at its last status."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationHostChecks,
        name="extra_host_conf:check_period",
        valuespec=_valuespec_extra_host_conf_check_period,
    ))


def _host_check_commands_host_check_command_choices():
    if config.user.may('wato.add_or_modify_executables'):
        custom_choice = [
            ("custom", _("Use a custom check plugin..."), PluginCommandLine()),
        ]
    else:
        custom_choice = []
    return [
        ("ping", _("PING (active check with ICMP echo request)")),
        ("smart", _("Smart PING (only with Check_MK Micro Core)")),
        ("tcp", _("TCP Connect"),
         Integer(label=_("to port:"), minvalue=1, maxvalue=65535, default_value=80)),
        ("ok", _("Always assume host to be up")),
        ("agent", _("Use the status of the Check_MK Agent")),
        ("service", _("Use the status of the service..."),
         TextUnicode(
             size=45,
             allow_empty=False,
             attrencode=True,
             help=_("You can use the macro <tt>$HOSTNAME$</tt> here. It will be replaced "
                    "with the name of the current host."),
         )),
    ] + custom_choice


def _valuespec_host_check_commands():
    return CascadingDropdown(
        title=_("Host Check Command"),
        help=_("Usually Check_MK uses a series of PING (ICMP echo request) in order to determine "
               "whether a host is up. In some cases this is not possible, however. With this rule "
               "you can specify an alternative way of determining the host's state.") +
        _("The option to use a custom command can only be configured with the permission "
          "\"Can add or modify executables\"."),
        choices=_host_check_commands_host_check_command_choices,
        default_value="ping",
        orientation="horizontal",
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationHostChecks,
        name="host_check_commands",
        valuespec=_valuespec_host_check_commands,
    ))


@rulespec_group_registry.register
class RulespecGroupMonitoringConfigurationNotifications(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "notifications"

    @property
    def title(self):
        return _("Notifications")


def _valuespec_extra_host_conf_notifications_enabled():
    return DropdownChoice(
        title=_("Enable/disable notifications for hosts"),
        help=_("This setting allows you to disable notifications about problems of a "
               "host completely. Per default all notifications are enabled. Sometimes "
               "it is more convenient to just disable notifications then to remove a "
               "host completely from the monitoring. Note: this setting has no effect "
               "on the notifications of service problems of a host."),
        choices=[
            ("1", _("Enable host notifications")),
            ("0", _("Disable host notifications")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        name="extra_host_conf:notifications_enabled",
        valuespec=_valuespec_extra_host_conf_notifications_enabled,
    ))


def _valuespec_extra_service_conf_notifications_enabled():
    return DropdownChoice(
        title=_("Enable/disable notifications for services"),
        help=_("This setting allows you to disable notifications about problems of a "
               "service completely. Per default all notifications are enabled."),
        choices=[
            ("1", _("Enable service notifications")),
            ("0", _("Disable service notifications")),
        ],
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        item_type="service",
        name="extra_service_conf:notifications_enabled",
        valuespec=_valuespec_extra_service_conf_notifications_enabled,
    ))


def _valuespec_extra_host_conf_notification_options():
    return Transform(
        ListChoice(
            choices=[
                ("d", _("Host goes down")),
                ("u", _("Host gets unreachble")),
                ("r", _("Host goes up again")),
                ("f", _("Start or end of flapping state")),
                ("s", _("Start or end of a scheduled downtime")),
            ],
            default_value=["d", "r", "f", "s"],
        ),
        title=_("Notified events for hosts"),
        help=_("This ruleset allows you to restrict notifications of host problems to certain "
               "states, e.g. only notify on DOWN, but not on UNREACHABLE. Please select the types "
               "of events that should initiate notifications. Please note that several other "
               "filters must also be passed in order for notifications to finally being sent out."
               "<br><br>"
               "Please note: There is a difference between the Microcore and Nagios when you have "
               "a host that has no matching rule in this ruleset. In this case the Microcore will "
               "not send out UNREACHABLE notifications while the Nagios core would send out "
               "UNREACHABLE notifications. To align this behaviour, create a rule matching "
               "all your hosts and configure it to either send UNREACHABLE notifications or not."),
        forth=lambda x: x != 'n' and x.split(",") or [],
        back=lambda x: ",".join(x) or "n",
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        name="extra_host_conf:notification_options",
        valuespec=_valuespec_extra_host_conf_notification_options,
    ))


def _valuespec_extra_service_conf_notification_options():
    return Transform(
        ListChoice(
            choices=[
                ("w", _("Service goes into warning state")),
                ("u", _("Service goes into unknown state")),
                ("c", _("Service goes into critical state")),
                ("r", _("Service recovers to OK")),
                ("f", _("Start or end of flapping state")),
                ("s", _("Start or end of a scheduled downtime")),
            ],
            default_value=["w", "u", "c", "r", "f", "s"],
        ),
        title=_("Notified events for services"),
        help=_("This ruleset allows you to restrict notifications of service problems to certain "
               "states, e.g. only notify on CRIT, but not on WARN. Please select the types "
               "of events that should initiate notifications. Please note that several other "
               "filters must also be passed in order for notifications to finally being sent out."),
        forth=lambda x: x != 'n' and x.split(",") or [],
        back=lambda x: ",".join(x) or "n",
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        item_type="service",
        name="extra_service_conf:notification_options",
        valuespec=_valuespec_extra_service_conf_notification_options,
    ))


def _valuespec_extra_host_conf_notification_period():
    return TimeperiodSelection(
        title=_("Notification period for hosts"),
        help=_("If you specify a notification period for a host then notifications "
               "about problems of that host (not of its services!) will only be sent "
               "if those problems occur within the notification period. Also you can "
               "filter out problems in the problems views for objects not being in "
               "their notification period (you can think of the notification period "
               "as the 'service time')."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        name="extra_host_conf:notification_period",
        valuespec=_valuespec_extra_host_conf_notification_period,
    ))


def _valuespec_extra_service_conf_notification_period():
    return TimeperiodSelection(
        title=_("Notification period for services"),
        help=_("If you specify a notification period for a service then notifications "
               "about that service will only be sent "
               "if those problems occur within the notification period. Also you can "
               "filter out problems in the problems views for objects not being in "
               "their notification period (you can think of the notification period "
               "as the 'service time')."),
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        item_type="service",
        name="extra_service_conf:notification_period",
        valuespec=_valuespec_extra_service_conf_notification_period,
    ))


def transform_float_minutes_to_age(float_minutes):
    return int(float_minutes * 60)


def transform_age_to_float_minutes(age):
    return float(age) / 60.0


def _valuespec_extra_host_conf_first_notification_delay():
    return Transform(
        Age(
            minvalue=0,
            default_value=300,
            label=_("Delay:"),
            title=_("Delay host notifications"),
            help=_("This setting delays notifications about host problems by the "
                   "specified amount of time. If the host is up again within that "
                   "time, no notification will be sent out."),
        ),
        forth=transform_float_minutes_to_age,
        back=transform_age_to_float_minutes,
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=0.0,
        group=RulespecGroupMonitoringConfigurationNotifications,
        name="extra_host_conf:first_notification_delay",
        valuespec=_valuespec_extra_host_conf_first_notification_delay,
    ))


def _valuespec_extra_service_conf_first_notification_delay():
    return Transform(
        Age(
            minvalue=0,
            default_value=300,
            label=_("Delay:"),
            unit=_("minutes"),
            title=_("Delay service notifications"),
            help=_("This setting delays notifications about service problems by the "
                   "specified amount of time. If the service is OK again within that "
                   "time, no notification will be sent out."),
        ),
        forth=transform_float_minutes_to_age,
        back=transform_age_to_float_minutes,
    )


rulespec_registry.register(
    ServiceRulespec(
        factory_default=0.0,
        group=RulespecGroupMonitoringConfigurationNotifications,
        item_type="service",
        name="extra_service_conf:first_notification_delay",
        valuespec=_valuespec_extra_service_conf_first_notification_delay,
    ))


def _valuespec_extra_host_conf_notification_interval():
    return Optional(
        Transform(
            Float(
                minvalue=0.05,
                default_value=120.0,
                label=_("Interval:"),
                unit=_("minutes"),
            ),
            forth=float,
        ),
        title=_("Periodic notifications during host problems"),
        help=_("If you enable periodic notifications, then during a problem state "
               "of the host notifications will be sent out in regular intervals "
               "until the problem is acknowledged."),
        label=_("Enable periodic notifications"),
        none_label=_("disabled"),
        none_value=0.0,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        name="extra_host_conf:notification_interval",
        valuespec=_valuespec_extra_host_conf_notification_interval,
    ))


def _valuespec_extra_service_conf_notification_interval():
    return Optional(
        Transform(
            Float(minvalue=0.05, default_value=120.0, label=_("Interval:"), unit=_("minutes")),
            forth=float,
        ),
        title=_("Periodic notifications during service problems"),
        help=_("If you enable periodic notifications, then during a problem state "
               "of the service notifications will be sent out in regular intervals "
               "until the problem is acknowledged."),
        label=_("Enable periodic notifications"),
        none_label=_("disabled"),
        none_value=0.0,
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        item_type="service",
        name="extra_service_conf:notification_interval",
        valuespec=_valuespec_extra_service_conf_notification_interval,
    ))


def _valuespec_extra_host_conf_flap_detection_enabled():
    return DropdownChoice(
        title=_("Enable/disable flapping detection for hosts"),
        help=_("This setting allows you to disable the flapping detection for a "
               "host completely."),
        choices=[
            ("1", _("Enable flap detection")),
            ("0", _("Disable flap detection")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        name="extra_host_conf:flap_detection_enabled",
        valuespec=_valuespec_extra_host_conf_flap_detection_enabled,
    ))


def _valuespec_extra_service_conf_flap_detection_enabled():
    return DropdownChoice(
        title=_("Enable/disable flapping detection for services"),
        help=_("This setting allows you to disable the flapping detection for a "
               "service completely."),
        choices=[
            ("1", _("Enable flap detection")),
            ("0", _("Disable flap detection")),
        ],
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        item_type="service",
        name="extra_service_conf:flap_detection_enabled",
        valuespec=_valuespec_extra_service_conf_flap_detection_enabled,
    ))


def _valuespec_extra_service_conf_notes_url():
    return TextAscii(
        label=_("URL:"),
        title=_("Notes URL for Services"),
        help=_("With this setting you can set links to documentations "
               "for each service"),
        attrencode=True,
        size=80,
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        item_type="service",
        name="extra_service_conf:notes_url",
        valuespec=_valuespec_extra_service_conf_notes_url,
    ))


def _valuespec_extra_host_conf_notes_url():
    return TextAscii(
        label=_("URL:"),
        title=_("Notes URL for Hosts"),
        help=_("With this setting you can set links to documentations "
               "for Hosts"),
        attrencode=True,
        size=80,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        name="extra_host_conf:notes_url",
        valuespec=_valuespec_extra_host_conf_notes_url,
    ))


def _valuespec_extra_service_conf_display_name():
    return TextUnicode(
        title=_("Alternative display name for Services"),
        help=_("This rule set allows you to specify an alternative name "
               "to be displayed for certain services. This name is available as "
               "a column when creating new views or modifying existing ones. "
               "It is always visible in the details view of a service. In the "
               "availability reporting there is an option for using that name "
               "instead of the normal service description. It does <b>not</b> automatically "
               "replace the normal service name in all views.<br><br><b>Note</b>: The "
               "purpose of this rule set is to define unique names for several well-known "
               "services. It cannot rename services in general."),
        size=64,
        attrencode=True,
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationNotifications,
        item_type="service",
        name="extra_service_conf:display_name",
        valuespec=_valuespec_extra_service_conf_display_name,
    ))


@rulespec_group_registry.register
class RulespecGroupMonitoringConfigurationInventoryAndCMK(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "inventory_and_check_mk_settings"

    @property
    def title(self):
        return _("Inventory and Check_MK settings")


def _help_only_hosts():
    return _("By adding rules to this ruleset you can define a subset of your hosts "
             "to be actually monitored. As long as the rule set is empty "
             "all configured hosts will be monitored. As soon as you add at least one "
             "rule, only hosts with a matching rule will be monitored.")


rulespec_registry.register(
    BinaryHostRulespec(
        group=RulespecGroupMonitoringConfigurationInventoryAndCMK,
        help_func=_help_only_hosts,
        is_optional=True,
        name="only_hosts",
        title=lambda: _("Hosts to be monitored"),
    ))


def _help_ignored_services():
    return _("Services that are declared as <u>disabled</u> by this rule set will not be added "
             "to a host during discovery (automatic service detection). Services that already "
             "exist will continued to be monitored but be marked as obsolete in the service "
             "list of a host.")


rulespec_registry.register(
    BinaryServiceRulespec(
        group=RulespecGroupMonitoringConfigurationInventoryAndCMK,
        help_func=_help_ignored_services,
        item_type="service",
        name="ignored_services",
        title=lambda: _("Disabled services"),
    ))


def _valuespec_ignored_checks():
    return CheckTypeSelection(
        title=_("Disabled checks"),
        help=_("This ruleset is similar to 'Disabled services', but selects checks to be disabled "
               "by their <b>type</b>. This allows you to disable certain technical implementations "
               "such as filesystem checks via SNMP on hosts that also have the Check_MK agent "
               "installed."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationInventoryAndCMK,
        name="ignored_checks",
        valuespec=_valuespec_ignored_checks,
    ))


def _help_clustered_services():
    return _("When you define HA clusters in WATO then you also have to specify which services "
             "of a node should be assigned to the cluster and which services to the physical "
             "node. This is done by this ruleset. Please note that the rule will be applied to "
             "the <i>nodes</i>, not to the cluster.<br><br>Please make sure that you re-"
             "inventorize the cluster and the physical nodes after changing this ruleset.")


rulespec_registry.register(
    BinaryServiceRulespec(
        group=RulespecGroupMonitoringConfigurationInventoryAndCMK,
        help_func=_help_clustered_services,
        item_type="service",
        name="clustered_services",
        title=lambda: _("Clustered services"),
    ))


def _periodic_discovery_add_severity_new_host_label(val):
    val.setdefault("severity_new_host_label", 1)
    return val


def _valuespec_periodic_discovery():
    return Alternative(
        title=_("Periodic service discovery"),
        style="dropdown",
        default_value={
            "check_interval": 2 * 60,
            "severity_unmonitored": 1,
            "severity_vanished": 0,
            "severity_new_host_label": 1,
            "inventory_check_do_scan": True,
        },
        elements=[
            FixedValue(
                None,
                title=_("Do not perform periodic service discovery check"),
                totext=_("no discovery check"),
            ),
            Transform(
                Dictionary(
                    title=_("Perform periodic service discovery check"),
                    help=_(
                        "If enabled, Check_MK will create one additional service per host "
                        "that does a periodic check, if the service discovery would find new services "
                        "that are currently not monitored."),
                    elements=[
                        ("check_interval",
                         Transform(
                             Age(minvalue=1, display=["days", "hours", "minutes"]),
                             forth=lambda v: int(v * 60),
                             back=lambda v: float(v) / 60.0,
                             title=_("Perform service discovery every"),
                         )),
                        ("severity_unmonitored",
                         DropdownChoice(
                             title=_("Severity of unmonitored services"),
                             help=_(
                                 "Please select which alarm state the service discovery check services "
                                 "shall assume in case that un-monitored services are found."),
                             choices=[
                                 (0, _("OK - do not alert, just display")),
                                 (1, _("Warning")),
                                 (2, _("Critical")),
                                 (3, _("Unknown")),
                             ],
                         )),
                        ("severity_vanished",
                         DropdownChoice(
                             title=_("Severity of vanished services"),
                             help=
                             _("Please select which alarm state the service discovery check services "
                               "shall assume in case that non-existing services are being monitored."
                              ),
                             choices=[
                                 (0, _("OK - do not alert, just display")),
                                 (1, _("Warning")),
                                 (2, _("Critical")),
                                 (3, _("Unknown")),
                             ],
                         )),
                        ("severity_new_host_label",
                         DropdownChoice(
                             title=_("Severity of new host labels"),
                             help=_(
                                 "Please select which state the service discovery check services "
                                 "shall assume in case that new host labels are found."),
                             choices=[
                                 (0, _("OK - do not alert, just display")),
                                 (1, _("Warning")),
                                 (2, _("Critical")),
                                 (3, _("Unknown")),
                             ],
                         )),
                        ("inventory_check_do_scan",
                         DropdownChoice(
                             title=_("Service discovery check for SNMP devices"),
                             choices=[
                                 (True, _("Perform full SNMP scan always, detect new check types")),
                                 (False,
                                  _("Just rely on existing check files, detect new items only"))
                             ])),
                        ("inventory_rediscovery",
                         Dictionary(
                             title=_("Automatically update service configuration"),
                             help=_(
                                 "If active the check will not only notify about un-monitored services, "
                                 "it will also automatically add/remove them as neccessary."),
                             elements=[
                                 ("mode",
                                  DropdownChoice(
                                      title=_("Mode"),
                                      choices=[
                                          (0, _("Add unmonitored services, new host labels")),
                                          (1, _("Remove vanished services")),
                                          (2,
                                           _("Add unmonitored & remove vanished services and host labels"
                                            )),
                                          (3,
                                           _("Refresh all services and host labels (tabula rasa)"))
                                      ],
                                      orientation="vertical",
                                      default_value=0,
                                  )),
                                 ("group_time",
                                  Age(title=_("Group discovery and activation for up to"),
                                      help=_(
                                          "A delay can be configured here so that multiple "
                                          "discoveries can be activated in one go. This avoids frequent core "
                                          "restarts in situations with frequent services changes."),
                                      default_value=15 * 60,
                                      display=["hours", "minutes"])),
                                 ("excluded_time",
                                  ListOfTimeRanges(
                                      title=
                                      _("Never do discovery or activate changes in the following time ranges"
                                       ),
                                      help=_("This avoids automatic changes during these times so "
                                             "that the automatic system doesn't interfere with "
                                             "user activity."),
                                  )),
                                 ("activation",
                                  DropdownChoice(
                                      title=_("Automatic activation"),
                                      choices=[
                                          (True, _("Automatically activate changes")),
                                          (False, _("Do not activate changes")),
                                      ],
                                      default_value=True,
                                      help=_(
                                          "Here you can have the changes activated whenever services "
                                          "have been added or removed."),
                                  )),
                                 ("service_whitelist",
                                  ListOfStrings(
                                      title=_("Activate only services matching"),
                                      allow_empty=False,
                                      help=
                                      _("Set service names or regular expression patterns here to "
                                        "allow only matching services to be activated automatically. "
                                        "If you set both this and \'Don't activate services matching\', "
                                        "both rules have to apply for a service to be activated."),
                                  )),
                                 ("service_blacklist",
                                  ListOfStrings(
                                      title=_("Don't activate services matching"),
                                      allow_empty=False,
                                      help=
                                      _("Set service names or regular expression patterns here to "
                                        "prevent matching services from being activated automatically. "
                                        "If you set both this and \'Activate only services matching\', "
                                        "both rules have to apply for a service to be activated."),
                                  )),
                             ],
                             optional_keys=["service_whitelist", "service_blacklist"],
                         )),
                    ],
                    optional_keys=["inventory_rediscovery"],
                ),
                forth=_periodic_discovery_add_severity_new_host_label,
            ),
        ])


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationInventoryAndCMK,
        name="periodic_discovery",
        valuespec=_valuespec_periodic_discovery,
    ))


@rulespec_group_registry.register
class RulespecGroupMonitoringConfigurationVarious(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "various"

    @property
    def title(self):
        return _("Various")


def _valuespec_clustered_services_mapping():
    return TextAscii(
        title=_("Clustered services for overlapping clusters"),
        label=_("Assign services to the following cluster:"),
        help=_("It's possible to have clusters that share nodes. You could say that "
               "such clusters &quot;overlap&quot;. In such a case using the ruleset "
               "<i>Clustered services</i> is not sufficient since it would not be clear "
               "to which of the several possible clusters a service found on such a shared "
               "node should be assigned to. With this ruleset you can assign services and "
               "explicitely specify which cluster assign them to."),
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationVarious,
        item_type="service",
        name="clustered_services_mapping",
        valuespec=_valuespec_clustered_services_mapping,
    ))


def _valuespec_extra_host_conf_service_period():
    return TimeperiodSelection(
        title=_("Service period for hosts"),
        help=_(
            "When it comes to availability reporting, you might want the report "
            "to cover only certain time periods, e.g. only Monday to Friday "
            "from 8:00 to 17:00. You can do this by specifying a service period "
            "for hosts or services. In the reporting you can then decide to "
            "include, exclude or ignore such periods und thus e.g. create a report "
            "of the availability just within or without these times. <b>Note</b>: Changes in the "
            "actual <i>definition</i> of a time period will only be reflected in "
            "times <i>after</i> that change. Selecting a different service period "
            "will also be reflected in the past."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationVarious,
        name="extra_host_conf:service_period",
        valuespec=_valuespec_extra_host_conf_service_period,
    ))


def _valuespec_extra_service_conf_service_period():
    return TimeperiodSelection(
        title=_("Service period for services"),
        help=_(
            "When it comes to availability reporting, you might want the report "
            "to cover only certain time periods, e.g. only Monday to Friday "
            "from 8:00 to 17:00. You can do this by specifying a service period "
            "for hosts or services. In the reporting you can then decide to "
            "include, exclude or ignore such periods und thus e.g. create a report "
            "of the availability just within or without these times. <b>Note</b>: Changes in the "
            "actual <i>definition</i> of a time period will only be reflected in "
            "times <i>after</i> that change. Selecting a different service period "
            "will also be reflected in the past."),
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupMonitoringConfigurationVarious,
        item_type="service",
        name="extra_service_conf:service_period",
        valuespec=_valuespec_extra_service_conf_service_period,
    ))


def _valuespec_piggybacked_host_files():
    return Dictionary(
        title=_("Piggybacked Host Files"),
        optional_keys=[],
        elements=[
            ("global_max_cache_age", _vs_max_cache_age()),
            ("global_validity", _vs_validity()),
            ("per_piggybacked_host",
             ListOf(
                 Dictionary(
                     optional_keys=[],
                     elements=[
                         ("piggybacked_hostname",
                          TextUnicode(
                              title=_("Piggybacked host name"),
                              allow_empty=False,
                          )),
                         ("max_cache_age", _vs_max_cache_age(additional_title="or above")),
                         ("validity", _vs_validity()),
                     ],
                 ),
                 title=_("Exceptions for piggybacked hosts"),
                 add_label=_("Add exception"),
             )),
        ],
        help=_(
            "We assume that a source host is sending piggyback data every check interval "
            "by default. If this is not the case for some source hosts then the <b>Check_MK</b> "
            "and <b>Check_MK Disovery</b> services of the piggybacked hosts report "
            "<b>Got not information from host</b> resp. <b>vanished services</b> if the piggybacked "
            "data is missing within a check interval. "
            "This rule helps you to get more control over the piggybacked host data handling. "
            "The source host names have to be set in the condition field 'Explicit hosts'."),
    )


def _vs_max_cache_age(additional_title=None):
    if additional_title is None:
        title = _("Use maximum age from global settings")
    else:
        title = _("Use maximum age from global settings %s" % additional_title)
    return Alternative(
        title=_("Set maximum age how long piggyback files are kept"),
        style="dropdown",
        elements=[
            FixedValue(
                "global",
                title=title,
                totext="",
            ),
            Age(
                title=_("Set maximum age"),
                default_value=3600,
            ),
        ],
    )


def _vs_validity():
    return Dictionary(
        title=_("Set period how long piggyback files are treated as valid"),
        elements=[
            ("period", Age(
                title=_("Period"),
                default_value=60,
            )),
            ("check_mk_state",
             MonitoringState(
                 title=_("Check MK status within this period"),
                 default_value=0,
             )),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringConfigurationHostChecks,
        name="piggybacked_host_files",
        valuespec=_valuespec_piggybacked_host_files,
    ))

#.
#   .--User Interface------------------------------------------------------.
#   |   _   _                 ___       _             __                   |
#   |  | | | |___  ___ _ __  |_ _|_ __ | |_ ___ _ __ / _| __ _  ___ ___    |
#   |  | | | / __|/ _ \ '__|  | || '_ \| __/ _ \ '__| |_ / _` |/ __/ _ \   |
#   |  | |_| \__ \  __/ |     | || | | | ||  __/ |  |  _| (_| | (_|  __/   |
#   |   \___/|___/\___|_|    |___|_| |_|\__\___|_|  |_|  \__,_|\___\___|   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | User interface specific rule sets                                    |
#   '----------------------------------------------------------------------'


@rulespec_group_registry.register
class RulespecGroupUserInterface(RulespecGroup):
    @property
    def name(self):
        return "user_interface"

    @property
    def title(self):
        return _("User Interface")

    @property
    def help(self):
        return _("Settings concerning the user interface of Check_MK")


def _valuespec_extra_host_conf_icon_image():
    return Transform(
        IconSelector(
            title=_("Icon image for hosts in status GUI"),
            help=_("You can assign icons to hosts for the status GUI. "
                   "Put your images into <tt>%s</tt>. ") %
            (cmk.utils.paths.omd_root + "/local/share/check_mk/web/htdocs/images/icons"),
        ),
        forth=lambda v: v and (v.endswith('.png') and v[:-4]) or v,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupUserInterface,
        name="extra_host_conf:icon_image",
        valuespec=_valuespec_extra_host_conf_icon_image,
    ))


def _valuespec_extra_service_conf_icon_image():
    return Transform(
        IconSelector(
            title=_("Icon image for services in status GUI"),
            help=_("You can assign icons to services for the status GUI. "
                   "Put your images into <tt>%s</tt>. ") %
            (cmk.utils.paths.omd_root + "/local/share/check_mk/web/htdocs/images/icons"),
        ),
        forth=lambda v: v and (v.endswith('.png') and v[:-4]) or v,
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupUserInterface,
        item_type="service",
        name="extra_service_conf:icon_image",
        valuespec=_valuespec_extra_service_conf_icon_image,
    ))


def _valuespec_host_icons_and_actions():
    return UserIconOrAction(
        title=_("Custom icons or actions for hosts in status GUI"),
        help=_("You can assign icons or actions to hosts for the status GUI."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupUserInterface,
        match_type="all",
        name="host_icons_and_actions",
        valuespec=_valuespec_host_icons_and_actions,
    ))


def _valuespec_service_icons_and_actions():
    return UserIconOrAction(
        title=_("Custom icons or actions for services in status GUI"),
        help=_("You can assign icons or actions to services for the status GUI."),
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupUserInterface,
        item_type="service",
        match_type="all",
        name="service_icons_and_actions",
        valuespec=_valuespec_service_icons_and_actions,
    ))


def _valuespec_extra_host_conf__ESCAPE_PLUGIN_OUTPUT():
    return DropdownChoice(
        title=_("Escape HTML codes in host output"),
        help=_("By default, for security reasons, the GUI does not interpret any HTML "
               "code received from external sources, like plugin output or log messages. "
               "If you are really sure what you are doing and need to have HTML codes, like "
               "links rendered, disable this option. Be aware, you might open the way "
               "for several injection attacks.") +
        _("This setting can either be set globally or individually for selected hosts "
          "or services using the host or service rulesets."),
        choices=[
            ("1", _("Escape HTML codes")),
            ("0", _("Don't escape HTML codes (insecure)")),
        ],
        default_value="1",
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupUserInterface,
        name="extra_host_conf:_ESCAPE_PLUGIN_OUTPUT",
        valuespec=_valuespec_extra_host_conf__ESCAPE_PLUGIN_OUTPUT,
    ))


def _valuespec_extra_service_conf__ESCAPE_PLUGIN_OUTPUT():
    return DropdownChoice(
        title=_("Escape HTML codes in service output"),
        help=_("By default, for security reasons, the GUI does not interpret any HTML "
               "code received from external sources, like plugin output or log messages. "
               "If you are really sure what you are doing and need to have HTML codes, like "
               "links rendered, disable this option. Be aware, you might open the way "
               "for several injection attacks.") +
        _("This setting can either be set globally or individually for selected hosts "
          "or services using the host or service rulesets."),
        choices=[
            ("1", _("Escape HTML codes")),
            ("0", _("Don't escape HTML codes (insecure)")),
        ],
        default_value="1",
    )


rulespec_registry.register(
    ServiceRulespec(
        group=RulespecGroupUserInterface,
        item_type="service",
        name="extra_service_conf:_ESCAPE_PLUGIN_OUTPUT",
        valuespec=_valuespec_extra_service_conf__ESCAPE_PLUGIN_OUTPUT,
    ))


@rulespec_group_registry.register
class RulespecGroupAgent(RulespecGroup):
    @property
    def name(self):
        return "agent"

    @property
    def title(self):
        return _("Access to Agents")

    @property
    def help(self):
        return _("Settings concerning the connection to the Check_MK and SNMP agents")


@rulespec_group_registry.register
class RulespecGroupAgentGeneralSettings(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupAgent

    @property
    def sub_group_name(self):
        return "general_settings"

    @property
    def title(self):
        return _("General Settings")


def _help_dyndns_hosts():
    return _("This ruleset selects host for dynamic DNS lookup during monitoring. Normally the "
             "IP addresses of hosts are statically configured or looked up when you activate "
             "the changes. In some rare cases DNS lookups must be done each time a host is "
             "connected to, e.g. when the IP address of the host is dynamic and can change.")


rulespec_registry.register(
    BinaryHostRulespec(
        group=RulespecGroupAgentGeneralSettings,
        help_func=_help_dyndns_hosts,
        name="dyndns_hosts",
        title=lambda: _("Hosts with dynamic DNS lookup during monitoring"),
    ))


def _valuespec_primary_address_family():
    return DropdownChoice(
        choices=[
            ("ipv4", _("IPv4")),
            ("ipv6", _("IPv6")),
        ],
        title=_("Primary IP address family of dual-stack hosts"),
        help=_("When you configure dual-stack host (IPv4 + IPv6) monitoring in Check_MK, "
               "normally IPv4 is used as primary address family to communicate with this "
               "host. The other family, IPv6, is just being pinged. You can use this rule "
               "to invert this behaviour to use IPv6 as primary address family."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentGeneralSettings,
        name="primary_address_family",
        valuespec=_valuespec_primary_address_family,
    ))


@rulespec_group_registry.register
class RulespecGroupAgentSNMP(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupAgent

    @property
    def sub_group_name(self):
        return "snmp"

    @property
    def title(self):
        return _("SNMP")


def _valuespec_snmp_communities():
    return SNMPCredentials(
        title=_("SNMP credentials of monitored hosts"),
        help=
        _("By default Check_MK uses the community \"public\" to contact hosts via SNMP v1/v2. This rule "
          "can be used to customize the the credentials to be used when contacting hosts via SNMP."
         ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentSNMP,
        name="snmp_communities",
        valuespec=_valuespec_snmp_communities,
    ))


def _valuespec_management_board_config():
    return CascadingDropdown(
        title=_("Management board config"),
        choices=[
            ("snmp", _("SNMP"), SNMPCredentials()),
            ("ipmi", _("IPMI"), IPMIParameters()),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentSNMP,
        name="management_board_config",
        valuespec=_valuespec_management_board_config,
    ))


def _valuespec_snmp_character_encodings():
    return DropdownChoice(
        title=_("Output text encoding settings for SNMP devices"),
        help=_("Some devices send texts in non-ASCII characters. Check_MK"
               " always assumes UTF-8 encoding. You can declare other "
               " other encodings here"),
        choices=[
            ("utf-8", _("UTF-8")),
            ("latin1", _("latin1")),
            ("cp437", _("cp437")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentSNMP,
        name="snmp_character_encodings",
        valuespec=_valuespec_snmp_character_encodings,
    ))


def _help_bulkwalk_hosts():
    return _("Most SNMP hosts support SNMP version 2c. However, Check_MK defaults to version "
             "1, in order to support as many devices as possible. Please use this ruleset in "
             "order to configure SNMP v2c for as many hosts as possible. That version has two "
             "advantages: it supports 64 bit counters, which avoids problems with wrapping "
             "counters at too much traffic. And it supports bulk walk, which saves much CPU "
             "and network resources. Please be aware, however, that there are some broken "
             "devices out there, that support bulk walk but behave very bad when it is used. "
             "When you want to enable v2c while not using bulk walk, please use the rule set "
             "snmpv2c_hosts instead.")


rulespec_registry.register(
    BinaryHostRulespec(
        group=RulespecGroupAgentSNMP,
        help_func=_help_bulkwalk_hosts,
        name="bulkwalk_hosts",
        title=lambda: _("Bulk walk: Hosts using bulk walk (enforces SNMP v2c)"),
    ))


def _valuespec_snmp_bulk_size():
    return Integer(
        title=_("Bulk walk: Number of OIDs per bulk"),
        label=_("Number of OIDs to request per bulk: "),
        minvalue=1,
        maxvalue=100,
        default_value=10,
        help=_("This variable allows you to configure the numbr of OIDs Check_MK should request "
               "at once. This rule only applies to SNMP hosts that are configured to be bulk "
               "walk hosts.You may want to use this rule to tune SNMP performance. Be aware: A "
               "higher value is not always better. It may decrease the transactions between "
               "Check_MK and the target system, but may increase the OID overhead in case you "
               "only need a small amount of OIDs."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentSNMP,
        name="snmp_bulk_size",
        valuespec=_valuespec_snmp_bulk_size,
    ))


def _help_snmp_without_sys_descr():
    return _("Devices which do not publish the system description OID .1.3.6.1.2.1.1.1.0 are "
             "normally ignored by the SNMP inventory. Use this ruleset to select hosts which "
             "should nevertheless be checked.")


rulespec_registry.register(
    BinaryHostRulespec(
        group=RulespecGroupAgentSNMP,
        help_func=_help_snmp_without_sys_descr,
        name="snmp_without_sys_descr",
        title=lambda: _("Hosts without system description OID"),
    ))


def _help_snmpv2c_hosts():
    return _("There exist a few devices out there that behave very badly when using SNMP v2c "
             "and bulk walk. If you want to use SNMP v2c on those devices, nevertheless, you "
             "need to configure this device as legacy snmp device and upgrade it to SNMP v2c "
             "(without bulk walk) with this rule set. One reason is enabling 64 bit counters. "
             "Note: This rule won't apply if the device is already configured as SNMP v2c "
             "device.")


rulespec_registry.register(
    BinaryHostRulespec(
        group=RulespecGroupAgentSNMP,
        help_func=_help_snmpv2c_hosts,
        name="snmpv2c_hosts",
        title=lambda: _("Legacy SNMP devices using SNMP v2c"),
    ))


def _valuespec_snmp_timing():
    return Dictionary(
        title=_("Timing settings for SNMP access"),
        help=_("This rule decides about the number of retries and timeout values "
               "for the SNMP access to devices."),
        elements=[
            (
                "timeout",
                Float(
                    title=_("Response timeout for a single query"),
                    help=_(
                        "After a request is sent to the remote SNMP agent we will wait up to this "
                        "number of seconds until assuming the answer get lost and retrying."),
                    default_value=1,
                    minvalue=0.1,
                    maxvalue=60,
                    allow_int=True,
                    unit=_("sec"),
                    size=6,
                ),
            ),
            ("retries",
             Integer(
                 title=_("Number of retries"),
                 default_value=5,
                 minvalue=0,
                 maxvalue=50,
             )),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default={
            'retries': 5,
            'timeout': 1
        },
        group=RulespecGroupAgentSNMP,
        match_type="dict",
        name="snmp_timing",
        valuespec=_valuespec_snmp_timing,
    ))


def _help_non_inline_snmp_hosts():
    return _("Check_MK has an efficient SNMP implementation called Inline SNMP which reduces "
             "the load produced by SNMP monitoring on the monitoring host significantly. This "
             "option is enabled by default for all SNMP hosts and it is a good idea to keep "
             "this default setting. However, there are SNMP devices which have problems with "
             "this SNMP implementation. You can use this rule to disable Inline SNMP for these "
             "hosts.")


rulespec_registry.register(
    BinaryHostRulespec(
        group=RulespecGroupAgentSNMP,
        help_func=_help_non_inline_snmp_hosts,
        name="non_inline_snmp_hosts",
        title=lambda: _("Hosts not using Inline-SNMP"),
    ))


def _help_usewalk_hosts():
    return _("This ruleset helps in test and development. You can create stored SNMP walks on "
             "the command line with cmk --snmpwalk HOSTNAME. A host that is configured with "
             "this ruleset will then use the information from that file instead of using real "
             "SNMP.")


rulespec_registry.register(
    BinaryHostRulespec(
        group=RulespecGroupAgentSNMP,
        help_func=_help_usewalk_hosts,
        name="usewalk_hosts",
        title=lambda: _("Simulating SNMP by using a stored SNMP walk"),
    ))


def _valuespec_snmp_ports():
    return Integer(
        minvalue=1,
        maxvalue=65535,
        default_value=161,
        title=_("UDP port used for SNMP"),
        help=_("This variable allows you to customize the UDP port to be used to "
               "communicate via SNMP on a per-host-basis."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentSNMP,
        name="snmp_ports",
        valuespec=_valuespec_snmp_ports,
    ))


@rulespec_group_registry.register
class RulespecGroupAgentCMKAgent(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupAgent

    @property
    def sub_group_name(self):
        return "check_mk_agent"

    @property
    def title(self):
        return _("Check_MK Agent")


def _valuespec_agent_ports():
    return Integer(
        minvalue=1,
        maxvalue=65535,
        default_value=6556,
        title=_("TCP port for connection to Check_MK agent"),
        help=_("This variable allows to specify the TCP port to "
               "be used to connect to the agent on a per-host-basis. "),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentCMKAgent,
        name="agent_ports",
        valuespec=_valuespec_agent_ports,
    ))


def _valuespec_tcp_connect_timeouts():
    return Float(
        minvalue=1.0,
        default_value=5.0,
        unit="sec",
        title=_("Agent TCP connect timeout"),
        help=_(
            "Timeout for TCP connect to the Check_MK agent in seconds. If the connection "
            "to the agent cannot be established within this time, it is considered to be unreachable. "
            "Note: This does <b>not</b> limit the time the agent needs to "
            "generate its output. "
            "This rule can be used to specify a timeout on a per-host-basis."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentCMKAgent,
        name="tcp_connect_timeouts",
        valuespec=_valuespec_tcp_connect_timeouts,
    ))


def _valuespec_agent_encryption():
    return Dictionary(
        elements=[
            ("passphrase", PasswordSpec(title=_("Encryption secret"), allow_empty=False)),
            ("use_regular",
             DropdownChoice(
                 title=_("Encryption for Agent"),
                 help=_("Choose if the agent agents encrypt packages. This controls whether "
                        "baked agents encrypt their output and whether check_mk expects "
                        "encrypted output. "
                        "Please note: If you opt to enforce encryption, "
                        "agents that don't support encryption will not work any more. "
                        "Further note: This only affects regular agents, not special agents "
                        "aka datasource programs."),
                 default_value="disable",
                 choices=[("enforce", _("Enforce (drop unencrypted data)")),
                          ("allow", _("Enable  (accept encrypted and unencrypted data)")),
                          ("disable", _("Disable (drop encrypted data)"))])),
            ("use_realtime",
             DropdownChoice(title=_("Encryption for Realtime Updates"),
                            help=_("Choose if realtime updates are sent/expected encrypted"),
                            default_value="enforce",
                            choices=[("enforce", _("Enforce (drop unencrypted data)")),
                                     ("allow",
                                      _("Enable  (accept encrypted and unencrypted data)")),
                                     ("disable", _("Disable (drop encrypted data)"))])),
        ],
        optional_keys=[],
        title=_("Encryption"),
        help=_("Control encryption of data sent from agent to host."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentCMKAgent,
        name="agent_encryption",
        valuespec=_valuespec_agent_encryption,
    ))


def _common_check_mk_exit_status_elements():
    return [
        (
            "empty_output",
            MonitoringState(default_value=2, title=_("State in case of empty output")),
        ),
        (
            "connection",
            MonitoringState(default_value=2, title=_("State in case of connection problems")),
        ),
        (
            "timeout",
            MonitoringState(default_value=2, title=_("State in case of a timeout")),
        ),
        (
            "exception",
            MonitoringState(default_value=3, title=_("State in case of unhandled exception")),
        ),
    ]


def transform_exit_code_spec(p):
    if "overall" in p:
        return p
    return {"overall": p}


def _factory_default_check_mk_exit_status():
    return {
        'connection': 2,
        'wrong_version': 1,
        'exception': 3,
        'empty_output': 2,
        'missing_sections': 1
    }


def _valuespec_check_mk_exit_status():
    return Transform(
        Dictionary(
            elements=[
                ("overall",
                 Dictionary(
                     title=_("Overall status"),
                     elements=_common_check_mk_exit_status_elements() + [
                         (
                             "wrong_version",
                             MonitoringState(default_value=1,
                                             title=_("State in case of wrong agent version")),
                         ),
                         (
                             "missing_sections",
                             MonitoringState(
                                 default_value=1,
                                 title=_("State if just <i>some</i> agent sections are missing")),
                         ),
                         (
                             "specific_missing_sections",
                             ListOf(
                                 Tuple(elements=[
                                     RegExpUnicode(help=_(
                                         'Beside of setting the generic "Missing sections" state above '
                                         'you can specify a regex pattern to match specific section names and '
                                         'give them an individual state in case they are missing. '
                                         'Note that the first match is used.'),
                                                   mode=RegExpUnicode.prefix),
                                     MonitoringState(),
                                 ],
                                       orientation="horizontal"),
                                 title=_("State if specific sections are missing"),
                             ),
                         ),
                     ])),
                ("individual",
                 Dictionary(title=_("Individual states per data source"),
                            elements=[
                                ("agent",
                                 Dictionary(
                                     title=_("Agent"),
                                     elements=_common_check_mk_exit_status_elements() + [
                                         (
                                             "wrong_version",
                                             MonitoringState(
                                                 default_value=1,
                                                 title=_("State in case of wrong agent version")),
                                         ),
                                     ])),
                                ("programs",
                                 Dictionary(title=_("Programs"),
                                            elements=_common_check_mk_exit_status_elements())),
                                ("special",
                                 Dictionary(title=_("Programs"),
                                            elements=_common_check_mk_exit_status_elements())),
                                ("snmp",
                                 Dictionary(title=_("SNMP"),
                                            elements=_common_check_mk_exit_status_elements())),
                                ("mgmt_snmp",
                                 Dictionary(title=_("SNMP Management Board"),
                                            elements=_common_check_mk_exit_status_elements())),
                                ("mgmt_ipmi",
                                 Dictionary(title=_("IPMI Management Board"),
                                            elements=_common_check_mk_exit_status_elements())),
                                ("piggyback",
                                 Dictionary(title=_("Piggyback"),
                                            elements=_common_check_mk_exit_status_elements())),
                            ])),
            ],
            optional_keys=["individual"],
        ),
        forth=transform_exit_code_spec,
        title=_("Status of the Check_MK services"),
        help=_("This ruleset specifies the total status of the Check_MK services <i>Check_MK</i>, "
               "<i>Check_MK Discovery</i> and <i>Check_MK HW/SW Inventory</i> in case of various "
               "error situations. One use case is the monitoring of hosts that are not always up. "
               "You can have Check_MK an OK status here if the host is not reachable. Note: the "
               "<i>Timeout</i> setting only works when using the Check_MK Micro Core."),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_check_mk_exit_status(),
        group=RulespecGroupAgentCMKAgent,
        match_type="dict",
        name="check_mk_exit_status",
        valuespec=_valuespec_check_mk_exit_status,
    ))


def _valuespec_check_mk_agent_target_versions():
    return Transform(
        CascadingDropdown(
            title=_("Check for correct version of Check_MK agent"),
            help=_("Here you can make sure that all of your Check_MK agents are running"
                   " one specific version. Agents running "
                   " a different version return a non-OK state."),
            choices=[
                ("ignore", _("Ignore the version")),
                ("site", _("Same version as the monitoring site")),
                ("specific", _("Specific version"), TextAscii(allow_empty=False,)),
                ("at_least", _("At least"),
                 Dictionary(elements=[
                     ('release', TextAscii(
                         title=_('Official Release version'),
                         allow_empty=False,
                     )),
                     ('daily_build', TextAscii(
                         title=_('Daily build'),
                         allow_empty=False,
                     )),
                 ])),
            ],
            default_value="ignore",
        ),
        # In the past, this was a OptionalDropdownChoice() which values could be strings:
        # ignore, site or a custom string representing a version number.
        forth=lambda x: isinstance(x, str) and x not in ["ignore", "site"] and ("specific", x) or x,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentCMKAgent,
        name="check_mk_agent_target_versions",
        valuespec=_valuespec_check_mk_agent_target_versions,
    ))


@rulespec_group_registry.register
class RulespecGroupMonitoringAgents(RulespecGroup):
    @property
    def name(self):
        return "agents"

    @property
    def title(self):
        return _("Monitoring Agents")

    @property
    def help(self):
        return _("Configuration of monitoring agents for Linux, Windows and Unix")


@rulespec_group_registry.register
class RulespecGroupMonitoringAgentsGenericOptions(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringAgents

    @property
    def sub_group_name(self):
        return "generic_options"

    @property
    def title(self):
        return _("Generic Options")


def _valuespec_agent_config_only_from():
    return ListOfStrings(
        valuespec=IPNetwork(),
        title=_("Allowed agent access via IP address"),
        help=_("This rule allows you to restrict the access to the "
               "Check_MK agent to certain IP addresses and networks. "
               "Usually you configure just the IP addresses of your "
               "Check_MK servers here. You can enter either IP addresses "
               "in the form <tt>1.2.3.4</tt> or networks in the style "
               "<tt>1.2.0.0/16</tt>. If you leave this configuration empty "
               "or create no rule then <b>all</b> addresses are allowed to "
               "access the agent. IPv6 addresses and networks are also allowed."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsGenericOptions,
        name="agent_config:only_from",
        valuespec=_valuespec_agent_config_only_from,
    ))


def _valuespec_piggyback_translation():
    return HostnameTranslation(
        title=_("Hostname translation for piggybacked hosts"),
        help=_(
            "Some agents or agent plugins send data not only for the queried host but also "
            "for other hosts &quot;piggyback&quot; with their own data. This is the case "
            "for the vSphere special agent and the SAP R/3 plugin, for example. The hostnames "
            "that these agents send must match your hostnames in your monitoring configuration. "
            "If that is not the case, then with this rule you can define a hostname translation. "
            "Note: This rule must be configured for the &quot;pig&quot; - i.e. the host that the "
            "agent is running on. It is not applied to the translated piggybacked hosts."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentGeneralSettings,
        match_type="dict",
        name="piggyback_translation",
        valuespec=_valuespec_piggyback_translation,
    ))


def _valuespec_service_description_translation():
    return ServiceDescriptionTranslation(
        title=_("Translation of service descriptions"),
        help=_(
            "Within this ruleset service descriptions can be translated similar to the ruleset "
            "<tt>Hostname translation for piggybacked hosts</tt>. Services such as "
            "<tt>Check_MK</tt>, <tt>Check_MK Agent</tt>, <tt>Check_MK Discovery</tt>, "
            "<tt>Check_MK inventory</tt>, and <tt>Check_MK HW/SW Inventory</tt> are excluded. "
            "<b>Attention:</b><ul>"
            "<li>Downtimes and other configured rules which match these "
            "services have to be adapted.</li>"
            "<li>Performance data and graphs will begin from scratch for translated services.</li>"
            "<li>Especially configured check parameters keep their functionality further on.</li>"
            "<li>This new ruleset translates also the item part of a service description. "
            "This means that after such a translation the item may be gone but is used in the "
            "conditions of the parameters further on if any parameters are configured. "
            "This might be confusing.</li></ul>"
            "This rule should only be configured in the early stages."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentGeneralSettings,
        name="service_description_translation",
        valuespec=_valuespec_service_description_translation,
    ))


def get_snmp_checktypes():
    checks = get_check_information()
    types = sorted([(cn, (c['title'] != cn and '%s: ' % cn or '') + c['title'])
                    for (cn, c) in checks.items()
                    if c['snmp']])
    return [(None, _('All SNMP Checks'))] + types


def get_snmp_section_names():
    checks = get_check_information()
    snmp_section_names = set(cn.split(".", 1)[0] for (cn, c) in checks.items() if c['snmp'])
    section_choices = [(sn, sn) for sn in snmp_section_names]
    return [(None, _('All SNMP Checks'))] + sorted(section_choices)


def _valuespec_snmp_check_interval():
    return Tuple(
        title=_('Check intervals for SNMP checks'),
        help=_('This rule can be used to customize the check interval of each SNMP based check. '
               'With this option it is possible to configure a longer check interval for specific '
               'checks, than then normal check interval.'),
        elements=[
            Transform(
                DropdownChoice(
                    title=_("Check"),
                    help=_("You can only configure \"section names\" here and not choose all "
                           "individual SNMP based checks here. It is only possible to define "
                           "SNMP check intervals for main checks and all the related sub "
                           "checks together. The reason for this is that the data of the "
                           "main check and it's sub checks is defined for the whole group "
                           "of checks in the main check and also fetched for all these "
                           "checks together."),
                    choices=get_snmp_section_names,
                ),
                # Transform check types to section names
                forth=lambda e: e.split(".")[0] if e is not None else None,
            ),
            Integer(
                title=_("Do check every"),
                unit=_("minutes"),
                min_value=1,
                default_value=1,
            ),
        ])


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentSNMP,
        name="snmp_check_interval",
        valuespec=_valuespec_snmp_check_interval,
    ))


def _valuespec_snmpv3_contexts():
    return Tuple(
        title=_('SNMPv3 contexts to use in requests'),
        help=_('By default Check_MK does not use a specific context during SNMPv3 queries, '
               'but some devices are offering their information in different SNMPv3 contexts. '
               'This rule can be used to configure, based on hosts and check type, which SNMPv3 '
               'contexts Check_MK should ask for when getting information via SNMPv3.'),
        elements=[
            DropdownChoice(
                title=_("Checktype"),
                choices=get_snmp_checktypes,
            ),
            ListOfStrings(
                title=_("SNMP Context IDs"),
                allow_empty=False,
            ),
        ])


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupAgentSNMP,
        name="snmpv3_contexts",
        valuespec=_valuespec_snmpv3_contexts,
    ))
