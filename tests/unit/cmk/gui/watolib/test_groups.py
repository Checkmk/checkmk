#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.utils.paths

from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import application_and_request_context
from cmk.gui.watolib import groups_io
from cmk.gui.watolib.groups import contact_group_usage_finder_registry


@pytest.fixture(autouse=True)
def patch_config_paths(monkeypatch, tmp_path):
    cmk_confd = tmp_path / "check_mk" / "conf.d"
    monkeypatch.setattr(cmk.utils.paths, "check_mk_config_dir", cmk_confd)
    (cmk_confd / "wato").mkdir(parents=True)

    gui_confd = tmp_path / "check_mk" / "multisite.d"
    monkeypatch.setattr(cmk.utils.paths, "default_config_dir", gui_confd.parent)
    (gui_confd / "wato").mkdir(parents=True)


@pytest.mark.usefixtures("tmp_path")
def test_load_group_information_empty() -> None:
    with application_and_request_context(), SuperUserContext():
        assert groups_io.load_contact_group_information() == {}
        assert groups_io.load_host_group_information() == {}
        assert groups_io.load_service_group_information() == {}


@pytest.mark.usefixtures("tmp_path")
def test_load_group_information() -> None:
    with open(cmk.utils.paths.check_mk_config_dir / "wato/groups.mk", "w") as f:
        f.write(
            """# encoding: utf-8

define_hostgroups.update({'all_hosts': u'All hosts :-)'})
define_servicegroups.update({'all_services': u'All särvices'})
define_contactgroups.update({'all': u'Everything'})
"""
        )

    with open(cmk.utils.paths.default_config_dir / "multisite.d/wato/groups.mk", "w") as f:
        f.write(
            """# encoding: utf-8

multisite_hostgroups = {
    "all_hosts": {
        "customer": "foo",
    },
}

multisite_servicegroups = {
    "all_services": {
        "unknown": "field",
    },
}

multisite_contactgroups = {
    "all": {
        "inventory_paths": "allow_all",
    },
}
"""
        )

    with application_and_request_context(), SuperUserContext():
        assert groups_io.load_group_information() == {
            "host": {
                "all_hosts": {
                    "alias": "All hosts :-)",
                    "customer": "foo",
                }
            },
            "service": {
                "all_services": {
                    "alias": "All s\xe4rvices",
                    "unknown": "field",
                }
            },
            "contact": {
                "all": {
                    "alias": "Everything",
                    "inventory_paths": "allow_all",
                }
            },
        }

        assert groups_io.load_host_group_information() == {
            "all_hosts": {
                "alias": "All hosts :-)",
                "customer": "foo",
            }
        }

        assert groups_io.load_service_group_information() == {
            "all_services": {
                "alias": "All s\xe4rvices",
                "unknown": "field",
            }
        }

        assert groups_io.load_contact_group_information() == {
            "all": {
                "alias": "Everything",
                "inventory_paths": "allow_all",
            }
        }


def test_group_usage_finder_registry_entries() -> None:
    expected = [
        "find_usages_of_contact_group_in_dashboards",
        "find_usages_of_contact_group_in_default_user_profile",
        "find_usages_of_contact_group_in_ec_rules",
        "find_usages_of_contact_group_in_hosts_and_folders",
        "find_usages_of_contact_group_in_mkeventd_notify_contactgroup",
        "find_usages_of_contact_group_in_notification_rules",
        "find_usages_of_contact_group_in_users",
    ]

    registered = [f.__name__ for f in contact_group_usage_finder_registry.values()]
    assert sorted(registered) == sorted(expected)
