STUNNEL := stunnel

STUNNEL_BUILD := $(BUILD_HELPER_DIR)/$(STUNNEL)-build
STUNNEL_INSTALL := $(BUILD_HELPER_DIR)/$(STUNNEL)-install

.PHONY: $(STUNNEL_BUILD)
$(STUNNEL_BUILD):
	$(BAZEL_CMD) build @$(STUNNEL)//:$(STUNNEL)
	$(BAZEL_CMD) build @$(STUNNEL)//:skel

.PHONY: $(STUNNEL_INSTALL)
$(STUNNEL_INSTALL): $(STUNNEL_BUILD)
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(STUNNEL)/$(STUNNEL)/bin $(DESTDIR)$(OMD_ROOT)/
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(STUNNEL)/$(STUNNEL)/lib $(DESTDIR)$(OMD_ROOT)/
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(STUNNEL)/$(STUNNEL)/share/$(STUNNEL).bash $(DESTDIR)$(OMD_ROOT)/skel/etc/bash_completion.d/
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(STUNNEL)/skel/ $(DESTDIR)$(OMD_ROOT)/skel
	cd $(DESTDIR)$(OMD_ROOT)/skel/etc/rc.d/ && $(LN) -sf ../init.d/$(STUNNEL) 85-$(STUNNEL)
	chmod 640 $(DESTDIR)$(OMD_ROOT)/skel/etc/logrotate.d/$(STUNNEL)
	chmod 640 $(DESTDIR)$(OMD_ROOT)/skel/etc/$(STUNNEL)/server.conf
	find $(DESTDIR)$(OMD_ROOT)/skel -name ".gitignore" -delete
