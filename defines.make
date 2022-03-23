# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

# Will be set to "yes" by cmk build system when building a free edition
FREE               := no

ifeq (yes,$(FREE))
EDITION            := free
EDITION_SHORT      := cfe
endif

VERSION            := 2.0.0p23
OMD_VERSION        := $(VERSION).$(EDITION_SHORT)
# Do not use the the ".c?e" EDITION_SHORT suffix, the edition is part of the package name
PKG_VERSION        := $(VERSION)

# Currently only used for the OMD package build cache. We did not want to use
# the branch name, because we want to re-use a single cache also for derived sandbox
# branches (1.7.0i1 -> 1.7.0).
# This needs to be changed in the master branch every time a stable branch is forked.
BRANCH_VERSION     := 2.0.0
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
