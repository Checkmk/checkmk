UNIXCAT := unixcat
UNIXCAT_DIR := $(UNIXCAT)
UNIXCAT_PACKAGE := $(REPO_PATH)/packages/unixcat

UNIXCAT_BUILD := $(BUILD_HELPER_DIR)/unixcat-build
UNIXCAT_INSTALL := $(BUILD_HELPER_DIR)/unixcat-install

$(UNIXCAT_BUILD):
	$(UNIXCAT_PACKAGE)/run --build
	$(TOUCH) $@

$(UNIXCAT_INSTALL): $(UNIXCAT_BUILD)
	install -m 755 $(UNIXCAT_PACKAGE)/build/src/unixcar $(DESTDIR)$(OMD_ROOT)/bin/
	$(TOUCH) $@
