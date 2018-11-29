CMA_INSTALL := $(BUILD_HELPER)/cma-install

install: $(CMA_INSTALL)
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/check_mk/web/plugins/sidebar
	install -m 644 $(PACKAGE_DIR)/cma/webconf_snapin.py $(DESTDIR)$(OMD_ROOT)/share/check_mk/web/plugins/sidebar
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/cma
	install -m 755 i$(PACKAGE_DIR)/cma/post-install $(DESTDIR)$(OMD_ROOT)/lib/cma
