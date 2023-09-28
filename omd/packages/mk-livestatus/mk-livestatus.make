MK_LIVESTATUS := mk-livestatus
MK_LIVESTATUS_DIR := $(MK_LIVESTATUS)-$(CMK_VERSION)

# It is used from top-level Makefile and this makefile as an intermediate step.
# We should end up with one central place to care for packaging our files
# without the need to have shared logic between like this.
include ../artifacts.make

# Attention: copy-n-paste from check_mk/Makefile below...
MK_LIVESTATUS_UNPACK := $(BUILD_HELPER_DIR)/$(MK_LIVESTATUS_DIR)-unpack
MK_LIVESTATUS_BUILD := $(BUILD_HELPER_DIR)/$(MK_LIVESTATUS_DIR)-build
MK_LIVESTATUS_INSTALL := $(BUILD_HELPER_DIR)/$(MK_LIVESTATUS_DIR)-install

#MK_LIVESTATUS_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(MK_LIVESTATUS_DIR)
MK_LIVESTATUS_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(MK_LIVESTATUS_DIR)
#MK_LIVESTATUS_WORK_DIR := $(PACKAGE_WORK_DIR)/$(MK_LIVESTATUS_DIR)

$(LIVESTATUS_INTERMEDIATE_ARCHIVE):
ifneq ($(CI),)
	@echo "ERROR: Should have been built by source stage (top level: 'make dist')" ; exit 1
endif
	$(MAKE) -C $(REPO_PATH) $(LIVESTATUS_INTERMEDIATE_ARCHIVE)

$(MK_LIVESTATUS_UNPACK): $(LIVESTATUS_INTERMEDIATE_ARCHIVE)
	$(RM) -r $(BUILD_HELPER_DIR)/$*
	$(MKDIR) $(PACKAGE_BUILD_DIR)
	$(TAR_GZ) $< -C $(PACKAGE_BUILD_DIR)
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@

$(MK_LIVESTATUS_BUILD): $(MK_LIVESTATUS_UNPACK) $(RRDTOOL_CACHE_PKG_PROCESS_LIBRARY)

$(MK_LIVESTATUS_INSTALL): $(MK_LIVESTATUS_BUILD) $(PACKAGE_PYTHON3_MODULES_PYTHON_DEPS)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(PACKAGE_DIR)/$(MK_LIVESTATUS)/lq $(DESTDIR)$(OMD_ROOT)/bin
	
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/python3
	install -m 644 $(MK_LIVESTATUS_BUILD_DIR)/api/python/livestatus.py $(DESTDIR)$(OMD_ROOT)/lib/python3
	$(PACKAGE_PYTHON3_MODULES_PYTHON) -m compileall $(DESTDIR)$(OMD_ROOT)/lib/python3/livestatus.py
	
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks
	install -m 755 $(PACKAGE_DIR)/$(MK_LIVESTATUS)/LIVESTATUS_TCP $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(MK_LIVESTATUS)/LIVESTATUS_TCP_ONLY_FROM $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(MK_LIVESTATUS)/LIVESTATUS_TCP_PORT $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(MK_LIVESTATUS)/LIVESTATUS_TCP_TLS $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	$(TOUCH) $@
