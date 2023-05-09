#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess

import os
from pathlib import Path


def test_no_exeption(site):
    """
    The execution of a special agent should not lead to an exception
    if the agent is called without any arguments.
    Possible reasons for an exception are e.g. a wrong shebang, import
    errors or a wrong PYTHONPATH.
    """
    special_agent_dir = Path(site.root) / 'share' / 'check_mk' / 'agents' / 'special'
    for special_agent_path in special_agent_dir.glob('agent_*'):
        command = [str(special_agent_path)]
        p = site.execute(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=open(os.devnull))
        stderr = p.communicate()[1]
        assert "Traceback (most recent call last):" not in stderr
