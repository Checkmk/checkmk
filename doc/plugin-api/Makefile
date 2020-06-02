# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

REPO_PATH := $(realpath $(dir $(realpath $(dir $(realpath $(dir $(lastword $(MAKEFILE_LIST))))))))

include $(REPO_PATH)/defines.make

PIPENV3 := $(REPO_PATH)/scripts/run-pipenv 3


# You can set these variables from the command line, and also
# from the environment for the first one.
SPHINXOPTS    ?=
SPHINXBUILD   := $(PIPENV3) run sphinx-build
SPHINXAPIDOC  := $(PIPENV3) run sphinx-apidoc
BASEDIR       = $(REPO_PATH)/doc/plugin-api
SOURCEDIR     = $(BASEDIR)/source
BUILDDIR      = $(BASEDIR)/build
TEMPDIR       = $(BASEDIR)/templates

.PHONY: help Makefile apidoc apidoc-clean

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

apidoc-clean:
	rm "$(SOURCEDIR)/apidoc" -rf

apidoc:
	$(SPHINXAPIDOC) \
	    --no-toc \
	    --templatedir "$(TEMPDIR)" \
	    --output-dir "$(SOURCEDIR)/apidoc/agent_based" \
	    "$(REPO_PATH)/cmk/base/plugins/agent_based/agent_based_api"
ifeq ($(ENTERPRISE),yes)
	$(SPHINXAPIDOC) \
	    --no-toc \
	    --templatedir "$(TEMPDIR)" \
	    --output-dir "$(SOURCEDIR)/apidoc/dcd" \
	    "$(REPO_PATH)/enterprise/cmk/cee/dcd/plugins/connectors/connectors_api"
endif

# TODO: Don't understand why we need this. Something calls the % target below
# with the "$(REPO_PATH)/defines.make" target once we include this file above.
# This target prevents the % from handling the call.
$(REPO_PATH)/defines.make:
	@echo ""

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
