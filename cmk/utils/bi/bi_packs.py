#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import marshmallow  # type: ignore[import]
from marshmallow.fields import String, Nested  # type: ignore[import]
from marshmallow import Schema  # type: ignore[import]

from pathlib import Path
from cmk.utils.i18n import _
import cmk.utils.store as store
import cmk.utils.paths

from typing import (
    List,
    Dict,
    Set,
    Tuple,
    Type,
    Optional,
    Any,
    NamedTuple,
)

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.bi.bi_lib import (
    ReqList,
    ReqString,
    ReqNested,
    ReqBoolean,
)

from cmk.utils.bi.bi_rule import BIRule, BIRuleSchema
from cmk.utils.bi.bi_rule_interface import bi_rule_id_registry
from cmk.utils.bi.bi_legacy_config_converter import BILegacyConfigConverter
from cmk.utils.bi.bi_sample_configs import bi_sample_config
from cmk.utils.bi.bi_aggregation import BIAggregation, BIAggregationSchema
from cmk.utils.bi.bi_node_generator import BINodeGenerator
from cmk.utils.bi.bi_actions import (
    BICallARuleAction,
    BIStateOfHostAction,
    BIStateOfServiceAction,
    BIStateOfRemainingServicesAction,
)
from cmk.utils.bi.bi_search import (
    BIHostSearch,
    BIServiceSearch,
)

RuleReferencesResult = NamedTuple("RuleReferencesResult", [
    ("aggr_refs", int),
    ("rule_refs", int),
    ("level", int),
])
#   .--Packs---------------------------------------------------------------.
#   |                      ____            _                               |
#   |                     |  _ \ __ _  ___| | _____                        |
#   |                     | |_) / _` |/ __| |/ / __|                       |
#   |                     |  __/ (_| | (__|   <\__ \                       |
#   |                     |_|   \__,_|\___|_|\_\___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class BIAggregationPack:
    def __init__(self, pack_config: Dict[str, Any]):
        super().__init__()
        self.id = pack_config["id"]
        self.title = pack_config["title"]
        self.contact_groups = pack_config["contact_groups"]
        self.public = pack_config["public"]

        self.rules = {x["id"]: BIRule(x, self.id) for x in pack_config["rules"]}
        self.aggregations = {
            x["id"]: BIAggregation(x, self.id) for x in pack_config["aggregations"]
        }

    @classmethod
    def schema(cls) -> Type["BIAggregationPackSchema"]:
        return BIAggregationPackSchema

    def num_aggregations(self) -> int:
        return len(self.aggregations)

    def num_rules(self) -> int:
        return len(self.rules)

    def get_rules(self) -> Dict[str, BIRule]:
        return self.rules

    def get_aggregations(self) -> Dict[str, BIAggregation]:
        return self.aggregations

    def add_rule(self, bi_rule: BIRule) -> None:
        self.rules[bi_rule.id] = bi_rule

    def delete_rule(self, rule_id: str) -> None:
        del self.rules[rule_id]

    def get_rule(self, rule_id: str) -> Optional[BIRule]:
        return self.rules.get(rule_id)

    def get_rule_mandatory(self, rule_id: str) -> BIRule:
        return self.rules[rule_id]

    def add_aggregation(self, bi_aggregation: BIAggregation) -> None:
        self.aggregations[bi_aggregation.id] = bi_aggregation

    def delete_aggregation(self, aggregation_id: str) -> None:
        del self.aggregations[aggregation_id]

    def get_aggregation(self, aggregation_id: str) -> Optional[BIAggregation]:
        return self.aggregations.get(aggregation_id)

    def get_aggregation_mandatory(self, aggregation_id: str) -> BIAggregation:
        return self.aggregations[aggregation_id]


class BIAggregationPacks:
    def __init__(self, packs_config: Dict[str, Any]):
        super().__init__()
        self.packs: Dict[str, BIAggregationPack] = {}
        self._instantiate_packs(packs_config.get("packs", []))

    def _instantiate_packs(self, packs_data: List[Dict[str, Any]]):
        self.packs = {x["id"]: BIAggregationPack(x) for x in packs_data}

    @classmethod
    def schema(cls) -> Type["BIAggregationPacksSchema"]:
        return BIAggregationPacksSchema

    def cleanup(self) -> None:
        self.packs.clear()
        bi_rule_id_registry.clear()

    def pack_exists(self, pack_id: str) -> bool:
        return pack_id in self.packs

    def get_packs(self) -> Dict[str, BIAggregationPack]:
        return self.packs

    def add_pack(self, pack: BIAggregationPack):
        self.packs[pack.id] = pack

    def get_pack(self, pack_id: str) -> Optional[BIAggregationPack]:
        return self.packs.get(pack_id)

    def get_pack_mandatory(self, pack_id: str) -> BIAggregationPack:
        return self.packs[pack_id]

    def delete_pack(self, pack_id: str) -> None:
        del self.packs[pack_id]

    def get_rule(self, rule_id: str) -> Optional[BIRule]:
        for bi_pack in self.packs.values():
            bi_rule = bi_pack.get_rule(rule_id)
            if bi_rule:
                return bi_rule
        return None

    def get_rule_mandatory(self, rule_id: str) -> BIRule:
        bi_rule = self.get_rule(rule_id)
        if bi_rule:
            return bi_rule
        assert False

    def get_all_rules(self) -> List[BIRule]:
        return [
            bi_rule for bi_pack in self.packs.values() for bi_rule in bi_pack.get_rules().values()
        ]

    def get_aggregation_group_trees(self) -> List[str]:
        all_groups: Set[str] = set()
        for aggregation in self.get_all_aggregations():
            if aggregation.computation_options.disabled:
                continue
            all_groups.update(["/".join(x) for x in aggregation.groups.paths])
        return sorted(all_groups)

    def get_aggregation_group_choices(self) -> List[Tuple[str, str]]:
        """ Return a list of all available group names and fully combined group paths"""
        all_groups: Set[str] = set()
        for aggregation in self.get_all_aggregations():
            if aggregation.computation_options.disabled:
                continue
            all_groups.update(map(str, aggregation.groups.names))
            all_groups.update(["/".join(x) for x in aggregation.groups.paths])
        return [(gn, gn) for gn in sorted(all_groups, key=lambda x: x.lower())]

    def get_aggregation(self, aggregation_id: str) -> Optional[BIAggregation]:
        for bi_pack in self.packs.values():
            bi_aggregation = bi_pack.get_aggregation(aggregation_id)
            if bi_aggregation:
                return bi_aggregation
        return None

    def get_aggregation_mandatory(self, aggregation_id: str) -> BIAggregation:
        bi_aggregation = self.get_aggregation(aggregation_id)
        if bi_aggregation:
            return bi_aggregation
        assert False

    def get_all_aggregations(self) -> List[BIAggregation]:
        aggregations: List[BIAggregation] = []
        for bi_pack in self.packs.values():
            aggregations.extend(bi_pack.get_aggregations().values())
        return aggregations

    def get_pack_of_rule(self, rule_id: str) -> Optional[BIAggregationPack]:
        for bi_pack in self.packs.values():
            if bi_pack.get_rule(rule_id) is not None:
                return bi_pack
        return None

    def get_pack_of_aggregation(self, aggr_id: str) -> Optional[BIAggregationPack]:
        for bi_pack in self.packs.values():
            if bi_pack.get_aggregation(aggr_id) is not None:
                return bi_pack
        return None

    def get_rule_ids_of_aggregation(self, aggr_id: str) -> Set[str]:
        bi_aggregation = self.get_aggregation_mandatory(aggr_id)
        if isinstance(bi_aggregation.node.action, BICallARuleAction):
            return self._get_rule_ids_of_rule(bi_aggregation.node.action.rule_id)
        return set()

    def _get_rule_ids_of_rule(self, rule_id: str) -> Set[str]:
        rule_ids = [rule_id] + [
            bi_node.action.rule_id
            for bi_node in self.get_rule_mandatory(rule_id).get_nodes()
            if isinstance(bi_node.action, BICallARuleAction)
        ]
        return set(rule_ids)

    def rename_rule_id(self, old_id: str, new_id: str) -> None:
        # Rename the rule itself and all call_a_rule references in rules and aggregations
        for bi_pack in self.packs.values():
            for bi_rule in list(bi_pack.get_rules().values()):
                if bi_rule.id == old_id:
                    bi_pack.delete_rule(old_id)
                    bi_rule.id = new_id
                    bi_pack.add_rule(bi_rule)

                for bi_node in bi_rule.get_nodes():
                    if isinstance(bi_node.action,
                                  BICallARuleAction) and bi_node.action.rule_id == old_id:
                        bi_node.action.rule_id = new_id

            for bi_aggregation in bi_pack.get_aggregations().values():
                if isinstance(bi_aggregation.node.action,
                              BICallARuleAction) and bi_aggregation.node.action.rule_id == old_id:
                    bi_aggregation.node.action.rule_id = new_id

    def load_config(self) -> None:
        self.cleanup()
        if not Path(self.bi_configuration_file).exists():
            legacy_filename = self.bi_config_dir / "bi.mk"
            if legacy_filename.exists():
                packs_data = BILegacyConfigConverter().get_schema_for_packs()
                self._instantiate_packs(packs_data)
                self.save_config()
            else:
                self.load_config_from_schema(bi_sample_config)
                return

        self.load_config_from_schema(store.load_object_from_file(self.bi_configuration_file))

    def load_config_from_schema(self, config_packs_schema: Dict) -> None:
        data = BIAggregationPacksSchema().load(config_packs_schema)
        self._instantiate_packs(data.data["packs"])

    def save_config(self) -> None:
        store.save_file(self.bi_configuration_file, repr(self.generate_config()))

    def generate_config(self) -> Dict[str, Any]:
        self._check_rule_cycles()
        return BIAggregationPacksSchema().dump(self).data

    def _check_rule_cycles(self) -> None:
        toplevel_rules = {
            bi_aggregation.node.action.rule_id
            for bi_aggregation in self.get_all_aggregations()
            if isinstance(bi_aggregation.node.action, BICallARuleAction)
        }

        for toplevel_rule in toplevel_rules:
            self._traverse_rule(self.get_rule_mandatory(toplevel_rule))

    def _traverse_rule(self, bi_rule: BIRule, parents=None) -> None:
        if not parents:
            parents = []

        if bi_rule.id in parents:
            parents.append(bi_rule.id)
            raise MKGeneralException(
                _("There is a cycle in your rules. This rule calls itself - "
                  "either directly or indirectly: %s") % "->".join(parents))

        parents.append(bi_rule.id)
        for node in bi_rule.nodes:
            if isinstance(node.action, BICallARuleAction):
                self._traverse_rule(self.get_rule_mandatory(node.action.rule_id), list(parents))

    def count_rule_references(self, check_rule_id: str) -> RuleReferencesResult:
        aggr_refs = 0
        for bi_aggregation in self.get_all_aggregations():
            if isinstance(bi_aggregation.node.action, BICallARuleAction):
                if bi_aggregation.node.action.rule_id == check_rule_id:
                    aggr_refs += 1

        level = 0
        rule_refs = 0
        for bi_rule in self.get_all_rules():
            lv = self._rule_uses_rule(bi_rule, check_rule_id)
            level = max(lv, level)
            if lv == 1:
                rule_refs += 1

        return RuleReferencesResult(aggr_refs, rule_refs, level)

    def _rule_uses_rule(self, bi_rule: BIRule, check_rule_id: str, level: int = 0) -> int:
        for bi_node in bi_rule.get_nodes():
            if isinstance(bi_node.action, BICallARuleAction):
                node_rule_id = bi_node.action.rule_id
                if node_rule_id == check_rule_id:  # Rule is directly being used
                    return level + 1
                # Check if lower rules use it
                bi_subrule = bi_packs.get_rule_mandatory(node_rule_id)
                lv = self._rule_uses_rule(bi_subrule, check_rule_id, level + 1)
                if lv != -1:
                    return lv
        return -1

    @property
    def bi_configuration_file(self) -> str:
        return str(self.bi_config_dir / "bi_config.mk")

    @property
    def bi_config_dir(self) -> Path:
        return Path(cmk.utils.paths.default_config_dir, "multisite.d", "wato")


class BIAggregationPackSchema(Schema):
    id = ReqString(default="", example="bi_pack1")
    title = ReqString(default="", example="BI Title")
    contact_groups = ReqList(String(), default=[], example=["contactgroup_a", "contactgroup_b"])
    public = ReqBoolean(default=False)
    rules = ReqList(Nested(BIRuleSchema()), default=[])
    aggregations = ReqList(Nested(BIAggregationSchema()), default=[])

    @marshmallow.pre_dump
    def pre_dump(self, obj: BIAggregationPack) -> Dict:
        # Convert aggregations and rules to list
        return {
            "id": obj.id,
            "title": obj.title,
            "contact_groups": obj.contact_groups,
            "public": obj.public,
            "rules": obj.get_rules().values(),
            "aggregations": obj.get_aggregations().values(),
        }


class BIAggregationPacksSchema(Schema):
    packs = ReqList(ReqNested(BIAggregationPackSchema))

    @marshmallow.pre_dump
    def pre_dump(self, obj: BIAggregationPacks) -> Dict:
        # Convert packs to list
        return {"packs": obj.packs.values()}


bi_packs = BIAggregationPacks({})

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


class BIHostRenamer:
    def rename_host(self, oldname: str, newname: str) -> List:
        bi_packs.load_config()
        renamed = 0

        for bi_pack in bi_packs.get_packs().values():
            for bi_rule in bi_pack.get_rules().values():
                renamed += sum([self.rename_node(x, oldname, newname) for x in bi_rule.nodes])

            for bi_aggregation in bi_pack.get_aggregations().values():
                renamed += self.rename_node(bi_aggregation.node, oldname, newname)

        if renamed:
            bi_packs.save_config()
            return ["bi"] * renamed
        return []

    def rename_node(self, bi_node: BINodeGenerator, oldname: str, newname: str) -> int:
        renamed = 0
        renamed += self.rename_node_action(bi_node, oldname, newname)
        renamed += self.rename_node_search(bi_node, oldname, newname)
        return renamed

    def rename_node_action(self, bi_node: BINodeGenerator, oldname: str, newname: str) -> int:
        # TODO: renaming can be moved into the action class itself. allows easier plugins
        if isinstance(
                bi_node.action,
            (BIStateOfHostAction, BIStateOfServiceAction, BIStateOfRemainingServicesAction)):
            if bi_node.action.host_regex == oldname:
                bi_node.action.host_regex = newname
                return 1

        elif isinstance(bi_node.action, BICallARuleAction):
            arguments = bi_node.action.params.arguments
            if oldname in arguments:
                new_arguments = [newname if x == oldname else x for x in arguments]
                bi_node.action.params.arguments = new_arguments
                return 1

        return 0

    def rename_node_search(self, bi_node: BINodeGenerator, oldname: str, newname: str) -> int:
        # TODO: renaming can be moved into the search class itself. allows easier plugins
        if isinstance(bi_node.search, (BIHostSearch, BIServiceSearch)):
            if bi_node.search.conditions["host_choice"][
                    "type"] == "host_name_regex" and bi_node.search.conditions["host_choice"][
                        "pattern"] == oldname:
                bi_node.search.conditions["host_choice"]["pattern"] = newname
                return 1

        return 0
