# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

REPO_PATH := $(realpath $(dir $(realpath $(dir $(realpath $(dir $(lastword $(MAKEFILE_LIST))))))))

include $(REPO_PATH)/defines.make

PIPENV := $(REPO_PATH)/scripts/run-pipenv


# You can set these variables from the command line, and also
# from the environment for the first one.
SPHINXOPTS    ?=
SPHINXBUILD   := $(PIPENV) run sphinx-build
SPHINXAPIDOC  := $(PIPENV) run sphinx-apidoc
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

# TODO: We can possibly dump apidoc, as the only thing we use is to generate
# the always-same ..autodoc directive for all out modules.
# A proper toc generation would be nice, but apidoc failed to generate a
# nice-looking toc. (Or we failed configuring autodoc...)
# Explanation for some arguments:
# --module-first: We want e.g. bakery_api.v1 before bakery_api.v1.register
# --no-toc: We write our own toc in source/index.rst
# --separate: Generates one page per module. Keep this. all submodules of a
#             package will be missing otherwise, because we don't iterate
#             over them in the package.rst_t template
apidoc:
	SPHINX_APIDOC_OPTIONS=members,show-inheritance \
	$(SPHINXAPIDOC) \
	    --follow-links \
	    --implicit-namespaces \
	    --module-first \
	    --no-toc \
	    --no-headings \
	    --separate \
	    --templatedir "$(TEMPDIR)" \
	    --output-dir "$(SOURCEDIR)/apidoc/cmk" \
	    "$(REPO_PATH)/cmk"
# sphinx-apidoc file / module selection is not very powerful. Sort out the
# non api files on our own here
	find source/apidoc -type f ! -name 'cmk.*.plugins.*.*_api.*' -exec rm {} \;
	rm source/apidoc/cmk/cmk.base.plugins.agent_based.utils.netapp_api.rst;

# TODO: Don't understand why we need this. Something calls the % target below
# with the "$(REPO_PATH)/defines.make" target once we include this file above.
# This target prevents the % from handling the call.
$(REPO_PATH)/defines.make:
	@echo ""

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
