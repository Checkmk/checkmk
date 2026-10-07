#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import dataclasses
from http import HTTPStatus

from cmk.ccc.site import omd_site
from cmk.gui import exceptions
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.openapi.api_endpoints.rule.conditions import (
    host_tags_to_api,
    host_tags_to_internal,
    label_groups_to_api,
    label_groups_to_internal,
    match_expr_to_api,
    match_expr_to_internal,
)
from cmk.gui.openapi.framework import ApiContext, ETag
from cmk.gui.openapi.framework.endpoint_link import link_to_endpoint
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.utils import ProblemException, RestAPIRequestDataValidationException
from cmk.gui.user_sites import activation_sites
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree
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
from cmk.ruleset_matcher.conditions import (
    allow_host_label_conditions,
    allow_service_label_conditions,
)
from cmk.ruleset_matcher.definition import RuleGroup
from cmk.ruleset_matcher.matcher import RuleOptionsSpec
from cmk.web.utils import permission_verification as permissions
from cmk.web.utils.escaping import strip_tags

from ._family import RULE_FAMILY
from .models.request_models import (
    RuleConditionsRequestModel,
    RulePropertiesRequestModel,
)
from .models.response_models import (
    RuleConditionsModel,
    RuleExtensionsModel,
    RuleObjectModel,
    RulePropertiesResponseModel,
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
#   .--validation / lookup-------------------------------------------------.


def validate_value(ruleset: Ruleset, value: RuleValue) -> None:
    """Validate a rule value via the form spec, falling back to the legacy valuespec.

    The value is persisted verbatim, so it must already be in the current format. A value
    that only becomes valid after migration is rejected instead of being migrated silently:
    unlike the GUI - which renders the migrated value before the user saves it - the API
    client never gets to see such a change, so persisting it would store something the
    client is unaware of (and the ``value_raw`` reported back would no longer match the
    input).

    The FormSpec path validates the raw value without migration (``migrate_values=False``),
    so an outdated value is already rejected there. The legacy valuespec validates the
    migrated value, hence we additionally reject values whose migrated form differs from
    the input.
    """
    # FormSpec validation
    try:
        if problems := get_visitor(
            ruleset.rulespec.form_spec, VisitorOptions(migrate_values=False, mask_values=False)
        ).validate(RawDiskData(value)):
            raise ProblemException(
                status=HTTPStatus.BAD_REQUEST,
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

        raise ProblemException(
            status=HTTPStatus.BAD_REQUEST, title=title, detail=strip_tags(exc.message)
        )

    # Reject values that are not already in the current format. The legacy valuespec
    # validates the migrated value, so a value in an outdated format can pass validation
    # above. We deep-copy before migrating because some migrations mutate their input.
    if valuespec.transform_value(copy.deepcopy(value)) != value:
        raise ProblemException(
            status=HTTPStatus.BAD_REQUEST,
            title="Outdated value format",
            detail=(
                "The provided 'value_raw' is in an outdated format. Please migrate it to the "
                "current format - for example by opening and saving the rule in the GUI - and "
                "send the migrated value."
            ),
        )


def get_rule_by_id(
    tree: FolderTree, rule_uuid: str, all_rulesets: AllRulesets | None = None
) -> RuleEntry:
    if all_rulesets is None:
        all_rulesets = AllRulesets.load_all_rulesets(tree)

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
        status=HTTPStatus.NOT_FOUND,
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
        status=HTTPStatus.BAD_REQUEST,
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
    # `match_expr_to_api` returns `None` only for an absent (`None`) condition; an empty
    # match_on list is a distinct, meaningful condition ("matches no host/service") and
    # must not be conflated with "no condition set".
    host_name = match_expr_to_api(conditions.host_name, "adaptive")
    service_description = match_expr_to_api(conditions.service_description, "always")
    # host_tags / host_label_groups / service_label_groups are always emitted (the old serializer
    # only dropped `None` values, and these internal fields default to `{}` / `[]`, never `None`).
    return RuleConditionsModel(
        host_name=ApiOmitted() if host_name is None else host_name,
        host_tags=host_tags_to_api(conditions.host_tags),
        host_label_groups=label_groups_to_api(conditions.host_label_groups),
        service_description=ApiOmitted() if service_description is None else service_description,
        service_label_groups=label_groups_to_api(conditions.service_label_groups),
    )


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
                as_relation="self",
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
        acting_user=api_context.user.id,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=api_context.config.wato_use_git),
            index_update_change_hook,
        ),
    )
