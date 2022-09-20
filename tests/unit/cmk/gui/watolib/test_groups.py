#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Tuple

import pytest

import cmk.utils.paths

from cmk.ec.export import ECRulePack

import cmk.gui.groups as gui_groups
import cmk.gui.watolib.groups as groups
from cmk.gui.utils.script_helpers import application_and_request_context


@pytest.fixture(autouse=True)
def patch_config_paths(monkeypatch, tmp_path):
    cmk_confd = tmp_path / "check_mk" / "conf.d"
    monkeypatch.setattr(cmk.utils.paths, "check_mk_config_dir", str(cmk_confd))
    (cmk_confd / "wato").mkdir(parents=True)

    gui_confd = tmp_path / "check_mk" / "multisite.d"
    monkeypatch.setattr(cmk.utils.paths, "default_config_dir", str(gui_confd.parent))
    (gui_confd / "wato").mkdir(parents=True)


def test_load_group_information_empty(tmp_path, run_as_superuser):
    with application_and_request_context(), run_as_superuser():
        assert groups.load_contact_group_information() == {}
        assert gui_groups.load_host_group_information() == {}
        assert gui_groups.load_service_group_information() == {}


def test_load_group_information(tmp_path, run_as_superuser):
    with open(cmk.utils.paths.check_mk_config_dir + "/wato/groups.mk", "w") as f:
        f.write(
            """# encoding: utf-8

define_contactgroups.update({'all': u'Everything'})
define_hostgroups.update({'all_hosts': u'All hosts :-)'})
define_servicegroups.update({'all_services': u'All särvices'})
"""
        )

    with open(cmk.utils.paths.default_config_dir + "/multisite.d/wato/groups.mk", "w") as f:
        f.write(
            """# encoding: utf-8

multisite_hostgroups = {
    "all_hosts": {
        "ding": "dong",
    },
}

multisite_servicegroups = {
    "all_services": {
        "d1ng": "dong",
    },
}

multisite_contactgroups = {
    "all": {
        "d!ng": "dong",
    },
}
"""
        )

    with application_and_request_context(), run_as_superuser():
        assert groups.load_group_information() == {
            "contact": {
                "all": {
                    "alias": "Everything",
                    "d!ng": "dong",
                }
            },
            "host": {
                "all_hosts": {
                    "alias": "All hosts :-)",
                    "ding": "dong",
                }
            },
            "service": {
                "all_services": {
                    "alias": "All s\xe4rvices",
                    "d1ng": "dong",
                }
            },
        }

        assert groups.load_contact_group_information() == {
            "all": {
                "alias": "Everything",
                "d!ng": "dong",
            }
        }

        assert gui_groups.load_host_group_information() == {
            "all_hosts": {
                "alias": "All hosts :-)",
                "ding": "dong",
            }
        }

        assert gui_groups.load_service_group_information() == {
            "all_services": {
                "alias": "All s\xe4rvices",
                "d1ng": "dong",
            }
        }


def _rule_packs() -> list[ECRulePack]:
    return [
        {
            "id": "default",
            "title": "Default rule pack",
            "rules": [
                {
                    "id": "test2",
                    "contact_groups": {
                        "groups": ["my_contact_group"],
                        "notify": True,
                        "precedence": "host",
                    },
                },
                {
                    "id": "test4",
                    "contact_groups": {"groups": ["all"], "notify": True, "precedence": "host"},
                },
                {
                    "id": "test1",
                    "contact_groups": {
                        "groups": ["my_contact_group"],
                        "notify": True,
                        "precedence": "host",
                    },
                },
                {
                    "id": "test",
                    "contact_groups": {
                        "groups": ["my_contact_group"],
                        "notify": True,
                        "precedence": "host",
                    },
                },
            ],
        }
    ]


@pytest.mark.parametrize(
    "contact_group, rule_packs, expected_result",
    [
        pytest.param(
            "my_contact_group",
            _rule_packs,
            [
                (
                    "Event console rule: test2",
                    "wato.py?edit=0&folder=&mode=mkeventd_edit_rule&rule_pack=default",
                ),
                (
                    "Event console rule: test1",
                    "wato.py?edit=2&folder=&mode=mkeventd_edit_rule&rule_pack=default",
                ),
                (
                    "Event console rule: test",
                    "wato.py?edit=3&folder=&mode=mkeventd_edit_rule&rule_pack=default",
                ),
            ],
            id="existing contact group, should match",
        ),
        pytest.param(
            "bielefeld",
            _rule_packs,
            [],
            id="none existing contact group",
        ),
    ],
)
def test_find_usages_of_contact_group_in_ec_rules(
    request_context,
    monkeypatch,
    contact_group: str,
    rule_packs: list[ECRulePack],
    expected_result: List[Tuple[str, str]],
) -> None:
    monkeypatch.setattr(cmk.gui.watolib.mkeventd, "load_mkeventd_rules", rule_packs)
    assert (
        groups._find_usages_of_contact_group_in_ec_rules(contact_group)
        == expected_result  # pylint: disable=protected-access
    )
