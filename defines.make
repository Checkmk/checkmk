# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
#

REPO_PATH          := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))

EDITION            := raw
EDITION_SHORT      := cre

ifneq (,$(wildcard $(REPO_PATH)/enterprise))
ENTERPRISE         := yes
EDITION            := enterprise
EDITION_SHORT      := cee
else
ENTERPRISE         := no
endif

ifneq (,$(wildcard $(REPO_PATH)/managed))
MANAGED            := yes
EDITION            := managed
EDITION_SHORT      := cme
else
MANAGED            := no
endif

VERSION            := 1.6.0p29
# Will be set to ".demo" by cmk build system when building a demo package
DEMO_SUFFIX        :=
OMD_VERSION        := $(VERSION).$(EDITION_SHORT)$(DEMO_SUFFIX)
# Do not use the the ".c?e" EDITION_SHORT suffix, the edition is part of the package name
# But keep the ".demo" suffix. Somehow inconsistent, but this is our scheme.
PKG_VERSION        := $(VERSION)$(DEMO_SUFFIX)

SHELL              := /bin/bash
# TODO: Be more strict - Add this:
#SHELL              := /bin/bash -e -o pipefail

# Helper for shell checkers / fixers with all shell script the tools
# should care about
# TODO: Complete this list
SHELL_FILES := \
	agents/check_mk_agent.linux \
	agents/check_mk_caching_agent.linux
