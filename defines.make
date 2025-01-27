# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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

ifneq (,$(wildcard $(REPO_PATH)/cloud))
CLOUD              := yes
EDITION            := cloud
EDITION_SHORT      := cce
else
CLOUD              := no
endif

VERSION            := 2.2.0p40
OMD_VERSION        := $(VERSION).$(EDITION_SHORT)
# Do not use the the ".c?e" EDITION_SHORT suffix, the edition is part of the package name
PKG_VERSION        := $(VERSION)

# Currently only used for the OMD package build cache. We did not want to use
# the branch name, because we want to re-use a single cache also for derived sandbox
# branches (1.7.0i1 -> 1.7.0).
# This needs to be changed in the master branch every time a stable branch is forked.
BRANCH_VERSION     := 2.2.0

# return nothing if the branch name, e.g. "master" is not the version e.g. 2.4.0
# this is evaluated by "buildscripts/scripts/utils/versioning.groovy" and does
# fallback to "master" instead of the branch version value above
# set this to any value after creating a new (beta) branch
BRANCH_NAME_IS_BRANCH_VERSION := yes

# This automatism did not work well in all cases. There were daily build jobs that used
# e.g. 2020.02.08 as BRANCH_VERSION, even if they should use 1.7.0
#BRANCH_VERSION := $(shell echo "$(VERSION)" | sed -E 's/^([0-9]+.[0-9]+.[0-9]+).*$$/\1/')
# In case of "master daily builds" we get the DATE as BRANCH_VERSION, which is
# not what we want. TODO: Find a solution for this
#ifeq ($(BRANCH_VERSION),$(shell date +%Y.%m.%d))
#    BRANCH_VERSION := 1.7.0
#endif

SHELL              := /bin/bash
CLANG_VERSION      := 14

PLANTUML_JAR_PATH  := $(REPO_PATH)/third_party/plantuml

# In our CI we use this compiler, but we are not restricted to this exact version
GCC_VERSION_MAJOR      := 13
GCC_VERSION_MINOR      := 2
GCC_VERSION_PATCHLEVEL := 0
GCC_VERSION	       := ${GCC_VERSION_MAJOR}.${GCC_VERSION_MINOR}.${GCC_VERSION_PATCHLEVEL}

# NOTE: When you update the Python version, please take care of the following things:
# * update test_03_pip_interpreter_version
# * update omd/Licenses.csv, too.
# * you may need to regenerate the Pipfile.lock with "make --what-if Pipfile Pipfile.lock"
PYTHON_VERSION  := 3.11.10

# convenience stuff derived from PYTHON_VERSION
PY_ARRAY	       := $(subst ., ,$(PYTHON_VERSION))
PYTHON_VERSION_MAJOR   := $(word 1,$(PY_ARRAY))
PYTHON_VERSION_MINOR   := $(word 2,$(PY_ARRAY))
PYTHON_VERSION_PATCH   := $(word 3,$(PY_ARRAY))
PYTHON_MAJOR_MINOR     := $(PYTHON_VERSION_MAJOR)$(PYTHON_VERSION_MINOR)
PYTHON_MAJOR_DOT_MINOR := $(PYTHON_VERSION_MAJOR).$(PYTHON_VERSION_MINOR)

AGENT_PLUGIN_PYTHON_VERSIONS := 2.7 3.4 3.5 3.6 3.7 3.8 3.9 3.10 3.11

# Needed for bootstrapping CI and development environments
PIPENV_VERSION := 2023.2.18
VIRTUALENV_VERSION := 20.20.0
NODEJS_VERSION := 18
NPM_VERSION := 10

# PyPi Mirror Configuration
# By default our internal Python mirror is used.
# To use the official Python mirror, please export `USE_EXTERNAL_PIPENV_MIRROR=true`.
EXTERNAL_PYPI_MIRROR := https://pypi.python.org/simple
INTERNAL_PYPI_MIRROR :=  https://devpi.lan.tribe29.com/root/pypi

ifeq (true,${USE_EXTERNAL_PIPENV_MIRROR})
PIPENV_PYPI_MIRROR  := $(EXTERNAL_PYPI_MIRROR)
else
PIPENV_PYPI_MIRROR  := $(INTERNAL_PYPI_MIRROR)
endif

print-%:
	@echo '$($*)'
