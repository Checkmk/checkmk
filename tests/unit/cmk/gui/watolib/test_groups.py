# encoding: utf-8

import pytest

import cmk.utils.paths
import cmk.gui.watolib.groups as groups


@pytest.fixture(autouse=True)
def patch_config_paths(monkeypatch, tmp_path):
    cmk_confd = tmp_path / "check_mk" / "conf.d"
    monkeypatch.setattr(cmk.utils.paths, "check_mk_config_dir", str(cmk_confd))
    (cmk_confd / "wato").mkdir(parents=True)

    gui_confd = tmp_path / "check_mk" / "multisite.d"
    monkeypatch.setattr(cmk.utils.paths, "default_config_dir", str(gui_confd.parent))
    (gui_confd / "wato").mkdir(parents=True)


def test_load_group_information_empty(tmp_path):
    assert groups.load_group_information() == {'contact': {}, 'host': {}, 'service': {}}


def test_load_group_information(tmp_path):
    with open(cmk.utils.paths.check_mk_config_dir + "/wato/groups.mk", "w") as f:
        f.write("""# encoding: utf-8

if type(define_contactgroups) != dict:
    define_contactgroups = {}
define_contactgroups.update({'all': u'Everything'})

if type(define_hostgroups) != dict:
    define_hostgroups = {}
define_hostgroups.update({'all_hosts': u'All hosts :-)'})

if type(define_servicegroups) != dict:
    define_servicegroups = {}
define_servicegroups.update({'all_services': u'All särvices'})
""")

    with open(cmk.utils.paths.default_config_dir + "/multisite.d/wato/groups.mk", "w") as f:
        f.write("""# encoding: utf-8

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
""")

    assert groups.load_group_information() == {
        'contact': {
            'all': {
                'alias': u'Everything',
                "d!ng": "dong",
            }
        },
        'host': {
            'all_hosts': {
                'alias': u'All hosts :-)',
                "ding": "dong",
            }
        },
        'service': {
            'all_services': {
                'alias': u'All s\xe4rvices',
                "d1ng": "dong",
            }
        },
    }
