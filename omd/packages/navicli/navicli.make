NAVICLI := navicli
NAVICLI_VERS := 0.7.1
NAVICLI_DIR := $(NAVICLI)-$(NAVICLI_VERS)

NAVICLI_BUILD := $(BUILD_HELPER_DIR)/$(NAVICLI_DIR)-build
NAVICLI_INSTALL := $(BUILD_HELPER_DIR)/$(NAVICLI_DIR)-install

$(NAVICLI_BUILD):
	$(TOUCH) $@

# NOTE: The EMC Navisphere command line tools come with their own dynamic
# libraries, which are quite old and some of them even collide with newer ones
# supplied by the distro, e.g. the OpenSSL libraries. We must take great care
# and should NEVER EVER put these ancient libraries into the search path of the
# dynamic linker, the only exception being when calling naviseccli itself. As a
# consequence, we install the libraries to a subdirectory which is not searched
# and call the command via a wrapper which sets LD_LIBRARY_PATH.
$(NAVICLI_INSTALL):
	install -m 755 $(PACKAGE_DIR)/$(NAVICLI)/$(NAVICLI_DIR)/bin/admsnap $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(PACKAGE_DIR)/$(NAVICLI)/$(NAVICLI_DIR)/bin/setlevel_cli.sh $(DESTDIR)$(OMD_ROOT)/bin
	( echo '#! /bin/sh' ; \
	  echo 'LD_LIBRARY_PATH="$$LD_LIBRARY_PATH:$(OMD_ROOT)/lib/seccli" exec $(OMD_ROOT)/lib/seccli/naviseccli "$$@"' ) > $(DESTDIR)$(OMD_ROOT)/bin/naviseccli
	chmod 0755 $(DESTDIR)$(OMD_ROOT)/bin/naviseccli
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/seccli
	install -m 755 $(PACKAGE_DIR)/$(NAVICLI)/$(NAVICLI_DIR)/bin/naviseccli $(DESTDIR)$(OMD_ROOT)/lib/seccli
	install -m 755 $(PACKAGE_DIR)/$(NAVICLI)/$(NAVICLI_DIR)/lib/seccli/* $(DESTDIR)$(OMD_ROOT)/lib/seccli
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/navicli
	cp -pr $(PACKAGE_DIR)/$(NAVICLI)/$(NAVICLI_DIR)/seccli/CST $(DESTDIR)$(OMD_ROOT)/share/navicli
	chmod 755 $(DESTDIR)$(OMD_ROOT)/share/navicli/CST
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/navicli/CST/*.xml
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/navicli/CST/*.xsd
	$(TOUCH) $@
