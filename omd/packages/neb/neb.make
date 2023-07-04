NEB := neb
NEB_DIR := $(NEB)
NEB_PACKAGE := $(REPO_PATH)/packages/neb

NEB_BUILD := $(BUILD_HELPER_DIR)/neb-build
NEB_INSTALL := $(BUILD_HELPER_DIR)/neb-install

$(NEB_BUILD):
	$(NEB_PACKAGE)/run --build
	$(TOUCH) $@

$(NEB_INSTALL): $(NEB_BUILD)
	$(MKDIR) -p $(DESTDIR)$(OMD_ROOT)/lib/mk-livestatus
	install -m 755 $(NEB_PACKAGE)/build/src/libneb.so $(DESTDIR)$(OMD_ROOT)/lib/mk-livestatus/livestatus.o
	$(TOUCH) $@
