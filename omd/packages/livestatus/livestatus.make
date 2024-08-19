LIVESTATUS := livestatus
LIVESTATUS_PACKAGE := packages/livestatus

LIVESTATUS_BUILD := $(BUILD_HELPER_DIR)/livestatus-build
LIVESTATUS_INSTALL := $(BUILD_HELPER_DIR)/livestatus-install

.PHONY: $(LIVESTATUS_BUILD)
$(LIVESTATUS_BUILD):
ifneq ($(filter $(DISTRO_CODE),el8 el9 sles15sp3 sles15sp4 sles15sp5),)
	BAZEL_EXTRA_ARGS="--define non-standard-glib-path=true" $(BAZEL_BUILD) //$(LIVESTATUS_PACKAGE):$(LIVESTATUS)_shared
else
	$(BAZEL_BUILD) //$(LIVESTATUS_PACKAGE):$(LIVESTATUS)_shared
endif

$(LIVESTATUS_INSTALL): $(LIVESTATUS_BUILD)
	install -m 644 $(BAZEL_BIN)/$(LIVESTATUS_PACKAGE)/liblivestatus.so $(DESTDIR)$(OMD_ROOT)/lib/liblivestatus.so.0.1
	ln -sf liblivestatus.so.0.1 $(DESTDIR)$(OMD_ROOT)/lib/liblivestatus.so.0
	ln -sf liblivestatus.so.0 $(DESTDIR)$(OMD_ROOT)/lib/liblivestatus.so
	$(TOUCH) $@
