# Makefile for Sphinx documentation

.DEFAULT_GOAL := help

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?= -W
SPHINXBUILD   ?= ../../scripts/run-pipenv run sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build
PLANTUML_VERSION = 1.2020.6
PLANTUML_JAR = plantuml.${PLANTUML_VERSION}.jar

.PHONY: help
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

${PLANTUML_JAR}:
	wget "http://downloads.sourceforge.net/project/plantuml/${PLANTUML_VERSION}/$@"
	ln -sf $@ plantuml.jar

.PHONY: spell
spell:
	@$(SPHINXBUILD) -b spelling "$(SOURCEDIR)" "$(BUILDDIR)"

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
.PHONY: Makefile
%: Makefile ${PLANTUML_JAR} spell
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
