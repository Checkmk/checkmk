#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#   .--Converter-----------------------------------------------------------.
#   |              ____                          _                         |
#   |             / ___|___  _ ____   _____ _ __| |_ ___ _ __              |
#   |            | |   / _ \| '_ \ \ / / _ \ '__| __/ _ \ '__|             |
#   |            | |__| (_) | | | \ V /  __/ |  | ||  __/ |                |
#   |             \____\___/|_| |_|\_/ \___|_|   \__\___|_|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Welcome to the old world. Avoid adding any new features here.
# This code will be abandoned with the version following 2.0

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.rulesets.ruleset_matcher import get_tag_to_group_map, RulesetToDictTransformer

from cmk.gui.config import active_config  # pylint: disable=cmk-module-layer-violation
from cmk.gui.watolib.utils import multisite_dir  # pylint: disable=cmk-module-layer-violation

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=cmk-module-layer-violation,no-name-in-module

from cmk.utils.bi.bi_packs import BIAggregationPacks
from cmk.utils.exceptions import MKGeneralException

BIAggrOptions = Dict[str, Any]
BIAggrGroups = List[str]
BIAggrNode = Tuple


class ErrorCounter:
    def __init__(self) -> None:
        self._count = 0

    def increase_error_count(self):
        self._count += 1

    def check(self):
        if self._count > 0:
            raise MKGeneralException(f"Detected {self._count} errors in BI rules")


class BIRuleSchemaConverter:
    def __init__(self, logger: logging.Logger, error_counter: ErrorCounter):
        self._logger = logger
        self._error_counter = error_counter

    def old_to_new_schema(self, pack_id, old_schema):
        ID = old_schema["id"]
        new_schema = {}
        new_schema["id"] = ID
        new_schema["params"] = {"arguments": old_schema.get("params", [])}
        new_schema["computation_options"] = {"disabled": old_schema.get("disabled", False)}
        new_schema["properties"] = {
            "state_messages": old_schema.get("state_messages", {}),
            "title": old_schema["title"],
            "comment": old_schema.get("comment", ""),
            "docu_url": old_schema.get("docu_url", ""),
            "icon": old_schema.get("icon", ""),
        }
        if new_schema["properties"]["state_messages"] is None:
            new_schema["properties"]["state_messages"] = {}
        if new_schema["properties"]["icon"] is None:
            new_schema["properties"]["icon"] = ""
        new_schema["node_visualization"] = self.convert_node_visualization_old_to_new(
            old_schema.get("layout_style")
        )
        new_schema["aggregation_function"] = self.convert_aggr_func_old_to_new(
            old_schema["aggregation"]
        )
        new_schema["nodes"] = [
            self.convert_node_old_to_new(pack_id, ID, nr, node)
            for nr, node in enumerate(old_schema["nodes"], 1)
        ]
        return new_schema

    def convert_node_visualization_old_to_new(self, node_vis_old):
        if node_vis_old is None:
            return {"type": "none", "style_config": {}}

        return {
            "type": node_vis_old["style_type"],
            "style_config": node_vis_old.get("style_config", {}),
        }

    def convert_aggr_func_old_to_new(self, aggr_func_old):
        aggr_func_new = {"type": aggr_func_old[0]}

        # Add missing default values
        if len(aggr_func_old[1]) == 0:
            default_values = None
            if aggr_func_new["type"] in ["worst", "best"]:
                default_values = (1, 2)
            elif aggr_func_new["type"] in ["count_ok"]:
                default_values = (2, 1)
            assert default_values is not None
            aggr_func_old = tuple([aggr_func_old[0], default_values])

        if aggr_func_new["type"] in ["worst", "best"]:
            aggr_func_new["count"] = aggr_func_old[1][0]
            aggr_func_new["restrict_state"] = int(aggr_func_old[1][1])
        elif aggr_func_new["type"] == "count_ok":
            aggr_func_new["levels_ok"] = {
                "type": "percentage" if str(aggr_func_old[1][0]).endswith("%") else "count",
                "value": int(str(aggr_func_old[1][0]).rstrip("%")),
            }
            aggr_func_new["levels_warn"] = {
                "type": "percentage" if str(aggr_func_old[1][1]).endswith("%") else "count",
                "value": int(str(aggr_func_old[1][1]).rstrip("%")),
            }
        return aggr_func_new

    def _validate_regex(self, regex, diagnostic_msg):
        try:
            re.compile(regex)
        except re.error as e:
            self._error_counter.increase_error_count()
            self._logger.error(
                f"ERROR: Invalid regular expression in BI rule detected: {diagnostic_msg}, regex:{regex}, Exception: {e}"
            )

    def convert_node_old_to_new(self, pack_id: str, ID: str, nr: int, node):
        if node[0] == "call":
            return {
                "search": {"type": "empty"},
                "action": {
                    "type": "call_a_rule",
                    "rule_id": node[1][0],
                    "params": {
                        "arguments": node[1][1],
                    },
                },
            }
        if node[0] == "service":
            host_regex = node[1][0]
            self._validate_regex(host_regex, f"pack: {pack_id}, id: {ID}, child node nr:{nr}")
            service_regex = node[1][1]
            self._validate_regex(service_regex, f"pack: {pack_id}, id: {ID}, child node nr:{nr}")
            return {
                "search": {"type": "empty"},
                "action": {
                    "type": "state_of_service",
                    "host_regex": host_regex,
                    "service_regex": service_regex,
                },
            }

        if node[0] == "host":
            host_regex = node[1][0]
            self._validate_regex(host_regex, f"pack: {pack_id}, id: {ID}, child node nr:{nr}")
            return {
                "search": {"type": "empty"},
                "action": {
                    "type": "state_of_host",
                    "host_regex": host_regex,
                },
            }

        if node[0] == "remaining":
            host_regex = node[1][0]
            self._validate_regex(host_regex, f"pack: {pack_id}, id: {ID}, child node nr:{nr}")
            return {
                "search": {"type": "empty"},
                "action": {
                    "type": "state_of_remaining_services",
                    "host_regex": host_regex,
                },
            }

        if node[0] == "foreach_host":
            node_config = node[1]
            conditions = {
                "host_tags": node_config[1],
                "host_folder": "",
                "host_labels": {},
            }
            if node_config[2] is None:
                conditions["host_choice"] = {"type": "all_hosts"}
            elif isinstance(node_config[2], str):
                conditions["host_choice"] = {"type": "host_name_regex", "pattern": node_config[2]}
            else:
                conditions["host_choice"] = {
                    "type": "host_alias_regex",
                    "pattern": node_config[2][1],
                }

            return {
                "search": {
                    "type": "host_search",
                    "refer_to": node_config[0],
                    "conditions": conditions,
                },
                "action": self.convert_node_old_to_new(pack_id, ID + ".action", nr, node_config[3])[
                    "action"
                ],
            }

        if node[0] == "foreach_service":
            node_config = node[1]
            conditions = {
                "host_tags": node_config[0],
                "host_folder": "",
                "host_labels": {},
            }
            if node_config[1] is None:
                conditions["host_choice"] = {"type": "all_hosts"}
            elif isinstance(node_config[1], str):
                conditions["host_choice"] = {"type": "host_name_regex", "pattern": node_config[1]}
            else:
                conditions["host_choice"] = {
                    "type": "host_alias_regex",
                    "pattern": node_config[1][1],
                }
            service_regex = node_config[2]
            self._validate_regex(service_regex, f"pack: {pack_id}, id: {ID}, child node nr:{nr}")
            conditions["service_regex"] = service_regex
            conditions["service_labels"] = {}

            return {
                "search": {"type": "service_search", "conditions": conditions},
                "action": self.convert_node_old_to_new(pack_id, ID + ".action", nr, node_config[3])[
                    "action"
                ],
            }
        return None


class BIAggregationSchemaConverter:
    def __init__(self, logger: logging.Logger, error_counter: ErrorCounter):
        self._logger = logger
        self._error_counter = error_counter

    def old_to_new_schema(self, pack_id: str, old_schema):
        new_schema = {}
        ID = old_schema["ID"]
        new_schema["id"] = ID
        new_schema["computation_options"] = {
            "disabled": old_schema.get("disabled", False),
            "escalate_downtimes_as_warn": old_schema.get("downtime_aggr_warn", False),
            "use_hard_states": old_schema.get("hard_states", False),
        }
        node_vis = old_schema.get("node_visualization")
        if node_vis is None or node_vis == {}:
            node_vis = self.default_node_visualiziation
        new_schema["aggregation_visualization"] = node_vis
        if "customer" in old_schema:
            new_schema["customer"] = old_schema["customer"]
        rule_converter = BIRuleSchemaConverter(self._logger, self._error_counter)
        new_schema["node"] = rule_converter.convert_node_old_to_new(
            pack_id, ID, 1, old_schema["node"]
        )
        new_schema["groups"] = self.convert_old_groups(old_schema["groups"])

        return new_schema

    @property
    def default_node_visualiziation(self):
        return {"ignore_rule_styles": False, "layout_id": "builtin_default", "line_style": "round"}

    def convert_old_groups(self, old_groups):
        new_groups: Dict[str, List] = {"names": [], "paths": []}
        for group in old_groups:
            if "/" in group:
                new_groups["paths"].append(group.split("/"))
            else:
                new_groups["names"].append(group)
        return new_groups


class BIPackSchemaConverter:
    def __init__(self, logger: logging.Logger, error_counter: ErrorCounter):
        self._logger = logger
        self._error_counter = error_counter

    def old_to_new_schema(self, old_schema):
        new_schema = {}
        pack_id = old_schema["id"]
        new_schema["id"] = pack_id
        new_schema["title"] = old_schema["title"]
        new_schema["public"] = old_schema["public"]
        new_schema["contact_groups"] = old_schema["contact_groups"]

        rule_converter = BIRuleSchemaConverter(self._logger, self._error_counter)
        new_schema["rules"] = [
            rule_converter.old_to_new_schema(pack_id, x) for x in old_schema["rules"].values()
        ]

        aggr_converter = BIAggregationSchemaConverter(self._logger, self._error_counter)
        new_schema["aggregations"] = [
            aggr_converter.old_to_new_schema(pack_id, x) for x in old_schema["aggregations"]
        ]
        return new_schema


class BIManagement:
    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._load_config()

    # .--------------------------------------------------------------------.
    # | Loading and saving                                                 |
    # '--------------------------------------------------------------------'

    def _get_config_string(self):
        filename = Path(cmk.utils.paths.default_config_dir, "multisite.d", "wato", "bi.mk")
        with filename.open("rb") as f:
            return f.read()

    def _load_config(self):
        self._bi_constants = {
            "ALL_HOSTS": "ALL_HOSTS-f41e728b-0bce-40dc-82ea-51091d034fc3",
            "HOST_STATE": "HOST_STATE-f41e728b-0bce-40dc-82ea-51091d034fc3",
            "HIDDEN": "HIDDEN-f41e728b-0bce-40dc-82ea-51091d034fc3",
            "FOREACH_HOST": "FOREACH_HOST-f41e728b-0bce-40dc-82ea-51091d034fc3",
            "FOREACH_CHILD": "FOREACH_CHILD-f41e728b-0bce-40dc-82ea-51091d034fc3",
            "FOREACH_CHILD_WITH": "FOREACH_CHILD_WITH-f41e728b-0bce-40dc-82ea-51091d034fc3",
            "FOREACH_PARENT": "FOREACH_PARENT-f41e728b-0bce-40dc-82ea-51091d034fc3",
            "FOREACH_SERVICE": "FOREACH_SERVICE-f41e728b-0bce-40dc-82ea-51091d034fc3",
            "REMAINING": "REMAINING-f41e728b-0bce-40dc-82ea-51091d034fc3",
            "DISABLED": "DISABLED-f41e728b-0bce-40dc-82ea-51091d034fc3",
            "HARD_STATES": "HARD_STATES-f41e728b-0bce-40dc-82ea-51091d034fc3",
            "DT_AGGR_WARN": "DT_AGGR_WARN-f41e728b-0bce-40dc-82ea-51091d034fc3",
        }
        self._hosttags_transformer = RulesetToDictTransformer(
            tag_to_group_map=get_tag_to_group_map(active_config.tags)
        )

        try:
            vars_: Dict[str, Any] = {
                "aggregation_rules": {},
                "aggregations": [],
                "host_aggregations": [],
                "bi_packs": {},
            }
            vars_.update(self._bi_constants)

            exec(self._get_config_string(), vars_, vars_)

            # put legacy non-pack stuff into packs
            if (
                vars_["aggregation_rules"] or vars_["aggregations"] or vars_["host_aggregations"]
            ) and "default" not in vars_["bi_packs"]:
                vars_["bi_packs"]["default"] = {
                    "title": "Default Pack",
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
                        self._convert_aggregation_from_bi(aggregation, single_host=False)
                    )
                for aggregation in pack["host_aggregations"]:
                    aggregations.append(
                        self._convert_aggregation_from_bi(aggregation, single_host=True)
                    )

                self._packs[pack_id] = {
                    "id": pack_id,
                    "title": pack["title"],
                    "rules": aggregation_rules,
                    "aggregations": aggregations,
                    "public": pack["public"],
                    "contact_groups": pack["contact_groups"],
                }

                self._add_missing_aggr_ids()
        except Exception as e:
            self._logger.error("Unable to load legacy bi.mk configuration %s", str(e))
            raise

    def _add_missing_aggr_ids(self):
        # Determine existing IDs
        used_aggr_ids = set()
        for pack_id, pack in self._packs.items():
            used_aggr_ids.update({x["ID"] for x in pack["aggregations"] if "ID" in x})

        # Compute missing IDs
        new_id = ""
        for pack_id, pack in self._packs.items():
            aggr_id_counter = 0
            for aggregation in pack["aggregations"]:
                if "ID" not in aggregation:
                    while True:
                        aggr_id_counter += 1
                        new_id = "%s_aggr_%d" % (pack_id, aggr_id_counter)
                        if new_id in used_aggr_ids:
                            continue
                        break
                    used_aggr_ids.add(new_id)
                    aggregation["ID"] = new_id

    def _convert_pack_to_bi(self, pack):
        converted_rules = {
            rule_id: self._convert_rule_to_bi(rule) for rule_id, rule in pack["rules"].items()
        }
        converted_aggregations: List[Tuple[BIAggrOptions, BIAggrGroups, BIAggrNode]] = []
        converted_host_aggregations: List[Tuple[BIAggrOptions, BIAggrGroups, BIAggrNode]] = []
        for aggregation in pack["aggregations"]:
            converted_aggregation = self._convert_aggregation_to_bi(aggregation)
            if aggregation["single_host"]:
                converted_host_aggregations.append(converted_aggregation)
            else:
                converted_aggregations.append(converted_aggregation)

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
        return s[0] + "\n " + s[1:-1] + "\n" + s[-1]

    def _convert_aggregation_to_bi(self, aggr):
        node = self._convert_node_to_bi(aggr["node"])
        option_keys: List[Tuple[str, Any]] = [
            ("ID", None),
            ("node_visualization", {}),
            ("hard_states", False),
            ("downtime_aggr_warn", False),
            ("disabled", False),
        ]

        if cmk_version.is_managed_edition():
            option_keys.append(("customer", managed.default_customer_id()))

        # Create dict with all aggregation options
        options = {}
        for option, default_value in option_keys:
            options[option] = aggr.get(option, default_value)

        return (options, self._convert_aggregation_groups(aggr["groups"])) + node

    def _convert_node_to_bi(self, node):
        if node[0] == "call":
            return node[1]
        if node[0] == "host":
            return (node[1][0], self._bi_constants["HOST_STATE"])
        if node[0] == "remaining":
            return (node[1][0], self._bi_constants["REMAINING"])
        if node[0] == "service":
            return node[1]
        if node[0] == "foreach_host":
            what = node[1][0]

            tags = node[1][1]
            if node[1][2]:
                hostspec = node[1][2]
            else:
                hostspec = self._bi_constants["ALL_HOSTS"]

            if isinstance(what, tuple) and what[0] == "child_with":
                child_conditions = what[1]
                what = what[0]
                child_tags = child_conditions[0]
                child_hostspec = (
                    child_conditions[1] if child_conditions[1] else self._bi_constants["ALL_HOSTS"]
                )
                return (
                    self._bi_constants["FOREACH_" + what.upper()],
                    child_tags,
                    child_hostspec,
                    tags,
                    hostspec,
                ) + self._convert_node_to_bi(node[1][3])
            return (
                self._bi_constants["FOREACH_" + what.upper()],
                tags,
                hostspec,
            ) + self._convert_node_to_bi(node[1][3])
        if node[0] == "foreach_service":
            tags = node[1][0]
            if node[1][1]:
                spec = node[1][1]
            else:
                spec = self._bi_constants["ALL_HOSTS"]
            service = node[1][2]
            return (
                self._bi_constants["FOREACH_SERVICE"],
                tags,
                spec,
                service,
            ) + self._convert_node_to_bi(node[1][3])
        return None

    def _convert_aggregation_from_bi(self, aggr, single_host):
        if isinstance(aggr[0], dict):
            options = aggr[0]
            aggr = aggr[1:]
        else:
            # Legacy configuration
            options = {}
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
            except ValueError:
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
        crule["nodes"] = list(map(self._convert_node_from_bi, rule["nodes"]))
        parts = rule["aggregation"].split("!")
        crule["aggregation"] = (parts[0], tuple(map(tryint, parts[1:])))
        crule["id"] = ruleid
        return crule

    def _convert_rule_to_bi(self, rule):
        brule = {}
        brule.update(rule)
        if "id" in brule:
            del brule["id"]
        brule["nodes"] = list(map(self._convert_node_to_bi, rule["nodes"]))
        brule["aggregation"] = "!".join(
            [rule["aggregation"][0]] + list(map(str, rule["aggregation"][1]))
        )
        return brule

    # Convert node-Tuple into format used by CascadingDropdown
    def _convert_node_from_bi(self, node):
        if len(node) == 2:
            if isinstance(node[1], list):
                return ("call", node)
            if node[1] == self._bi_constants["HOST_STATE"]:
                return ("host", (node[0],))
            if node[1] == self._bi_constants["REMAINING"]:
                return ("remaining", (node[0],))
            return ("service", node)

        foreach_spec = node[0]
        if foreach_spec == self._bi_constants["FOREACH_CHILD_WITH"]:
            # extract the conditions meant for matching the childs
            child_conditions = list(node[1:3])
            if child_conditions[1] == self._bi_constants["ALL_HOSTS"]:
                child_conditions[1] = None
            node = node[0:1] + node[3:]

            if not isinstance(child_conditions[0], dict):
                new_tags = self._hosttags_transformer.transform_host_tags(child_conditions[0])
                child_conditions[0] = new_tags.get("host_tags", {})

        # Extract the list of tags
        if isinstance(node[1], (list, dict)):
            tags = node[1]
            node = node[0:1] + node[2:]
            if not isinstance(tags, dict):
                new_tags = self._hosttags_transformer.transform_host_tags(tags)
                tags = new_tags.get("host_tags", {})
        else:
            tags = {}

        hostspec = node[1]
        if hostspec == self._bi_constants["ALL_HOSTS"]:
            hostspec = None

        if foreach_spec == self._bi_constants["FOREACH_SERVICE"]:
            service = node[2]
            subnode = self._convert_node_from_bi(node[3:])
            return ("foreach_service", (tags, hostspec, service, subnode))

        subnode = self._convert_node_from_bi(node[2:])
        if foreach_spec == self._bi_constants["FOREACH_HOST"]:
            what: Union[str, Tuple] = "host"
        elif foreach_spec == self._bi_constants["FOREACH_CHILD"]:
            what = "child"
        elif foreach_spec == self._bi_constants["FOREACH_CHILD_WITH"]:
            what = ("child_with", child_conditions)
        elif foreach_spec == self._bi_constants["FOREACH_PARENT"]:
            what = "parent"
        return ("foreach_host", (what, tags, hostspec, subnode))


class BILegacyConfigConverter(BIManagement):
    def __init__(self, logger: logging.Logger):
        super().__init__(logger)
        self._logger = logger
        self._error_counter = ErrorCounter()

    def get_schema_for_packs(self):
        pack_converter = BIPackSchemaConverter(self._logger, self._error_counter)
        packs = []
        for x in self._packs.values():
            packs.append(pack_converter.old_to_new_schema(x))
        self._error_counter.check()
        return packs


class BILegacyPacksConverter(BIAggregationPacks):
    def __init__(self, logger: logging.Logger, bi_configuration_file: str):
        super().__init__(bi_configuration_file)
        self._logger = logger

    def convert_config(self):
        old_bi_config = Path(multisite_dir(), "bi.mk")
        if not old_bi_config.exists():
            self._logger.info("Skipping conversion of bi.mk (already done)")
            return

        try:
            if Path(self._bi_configuration_file).exists():
                # Already converted bi.mk -> bi_config.bi
                return
            packs_data = BILegacyConfigConverter(self._logger).get_schema_for_packs()
            self._instantiate_packs(packs_data)
            self.save_config()
        finally:
            # Delete superfluous bi.mk, otherwise it would be read on every web request
            old_bi_config.unlink(missing_ok=True)
