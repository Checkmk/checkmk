#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from werkzeug.test import create_environ

import cmk.utils.paths
import cmk.gui.watolib.groups as groups
import cmk.gui.htmllib as htmllib
from cmk.gui.http import Request
from cmk.gui.globals import AppContext, RequestContext
from testlib.utils import DummyApplication


@pytest.fixture(autouse=True)
def patch_config_paths(monkeypatch, tmp_path):
    cmk_confd = tmp_path / "check_mk" / "conf.d"
    monkeypatch.setattr(cmk.utils.paths, "check_mk_config_dir", str(cmk_confd))
    (cmk_confd / "wato").mkdir(parents=True)

    gui_confd = tmp_path / "check_mk" / "multisite.d"
    monkeypatch.setattr(cmk.utils.paths, "default_config_dir", str(gui_confd.parent))
    (gui_confd / "wato").mkdir(parents=True)


def test_load_group_information_empty(tmp_path):
    environ = dict(create_environ(), REQUEST_URI='')
    with AppContext(DummyApplication(environ, None)), \
         RequestContext(htmllib.html(Request(environ))):
        assert groups.load_contact_group_information() == {}
        assert groups.load_host_group_information() == {}
        assert groups.load_service_group_information() == {}


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

    environ = dict(create_environ(), REQUEST_URI='')
    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(Request(environ))):
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

        assert groups.load_contact_group_information() == {
            'all': {
                'alias': u'Everything',
                "d!ng": "dong",
            }
        }

        assert groups.load_host_group_information() == {
            'all_hosts': {
                'alias': u'All hosts :-)',
                "ding": "dong",
            }
        }

        assert groups.load_service_group_information() == {
            'all_services': {
                'alias': u'All s\xe4rvices',
                "d1ng": "dong",
            }
        }
