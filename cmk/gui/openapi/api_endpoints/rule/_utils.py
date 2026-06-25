#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.ccc.site import omd_site
from cmk.gui import exceptions
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.openapi.framework import ApiContext, ETag
from cmk.gui.openapi.framework.endpoint_link import link_to_endpoint
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.utils import ProblemException, RestAPIRequestDataValidationException
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.utils.escaping import strip_tags
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    Rule,
    RuleConditions,
    RuleOptions,
    Ruleset,
    RulesetCollection,
    RuleValue,
    visible_ruleset,
    visible_rulesets,
)
from cmk.gui.watolib.rulespecs import FormSpecNotImplementedError
from cmk.utils.labels import LabelGroups
from cmk.utils.rulesets.conditions import (
    allow_host_label_conditions,
    allow_service_label_conditions,
    HostOrServiceConditionRegex,
    HostOrServiceConditions,
    HostOrServiceConditionsSimple,
)
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import (
    RuleOptionsSpec,
    TagCondition,
    TagConditionNE,
    TagConditionNOR,
    TagConditionOR,
)
from cmk.utils.tags import TagGroupID, TagID

from ._family import RULE_FAMILY
from .models.request_models import (
    LabelGroupConditionRequestModel,
    RuleConditionsRequestModel,
    RulePropertiesRequestModel,
)
from .models.response_models import (
    LabelConditionModel,
    LabelGroupConditionModel,
    MatchExpressionModel,
    RuleConditionsModel,
    RuleExtensionsModel,
    RuleObjectModel,
    RulePropertiesResponseModel,
    TagConditionCollectionModel,
    TagConditionModel,
    TagConditionScalarModel,
)

PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.rulesets"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
    ]
)

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        *PERMISSIONS.perms,
    ]
)


# NOTE: This is a dataclass and no namedtuple because it needs to be mutable. See `move_rule`.
@dataclasses.dataclass
class RuleEntry:
    rule: Rule
    ruleset: Ruleset
    all_rulesets: AllRulesets
    # NOTE: Can't be called "index", because mypy doesn't like that. Duh.
    index_nr: int
    folder: Folder


# .
#   .--conversions---------------------------------------------------------.
#   |  Bidirectional API <-> internal conversion (ported from the old      |
#   |  marshmallow `fields.py` pre_dump / post_load hooks).                |
#   '----------------------------------------------------------------------'


def _scalar_value(
    value: str | None, operator: Literal["is", "is_not"]
) -> TagID | None | TagConditionNE:
    """Construct a scalar internal tag value or the negation of it.

    >>> _scalar_value("foo", "is")
    'foo'
    >>> _scalar_value("foo", "is_not")
    {'$ne': 'foo'}
    """
    tag_id = TagID(value) if value is not None else None
    if operator == "is":
        return tag_id
    return {"$ne": tag_id}


def _collection_value(
    value: Sequence[str | None], operator: Literal["one_of", "none_of"]
) -> TagConditionOR | TagConditionNOR:
    """Construct a collection internal tag value.

    >>> _collection_value(["Beavis", "Butthead"], "one_of")
    {'$or': ['Beavis', 'Butthead']}
    >>> _collection_value(["Beavis", "Butthead"], "none_of")
    {'$nor': ['Beavis', 'Butthead']}
    """
    tag_ids = [TagID(v) if v is not None else None for v in value]
    if operator == "one_of":
        return {"$or": tag_ids}
    return {"$nor": tag_ids}


def host_tags_to_internal(
    host_tags: Sequence[TagConditionModel],
) -> dict[TagGroupID, TagCondition]:
    """Convert the API host-tag list into the internal dict keyed by tag name."""
    result: dict[TagGroupID, TagCondition] = {}
    for cond in host_tags:
        key = TagGroupID(cond.key)
        if key in result:
            raise RestAPIRequestDataValidationException(
                title="Invalid condition.",
                detail=f"Key {cond.key!r} may only appear once!",
            )
        if isinstance(cond, TagConditionCollectionModel):
            result[key] = _collection_value(cond.value, cond.operator)
        else:
            result[key] = _scalar_value(cond.value, cond.operator)
    return result


def host_tags_to_api(host_tags: Mapping[TagGroupID, TagCondition]) -> list[TagConditionModel]:
    """Convert the internal host-tag dict into the API list."""
    result: list[TagConditionModel] = []
    for key, value in host_tags.items():
        match value:
            case None | str():
                result.append(TagConditionScalarModel(key=key, operator="is", value=value))
            case {"$ne": str() | None as negated}:
                result.append(TagConditionScalarModel(key=key, operator="is_not", value=negated))
            case {"$or": list() as values}:
                result.append(TagConditionCollectionModel(key=key, operator="one_of", value=values))
            case {"$nor": list() as values}:
                result.append(
                    TagConditionCollectionModel(key=key, operator="none_of", value=values)
                )
            case _:
                raise RestAPIRequestDataValidationException(
                    title="Invalid condition.",
                    detail=f"Unsupported tag condition for {key!r}: {value!r}",
                )
    return result


def _wrap_adaptive(entry: str) -> HostOrServiceConditionRegex | str:
    if entry and entry[0] == "~":
        return {"$regex": f"^{entry[1:]}"}
    return entry


def match_expr_to_internal(
    model: MatchExpressionModel, use_regex: Literal["always", "adaptive"]
) -> HostOrServiceConditions:
    """Convert an API match expression into the internal host/service condition."""
    match_on: HostOrServiceConditionsSimple
    if use_regex == "always":
        match_on = [{"$regex": entry} for entry in model.match_on]
    else:
        match_on = [_wrap_adaptive(entry) for entry in model.match_on]

    if model.operator == "one_of":
        return match_on
    return {"$nor": match_on}


def _unwrap_regex(
    entry: HostOrServiceConditionRegex | str, use_regex: Literal["always", "adaptive"]
) -> str:
    if isinstance(entry, dict):
        regex = entry["$regex"]
        if use_regex == "adaptive" and regex:
            return "~" + (regex[1:] if regex[0] == "^" else regex)
        return regex
    return entry


def match_expr_to_api(
    data: HostOrServiceConditions | None, use_regex: Literal["always", "adaptive"]
) -> MatchExpressionModel | None:
    """Convert the internal host/service condition into an API match expression."""
    operator: Literal["one_of", "none_of"]
    entries: HostOrServiceConditionsSimple
    match data:
        case None | []:
            return None
        case {"$nor": list() as entries}:
            operator = "none_of"
        case list() as entries:
            operator = "one_of"
        case _:
            return None

    return MatchExpressionModel(
        match_on=[_unwrap_regex(entry, use_regex) for entry in entries],
        operator=operator,
    )


def label_groups_to_internal(
    groups: Sequence[LabelGroupConditionRequestModel] | None,
) -> LabelGroups | None:
    """Convert API label groups into the internal label-group format.

    >>> from cmk.gui.openapi.api_endpoints.rule.models.request_models import (
    ...     LabelConditionRequestModel, LabelGroupConditionRequestModel)
    >>> label_groups_to_internal(
    ...     [LabelGroupConditionRequestModel(operator="and",
    ...         label_group=[LabelConditionRequestModel(operator="and", label="os:windows")])])
    [('and', [('and', 'os:windows')])]
    """
    if groups is None:
        return None
    return [
        (group.operator, [(cond.operator, cond.label) for cond in group.label_group])
        for group in groups
    ]


def label_groups_to_api(label_groups: LabelGroups) -> list[LabelGroupConditionModel]:
    """Convert internal label groups into the API label-group format."""
    return [
        LabelGroupConditionModel(
            operator=group_op,
            label_group=[
                LabelConditionModel(operator=op, label=label) for op, label in label_group
            ],
        )
        for group_op, label_group in label_groups
    ]


# .
#   .--validation / lookup-------------------------------------------------.


def validate_value(ruleset: Ruleset, value: RuleValue) -> None:
    """Validate a rule value via the form spec, falling back to the legacy valuespec."""
    # FormSpec validation
    try:
        if problems := get_visitor(
            ruleset.rulespec.form_spec, VisitorOptions(migrate_values=False, mask_values=False)
        ).validate(RawDiskData(value)):
            raise ProblemException(
                status=400,
                title=f"Problem in field {'.'.join(problems[0].location)}",
                detail=problems[0].message,
            )
        return
    except FormSpecNotImplementedError:
        pass

    # Legacy valuespec validation
    try:
        valuespec = ruleset.rulespec.valuespec
        valuespec.validate_datatype(value, "")
        valuespec.validate_value(value, "")
    except exceptions.MKUserError as exc:
        if exc.varname is None:
            title = "A field has a problem"
        else:
            field_name = strip_tags(exc.varname.replace("_p_", ""))
            title = f"Problem in (sub-)field {field_name!r}"

        raise ProblemException(status=400, title=title, detail=strip_tags(exc.message))


def get_rule_by_id(rule_uuid: str, all_rulesets: AllRulesets | None = None) -> RuleEntry:
    if all_rulesets is None:
        all_rulesets = AllRulesets.load_all_rulesets()

    for ruleset in visible_rulesets(all_rulesets.get_rulesets()).values():
        folder: Folder
        index: int
        rule: Rule
        for folder, index, rule in ruleset.get_rules():
            if rule.id == rule_uuid:
                return RuleEntry(
                    index_nr=index,
                    rule=rule,
                    folder=folder,
                    ruleset=ruleset,
                    all_rulesets=all_rulesets,
                )

    raise ProblemException(
        status=404,
        title="Unknown rule.",
        detail=f"Rule with UUID '{rule_uuid}' was not found.",
    )


def validate_rule_move(lhs: RuleEntry, rhs: RuleEntry) -> None:
    if lhs.ruleset.name != rhs.ruleset.name:
        raise RestAPIRequestDataValidationException(
            title="Invalid rule move.", detail="The two rules are not in the same ruleset."
        )
    if lhs.rule.id == rhs.rule.id:
        raise RestAPIRequestDataValidationException(
            title="Invalid rule move", detail="You cannot move a rule before/after itself."
        )


def retrieve_from_rulesets(rulesets: RulesetCollection, ruleset_name: str) -> Ruleset:
    ruleset_exception = ProblemException(
        status=400,
        title="Unknown ruleset.",
        detail=f"The ruleset of name {ruleset_name!r} is not known.",
    )
    try:
        ruleset = rulesets.get(ruleset_name)
    except KeyError:
        # We renamed the discovery rules from 2.5 -> 3.0
        # To not break existing API clients we check for the old name if the new one is not found.
        # Can be removed after 3.0 is branched off.
        try:
            ruleset = rulesets.get(RuleGroup.DiscoveryParameters(ruleset_name))
        except KeyError:
            raise ruleset_exception

    if not visible_ruleset(ruleset.rulespec.name):
        raise ruleset_exception

    return ruleset


# .
#   .--rule building / serialization---------------------------------------.


def properties_to_config(model: RulePropertiesRequestModel | None) -> RuleOptionsSpec:
    if model is None:
        return {}
    config: RuleOptionsSpec = {"disabled": model.disabled}
    if model.description is not None:
        config["description"] = model.description
    if model.comment is not None:
        config["comment"] = model.comment
    if model.documentation_url is not None:
        config["docu_url"] = model.documentation_url
    return config


def create_rule_object(
    folder: Folder,
    ruleset: Ruleset,
    conditions: RuleConditionsRequestModel | None,
    properties: RulePropertiesRequestModel | None,
    validated_value: RuleValue,
    rule_id: str,
) -> Rule:
    if conditions is None:
        conditions = RuleConditionsRequestModel()
    return Rule(
        rule_id,
        folder,
        ruleset,
        RuleConditions(
            host_folder=folder.path(),
            host_tags=(
                host_tags_to_internal(conditions.host_tags) if conditions.host_tags else None
            ),
            host_label_groups=(
                label_groups_to_internal(conditions.host_label_groups)
                if allow_host_label_conditions(ruleset.rulespec.name)
                else None
            ),
            host_name=(
                match_expr_to_internal(conditions.host_name, "adaptive")
                if conditions.host_name
                else None
            ),
            service_description=(
                match_expr_to_internal(conditions.service_description, "always")
                if conditions.service_description and ruleset.item_type()
                else None
            ),
            service_label_groups=(
                label_groups_to_internal(conditions.service_label_groups)
                if ruleset.item_type() and allow_service_label_conditions(ruleset.rulespec.name)
                else None
            ),
        ),
        RuleOptions.from_config(properties_to_config(properties)),
        validated_value,
    )


def _masked_rule_value(rule: Rule) -> str:
    try:
        return repr(
            get_visitor(
                rule.ruleset.rulespec.form_spec,
                VisitorOptions(migrate_values=False, mask_values=True),
            ).to_disk(RawDiskData(rule.value))
        )
    except FormSpecNotImplementedError:
        return repr(rule.ruleset.rulespec.valuespec.mask(rule.value))


def _properties_to_api(config: RuleOptionsSpec) -> RulePropertiesResponseModel:
    return RulePropertiesResponseModel(
        description=config.get("description", ApiOmitted()),
        comment=config.get("comment", ApiOmitted()),
        documentation_url=config.get("docu_url", ApiOmitted()),
        disabled=config.get("disabled", ApiOmitted()),
    )


def _conditions_to_api(conditions: RuleConditions) -> RuleConditionsModel:
    # host_tags / host_label_groups / service_label_groups are always emitted (the old serializer
    # only dropped `None` values, and these internal fields default to `{}` / `[]`, never `None`).
    model = RuleConditionsModel(
        host_tags=host_tags_to_api(conditions.host_tags),
        host_label_groups=label_groups_to_api(conditions.host_label_groups),
        service_label_groups=label_groups_to_api(conditions.service_label_groups),
    )
    # `match_expr_to_api` already returns `None` for absent (`None`/empty) conditions.
    if (host_name := match_expr_to_api(conditions.host_name, "adaptive")) is not None:
        model.host_name = host_name
    if (
        service_description := match_expr_to_api(conditions.service_description, "always")
    ) is not None:
        model.service_description = service_description
    return model


def serialize_rule(rule_entry: RuleEntry, api_context: ApiContext) -> RuleObjectModel:
    rule = rule_entry.rule
    return RuleObjectModel(
        domainType="rule",
        id=rule.id,
        title=rule.description(),
        links=[
            link_to_endpoint(
                family=RULE_FAMILY.name,
                link_relation="cmk/show",
                version=api_context.version,
                host_url=api_context.host_url,
                parameters={"rule_id": rule.id},
                as_self=True,
            ),
            link_to_endpoint(
                family=RULE_FAMILY.name,
                link_relation=".../delete",
                version=api_context.version,
                host_url=api_context.host_url,
                parameters={"rule_id": rule.id},
            ),
        ],
        extensions=RuleExtensionsModel(
            ruleset=rule.ruleset.name,
            folder=rule_entry.folder,
            folder_index=rule_entry.index_nr,
            properties=_properties_to_api(rule.rule_options.to_config()),
            value_raw=_masked_rule_value(rule),
            conditions=_conditions_to_api(rule.conditions),
        ),
    )


def rule_etag(rule: Rule) -> ETag:
    return ETag(
        {
            "id": rule.id,
            "value": repr(rule.value),
            "host_tags": repr(dict(rule.conditions.host_tags)),
            "host_name": repr(rule.conditions.host_name),
            "service_description": repr(rule.conditions.service_description),
            "host_label_groups": repr(rule.conditions.host_label_groups),
            "service_label_groups": repr(rule.conditions.service_label_groups),
            "properties": repr(rule.rule_options.to_config()),
        }
    )


def make_pending_changes(api_context: ApiContext) -> PendingChanges:
    return PendingChanges(
        activation_sites=activation_sites(api_context.config.sites),
        local_site=omd_site(),
        acting_user=api_context.user_id,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=api_context.config.wato_use_git),
            index_update_change_hook,
        ),
    )
