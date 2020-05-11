
BASEDIR := ../..

PIPENV3 := $(BASEDIR)/scripts/run-pipenv 3


# You can set these variables from the command line, and also
# from the environment for the first one.
SPHINXOPTS    ?=
SPHINXBUILD   := $(PIPENV3) run sphinx-build
SPHINXAPIDOC  := $(PIPENV3) run sphinx-apidoc
SOURCEDIR     = source
BUILDDIR      = build
TEMPDIR       = templates

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

apidoc-clean:
	rm "$(SOURCEDIR)/apidoc" -rf

apidoc:
	$(SPHINXAPIDOC) \
	    --no-toc \
	    --templatedir "$(TEMPDIR)" \
	    --output-dir "$(SOURCEDIR)/apidoc/agent_based" \
	    "$(BASEDIR)/cmk/base/plugins/agent_based/agent_based_api"

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
