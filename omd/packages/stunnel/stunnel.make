STUNNEL := stunnel

STUNNEL_BUILD := $(BUILD_HELPER_DIR)/$(STUNNEL)-build
STUNNEL_INSTALL := $(BUILD_HELPER_DIR)/$(STUNNEL)-install

.PHONY: $(STUNNEL_BUILD)
$(STUNNEL_BUILD):
	$(BAZEL_CMD) build @$(STUNNEL)//:$(STUNNEL)
	$(BAZEL_CMD) build //omd/packages/stunnel:skel_dir

.PHONY: $(STUNNEL_INSTALL)
$(STUNNEL_INSTALL): $(STUNNEL_BUILD)
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(STUNNEL)/$(STUNNEL)/bin $(DESTDIR)$(OMD_ROOT)/
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(STUNNEL)/$(STUNNEL)/lib $(DESTDIR)$(OMD_ROOT)/
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(STUNNEL)/$(STUNNEL)/share/$(STUNNEL).bash $(DESTDIR)$(OMD_ROOT)/skel/etc/bash_completion.d/
	tar -C $(DESTDIR)$(OMD_ROOT)/skel -xf $(BAZEL_BIN)/omd/packages/stunnel/stunnel-skel.tar.gz
