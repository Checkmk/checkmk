#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from typing import Annotated, Literal, Self

from pydantic import model_validator

from cmk.gui.openapi.api_endpoints.rule.models.response_models import (
    MatchExpressionModel,
    RULESET_NAME_DESCRIPTION,
    TagConditionModel,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import AnnotatedFolder
from cmk.gui.openapi.framework.model.converter import TypedPlainValidator

_VALUE_RAW_DESCRIPTION = (
    "The raw parameter value for this rule. To create the correct structure, for now use the "
    "'export for API' menu item in the Rule Editor of the GUI. The value is expected to be a "
    "valid Python type."
)

_CONDITIONS_EXAMPLE = {
    "host_name": {"match_on": ["host1", "host2"], "operator": "one_of"},
    "host_tags": [{"key": "criticality", "operator": "is", "value": "prod"}],
    "host_labels": [{"key": "os", "operator": "is", "value": "windows"}],
    "service_labels": [{"key": "os", "operator": "is", "value": "windows"}],
    "host_label_groups": [
        {"operator": "and", "label_group": [{"operator": "and", "label": "os:windows"}]}
    ],
    "service_label_groups": [
        {"operator": "and", "label_group": [{"operator": "and", "label": "os:windows"}]}
    ],
    "service_description": {"match_on": ["foo1", "bar2"], "operator": "none_of"},
}

_MOVE_POSITION_DESCRIPTION = (
    "The type of position to move to. Note that you cannot move rules before rules managed by a "
    "Quick setup. In the case of `top_of_folder` your rule will instead be after all managed "
    "rules. If you specify a managed rule in `after_specific_rule` or `before_specific_rule` you "
    "will receive an error."
)


def _parse_python_string(value: str) -> object:
    """Parse a Python literal expression."""
    try:
        return ast.literal_eval(value)
    except SyntaxError as exc:
        msg = str(exc).replace(" (<unknown>, line 1)", "")
        raise ValueError(f"Syntax Error: {msg} in {value!r}") from exc
    except ValueError as exc:
        raise ValueError(f"Not a Python data structure: {value!r}") from exc


type PythonStringValue = Annotated[object, TypedPlainValidator(str, _parse_python_string)]


@api_model
class LabelConditionRequestModel:
    operator: Literal["and", "not", "or"] = api_field(
        description=(
            "Boolean operator that connects the label to other labels within the same label group "
            "condition"
        ),
        default="and",
    )
    label: str = api_field(
        description='A label of format "{key}:{value}"',
        example="os:windows",
    )


@api_model
class LabelGroupConditionRequestModel:
    operator: Literal["and", "not", "or"] = api_field(
        description="Boolean operator that connects the label group to other label groups",
        default="and",
    )
    label_group: list[LabelConditionRequestModel] = api_field(
        description="A list of label conditions that form a label group",
        example=[{"operator": "and", "label": "os:linux"}],
    )


@api_model
class RulePropertiesRequestModel:
    description: str | None = api_field(
        description="A description for this rule to inform other users about its intent.",
        example="This rule is here to foo the bar hosts.",
        default=None,
    )
    comment: str | None = api_field(
        description="Any comment string.",
        example="Created yesterday due to foo hosts behaving weird.",
        default=None,
    )
    documentation_url: str | None = api_field(
        description="An URL (e.g. an internal Wiki entry) which explains this rule.",
        example="http://example.com/wiki/ConfiguringFooBarHosts",
        default=None,
    )
    disabled: bool = api_field(
        description="When set to False, the rule will be evaluated. Default is False.",
        example=False,
        default=False,
    )


@api_model
class LabelOldConditionModel:
    """Deprecated old-format label condition (``host_labels`` / ``service_labels``)."""

    key: str = api_field(description="The key of the label. e.g. 'os' in 'os:windows'")
    operator: Literal["is", "is_not"] = api_field(description="How the label should be matched.")
    value: str = api_field(description="The value of the label. e.g. 'windows' in 'os:windows'")


def _fold_old_labels(
    labels: list[LabelOldConditionModel],
) -> list[LabelGroupConditionRequestModel]:
    """Convert the deprecated old label format into the grouped format.

    Two different labels are folded into a single ``and`` group:

    >>> _fold_old_labels([LabelOldConditionModel(key="os", operator="is", value="windows"),
    ...                   LabelOldConditionModel(key="foo", operator="is_not", value="bar")])
    [LabelGroupConditionRequestModel(operator='and', label_group=[LabelConditionRequestModel(operator='and', label='os:windows'), LabelConditionRequestModel(operator='not', label='foo:bar')])]

    The same key with different values is allowed (e.g. to exclude several values
    of one key):

    >>> _fold_old_labels([LabelOldConditionModel(key="os", operator="is_not", value="windows"),
    ...                   LabelOldConditionModel(key="os", operator="is_not", value="linux")])
    [LabelGroupConditionRequestModel(operator='and', label_group=[LabelConditionRequestModel(operator='not', label='os:windows'), LabelConditionRequestModel(operator='not', label='os:linux')])]

    An exact duplicate label (same key and value) is rejected:

    >>> _fold_old_labels([LabelOldConditionModel(key="os", operator="is", value="windows"),
    ...                   LabelOldConditionModel(key="os", operator="is", value="windows")])
    Traceback (most recent call last):
    ...
    ValueError: Labels can only be used once. Duplicate label: 'os:windows'
    """
    label_group: list[LabelConditionRequestModel] = []
    labels_added: list[str] = []
    for entry in labels:
        label_str = f"{entry.key}:{entry.value}"
        if label_str in labels_added:
            raise ValueError(f"Labels can only be used once. Duplicate label: {label_str!r}")
        label_group.append(
            LabelConditionRequestModel(
                operator="not" if entry.operator == "is_not" else "and", label=label_str
            )
        )
        labels_added.append(label_str)
    return [LabelGroupConditionRequestModel(operator="and", label_group=label_group)]


@api_model
class RuleConditionsRequestModel:
    host_name: MatchExpressionModel | None = api_field(
        description=(
            "Here you can enter a list of explicit host names that the rule should or should not "
            "apply to. Leave this option disabled if you want the rule to apply for all hosts "
            "specified by the given tags. The names that you enter here are compared with case "
            "sensitive exact matching. Alternatively you can use regular expressions if you enter "
            "a tilde `~` as the first character. That regular expression must match the beginning "
            "of the host names in question."
        ),
        default=None,
    )
    host_tags: list[TagConditionModel] | None = api_field(
        description=(
            "The rule will only be applied to hosts fulfilling all the host tag conditions listed "
            "here, even if they appear in the list of explicit host names."
        ),
        default=None,
    )
    host_label_groups: list[LabelGroupConditionRequestModel] | None = api_field(
        description=(
            "Further restrict this rule by applying host label conditions. Although all items in "
            "this list have a default operator value, the operator value for the the first item "
            "in the list does not have any effect."
        ),
        default=None,
    )
    service_label_groups: list[LabelGroupConditionRequestModel] | None = api_field(
        description=(
            "Restrict the application of the rule, by checking against service label conditions. "
            "Although all items in this list have a default operator value, the operator value "
            "for the the first item in the list does not have any effect."
        ),
        default=None,
    )
    service_description: MatchExpressionModel | None = api_field(
        description=(
            "Specify a list of service patterns this rule shall apply to. The patterns must match "
            "the beginning of the service in question. Adding a `$` to the end forces an exact "
            "match. Patterns use regular expressions, and the match is performed case sensitive "
            "from the beginning. BE AWARE: Depending on the service ruleset the service_description "
            "is only a check item or a full service name."
        ),
        default=None,
    )
    host_labels: list[LabelOldConditionModel] | None = api_field(
        description=(
            "Further restrict this rule by applying host label conditions. - Deprecated: Use "
            "`host_label_groups` instead."
        ),
        example=[{"key": "os", "operator": "is", "value": "windows"}],
        deprecated=True,
        default=None,
    )
    service_labels: list[LabelOldConditionModel] | None = api_field(
        description=(
            "Restrict the application of the rule, by checking against service label conditions. - "
            "Deprecated: Use `service_label_groups` instead."
        ),
        example=[{"key": "os", "operator": "is", "value": "windows"}],
        deprecated=True,
        default=None,
    )

    @model_validator(mode="after")
    def _fold_deprecated_labels(self) -> Self:
        """Reject the old + new label formats together and fold the old format into the new one."""
        if self.host_labels and self.host_label_groups:
            raise ValueError(
                "Please provide the field 'host_labels' OR 'host_label_groups', not both."
            )
        if self.service_labels and self.service_label_groups:
            raise ValueError(
                "Please provide the field 'service_labels' OR 'service_label_groups', not both."
            )
        if self.host_labels:
            self.host_label_groups = _fold_old_labels(self.host_labels)
            self.host_labels = None
        if self.service_labels:
            self.service_label_groups = _fold_old_labels(self.service_labels)
            self.service_labels = None
        return self


@api_model
class UpdateRuleModel:
    properties: RulePropertiesRequestModel | None = api_field(
        description="Configuration values for rules.",
        example={"disabled": False},
        default=None,
    )
    value_raw: PythonStringValue = api_field(
        description=_VALUE_RAW_DESCRIPTION,
        example="{'cmk/os_family': 'linux'}",
    )
    conditions: RuleConditionsRequestModel | None = api_field(
        description="Conditions.",
        example=_CONDITIONS_EXAMPLE,
        default=None,
    )


@api_model
class CreateRuleModel(UpdateRuleModel):
    ruleset: str = api_field(description=RULESET_NAME_DESCRIPTION, example="host_label_rules")
    folder: AnnotatedFolder = api_field(
        description="The path name of the folder.", example="~hosts~linux"
    )


@api_model
class MoveToFolderModel:
    position: Literal["top_of_folder", "bottom_of_folder"] = api_field(
        description=_MOVE_POSITION_DESCRIPTION, example="top_of_folder"
    )
    folder: AnnotatedFolder = api_field(description="The path name of the folder.", example="/")


@api_model
class MoveToSpecificRuleModel:
    position: Literal["after_specific_rule", "before_specific_rule"] = api_field(
        description=_MOVE_POSITION_DESCRIPTION, example="after_specific_rule"
    )
    rule_id: str = api_field(
        description="The UUID of the rule to move after/before.",
        example="f8b74720-a454-4242-99c4-62994ef0f2bf",
    )
