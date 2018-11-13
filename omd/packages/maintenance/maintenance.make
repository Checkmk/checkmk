MAINTENANCE := maintenance
MAINTENANCE_VERS := $(OMD_VERSION)

MAINTENANCE_INSTALL := $(BUILD_HELPER_DIR)/$(MAINTENANCE)-install

.PHONY: $(MAINTENANCE) $(MAINTENANCE)-skel $(MAINTENANCE)-clean build-helper/maintenance

$(MAINTENANCE)-install: $(MAINTENANCE_INSTALL)

$(MAINTENANCE):

$(MAINTENANCE_INSTALL):
	mkdir -p $(DESTDIR)$(OMD_ROOT)/bin
	install -v -m 755 $(PACKAGE_DIR)/$(MAINTENANCE)/merge-crontabs $(DESTDIR)$(OMD_ROOT)/bin
	install -v -m 755 $(PACKAGE_DIR)/$(MAINTENANCE)/diskspace $(DESTDIR)$(OMD_ROOT)/bin
	install -v -m 755 $(PACKAGE_DIR)/$(MAINTENANCE)/logrotate $(DESTDIR)$(OMD_ROOT)/bin
	
	# Create directory for the diskspace plugin
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/diskspace
	$(TOUCH) $@

maintenance-skel:

maintenance-clean:
