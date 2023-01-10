PATCH := patch
PATCH_VERS := 2.7.6
PATCH_DIR := $(PATCH)-$(PATCH_VERS)

PATCH_BUILD := $(BUILD_HELPER_DIR)/$(PATCH_DIR)-build
PATCH_INSTALL := $(BUILD_HELPER_DIR)/$(PATCH_DIR)-install

$(PATCH_BUILD):
	bazel build @patch//:build
	$(TOUCH) $@

$(PATCH_INSTALL): $(PATCH_CACHE_PKG_PROCESS)
	bazel run @patch//:deploy
	$(RSYNC) --chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rwx,Fg=rx,Fo=rx build/by_bazel/patch/bin $(DESTDIR)$(OMD_ROOT)/
	$(RSYNC) --chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rw,Fg=r,Fo=r build/by_bazel/patch/share $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
