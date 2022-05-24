#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Tuple

import pytest  # type: ignore[import]

from cmk.gui.forms import remove_unused_vars
from cmk.gui.globals import html
from cmk.gui.wato.pages.rulesets import _is_var_to_delete


@pytest.mark.parametrize(
    "request_vars, expected_removed",
    [
        pytest.param(
            [
                (
                    "search_p_ruleset_group",
                    "8314def34678f3c2ab8fcb0f207f69fec2113942e2ac995e19b145497e629bf1",
                ),
                ("search_p_ruleset_name", ""),
                ("search_p_ruleset_title", ""),
                ("search_p_ruleset_help", ""),
                ("search_p_ruleset_deprecated_USE", "on"),
                (
                    "search_p_ruleset_deprecated",
                    "60a33e6cf5151f2d52eddae9685cfa270426aa89d8dbc7dfb854606f1d1a40fe",
                ),
                (
                    "search_p_ruleset_used",
                    "3cbc87c7681f34db4617feaa2c8801931bc5e42d8d0f560e756dd4cd92885f18",
                ),
                ("search_p_rule_description", ""),
                ("search_p_rule_comment", ""),
                ("search_p_rule_value", ""),
                ("search_p_rule_host_list", ""),
                ("search_p_rule_item_list", ""),
                ("search_p_rule_hosttags_tag_address_family", "ignore"),
                ("search_p_rule_hosttags_tagvalue_address_family", "ip-v4-only"),
                ("search_p_rule_hosttags_auxtag_ip-v4", "ignore"),
                ("search_p_rule_hosttags_auxtag_ip-v6", "ignore"),
                ("search_p_rule_hosttags_tag_agent", "ignore"),
                ("search_p_rule_hosttags_tagvalue_agent", "cmk-agent"),
                ("search_p_rule_hosttags_tag_piggyback", "ignore"),
                ("search_p_rule_hosttags_tagvalue_piggyback", "auto-piggyback"),
                ("search_p_rule_hosttags_tag_snmp_ds", "ignore"),
                ("search_p_rule_hosttags_tagvalue_snmp_ds", "no-snmp"),
                ("search_p_rule_hosttags_auxtag_snmp", "ignore"),
                ("search_p_rule_hosttags_auxtag_tcp", "ignore"),
                ("search_p_rule_hosttags_auxtag_ping", "ignore"),
                ("search_p_rule_hosttags_tag_criticality", "ignore"),
                ("search_p_rule_hosttags_tagvalue_criticality", "prod"),
                ("search_p_rule_hosttags_tag_networking", "ignore"),
                ("search_p_rule_hosttags_tagvalue_networking", "lan"),
                (
                    "search_p_rule_disabled",
                    "3cbc87c7681f34db4617feaa2c8801931bc5e42d8d0f560e756dd4cd92885f18",
                ),
                (
                    "search_p_rule_ineffective",
                    "3cbc87c7681f34db4617feaa2c8801931bc5e42d8d0f560e756dd4cd92885f18",
                ),
                ("search_p_rule_folder_USE", "ON"),
                (
                    "search_p_rule_folder_0",
                    "6f49cdbd80e1b95d5e6427e1501fc217790daee87055fa5b4e71064288bddede",
                ),
                (
                    "search_p_rule_folder_1",
                    "60a33e6cf5151f2d52eddae9685cfa270426aa89d8dbc7dfb854606f1d1a40fe",
                ),
            ],
            [
                "search_p_ruleset_group",
                "search_p_ruleset_name",
                "search_p_ruleset_title",
                "search_p_ruleset_help",
                "search_p_ruleset_used",
                "search_p_rule_description",
                "search_p_rule_comment",
                "search_p_rule_value",
                "search_p_rule_host_list",
                "search_p_rule_item_list",
                "search_p_rule_hosttags_tag_address_family",
                "search_p_rule_hosttags_tagvalue_address_family",
                "search_p_rule_hosttags_auxtag_ip-v4",
                "search_p_rule_hosttags_auxtag_ip-v6",
                "search_p_rule_hosttags_tag_agent",
                "search_p_rule_hosttags_tagvalue_agent",
                "search_p_rule_hosttags_tag_piggyback",
                "search_p_rule_hosttags_tagvalue_piggyback",
                "search_p_rule_hosttags_tag_snmp_ds",
                "search_p_rule_hosttags_tagvalue_snmp_ds",
                "search_p_rule_hosttags_auxtag_snmp",
                "search_p_rule_hosttags_auxtag_tcp",
                "search_p_rule_hosttags_auxtag_ping",
                "search_p_rule_hosttags_tag_criticality",
                "search_p_rule_hosttags_tagvalue_criticality",
                "search_p_rule_hosttags_tag_networking",
                "search_p_rule_hosttags_tagvalue_networking",
                "search_p_rule_disabled",
                "search_p_rule_ineffective",
            ],
            id="search_with_default_settings",
        ),
        pytest.param(
            [
                (
                    "search_p_ruleset_group",
                    "8314def34678f3c2ab8fcb0f207f69fec2113942e2ac995e19b145497e629bf1",
                ),
                ("search_p_ruleset_group_USE", "ON"),
                ("search_p_ruleset_name", "FO"),
                ("search_p_ruleset_name_USE", "ON"),
                ("search_p_ruleset_title", "FO"),
                ("search_p_ruleset_title_USE", "ON"),
                ("search_p_ruleset_help", "FO"),
                ("search_p_ruleset_help_USE", "ON"),
                (
                    "search_p_ruleset_used",
                    "3cbc87c7681f34db4617feaa2c8801931bc5e42d8d0f560e756dd4cd92885f18",
                ),
                ("search_p_ruleset_used_USE", "ON"),
                ("search_p_rule_hosttags_tag_agent", "ignore"),
            ],
            [
                "search_p_rule_hosttags_tag_agent",
            ],
            id="search_group_name_title_help_used",
        ),
        pytest.param(
            [
                ("search_p_rule_description", "FO"),
                ("search_p_rule_description_USE", "ON"),
                ("search_p_rule_comment", "FO"),
                ("search_p_rule_comment_USE", "ON"),
                ("search_p_rule_value", "FO"),
                ("search_p_rule_value_USE", "ON"),
                ("search_p_rule_hosttags_tag_agent", "ignore"),
            ],
            [
                "search_p_rule_hosttags_tag_agent",
            ],
            id="search_desc_comment_value",
        ),
        pytest.param(
            [
                ("search_p_rule_host_list", "stable+beta"),
                ("search_p_rule_host_list_USE", "ON"),
                ("search_p_rule_hosttags_tag_agent", "ignore"),
            ],
            [
                "search_p_rule_hosttags_tag_agent",
            ],
            id="search_host_match",
        ),
        pytest.param(
            [
                ("search_p_rule_item_list", "CPU"),
                ("search_p_rule_item_list_USE", "ON"),
                ("search_p_rule_hosttags_tag_agent", "ignore"),
            ],
            [
                "search_p_rule_hosttags_tag_agent",
            ],
            id="search_item_match",
        ),
        pytest.param(
            [
                ("search_p_rule_hosttags_USE", "ON"),
                ("search_p_rule_hosttags_tag_agent", "is"),
                ("search_p_rule_hosttags_tagvalue_agent", "cmk-agent"),
                ("search_p_rule_hosttags_tag_address_family", "is not"),
                ("search_p_rule_hosttags_tagvalue_address_family", "ip-v4-only"),
                ("search_p_rule_hosttags_tag_piggyback", "ignore"),
                ("search_p_rule_hosttags_tagvalue_piggyback", "auto-piggyback"),
                ("search_p_rule_hosttags_auxtag_ip-v4", "is"),
            ],
            [
                "search_p_rule_hosttags_tag_piggyback",
                "search_p_rule_hosttags_tagvalue_piggyback",
            ],
            id="search_hosttags",
        ),
    ],
)
def test_vars_to_delete(
    request_vars: List[Tuple[str, str]],
    expected_removed: List[str],
):
    form_prefix: str = "search_p_rule"
    for var, val in request_vars:
        html.request.set_var(var, val)

    remove_unused_vars(form_prefix, _is_var_to_delete)
    for varname, _value in html.request.itervars(form_prefix):
        if varname in expected_removed:
            assert not html.request.var(varname)
        else:
            assert html.request.var(varname)
