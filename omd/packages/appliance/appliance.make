APPLIANCE := appliance

APPLIANCE_INSTALL_CMA := $(BUILD_HELPER_DIR)/$(APPLIANCE)-install
APPLIANCE_SKEL_CMA := $(BUILD_HELPER_DIR)/$(APPLIANCE)-skel

.PHONY: $(APPLIANCE) $(APPLIANCE)-install $(APPLIANCE)-skel

$(APPLIANCE)-install: $(APPLIANCE_INSTALL_CMA)
$(APPLIANCE)-skel: $(APPLIANCE_SKEL_CMA)

# Do not name APPLIANCE_INSTALL: Otherwise it would be installed for all packaging variants
# This target is called explicitly by "cma" target in top level Makefile
$(APPLIANCE_INSTALL_CMA):
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/web/plugins/sidebar
	install -m 644 $(PACKAGE_DIR)/appliance/webconf_snapin.py $(DESTDIR)$(OMD_ROOT)/share/check_mk/web/plugins/sidebar
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/cma
	install -m 755 $(PACKAGE_DIR)/appliance/post-install $(DESTDIR)$(OMD_ROOT)/lib/cma
	$(TOUCH) $@


# Do not name APPLIANCE_SKEL: Otherwise it would be installed for all packaging variants
# This target is called explicitly by "cma" target in top level Makefile
$(APPLIANCE_SKEL_CMA):
	$(MKDIR) $(SKEL)/etc/apache/conf.d
	install -m 644 $(PACKAGE_DIR)/appliance/cma.conf $(SKEL)/etc/apache/conf.d/
	$(TOUCH) $@
