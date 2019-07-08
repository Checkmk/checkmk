#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import subprocess

import os
from pathlib2 import Path


def test_no_exeption(site):
    """
    The execution of a special agent should not lead to an exception
    if the agent is called without any arguments.
    Possible reasons for an exception are e.g. a wrong shebang, import
    errors or a wrong PYTHONPATH.
    """
    special_agent_dir = Path(site.root) / 'share' / 'check_mk' / 'agents' / 'special'
    for special_agent_path in special_agent_dir.glob('agent_*'):  # pylint: disable=no-member
        command = [str(special_agent_path)]
        p = site.execute(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=open(os.devnull))
        stderr = p.communicate()[1]
        assert "Traceback (most recent call last):" not in stderr
