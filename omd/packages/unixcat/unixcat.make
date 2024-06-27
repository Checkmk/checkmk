UNIXCAT := unixcat
UNIXCAT_PACKAGE := packages/$(UNIXCAT)

UNIXCAT_BUILD := $(BUILD_HELPER_DIR)/unixcat-build
UNIXCAT_INSTALL := $(BUILD_HELPER_DIR)/unixcat-install

.PHONY: $(UNIXCAT_BUILD)
$(UNIXCAT_BUILD):
ifeq ($(DISTRO_CODE),el8)
	BAZEL_EXTRA_ARGS="--define non-standard-glib-path=true" $(BAZEL_BUILD) //$(UNIXCAT_PACKAGE)
else
	$(BAZEL_BUILD) //$(UNIXCAT_PACKAGE)
endif

$(UNIXCAT_INSTALL): $(UNIXCAT_BUILD)
	install -m 755 $(REPO_PATH)/bazel-bin/$(UNIXCAT_PACKAGE)/$(UNIXCAT) $(DESTDIR)/$(OMD_ROOT)/bin/
	$(TOUCH) $@
