#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess

import pytest
from utils import plugin_path

PLUGIN = os.path.join(plugin_path(), "mk_errpt.aix")

ERRPT_OUTPUT = [
    "IDENTIFIER TIMESTAMP  T C RESOURCE_NAME  DESCRIPTION",
    "8650BE3F   0820122810 I H ent2           ETHERCHANNEL RECOVERY",
    "F3846E13   0820122510 P H ent2           ETHERCHANNEL FAILOVER",
    "8650BE3F   0820104410 I H ent2           ETHERCHANNEL RECOVERY",
    "F3846E13   0820093810 P H ent2           ETHERCHANNEL FAILOVER",
    "8650BE3F   0820090910 I H ent2           ETHERCHANNEL RECOVERY",
]

STATE_FILE_NAME = "mk_errpt_aix.last_reported"

LEGACY_STATE_FILE_NAME = "mk_logwatch_aix.last_reported"


def _prepare_mock_errpt(tmp_dir, errpt_output):
    errpt_name = os.path.join(tmp_dir, "errpt")
    errpt_script = "".join(["#!/bin/sh\n"] + ['echo "%s"\n' % line for line in errpt_output])
    with open(errpt_name, "w") as errpt_file:
        errpt_file.write(errpt_script)
    os.chmod(errpt_name, 0o777)  # nosec


def _get_env(tmp_dir):
    env = os.environ.copy()
    env.update({"PATH": "%s:%s" % (tmp_dir, os.getenv("PATH")), "MK_VARDIR": tmp_dir})
    return env


def prepare_state(filepath, write_name, state):
    # make sure we have no left-over files
    for base_file in (STATE_FILE_NAME, LEGACY_STATE_FILE_NAME):
        try:
            os.unlink(os.path.join(filepath, base_file))
        except OSError:
            pass

    if state is None:
        return

    path = os.path.join(filepath, write_name)
    with open(path, "w") as statefile:
        statefile.write("%s\n" % state)


def read_state(filepath):
    try:
        path = os.path.join(filepath, STATE_FILE_NAME)
        with open(path) as statefile:
            new_state = statefile.read()
            assert new_state[-1] == "\n"
            return new_state[:-1]
    except IOError:
        return None


def _format_expected(lines):
    added_prefix = ["C %s\n" % line for line in lines]
    added_header = ["<<<logwatch>>>\n", "[[[errorlog]]]\n"] + added_prefix
    return "".join(added_header)


@pytest.mark.skip("Not a real unit test, we'll have to find a better place")
@pytest.mark.parametrize(
    "state_file_name,errpt_output,last_reported,expectations",
    [
        (
            STATE_FILE_NAME,
            ERRPT_OUTPUT,
            [None, "", ERRPT_OUTPUT[3], ERRPT_OUTPUT[1], "something else entirely"],
            [ERRPT_OUTPUT[1:], ERRPT_OUTPUT[1:], ERRPT_OUTPUT[1:3], [], ERRPT_OUTPUT[1:]],
        ),
        (
            STATE_FILE_NAME,
            ERRPT_OUTPUT[:1],  # no output, just header
            [None, "", "what ever"],
            [[], [], []],
        ),
        (  # legacy statefile name:
            "mk_logwatch_aix.last_reported",
            ERRPT_OUTPUT,
            [None, "", ERRPT_OUTPUT[3], ERRPT_OUTPUT[1], "something else entirely"],
            [ERRPT_OUTPUT[1:], ERRPT_OUTPUT[1:], ERRPT_OUTPUT[1:3], [], ERRPT_OUTPUT[1:]],
        ),
    ],
)
def test_mk_errpt_aix(tmpdir, state_file_name, errpt_output, last_reported, expectations):
    tmp_dir = str(tmpdir)
    _prepare_mock_errpt(tmp_dir, errpt_output)
    env = _get_env(tmp_dir)

    for state, expected in zip(last_reported, expectations):

        prepare_state(tmp_dir, state_file_name, state)

        completed_process = subprocess.run(PLUGIN, env=env, stdout=subprocess.STDOUT, check=False)

        expected = _format_expected(expected)
        assert completed_process.stdout == expected, "expected\n  %r, but got\n  %r" % (
            expected,
            completed_process.stdout,
        )

        new_state = read_state(tmp_dir)

        if len(errpt_output) > 1:  # we should have updated state file
            assert new_state == errpt_output[1]
        else:  # it should not have changed
            assert new_state == state
