#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence

import pytest

from cmk.ccc.site import omd_site
from cmk.gui.config import active_config
from cmk.gui.form_specs import DEFAULT_VALUE, get_visitor, RawDiskData, VisitorOptions
from cmk.gui.logged_in import user
from cmk.gui.quick_setup.config_setups.aws_v2.stages import (
    action,
    collect_params,
    configure_host_and_regions,
    quick_setup_aws_v2,
    quick_setup_formspec,
)
from cmk.gui.quick_setup.handlers.utils import InfoLogger
from cmk.gui.quick_setup.v0_unstable.definitions import (
    QSHostName,
    QSHostPath,
    QSSiteSelection,
    UniqueBundleIDStr,
    UniqueFormSpecIDStr,
)
from cmk.gui.quick_setup.v0_unstable.predefined import build_formspec_map_from_stages
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetupActionMode, QuickSetupContext
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import Collapsible, FormSpecId, FormSpecWrapper, Widget
from cmk.gui.watolib.passwords import load_passwords
from cmk.gui.watolib.rulesets import FolderRulesets
from cmk.plugins.aws_v2.rulesets import aws
from cmk.rulesets.v1.form_specs import DictElement, Dictionary
from tests.testlib.unit.gui.web_test_app import SetConfig

_PASSWORD_ID = "uuid0f2d5b58-1d9e-4ba5-9a5e-1d0c3e1b9a77"
_SECRET = ("cmk_postprocessed", "explicit_password", (_PASSWORD_ID, "my_secret_access_key"))

_FORM_DATA: ParsedFormData = {
    FormSpecId(UniqueFormSpecIDStr): {UniqueBundleIDStr: "my_aws_account"},
    FormSpecId("credentials"): {"access_key_id": "my_access_key", "secret_access_key": _SECRET},
    FormSpecId("host_data"): {QSHostName: "aws_host", QSHostPath: "aws_folder"},
    FormSpecId("configure_regions"): {"regions": ["eu_central_1"]},
    FormSpecId("configure_services_to_monitor"): {
        "global_services": {"ce": ("all", {})},
        "regional_services": {"ec2": ("all", {"limits": True})},
    },
}

# These widgets are part of every Quick Setup, they do not configure the rule.
_GENERIC_FORMS = {FormSpecId(UniqueFormSpecIDStr), FormSpecId("host_data"), FormSpecId("site")}

_SIX_REGIONS = ["eu_central_1", "eu_north_1", "eu_west_1", "eu_west_2", "eu_west_3", "us_east_1"]


def _form_specs(widgets: Sequence[Widget]) -> Iterator[FormSpecWrapper]:
    for widget in widgets:
        if isinstance(widget, FormSpecWrapper):
            yield widget
        elif isinstance(widget, Collapsible):
            yield from _form_specs(widget.items)


def _schemas(elements: Mapping[str, DictElement[object]]) -> Mapping[str, object]:
    # Form specs do not compare by value, the schemas the GUI renders from them do.
    options = VisitorOptions(migrate_values=False, mask_values=False)
    return {
        name: get_visitor(Dictionary(elements={name: element}), options).to_vue(DEFAULT_VALUE)[0]
        for name, element in elements.items()
    }


def _ctx() -> QuickSetupContext:
    return QuickSetupContext.from_config(active_config, user)


def _stage_widgets() -> Iterator[Widget]:
    for stage in quick_setup_aws_v2.stages:
        components = stage().configure_components
        yield from components(_ctx()) if callable(components) else components


@pytest.mark.usefixtures("with_admin_login")
def test_quick_setup_offers_the_fields_of_the_rule_with_the_access_key_as_authentication() -> None:
    offered_fields = {
        name: element
        for wrapper in _form_specs(list(_stage_widgets()))
        if wrapper.id not in _GENERIC_FORMS and isinstance(form := wrapper.form_spec, Dictionary)
        for name, element in form.elements.items()
        if name != "regions"
    }

    assert _schemas(offered_fields) == _schemas(
        {
            **{
                name: element
                for name, element in aws.formspec().elements.items()
                if name not in {"auth", "regions"}
            },
            **aws.configuration_access_key(),
        }
    )


@pytest.mark.parametrize(
    "regions, expected_errors",
    [
        pytest.param(_SIX_REGIONS[:5], [], id="five regions"),
        pytest.param(_SIX_REGIONS, ["Please select at most 5 regions."], id="six regions"),
    ],
)
@pytest.mark.usefixtures("with_admin_login")
def test_quick_setup_limits_the_regions_to_five(
    regions: Sequence[str], expected_errors: Sequence[str]
) -> None:
    form = build_formspec_map_from_stages([configure_host_and_regions()], _ctx())[
        FormSpecId("configure_regions")
    ]

    errors = get_visitor(form, VisitorOptions(migrate_values=False, mask_values=False)).validate(
        RawDiskData({"regions": regions})
    )

    assert [error.message for error in errors] == expected_errors


@pytest.mark.usefixtures("with_admin_login")
def test_access_key_becomes_the_authentication_of_the_rule() -> None:
    rule_value = collect_params(_FORM_DATA, quick_setup_formspec())

    assert rule_value["auth"] == (
        "access_key",
        {
            "access_key_id": "my_access_key",
            "secret_access_key": _SECRET,
            "accounts": ("single", None),
        },
    )


@pytest.mark.usefixtures("with_admin_login")
def test_quick_setup_creates_a_valid_rule_value() -> None:
    rule_value = collect_params(_FORM_DATA, quick_setup_formspec())

    errors = get_visitor(
        aws.formspec(), VisitorOptions(migrate_values=False, mask_values=False)
    ).validate(RawDiskData(rule_value))

    assert not errors


@pytest.mark.usefixtures("with_admin_login", "mock_password_file_regeneration")
def test_saved_rule_refers_to_the_stored_password(set_config: SetConfig) -> None:
    # The Quick Setup skips the service discovery for a remote site without replication.
    remote_site = {
        **active_config.sites[omd_site()],
        "id": "remote",
        "socket": ("tcp", {}),
        "replication": None,
    }
    form_data = {**_FORM_DATA, FormSpecId("site"): {QSSiteSelection: "remote"}}
    with set_config(sites={**active_config.sites, "remote": remote_site}):
        ctx = _ctx()

        action(form_data, QuickSetupActionMode.SAVE, InfoLogger(), None, ctx)

    folder = ctx.tree.root_folder().subfolder("aws_folder")
    assert folder is not None
    ((_folder, _index, rule),) = (
        FolderRulesets.load_folder_rulesets(folder).get("special_agents:aws_v2").get_rules()
    )
    assert (
        rule.value["auth"][1]["secret_access_key"],
        load_passwords(user)[_PASSWORD_ID]["password"],
    ) == (("cmk_postprocessed", "stored_password", (_PASSWORD_ID, "")), "my_secret_access_key")
