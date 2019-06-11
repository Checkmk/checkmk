APPLIANCE := appliance
DISTNAME := $(APPLIANCE)

APPLIANCE_INSTALL_CMA := $(BUILD_HELPER_DIR)/$(DISTNAME)-install

.PHONY: $(APPLIANCE) $(APPLIANCE)-install

$(APPLIANCE)-install: $(APPLIANCE_INSTALL_CMA)

# Do not name APPLIANCE_INSTALL: Otherwise it would be installed for all packaging variants
# This target is called explicitly by "cma" target in top level Makefile
$(APPLIANCE_INSTALL_CMA):
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/web/plugins/sidebar
	install -m 644 $(PACKAGE_DIR)/appliance/webconf_snapin.py $(DESTDIR)$(OMD_ROOT)/share/check_mk/web/plugins/sidebar
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/cma
	install -m 755 $(PACKAGE_DIR)/appliance/post-install $(DESTDIR)$(OMD_ROOT)/lib/cma
	$(TOUCH) $@
