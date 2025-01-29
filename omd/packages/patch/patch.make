PATCH := patch
PATCH_DIR := $(PATCH)

PATCH_BUILD := $(BUILD_HELPER_DIR)/$(PATCH_DIR)-build
PATCH_INSTALL := $(BUILD_HELPER_DIR)/$(PATCH_DIR)-install

.PHONY: $(PATCH_BUILD)
$(PATCH_BUILD):
	$(BAZEL_CMD) build @$(PATCH)//:build

.PHONY: $(PATCH_INSTALL)
$(PATCH_INSTALL): $(PATCH_BUILD)
	$(RSYNC) --chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rwx,Fg=rx,Fo=rx $(BAZEL_BIN_EXT)/_main~_repo_rules~patch/bin $(DESTDIR)$(OMD_ROOT)/
	$(RSYNC) --chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rw,Fg=r,Fo=r $(BAZEL_BIN_EXT)/_main~_repo_rules~patch/share $(DESTDIR)$(OMD_ROOT)/
