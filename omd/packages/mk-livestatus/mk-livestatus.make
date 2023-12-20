MK_LIVESTATUS := mk-livestatus
MK_LIVESTATUS_DIR := $(MK_LIVESTATUS)-$(CMK_VERSION)

# It is used from top-level Makefile and this makefile as an intermediate step.
# We should end up with one central place to care for packaging our files
# without the need to have shared logic between like this.
include ../artifacts.make

#MK_LIVESTATUS_UNPACK := $(BUILD_HELPER_DIR)/$(MK_LIVESTATUS_DIR)-unpack
#MK_LIVESTATUS_BUILD := $(BUILD_HELPER_DIR)/$(MK_LIVESTATUS_DIR)-build
MK_LIVESTATUS_INSTALL := $(BUILD_HELPER_DIR)/$(MK_LIVESTATUS_DIR)-install

#MK_LIVESTATUS_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(MK_LIVESTATUS_DIR)
#MK_LIVESTATUS_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(MK_LIVESTATUS_DIR)
#MK_LIVESTATUS_WORK_DIR := $(PACKAGE_WORK_DIR)/$(MK_LIVESTATUS_DIR)


$(MK_LIVESTATUS_INSTALL):
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(PACKAGE_DIR)/$(MK_LIVESTATUS)/lq $(DESTDIR)$(OMD_ROOT)/bin
	
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks
	install -m 755 $(PACKAGE_DIR)/$(MK_LIVESTATUS)/LIVESTATUS_TCP $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(MK_LIVESTATUS)/LIVESTATUS_TCP_ONLY_FROM $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(MK_LIVESTATUS)/LIVESTATUS_TCP_PORT $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	install -m 755 $(PACKAGE_DIR)/$(MK_LIVESTATUS)/LIVESTATUS_TCP_TLS $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/
	$(TOUCH) $@
