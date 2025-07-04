from collections.abc import Mapping
from typing import Any

import pytest

from cmk.plugins.collection.rulesets.diskstat import _form_spec_diskstat_inventory
from cmk.rulesets.v1.form_specs import Dictionary


@pytest.mark.parametrize(
    "value, expected_output",
    [
        pytest.param(
            {},
            {
                "summary": True,
                "physical": "name",
                "lvm": False,
                "diskless": False,
                "vxvm": False,
            },
            id="migrate-empty-dict",
        ),
        pytest.param(
            {
                "summary": True,
                "physical": {"service_description": "name"},
                "lvm": True,
                "diskless": False,
                "vxvm": False,
            },
            {
                "summary": True,
                "physical": "name",
                "lvm": True,
                "diskless": False,
                "vxvm": False,
            },
            id="migrate-service-description",
        ),
        pytest.param(
            {
                "summary": True,
                "physical": True,
                "lvm": "bad_value",
                "diskless": False,
                "vxvm": False,
            },
            {
                "summary": True,
                "physical": "name",
                "lvm": "bad_value",
                "diskless": False,
                "vxvm": False,
            },
            id="migrate-bad-value",
        ),
    ],
)
def test_diskstat_inventory_migration(value: Mapping[str, object], expected_output: dict) -> None:
    def migrate(form_spec: Dictionary, key: str, mig_value: Any) -> Any:
        # migrate the fields first
        try:
            form_element = form_spec.elements[key]
            if migrate := form_element.parameter_form.migrate:
                return migrate(mig_value)
            return mig_value
        except KeyError:
            return mig_value

    form_spec = _form_spec_diskstat_inventory()
    if callable(form_spec.migrate):
        value = form_spec.migrate(value)

    assert {
        key: migrate(form_spec, key, value.get(key)) for key in form_spec.elements
    } == expected_output


@pytest.mark.parametrize(
    "value, expected_output",
    [
        pytest.param(
            {
                "summary": True,
                "physical": "name",
                "lvm": True,
                "add-key": "add-value",
                "diskless": False,
                "vxvm": False,
            },
            {
                "summary": True,
                "physical": "name",
                "lvm": True,
                "add-key": "add-value",
                "diskless": False,
                "vxvm": False,
            },
            id="migrate-additional-key",
        ),
        pytest.param(
            {
                "somekey": {"otherkey": "value"},
                "anotherkey": "bad_value",
                "nokey": True,
            },
            {
                "somekey": {"otherkey": "value"},
                "anotherkey": "bad_value",
                "nokey": True,
                "physical": "name",
                "summary": False,
                "lvm": False,
                "diskless": False,
                "vxvm": False,
            },
            id="migrate-nonsense",
        ),
    ],
)
@pytest.mark.skip()
def test_diskstat_inventory_migration_error(value: dict, expected_output: dict) -> None:
    with pytest.raises(TypeError):
        pass
        # migrate_diskstat_inventory(value)
