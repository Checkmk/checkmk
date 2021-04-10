# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

REPO_PATH := $(realpath $(dir $(realpath $(dir $(realpath $(dir $(lastword $(MAKEFILE_LIST))))))))

include $(REPO_PATH)/defines.make

PIPENV := $(REPO_PATH)/scripts/run-pipenv


# You can set these variables from the command line, and also
# from the environment for the first one.
SPHINXOPTS    ?=
SPHINXBUILD   := $(PIPENV) run sphinx-build
BASEDIR       = $(REPO_PATH)/doc/plugin-api
SOURCEDIR     = $(BASEDIR)/source
BUILDDIR      = $(BASEDIR)/build
TEMPDIR       = $(BASEDIR)/templates

.PHONY: help Makefile

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# TODO: Don't understand why we need this. Something calls the % target below
# with the "$(REPO_PATH)/defines.make" target once we include this file above.
# This target prevents the % from handling the call.
$(REPO_PATH)/defines.make:
	@echo ""

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
