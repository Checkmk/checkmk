#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.defines as defines
import cmk.utils.paths

from cmk.gui.i18n import _
from cmk.gui.inventory import vs_element_inventory_visible_raw_path, vs_inventory_path_or_keys_help
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_group_registry,
    rulespec_registry,
    RulespecGroup,
)
from cmk.gui.valuespec import (
    Age,
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    DualListChoice,
    ListOf,
    ListOfStrings,
    MonitoringState,
    RegExp,
    TextInput,
    Transform,
    ValueSpec,
)


@rulespec_group_registry.register
class RulespecGroupInventory(RulespecGroup):
    @property
    def name(self) -> str:
        return "inventory"

    @property
    def title(self) -> str:
        return _("Hardware / Software Inventory")

    @property
    def help(self):
        return _("Configuration of the Checkmk Hardware and Software Inventory System")


def _valuespec_active_checks_cmk_inv():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "sw_changes",
                    MonitoringState(
                        title=_("State when software changes are detected"),
                        default_value=0,
                    ),
                ),
                (
                    "sw_missing",
                    MonitoringState(
                        title=_("State when software packages info is missing"),
                        default_value=0,
                    ),
                ),
                (
                    "hw_changes",
                    MonitoringState(
                        title=_("State when hardware changes are detected"),
                        default_value=0,
                    ),
                ),
                (
                    "fail_status",
                    MonitoringState(
                        title=_("State when inventory fails"),
                        help=_(
                            "The check takes this state in case the inventory cannot be "
                            "updated because of any possible reason. A common use is "
                            "setting this to OK for workstations that can be switched "
                            "off - so you will get no notifications in that case."
                        ),
                        default_value=1,
                    ),
                ),
                (
                    "status_data_inventory",
                    DropdownChoice(
                        title=_("Status data inventory"),
                        help=_(
                            "All hosts configured via this ruleset will do a hardware and "
                            "software inventory after every check cycle if there's at least "
                            "one inventory plugin which processes status data. "
                            "<b>Note:</b> in order to get any useful "
                            "result for agent based hosts make sure that you have installed "
                            "the agent plugin <tt>mk_inventory</tt> on these hosts."
                        ),
                        choices=[
                            (True, _("Do status data inventory")),
                            (False, _("Do not status data inventory")),
                        ],
                        default_value=True,
                    ),
                ),
            ]
        ),
        title=_("Do hardware/software inventory"),
        help=_(
            "All hosts configured via this ruleset will do a hardware and "
            "software inventory. For each configured host a new active check "
            "will be created. You should also create a rule for changing the "
            "normal interval for that check to something between a couple of "
            "hours and one day. "
            "<b>Note:</b> in order to get any useful "
            "result for agent based hosts make sure that you have installed "
            "the agent plugin <tt>mk_inventory</tt> on these hosts."
        ),
        forth=lambda x: x is not None and x or {},  # convert from legacy None
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupInventory,
        match_type="all",
        name="active_checks:cmk_inv",
        valuespec=_valuespec_active_checks_cmk_inv,
    )
)


def _valuespec_inv_exports_software_csv() -> Dictionary:
    return Dictionary(
        title=_("Export List of Software packages as CSV file"),
        elements=[
            (
                "filename",
                TextInput(
                    title=_(
                        "Export file to create, containing <tt>&lt;HOST&gt;</tt> for the hostname"
                    ),
                    help=_(
                        "Please specify the path to the export file. The text <tt>[HOST]</tt> "
                        "will be replaced with the host name the inventory has been done for. "
                        "If you use a relative path then that will be relative to Check_MK's directory "
                        "for variable data, which is <tt>%s</tt>."
                    )
                    % cmk.utils.paths.var_dir,
                    allow_empty=False,
                    size=64,
                    default_value="csv-export/[HOST].csv",
                ),
            ),
            (
                "separator",
                TextInput(
                    title=_("Separator"),
                    allow_empty=False,
                    size=1,
                    default_value=";",
                ),
            ),
            (
                "quotes",
                DropdownChoice(
                    title=_("Quoting"),
                    choices=[
                        (None, _("Don't use quotes")),
                        ("single", _("Use single quotes, escape contained quotes with backslash")),
                        ("double", _("Use double quotes, escape contained quotes with backslash")),
                    ],
                    default_value=None,
                ),
            ),
            (
                "headers",
                DropdownChoice(
                    title=_("Column headers"),
                    choices=[
                        (False, _("Do not add column headers")),
                        (True, _("Add a first row with column titles")),
                    ],
                    default_value=False,
                ),
            ),
        ],
        required_keys=["filename"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupInventory,
        name="inv_exports:software_csv",
        valuespec=_valuespec_inv_exports_software_csv,
    )
)


def _valuespec_inv_parameters_inv_if():
    return Dictionary(
        title=_("Parameters for switch port inventory"),
        elements=[
            (
                "unused_duration",
                Age(
                    title=_("Port down time until considered unused"),
                    help=_("After this time in the state <i>down</i> a port is considered unused."),
                    default_value=30 * 86400,
                ),
            ),
            (
                "usage_port_types",
                DualListChoice(
                    title=_("Port types to include in usage statistics"),
                    choices=defines.interface_port_types(),
                    autoheight=False,
                    rows=40,
                    enlarge_active=False,
                    custom_order=True,
                    default_value=[
                        "6",
                        "32",
                        "62",
                        "117",
                        "127",
                        "128",
                        "129",
                        "180",
                        "181",
                        "182",
                        "205",
                        "229",
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupInventory,
        match_type="dict",
        name="inv_parameters:inv_if",
        valuespec=_valuespec_inv_parameters_inv_if,
    )
)


def _valuespec_inv_parameters_lnx_sysctl():
    return Dictionary(
        title=_("Inventory of Linux kernel configuration (sysctl)"),
        help=_(
            "This rule allows for defining regex-patterns for in- and excluding kernel "
            "configuration parameters in the inventory. By default, no parameters are included. "
            "Note that some kernel configuration parameters change frequently. Inventorizing "
            "one of these parameters will lead to frequent changes in the HW/SW inventory, "
            "which can quickly fill up the temporary file system."
        ),
        elements=[
            (
                "include_patterns",
                ListOfStrings(
                    valuespec=RegExp(mode=RegExp.prefix),
                    title=_("Inclusion patterns"),
                    help=_(
                        "Define patterns for including kernel configuration parameters in the "
                        "inventory."
                    ),
                ),
            ),
            (
                "exclude_patterns",
                ListOfStrings(
                    valuespec=RegExp(mode=RegExp.prefix),
                    title=_("Exclusion patterns"),
                    help=_(
                        "Define patterns for excluding kernel configuration parameters from the "
                        "inventory."
                    ),
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupInventory,
        match_type="dict",
        name="inv_parameters:lnx_sysctl",
        valuespec=_valuespec_inv_parameters_lnx_sysctl,
    )
)


def _valuespec_inv_retention_intervals() -> ValueSpec:
    def vs_choices(title):
        return CascadingDropdown(
            title=title,
            choices=[
                ("all", _("Choose all")),
                (
                    "choices",
                    _("Choose the following keys"),
                    ListOfStrings(
                        orientation="horizontal",
                        size=15,
                        allow_empty=True,
                    ),
                ),
            ],
            default_value="choices",
        )

    return ListOf(
        valuespec=Dictionary(
            elements=[
                (
                    "interval",
                    Age(
                        title=_("How long single values or table columns are kept."),
                        minvalue=1,
                        default_value=3600 * 2,
                        display=["days", "hours", "minutes"],
                    ),
                ),
                vs_element_inventory_visible_raw_path(),
                ("attributes", vs_choices(_("Choose single values"))),
                ("columns", vs_choices(_("Choose table columns"))),
            ],
            optional_keys=["attributes", "columns"],
        ),
        title=_("Retention intervals for HW/SW inventory entities"),
        help=vs_inventory_path_or_keys_help()
        + _(
            "<br>With these intervals specific single values or table columns can be kept"
            " from the previous inventory tree if the current agent output does not"
            " provide any new data for these entries."
            "<br>Only entries corresponding to chosen single values or columns are added."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupInventory,
        match_type="all",
        name="inv_retention_intervals",
        valuespec=_valuespec_inv_retention_intervals,
    )
)
