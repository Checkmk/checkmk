import pytest

# Following import is used to trigger pluggin loading
import cmk.gui.wato  # pylint: disable=unused-import
import cmk.gui.plugins.wato.utils.main_menu as main_menu


def test_registered_modules():
    module_names = [m.mode_or_url for m in main_menu.get_modules()]
    assert module_names == [
        'dcd_connections',
        'agents',
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
        'alert_handlers',
        'analyze_config',
        'background_jobs_overview',
        'mkps',
        'pattern_editor',
        'icons',
    ]


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
