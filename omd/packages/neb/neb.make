NEB := neb
NEB_DIR := $(NEB)
NEB_PACKAGE := packages/$(NEB)

NEB_BUILD := $(BUILD_HELPER_DIR)/neb-build
NEB_INSTALL := $(BUILD_HELPER_DIR)/neb-install

.PHONY: $(NEB_BUILD)
$(NEB_BUILD):
	bazel build //$(NEB_PACKAGE):$(NEB)_shared --cmk_version="$(VERSION)"

$(NEB_INSTALL): $(NEB_BUILD)
	$(MKDIR) -p $(DESTDIR)$(OMD_ROOT)/lib/mk-livestatus
	install -m 644 $(BAZEL_BIN)/$(NEB_PACKAGE)/libneb_shared.so $(DESTDIR)$(OMD_ROOT)/lib/mk-livestatus/livestatus.o
	$(TOUCH) $@
