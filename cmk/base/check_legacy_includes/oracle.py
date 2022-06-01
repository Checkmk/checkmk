#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=no-else-continue

from cmk.base.check_api import MKGeneralException


# This function must be executed for each agent line which has been
# found for the current item. It must deal with the ORA-* error
# messages. It has to skip over the lines which show the SQL statement
# and the SQL error message which comes before the ORA-* message.
#
# The check must completely skip the lines before the ORA-* messages
# and return UNKNOWN on the first found ORA-* message.
# line[0] is the item (db instance)
#
# This function returns a tuple when an ORA-* message has been found.
# It returns False if this line should be skipped by the check.
# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/oracle.py
# ==================================================================================================
def oracle_handle_ora_errors(line):
    if len(line) == 1:
        return None

    legacy_error = oracle_handle_legacy_ora_errors(line)
    if legacy_error:
        return legacy_error

    # Handle error output from new agent
    if line[1] == "FAILURE":
        if len(line) >= 3 and line[2].startswith("ORA-"):
            return (3, "%s" % " ".join(line[2:]))
        return False  # ignore other FAILURE lines

    # Handle error output from old (pre 1.2.0p2) agent
    if line[1] in ["select", "*", "ERROR"]:
        return False
    if line[1].startswith("ORA-"):
        return (3, 'Found error in agent output "%s"' % " ".join(line[1:]))
    return None


# ==================================================================================================
# THE VARIABLES AND FUNCTIONS DEFINED HERE ARE IN THE PROCESS OF OR HAVE ALREADY BEEN MIGRATED TO
# THE NEW CHECK API. PLEASE DO NOT MODIFY THIS FILE ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/oracle.py
# ==================================================================================================
def oracle_handle_legacy_ora_errors(line):
    # Skip over line before ORA- errors (e.g. sent by AIX agent from 2014)
    if line == ["ERROR:"]:
        return False

    if line[0].startswith("ORA-"):
        return (3, 'Found error in agent output "%s"' % " ".join(line))

    # Handle error output from 1.6 solaris agent, see SUP-9521
    if line[0] == "Error":
        return (3, 'Found error in agent output "%s"' % " ".join(line[1:]))
    return None


# Fully prevent creation of services when an error is found.
def oracle_handle_ora_errors_discovery(info):
    for line in info:
        err = oracle_handle_ora_errors(line)
        if err is False:
            continue
        elif isinstance(err, tuple):
            raise MKGeneralException(err[1])
