#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.endpoint_link import link_to_endpoint
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.watolib.rulesets import AllRulesets

from ._family import RULE_FAMILY
from ._utils import PERMISSIONS, retrieve_from_rulesets, RuleEntry, serialize_rule
from .models.response_models import RuleCollectionModel, RULESET_NAME_DESCRIPTION


def list_rules_v1(
    api_context: ApiContext,
    ruleset_name: Annotated[
        str,
        QueryParam(description=RULESET_NAME_DESCRIPTION, example="host_groups"),
    ],
) -> RuleCollectionModel:
    """List rules"""
    user.need_permission("wato.rulesets")
    all_rulesets = AllRulesets.load_all_rulesets()
    ruleset = retrieve_from_rulesets(all_rulesets, ruleset_name)

    rules = [
        serialize_rule(
            RuleEntry(
                rule=rule,
                ruleset=rule.ruleset,
                folder=folder,
                index_nr=index,
                all_rulesets=all_rulesets,
            ),
            api_context,
        )
        for folder, index, rule in ruleset.get_rules()
    ]

    return RuleCollectionModel(
        id="all",
        domainType="rule",
        value=rules,
        extensions={"found_rules": len(rules)},
        links=[
            link_to_endpoint(
                family=RULE_FAMILY.name,
                link_relation=".../collection",
                version=api_context.version,
                host_url=api_context.host_url,
                as_self=True,
            )
        ],
    )


ENDPOINT_LIST_RULES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("rule"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=RULE_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=list_rules_v1)},
)
