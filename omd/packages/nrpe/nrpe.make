NRPE := nrpe
NRPE_VERS := 3.2.1
NRPE_DIR := $(NRPE)-$(NRPE_VERS)

NRPE_UNPACK := $(BUILD_HELPER_DIR)/$(NRPE_DIR)-unpack
NRPE_BUILD := $(BUILD_HELPER_DIR)/$(NRPE_DIR)-build
NRPE_INSTALL := $(BUILD_HELPER_DIR)/$(NRPE_DIR)-install

#NRPE_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(NRPE_DIR)
NRPE_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(NRPE_DIR)
#NRPE_WORK_DIR := $(PACKAGE_WORK_DIR)/$(NRPE_DIR)

$(NRPE_BUILD): $(NRPE_UNPACK)
	cd $(NRPE_BUILD_DIR) ; ./configure
	$(MAKE) -C $(NRPE_BUILD_DIR)/src check_nrpe
	$(TOUCH) $@

$(NRPE_INSTALL): $(NRPE_BUILD)
	install -m 755 $(NRPE_BUILD_DIR)/src/check_nrpe $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/nrpe
	install -m 644 $(NRPE_BUILD_DIR)/*.md $(DESTDIR)$(OMD_ROOT)/share/doc/nrpe
	install -m 644 $(NRPE_BUILD_DIR)/LEGAL $(DESTDIR)$(OMD_ROOT)/share/doc/nrpe
	$(TOUCH) $@
