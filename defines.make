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

VERSION            := 1.7.0i1
# Will be set to ".demo" by cmk build system when building a demo package
DEMO_SUFFIX        :=
OMD_VERSION        := $(VERSION).$(EDITION_SHORT)$(DEMO_SUFFIX)
# Do not use the the ".c?e" EDITION_SHORT suffix, the edition is part of the package name
# But keep the ".demo" suffix. Somehow inconsistent, but this is our scheme.
PKG_VERSION        := $(VERSION)$(DEMO_SUFFIX)

# Currently only used for the OMD package build cache. We did not want to use
# the branch name, because we want to re-use a single cache also for derived sandbox
# branches (1.7.0i1 -> 1.7.0).
# This needs to be changed in the master branch every time a stable branch is forked.
BRANCH_VERSION     := 1.7.0
# This automatism did not work well in all cases. There were daily build jobs that used
# e.g. 2020.02.08 as BRANCH_VERSION, even if they should use 1.7.0
#BRANCH_VERSION := $(shell echo "$(VERSION)" | sed -E 's/^([0-9]+.[0-9]+.[0-9]+).*$$/\1/')
# In case of "master daily builds" we get the DATE as BRANCH_VERSION, which is
# not what we want. TODO: Find a solution for this
#ifeq ($(BRANCH_VERSION),$(shell date +%Y.%m.%d))
#    BRANCH_VERSION := 1.7.0
#endif

SHELL              := /bin/bash
# TODO: Be more strict - Add this:
#SHELL              := /bin/bash -e -o pipefail

# Helper for shell checkers / fixers with all shell script the tools
# should care about
# TODO: Complete this list
SHELL_FILES := \
	agents/check_mk_agent.linux \
	agents/check_mk_caching_agent.linux
