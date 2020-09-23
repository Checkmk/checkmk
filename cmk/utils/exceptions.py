#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__all__ = [
    "MKException",
    "MKGeneralException",
    "MKTerminate",
    "MKBailOut",
    "MKTimeout",
    "MKSNMPError",
    "MKIPAddressLookupError",
]


# never used directly in the code. Just some wrapper to make all of our
# exceptions handleable with one call
class MKException(Exception):
    pass


class MKGeneralException(MKException):
    pass


# This exception is raises when the current program execution should be
# terminated. For example it is raised by the SIGINT signal handler to
# propagate the termination up the callstack.
# This should be raised in all cases where the program termination is a
# "normal" case and no exception handling like printing a stack trace
# nor an error message should be done. The program is stopped with
# exit code 0.
class MKTerminate(MKException):
    pass


# This is raised to print an error message and then end the program.
# The program should catch this at top level and end exit the program
# with exit code 3, in order to be compatible with monitoring plugin API.
class MKBailOut(MKException):
    pass


# This exception is raised when a previously configured timeout is reached.
# It is used during keepalive mode. It is also used by the automations
# which have a timeout set.
class MKTimeout(MKException):
    pass


class MKSNMPError(MKException):
    pass


class MKIPAddressLookupError(MKGeneralException):
    pass
