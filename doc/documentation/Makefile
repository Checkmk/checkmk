# Makefile for Sphinx documentation

include ../../defines.make

.DEFAULT_GOAL := help

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?= -W
SPHINXBUILD   ?= ../../scripts/run-uvenv sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: spell
spell:
	@PLANTUML_JAR_PATH=$(PLANTUML_JAR_PATH) $(SPHINXBUILD) -b spelling "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

.PHONY: htmlhelp html
htmlhelp html: Makefile spell
	@PLANTUML_JAR_PATH=$(PLANTUML_JAR_PATH) $(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
