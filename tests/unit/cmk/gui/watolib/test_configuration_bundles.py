#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterable

import pytest

from tests.unit.cmk.gui.watolib.test_watolib_password_store import (  # noqa: F401
    mock_update_passwords_merged_file,
)

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId

from cmk.utils.password_store import Password
from cmk.utils.rulesets.ruleset_matcher import RuleSpec

from cmk.automations.results import DeleteHostsResult

import cmk.gui.watolib.check_mk_automations
from cmk.gui.watolib.configuration_bundle_store import BundleId, ConfigBundle
from cmk.gui.watolib.configuration_bundles import (
    create_config_bundle,
    CreateBundleEntities,
    CreateHost,
    CreatePassword,
    CreateRule,
    delete_config_bundle,
    identify_single_bundle_references,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree, Host
from cmk.gui.watolib.passwords import load_passwords
from cmk.gui.watolib.rulesets import SingleRulesetRecursively

logger = logging.getLogger(__name__)


def _make_bundle(
    bundle_id: str = "test-bundle-id",
    group: str = "special_agents:aws",
    owned_by: str | None = "cmkadmin",
) -> tuple[BundleId, ConfigBundle]:
    bundle = ConfigBundle(
        title="", comment="", owned_by=owned_by, group=group, program_id="quick_setup"
    )
    return BundleId(bundle_id), bundle


@pytest.mark.usefixtures("request_context")
def test_create_config_bundle_empty(with_admin_login: UserId) -> None:
    bundle_id, bundle = _make_bundle()
    create_config_bundle(
        bundle_id,
        bundle,
        CreateBundleEntities(),
        user_id=with_admin_login,
        pprint_value=False,
        use_git=False,
        debug=False,
    )
    references = identify_single_bundle_references(bundle_id, bundle["group"])

    assert references.hosts is None
    assert references.rules is None
    assert references.passwords is None


@pytest.mark.usefixtures("request_context")
def test_create_config_bundle_duplicate_id(with_admin_login: UserId) -> None:
    bundle_id, bundle = _make_bundle()
    create_config_bundle(
        bundle_id,
        bundle,
        CreateBundleEntities(),
        user_id=with_admin_login,
        pprint_value=False,
        use_git=False,
        debug=False,
    )

    with pytest.raises(MKGeneralException, match="already exists"):
        create_config_bundle(
            bundle_id,
            bundle,
            CreateBundleEntities(),
            user_id=with_admin_login,
            pprint_value=False,
            use_git=False,
            debug=False,
        )


@pytest.mark.usefixtures("request_context")
def test_delete_config_bundle_empty(with_admin_login: UserId) -> None:
    bundle_id, bundle = _make_bundle()
    create_config_bundle(
        bundle_id,
        bundle,
        CreateBundleEntities(),
        user_id=with_admin_login,
        pprint_value=False,
        use_git=False,
        debug=False,
    )
    delete_config_bundle(
        bundle_id,
        user_id=with_admin_login,
        pprint_value=False,
        use_git=False,
        debug=False,
    )


def test_delete_config_bundle_unknown_id() -> None:
    with pytest.raises(MKGeneralException, match="does not exist"):
        delete_config_bundle(
            BundleId("unknown"),
            user_id=UserId("harry"),
            pprint_value=False,
            use_git=False,
            debug=False,
        )


@pytest.fixture(
    name="other_folder",
)
def fixture_other_folder(request_context: None, with_admin_login: UserId) -> str:
    path = "subfolder"
    folder_tree().create_missing_folders(path, pprint_value=False)
    return path


@pytest.fixture
def mock_delete_host_automation(monkeypatch: pytest.MonkeyPatch) -> Iterable[None]:
    monkeypatch.setattr(
        cmk.gui.watolib.check_mk_automations,
        cmk.gui.watolib.check_mk_automations.delete_hosts.__name__,
        lambda *args, **kwargs: DeleteHostsResult(),
    )
    yield


@pytest.mark.usefixtures("request_context", "mock_delete_host_automation")
def test_create_and_delete_config_bundle_hosts(other_folder: str, with_admin_login: UserId) -> None:
    bundle_id, bundle = _make_bundle()
    tree = folder_tree()
    hosts = [
        CreateHost(
            folder=tree.root_folder(),
            name=HostName("test-host-1"),
            attributes={},
        ),
        CreateHost(
            folder=tree.root_folder().create_subfolder(
                name=other_folder, title=other_folder, attributes={}, pprint_value=False
            ),
            name=HostName("test-host-2"),
            attributes={},
        ),
    ]
    before_create_host_count = len(Host.all())
    create_config_bundle(
        bundle_id,
        bundle,
        CreateBundleEntities(hosts=hosts),
        user_id=with_admin_login,
        pprint_value=False,
        use_git=False,
        debug=False,
    )

    references = identify_single_bundle_references(bundle_id, bundle["group"])

    assert references.hosts is not None
    assert len(references.hosts) == 2
    assert len(Host.all()) - before_create_host_count == 2

    delete_config_bundle(
        bundle_id,
        user_id=with_admin_login,
        pprint_value=False,
        use_git=False,
        debug=False,
    )
    references_after_delete = identify_single_bundle_references(bundle_id, bundle["group"])
    assert references_after_delete.hosts is None
    assert len(Host.all()) == before_create_host_count, "Expected created hosts to be deleted"


@pytest.mark.usefixtures("request_context", "mock_update_passwords_merged_file")
def test_create_and_delete_config_bundle_passwords(with_admin_login: UserId) -> None:
    bundle_id, bundle = _make_bundle()
    passwords = [
        CreatePassword(
            id="password-1",
            spec=Password(
                title="", comment="", docu_url="", password="123", owned_by=None, shared_with=[]
            ),
        ),
        CreatePassword(
            id="password-2",
            spec=Password(
                title="", comment="", docu_url="", password="123", owned_by=None, shared_with=[]
            ),
        ),
    ]
    before_create_password_count = len(load_passwords())
    create_config_bundle(
        bundle_id,
        bundle,
        CreateBundleEntities(passwords=passwords),
        user_id=with_admin_login,
        pprint_value=False,
        use_git=False,
        debug=False,
    )
    references = identify_single_bundle_references(bundle_id, bundle["group"])

    assert references.passwords is not None
    assert len(references.passwords) == 2
    assert len(load_passwords()) - before_create_password_count == 2

    delete_config_bundle(
        bundle_id,
        user_id=with_admin_login,
        pprint_value=False,
        use_git=False,
        debug=False,
    )
    references_after_delete = identify_single_bundle_references(bundle_id, bundle["group"])
    assert references_after_delete.passwords is None
    assert len(load_passwords()) == before_create_password_count, (
        "Expected created passwords to be deleted"
    )


@pytest.mark.usefixtures("request_context")
def test_create_and_delete_config_bundle_rules(other_folder: str, with_admin_login: UserId) -> None:
    bundle_id, bundle = _make_bundle()
    ruleset_name = "checkgroup_parameters:local"
    rules = [
        CreateRule(
            folder="",
            ruleset=ruleset_name,
            spec=RuleSpec[object](
                id="rule-1",
                value="VAL1",
                condition={},
            ),
        ),
        CreateRule(
            folder=other_folder,
            ruleset=ruleset_name,
            spec=RuleSpec[object](
                id="rule-2",
                value="VAL2",
                condition={},
            ),
        ),
    ]

    def _len_rules() -> int:
        return len(
            SingleRulesetRecursively.load_single_ruleset_recursively(ruleset_name)
            .get(ruleset_name)
            .get_rules()
        )

    before_create_rules_count = _len_rules()
    create_config_bundle(
        bundle_id,
        bundle,
        CreateBundleEntities(rules=rules),
        user_id=with_admin_login,
        pprint_value=False,
        use_git=False,
        debug=False,
    )
    references = identify_single_bundle_references(bundle_id, bundle["group"])

    assert references.rules is not None
    assert len(references.rules) == 2
    assert _len_rules() - before_create_rules_count == 2

    delete_config_bundle(
        bundle_id,
        user_id=with_admin_login,
        pprint_value=False,
        use_git=False,
        debug=False,
    )
    references_after_delete = identify_single_bundle_references(bundle_id, bundle["group"])

    assert references_after_delete.rules is None
    assert _len_rules() == before_create_rules_count, "Expected created rules to be deleted"
