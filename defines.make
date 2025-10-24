# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#

REPO_PATH          := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))

EDITION            := raw
EDITION_SHORT      := cre

ifneq (,$(wildcard $(REPO_PATH)/omd/packages/enterprise))
EDITION            := enterprise
EDITION_SHORT      := cee
endif

ifneq (,$(wildcard $(REPO_PATH)/omd/packages/cloud))
EDITION            := cloud
EDITION_SHORT      := cce
endif

ifneq (,$(wildcard $(REPO_PATH)/omd/packages/managed))
EDITION            := managed
EDITION_SHORT      := cme
endif

ifneq (,$(wildcard $(REPO_PATH)/omd/packages/saas))
EDITION            := saas
EDITION_SHORT      := cse
endif

VERSION            := 2.5.0b1
OMD_VERSION        := $(VERSION).$(EDITION_SHORT)
# Do not use the the ".c?e" EDITION_SHORT suffix, the edition is part of the package name
PKG_VERSION        := $(VERSION)

# Currently only used for the OMD package build cache. We did not want to use
# the branch name, because we want to re-use a single cache also for derived sandbox
# branches (1.7.0i1 -> 1.7.0).
# This needs to be changed in the master branch every time a stable branch is forked.
BRANCH_VERSION     := 2.5.0

# return nothing if the branch name, e.g. "master" is not the version e.g. 2.4.0
# this is evaluated by "buildscripts/scripts/utils/versioning.groovy" and does
# fallback to "master" instead of the branch version value above
# set this to any value after creating a new (beta) branch
BRANCH_NAME_IS_BRANCH_VERSION :=

SHELL              := /bin/bash
CLANG_VERSION      := 19

PLANTUML_JAR_PATH  := $(REPO_PATH)/third_party/plantuml

# In our CI we use this compiler, but we are not restricted to this exact version
GCC_VERSION_MAJOR      := 14
GCC_VERSION_MINOR      := 2
GCC_VERSION_PATCHLEVEL := 0
GCC_VERSION	       := ${GCC_VERSION_MAJOR}.${GCC_VERSION_MINOR}.${GCC_VERSION_PATCHLEVEL}

# NOTE: When you update the Python version, please take care of the following things:
# * the python version is now centralized within bazel, see package_versions.bzl
# * update test_03_pip_interpreter_version
PYTHON_VERSION  := $(shell sed -n 's|^PYTHON_VERSION = \"\(\S*\)\"$$|\1|p' $(REPO_PATH)/package_versions.bzl)

# convenience stuff derived from PYTHON_VERSION
PY_ARRAY	       := $(subst ., ,$(PYTHON_VERSION))
PYTHON_VERSION_MAJOR   := $(word 1,$(PY_ARRAY))
PYTHON_VERSION_MINOR   := $(word 2,$(PY_ARRAY))
PYTHON_VERSION_PATCH   := $(word 3,$(PY_ARRAY))
PYTHON_MAJOR_MINOR     := $(PYTHON_VERSION_MAJOR)$(PYTHON_VERSION_MINOR)
PYTHON_MAJOR_DOT_MINOR := $(PYTHON_VERSION_MAJOR).$(PYTHON_VERSION_MINOR)

# We're separating the python version used in the windows agent modules as they are not directly connected.
# However, we should keep them as close as possible.
PYTHON_VERSION_WINDOWS := 3.12.6

# convenience stuff derived from PYTHON_VERSION_WINDOWS
PY_ARRAY_WINDOWS		:= $(subst ., ,$(PYTHON_VERSION_WINDOWS))
PYTHON_VERSION_WINDOWS_MAJOR	:= $(word 1,$(PY_ARRAY_WINDOWS))
PYTHON_VERSION_WINDOWS_MINOR   := $(word 2,$(PY_ARRAY_WINDOWS))
PYTHON_VERSION_WINDOWS_PATCH   := $(word 3,$(PY_ARRAY_WINDOWS))
PYTHON_VERSION_WINDOWS_MAJOR_DOT_MINOR := $(PYTHON_VERSION_WINDOWS_MAJOR).$(PYTHON_VERSION_WINDOWS_MINOR)

AGENT_PLUGIN_PYTHON_VERSIONS := 3.4 3.5 3.6 3.7 3.8 3.9 3.10 3.11 3.12

# Needed for bootstrapping CI and development environments
VIRTUALENV_VERSION := 20.25.0
NODEJS_VERSION := 22
NPM_VERSION := 10

# Bazel paths
BAZEL_BIN := "$(REPO_PATH)/bazel-bin"
BAZEL_BIN_EXT := "$(BAZEL_BIN)/external"

print-%:
	@echo '$($*)'
