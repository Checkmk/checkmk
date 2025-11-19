#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Sequence
from dataclasses import dataclass

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.form_specs import (
    get_visitor,
    process_validation_messages,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.openapi.utils import RestAPIRequestGeneralException
from cmk.gui.utils import gen_id
from cmk.gui.watolib.hosts_and_folders import FolderTree
from cmk.gui.watolib.rulesets import (
    create_rule_catalog,
    FolderRulesets,
    get_rule_conditions_from_catalog_value,
    get_rule_options_from_catalog_value,
    may_edit_ruleset,
    Rule,
    RuleIdentifier,
    RuleSpecItem,
)
from cmk.gui.watolib.rulespecs import Rulespec, rulespec_registry
from cmk.rulesets.v1.form_specs import FormSpec


def _check_edit_permissions(name: str, user: LoggedInUser) -> None:
    user.need_permission("wato.rulesets")
    if not may_edit_ruleset(name):
        raise MKAuthException(_("You are not permitted to edit this rule."))


def _get_rule_spec(name: str) -> Rulespec:
    try:
        return rulespec_registry[name]
    except KeyError:
        raise MKUserError(None, _("The rule specification %r does not exist.") % name)


def rule_form_spec_title(name: str) -> str:
    return _get_rule_spec(name).title or ""


def _get_rule_spec_and_form_spec(
    rule_identifier: RuleIdentifier,
    tree: FolderTree,
    user: LoggedInUser,
) -> tuple[Rulespec, FormSpec]:
    rule_spec = _get_rule_spec(rule_identifier.name)

    if not rule_spec.has_form_spec:
        raise MKUserError(
            None, _('The ruleset "%s" uses legacy valuespecs.') % rule_identifier.name
        )

    return (
        rule_spec,
        create_rule_catalog(
            rule_identifier=rule_identifier,
            is_locked=None,
            title=rule_spec.title,
            value_parameter_form=rule_spec.form_spec,
            tree=tree,
            rule_spec_name=rule_spec.name,
            rule_spec_item=(
                RuleSpecItem(rule_spec.item_name, rule_spec.item_enum or [])
                if (rule_spec.item_type and rule_spec.item_name is not None)
                else None
            ),
        ),
    )


@dataclass(frozen=True, kw_only=True)
class RuleFormSpecDescription:
    ident: str
    description: str


def save_rule_form_spec_from_slidein_schema(
    name: str, data: RawFrontendData, tree: FolderTree, user: LoggedInUser
) -> RuleFormSpecDescription:
    _check_edit_permissions(name, user)

    if not isinstance(data.value, dict):
        raise TypeError(data.value)

    rule_id = data.value["properties"]["id"]
    rule_spec, form_spec = _get_rule_spec_and_form_spec(
        RuleIdentifier(id=rule_id, name=name), tree, user
    )

    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))
    process_validation_messages(visitor.validate(data))

    disk_data = visitor.to_disk(data)
    if not isinstance(disk_data, dict):
        raise TypeError(disk_data)

    rule_conditions = get_rule_conditions_from_catalog_value(disk_data)
    folder = tree.folder(rule_conditions.host_folder)
    folder.permissions.need_permission("write")

    rulesets = FolderRulesets.load_folder_rulesets(folder)
    ruleset = rulesets.get(name)
    try:
        ruleset.get_rule_by_id(rule_id)
    except KeyError:
        pass
    else:
        raise RestAPIRequestGeneralException(
            status=409,
            title="Rule ID conflict",
            detail=f"Cannot overwrite the existing rule {rule_id!r}",
        )

    rule = Rule(
        rule_id,
        folder,
        ruleset,
        rule_conditions,
        get_rule_options_from_catalog_value(disk_data),
        disk_data["value"]["value"],
    )
    index = ruleset.append_rule(folder, rule)
    rulesets.save_folder(
        pprint_value=active_config.wato_pprint_config,
        debug=active_config.debug,
    )
    ruleset.add_new_rule_change(index, folder, rule, use_git=active_config.wato_use_git)

    return RuleFormSpecDescription(ident=name, description=rule_spec.title or "")


def get_rule_form_spec_slidein_schema(name: str, tree: FolderTree, user: LoggedInUser) -> FormSpec:
    _check_edit_permissions(name, user)
    _rule_spec, form_spec = _get_rule_spec_and_form_spec(
        RuleIdentifier(id=gen_id(), name=name), tree, user
    )
    return form_spec


def list_rule_form_spec_descriptions(
    name: str, user: LoggedInUser
) -> Sequence[RuleFormSpecDescription]:
    user.need_permission("wato.rulesets")
    return [
        RuleFormSpecDescription(ident=name, description=rule_spec.title or "")
        for rule_spec_name, rule_spec in rulespec_registry.items()
        if name == rule_spec_name
    ]
