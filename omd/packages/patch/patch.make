PATCH := patch
PATCH_VERS := 2.7.6
PATCH_DIR := $(PATCH)-$(PATCH_VERS)

PATCH_BUILD := $(BUILD_HELPER_DIR)/$(PATCH_DIR)-build
PATCH_INSTALL := $(BUILD_HELPER_DIR)/$(PATCH_DIR)-install

$(PATCH_BUILD):
	$(BAZEL_BUILD) @patch//:build

$(PATCH_INSTALL): $(PATCH_BUILD)
	$(RSYNC) --chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rwx,Fg=rx,Fo=rx $(BAZEL_BIN)/patch/bin $(DESTDIR)$(OMD_ROOT)/
	$(RSYNC) --chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rw,Fg=r,Fo=r $(BAZEL_BIN)/patch/share $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
