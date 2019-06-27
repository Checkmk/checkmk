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
"""WATO-Module for the rules and aggregations of Check_MK BI"""

import os
import pprint

import cmk
import cmk.utils.store as store

if cmk.is_managed_edition():
    import cmk.gui.cme.managed as managed
else:
    managed = None

import cmk.gui.config as config
import cmk.gui.userdb as userdb
from cmk.gui.table import table_element
import cmk.gui.forms as forms
import cmk.gui.watolib as watolib
from cmk.gui.permissions import (
    permission_registry,
    Permission,
)
from cmk.gui.exceptions import MKUserError, MKGeneralException, MKAuthException
from cmk.gui.valuespec import (
    Tuple,
    Transform,
    Percentage,
    Integer,
    Alternative,
    FixedValue,
    TextAscii,
    Dictionary,
    MonitoringState,
    IconSelector,
    ListOf,
    CascadingDropdown,
    ListOfStrings,
    Checkbox,
    TextUnicode,
    TextAreaUnicode,
    Optional,
    ID,
    DropdownChoice,
)
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML

from cmk.gui.watolib.groups import load_contact_group_information
from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
    ContactGroupSelection,
    MainMenu,
    MenuItem,
    main_module_registry,
    MainModule,
    global_buttons,
    add_change,
    wato_confirm,
    HostTagCondition,
    PermissionSectionWATO,
)

import cmk.gui.node_visualization

#   .--Base class----------------------------------------------------------.
#   |             ____                        _                            |
#   |            | __ )  __ _ ___  ___    ___| | __ _ ___ ___              |
#   |            |  _ \ / _` / __|/ _ \  / __| |/ _` / __/ __|             |
#   |            | |_) | (_| \__ \  __/ | (__| | (_| \__ \__ \             |
#   |            |____/ \__,_|___/\___|  \___|_|\__,_|___/___/             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class BIManagement(object):
    def __init__(self):
        # We need to replace the BI constants internally with something
        # that we can replace back after writing the BI-Rules out
        # with pprint.pformat
        self._bi_constants = {
            'ALL_HOSTS': 'ALL_HOSTS-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'HOST_STATE': 'HOST_STATE-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'HIDDEN': 'HIDDEN-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'FOREACH_HOST': 'FOREACH_HOST-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'FOREACH_CHILD': 'FOREACH_CHILD-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'FOREACH_CHILD_WITH': 'FOREACH_CHILD_WITH-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'FOREACH_PARENT': 'FOREACH_PARENT-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'FOREACH_SERVICE': 'FOREACH_SERVICE-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'REMAINING': 'REMAINING-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'DISABLED': 'DISABLED-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'HARD_STATES': 'HARD_STATES-f41e728b-0bce-40dc-82ea-51091d034fc3',
            'DT_AGGR_WARN': 'DT_AGGR_WARN-f41e728b-0bce-40dc-82ea-51091d034fc3',
        }
        self._load_config()

        if not config.user.may("wato.bi_admin"):
            self._user_contactgroups = userdb.contactgroups_of_user(config.user.id)
        else:
            self._user_contactgroups = None  # meaning I am admin

        # Most modes need a pack as context
        if html.request.has_var("pack"):
            self._pack_id = html.request.var("pack")
            try:
                self._pack = self._packs[self._pack_id]
            except KeyError:
                raise MKUserError("pack", _("This BI pack does not exist."))
        else:
            self._pack_id = None
            self._pack = None

    # .--------------------------------------------------------------------.
    # | Loading and saving                                                 |
    # '--------------------------------------------------------------------'

    def _load_config(self):
        filename = watolib.multisite_dir() + "bi.mk"
        try:
            vars_ = {
                "aggregation_rules": {},
                "aggregations": [],
                "host_aggregations": [],
                "bi_packs": {},
            }
            vars_.update(self._bi_constants)
            if os.path.exists(filename):
                execfile(filename, vars_, vars_)
            else:
                exec (bi_example, vars_, vars_)

            # put legacy non-pack stuff into packs
            if (vars_["aggregation_rules"] or vars_["aggregations"] or vars_["host_aggregations"]) and \
                "default" not in vars_["bi_packs"]:
                vars_["bi_packs"]["default"] = {
                    "title": _("Default Pack"),
                    "rules": vars_["aggregation_rules"],
                    "aggregations": vars_["aggregations"],
                    "host_aggregations": vars_["host_aggregations"],
                    "public": True,
                    "contact_groups": [],
                }

            self._packs = {}
            for pack_id, pack in vars_["bi_packs"].items():
                # Convert rules from old-style tuples to new-style dicts
                aggregation_rules = {}
                for ruleid, rule in pack["rules"].items():
                    aggregation_rules[ruleid] = self._convert_rule_from_bi(rule, ruleid)

                aggregations = []
                for aggregation in pack["aggregations"]:
                    aggregations.append(
                        self._convert_aggregation_from_bi(aggregation, single_host=False))
                for aggregation in pack["host_aggregations"]:
                    aggregations.append(
                        self._convert_aggregation_from_bi(aggregation, single_host=True))

                self._packs[pack_id] = {
                    "id": pack_id,
                    "title": pack["title"],
                    "rules": aggregation_rules,
                    "aggregations": aggregations,
                    "public": pack["public"],
                    "contact_groups": pack["contact_groups"],
                }

        except Exception as e:
            if config.debug:
                raise

            raise MKGeneralException(_("Cannot read configuration file %s: %s") % (filename, e))

    def save_config(self):
        output = self.generate_bi_config_file_content(self._packs)
        store.mkdir(watolib.multisite_dir())
        store.save_file(watolib.multisite_dir() + "bi.mk", output)

    def generate_bi_config_file_content(self, packs):
        output = watolib.wato_fileheader()
        for pack_id, pack in sorted(packs.items()):
            converted_pack = self._convert_pack_to_bi(pack)
            output += "bi_packs[%r] = %s\n\n" % (
                pack_id, self._replace_bi_constants(pprint.pformat(converted_pack, width=50)))
        return output

    def _convert_pack_to_bi(self, pack):
        converted_rules = dict([
            (rule_id, self._convert_rule_to_bi(rule)) for (rule_id, rule) in pack["rules"].items()
        ])
        converted_aggregations = []
        converted_host_aggregations = []
        for aggregation in pack["aggregations"]:
            if aggregation["single_host"]:
                append_to = converted_host_aggregations
            else:
                append_to = converted_aggregations
            append_to.append(self._convert_aggregation_to_bi(aggregation))

        converted_pack = pack.copy()
        converted_pack["aggregations"] = converted_aggregations
        converted_pack["host_aggregations"] = converted_host_aggregations
        converted_pack["rules"] = converted_rules
        return converted_pack

    def _replace_bi_constants(self, s):
        for name, uuid in self._bi_constants.items():
            while True:
                n = s.replace("'%s'" % uuid, name)
                if n != s:
                    s = n
                else:
                    break
        return s[0] + '\n ' + s[1:-1] + '\n' + s[-1]

    def _convert_aggregation_to_bi(self, aggr):
        node = self._convert_node_to_bi(aggr["node"])
        option_keys = [
            ("id", ""),
            ("use_layout_id", ""),
            ("hard_states", False),
            ("downtime_aggr_warn", False),
            ("disabled", False),
        ]

        if cmk.is_managed_edition():
            option_keys.append(("customer", managed.default_customer_id()))

        # Create dict with all aggregation options
        options = {}
        for option, default_value in option_keys:
            options[option] = aggr.get(option, default_value)

        return (options, self._convert_aggregation_groups(aggr["groups"])) + node

    def _convert_node_to_bi(self, node):
        if node[0] == "call":
            return node[1]
        elif node[0] == "host":
            return (node[1][0], self._bi_constants['HOST_STATE'])
        elif node[0] == "remaining":
            return (node[1][0], self._bi_constants['REMAINING'])
        elif node[0] == "service":
            return node[1]
        elif node[0] == "foreach_host":
            what = node[1][0]

            tags = node[1][1]
            if node[1][2]:
                hostspec = node[1][2]
            else:
                hostspec = self._bi_constants['ALL_HOSTS']

            if type(what == tuple) and what[0] == 'child_with':
                child_conditions = what[1]
                what = what[0]
                child_tags = child_conditions[0]
                child_hostspec = child_conditions[1] if child_conditions[1] else self._bi_constants[
                    'ALL_HOSTS']
                return (self._bi_constants["FOREACH_" + what.upper()], child_tags, child_hostspec, tags, hostspec) \
                       + self._convert_node_to_bi(node[1][3])
            return (self._bi_constants["FOREACH_" + what.upper()], tags,
                    hostspec) + self._convert_node_to_bi(node[1][3])
        elif node[0] == "foreach_service":
            tags = node[1][0]
            if node[1][1]:
                spec = node[1][1]
            else:
                spec = self._bi_constants['ALL_HOSTS']
            service = node[1][2]
            return (self._bi_constants["FOREACH_SERVICE"], tags, spec,
                    service) + self._convert_node_to_bi(node[1][3])

    def _convert_aggregation_from_bi(self, aggr, single_host):
        if isinstance(aggr[0], dict):
            options = aggr[0]
            aggr = aggr[1:]
        else:
            # Legacy configuration
            options = {}
            options["id"] = ""
            options["use_layout"] = ""
            if aggr[0] == self._bi_constants["DISABLED"]:
                options["disabled"] = True
                aggr = aggr[1:]
            else:
                options["disabled"] = False

            if aggr[0] == self._bi_constants["DT_AGGR_WARN"]:
                options["downtime_aggr_warn"] = True
                aggr = aggr[1:]
            else:
                options["downtime_aggr_warn"] = False

            if aggr[0] == self._bi_constants["HARD_STATES"]:
                options["hard_states"] = True
                aggr = aggr[1:]
            else:
                options["hard_states"] = False

        node = self._convert_node_from_bi(aggr[1:])
        aggr_dict = {
            "groups": self._convert_aggregation_groups(aggr[0]),
            "node": node,
            "single_host": single_host,
        }
        aggr_dict.update(options)
        return aggr_dict

    def _convert_aggregation_groups(self, old_groups):
        if isinstance(old_groups, list):
            return old_groups
        return [old_groups]

    # Make some conversions so that the format of the
    # valuespecs is matched
    def _convert_rule_from_bi(self, rule, ruleid):
        def tryint(x):
            try:
                return int(x)
            except:
                return x

        if isinstance(rule, tuple):
            rule = {
                "title": rule[0],
                "params": rule[1],
                "aggregation": rule[2],
                "nodes": rule[3],
            }
        crule = {}
        crule.update(rule)
        crule["nodes"] = map(self._convert_node_from_bi, rule["nodes"])
        parts = rule["aggregation"].split("!")
        crule["aggregation"] = (parts[0], tuple(map(tryint, parts[1:])))
        crule["id"] = ruleid
        return crule

    def _convert_rule_to_bi(self, rule):
        brule = {}
        brule.update(rule)
        if "id" in brule:
            del brule["id"]
        brule["nodes"] = map(self._convert_node_to_bi, rule["nodes"])
        brule["aggregation"] = "!".join([rule["aggregation"][0]] + map(str, rule["aggregation"][1]))
        return brule

    # Convert node-Tuple into format used by CascadingDropdown
    def _convert_node_from_bi(self, node):
        if len(node) == 2:
            if isinstance(node[1], list):
                return ("call", node)
            elif node[1] == self._bi_constants['HOST_STATE']:
                return ("host", (node[0],))
            elif node[1] == self._bi_constants['REMAINING']:
                return ("remaining", (node[0],))
            return ("service", node)

        else:  # FOREACH_...

            foreach_spec = node[0]
            if foreach_spec == self._bi_constants['FOREACH_CHILD_WITH']:
                # extract the conditions meant for matching the childs
                child_conditions = list(node[1:3])
                if child_conditions[1] == self._bi_constants['ALL_HOSTS']:
                    child_conditions[1] = None
                node = node[0:1] + node[3:]

            # Extract the list of tags
            if isinstance(node[1], list):
                tags = node[1]
                node = node[0:1] + node[2:]
            else:
                tags = []

            hostspec = node[1]
            if hostspec == self._bi_constants['ALL_HOSTS']:
                hostspec = None

            if foreach_spec == self._bi_constants['FOREACH_SERVICE']:
                service = node[2]
                subnode = self._convert_node_from_bi(node[3:])
                return ("foreach_service", (tags, hostspec, service, subnode))
            else:

                subnode = self._convert_node_from_bi(node[2:])
                if foreach_spec == self._bi_constants['FOREACH_HOST']:
                    what = "host"
                elif foreach_spec == self._bi_constants['FOREACH_CHILD']:
                    what = "child"
                elif foreach_spec == self._bi_constants['FOREACH_CHILD_WITH']:
                    what = ("child_with", child_conditions)
                elif foreach_spec == self._bi_constants['FOREACH_PARENT']:
                    what = "parent"
                return ("foreach_host", (what, tags, hostspec, subnode))

    def get_packs(self):
        return self._packs

    def find_aggregation_rule_usages(self):
        aggregations_that_use_rule = {}
        for pack_id, pack in self._packs.iteritems():
            for aggr_id, aggregation in enumerate(pack["aggregations"]):
                rule_id, _description = self.rule_called_by_node(aggregation["node"])
                aggregations_that_use_rule.setdefault(rule_id, []).append((pack_id, aggr_id,
                                                                           aggregation))
                sub_rule_ids = self._aggregation_recursive_sub_rule_ids(rule_id)
                for sub_rule_id in sub_rule_ids:
                    aggregations_that_use_rule.setdefault(sub_rule_id, []).append((pack_id, aggr_id,
                                                                                   aggregation))
        return aggregations_that_use_rule

    def _aggregation_recursive_sub_rule_ids(self, ruleid):
        rule = self.find_rule_by_id(ruleid)
        if not rule:
            return []

        sub_rule_ids = self.aggregation_sub_rule_ids(rule)
        if not sub_rule_ids:
            return []

        result = sub_rule_ids[:]
        for sub_rule_id in sub_rule_ids:
            result += self._aggregation_recursive_sub_rule_ids(sub_rule_id)
        return result

    def find_rule_by_id(self, ruleid):
        pack = self.pack_containing_rule(ruleid)
        if pack:
            return pack["rules"][ruleid]

    def pack_containing_rule(self, ruleid):
        for pack in self._packs.values():
            if ruleid in pack["rules"]:
                return pack
        return None

    def aggregation_sub_rule_ids(self, rule):
        sub_rule_ids = []
        for node in rule["nodes"]:
            r = self.rule_called_by_node(node)
            if r:
                sub_rule_ids.append(r[0])
        return sub_rule_ids

    def rule_called_by_node(self, node):
        """Returns the rule called by a node - if any
        Result is a pair of the rule and a descriptive title"""
        if node[0] == "call":
            if node[1][1]:
                args = _("with arguments: %s") % ", ".join(node[1][1])
            else:
                args = _("without arguments")
            return node[1][0], _("Explicit call ") + args
        elif node[0] == "foreach_host":
            subnode = node[1][-1]
            if subnode[0] == 'call':
                if node[1][0] == 'host':
                    info = _("Called for each host...")
                elif node[1][0] == 'child':
                    info = _("Called for each child of...")
                else:
                    info = _("Called for each parent of...")
                return subnode[1][0], info
        elif node[0] == "foreach_service":
            subnode = node[1][-1]
            if subnode[0] == 'call':
                return subnode[1][0], _("Called for each service...")


# TODO: Rename to BIMode
class ModeBI(WatoMode, BIManagement):

    # .--------------------------------------------------------------------.
    # | Initialization and default modes                                   |
    # '--------------------------------------------------------------------'
    def __init__(self):
        super(ModeBI, self).__init__()
        self._create_valuespecs()

    def title(self):
        title = _("Business Intelligence")
        if self._pack:
            title += " - " + html.attrencode(self._pack["title"])
        return title

    def buttons(self):
        global_buttons()
        if self._pack:
            html.context_button(
                _("All Packs"), html.makeuri_contextless([("mode", "bi_packs")]), "back")

    def _add_change(self, action_name, text):
        site_ids = [site[0] for site in config.wato_slave_sites()] + [config.omd_site()]
        add_change(action_name, text, domains=[watolib.ConfigDomainGUI], sites=site_ids)

    # .--------------------------------------------------------------------.
    # | Valuespecs                                                         |
    # '--------------------------------------------------------------------'

    # FIXME TODO self._vs_call_rule etc. refactor to properties
    def _create_valuespecs(self):
        self._vs_call_rule = self._get_vs_call_rule()
        self._vs_host_re = self._get_vs_host_re()
        self._vs_node = self._get_vs_node()
        self._vs_aggregation = self._get_vs_aggregation()

    def _allowed_rule_choices(self):
        choices = []
        for pack_id, pack in sorted(self._packs.iteritems()):
            if self.may_use_rules_in_pack(pack):
                pack_choices = [(rule_id, "%s (%s)" % (rule["title"], rule["id"]))
                                for rule_id, rule in pack["rules"].iteritems()]
                choices.append((pack_id, "%s (%s)" % (pack["title"], pack["id"]),
                                DropdownChoice(choices=sorted(pack_choices))))
        return choices

    def may_use_rules_in_pack(self, pack):
        return pack["public"] or self.is_contact_for_pack(pack)

    def is_contact_for_pack(self, pack=None):
        if self._user_contactgroups is None:
            return True  # I am BI admin

        if pack is None:
            pack = self._pack

        for group in self._user_contactgroups:
            if group in pack["contact_groups"]:
                return True
        return False

    def must_be_contact_for_pack(self, pack=None):
        if not self.is_contact_for_pack(pack=pack):
            if pack is None:
                pack_title = self._pack["title"]
            else:
                pack_title = pack["title"]
            raise MKAuthException(
                _("You have no permission for changes in this BI pack %s.") % pack_title)

    def _validate_rule_call(self, value, varprefix):
        rule_id, arguments = value
        rule = self.find_rule_by_id(rule_id)
        rule_params = rule['params']

        if len(arguments) != len(rule_params):
            raise MKUserError(
                varprefix + "_1_0",
                _("The rule you selected needs %d argument(s) (%s), "
                  "but you configured %d arguments.") % (len(rule_params), ', '.join(rule_params),
                                                         len(arguments)))

    def _get_vs_call_rule(self):
        return Tuple(
            elements=[
                Transform(
                    CascadingDropdown(
                        title=_("Rule:"),
                        orientation="horizontal",
                        choices=self._allowed_rule_choices(),
                        sorted=True,
                    ),
                    back=self._transform_back_vs_call_rule,
                    forth=self._transform_forth_vs_call_rule,
                ),
                ListOfStrings(
                    orientation="horizontal",
                    size=80,
                    title=_("Arguments:"),
                ),
            ],
            validate=self._validate_rule_call,
        )

    def _transform_back_vs_call_rule(self, choice):
        return choice[1]

    def _transform_forth_vs_call_rule(self, choice):
        pack = self.pack_containing_rule(choice)
        if pack:
            return (pack['id'], choice)
        return None

    def _get_vs_host_re(self):
        host_re_help = _(
            "Either an exact host name or a regular expression exactly matching the host "
            "name. Example: <tt>srv.*p</tt> will match <tt>srv4711p</tt> but not <tt>xsrv4711p2</tt>. "
        )
        return TextUnicode(
            title=_("Host:"),
            help=host_re_help,
            allow_empty=False,
        )

    def _node_call_choices(self):
        # Configuration of explicit rule call
        return [
            ("call", _("Call a Rule"), self._vs_call_rule),
        ]

    def _host_valuespec(self, title):
        return Alternative(
            title=title,
            style="dropdown",
            elements=[
                FixedValue(
                    None,
                    title=_("All Hosts"),
                    totext="",
                ),
                TextAscii(title=_("Regex for host name"), size=60),
                Tuple(
                    title=_("Regex for host alias"),
                    elements=[
                        FixedValue(
                            "alias",
                            totext="",
                        ),
                        TextAscii(size=60,),
                    ],
                ),
            ],
            help=_("If you choose \"Regex for host name\" or \"Regex for host alias\", "
                   "you need to provide a regex which results in exactly one match group."),
            default_value=None,
        )

    # Configuration of FOREACH_...-type nodes
    def _foreach_choices(self, subnode_choices):
        return [
            ("foreach_host", _("Create nodes based on a host search"),
             Tuple(elements=[
                 CascadingDropdown(
                     title=_("Refer to:"),
                     choices=[
                         ('host', _("The found hosts themselves")),
                         ('child', _("The found hosts' childs")),
                         ('child_with', _("The found hosts' childs (with child filtering)"),
                          Tuple(elements=[
                              HostTagCondition(title=_("Child Host Tags:")),
                              self._host_valuespec(_("Child host name:")),
                          ])),
                         ('parent', _("The found hosts' parents")),
                     ],
                     help=_(
                         'When selecting <i>The found hosts\' childs</i>, the conditions '
                         '(tags and host name) are used to match a host, but you will get one '
                         'node created for each child of the matched host. The '
                         'place holder <tt>$HOSTNAME$</tt> contains the name of the found child '
                         'and the place holder <tt>$HOSTALIAS$</tt> contains it\'s alias.<br><br>'
                         'When selecting <i>The found hosts\' parents</i>, the conditions '
                         '(tags and host name) are used to match a host, but you will get one '
                         'node created for each of the parent hosts of the matched host. '
                         'The place holder <tt>$HOSTNAME$</tt> contains the name of the child '
                         'host and <tt>$2$</tt> the name of the parent host.'),
                 ),
                 HostTagCondition(title=_("Host Tags:")),
                 self._host_valuespec(_("Host name:")),
                 CascadingDropdown(
                     title=_("Nodes to create:"),
                     help=_("When calling a rule you can use the place holder "
                            "<tt>$HOSTNAME$</tt> in the rule arguments. It will be replaced "
                            "by the actual host names found by the search - one host name "
                            "for each rule call. Use <tt>$HOSTALIAS$</tt> to get the alias of"
                            " the matched host."),
                     choices=subnode_choices,
                 ),
             ])),
            ("foreach_service", _("Create nodes based on a service search"),
             Tuple(elements=[
                 HostTagCondition(title=_("Host Tags:")),
                 self._host_valuespec(_("Host name:")),
                 TextAscii(
                     title=_("Service Regex:"),
                     help=_(
                         "Subexpressions enclosed in <tt>(</tt> and <tt>)</tt> will be available "
                         "as arguments <tt>$2$</tt>, <tt>$3$</tt>, etc."),
                     size=80,
                 ),
                 CascadingDropdown(
                     title=_("Nodes to create:"),
                     help=_("When calling a rule you can use the place holder <tt>$HOSTNAME$</tt> "
                            "in the rule arguments. It will be replaced by the actual host "
                            "names found by the search - one host name for each rule call. "
                            "Use <tt>$HOSTALIAS$</tt> to get the alias of the matched host. "
                            "If you have regular expression subgroups in the service pattern, then "
                            "the place holders <tt>$2$</tt> will represent the first group match, "
                            "<tt>$3</tt> the second, and so on..."),
                     choices=subnode_choices,
                 ),
             ]))
        ]

    def _get_vs_node(self):
        # Configuration of leaf nodes
        vs_node_simplechoices = [
            ("host", _("State of a host"),
             Tuple(
                 help=_("Will create child nodes representing the state of hosts (usually the "
                        "host check is done via ping)."),
                 elements=[self._vs_host_re])),
            ("service", _("State of a service"),
             Tuple(
                 help=_("Will create child nodes representing the state of services."),
                 elements=[
                     self._vs_host_re,
                     TextUnicode(
                         title=_("Service:"),
                         help=_(
                             "A regular expression matching the <b>beginning</b> of a service "
                             "description. You can use a trailing <tt>$</tt> in order to define an "
                             "exact match. For each matching service on the specified hosts one child "
                             "node will be created. "),
                         size=80,
                     ),
                 ])),
            ("remaining", _("State of remaining services"),
             Tuple(
                 help=_("Create a child node for each service on the specified hosts that is not "
                        "contained in any other node of the aggregation."),
                 elements=[self._vs_host_re],
             )),
        ]

        return CascadingDropdown(
            choices=vs_node_simplechoices + self._node_call_choices() +
            self._foreach_choices(vs_node_simplechoices + self._node_call_choices()))

    def _aggregation_choices(self):
        choices = []
        for aid, ainfo in bi_aggregation_functions.items():
            choices.append((
                aid,
                ainfo["title"],
                ainfo["valuespec"],
            ))
        return choices

    def _get_vs_aggregation(self):
        def transform_aggregation_groups_to_gui(groups):
            if not isinstance(groups, list):
                groups = [groups]
            new = []
            for group in groups:
                if "/" in group:
                    new.append(group.split("/"))
                else:
                    new.append(group)
            return new

        def transform_aggregation_groups_to_disk(groups):
            new = []
            for group in groups:
                if isinstance(group, list):
                    new.append("/".join(group))
                else:
                    new.append(group)
            return new

        if cmk.is_managed_edition():
            cme_elements = managed.customer_choice_element()
        else:
            cme_elements = []

        visualization_choices = []
        visualization_choices.append((None, _("Use default layout")))
        templates = cmk.gui.node_visualization.BILayoutManagement.get_all_bi_template_layouts()
        for template_id in sorted(templates.keys()):
            visualization_choices.append((template_id, template_id))

        return Dictionary(
            title=_("Aggregation Properties"),
            optional_keys=False,
            render="form",
            elements=cme_elements + [
                #              ("id",
                #              TextAscii(
                #                  title=_("Aggregation ID"),
                #                  help=_(
                #                      "The ID of the aggregation must be a unique text. It will be as unique ID."),
                #                  allow_empty=False,
                #                  size=80,
                #              )),
                ("groups",
                 Transform(
                     ListOf(
                         Alternative(
                             style="dropdown",
                             orientation="horizontal",
                             elements=[
                                 TextUnicode(title=_("Group name")),
                                 ListOfStrings(
                                     title=_("Group path"), orientation="horizontal",
                                     separator="/"),
                             ],
                         ),
                         title=_("Aggregation Groups")),
                     back=transform_aggregation_groups_to_disk,
                     forth=transform_aggregation_groups_to_gui,
                 )),
                ("node",
                 CascadingDropdown(
                     title=_("Rule to call"),
                     choices=self._node_call_choices() + self._foreach_choices(
                         self._node_call_choices()))),
                ("disabled",
                 Checkbox(
                     title=_("Disabled"),
                     label=_("Currently disable this aggregation"),
                 )),
                ("hard_states",
                 Checkbox(
                     title=_("Use Hard States"),
                     label=_("Base state computation on hard states"),
                     help=
                     _("Hard states can only differ from soft states if at least one host or service "
                       "of the BI aggregate has more than 1 maximum check attempt. For example if you "
                       "set the maximum check attempts of a service to 3 and the service is CRIT "
                       "just since one check then it's soft state is CRIT, but its hard state is still OK. "
                       "<b>Note:</b> When computing the availbility of a BI aggregate this option "
                       "has no impact. For that purpose always the soft (i.e. real) states will be used."
                      ),
                 )),
                ("downtime_aggr_warn",
                 Checkbox(
                     title=_("Aggregation of Downtimes"),
                     label=_("Escalate downtimes based on aggregated WARN state"),
                     help=
                     _("When computing the state 'in scheduled downtime' for an aggregate "
                       "first all leaf nodes that are within downtime are assumed CRIT and all others "
                       "OK. Then each aggregated node is assumed to be in downtime if the state "
                       "is CRIT under this assumption. You can change this to WARN. The influence of "
                       "this setting is especially relevant if you use aggregation functions of type <i>count</i> "
                       "and want the downtime information also escalated in case such a node would go into "
                       "WARN state."),
                 )),
                (
                    "single_host",
                    Checkbox(
                        title=_("Optimization"),
                        label=_("The aggregation covers data from only one host and its parents."),
                        help=_(
                            "If you have a large number of aggregations that cover only one host and "
                            "maybe its parents (such as Check_MK cluster hosts), "
                            "then please enable this optimization. It reduces the time for the "
                            "computation. Do <b>not</b> enable this for aggregations that contain "
                            "data of more than one host!"),
                    ),
                ),
                ("use_layout_id",
                 DropdownChoice(
                     title=_("Use visualization layout"),
                     choices=visualization_choices,
                     default_value=None))
            ])

    # .--------------------------------------------------------------------.
    # | Methods for analysing the rules and aggregations                   |
    # '--------------------------------------------------------------------'

    def aggregation_title(self, aggregation):
        rule = self.aggregation_toplevel_rule(aggregation)
        return "%s (%s)" % (rule["title"], rule["id"])

    def aggregation_toplevel_rule(self, aggregation):
        rule_id, _description = self.rule_called_by_node(aggregation["node"])
        return self.find_rule_by_id(rule_id)

    def have_rules(self):
        for pack in self._packs.values():
            if pack["rules"]:
                return True
        return False

    # Checks if the rule 'rule' uses either directly
    # or indirectly the rule with the id 'ruleid'. In
    # case of success, returns the nesting level
    def rule_uses_rule(self, rule, ruleid, level=0):
        for node in rule["nodes"]:
            r = self.rule_called_by_node(node)
            if r:
                ru_id, _info = r
                if ru_id == ruleid:  # Rule is directly being used
                    return level + 1
                # Check if lower rules use it
                else:
                    subrule = self.find_rule_by_id(ru_id)
                    l = self.rule_uses_rule(subrule, ruleid, level + 1)
                    if l:
                        return l
        return False

    def count_rule_references(self, ruleid):
        aggr_refs = 0
        for pack in self._packs.values():
            for aggregation in pack["aggregations"]:
                called_rule_id, _info = self.rule_called_by_node(aggregation["node"])
                if called_rule_id == ruleid:
                    aggr_refs += 1

        level = 0
        rule_refs = 0
        for pack in self._packs.values():
            for rule in pack["rules"].itervalues():
                l = self.rule_uses_rule(rule, ruleid)
                level = max(l, level)
                if l == 1:
                    rule_refs += 1

        return aggr_refs, rule_refs, level

    # .--------------------------------------------------------------------.
    # | Generic rendering                                                  |
    # '--------------------------------------------------------------------'

    def url_to_pack(self, addvars):
        return html.makeuri_contextless(addvars + [("pack", self._pack_id)])

    def render_rule_tree(self, ruleid, tree_path, tree_prefix=""):
        pack = self.pack_containing_rule(ruleid)
        rule = pack["rules"][ruleid]
        edit_url = html.makeuri_contextless([("mode", "bi_edit_rule"), ("id", ruleid),
                                             ("pack", pack["id"])])
        title = "%s (%s)" % (rule["title"], ruleid)

        sub_rule_ids = self.aggregation_sub_rule_ids(rule)
        if not sub_rule_ids:
            html.open_li()
            html.open_a(href=edit_url)
            html.write_text(title)
            html.close_a()
            html.close_li()
        else:
            html.begin_foldable_container(
                "bi_rule_trees",
                "%s%s" % (tree_prefix, tree_path),
                False,
                title,
                title_url=edit_url,
                tree_img="tree_black")
            for sub_rule_id in sub_rule_ids:
                self.render_rule_tree(sub_rule_id, tree_path + "/" + sub_rule_id, tree_prefix)
            html.end_foldable_container()

    # .--------------------------------------------------------------------.
    # | Some helper                                                        |
    # '--------------------------------------------------------------------'

    def _get_selection(self, _type):
        checkbox_name = "_c_%s_" % _type
        return [varname.split(checkbox_name)[-1] \
                for varname, _value in html.request.itervars(prefix=checkbox_name)
                if html.get_checkbox(varname)]


#.
#   .--Packs---------------------------------------------------------------.
#   |                      ____            _                               |
#   |                     |  _ \ __ _  ___| | _____                        |
#   |                     | |_) / _` |/ __| |/ / __|                       |
#   |                     |  __/ (_| | (__|   <\__ \                       |
#   |                     |_|   \__,_|\___|_|\_\___/                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeBIPacks(ModeBI):
    @classmethod
    def name(cls):
        return "bi_packs"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    def __init__(self):
        ModeBI.__init__(self)
        self._contact_group_names = load_contact_group_information()

    def buttons(self):
        ModeBI.buttons(self)
        if config.user.may("wato.bi_admin"):
            html.context_button(
                _("New BI Pack"), html.makeuri_contextless([("mode", "bi_edit_pack")]), "new")

    def action(self):
        if config.user.may("wato.bi_admin") and html.request.has_var("_delete"):
            pack_id = html.request.var("_delete")
            try:
                pack = self._packs[pack_id]
            except KeyError:
                raise MKUserError("_delete", _("This BI pack does not exist."))

            if pack["rules"]:
                raise MKUserError(
                    None,
                    _("You cannot delete this pack. It contains <b>%d</b> rules.") % len(
                        pack["rules"]))
            c = wato_confirm(
                _("Confirm BI pack deletion"),
                _("Do you really want to delete the BI pack <b>%s</b> <i>%s</i> with <b>%d</b> rules and <b>%d</b> aggregations?"
                 ) % (pack_id, pack["title"], len(pack["rules"]), len(pack["aggregations"])))
            if c:
                self._add_change("delete-bi-pack", _("Deleted BI pack %s") % pack_id)
                del self._packs[pack_id]
                self.save_config()
            elif c is False:
                return ""

    def page(self):
        with table_element(title=_("BI Configuration Packs")) as table:
            for pack_id, pack in sorted(self._packs.items()):
                if not self.may_use_rules_in_pack(pack):
                    continue

                table.row()
                table.cell(_("Actions"), css="buttons")
                if config.user.may("wato.bi_admin"):
                    edit_url = html.makeuri_contextless([("mode", "bi_edit_pack"), ("pack",
                                                                                    pack_id)])
                    html.icon_button(edit_url, _("Edit properties of this BI pack"), "edit")
                    delete_url = html.makeactionuri([("_delete", pack_id)])
                    html.icon_button(delete_url, _("Delete this BI pack"), "delete")
                rules_url = html.makeuri_contextless([("mode", "bi_rules"), ("pack", pack_id)])
                html.icon_button(rules_url,
                                 _("View and edit the rules and aggregations in this BI pack"),
                                 "bi_rules")
                table.text_cell(_("ID"), pack_id)
                table.text_cell(_("Title"), pack["title"])
                table.text_cell(_("Public"), pack["public"] and _("Yes") or _("No"))
                table.text_cell(_("Aggregations"), len(pack["aggregations"]), css="number")
                table.text_cell(_("Rules"), len(pack["rules"]), css="number")
                table.text_cell(
                    _("Contact groups"),
                    HTML(", ").join(map(self._render_contact_group, pack["contact_groups"])))

    def _render_contact_group(self, c):
        display_name = self._contact_group_names.get(c, {'alias': c})['alias']
        return html.render_a(display_name, "wato.py?mode=edit_contact_group&edit=%s" % c)


#.
#   .--Edit Pack-----------------------------------------------------------.
#   |               _____    _ _ _     ____            _                   |
#   |              | ____|__| (_) |_  |  _ \ __ _  ___| | __               |
#   |              |  _| / _` | | __| | |_) / _` |/ __| |/ /               |
#   |              | |__| (_| | | |_  |  __/ (_| | (__|   <                |
#   |              |_____\__,_|_|\__| |_|   \__,_|\___|_|\_\               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeBIEditPack(ModeBI):
    @classmethod
    def name(cls):
        return "bi_edit_pack"

    @classmethod
    def permissions(cls):
        return ["bi_rules", "bi_admin"]

    def title(self):
        if self._pack:
            return ModeBI.title(self) + " - " + _("Edit BI Pack %s") % self._pack["title"]
        return ModeBI.title(self) + " - " + _("Create New BI Pack")

    def action(self):
        if html.check_transaction():
            new_pack = self._vs_pack().from_html_vars("bi_pack")
            self._vs_pack().validate_value(new_pack, 'bi_pack')
            if self._pack:
                self._add_change("bi-edit-pack", _("Modified BI pack %s") % self._pack_id)
                new_pack["rules"] = self._pack["rules"]
                new_pack["aggregations"] = self._pack["aggregations"]
                new_pack["id"] = self._pack_id
            else:
                if new_pack["id"] in self._packs:
                    raise MKUserError("pack_id", _("A BI pack with this ID already exists."))
                self._add_change("bi-new-pack", _("Created new BI pack %s") % new_pack["id"])
                new_pack["rules"] = {}
                new_pack["aggregations"] = []
            self._packs[new_pack["id"]] = new_pack
            self.save_config()

        return "bi_packs"

    def buttons(self):
        html.context_button(_("Abort"), html.makeuri([("mode", "bi_packs")]), "abort")

    def page(self):
        html.begin_form("bi_pack", method="POST")
        self._vs_pack().render_input("bi_pack", self._pack)
        forms.end()
        html.hidden_fields()
        html.button("_save", self._pack and _("Save") or _("Create"), "submit")
        if self._pack:
            html.set_focus("bi_pack_p_title")
        else:
            html.set_focus("bi_pack_p_id")
        html.end_form()

    def _vs_pack(self):
        if self._pack:
            id_element = FixedValue(title=_("Pack ID"), value=self._pack_id)
        else:
            id_element = ID(
                title=_("BI pack ID"),
                help=_("A unique ID of this BI pack."),
                allow_empty=False,
                size=24,
            )
        return Dictionary(
            title=_("BI Pack Properties"),
            optional_keys=False,
            render="form",
            elements=
            [("id", id_element),
             ("title",
              TextUnicode(
                  title=_("Title"),
                  help=_("A descriptive title for this rule pack"),
                  allow_empty=False,
                  size=64,
              )),
             ("contact_groups",
              ListOf(
                  ContactGroupSelection(),
                  title=_("Permitted Contact Groups"),
                  help=_(
                      "The rules and aggregations in this pack can be edited by all members of the "
                      "contact groups specified here - even if they have no administrator priviledges."
                  ),
                  movable=False,
                  add_label=_("Add Contact Group"),
              )),
             ("public",
              Checkbox(
                  title=_("Public"),
                  label=_("Allow all users to refer to rules contained in this pack"),
                  help=_("Without this option users can only use rules if they have administrator "
                         "priviledges or are member of the listed contact groups."),
              ))],
        )


#.
#   .--Aggregations--------------------------------------------------------.
#   |       _                                    _   _                     |
#   |      / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __  ___     |
#   |     / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \/ __|    |
#   |    / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | \__ \    |
#   |   /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|___/    |
#   |           |___/ |___/          |___/                                 |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeBIAggregations(ModeBI):
    @classmethod
    def name(cls):
        return "bi_aggregations"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    def title(self):
        return ModeBI.title(self) + " - " + _("Aggregations")

    def buttons(self):
        ModeBI.buttons(self)
        html.context_button(_("Rules"), self.url_to_pack([("mode", "bi_rules")]), "aggr")
        if self.have_rules() and self.is_contact_for_pack():
            html.context_button(
                _("New Aggregation"), self.url_to_pack([("mode", "bi_edit_aggregation")]), "new")

    def action(self):
        self.must_be_contact_for_pack()

        if html.request.var("_del_aggr"):
            return self._delete_after_confirm()

        elif html.request.var("_bulk_delete_bi_aggregations"):
            return self._bulk_delete_after_confirm()

        elif html.request.var("_bulk_move_bi_aggregations"):
            return self._bulk_move_after_confirm()

    def _delete_after_confirm(self):
        aggregation_id = html.get_integer_input("_del_aggr")
        c = wato_confirm(
            _("Confirm aggregation deletion"),
            _("Do you really want to delete the aggregation number <b>%s</b>?") %
            (aggregation_id + 1))
        if c:
            del self._pack["aggregations"][aggregation_id]
            self._add_change("bi-delete-aggregation",
                             _("Deleted BI aggregation number %d") % (aggregation_id + 1))
            self.save_config()
        elif c is False:  # not yet confirmed
            return ""

    def _bulk_delete_after_confirm(self):
        selection = sorted(map(int, self._get_selection("aggregation")))
        if selection:
            c = wato_confirm(_("Confirm deletion of %d aggregations") % \
                               len(selection),
                             _("Do you really want to delete %d aggregations?") % \
                               len(selection))
            if c:
                for aggregation_id in selection[::-1]:
                    del self._pack["aggregations"][aggregation_id]
                    self._add_change("bi-delete-aggregation",
                                     _("Deleted BI aggregation with ID %s") % (aggregation_id + 1))
                self.save_config()

            elif c is False:
                return ""

    def _bulk_move_after_confirm(self):
        target = None
        if html.request.has_var('bulk_moveto'):
            target = html.request.var('bulk_moveto', '')
            html.javascript('cmk.selection.update_bulk_moveto("%s")' % target)

        target_pack = None
        if target in self._packs:
            target_pack = self._packs[target]
            self.must_be_contact_for_pack(target_pack)

        selection = map(int, self._get_selection("aggregation"))
        if selection and target_pack is not None:
            c = wato_confirm(_("Confirm moving of %d aggregations to %s") % \
                              (len(selection), target_pack['title']),
                             _("Do you really want to move %d aggregations to %s?") % \
                              (len(selection), target_pack['title']))
            if c:
                for aggregation_id in selection[::-1]:
                    aggregation = self._pack["aggregations"][aggregation_id]
                    target_pack["aggregations"].append(aggregation)
                    del self._pack["aggregations"][aggregation_id]
                    self._add_change("bi-move-aggregation",
                                   _("Moved BI aggregation with ID %s to BI pack %s") % \
                                    (aggregation_id+1, target))
                self.save_config()
            elif c is False:
                return ""

    def page(self):
        html.begin_form("bulk_delete_form", method="POST")
        self._render_aggregations()
        html.hidden_fields()
        if self._pack["aggregations"]:
            fieldstyle = "margin-top:10px"
            html.button(
                "_bulk_delete_bi_aggregations", _("Bulk delete"), "submit", style=fieldstyle)

            move_choices = [(pack_id, attrs["title"])
                            for pack_id, attrs in self._packs.items()
                            if pack_id is not self._pack["id"] and self.is_contact_for_pack(attrs)]

            if move_choices:
                html.button(
                    "_bulk_move_bi_aggregations", _("Bulk move"), "submit", style=fieldstyle)

                if html.request.has_var('bulk_moveto'):
                    html.javascript('cmk.selection.update_bulk_moveto("%s")' % html.request.var(
                        'bulk_moveto', ''))

                html.select(
                    "bulk_moveto",
                    move_choices,
                    "@",
                    onchange="cmk.selection.update_bulk_moveto(this.value)",
                    attrs={
                        'class': 'bulk_moveto',
                        'style': fieldstyle
                    })
        html.end_form()

    def _render_aggregations(self):
        with table_element("bi_aggr", _("Aggregations")) as table:
            for aggregation_id, aggregation in enumerate(self._pack["aggregations"]):
                table.row()
                table.cell(
                    html.render_input(
                        "_toggle_group",
                        type_="button",
                        class_="checkgroup",
                        onclick="cmk.selection.toggle_all_rows();",
                        value='X'),
                    sortable=False,
                    css="checkbox")
                html.checkbox("_c_aggregation_%s" % aggregation_id)

                table.cell(_("Actions"), css="buttons")
                edit_url = html.makeuri_contextless([("mode", "bi_edit_aggregation"),
                                                     ("id", aggregation_id), ("pack",
                                                                              self._pack_id)])
                html.icon_button(edit_url, _("Edit this aggregation"), "edit")

                if self.is_contact_for_pack():
                    delete_url = html.makeactionuri([("_del_aggr", aggregation_id)])
                    html.icon_button(delete_url, _("Delete this aggregation"), "delete")

                table.text_cell(_("Nr."), aggregation_id + 1, css="number")

                if cmk.is_managed_edition():
                    table.text_cell(_("Customer"))
                    if "customer" in aggregation:
                        html.write_text(managed.get_customer_name(aggregation))

                table.text_cell(_("Options"), css="buttons")

                if aggregation["disabled"]:
                    html.icon(_("This aggregation is currently disabled."), "disabled")
                else:
                    html.icon(_("This aggregation is currently enabled."), "enabled")

                if aggregation["single_host"]:
                    html.icon(_("This aggregation covers only data from a single host."), "host")
                else:
                    html.icon(_("This aggregation works with data of multiple hosts."), "aggr")

                if aggregation["hard_states"]:
                    html.icon(_("Base state computation on hard states"), "hard_states")
                else:
                    html.icon(_("Base state computation on soft and hard states"), "all_states")

                if aggregation["downtime_aggr_warn"]:
                    html.icon(_("Escalate downtimes based on aggregated WARN state"), "warning")
                else:
                    html.icon(_("Escalate downtimes based on aggregated CRIT state"), "critical")

                table.text_cell(_("Groups"), ", ".join(aggregation["groups"]))

                ruleid, description = self.rule_called_by_node(aggregation["node"])
                edit_url = html.makeuri([("mode", "bi_edit_rule"), ("pack", self._pack_id),
                                         ("id", ruleid)])
                table.cell(_("Rule Tree"), css="bi_rule_tree")
                self.render_aggregation_rule_tree(aggregation_id, aggregation)
                table.text_cell(_("Note"), description)

    def render_aggregation_rule_tree(self, aggregation_id, aggregation):
        toplevel_rule = self.aggregation_toplevel_rule(aggregation)
        if not toplevel_rule:
            html.show_error(_("The top level rule does not exist."))
            return
        self.render_rule_tree(
            toplevel_rule["id"], toplevel_rule["id"], tree_prefix="%s_" % aggregation_id)


#.
#   .--Rules---------------------------------------------------------------.
#   |                       ____        _                                  |
#   |                      |  _ \ _   _| | ___  ___                        |
#   |                      | |_) | | | | |/ _ \/ __|                       |
#   |                      |  _ <| |_| | |  __/\__ \                       |
#   |                      |_| \_\\__,_|_|\___||___/                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeBIRules(ModeBI):
    @classmethod
    def name(cls):
        return "bi_rules"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    def __init__(self):
        ModeBI.__init__(self)
        self._view_type = html.request.var("view", "list")

    def title(self):
        if self._view_type == "list":
            return ModeBI.title(self) + " - " + _("Rules")
        return ModeBI.title(self) + " - " + _("Unused Rules")

    def buttons(self):
        ModeBI.buttons(self)
        if self._view_type == "list":
            html.context_button(
                _("Aggregations"), self.url_to_pack([("mode", "bi_aggregations")]), "aggr")
            if self.is_contact_for_pack():
                html.context_button(
                    _("New Rule"),
                    self.url_to_pack([("mode", "bi_edit_rule"), ("pack", self._pack_id)]), "new")
            html.context_button(
                _("Unused Rules"), self.url_to_pack([("mode", "bi_rules"), ("view", "unused")]),
                "unusedbirules")
        else:
            html.context_button(_("Back"), html.makeuri([("view", "list")]), "back")

    def action(self):
        self.must_be_contact_for_pack()

        if html.request.var("_del_rule"):
            return self._delete_after_confirm()

        elif html.request.var("_bulk_delete_bi_rules"):
            return self._bulk_delete_after_confirm()

        elif html.request.var("_bulk_move_bi_rules"):
            return self._bulk_move_after_confirm()

    def _delete_after_confirm(self):
        rule_id = html.request.var("_del_rule")
        self._check_delete_rule_id_permission(rule_id)
        c = wato_confirm(
            _("Confirm rule deletion"),
            _("Do you really want to delete the rule with "
              "the ID <b>%s</b>?") % rule_id)
        if c:
            del self._pack["rules"][rule_id]
            self._add_change("bi-delete-rule", _("Deleted BI rule with ID %s") % rule_id)
            self.save_config()
        elif c is False:  # not yet confirmed
            return ""

    def _bulk_delete_after_confirm(self):
        selection = self._get_selection("rule")
        for rule_id in selection:
            self._check_delete_rule_id_permission(rule_id)

        if selection:
            c = wato_confirm(_("Confirm deletion of %d rules") % \
                               len(selection),
                             _("Do you really want to delete %d rules?") % \
                               len(selection))
            if c:
                for rule_id in selection:
                    del self._pack["rules"][rule_id]
                    self._add_change("bi-delete-rule", _("Deleted BI rule with ID %s") % rule_id)
                self.save_config()
            elif c is False:
                return ""

    def _check_delete_rule_id_permission(self, rule_id):
        aggr_refs, rule_refs, _level = self.count_rule_references(rule_id)
        if aggr_refs:
            raise MKUserError(None,
                              _("You cannot delete this rule: it is still used by aggregations."))
        if rule_refs:
            raise MKUserError(None,
                              _("You cannot delete this rule: it is still used by other rules."))

    def _bulk_move_after_confirm(self):
        target = None
        if html.request.has_var('bulk_moveto'):
            target = html.request.var('bulk_moveto', '')
            html.javascript('cmk.selection.update_bulk_moveto("%s")' % target)

        target_pack = None
        if target in self._packs:
            target_pack = self._packs[target]
            self.must_be_contact_for_pack(target_pack)

        selection = self._get_selection("rule")
        if selection and target_pack is not None:
            c = wato_confirm(_("Confirm moving of %d rules to %s") % \
                              (len(selection), target_pack['title']),
                             _("Do you really want to move %d rules to %s?") % \
                              (len(selection), target_pack['title']))
            if c:
                for rule_id in selection:
                    rule_attrs = self._pack["rules"][rule_id]
                    target_pack["rules"].setdefault(rule_id, rule_attrs)
                    del self._pack["rules"][rule_id]
                    self._add_change(
                        "bi-move-rule",
                        _("Moved BI rule with ID %s to BI pack %s") % (rule_id, target))
                self.save_config()
            elif c is False:
                return ""

    def page(self):
        self.must_be_contact_for_pack()
        if not self._pack["aggregations"] and not self._pack["rules"]:
            menu = MainMenu()
            menu.add_item(
                MenuItem(
                    mode_or_url=self.url_to_pack([("mode", "bi_edit_rule")]),
                    title=_("Create aggregation rule"),
                    icon="new",
                    permission="bi_rules",
                    description=_("Rules are the nodes in BI aggregations. "
                                  "Each aggregation has one rule as its root."),
                ))
            menu.show()
            return

        html.begin_form("bulk_delete_form", method="POST")
        if self._view_type == "list":
            self.render_rules(_("Rules"), only_unused=False)
        else:
            self.render_rules(_("Unused BI Rules"), only_unused=True)

        html.hidden_fields()
        if self._pack["rules"]:
            fieldstyle = "margin-top:10px"
            html.button("_bulk_delete_bi_rules", _("Bulk delete"), "submit", style=fieldstyle)

            move_choices = [(pack_id, attrs["title"])
                            for pack_id, attrs in self._packs.items()
                            if pack_id is not self._pack["id"] and self.is_contact_for_pack(attrs)]

            if move_choices:
                html.button("_bulk_move_bi_rules", _("Bulk move"), "submit", style=fieldstyle)

                if html.request.has_var('bulk_moveto'):
                    html.javascript('cmk.selection.update_bulk_moveto("%s")' % html.request.var(
                        'bulk_moveto', ''))

                html.select(
                    "bulk_moveto",
                    move_choices,
                    "@",
                    onchange="cmk.selection.update_bulk_moveto(this.value)",
                    attrs={
                        'class': 'bulk_moveto',
                        'style': fieldstyle
                    })
        html.end_form()

    def render_rules(self, title, only_unused):
        aggregations_that_use_rule = self.find_aggregation_rule_usages()

        rules = self._pack["rules"].items()
        # Sort rules according to nesting level, and then to id
        rules_refs = [
            (rule_id, rule, self.count_rule_references(rule_id)) for (rule_id, rule) in rules
        ]
        rules_refs.sort(cmp=lambda a, b: cmp(a[2][2], b[2][2]) or cmp(a[1]["title"], b[1]["title"]))

        with table_element("bi_rules", title) as table:
            for rule_id, rule, (aggr_refs, rule_refs, level) in rules_refs:
                refs = aggr_refs + rule_refs
                if not only_unused or refs == 0:
                    table.row()
                    table.cell(
                        html.render_input(
                            "_toggle_group",
                            type_="button",
                            class_="checkgroup",
                            onclick="cmk.selection.toggle_all_rows();",
                            value='X'),
                        sortable=False,
                        css="checkbox")
                    html.checkbox("_c_rule_%s" % rule_id)

                    table.cell(_("Actions"), css="buttons")
                    edit_url = self.url_to_pack([("mode", "bi_edit_rule"), ("id", rule_id)])
                    html.icon_button(edit_url, _("Edit this rule"), "edit")

                    clone_url = self.url_to_pack([("mode", "bi_edit_rule"), ("clone", rule_id)])
                    html.icon_button(clone_url, _("Create a copy of this rule"), "clone")

                    if rule_refs == 0:
                        tree_url = html.makeuri_contextless([
                            ("mode", "bi_rule_tree"),
                            ("id", rule_id),
                            ("pack", self._pack_id),
                        ])
                        html.icon_button(tree_url, _("This is a top-level rule. Show rule tree"),
                                         "bitree")

                    if refs == 0:
                        delete_url = html.makeactionuri_contextless([("mode", "bi_rules"),
                                                                     ("_del_rule", rule_id),
                                                                     ("pack", self._pack_id)])
                        html.icon_button(delete_url, _("Delete this rule"), "delete")

                    table.cell("", css="narrow")
                    if rule.get("disabled"):
                        html.icon(
                            _("This rule is currently disabled and will not be applied"),
                            "disabled")
                    else:
                        html.empty_icon_button()

                    table.text_cell(_("Level"), level or "", css="number")
                    table.text_cell(_("ID"), html.render_a(rule_id, edit_url))
                    table.text_cell(_("Parameters"), " ".join(rule["params"]))

                    if rule.get('icon'):
                        title = html.render_icon(rule["icon"]) + "&nbsp;" + rule["title"]
                    else:
                        title = rule["title"]
                    table.text_cell(_("Title"), title)

                    table.text_cell(
                        _("Aggregation"),
                        "/".join([rule["aggregation"][0]] + map(str, rule["aggregation"][1])))
                    table.text_cell(_("Nodes"), len(rule["nodes"]), css="number")
                    table.cell(_("Used by"))
                    have_this = set([])
                    for (pack_id, aggr_id, aggregation) in aggregations_that_use_rule.get(
                            rule_id, []):
                        if aggr_id not in have_this:
                            aggr_url = html.makeuri_contextless([("mode", "bi_edit_aggregation"),
                                                                 ("id", aggr_id), ("pack",
                                                                                   pack_id)])
                            html.a(self.aggregation_title(aggregation), href=aggr_url)
                            html.br()
                            have_this.add(aggr_id)

                    table.text_cell(_("Comment"), rule.get("comment", ""))
                    table.text_cell(_("Documentation URL"), rule.get("docu_url", ""))


#.
#   .--Rule Tree-----------------------------------------------------------.
#   |               ____        _        _____                             |
#   |              |  _ \ _   _| | ___  |_   _| __ ___  ___                |
#   |              | |_) | | | | |/ _ \   | || '__/ _ \/ _ \               |
#   |              |  _ <| |_| | |  __/   | || | |  __/  __/               |
#   |              |_| \_\\__,_|_|\___|   |_||_|  \___|\___|               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeBIRuleTree(ModeBI):
    @classmethod
    def name(cls):
        return "bi_rule_tree"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    def __init__(self):
        ModeBI.__init__(self)
        self._ruleid = html.get_ascii_input("id")
        if not self.pack_containing_rule(self._ruleid):
            raise MKUserError("id", _("This BI rule does not exist"))

    def title(self):
        return ModeBI.title(self) + " - " + _("Rule Tree of") + " " + self._ruleid

    def buttons(self):
        ModeBI.buttons(self)
        html.context_button(_("Back"), html.makeuri([("mode", "bi_rules")]), "back")

    def page(self):
        _aggr_refs, rule_refs, _level = self.count_rule_references(self._ruleid)
        if rule_refs == 0:
            with table_element(sortable=False, searchable=False) as table:
                table.row()
                table.cell(_("Rule Tree"), css="bi_rule_tree")
                self.render_rule_tree(self._ruleid, self._ruleid)


#.
#   .--Edit Aggregation----------------------------------------------------.
#   |                          _____    _ _ _                              |
#   |                         | ____|__| (_) |_                            |
#   |                         |  _| / _` | | __|                           |
#   |                         | |__| (_| | | |_                            |
#   |                         |_____\__,_|_|\__|                           |
#   |                                                                      |
#   |         _                                    _   _                   |
#   |        / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __        |
#   |       / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \       |
#   |      / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | |      |
#   |     /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|      |
#   |             |___/ |___/          |___/                               |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeBIEditAggregation(ModeBI):
    @classmethod
    def name(cls):
        return "bi_edit_aggregation"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    def __init__(self):
        ModeBI.__init__(self)
        self._edited_nr = html.get_integer_input("id", -1)  # In case of Aggregations: index in list
        if self._edited_nr == -1:
            self._new = True
            self._edited_aggregation = {"groups": [_("Main")]}
        else:
            self._new = False
            try:
                self._edited_aggregation = self._pack["aggregations"][self._edited_nr]
            except IndexError:
                raise MKUserError("id", _("This aggregation does not exist."))

    def title(self):
        if self._new:
            return ModeBI.title(self) + " - " + _("Create New Aggregation")
        return ModeBI.title(self) + " - " + _("Edit Aggregation")

    def buttons(self):
        html.context_button(_("Abort"), html.makeuri([("mode", "bi_aggregations")]), "abort")

    def action(self):
        self.must_be_contact_for_pack()
        if html.check_transaction():
            new_aggr = self._vs_aggregation.from_html_vars('aggr')
            self._vs_aggregation.validate_value(new_aggr, 'aggr')
            if len(new_aggr["groups"]) == 0:
                raise MKUserError('rule_p_groups_0',
                                  _("Please define at least one aggregation group"))
            if self._new:
                self._pack["aggregations"].append(new_aggr)
                self._add_change(
                    "bi-new-aggregation",
                    _("Created new BI aggregation %d") % (len(self._pack["aggregations"])))
            else:
                self._pack["aggregations"][self._edited_nr] = new_aggr
                self._add_change("bi-edit-aggregation",
                                 _("Modified BI aggregation %d") % (self._edited_nr + 1))
            self.save_config()
        return "bi_aggregations"

    def page(self):
        html.begin_form("biaggr", method="POST")
        self._vs_aggregation.render_input("aggr", self._edited_aggregation)
        forms.end()
        html.hidden_fields()
        if self.is_contact_for_pack():
            html.button("_save", self._new and _("Create") or _("Save"), "submit")
        html.set_focus("aggr_p_groups_0")
        html.end_form()


#.
#   .--Edit Rule-----------------------------------------------------------.
#   |                _____    _ _ _     ____        _                      |
#   |               | ____|__| (_) |_  |  _ \ _   _| | ___                 |
#   |               |  _| / _` | | __| | |_) | | | | |/ _ \                |
#   |               | |__| (_| | | |_  |  _ <| |_| | |  __/                |
#   |               |_____\__,_|_|\__| |_| \_\\__,_|_|\___|                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeBIEditRule(ModeBI):
    @classmethod
    def name(cls):
        return "bi_edit_rule"

    @classmethod
    def permissions(cls):
        return ["bi_rules"]

    def __init__(self):
        ModeBI.__init__(self)
        self._ruleid = html.get_ascii_input("id")  # In case of Aggregations: index in list
        self._new = self._ruleid is None

        if not self._new and not self.pack_containing_rule(self._ruleid):
            raise MKUserError("id", _("This BI rule does not exist"))

    def title(self):
        if self._new:
            return ModeBI.title(self) + " - " + _("Create New Rule")
        return ModeBI.title(self) + " - " + _("Edit Rule") + " " + html.attrencode(self._ruleid)

    def buttons(self):
        html.context_button(_("Abort"), html.makeuri([("mode", "bi_rules")]), "abort")

    def action(self):
        self.must_be_contact_for_pack()

        vs_rule = self.valuespec()
        new_rule = vs_rule.from_html_vars('rule')
        vs_rule.validate_value(new_rule, 'rule')

        if self._ruleid and self._ruleid != new_rule["id"]:
            forbidden_packs = self._get_forbidden_packs_using_rule()
            if forbidden_packs:
                raise MKAuthException(
                    _("You have no permission for changes in BI packs <b>%s</b> "
                      "which uses rule <b>%s</b>.") % (", ".join(forbidden_packs), self._ruleid))

            new_ruleid = new_rule["id"]
            c = wato_confirm(_("Confirm renaming existing BI rule"),
                             _("Do you really want to rename the existing BI rule <b>%s</b> to <b>%s</b>?") % \
                              (self._ruleid, new_ruleid))

            if c:
                self._rename_ruleid_after_confirm(new_ruleid)
                self._add_change("bi-edit-rule",
                                 _("Renamed BI rule from %s to %s") % (self._ruleid, new_ruleid))
                self.save_config()

            else:
                return False

        elif html.check_transaction():
            if self._new:
                self._ruleid = new_rule["id"]

            if self._new and self.find_rule_by_id(self._ruleid):
                existing_rule = self.find_rule_by_id(self._ruleid)
                pack = self.pack_containing_rule(self._ruleid)
                raise MKUserError(
                    'rule_p_id',
                    _("There is already a rule with the ID <b>%s</b>. "
                      "It is in the pack <b>%s</b> and as the title <b>%s</b>") %
                    (self._ruleid, pack["title"], existing_rule["title"]))

            if not new_rule["nodes"]:
                raise MKUserError(None,
                                  _("Please add at least one child node. Empty rules are useless."))

            if self._new:
                del new_rule["id"]
                self._pack["rules"][self._ruleid] = new_rule
                self._add_change("bi-new-rule", _("Create new BI rule %s") % self._ruleid)
            else:
                self._pack["rules"][self._ruleid].update(new_rule)
                new_rule["id"] = self._ruleid
                if self.rule_uses_rule(new_rule, new_rule["id"]):
                    raise MKUserError(
                        None,
                        _("There is a cycle in your rules. This rule calls itself - "
                          "either directly or indirectly."))
                self._add_change("bi-edit-rule", _("Modified BI rule %s") % self._ruleid)

            self.save_config()

        return "bi_rules"

    def _get_forbidden_packs_using_rule(self):
        forbidden_packs = set()
        for packid, packinfo in self._packs.iteritems():
            uses_rule = False
            if self._pack == packinfo:
                continue
            for ruleid, rule_info in packinfo['rules'].iteritems():
                if ruleid == self._ruleid:
                    uses_rule = True
                    break
                for node_type, node_info in rule_info.get('nodes', []):
                    if node_type == 'call' and self._ruleid == node_info[0]:
                        uses_rule = True
                        break

            for aggregation in packinfo.get("aggregations", []):
                node = aggregation.get('node')
                if node is None:
                    continue
                if (node[0] == 'call' and self._ruleid == node[1][0]) or \
                   (node[0] in ["foreach_host", "foreach_service"] and node[-1][-1][0] == 'call' and \
                    self._ruleid == node[-1][-1][1][0]):
                    uses_rule = True
                    break
            if uses_rule and not self.is_contact_for_pack(pack=packinfo):
                forbidden_packs.add(packid)
        return forbidden_packs

    def _rename_ruleid_after_confirm(self, new_ruleid):
        new_packs = self._packs.copy()
        for packid, packinfo in self._packs.iteritems():
            for ruleid, rule_info in packinfo['rules'].iteritems():
                if ruleid == self._ruleid:
                    new_rule_info = rule_info.copy()
                    new_rule_info['id'] = new_ruleid
                    new_packs[packid]['rules'][new_ruleid] = new_rule_info
                    del new_packs[packid]['rules'][ruleid]
                    continue

                for node in rule_info.get('nodes', [])[::-1]:
                    new_node = self._get_new_node(node, new_ruleid)
                    if new_node is None:
                        continue
                    idx = new_packs[packid]['rules'][ruleid]['nodes'].index(node)
                    del new_packs[packid]['rules'][ruleid]['nodes'][idx]
                    new_packs[packid]['rules'][ruleid]['nodes'].insert(idx, new_node)

            for aggregation in packinfo.get("aggregations", [])[::-1]:
                node = aggregation.get('node')
                if node is None:
                    continue
                new_node = self._get_new_node(node, new_ruleid)
                if new_node is None:
                    continue
                new_aggregation = aggregation.copy()
                new_aggregation['node'] = new_node
                idx = new_packs[packid]["aggregations"].index(aggregation)
                del new_packs[packid]["aggregations"][idx]
                new_packs[packid]["aggregations"].insert(idx, new_aggregation)

        self._packs = new_packs
        self._ruleid = new_ruleid

    def _get_new_node(self, node, new_ruleid):
        new_node = None
        if node[0] == 'call' and self._ruleid == node[1][0]:
            new_node = self._create_call_node(new_ruleid, node[1][1])
        elif node[0] in ["foreach_host", "foreach_service"] and node[-1][-1][0] == 'call' and \
             self._ruleid == node[-1][-1][1][0]:
            new_node = self._create_foreach_node(node[0], list(node[1][:-1]), new_ruleid,
                                                 node[-1][-1][1][1])
        return new_node

    def _create_call_node(self, ruleid, arguments):
        return ('call', (ruleid, arguments))

    def _create_foreach_node(self, what, parameters, ruleid, arguments):
        return (what, tuple(parameters + [self._create_call_node(ruleid, arguments)]))

    def page(self):
        self.must_be_contact_for_pack()

        if self._new:
            cloneid = html.request.var("clone")
            if cloneid:
                try:
                    value = self._pack["rules"][cloneid]
                except KeyError:
                    raise MKGeneralException(_("This BI rule does not exist"))
            else:
                value = {}
        else:
            try:
                value = self._pack["rules"][self._ruleid]
            except KeyError:
                raise MKGeneralException(_("This BI rule does not exist"))

        self._may_use_rules_from_packs(value)

        html.begin_form("birule", method="POST")
        self.valuespec().render_input("rule", value)
        forms.end()
        html.hidden_fields()
        if self.is_contact_for_pack():
            html.button("_save", self._new and _("Create") or _("Save"), "submit")
        if self._new:
            html.set_focus("rule_p_id")
        else:
            html.set_focus("rule_p_title")
        html.end_form()

    def _may_use_rules_from_packs(self, rulepack):
        rules_without_permissions = {}
        for node in rulepack.get("nodes", []):
            node_type, node_content = node
            if node_type != 'call':
                continue

            node_ruleid = node_content[0]
            pack = self.pack_containing_rule(node_ruleid)
            if pack is not None and not self.may_use_rules_in_pack(pack):
                packid = (pack['id'], pack['title'])
                rules_without_permissions.setdefault(packid, [])
                rules_without_permissions[packid].append(node_ruleid)

        if rules_without_permissions:
            message = ", ".join([_("BI rules %s from BI pack '%s'") % \
                                 (", ".join([ "'%s'" % ruleid for ruleid in ruleids]), title)
                                 for (_nodeid, title), ruleids in rules_without_permissions.items()])
            raise MKAuthException(
                _("You have no permission for changes in this rule using %s.") % message)

    def valuespec(self):
        elements = [
            ("id",
             TextAscii(
                 title=_("Rule ID"),
                 help=_(
                     "The ID of the rule must be a unique text. It will be used as an internal key "
                     "when rules refer to each other. The rule IDs will not be visible in the status "
                     "GUI. They are just used within the configuration."),
                 allow_empty=False,
                 size=80,
             )),
            ("title",
             TextUnicode(
                 title=_("Rule Title"),
                 help=_("The title of the BI nodes which are created from this rule. This will be "
                        "displayed as the name of the node in the BI view. For "
                        "top level nodes this title must be unique. You can insert "
                        "rule parameters like <tt>$FOO$</tt> or <tt>$BAR$</tt> here."),
                 allow_empty=False,
                 size=80,
             )),
            ("comment",
             TextAreaUnicode(
                 title=_("Comment"),
                 help=_("An arbitrary comment of this rule for you."),
                 cols=80,
                 rows=4,
             )),
            ("docu_url",
             TextAscii(
                 title=_("Documentation URL"),
                 help=HTML(
                     _("An optional URL pointing to documentation or any other page. This will be "
                       "displayed as an icon %s and open "
                       "a new page when clicked. You can use either global URLs (beginning with "
                       "<tt>http://</tt>), absolute local urls (beginning with <tt>/</tt>) or relative "
                       "URLs (that are relative to <tt>check_mk/</tt>).") %
                     html.render_icon("url")),
                 size=80,
             )),
            ("params",
             ListOfStrings(
                 title=_("Parameters"),
                 help=_(
                     "Parameters are used in order to make rules more flexible. They must "
                     "be named like variables in programming languages. For example you can "
                     "make your rule have the two parameters <tt>HOST</tt> and <tt>INST</tt>. "
                     "When calling the rule - from an aggergation or a higher level rule - "
                     "you can then specify two arbitrary values for these parameters. In the "
                     "title of the rule as well as the host and service names, you can insert the "
                     "actual value of the parameters by <tt>$HOST$</tt> and <tt>$INST$</tt> "
                     "(enclosed in dollar signs)."),
                 orientation="horizontal",
                 valuespec=TextAscii(
                     size=80,
                     regex='[A-Za-z_][A-Za-z0-9_]*',
                     regex_error=_("Parameters must contain only A-Z, a-z, 0-9 and _ "
                                   "and must not begin with a digit."),
                 ))),
            ("disabled",
             Checkbox(
                 title=_("Rule activation"),
                 help=_("Disabled rules are kept in the configuration but are not applied."),
                 label=_("do not apply this rule"),
             )),
            ("aggregation",
             CascadingDropdown(
                 title=_("Aggregation Function"),
                 help=_("The aggregation function decides how the status of a node "
                        "is constructed from the states of the child nodes."),
                 orientation="horizontal",
                 choices=self._aggregation_choices(),
             )),
            ("nodes",
             ListOf(
                 self._vs_node,
                 add_label=_("Add child node generator"),
                 title=_("Nodes that are aggregated by this rule"),
             )),
            ("state_messages",
             Optional(
                 Dictionary(elements=[(state,
                                       TextAscii(
                                           title=_("Message when rule result is %s") % name,
                                           default_value=None,
                                           size=80,
                                       )) for state, name in [
                                           ("0", "OK"),
                                           ("1", "WARN"),
                                           ("2", "CRIT"),
                                           ("3", "UNKNOWN"),
                                       ]]),
                 title=_("Additional messages describing rule state"),
                 help=
                 _("This option allows you to display an additional, freely configurable text, to the rule outcome, "
                   "which may describe the state more in detail. For example, instead of <tt>CRIT</tt>, the rule can now "
                   "display <tt>CRIT, less than 70% of servers reachable</tt>. This message is also shown within the BI aggregation "
                   "check plugins."),
                 label=_("Add messages"))),
            ("icon", IconSelector(title=_("Icon"))),
        ]

        return Dictionary(
            title=_("Rule Properties"),
            optional_keys=False,
            render="form",
            elements=elements,
            headers=[
                (_("Rule Properties"), ["id", "title", "docu_url", "comment", "params",
                                        "disabled"]),
                (_("Child Node Generation"), ["nodes"]),
                (_("Aggregation Function"), ["aggregation", "state_messages", "icon"]),
            ])


#.
#   .--Aggregation functions-----------------------------------------------.
#   |             _                     __                                 |
#   |            / \   __ _  __ _ _ __ / _|_   _ _ __   ___ ___            |
#   |           / _ \ / _` |/ _` | '__| |_| | | | '_ \ / __/ __|           |
#   |          / ___ \ (_| | (_| | |  |  _| |_| | | | | (__\__ \           |
#   |         /_/   \_\__, |\__, |_|  |_|  \__,_|_| |_|\___|___/           |
#   |                 |___/ |___/                                          |
#   '----------------------------------------------------------------------'

bi_aggregation_functions = {}

bi_aggregation_functions["worst"] = {
    "title": _("Worst - take worst of all node states"),
    "valuespec": Tuple(elements=[
        Integer(
            help=_(
                "Normally this value is <tt>1</tt>, which means that the worst state "
                "of all child nodes is being used as the total state. If you set it for example "
                "to <tt>3</tt>, then instead the node with the 3rd worst state is being regarded. "
                "Example: In the case of five nodes with the states CRIT CRIT WARN OK OK then "
                "resulting state would be WARN. Or you could say that the worst to nodes are "
                "first dropped and then the worst of the remaining nodes defines the state. "),
            title=_("Take n'th worst state for n = "),
            default_value=1,
            min_value=1),
        MonitoringState(
            title=_("Restrict severity to at worst"),
            help=_("Here a maximum severity of the node state can be set. This severity is not "
                   "exceeded, even if some of the childs have more severe states."),
            default_value=2,
        ),
    ]),
}

bi_aggregation_functions["best"] = {
    "title": _("Best - take best of all node states"),
    "valuespec": Tuple(elements=[
        Integer(
            help=_("Normally this value is <tt>1</tt>, which means that the best state "
                   "of all child nodes is being used as the total state. If you set it for example "
                   "to <tt>2</tt>, then the node with the best state is not being regarded. "
                   "If the states of the child nodes would be CRIT, WARN and OK, then to total "
                   "state would be WARN."),
            title=_("Take n'th best state for n = "),
            default_value=1,
            min_value=1),
        MonitoringState(
            title=_("Restrict severity to at worst"),
            help=_("Here a maximum severity of the node state can be set. This severity is not "
                   "exceeded, even if some of the childs have more severe states."),
            default_value=2,
        ),
    ]),
}


def vs_count_ok_count(title, defval, defvalperc):
    return Alternative(
        title=title,
        style="dropdown",
        match=lambda x: str(x).endswith("%") and 1 or 0,
        elements=[
            Integer(
                title=_("Explicit number"),
                label=_("Number of OK-nodes"),
                min_value=0,
                default_value=defval),
            Transform(
                Percentage(
                    label=_("Percent of OK-nodes"), display_format="%.0f",
                    default_value=defvalperc),
                title=_("Percentage"),
                forth=lambda x: float(x[:-1]),
                back=lambda x: "%d%%" % x,
            ),
        ])


bi_aggregation_functions["count_ok"] = {
    "title": _("Count the number of nodes in state OK"),
    "valuespec": Tuple(elements=[
        vs_count_ok_count(_("Required number of OK-nodes for a total state of OK:"), 2, 50),
        vs_count_ok_count(_("Required number of OK-nodes for a total state of WARN:"), 1, 25),
    ]),
}

#.
#   .--Example Configuration-----------------------------------------------.
#   |               _____                           _                      |
#   |              | ____|_  ____ _ _ __ ___  _ __ | | ___                 |
#   |              |  _| \ \/ / _` | '_ ` _ \| '_ \| |/ _ \                |
#   |              | |___ >  < (_| | | | | | | |_) | |  __/                |
#   |              |_____/_/\_\__,_|_| |_| |_| .__/|_|\___|                |
#   |                                        |_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'

bi_example = '''
aggregation_rules["host"] = (
  "Host $HOSTNAME$",
  [ "HOSTNAME" ],
  "worst",
  [
      ( "general",      [ "$HOSTNAME$" ] ),
      ( "performance",  [ "$HOSTNAME$" ] ),
      ( "filesystems",  [ "$HOSTNAME$" ] ),
      ( "networking",   [ "$HOSTNAME$" ] ),
      ( "applications", [ "$HOSTNAME$" ] ),
      ( "logfiles",     [ "$HOSTNAME$" ] ),
      ( "hardware",     [ "$HOSTNAME$" ] ),
      ( "other",        [ "$HOSTNAME$" ] ),
  ]
)

aggregation_rules["general"] = (
  "General State",
  [ "HOSTNAME" ],
  "worst",
  [
      ( "$HOSTNAME$", HOST_STATE ),
      ( "$HOSTNAME$", "Uptime" ),
      ( "checkmk",    [ "$HOSTNAME$" ] ),
  ]
)

aggregation_rules["filesystems"] = (
  "Disk & Filesystems",
  [ "HOSTNAME" ],
  "worst",
  [
      ( "$HOSTNAME$", "Disk|MD" ),
      ( "multipathing", [ "$HOSTNAME$" ]),
      ( FOREACH_SERVICE, "$HOSTNAME$", "fs_(.*)", "filesystem", [ "$HOSTNAME$", "$1$" ] ),
      ( FOREACH_SERVICE, "$HOSTNAME$", "Filesystem(.*)", "filesystem", [ "$HOSTNAME$", "$1$" ] ),
  ]
)

aggregation_rules["filesystem"] = (
  "$FS$",
  [ "HOSTNAME", "FS" ],
  "worst",
  [
      ( "$HOSTNAME$", "fs_$FS$$" ),
      ( "$HOSTNAME$", "Filesystem$FS$$" ),
      ( "$HOSTNAME$", "Mount options of $FS$$" ),
  ]
)

aggregation_rules["multipathing"] = (
  "Multipathing",
  [ "HOSTNAME" ],
  "worst",
  [
      ( "$HOSTNAME$", "Multipath" ),
  ]
)

aggregation_rules["performance"] = (
  "Performance",
  [ "HOSTNAME" ],
  "worst",
  [
      ( "$HOSTNAME$", "CPU|Memory|Vmalloc|Kernel|Number of threads" ),
  ]
)

aggregation_rules["hardware"] = (
  "Hardware",
  [ "HOSTNAME" ],
  "worst",
  [
      ( "$HOSTNAME$", "IPMI|RAID" ),
  ]
)

aggregation_rules["networking"] = (
  "Networking",
  [ "HOSTNAME" ],
  "worst",
  [
      ( "$HOSTNAME$", "NFS|Interface|TCP" ),
  ]
)

aggregation_rules["checkmk"] = (
  "Check_MK",
  [ "HOSTNAME" ],
  "worst",
  [
       ( "$HOST$", "Check_MK|Uptime" ),
  ]
)

aggregation_rules["logfiles"] = (
  "Logfiles",
  [ "HOSTNAME" ],
  "worst",
  [
      ( "$HOSTNAME$", "LOG" ),
  ]
)
aggregation_rules["applications"] = (
  "Applications",
  [ "HOSTNAME" ],
  "worst",
  [
      ( "$HOSTNAME$", "ASM|ORACLE|proc" ),
  ]
)

aggregation_rules["other"] = (
  "Other",
  [ "HOSTNAME" ],
  "worst",
  [
      ( "$HOSTNAME$", REMAINING ),
  ]
)

host_aggregations += [
  ( DISABLED, "Hosts", FOREACH_HOST, [ "tcp" ], ALL_HOSTS, "host", ["$HOSTNAME$"] ),
]
'''

#.
#   .--Declarations--------------------------------------------------------.
#   |       ____            _                 _   _                        |
#   |      |  _ \  ___  ___| | __ _ _ __ __ _| |_(_) ___  _ __  ___        |
#   |      | | | |/ _ \/ __| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |_| |  __/ (__| | (_| | | | (_| | |_| | (_) | | | \__ \       |
#   |      |____/ \___|\___|_|\__,_|_|  \__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Integrate all that stuff into WATO                                  |
#   '----------------------------------------------------------------------'


@permission_registry.register
class BIRulesPermission(Permission):
    @property
    def section(self):
        return PermissionSectionWATO

    @property
    def permission_name(self):
        return "bi_rules"

    @property
    def title(self):
        return _("Business Intelligence Rules and Aggregations")

    @property
    def description(self):
        return _("Use the WATO BI module, create, modify and delete BI rules and "
                 "aggregations in packs that you are a contact of.")

    @property
    def defaults(self):
        return ["admin", "user"]


@permission_registry.register
class BIAdminPermission(Permission):
    @property
    def section(self):
        return PermissionSectionWATO

    @property
    def permission_name(self):
        return "bi_admin"

    @property
    def title(self):
        return _("Business Intelligence Administration")

    @property
    def description(self):
        return _("Edit all rules and aggregations for Business Intelligence, "
                 "create, modify and delete rule packs.")

    @property
    def defaults(self):
        return ["admin"]


@main_module_registry.register
class MainModuleBI(MainModule):
    @property
    def mode_or_url(self):
        return "bi_packs"

    @property
    def title(self):
        return _("Business Intelligence")

    @property
    def icon(self):
        return "aggr"

    @property
    def permission(self):
        return "bi_rules"

    @property
    def description(self):
        return _("Configuration of Check_MK's Business Intelligence component.")

    @property
    def sort_index(self):
        return 70


#.
#   .--Rename Hosts--------------------------------------------------------.
#   |   ____                                   _   _           _           |
#   |  |  _ \ ___ _ __   __ _ _ __ ___   ___  | | | | ___  ___| |_ ___     |
#   |  | |_) / _ \ '_ \ / _` | '_ ` _ \ / _ \ | |_| |/ _ \/ __| __/ __|    |
#   |  |  _ <  __/ | | | (_| | | | | | |  __/ |  _  | (_) \__ \ |_\__ \    |
#   |  |_| \_\___|_| |_|\__,_|_| |_| |_|\___| |_| |_|\___/|___/\__|___/    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Class just for renaming hosts in the BI configuration.              |
#   '----------------------------------------------------------------------'


class BIHostRenamer(BIManagement):
    def rename_host(self, oldname, newname):
        renamed = 0
        for pack in self._packs.values():
            renamed += self.rename_host_in_pack(pack, oldname, newname)
        if renamed:
            self.save_config()
            return ["bi"] * renamed
        return []

    def rename_host_in_pack(self, pack, oldname, newname):
        renamed = 0
        for aggregation in pack["aggregations"]:
            renamed += self.rename_host_in_aggregation(aggregation, oldname, newname)
        for rule in pack["rules"].values():
            renamed += self.rename_host_in_rule(rule, oldname, newname)
        return renamed

    def rename_host_in_aggregation(self, aggregation, oldname, newname):
        node = aggregation["node"]
        if node[0] == 'call':
            if watolib.rename_host_in_list(aggregation["node"][1][1], oldname, newname):
                return 1
        return 0

    def rename_host_in_rule(self, rule, oldname, newname):
        renamed = 0
        nodes = rule["nodes"]
        for nr, node in enumerate(nodes):
            if node[0] in ["host", "service", "remaining"]:
                if node[1][0] == oldname:
                    nodes[nr] = (node[0], (newname,) + node[1][1:])
                    renamed = 1
            elif node[0] == "call":
                if watolib.rename_host_in_list(node[1][1], oldname, newname):
                    renamed = 1
        return renamed
