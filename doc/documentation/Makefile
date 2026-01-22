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
	@echo "Targets:"
	@echo "  html            to make standalone HTML files (includes spell check)"
	@echo "  html-nospell    to make standalone HTML files without spell checking"
	@echo "  spell           to run spell checking only"

.PHONY: spell
spell:
	@PLANTUML_JAR_PATH=$(PLANTUML_JAR_PATH) $(SPHINXBUILD) -b spelling "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

.PHONY: htmlhelp html
htmlhelp html:
ifndef NOSPELL
	$(MAKE) spell
endif
	@PLANTUML_JAR_PATH=$(PLANTUML_JAR_PATH) $(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: html-nospell
html-nospell:
	$(MAKE) NOSPELL=1 html
