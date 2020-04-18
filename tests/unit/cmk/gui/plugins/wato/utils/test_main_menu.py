#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.version as cmk_version

# Following import is used to trigger plugin loading
import cmk.gui.wato  # pylint: disable=unused-import
import cmk.gui.plugins.wato.utils.main_menu as main_menu


def test_registered_modules():
    expected_modules = [
        'folder',
        'tags',
        'globalvars',
        'ruleeditor',
        'static_checks',
        'check_plugins',
        'host_groups',
        'users',
        'roles',
        'contact_groups',
        'notifications',
        'timeperiods',
        'mkeventd_rule_packs',
        'bi_packs',
        'sites',
        'backup',
        'passwords',
        'analyze_config',
        'background_jobs_overview',
        'pattern_editor',
        'icons',
        'diagnostics',
    ]

    if cmk_version.is_raw_edition():
        expected_modules += [
            'download_agents',
        ]

    if not cmk_version.is_raw_edition():
        expected_modules += [
            'agents',
            'alert_handlers',
            'mkps',
        ]

    module_names = [m.mode_or_url for m in main_menu.get_modules()]
    assert sorted(module_names) == sorted(expected_modules)


def test_register_module(monkeypatch):
    monkeypatch.setattr(main_menu, "main_module_registry", main_menu.ModuleRegistry())
    module = main_menu.WatoModule(
        mode_or_url="dang",
        description='descr',
        permission='icons',
        title='Custom DING',
        sort_index=100,
        icon='icons',
    )
    main_menu.register_modules(module)

    modules = main_menu.get_modules()
    assert len(modules) == 1
    registered = modules[0]
    assert isinstance(registered, main_menu.MainModule)
    assert registered.mode_or_url == "dang"
    assert registered.description == 'descr'
    assert registered.permission == 'icons'
    assert registered.title == 'Custom DING'
    assert registered.sort_index == 100
    assert registered.icon == 'icons'
