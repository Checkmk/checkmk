STUNNEL := stunnel
STUNNEL_DIR := $(STUNNEL)-$(CMK_VERSION)

# Attention: copy-n-paste from check_mk/Makefile below...
STUNNEL_INSTALL := $(BUILD_HELPER_DIR)/$(STUNNEL)-install

.PHONY: $(STUNNEL) $(STUNNEL)-install $(STUNNEL)-skel

$(STUNNEL_INSTALL):
	$(TOUCH) $@

$(STUNNEL)-skel:
