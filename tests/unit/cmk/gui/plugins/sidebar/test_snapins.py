#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.utils.version as cmk_version

from cmk.gui.plugins.sidebar.utils import snapin_registry

pytestmark = pytest.mark.usefixtures("load_plugins")


def test_registered_snapins():
    expected_snapins = [
        'about',
        'admin',
        'admin_mini',
        'biaggr_groups',
        'biaggr_groups_tree',
        'bookmarks',
        'custom_links',
        'dashboards',
        'hostgroups',
        'hostmatrix',
        'hosts',
        'master_control',
        'mkeventd_performance',
        'nagios_legacy',
        'nagvis_maps',
        'performance',
        'problem_hosts',
        'search',
        'servicegroups',
        'sitestatus',
        'speedometer',
        'tactical_overview',
        'tag_tree',
        'time',
        'views',
        'wato_folders',
        'wato_foldertree',
    ]

    if not cmk_version.is_raw_edition():
        expected_snapins += [
            'cmc_stats',
            'reports',
        ]

    if cmk_version.is_managed_edition():
        expected_snapins += [
            "customers",
        ]

    assert sorted(snapin_registry.keys()) == sorted(expected_snapins)


def test_refresh_snapins():
    expected_refresh_snapins = [
        'admin',
        'admin_mini',
        'performance',
        'hostmatrix',
        'mkeventd_performance',
        'problem_hosts',
        'sitestatus',
        'tactical_overview',
        'tag_tree',
        'time',
    ]

    if not cmk_version.is_raw_edition():
        expected_refresh_snapins += [
            'cmc_stats',
        ]

    refresh_snapins = [s.type_name() for s in snapin_registry.values() if s.refresh_regularly()]
    assert sorted(refresh_snapins) == sorted(expected_refresh_snapins)
