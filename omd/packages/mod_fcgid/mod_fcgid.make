MOD_FCGID := mod_fcgid
MOD_FCGID_DIR := $(MOD_FCGID)

MOD_FCGID_BUILD := $(BUILD_HELPER_DIR)/$(MOD_FCGID_DIR)-build
MOD_FCGID_INSTALL := $(BUILD_HELPER_DIR)/$(MOD_FCGID_DIR)-install

$(MOD_FCGID_BUILD):
	$(BAZEL_BUILD) @$(MOD_FCGID)//:$(MOD_FCGID)

$(MOD_FCGID_INSTALL): $(MOD_FCGID_BUILD)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	$(RSYNC) --chmod=644 $(BAZEL_BIN)/$(MOD_FCGID)/$(MOD_FCGID)/lib/mod_fcgid.so $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	$(MKDIR) $(SKEL)/tmp/apache/fcgid_sock
	$(TOUCH) $@
