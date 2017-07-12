#!/usr/bin/python
# encoding: utf-8

import os
import glob
import pytest
from testlib import cmk_path

# Mark all tests in this file to be executed in the git context
pytestmark = pytest.mark.git

def is_executable(path):
    return os.path.isfile(path) and os.access(path, os.X_OK)

def is_not_executable(path):
    return os.path.isfile(path) and not os.access(path, os.X_OK)

permissions = [
    # globbing pattern                check function,   excludes
    ('active_checks/*',               is_executable, ['Makefile', 'check_mkevents.cc']),
    ('agents/special/agent_*',        is_executable, []),
    ('agents/special/lib/*',          is_not_executable, []),
    ('agents/check_mk_agent.*',       is_executable, ['check_mk_agent.spec']),
    ('agents/plugins/*',              is_executable, ['README']),
    ('checks/*',                      is_not_executable, []),
    ('checkman/*',                    is_not_executable, []),
    ('inventory/*',                   is_not_executable, []),
    ('pnp-templates/*',               is_not_executable, []),
    ('notifications/*',               is_executable, ['README', 'debug']),
    ('bin/*',                         is_executable, ['Makefile', 'mkevent.cc', 'mkeventd_open514.cc']),
    # Enterprise specific
    ('enterprise/bin/*',              is_executable, []),
    ('enterprise/active_checks/*',    is_executable, []),
    ('enterprise/agents/bakery/*',    is_not_executable, []),
    ('enterprise/agents/plugins/*',   is_executable, []),
    ('enterprise/alert_handlers/*',   is_executable, []),
    ('enterprise/alert_handlers/*',   is_executable, []),
]

def test_permissions():
    for pattern, check_func, excludes in permissions:
        for f in glob.glob("%s/%s" % (cmk_path(), pattern)):
            if f.split('/')[-1] in excludes:
                continue
            assert check_func(f), "%s has wrong permissions (%r)" % \
							(f, check_func)
