HEIRLOOM_MAILX := heirloom-mailx

HEIRLOOM_MAILX_BUILD := $(BUILD_HELPER_DIR)/$(HEIRLOOM_MAILX)-build
HEIRLOOM_MAILX_INSTALL := $(BUILD_HELPER_DIR)/$(HEIRLOOM_MAILX)-install

HEIRLOOM_MAILX_BUILD_DIR := $(BAZEL_BIN_EXT)/_main~_repo_rules~heirloom-mailx/heirloom-mailx

.PHONY: $(HEIRLOOM_MAILX_BUILD)
$(HEIRLOOM_MAILX_BUILD):
	bazel build @$(HEIRLOOM_MAILX)//:$(HEIRLOOM_MAILX)

.PHONY: $(HEIRLOOM_MAILX_INSTALL)
$(HEIRLOOM_MAILX_INSTALL): $(HEIRLOOM_MAILX_BUILD)
	install -m 755 $(HEIRLOOM_MAILX_BUILD_DIR)/bin/mailx $(DESTDIR)$(OMD_ROOT)/bin/heirloom-mailx
	ln -sfn heirloom-mailx $(DESTDIR)$(OMD_ROOT)/bin/mail
	install -m 644 $(HEIRLOOM_MAILX_BUILD_DIR)/share/man/man1/mailx.1 $(DESTDIR)$(OMD_ROOT)/share/man/man1/heirloom-mailx.1
	gzip -f $(DESTDIR)$(OMD_ROOT)/share/man/man1/heirloom-mailx.1
