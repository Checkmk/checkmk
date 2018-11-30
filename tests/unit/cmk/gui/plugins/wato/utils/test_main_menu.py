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
        'hosttags',
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


@pytest.mark.parametrize("mode_or_url,attributes", [
    ('folder', {
        'description': u"Manage monitored hosts and services and the hosts' folder structure.",
        'permission': 'hosts',
        'title': u'Hosts',
        'sort_index': 10,
        'mode_or_url': 'folder',
        'icon': 'folder'
    }),
    ('hosttags', {
        'description': u'Tags classify hosts and are the fundament of configuration of hosts and services.',
        'permission': 'hosttags',
        'title': u'Host Tags',
        'sort_index': 15,
        'mode_or_url': 'hosttags',
        'icon': 'hosttag'
    }),
    ('globalvars', {
        'description': u'Global settings for Check_MK, Multisite and the monitoring core.',
        'permission': 'global',
        'title': u'Global Settings',
        'sort_index': 20,
        'mode_or_url': 'globalvars',
        'icon': 'configuration'
    }),
    ('ruleeditor', {
        'description': u'Check parameters and other configuration variables on hosts and services',
        'permission': 'rulesets',
        'title': u'Host & Service Parameters',
        'sort_index': 25,
        'mode_or_url': 'ruleeditor',
        'icon': 'rulesets'
    }),
    ('static_checks', {
        'description': u'Configure fixed checks without using service discovery',
        'permission': 'rulesets',
        'title': u'Manual Checks',
        'sort_index': 30,
        'mode_or_url': 'static_checks',
        'icon': 'static_checks'
    }),
    ('check_plugins', {
        'description': u'Browse the catalog of all check plugins, create static checks',
        'permission': None,
        'title': u'Check Plugins',
        'sort_index': 35,
        'mode_or_url': 'check_plugins',
        'icon': 'check_plugins'
    }),
    ('host_groups', {
        'description': u'Organize your hosts and services in groups independent of the tree structure.',
        'permission': 'groups',
        'title': u'Host & Service Groups',
        'sort_index': 40,
        'mode_or_url': 'host_groups',
        'icon': 'hostgroups'
    }),
    ('users', {
        'description': u'Manage users of the monitoring system.',
        'permission': 'users',
        'title': u'Users',
        'sort_index': 45,
        'mode_or_url': 'users',
        'icon': 'users'
    }),
    ('roles', {
        'description': u'User roles are configurable sets of permissions.',
        'permission': 'users',
        'title': u'Roles & Permissions',
        'sort_index': 50,
        'mode_or_url': 'roles',
        'icon': 'roles'
    }),
    ('contact_groups', {
        'description': u'Contact groups are used to assign persons to hosts and services',
        'permission': 'users',
        'title': u'Contact Groups',
        'sort_index': 55,
        'mode_or_url': 'contact_groups',
        'icon': 'contactgroups'
    }),
    ('notifications', {
        'description': u'Rules for the notification of contacts about host and service problems',
        'permission': 'notifications',
        'title': u'Notifications',
        'sort_index': 60,
        'mode_or_url': 'notifications',
        'icon': 'notifications'
    }),
    ('timeperiods', {
        'description': u'Timeperiods restrict notifications and other things to certain periods of the day.',
        'permission': 'timeperiods',
        'title': u'Time Periods',
        'sort_index': 65,
        'mode_or_url': 'timeperiods',
        'icon': 'timeperiods'
    }),
    ('bi_packs', {
        'description': u"Configuration of Check_MK's Business Intelligence component.",
        'permission': 'bi_rules',
        'title': u'Business Intelligence',
        'sort_index': 70,
        'mode_or_url': 'bi_packs',
        'icon': 'aggr'
    }),
    ('sites', {
        'description': u"Distributed monitoring using multiple Check_MK sites",
        'permission': 'sites',
        'title': u'Distributed Monitoring',
        'sort_index': 75,
        'mode_or_url': 'sites',
        'icon': 'sites'
    }),
    ('backup', {
        'description': u'Make backups of your whole site and restore previous backups.',
        'permission': 'backups',
        'title': u'Backup',
        'sort_index': 80,
        'mode_or_url': 'backup',
        'icon': 'backup'
    }),
    ('passwords', {
        'description': u'Store and share passwords for later use in checks.',
        'permission': 'passwords',
        'title': u'Passwords',
        'sort_index': 85,
        'mode_or_url': 'passwords',
        'icon': 'passwords'
    }),
    ('analyze_config', {
        'description': u'See hints how to improve your Check_MK installation',
        'permission': 'analyze_config',
        'title': u'Analyze configuration',
        'sort_index': 90,
        'mode_or_url': 'analyze_config',
        'icon': 'analyze_config'
    }),
    ('background_jobs_overview', {
        'description': u'Manage longer running tasks in the Check_MK GUI',
        'permission': 'background_jobs.manage_jobs',
        'title': u'Background jobs',
        'sort_index': 90,
        'mode_or_url': 'background_jobs_overview',
        'icon': 'background_jobs'
    }),
    ('pattern_editor', {
        'description': u'Analyze logfile pattern rules and validate logfile patterns against custom text.',
        'permission': 'pattern_editor',
        'title': u'Logfile Pattern Analyzer',
        'sort_index': 95,
        'mode_or_url': 'pattern_editor',
        'icon': 'analyze'
    }),
    ('icons', {
        'description': u'Upload your own icons that can be used in views or custom actions',
        'permission': 'icons',
        'title': u'Custom Icons',
        'sort_index': 100,
        'mode_or_url': 'icons',
        'icon': 'icons'
    })
])
def test_module_attributes(mode_or_url, attributes):
    for m in main_menu.get_modules():
        if m.mode_or_url == mode_or_url:
            for key, value in attributes.items():
                assert getattr(m, key) == value


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
