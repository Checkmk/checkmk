#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Where the GUI-only "Relations" host attribute is checked.

The shapes a stored value may take are pinned by the shared form-spec cases (see
tests/testlib/unit/gui/host_attributes_test_helper.py); what a value means for the host carrying
it is checked where that host is known (see tests/unit/cmk/gui/watolib/test_hosts_and_folders.py).
"""

import json

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.utils.host_relations import RelationLink
from cmk.gui.watolib.builtin_attributes import HostAttributeRelations
from cmk.gui.watolib.form_spec_generators import create_host_attributes_selection
from cmk.gui.watolib.host_attributes import (
    collect_attributes,
    host_attribute_registry,
    HostAttributes,
)
from cmk.rulesets.internal.form_specs import CascadingSingleChoiceExtended
from tests.unit.cmk.gui.helpers.host_attributes_test_helper import submitted_relation_row


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "link",
    [
        pytest.param({"kind": "peering", "direction": "symmetric", "host": "board"}, id="kind"),
        pytest.param(
            {"kind": "management", "direction": "sideways", "host": "board"}, id="direction"
        ),
        pytest.param(
            {"kind": "management", "direction": "symmetric", "host": "board"},
            id="end the kind does not have",
        ),
    ],
)
def test_validate_input_accepts_a_relation_it_does_not_know(link: object) -> None:
    """A row a later version wrote: dropped wherever the value is read, so refusing the save here
    would leave the host unsavable after a downgrade."""
    HostAttributeRelations().validate_input([link], "attr_")


@pytest.mark.usefixtures("request_context")
def test_validate_input_does_not_care_which_host_it_is_about() -> None:
    """The attribute never sees the host; relation_conflicts() checks where the owner is known."""
    HostAttributeRelations().validate_input(
        [{"kind": "management", "direction": "parent", "host": HostName("srv1")}], "attr_"
    )


@pytest.mark.usefixtures("request_context")
def test_a_row_without_a_host_is_reported_at_the_field() -> None:
    """collect_attributes() reads the form before it validates it, so the refusal has to come out
    of from_html_vars() as a user error - otherwise the save ends in a crash report."""
    request.set_var("relations", json.dumps([submitted_relation_row("management", "child", "")]))

    with pytest.raises(MKUserError, match="Select the host this relation points to"):
        HostAttributeRelations().from_html_vars("")


@pytest.mark.usefixtures("request_context")
def test_a_saved_host_keeps_a_relation_of_a_kind_the_dialog_cannot_show() -> None:
    """The dialog has no row for a kind of a later version, so the user cannot have removed it -
    and it must not take the other half on the related host with it."""
    attribute = HostAttributeRelations()
    later: RelationLink = {"kind": "peering", "direction": "symmetric", "host": HostName("peer")}
    request.set_var("host_change_relations", "1")
    request.set_var(
        "relations", json.dumps([submitted_relation_row("management", "child", "board")])
    )

    attributes = collect_attributes(
        {attribute.name(): attribute},
        for_what="host",
        new=False,
        stored=HostAttributes({"relations": [later]}),
    )

    assert attributes["relations"] == [
        {"kind": "management", "direction": "child", "host": "board"},
        later,
    ]


@pytest.mark.usefixtures("request_context")
def test_a_saved_host_drops_a_relation_whose_kind_does_not_have_that_end() -> None:
    """Unlike a kind of a later version, nothing will ever place it, and only the save can get
    rid of it: the dialog has no row for it and the export skips it."""
    attribute = HostAttributeRelations()
    request.set_var("host_change_relations", "1")
    request.set_var(
        "relations", json.dumps([submitted_relation_row("management", "child", "board")])
    )

    attributes = collect_attributes(
        {attribute.name(): attribute},
        for_what="host",
        new=False,
        stored=HostAttributes(
            {
                "relations": [
                    {"kind": "management", "direction": "symmetric", "host": HostName("board")}
                ]
            }
        ),
    )

    assert attributes["relations"] == [
        {"kind": "management", "direction": "child", "host": "board"}
    ]


def test_relations_attribute_is_described_by_its_form_spec() -> None:
    attribute = HostAttributeRelations()
    assert attribute.title() == "Relations"
    assert "management board" in str(attribute.help())
    assert "stored on both" in str(attribute.help())
    assert attribute.default_value() == []


def test_relations_are_offered_on_a_host_but_not_in_a_bulk_edit() -> None:
    attribute = HostAttributeRelations()
    assert attribute.is_visible("host", new=False) is True
    assert attribute.is_visible("bulk", new=False) is False


def test_every_other_attribute_keeps_its_checkbox() -> None:
    always_active = {
        name
        for name, attribute in host_attribute_registry.items()
        if attribute().is_always_active()
    }
    assert always_active == {"relations"}


@pytest.mark.usefixtures("request_context", "load_config")
def test_relations_are_not_offered_where_attributes_are_set_through_the_rest_api() -> None:
    """The DCD connections and the agent registration rules apply what is selected here through
    the REST API, which refuses an attribute it does not expose."""
    assert HostAttributeRelations().openapi_editable() is False
    assert "relations" not in _attribute_names_offered_for_setting()


def _attribute_names_offered_for_setting() -> set[str]:
    selection = create_host_attributes_selection(default_host_attributes=None)
    element_template = selection.element_template
    assert isinstance(element_template, CascadingSingleChoiceExtended)
    assert not callable(element_template.elements)
    return {element.name for element in element_template.elements}
