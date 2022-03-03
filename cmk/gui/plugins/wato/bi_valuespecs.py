#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import copy
from typing import Any, Dict, List, Type, Union

import cmk.utils.bi.bi_actions as bi_actions
import cmk.utils.plugin_registry as plugin_registry
from cmk.utils.bi.bi_aggregation_functions import (
    BIAggregationFunctionBest,
    BIAggregationFunctionCountOK,
    BIAggregationFunctionWorst,
)
from cmk.utils.bi.bi_lib import ABCBIAction, ABCBIAggregationFunction, ABCBISearch
from cmk.utils.bi.bi_search import (
    BIEmptySearch,
    BIFixedArgumentsSearch,
    BIHostSearch,
    BIServiceSearch,
)
from cmk.utils.defines import short_service_state_name

import cmk.gui.userdb as userdb
import cmk.gui.watolib as watolib
from cmk.gui.bi import get_cached_bi_packs
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import user
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import DictHostTagCondition, LabelCondition
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Integer,
    ListOf,
    ListOfStrings,
    MonitoringState,
    Percentage,
    TextInput,
    Transform,
    Tuple,
)

#   .--Generic converter---------------------------------------------------.
#   |                   ____                      _                        |
#   |                  / ___| ___ _ __   ___ _ __(_) ___                   |
#   |                 | |  _ / _ \ '_ \ / _ \ '__| |/ __|                  |
#   |                 | |_| |  __/ | | |  __/ |  | | (__                   |
#   |                  \____|\___|_| |_|\___|_|  |_|\___|                  |
#   |                                                                      |
#   |                                           _                          |
#   |              ___ ___  _ ____   _____ _ __| |_ ___ _ __               |
#   |             / __/ _ \| '_ \ \ / / _ \ '__| __/ _ \ '__|              |
#   |            | (_| (_) | | | \ V /  __/ |  | ||  __/ |                 |
#   |             \___\___/|_| |_|\_/ \___|_|   \__\___|_|                 |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def convert_to_cascading_vs_choice(value):
    return value["type"], value


def convert_from_cascading_vs_choice(value):
    result = value[1]
    result["type"] = value[0]
    return result


# Aggregation Valuespec <-> REST conversions
######################################################
#   ('call_a_rule',
#   {'params': {'arguments': []},
#    'rule_id': 'applications',
#    'type': 'call_a_rule'})
#####################################################
#   ('host_search',
#   ({'conditions': {'host_choice': {'type': 'all_hosts'},
#                    'host_folder': '',
#                    'host_labels': {},
#                    'host_tags': {}},
#     'refer_to': 'host'},
#    {'params': {'arguments': []},
#     'rule_id': 'applications',
#     'type': 'call_a_rule'}))
def _convert_bi_aggr_to_vs(value):
    if value["search"]["type"] == "empty":
        return value["action"]["type"], value["action"]
    return value["search"]["type"], (value["search"], value["action"])


def _convert_bi_aggr_from_vs(value):
    if value[0] == "call_a_rule":
        return {"action": value[1], "search": {"type": "empty"}}

    search = copy.deepcopy(value[1][0])
    search["type"] = value[0]
    return {
        "search": search,
        "action": value[1][1],
    }


def get_bi_aggregation_node_choices():
    return Transform(
        CascadingDropdown(choices=_get_aggregation_choices()),
        forth=_convert_bi_aggr_to_vs,
        back=_convert_bi_aggr_from_vs,
    )


def _get_aggregation_choices():
    # These choices are currently hardcoded
    # A more dynamic approach will be introduced once the BI GUI gets an overhaul
    elements = []
    call_a_rule = bi_config_action_registry["call_a_rule"]
    elements.append(call_a_rule.cascading_dropdown_choice_element())
    for search_plugin in ["host_search", "service_search"]:
        plugin = bi_config_search_registry[search_plugin]
        plugin_type, title, valuespec = plugin.cascading_dropdown_choice_element()
        elements.append(
            (
                plugin_type,
                title,
                Tuple(
                    elements=[
                        valuespec,
                        call_a_rule.valuespec(),
                    ],
                ),
            )
        )
    return elements


# Rule Valuespec <-> REST conversions
######################################################
#   ('call_a_rule',
#   {'params': {'arguments': []},
#    'rule_id': 'applications',
#    'type': 'call_a_rule'})
#####################################################
# ('host_search',
#  ({'conditions': {'host_choice': {'type': 'all_hosts'},
#                   'host_folder': '',
#                   'host_labels': {},
#                   'host_tags': {}},
#    'refer_to': 'host'},
#   ('call_a_rule',
#    {'params': {'arguments': ['test']},
#     'rule_id': 'applications',
#     'type': 'call_a_rule'})))
def _convert_bi_rule_to_vs(value):
    if value is None:
        # The "complain phase" sets the value to None. o.O
        # If None is returned, it seems the valuespec uses the parameters from the request
        return value
    if value["search"]["type"] == "empty":
        return value["action"]["type"], value["action"]

    return value["search"]["type"], (value["search"], (value["action"]["type"], value["action"]))


def _convert_bi_rule_from_vs(value):
    if value[0] in [
        "state_of_host",
        "state_of_service",
        "state_of_remaining_services",
        "call_a_rule",
    ]:
        action = copy.deepcopy(value[1])
        action["type"] = value[0]
        return {"action": action, "search": {"type": "empty"}}

    search = copy.deepcopy(value[1][0])
    search["type"] = value[0]
    action = copy.deepcopy(value[1][1][1])
    action["type"] = value[1][1][0]
    return {"search": search, "action": action}


def get_bi_rule_node_choices_vs():
    return Transform(
        CascadingDropdown(choices=_get_rule_choices(), sorted=False),
        forth=_convert_bi_rule_to_vs,
        back=_convert_bi_rule_from_vs,
    )


def _get_rule_choices():
    action_choices = _get_action_cascading_dropdown_choices()
    choices = list(action_choices)
    for search_plugin in ["host_search", "service_search"]:
        plugin = bi_config_search_registry[search_plugin]
        plugin_type, title, valuespec = plugin.cascading_dropdown_choice_element()
        choices.append(
            (
                plugin_type,
                title,
                Tuple(
                    elements=[
                        valuespec,
                        CascadingDropdown(title=_("Nodes to create"), choices=action_choices),
                    ]
                ),
            )
        )
    return choices


def _get_action_cascading_dropdown_choices():
    return [x.cascading_dropdown_choice_element() for x in bi_config_action_registry.values()]


def _get_search_cascading_dropdown_choices():
    return [x.cascading_dropdown_choice_element() for x in bi_config_search_registry.values()]

    # .--Search--------------------------------------------------------------.
    #   |                   ____                      _                        |
    #   |                  / ___|  ___  __ _ _ __ ___| |__                     |
    #   |                  \___ \ / _ \/ _` | '__/ __| '_ \                    |
    #   |                   ___) |  __/ (_| | | | (__| | | |                   |
    #   |                  |____/ \___|\__,_|_|  \___|_| |_|                   |
    #   |                                                                      |
    #   +----------------------------------------------------------------------+


class ABCBIConfigSearch(ABCBISearch):
    @classmethod
    @abc.abstractmethod
    def cascading_dropdown_choice_element(cls):
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def valuespec(cls):
        raise NotImplementedError()


class BIConfigSearchRegistry(plugin_registry.Registry[Type[ABCBIConfigSearch]]):
    def plugin_name(self, instance) -> str:
        return instance.type()


bi_config_search_registry = BIConfigSearchRegistry()


def _bi_host_choice_vs(title):
    def convert_to_vs(value):
        if value["type"] == "all_hosts":
            return "all_hosts"
        return value["type"], value["pattern"]

    def convert_from_vs(value):
        if isinstance(value, str):
            return {"type": "all_hosts"}
        return {"type": value[0], "pattern": value[1]}

    return Transform(
        CascadingDropdown(
            title=title,
            choices=[
                ("all_hosts", _("All hosts")),
                (
                    "host_name_regex",
                    _("Regex for host name"),
                    TextInput(label=_("Pattern"), size=60),
                ),
                (
                    "host_alias_regex",
                    _("Regex for host alias"),
                    TextInput(label=_("Pattern"), size=60),
                ),
            ],
            help=_(
                'If you choose "Regex for host name" or "Regex for host alias", '
                "you may use match groups as placeholder. The first match group can be used with the placeholder <tt>$1$</tt>. "
                "The complete set of match groups is also available with the placeholders "
                "<tt>$HOST_MG_1$</tt>, <tt>$HOST_MG_2$</tt> and so on."
            ),
            default_value="all_hosts",
        ),
        forth=convert_to_vs,
        back=convert_from_vs,
    )


@bi_config_search_registry.register
class BIConfigEmptySearch(BIEmptySearch, ABCBIConfigSearch):
    @classmethod
    def cascading_dropdown_choice_element(cls):
        return (
            cls.type(),
            _("No search"),
            Transform(
                FixedValue(value=""), forth=lambda x: "", back=lambda x: {"type": cls.type()}
            ),
        )

    @classmethod
    def valuespec(cls):
        return None


@bi_config_search_registry.register
class BIConfigHostSearch(BIHostSearch, ABCBIConfigSearch):
    @classmethod
    def cascading_dropdown_choice_element(cls):
        return (cls.type(), _("Create nodes based on a host search"), cls.valuespec())

    @classmethod
    def valuespec(cls):
        return Dictionary(
            elements=[
                (
                    "conditions",
                    Dictionary(
                        title=_("Conditions"), elements=cls.get_host_conditions(), optional_keys=[]
                    ),
                ),
                (
                    "refer_to",
                    CascadingDropdown(
                        title=_("Refer to:"),
                        choices=[
                            ("host", _("The found hosts themselves")),
                            ("child", _("The found hosts' childs")),
                            (
                                "child_with",
                                _("The found hosts' childs (with child filtering)"),
                                Tuple(
                                    elements=[
                                        DictHostTagCondition(
                                            title=_("Child Host Tags:"), help_txt=""
                                        ),
                                        _bi_host_choice_vs(_("Child host name:")),
                                    ]
                                ),
                            ),
                            ("parent", _("The found hosts' parents")),
                        ],
                        help=_(
                            "When selecting <i>The found hosts' childs</i>, the conditions "
                            "(tags and host name) are used to match a host, but you will get one "
                            "node created for each child of the matched host. The "
                            "place holder <tt>$HOSTNAME$</tt> contains the name of the found child "
                            "and the place holder <tt>$HOSTALIAS$</tt> contains it's alias.<br><br>"
                            "When selecting <i>The found hosts' parents</i>, the conditions "
                            "(tags and host name) are used to match a host, but you will get one "
                            "node created for each of the parent hosts of the matched host. "
                            "The place holder <tt>$HOSTNAME$</tt> contains the name of the child "
                            "host and <tt>$2$</tt> the name of the parent host."
                        ),
                    ),
                ),
            ],
            optional_keys=[],
        )

    @classmethod
    def get_host_conditions(cls):
        return [
            (
                "host_folder",
                DropdownChoice(
                    title=_("Folder"),
                    help=_("The rule is only applied to hosts directly in or below this folder."),
                    choices=watolib.Folder.folder_choices(),
                    encode_value=False,
                ),
            ),
            ("host_tags", DictHostTagCondition(title=_("Host Tags"), help_txt="")),
            ("host_labels", LabelCondition(title=_("Host Labels"), help_txt="")),
            ("host_choice", _bi_host_choice_vs(_("Filter Host"))),
        ]


@bi_config_search_registry.register
class BIConfigServiceSearch(BIServiceSearch, ABCBIConfigSearch):
    @classmethod
    def cascading_dropdown_choice_element(cls):
        return (cls.type(), _("Create nodes based on a service search"), cls.valuespec())

    @classmethod
    def valuespec(cls):
        return Dictionary(
            title=_("Conditions"),
            elements=[
                (
                    "conditions",
                    Dictionary(
                        elements=BIConfigHostSearch.get_host_conditions()
                        + cls.get_service_conditions(),
                        optional_keys=[],
                    ),
                )
            ],
            optional_keys=[],
        )

    @classmethod
    def get_service_conditions(cls):
        return [
            (
                "service_regex",
                TextInput(
                    title=_("Service Regex"),
                    help=_(
                        "Subexpressions enclosed in <tt>(</tt> and <tt>)</tt> will be available "
                        "as arguments <tt>$2$</tt>, <tt>$3$</tt>, etc."
                    ),
                    size=80,
                ),
            ),
            ("service_labels", LabelCondition(title=_("Service Labels"), help_txt="")),
        ]


@bi_config_search_registry.register
class BIConfigFixedArgumentsSearch(BIFixedArgumentsSearch, ABCBIConfigSearch):
    @classmethod
    def cascading_dropdown_choice_element(cls):
        return (cls.type(), _("No search, specify list of arguments"), cls.valuespec())

    @classmethod
    def valuespec(cls):
        return Dictionary(
            elements=[
                (
                    "arguments",
                    ListOf(
                        valuespec=Transform(
                            Tuple(
                                elements=[
                                    TextInput(title=_("Keyword")),
                                    ListOfStrings(
                                        title=_("Values"),
                                        orientation="horizontal",
                                    ),
                                ]
                            ),
                            forth=cls._convert_to_vs,
                            back=cls._convert_from_vs,
                        ),
                        magic="#keys#",
                    ),
                )
            ],
            optional_keys=[],
        )

    @classmethod
    def _convert_to_vs(cls, value):
        return (value["key"], value["values"])

    @classmethod
    def _convert_from_vs(cls, value):
        return {"key": value[0], "values": value[1]}


#   .--Action--------------------------------------------------------------.
#   |                       _        _   _                                 |
#   |                      / \   ___| |_(_) ___  _ __                      |
#   |                     / _ \ / __| __| |/ _ \| '_ \                     |
#   |                    / ___ \ (__| |_| | (_) | | | |                    |
#   |                   /_/   \_\___|\__|_|\___/|_| |_|                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class ABCBIConfigAction(ABCBIAction):
    @classmethod
    @abc.abstractmethod
    def cascading_dropdown_choice_element(cls):
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def valuespec(cls):
        raise NotImplementedError()


class BIConfigActionRegistry(plugin_registry.Registry[Type[ABCBIConfigAction]]):
    def plugin_name(self, instance) -> str:
        return instance.type()


bi_config_action_registry = BIConfigActionRegistry()


@bi_config_action_registry.register
class BIConfigCallARuleAction(bi_actions.BICallARuleAction, ABCBIConfigAction):
    @classmethod
    def cascading_dropdown_choice_element(cls):
        return (cls.type(), _("Call a Rule"), cls.valuespec())

    @classmethod
    def valuespec(cls):
        def convert_to_vs(value):
            if value.get("rule_id") is None:
                return None
            bi_pack = get_cached_bi_packs().get_pack_of_rule(value["rule_id"])
            if bi_pack is None:
                return None
            return (
                (bi_pack.id, value["rule_id"]),
                value["params"]["arguments"],
            )

        def convert_from_vs(value):
            return {
                "type": cls.type(),
                "params": {
                    "arguments": value[1],
                },
                "rule_id": value[0][1],
            }

        return Transform(
            Tuple(
                elements=[
                    Transform(
                        CascadingDropdown(
                            title=_("Rule:"),
                            orientation="horizontal",
                            choices=cls._allowed_rule_choices(),
                            sorted=True,
                        ),
                    ),
                    ListOfStrings(
                        orientation="horizontal",
                        size=80,
                        title=_("Arguments:"),
                    ),
                ],
                validate=cls._validate_rule_call,
            ),
            title=_("Call a rule"),
            forth=convert_to_vs,
            back=convert_from_vs,
        )

    @classmethod
    def _validate_rule_call(cls, value, varprefix):
        (_pack_id, rule_id), arguments = value
        bi_rule = get_cached_bi_packs().get_rule(rule_id)
        if bi_rule is None:
            raise MKUserError(varprefix + "_1_0", _("The target rule is no longer available"))

        rule_params = bi_rule.params.arguments

        if len(arguments) != len(rule_params):
            raise MKUserError(
                varprefix + "_1_0",
                _(
                    "The rule you selected needs %d argument(s) (%s), "
                    "but you configured %d arguments."
                )
                % (len(rule_params), ", ".join(rule_params), len(arguments)),
            )

    @classmethod
    def _allowed_rule_choices(cls):
        # TODO: cache
        choices = []
        for pack_id, bi_pack in sorted(get_cached_bi_packs().get_packs().items()):
            if may_use_rules_in_pack(bi_pack):
                pack_choices = [
                    (rule_id, "%s (%s)" % (bi_rule.title, rule_id))
                    for rule_id, bi_rule in bi_pack.get_rules().items()
                ]
                choices.append(
                    (
                        pack_id,
                        "%s (%s)" % (bi_pack.title, bi_pack.id),
                        DropdownChoice(
                            choices=sorted(pack_choices),
                            empty_text=_("There are no configured rules in this aggregation pack"),
                            on_change="cmk.bi.update_argument_hints();",
                        ),
                    )
                )

        return choices


def may_use_rules_in_pack(bi_pack):
    return bi_pack.public or is_contact_for_pack(bi_pack)


def is_contact_for_pack(bi_pack):
    if user.may("wato.bi_admin"):
        return True  # meaning I am admin

    assert user.id is not None
    contact_groups = userdb.contactgroups_of_user(user.id)
    if contact_groups is None:
        return True

    for group in contact_groups:
        if group in bi_pack.contact_groups:
            return True
    return False


@bi_config_action_registry.register
class BIConfigStateOfHostAction(bi_actions.BIStateOfHostAction, ABCBIConfigAction):
    @classmethod
    def cascading_dropdown_choice_element(cls):
        return (cls.type(), _("State of a host"), cls.valuespec())

    @classmethod
    def valuespec(cls):
        return Dictionary(
            help=_(
                "Will create child nodes representing the state of hosts (usually the "
                "host check is done via ping)."
            ),
            elements=[cls.get_state_of_host_choice()],
            optional_keys=[],
        )

    @classmethod
    def get_state_of_host_choice(cls):
        return (
            "host_regex",
            TextInput(
                title=_("Host:"),
                help=_(
                    "Either an exact host name or a regular expression exactly matching the host "
                    "name. Example: <tt>srv.*p</tt> will match <tt>srv4711p</tt> but not <tt>xsrv4711p2</tt>. "
                ),
                allow_empty=False,
            ),
        )


@bi_config_action_registry.register
class BIConfigStateOfServiceAction(bi_actions.BIStateOfServiceAction, ABCBIConfigAction):
    @classmethod
    def cascading_dropdown_choice_element(cls):
        return (cls.type(), _("State of a service"), cls.valuespec())

    @classmethod
    def valuespec(cls):
        return Dictionary(
            help=_("Will create child nodes representing the state of services."),
            elements=[
                BIConfigStateOfHostAction.get_state_of_host_choice(),
                cls._get_state_of_service_choice(),
            ],
            optional_keys=[],
        )

    @classmethod
    def _get_state_of_service_choice(cls):
        return (
            "service_regex",
            TextInput(
                title=_("Service Regex:"),
                help=_(
                    "A regular expression matching the <b>beginning</b> of a service "
                    "description. You can use a trailing <tt>$</tt> in order to define an "
                    "exact match. For each matching service on the specified hosts one child "
                    "node will be created. "
                ),
                size=80,
            ),
        )


@bi_config_action_registry.register
class BIConfigStateOfRemainingServicesAction(
    bi_actions.BIStateOfRemainingServicesAction, ABCBIConfigAction
):
    @classmethod
    def cascading_dropdown_choice_element(cls):
        return (cls.type(), _("State of remaining services"), cls.valuespec())

    @classmethod
    def valuespec(cls):
        return Dictionary(
            help=_(
                "Create a child node for each service on the specified hosts that is not "
                "contained in any other node of the aggregation."
            ),
            elements=[BIConfigStateOfHostAction.get_state_of_host_choice()],
            optional_keys=[],
        )


#   .--AggrFunction--------------------------------------------------------.
#   |      _                    _____                 _   _                |
#   |     / \   __ _  __ _ _ __|  ___|   _ _ __   ___| |_(_) ___  _ __     |
#   |    / _ \ / _` |/ _` | '__| |_ | | | | '_ \ / __| __| |/ _ \| '_ \    |
#   |   / ___ \ (_| | (_| | |  |  _|| |_| | | | | (__| |_| | (_) | | | |   |
#   |  /_/   \_\__, |\__, |_|  |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|   |
#   |          |___/ |___/                                                 |
#   +----------------------------------------------------------------------+


def get_aggregation_function_choices():
    choices: List[Any] = []
    for aggr_func_id, bi_aggr_func in bi_config_aggregation_function_registry.items():
        choices.append((aggr_func_id, bi_aggr_func.title(), bi_aggr_func.valuespec()))

    return Transform(
        CascadingDropdown(
            title=_("Aggregation Function"),
            help=_(
                "The aggregation function decides how the status of a node "
                "is constructed from the states of the child nodes."
            ),
            orientation="horizontal",
            choices=choices,
        ),
        forth=convert_to_cascading_vs_choice,
        back=convert_from_cascading_vs_choice,
    )


class ABCBIConfigAggregationFunction(ABCBIAggregationFunction):
    @classmethod
    def title(cls):
        raise NotImplementedError()

    @classmethod
    def valuespec(cls):
        raise NotImplementedError()


class BIConfigAggregationFunctionRegistry(
    plugin_registry.Registry[Type[ABCBIConfigAggregationFunction]]
):
    def plugin_name(self, instance) -> str:
        return instance.type()


bi_config_aggregation_function_registry = BIConfigAggregationFunctionRegistry()


@bi_config_aggregation_function_registry.register
class BIConfigAggregationFunctionBest(BIAggregationFunctionBest, ABCBIConfigAggregationFunction):
    def __str__(self):
        return _("Best state, %d nodes, restrict to %s") % (
            self.count,
            short_service_state_name(self.restrict_state),
        )

    @classmethod
    def title(cls):
        return _("Best - take best of all node states")

    @classmethod
    def valuespec(cls):
        def convert_to_vs(value):
            return value["count"], value["restrict_state"]

        def convert_from_vs(value):
            return {
                "type": cls.type(),
                "count": value[0],
                "restrict_state": value[1],
            }

        return Transform(
            Tuple(
                elements=[
                    Integer(
                        help=_(
                            "Normally this value is <tt>1</tt>, which means that the best state "
                            "of all child nodes is being used as the total state. If you set it for example "
                            "to <tt>2</tt>, then the node with the best state is not being regarded. "
                            "If the states of the child nodes would be CRIT, WARN and OK, then to total "
                            "state would be WARN."
                        ),
                        title=_("Take n'th best state for n = "),
                        default_value=1,
                        minvalue=1,
                    ),
                    MonitoringState(
                        title=_("Restrict severity to at worst"),
                        help=_(
                            "Here a maximum severity of the node state can be set. This severity is not "
                            "exceeded, even if some of the childs have more severe states."
                        ),
                        default_value=2,
                    ),
                ]
            ),
            forth=convert_to_vs,
            back=convert_from_vs,
        )


@bi_config_aggregation_function_registry.register
class BIConfigAggregationFunctionWorst(BIAggregationFunctionWorst, ABCBIConfigAggregationFunction):
    def __str__(self):
        return _("Worst state, %d nodes, restrict to %s") % (
            self.count,
            short_service_state_name(self.restrict_state),
        )

    @classmethod
    def title(cls):
        return _("Worst - take worst of all node states")

    @classmethod
    def valuespec(cls):
        def convert_to_vs(value):
            return value["count"], value["restrict_state"]

        def convert_from_vs(value):
            return {
                "type": cls.type(),
                "count": value[0],
                "restrict_state": value[1],
            }

        return Transform(
            Tuple(
                elements=[
                    Integer(
                        help=_(
                            "Normally this value is <tt>1</tt>, which means that the worst state "
                            "of all child nodes is being used as the total state. If you set it for example "
                            "to <tt>3</tt>, then instead the node with the 3rd worst state is being regarded. "
                            "Example: In the case of five nodes with the states CRIT CRIT WARN OK OK then "
                            "resulting state would be WARN. Or you could say that the worst to nodes are "
                            "first dropped and then the worst of the remaining nodes defines the state. "
                        ),
                        title=_("Take n'th worst state for n = "),
                        default_value=1,
                        minvalue=1,
                    ),
                    MonitoringState(
                        title=_("Restrict severity to at worst"),
                        help=_(
                            "Here a maximum severity of the node state can be set. This severity is not "
                            "exceeded, even if some of the childs have more severe states."
                        ),
                        default_value=2,
                    ),
                ]
            ),
            forth=convert_to_vs,
            back=convert_from_vs,
        )


@bi_config_aggregation_function_registry.register
class BIConfigAggregationFunctionCountOK(
    BIAggregationFunctionCountOK, ABCBIConfigAggregationFunction
):
    def __str__(self):
        info = []
        for state, settings in [(_("OK"), self.levels_ok), (_("WARN"), self.levels_warn)]:
            if settings["type"] == "count":
                info.append(
                    "%(state)s (%(value)s OK nodes)" % {"state": state, "value": settings["value"]}
                )
            else:
                info.append(
                    "%(state)s (%(value)s%% OK nodes)"
                    % {"state": state, "value": settings["value"]}
                )

        return ",".join(info)

    @classmethod
    def title(cls):
        return _("Count the number of nodes in state OK")

    @classmethod
    def valuespec(cls):
        def convert_to_vs(value):
            result = []
            for what in ["levels_ok", "levels_warn"]:
                field = value[what]
                if field["type"] == "count":
                    result.append(field["value"])
                else:
                    result.append("%s%%" % field["value"])

            return tuple(result)

        def convert_from_vs(value):
            result: Dict[str, Union[str, Dict[str, Union[int, str]]]] = {"type": cls.type()}

            for name, number in [("levels_ok", value[0]), ("levels_warn", value[1])]:
                result[name] = {
                    "type": "count" if isinstance(number, int) else "percentage",
                    "value": number if isinstance(number, int) else int(number.rstrip("%")),
                }
            return result

        return Transform(
            Tuple(
                elements=[
                    cls._vs_count_ok_count(
                        _("Required number of OK-nodes for a total state of OK:"), 2, 50
                    ),
                    cls._vs_count_ok_count(
                        _("Required number of OK-nodes for a total state of WARN:"), 1, 25
                    ),
                ]
            ),
            forth=convert_to_vs,
            back=convert_from_vs,
        )

    @classmethod
    def _vs_count_ok_count(cls, title: str, defval: int, defvalperc: int) -> Alternative:
        return Alternative(
            title=title,
            style="dropdown",
            match=lambda x: str(x).endswith("%") and 1 or 0,
            elements=[
                Integer(
                    title=_("Explicit number"),
                    label=_("Number of OK-nodes"),
                    minvalue=0,
                    default_value=defval,
                ),
                Transform(
                    Percentage(
                        label=_("Percent of OK-nodes"),
                        display_format="%.0f",
                        default_value=defvalperc,
                    ),
                    title=_("Percentage"),
                    forth=lambda x: float(x[:-1]),
                    back=lambda x: "%d%%" % x,
                ),
            ],
        )
