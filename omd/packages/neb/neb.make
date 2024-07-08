NEB := neb
NEB_DIR := $(NEB)
NEB_PACKAGE := packages/$(NEB)

NEB_BUILD := $(BUILD_HELPER_DIR)/neb-build
NEB_INSTALL := $(BUILD_HELPER_DIR)/neb-install

.PHONY: $(NEB_BUILD)
$(NEB_BUILD):
ifneq ($(filter $(DISTRO_CODE),el8 el9 sles15sp3 sles15sp4 sles15sp5),)
	BAZEL_EXTRA_ARGS="--define non-standard-glib-path=true" $(BAZEL_BUILD) //$(NEB_PACKAGE):$(NEB)_shared
else
	$(BAZEL_BUILD) //$(NEB_PACKAGE):$(NEB)_shared
endif

$(NEB_INSTALL): $(NEB_BUILD)
	$(MKDIR) -p $(DESTDIR)$(OMD_ROOT)/lib/mk-livestatus
	install -m 644 $(BAZEL_BIN)/$(NEB_PACKAGE)/libneb_shared.so $(DESTDIR)$(OMD_ROOT)/lib/mk-livestatus/livestatus.o
	$(TOUCH) $@
