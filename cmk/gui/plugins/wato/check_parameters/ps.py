#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import re
from typing import Any, Dict

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupEnforcedServicesApplications,
    UserIconOrAction,
)
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    DropdownChoices,
    Filesize,
    FixedValue,
    Integer,
    Labels,
    ListChoice,
    ListOf,
    MonitoringState,
    Percentage,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)

# This object indicates that the setting 'CPU rescale maximum load' has not been set, which can only
# be the case for legacy rules from before version 1.6.0, see werk #6646. Note that we cannot use
# None here because DropdownChoice only renders invalid_choice_title if the input value is not
# None...
CPU_RESCALE_MAX_UNSPEC = "cpu_rescale_max_unspecified"


def process_level_elements():
    cpu_rescale_max_choices: DropdownChoices = [
        (
            True,
            # xgettext: no-python-format
            _("100% is all cores at full load"),
        ),
        (False, _("N * 100% as each core contributes with 100% at full load")),
    ]
    return [
        (
            "cpu_rescale_max",
            DropdownChoice(
                title=_("CPU rescale maximum load"),
                help=_(
                    "CPU utilization is delivered by the Operating "
                    "System as a per CPU core basis. Thus each core contributes "
                    "with a 100% at full utilization, producing a maximum load "
                    "of N*100% (N=number of cores). For simplicity this maximum "
                    "can be rescaled down, making 100% the maximum and thinking "
                    "in terms of total CPU utilization."
                ),
                default_value=True,
                choices=cpu_rescale_max_choices,
                invalid_choice_title=_("Unspecified.")
                + " "
                + _(
                    "Starting from version 1.6.0 this value must be configured. "
                    "Read Werk #6646 for further information."
                ),
                invalid_choice_error=_("CPU rescale maximum load is Unspecified.")
                + " "
                + _(
                    "Starting from version 1.6.0 this value must be configured. "
                    "Read Werk #6646 for further information."
                ),
                deprecated_choices=[CPU_RESCALE_MAX_UNSPEC],
            ),
        ),
        (
            "levels",
            Tuple(
                title=_("Levels for process count"),
                help=_(
                    "Please note that if you specify and also if you modify levels "
                    "here, the change is activated only during an inventory."
                    "Saving this rule is not enough. This is due to the nature of"
                    "inventory rules."
                ),
                elements=[
                    Integer(
                        title=_("Critical below"),
                        unit=_("processes"),
                        default_value=1,
                    ),
                    Integer(
                        title=_("Warning below"),
                        unit=_("processes"),
                        default_value=1,
                    ),
                    Integer(
                        title=_("Warning above"),
                        unit=_("processes"),
                        default_value=99999,
                    ),
                    Integer(
                        title=_("Critical above"),
                        unit=_("processes"),
                        default_value=99999,
                    ),
                ],
            ),
        ),
        (
            "cpulevels",
            Tuple(
                title=_("Levels on total CPU utilization"),
                help=_(
                    "By activating this options you can set levels on the total "
                    "CPU utilization of all included processes."
                ),
                elements=[
                    Percentage(title=_("Warning at"), default_value=90, maxvalue=10000),
                    Percentage(title=_("Critical at"), default_value=98, maxvalue=10000),
                ],
            ),
        ),
        (
            "cpu_average",
            Integer(
                title=_("CPU Averaging"),
                help=_(
                    "By activating averaging, Check_MK will compute the average of "
                    "the total CPU utilization over a given interval. If you have defined "
                    "alerting levels then these will automatically be applied on the "
                    "averaged value. This helps to mask out short peaks. "
                ),
                unit=_("minutes"),
                minvalue=1,
                default_value=15,
            ),
        ),
        (
            "single_cpulevels",
            Tuple(
                title=_("Levels on CPU utilization of a single process"),
                help=_(
                    "Here you can define levels on the CPU utilization of single "
                    "processes. For performance reasons CPU Averaging will not be "
                    "applied to to the levels of single processes."
                ),
                elements=[
                    Percentage(title=_("Warning at"), default_value=90, maxvalue=10000),
                    Percentage(title=_("Critical at"), default_value=98, maxvalue=10000),
                ],
            ),
        ),
        (
            "min_age",
            Tuple(
                title=_("Minimum allowed age"),
                help=_(
                    "Set lower levels on the age of the process (not the consumed CPU time, "
                    "but the real time)."
                ),
                elements=[
                    Age(title=_("Warning at"), default_value=3600),
                    Age(title=_("Critical at"), default_value=1800),
                ],
            ),
        ),
        (
            "max_age",
            Tuple(
                title=_("Maximum allowed age"),
                help=_(
                    "Set upper levels on the age of the process (not the consumed CPU time, "
                    "but the real time)."
                ),
                elements=[
                    Age(title=_("Warning at"), default_value=3600),
                    Age(title=_("Critical at"), default_value=7200),
                ],
            ),
        ),
        (
            "virtual_levels",
            Tuple(
                title=_("Virtual memory usage"),
                elements=[
                    Filesize(title=_("Warning at"), default_value=1000 * 1024 * 1024 * 1024),
                    Filesize(title=_("Critical at"), default_value=2000 * 1024 * 1024 * 1024),
                ],
            ),
        ),
        (
            "resident_levels",
            Tuple(
                title=_("Physical memory usage"),
                elements=[
                    Filesize(title=_("Warning at"), default_value=100 * 1024 * 1024),
                    Filesize(title=_("Critical at"), default_value=200 * 1024 * 1024),
                ],
            ),
        ),
        (
            "resident_levels_perc",
            Tuple(
                title=_("Physical memory usage, in percentage of total RAM"),
                elements=[
                    Percentage(title=_("Warning at"), default_value=25.0),
                    Percentage(title=_("Critical at"), default_value=50.0),
                ],
            ),
        ),
        (
            "handle_count",
            Tuple(
                title=_("Handle Count (Windows only)"),
                help=_(
                    "The number of object handles in the processes object table. This includes "
                    "open handles to threads, files and other resources like registry keys."
                ),
                elements=[
                    Integer(
                        title=_("Warning above"),
                        unit=_("handles"),
                    ),
                    Integer(
                        title=_("Critical above"),
                        unit=_("handles"),
                    ),
                ],
            ),
        ),
        (
            "process_info",
            DropdownChoice(
                title=_("Enable per-process details in long-output"),
                label=_("Enable per-process details"),
                help=_(
                    "If active, the long output of this service will contain a list of all the "
                    "matching processes and their details (i.e. PID, CPU usage, memory usage). "
                    "Please note that HTML output will only work if rules in the rulesets "
                    '"%s" or "%s" are created or the global setting "%s" is disabled. '
                    "This might expose you to Cross-Site-Scripting attacks (everyone with "
                    "write-access to checks could get scripts executed on the monitoring site "
                    "in the context of the user of the monitoring site), so please do this if "
                    "you understand the consequences."
                )
                % (
                    _("Escape HTML codes in host output"),
                    _("Escape HTML codes in service output"),
                    _("Escape HTML codes in service output"),
                ),
                choices=[
                    (None, _("Disable")),
                    ("text", _("Text output")),
                    ("html", _("HTML output")),
                ],
                default_value=None,
            ),
        ),
        (
            "process_info_arguments",
            Integer(
                title=_("Include process arguments in long-output"),
                label=_("Include per-process arguments (security risk!)"),
                help=_(
                    "If non-zero, the list of all the matching processes and their details in the"
                    " long-output will include up to the first N characters of all arguments for each"
                    " process. Please note this may include sensitive data like credentials,"
                    " and is strongly discouraged."
                ),
                default_value=0,
            ),
        ),
        (
            "icon",
            UserIconOrAction(
                title=_("Add custom icon or action"),
                help=_("You can assign icons or actions to the found services in the status GUI."),
            ),
        ),
    ]


# Add checks that have parameters but are only configured as manual checks
def ps_cleanup_params(params):
    # New parameter format: dictionary. Example:
    # {
    #    "user" : "foo",
    #    "process" : "/usr/bin/food",
    #    "warnmin" : 1,
    #    "okmin"   : 1,
    #    "okmax"   : 1,
    #    "warnmax" : 1,
    # }

    # Even newer format:
    # {
    #   "user" : "foo",
    #   "levels" : (1, 1, 99999, 99999)
    # }

    # TODO: This is a workaround which makes sure input arguments are not getting altered.
    #       A nice implementation would return a new dict based on the input
    params = copy.deepcopy(params)

    if isinstance(params, (list, tuple)):
        if len(params) == 5:
            procname, warnmin, okmin, okmax, warnmax = params
            user = None
        elif len(params) == 6:
            procname, user, warnmin, okmin, okmax, warnmax = params
        params = {
            "process": procname,
            "levels": (warnmin, okmin, okmax, warnmax),
            "user": user,
        }

    elif any(k in params for k in ["okmin", "warnmin", "okmax", "warnmax"]):
        params["levels"] = (
            params.pop("warnmin", 1),
            params.pop("okmin", 1),
            params.pop("okmax", 99999),
            params.pop("warnmax", 99999),
        )

    if "cpu_rescale_max" not in params:
        params["cpu_rescale_max"] = CPU_RESCALE_MAX_UNSPEC

    return params


def ps_convert_inventorized_from_singlekeys(old_params):
    params = ps_cleanup_params(old_params)
    if "user" in params:
        del params["user"]
    if "process" in params:
        del params["process"]
    return params


def forbid_re_delimiters_inside_groups(pattern, varprefix):
    # Used as input validation in PS check wato config
    group_re = r"\(.*?\)"
    for match in re.findall(group_re, pattern):
        for char in ["\\b", "$", "^"]:
            if char in match:
                raise MKUserError(
                    varprefix,
                    _(
                        '"%s" is not allowed inside the regular expression group %s. '
                        "Bounding characters inside groups will vanish after discovery, "
                        "because processes are instanced for every matching group. "
                        "Thus enforce delimiters outside the group."
                    )
                    % (char, match),
                )


def match_alt(x):
    if x is False:
        return 3
    if x is None or x == "":
        return 2
    if x.startswith("~"):
        return 1
    return 0


def validate_process_discovery_descr_option(description, varprefix):
    if "%s" in description and re.search(r"%(\d+)", description):
        raise MKUserError(
            varprefix,
            _(
                'Combining "%s" and "%1" style replacements in the sevice description is not allowed.'
            ),
        )


def process_discovery_descr_option():
    return TextInput(
        title=_("Process Name"),
        allow_empty=False,
        validate=validate_process_discovery_descr_option,
        help=_(
            "<p>The process name may contain one or more occurrences of <tt>%s</tt>. If "
            "you do this, then the pattern must be a regular expression and be prefixed "
            "with ~. For each <tt>%s</tt> in the description, the expression has to "
            'contain one "group". A group is a subexpression enclosed in brackets, '
            "for example <tt>(.*)</tt> or <tt>([a-zA-Z]+)</tt> or <tt>(...)</tt>. "
            "When the inventory finds a process matching the pattern, it will "
            "substitute all such groups with the actual values when creating the "
            "check. That way one rule can create several checks on a host.</p>"
            "<p>If the pattern contains more groups then occurrences of <tt>%s</tt> in "
            "the service description then only the first matching subexpressions are "
            "used for the service descriptions. The matched substrings corresponding to "
            "the remaining groups are copied into the regular expression, "
            "nevertheless.</p>"
            "<p>As an alternative to <tt>%s</tt> you may also use <tt>%1</tt>, "
            "<tt>%2</tt>, etc.  These will be replaced by the first, second, "
            "... matching group. This allows you to reorder thing"
        ),
    )


def process_match_options():
    return Alternative(
        title=_("Process Matching"),
        elements=[
            TextInput(
                title=_("Exact name of the process without arguments"),
                label=_("Executable:"),
                size=50,
            ),
            Transform(
                RegExp(
                    size=50,
                    label=_("Command line:"),
                    mode=RegExp.prefix,
                    validate=forbid_re_delimiters_inside_groups,
                ),
                title=_("Regular expression matching command line"),
                help=_(
                    "This regex must match the <i>beginning</i> of the complete "
                    "command line of the process including arguments.<br>"
                    "When using groups, matches will be instantiated "
                    "during process discovery. e.g. (py.*) will match python, python_dev "
                    "and python_test and discover 3 services. At check time, because "
                    "python is a substring of python_test and python_dev it will aggregate"
                    "all process that start with python. If that is not the intended behavior "
                    "please use a delimiter like '$' or '\\b' around the group, e.g. (py.*)$<br>"
                    "In manual check groups are aggregated"
                ),
                forth=lambda x: x[1:],  # remove ~
                back=lambda x: "~" + x,  # prefix ~
            ),
            FixedValue(
                value=None,
                totext="",
                title=_("Match all processes"),
            ),
        ],
        match=match_alt,
        default_value="/usr/sbin/foo",
    )


def user_match_options(extra_elements=None):
    if extra_elements is None:
        extra_elements = []

    return Alternative(
        title=_("Name of operating system user"),
        elements=[
            TextInput(
                title=_("Exact name of the operating system user"), label=_("User:"), size=50
            ),
            Transform(
                RegExp(
                    size=50,
                    mode=RegExp.prefix,
                ),
                title=_("Regular expression matching username"),
                help=_("This regex must match the <i>beginning</i> of the complete " "username"),
                forth=lambda x: x[1:],  # remove ~
                back=lambda x: "~" + x,  # prefix ~
            ),
            FixedValue(
                value=None,
                totext="",
                title=_("Match all users"),
            ),
        ]
        + extra_elements,
        match=match_alt,
        help=_(
            "<p>The user specification is a user name (string). The "
            "inventory will then trigger only if that user matches the user the "
            "process is running as. The resulting check will require such "
            "user. If user is not "
            "selected the created check will not look for a specific user.</p> "
            "<p>Windows users are specified by the namespace followed "
            'by the actual user name. For example "\\\\NT AUTHORITY\\NETWORK '
            'SERVICE" or "\\\\CHKMKTEST\\Administrator".</p> '
        ),
    )


def cgroup_match_options():
    return Tuple(
        title=_("Operating system control group information"),
        elements=[
            Alternative(
                elements=[
                    TextInput(
                        title=_("Exact content of the operating system control group info"),
                        label=_("Control group:"),
                        size=50,
                    ),
                    Transform(
                        RegExp(
                            size=50,
                            mode=RegExp.prefix,
                        ),
                        title=_("Regular expression matching control group info"),
                        help=_(
                            "This regex must match the <i>beginning</i> of the complete "
                            "control group information"
                        ),
                        forth=lambda x: x[1:],  # remove ~
                        back=lambda x: "~" + x,  # prefix ~
                    ),
                    FixedValue(
                        value=None,
                        totext="",
                        title=_("Match all control groups"),
                    ),
                ],
                match=match_alt,
                help=_(
                    "<p>The control group information is currently only specified by the linux agent"
                    " (cgroup). If it is present and this rule is set, the inventory will only trigger"
                    " if the control group of the corresponding process matches."
                    " For instance: you can use this rule to exclude all processes belonging to"
                    ' a docker container by specifying the expression "%s" (without the quotes),'
                    ' and selecting "%s".</p>'
                )
                % (r".*/docker/", _("Invert matching")),
            ),
            Checkbox(label=_("Invert matching"), default_value=False),
        ],
    )


def _item_spec_ps():
    return TextInput(
        title=_("Discovered process name"),
    )


def _parameter_valuespec_ps():
    return Transform(
        Dictionary(
            elements=process_level_elements(),
            ignored_keys=["match_groups", "cgroup"],
            required_keys=["cpu_rescale_max"],
        ),
        forth=ps_convert_inventorized_from_singlekeys,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ps",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_ps,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ps,
        title=lambda: _("State and count of processes"),
    )
)


# Rule for static process checks
def _manual_item_spec_ps():
    return TextInput(
        title=_("Process Name"),
        help=_("This name will be used in the description of the service"),
        allow_empty=False,
        regex="^[a-zA-Z_0-9 _./-]*$",
        regex_error=_(
            "Please use only a-z, A-Z, 0-9, space, underscore, "
            "dot, hyphen and slash for your service description"
        ),
    )


def _manual_parameter_valuespec_ps():
    return Transform(
        Dictionary(
            elements=[
                ("process", process_match_options()),
                ("user", user_match_options()),
            ]
            + process_level_elements(),
            ignored_keys=["match_groups"],
            required_keys=["cpu_rescale_max"],
        ),
        forth=ps_cleanup_params,
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="ps",
        group=RulespecGroupEnforcedServicesApplications,
        item_spec=_manual_item_spec_ps,
        parameter_valuespec=_manual_parameter_valuespec_ps,
        title=lambda: _("State and count of processes"),
    )
)


# In version 1.2.4 the check parameters for the resulting ps check
# where defined in the discovery rule. We moved that to an own rule
# in the classical check parameter style. In order to support old
# configuration we allow reading old discovery rules and ship these
# settings in an optional sub-dictionary.
def convert_inventory_processes(old_dict):
    new_dict: Dict[str, Dict[str, Any]] = {"default_params": {}}
    for key in old_dict:
        if key in [
            "levels",
            "handle_count",
            "cpulevels",
            "cpu_average",
            "virtual_levels",
            "resident_levels",
        ]:
            new_dict["default_params"][key] = old_dict[key]
        elif key != "perfdata":
            new_dict[key] = old_dict[key]

    # cmk1.6 cpu rescaling load rule
    if "cpu_rescale_max" not in old_dict.get("default_params", {}):
        new_dict["default_params"]["cpu_rescale_max"] = CPU_RESCALE_MAX_UNSPEC

    # cmk1.6 move icon into default_params to match setup of static and discovered ps checks
    if "icon" in old_dict:
        new_dict["default_params"]["icon"] = old_dict.pop("icon")

    return new_dict


def _valuespec_inventory_processes_rules() -> Transform:
    return Transform(
        Dictionary(
            title=_("Process discovery"),
            help=_(
                "This ruleset defines criteria for automatically creating checks for running "
                "processes based upon what is running when the service discovery is "
                "done. These services will be created with default parameters. They will get "
                "critical when no process is running and OK otherwise. You can parameterize "
                "the check with the ruleset <i>State and count of processes</i>."
            ),
            elements=[
                ("descr", process_discovery_descr_option()),
                ("match", process_match_options()),
                (
                    "user",
                    user_match_options(
                        [
                            FixedValue(
                                value=False,
                                title=_("Grab user from found processess"),
                                totext="",
                                help=_(
                                    'Specifying "grab user" makes the created check expect the process to '
                                    "run as the same user as during inventory: the user name will be "
                                    "hardcoded into the check. In that case if you put %u into the service "
                                    "description, that will be replaced by the actual user name during "
                                    "inventory. You need that if your rule might match for more than one "
                                    "user - your would create duplicate services with the same description "
                                    "otherwise."
                                ),
                            )
                        ]
                    ),
                ),
                ("cgroup", cgroup_match_options()),
                (
                    "label",
                    Labels(
                        Labels.World.CONFIG,
                        title=_("Host Label"),
                        help=_(
                            "Here you can set host labels that automatically get created when discovering the services."
                        ),
                    ),
                ),
                (
                    "default_params",
                    Dictionary(
                        title=_("Default parameters for detected services"),
                        help=_(
                            "Here you can select default parameters that are being set "
                            "for detected services. Note: the preferred way for setting parameters is to use "
                            'the rule set <a href="wato.py?varname=checkgroup_parameters:ps&mode=edit_ruleset"> '
                            "State and Count of Processes</a> instead. "
                            "A change there will immediately be active, while a change in this rule "
                            "requires a re-discovery of the services."
                        ),
                        elements=process_level_elements(),
                        ignored_keys=["match_groups"],
                        required_keys=["cpu_rescale_max"],
                    ),
                ),
            ],
            required_keys=["descr", "default_params"],
        ),
        forth=convert_inventory_processes,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="inventory_processes_rules",
        valuespec=_valuespec_inventory_processes_rules,
    )
)

#   .--SNMP processes------------------------------------------------------.
#   |                      ____  _   _ __  __ ____                         |
#   |                     / ___|| \ | |  \/  |  _ \                        |
#   |                     \___ \|  \| | |\/| | |_) |                       |
#   |                      ___) | |\  | |  | |  __/                        |
#   |                     |____/|_| \_|_|  |_|_|                           |
#   |                                                                      |
#   |                                                                      |
#   |             _ __  _ __ ___   ___ ___  ___ ___  ___  ___              |
#   |            | '_ \| '__/ _ \ / __/ _ \/ __/ __|/ _ \/ __|             |
#   |            | |_) | | | (_) | (_|  __/\__ \__ \  __/\__ \             |
#   |            | .__/|_|  \___/ \___\___||___/___/\___||___/             |
#   |            |_|                                                       |
#   '----------------------------------------------------------------------'


def match_hr_alternative(x):
    if x.startswith("~"):
        return 1
    return 0


def hr_process_match_name_option():
    return Alternative(
        title=_("Process Name Matching"),
        elements=[
            TextInput(
                title=_("Exact name of the textual description"),
                size=50,
                allow_empty=False,
            ),
            Transform(
                RegExp(
                    size=50,
                    mode=RegExp.prefix,
                    validate=forbid_re_delimiters_inside_groups,
                    allow_empty=False,
                ),
                title=_("Regular expression matching the textual description"),
                help=_(
                    "This regex must match the <i>beginning</i> of the complete "
                    "textual description of the process including arguments.<br>"
                    "When using groups, matches will be instantiated "
                    "during process discovery. e.g. (py.*) will match python, python_dev "
                    "and python_test and discover 3 services. At check time, because "
                    "python is a substring of python_test and python_dev it will aggregate"
                    "all process that start with python. If that is not the intended behavior "
                    "please use a delimiter like '$' or '\\b' around the group, e.g. (py.*)$<br>"
                    "In manual check groups are aggregated"
                ),
                forth=lambda x: x[1:],  # remove ~
                back=lambda x: "~" + x,  # prefix ~
            ),
        ],
        match=match_hr_alternative,
        default_value="Foo Bar",
    )


def hr_process_match_path_option():
    return Alternative(
        title=_("Process Path Matching"),
        elements=[
            TextInput(
                title=_("Exact name of the process path"),
                size=50,
                allow_empty=False,
            ),
            Transform(
                RegExp(
                    size=50,
                    mode=RegExp.prefix,
                    validate=forbid_re_delimiters_inside_groups,
                    allow_empty=False,
                ),
                title=_("Regular expression matching the process path"),
                help=_(
                    "This regex must match the <i>beginning</i> of the complete "
                    "path of the process including arguments.<br>"
                    "When using groups, matches will be instantiated "
                    "during process discovery. e.g. (py.*) will match python, python_dev "
                    "and python_test and discover 3 services. At check time, because "
                    "python is a substring of python_test and python_dev it will aggregate"
                    "all process that start with python. If that is not the intended behavior "
                    "please use a delimiter like '$' or '\\b' around the group, e.g. (py.*)$<br>"
                    "In manual check groups are aggregated"
                ),
                forth=lambda x: x[1:],  # remove ~
                back=lambda x: "~" + x,  # prefix ~
            ),
        ],
        match=match_hr_alternative,
        default_value="/usr/sbin/foo",
    )


def hr_process_match_elements():
    return [
        (
            "match_name_or_path",
            CascadingDropdown(
                title=_("Process Match textual description or path of process"),
                choices=[
                    ("match_name", _("Match textual description"), hr_process_match_name_option()),
                    ("match_path", _("Match process path"), hr_process_match_path_option()),
                    ("match_all", _("Match all processes")),
                ],
            ),
        ),
        (
            "match_status",
            ListChoice(
                title=_("Process Status Matching"),
                choices=[
                    ("running", _("Running")),
                    ("runnable", _("Runnable (Waiting for resource)")),
                    ("not_runnable", _("Not runnable (Loaded but waiting for event)")),
                    ("invalid", _("Invalid (Not loaded)")),
                ],
            ),
        ),
    ]


def hr_process_parameter_elements():
    return [
        (
            "levels",
            Tuple(
                title=_("Levels for process count"),
                help=_(
                    "Please note that if you specify and also if you modify levels "
                    "here, the change is activated only during an inventory."
                    "Saving this rule is not enough. This is due to the nature of"
                    "inventory rules."
                ),
                elements=[
                    Integer(
                        title=_("Critical below"),
                        unit=_("processes"),
                        default_value=1,
                    ),
                    Integer(
                        title=_("Warning below"),
                        unit=_("processes"),
                        default_value=1,
                    ),
                    Integer(
                        title=_("Warning above"),
                        unit=_("processes"),
                        default_value=99999,
                    ),
                    Integer(
                        title=_("Critical above"),
                        unit=_("processes"),
                        default_value=99999,
                    ),
                ],
            ),
        ),
        (
            "status",
            ListOf(
                Tuple(
                    orientation="horizontal",
                    elements=[
                        DropdownChoice(
                            choices=[
                                ("running", _("Running")),
                                ("runnable", _("Runnable (Waiting for resource)")),
                                ("not_runnable", _("Not runnable (Loaded but waiting for event)")),
                                ("invalid", _("Invalid (Not loaded)")),
                            ]
                        ),
                        MonitoringState(),
                    ],
                ),
                title=_("Map process states"),
            ),
        ),
    ]


def _valuespec_discovery_hr_processes_rules():
    return Dictionary(
        title=_("Process discovery (only SNMP)"),
        help=_(
            "This ruleset defines criteria for automatically creating checks for running "
            "SNMP processes based upon the HOST Resource MIB and what is running when the "
            "service discovery is done. You can either specify the textual description "
            "or the path of process within the matching criteria."
        ),
        elements=[
            ("descr", process_discovery_descr_option()),
        ]
        + hr_process_match_elements()
        + [
            (
                "default_params",
                Dictionary(
                    title=_("Default parameters for detected services"),
                    help=_(
                        "Here you can select default parameters that are being set "
                        "for detected services. Note: the preferred way for setting parameters is to use "
                        'the rule set <a href="wato.py?varname=checkgroup_parameters:ps&mode=edit_ruleset"> '
                        "State and Count of Processes</a> instead. "
                        "A change there will immediately be active, while a change in this rule "
                        "requires a re-discovery of the services."
                    ),
                    elements=hr_process_parameter_elements(),
                    ignored_keys=["match_groups"],
                ),
            ),
        ],
        required_keys=["descr", "default_params"],
        ignored_keys=["match_groups"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="discovery_hr_processes_rules",
        valuespec=_valuespec_discovery_hr_processes_rules,
    )
)


def _parameter_valuespec_hr_ps():
    return Dictionary(
        help=_(
            "This ruleset defines criteria for SNMP processes base upon the HOST Resources MIB."
        ),
        elements=hr_process_parameter_elements(),
        ignored_keys=["match_name_or_path", "match_status", "match_groups"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hr_ps",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_ps,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hr_ps,
        title=lambda: _("State and count of processes (only SNMP)"),
    )
)


# Rule for static process checks
def _manual_item_spec_hr_ps():
    return TextInput(
        title=_("Process Name"),
        help=_("This name will be used in the description of the service"),
        allow_empty=False,
        regex="^[a-zA-Z_0-9 _./-]*$",
        regex_error=_(
            "Please use only a-z, A-Z, 0-9, space, underscore, "
            "dot, hyphen and slash for your service description"
        ),
    )


def _manual_parameter_valuespec_hr_ps():
    return Dictionary(
        elements=hr_process_match_elements() + hr_process_parameter_elements(),
        required_keys=["descr"],
        ignored_keys=["match_name_or_path", "match_status", "match_groups"],
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="hr_ps",
        group=RulespecGroupEnforcedServicesApplications,
        item_spec=_manual_item_spec_hr_ps,
        parameter_valuespec=_manual_parameter_valuespec_hr_ps,
        title=lambda: _("State and count of processes (only SNMP)"),
    )
)
