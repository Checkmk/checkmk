#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from copy import deepcopy

import pytest

from cmk.automations.results import DeleteHostsResult
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.gui import login
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.logged_in import user
from cmk.gui.permissions import all_permissions
from cmk.gui.quick_setup.config_setups.azure_v2.stages import azure_collect_params
from cmk.gui.quick_setup.handlers.utils import InfoLogger
from cmk.gui.quick_setup.v0_unstable.definitions import (
    QSHostName,
    QSHostPath,
    QSSiteSelection,
    UniqueBundleIDStr,
    UniqueFormSpecIDStr,
)
from cmk.gui.quick_setup.v0_unstable.predefined import complete
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupContext
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib import check_mk_automations
from cmk.gui.watolib.configuration_bundle_store import BundleId, load_configuration_bundles
from cmk.gui.watolib.configuration_bundles import CreateRule, delete_config_bundle
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree
from cmk.gui.watolib.pending_changes import PendingChanges, PendingChangesStore
from cmk.gui.watolib.rulesets import Rule, SingleRulesetRecursively
from cmk.plugins.azure_v2.rulesets import azure
from cmk.ruleset_matcher.matcher import RuleConditionsSpec
from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_QUICK_SETUP
from tests.testlib.unit.gui.web_test_app import SetConfig


def test_explicit_password_in_cascading_choice_is_replaced_by_stored_password() -> None:
    rule_params = {
        "auth": (
            "access_key",
            {"secret": ("cmk_postprocessed", "explicit_password", ("pw_id", "secret"))},
        )
    }

    converted = complete.convert_explicit_passwords_to_stored_passwords(rule_params, {"pw_id"})

    assert converted == {
        "auth": (
            "access_key",
            {"secret": ("cmk_postprocessed", "stored_password", ("pw_id", ""))},
        )
    }


def test_explicit_password_in_list_is_replaced_by_stored_password() -> None:
    rule_params = {
        "secrets": [
            "unrelated",
            ("cmk_postprocessed", "explicit_password", ("pw_id", "secret")),
        ]
    }

    converted = complete.convert_explicit_passwords_to_stored_passwords(rule_params, {"pw_id"})

    assert converted == {
        "secrets": [
            "unrelated",
            ("cmk_postprocessed", "stored_password", ("pw_id", "")),
        ]
    }


def test_explicit_password_with_unknown_id_is_kept() -> None:
    rule_params = {
        "auth": (
            "access_key",
            {"secret": ("cmk_postprocessed", "explicit_password", ("other_id", "secret"))},
        )
    }

    converted = complete.convert_explicit_passwords_to_stored_passwords(rule_params, {"pw_id"})

    assert converted == rule_params


_BUNDLE_ID = BundleId("my_azure_config")

_FORM_DATA: ParsedFormData = {
    FormSpecId(UniqueFormSpecIDStr): {UniqueBundleIDStr: _BUNDLE_ID},
    FormSpecId("credentials"): {
        "subscription": ("all_subscriptions", None),
        "tenant_name": "my_tenant",
        "tenant": "my_tenant_id",
        "client": "my_client_id",
        "secret": (
            "cmk_postprocessed",
            "explicit_password",
            ("uuid-azure-secret", "my_client_secret"),
        ),
        "authority": "global_",
    },
    FormSpecId("host_data"): {QSHostName: "azure_host", QSHostPath: "azure_folder"},
    # The Quick Setup skips the service discovery for a remote site without replication.
    FormSpecId("site"): {QSSiteSelection: "remote"},
    FormSpecId("configure_services_to_monitor"): {"services": []},
}

_ADDITIONAL_RULESET = "ping_levels"


def _additional_rules_of(ruleset: str) -> complete.AdditionalRules:
    def additional_rules(
        _params: Mapping[str, object], bundle_id: BundleId, site_id: SiteId, folder: Folder
    ) -> Sequence[CreateRule]:
        return [
            complete.create_bundle_rule(
                params={},
                host_path=folder.path(),
                rulespec_name=ruleset,
                condition=RuleConditionsSpec(host_folder=folder.path()),
                bundle_id=bundle_id,
                site_id=site_id,
            )
        ]

    return additional_rules


def _sites_with_remote_site(**remote_site_config: object) -> Mapping[SiteId, object]:
    return {
        **active_config.sites,
        SiteId("remote"): {
            **active_config.sites[omd_site()],
            "id": "remote",
            "socket": ("tcp", {}),
            **remote_site_config,
        },
    }


@pytest.fixture(name="bundle_tree")
def fixture_bundle_tree(set_config: SetConfig) -> FolderTree:
    with set_config(sites=_sites_with_remote_site(replication=None)):
        tree = QuickSetupContext.from_config(active_config, user).tree
        complete.create_and_save_special_agent_bundle_custom_collect_params(
            special_agent_name="azure_v2",
            parameter_form=azure.formspec(),
            all_stages_form_data=_FORM_DATA,
            custom_collect_params=azure_collect_params,
            progress_logger=InfoLogger(),
            tree=tree,
            additional_rules=_additional_rules_of(_ADDITIONAL_RULESET),
        )
    return tree


def _additional_rules(tree: FolderTree) -> Sequence[Rule]:
    ruleset = SingleRulesetRecursively.load_single_ruleset_recursively(
        tree, _ADDITIONAL_RULESET
    ).get(_ADDITIONAL_RULESET)
    return [rule for _folder, _index, rule in ruleset.get_rules()]


@pytest.mark.usefixtures("with_admin_login", "mock_password_file_regeneration")
def test_bundle_creates_the_additional_rules_locked_by_the_bundle(bundle_tree: FolderTree) -> None:
    assert [rule.locked_by for rule in _additional_rules(bundle_tree)] == [
        GlobalIdent(site_id=omd_site(), program_id=PROGRAM_ID_QUICK_SETUP, instance_id=_BUNDLE_ID)
    ]


@pytest.fixture(name="no_host_deletion_automation")
def fixture_no_host_deletion_automation(monkeypatch: pytest.MonkeyPatch) -> None:
    # The automation connects to the site of the host.
    monkeypatch.setattr(
        check_mk_automations,
        check_mk_automations.delete_hosts.__name__,
        lambda *_args, **_kwargs: DeleteHostsResult(),
    )


@pytest.mark.usefixtures(
    "with_admin_login", "mock_password_file_regeneration", "no_host_deletion_automation"
)
def test_deleting_the_bundle_deletes_the_additional_rules(
    bundle_tree: FolderTree, set_config: SetConfig
) -> None:
    # The host of the bundle can be deleted only on a site with replication.
    with set_config(sites=_sites_with_remote_site(replication="slave", secret="my_secret")):
        tree = QuickSetupContext.from_config(active_config, user).tree
        delete_config_bundle(
            tree,
            _BUNDLE_ID,
            acting_user=user,
            user_permissions=UserPermissions.from_config(active_config, all_permissions()),
            pprint_value=False,
            debug=False,
            pending_changes=PendingChanges(
                activation_sites=activation_sites(active_config.sites),
                local_site=omd_site(),
                acting_user=user.id,
                store=PendingChangesStore(),
                hooks=(),
            ),
        )

    assert not _additional_rules(bundle_tree)


@pytest.fixture(name="normal_user_login")
def fixture_normal_user_login(load_config: Config, with_user: tuple[UserId, str]) -> Iterator[None]:
    # A user who may edit all folders, but may not add executables.
    user_id = UserId(with_user[0])
    user_role = deepcopy(load_config.roles["user"])
    user_role["permissions"]["wato.all_folders"] = True
    roles = {**load_config.roles, "user": user_role}
    with login.TransactionIdContext(
        user_id, UserPermissions(roles, all_permissions(), {user_id: ["user"]}, [])
    ):
        yield


@pytest.mark.usefixtures("normal_user_login", "mock_password_file_regeneration")
def test_bundle_with_a_rule_the_user_may_not_create_is_not_created(set_config: SetConfig) -> None:
    with set_config(sites=_sites_with_remote_site(replication=None)):
        tree = QuickSetupContext.from_config(active_config, user).tree
        # Rules of this rule set need the permission "wato.add_or_modify_executables".
        with pytest.raises(MKAuthException, match="custom_checks"):
            complete.create_and_save_special_agent_bundle_custom_collect_params(
                special_agent_name="azure_v2",
                parameter_form=azure.formspec(),
                all_stages_form_data=_FORM_DATA,
                custom_collect_params=azure_collect_params,
                progress_logger=InfoLogger(),
                tree=tree,
                additional_rules=_additional_rules_of("custom_checks"),
            )

    assert _BUNDLE_ID not in load_configuration_bundles()
