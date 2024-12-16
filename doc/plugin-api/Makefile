# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

REPO_PATH := $(realpath $(dir $(realpath $(dir $(realpath $(dir $(lastword $(MAKEFILE_LIST))))))))

include $(REPO_PATH)/defines.make

UVENV := $(REPO_PATH)/scripts/run-uvenv


# You can set these variables from the command line, and also
# from the environment for the first one.
SPHINXOPTS    ?= --fail-on-warning
SPHINXBUILD   := $(UVENV) sphinx-build
BASEDIR       = $(REPO_PATH)/doc/plugin-api
SOURCEDIR     = $(BASEDIR)/source
BUILDDIR      = $(BASEDIR)/build
TEMPDIR       = $(BASEDIR)/templates

.PHONY: help Makefile

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	@rm "$(BUILDDIR)" -rf

url:
	@echo file://$(BUILDDIR)/html/index.html

# TODO: Don't understand why we need this. Something calls the % target below
# with the "$(REPO_PATH)/defines.make" target once we include this file above.
# This target prevents the % from handling the call.
$(REPO_PATH)/defines.make:
	@echo ""

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
