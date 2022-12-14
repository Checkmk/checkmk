LIVESTATUS_PACKAGE := $(REPO_PATH)/packages/livestatus

LIVESTATUS_BUILD := $(BUILD_HELPER_DIR)/livestatus-build
LIVESTATUS_INSTALL := $(BUILD_HELPER_DIR)/livestatus-install

$(LIVESTATUS_BUILD):
	$(LIVESTATUS_PACKAGE)/run-ci --build
	$(TOUCH) $@

$(LIVESTATUS_INSTALL): $(LIVESTATUS_BUILD)
	install -m 755 $(LIVESTATUS_PACKAGE)/build/src/liblivestatus.so* $(DESTDIR)$(OMD_ROOT)/lib
	$(TOUCH) $@
