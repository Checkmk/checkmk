include ../../Makefile.omd

NAME    = navicli
VERSION = 0.7.1

UNAME_M := $(shell uname -m)
ifeq ($(UNAME_M),x86_64)
    SOURCE_DIR=navisphere-64
endif
ifeq ($(UNAME_M),i686)
    SOURCE_DIR=navisphere-32
endif

ifeq ($(SOURCE_DIR),)
    $(error "Falsche Architektur: $(UNAME_M)")
endif

.PHONY: build install skel clean

build:

# NOTE: The EMC Navisphere command line tools come with their own dynamic
# libraries, which are quite old and some of them even collide with newer ones
# supplied by the distro, e.g. the OpenSSL libraries. We must take great care
# and should NEVER EVER put these ancient libraries into the search path of the
# dynamic linker, the only exception being when calling naviseccli itself. As a
# consequence, we install the libraries to a subdirectory which is not searched
# and call the command via a wrapper which sets LD_LIBRARY_PATH.
install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(SOURCE_DIR)/bin/admsnap $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(SOURCE_DIR)/bin/setlevel_cli.sh $(DESTDIR)$(OMD_ROOT)/bin
	( echo '#! /bin/sh' ; \
	  echo 'LD_LIBRARY_PATH="$$LD_LIBRARY_PATH:$(OMD_ROOT)/lib/seccli" exec $(OMD_ROOT)/lib/seccli/naviseccli "$$@"' ) > $(DESTDIR)$(OMD_ROOT)/bin/naviseccli
	chmod 0755 $(DESTDIR)$(OMD_ROOT)/bin/naviseccli
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/seccli
	install -m 755 $(SOURCE_DIR)/bin/naviseccli $(DESTDIR)$(OMD_ROOT)/lib/seccli
	install -m 755 $(SOURCE_DIR)/lib/seccli/* $(DESTDIR)$(OMD_ROOT)/lib/seccli
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/navicli
	cp -pr $(SOURCE_DIR)/seccli/CST $(DESTDIR)$(OMD_ROOT)/share/navicli

skel:
