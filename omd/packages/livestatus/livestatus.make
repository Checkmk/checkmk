LIVESTATUS := livestatus
LIVESTATUS_VERS := 0.1
LIVESTATUS_DIR := $(LIVESTATUS)-$(LIVESTATUS_VERS)
LIVESTATUS_PACKAGE := $(REPO_PATH)/packages/livestatus

LIVESTATUS_BUILD := $(BUILD_HELPER_DIR)/livestatus-build
LIVESTATUS_INSTALL := $(BUILD_HELPER_DIR)/livestatus-install

$(LIVESTATUS_BUILD):
	$(LIVESTATUS_PACKAGE)/run-ci --build
	$(TOUCH) $@

$(LIVESTATUS_INSTALL): $(LIVESTATUS_BUILD)
	install -m 755 $(LIVESTATUS_PACKAGE)/build/src/liblivestatus.so.0.1 $(DESTDIR)$(OMD_ROOT)/lib/
	ln -sf liblivestatus.so.0.1 $(DESTDIR)$(OMD_ROOT)/lib/liblivestatus.so.0
	ln -sf liblivestatus.so.0 $(DESTDIR)$(OMD_ROOT)/lib/liblivestatus.so
	$(TOUCH) $@
