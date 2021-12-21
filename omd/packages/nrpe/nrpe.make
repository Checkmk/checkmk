NRPE := nrpe
NRPE_VERS := 3.2.1
NRPE_DIR := $(NRPE)-$(NRPE_VERS)
# Increase this to enforce a recreation of the build cache
NRPE_BUILD_ID := 1

NRPE_UNPACK := $(BUILD_HELPER_DIR)/$(NRPE_DIR)-unpack
NRPE_BUILD := $(BUILD_HELPER_DIR)/$(NRPE_DIR)-build
NRPE_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(NRPE_DIR)-install-intermediate
NRPE_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(NRPE_DIR)-cache-pkg-process
NRPE_INSTALL := $(BUILD_HELPER_DIR)/$(NRPE_DIR)-install

NRPE_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(NRPE_DIR)
NRPE_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(NRPE_DIR)
#NRPE_WORK_DIR := $(PACKAGE_WORK_DIR)/$(NRPE_DIR)

$(NRPE_BUILD): $(NRPE_UNPACK)
	cd $(NRPE_BUILD_DIR) ; ./configure --prefix=""
	$(MAKE) -C $(NRPE_BUILD_DIR)/src check_nrpe
	$(TOUCH) $@

NRPE_CACHE_PKG_PATH := $(call cache_pkg_path,$(NRPE_DIR),$(NRPE_BUILD_ID))

$(NRPE_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(NRPE_DIR),$(NRPE_BUILD_ID),$(NRPE_INTERMEDIATE_INSTALL))

$(NRPE_CACHE_PKG_PROCESS): $(NRPE_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(NRPE_CACHE_PKG_PATH),$(NRPE_DIR))
	$(call upload_pkg_archive,$(NRPE_CACHE_PKG_PATH),$(NRPE_DIR),$(NRPE_BUILD_ID))
	$(TOUCH) $@

$(NRPE_INTERMEDIATE_INSTALL): $(NRPE_BUILD)
	$(MKDIR) $(NRPE_INSTALL_DIR)/lib/nagios/plugins
	install -m 755 $(NRPE_BUILD_DIR)/src/check_nrpe $(NRPE_INSTALL_DIR)/lib/nagios/plugins
	
	$(MKDIR) $(NRPE_INSTALL_DIR)/share/doc/nrpe
	install -m 644 $(NRPE_BUILD_DIR)/*.md $(NRPE_INSTALL_DIR)/share/doc/nrpe
	install -m 644 $(NRPE_BUILD_DIR)/LEGAL $(NRPE_INSTALL_DIR)/share/doc/nrpe
	$(TOUCH) $@

$(NRPE_INSTALL): $(NRPE_CACHE_PKG_PROCESS)
	$(RSYNC) $(NRPE_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
