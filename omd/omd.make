# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# General settings included by all packages

REPO_PATH          := $(realpath $(dir $(realpath $(dir $(lastword $(MAKEFILE_LIST))))))

include $(REPO_PATH)/defines.make

# Needs to be set after defines.make load (to override the shell defined there)
# TODO: Enable this in a separate step. Seems we need to fix several places before merging
#SHELL := /bin/bash -e -o pipefail

# OMD packages, the single components, are located below this directory
# TODO: Cleanup one of these
PACKAGE_BASE       := $(REPO_PATH)/omd/packages
PACKAGE_DIR        := $(PACKAGE_BASE)
NON_FREE_PACKAGE_DIR := $(REPO_PATH)/non-free/packages
# The OMD build (RPM, DEB, ...) needs some working directorties of several types
# during the build. All of them should be located below this base directory to
# make it easier to clean them up.
BUILD_BASE_DIR     := $(REPO_PATH)/omd/build
# Several targets in the Makefiles need helper files to mark that the target
# excution succeeded.
BUILD_HELPER_DIR := $(BUILD_BASE_DIR)/stamps
# Base for extracting upstream packages to and compiling stuff.  Each OMD
# package creates a package-named subdirectory below this hierarchy which
# contains the files the package needs.
PACKAGE_BUILD_DIR := $(BUILD_BASE_DIR)/package_build
# Base for package specific work directories for random stuff that needs to be
# created during package build. Each OMD package creates a package-named
# subdirectory below this hierarchy which contains the files the package needs.
PACKAGE_WORK_DIR := $(BUILD_BASE_DIR)/package_work
# Each OMD package creates a package-named subdirectory below this hierarchy
# which contains the files the package wants to install.  The files need to be
# relative to $OMD_ROOT, for example
# $INTERMEDIATE_INSTALL_BASE/Python/bin/python will finally result in a file
# /opt/omd/versions/[version]/bin/python.
INTERMEDIATE_INSTALL_BASE := $(BUILD_BASE_DIR)/intermediate_install
# Results of intermediate install will be stored in package specific archives
# that are stored in the global cache directory.
XDG_CACHE_HOME     ?= $(HOME)/.cache
PACKAGE_CACHE_BASE := $(XDG_CACHE_HOME)/checkmk/packages

CMK_VERSION        := $(VERSION)
OMD_SERIAL         := 38

OMD_BASE           := /omd
OMD_PHYSICAL_BASE  := /opt/omd
OMD_ROOT           := $(OMD_BASE)/versions/$(OMD_VERSION)

default: build

# Determine the distro we are running on and its version
DISTRO_INFO        := $(shell $(REPO_PATH)/omd/distro)
DISTRO_NAME        := $(word 1, $(DISTRO_INFO))
DISTRO_VERSION     := $(word 2, $(DISTRO_INFO))

# Depending on the distro we include a Makefile with distro-specific variables.
include $(REPO_PATH)/omd/distros/$(DISTRO_NAME)_$(DISTRO_VERSION).mk

# Create a build target name prefix from a package directory name, e.g.
# python-modules -> PYTHON_MODULES
define package_target_prefix
$(shell echo $1 | tr 'a-z' 'A-Z' | tr '-' '_' )
endef
