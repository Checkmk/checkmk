#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Annotated, Literal

from pydantic import Discriminator, StringConstraints

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)
from cmk.gui.openapi.framework.model.common_fields import AnnotatedFolder

RULESET_NAME_DESCRIPTION = (
    "The name of the ruleset. Note: Since Checkmk 3.0 discovery rulesets are referred to by"
    " `discovery_parameters:<OLD NAME>`. Using `<OLD NAME>` on its own will stop working in"
    " Checkmk 3.1."
)

_HOST_NAME_CONDITION_DESCRIPTION = (
    "Here you can enter a list of explicit host names that the rule should or should not apply "
    "to. Leave this option disabled if you want the rule to apply for all hosts specified by the "
    "given tags. The names that you enter here are compared with case sensitive exact matching. "
    "Alternatively you can use regular expressions if you enter a tilde `~` as the first "
    "character. That regular expression must match the beginning of the host names in question."
)

_SERVICE_DESCRIPTION_CONDITION_DESCRIPTION = (
    "Specify a list of service patterns this rule shall apply to.\n"
    " * The patterns must match the beginning of the service in question.\n"
    " * Adding a `$` to the end forces an exact match.\n"
    " * Pattern use regular expressions. e.g. a `.*` will match an arbitrary text.\n"
    " * The text entered here is handled as a regular expression pattern.\n"
    " * The pattern is matched from the beginning.\n"
    " * The match is performed case sensitive.\n"
    "BE AWARE: Depending on the service ruleset the service_description of the rules is only a "
    "check item or a full service name. For example the check parameters rulesets only use the "
    "item, and other service rulesets like disabled services ruleset use full servicedescriptions."
)

_HOST_LABEL_GROUPS_DESCRIPTION = (
    "Further restrict this rule by applying host label conditions. Although all items in this "
    "list have a default operator value, the operator value for the the first item in the list "
    "does not have any effect."
)

_SERVICE_LABEL_GROUPS_DESCRIPTION = (
    "Restrict the application of the rule, by checking against service label conditions. Although "
    "all items in this list have a default operator value, the operator value for the the first "
    "item in the list does not have any effect."
)


@api_model
class MatchExpressionModel:
    match_on: list[Annotated[str, StringConstraints(min_length=1)]] = api_field(
        description="A list of string matching regular expressions.",
    )
    operator: Literal["none_of", "one_of"] = api_field(
        description=(
            "How the hosts or services should be matched.\n"
            " * one_of - will match if any of the hosts or services is matched\n"
            " * none_of - will match if none of the hosts are matched. In other words: will match"
            " all hosts or services which are not specified.\n"
        ),
    )


@api_model
class TagConditionScalarModel:
    key: str = api_field(description="The name of the tag.")
    operator: Literal["is", "is_not"] = api_field(
        description="If the tag's value should match what is given under the field `value`.",
    )
    # `None` is a valid tag value: the "(none)" tag choice of a tag group.
    value: str | None = api_field(description="The value of a tag.")


@api_model
class TagConditionCollectionModel:
    key: str = api_field(description="The name of the tag.")
    operator: Literal["none_of", "one_of"] = api_field(
        description="If the matched tag should be one of the given values, or not.",
    )
    value: list[str | None] = api_field(description="A list of values for the tag.")


type TagConditionModel = Annotated[
    TagConditionScalarModel | TagConditionCollectionModel, Discriminator("operator")
]


@api_model
class LabelConditionModel:
    operator: Literal["and", "not", "or"] = api_field(
        description=(
            "Boolean operator that connects the label to other labels within the same label group "
            "condition"
        ),
    )
    label: str = api_field(
        description='A label of format "{key}:{value}"',
        example="os:windows",
    )


@api_model
class LabelGroupConditionModel:
    operator: Literal["and", "not", "or"] = api_field(
        description="Boolean operator that connects the label group to other label groups",
    )
    label_group: list[LabelConditionModel] = api_field(
        description="A list of label conditions that form a label group",
        example=[{"operator": "and", "label": "os:linux"}],
    )


@api_model
class RuleConditionsModel:
    host_name: MatchExpressionModel | ApiOmitted = api_field(
        description=_HOST_NAME_CONDITION_DESCRIPTION,
        example={"match_on": ["host1", "host2"], "operator": "one_of"},
        default_factory=ApiOmitted,
    )
    host_tags: list[TagConditionModel] | ApiOmitted = api_field(
        description=(
            "The rule will only be applied to hosts fulfilling all the host tag conditions listed "
            "here, even if they appear in the list of explicit host names."
        ),
        example=[{"key": "criticality", "operator": "is", "value": "prod"}],
        default_factory=ApiOmitted,
    )
    host_label_groups: list[LabelGroupConditionModel] | ApiOmitted = api_field(
        description=_HOST_LABEL_GROUPS_DESCRIPTION,
        example=[
            {"label_group": [{"operator": "and", "label": "db:mssql"}]},
            {"operator": "and", "label_group": [{"operator": "and", "label": "os:windows"}]},
        ],
        default_factory=ApiOmitted,
    )
    service_label_groups: list[LabelGroupConditionModel] | ApiOmitted = api_field(
        description=_SERVICE_LABEL_GROUPS_DESCRIPTION,
        example=[
            {"label_group": [{"operator": "and", "label": "db:mssql"}]},
            {"operator": "and", "label_group": [{"operator": "and", "label": "os:windows"}]},
        ],
        default_factory=ApiOmitted,
    )
    service_description: MatchExpressionModel | ApiOmitted = api_field(
        description=_SERVICE_DESCRIPTION_CONDITION_DESCRIPTION,
        example={"match_on": ["foo1", "bar2"], "operator": "none_of"},
        default_factory=ApiOmitted,
    )


@api_model
class RulePropertiesResponseModel:
    description: str | ApiOmitted = api_field(
        description="A description for this rule to inform other users about its intent.",
        example="This rule is here to foo the bar hosts.",
        default_factory=ApiOmitted,
    )
    comment: str | ApiOmitted = api_field(
        description="Any comment string.",
        example="Created yesterday due to foo hosts behaving weird.",
        default_factory=ApiOmitted,
    )
    documentation_url: str | ApiOmitted = api_field(
        description="An URL (e.g. an internal Wiki entry) which explains this rule.",
        example="http://example.com/wiki/ConfiguringFooBarHosts",
        default_factory=ApiOmitted,
    )
    disabled: bool | ApiOmitted = api_field(
        description="When set to False, the rule will be evaluated. Default is False.",
        example=False,
        default_factory=ApiOmitted,
    )


@api_model
class RuleExtensionsModel:
    ruleset: str = api_field(description=RULESET_NAME_DESCRIPTION)
    folder: AnnotatedFolder = api_field(
        description="The path name of the folder.", example="~router"
    )
    folder_index: int = api_field(
        description="The position of this rule in the chain in this folder.",
    )
    properties: RulePropertiesResponseModel = api_field(description="Property values of this rule.")
    value_raw: str = api_field(
        description="The raw parameter value for this rule.",
        example='{"ignore_fs_types": ["tmpfs"]}',
    )
    conditions: RuleConditionsModel = api_field(description="Conditions.")


@api_model
class RuleObjectModel(DomainObjectModel):
    domainType: Literal["rule"] = api_field(description="Domain type of this object.")
    extensions: RuleExtensionsModel = api_field(description="Attributes specific to rule objects.")


@api_model
class RuleCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["rule"] = api_field(description="Domain type of this object.")
    value: list[RuleObjectModel] = api_field(
        description="The collection itself. Each entry in here is part of the collection.",
    )
