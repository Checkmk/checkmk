MOD_FCGID := mod_fcgid
MOD_FCGID_VERS := 2.3.9
MOD_FCGID_DIR := $(MOD_FCGID)-$(MOD_FCGID_VERS)

# Try to find the apxs binary
ifneq ("$(wildcard /usr/sbin/apxs)","")
    APXS := /usr/sbin/apxs
endif
ifneq ("$(wildcard /usr/sbin/apxs2)","")
    APXS := /usr/sbin/apxs2
endif
ifneq ("$(wildcard /usr/bin/apxs2)","")
    APXS := /usr/bin/apxs2
endif

MOD_FCGID_BUILD := $(BUILD_HELPER_DIR)/$(MOD_FCGID_DIR)-build
MOD_FCGID_INSTALL := $(BUILD_HELPER_DIR)/$(MOD_FCGID_DIR)-install
MOD_FCGID_PATCHING := $(BUILD_HELPER_DIR)/$(MOD_FCGID_DIR)-patching
MOD_FCGID_SKEL := $(BUILD_HELPER_DIR)/$(MOD_FCGID_DIR)-skel

.PHONY: $(MOD_FCGID) $(MOD_FCGID)-install $(MOD_FCGID)-skel $(MOD_FCGID)-clean

$(MOD_FCGID): $(MOD_FCGID_BUILD)

$(MOD_FCGID)-install: $(MOD_FCGID_INSTALL)

$(MOD_FCGID)-skel: $(MOD_FCGID_SKEL)

$(MOD_FCGID_BUILD): $(MOD_FCGID_PATCHING)
	cd $(MOD_FCGID_DIR) && APXS=$(APXS) ./configure.apxs
	CPATH="/usr/include/apache2-worker" $(MAKE) -C $(MOD_FCGID_DIR)
	$(TOUCH) $@

$(MOD_FCGID_INSTALL): $(MOD_FCGID_BUILD)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	cp $(MOD_FCGID_DIR)/modules/fcgid/.libs/mod_fcgid.so $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	chmod 644 $(DESTDIR)$(OMD_ROOT)/lib/apache/modules/mod_fcgid.so
	$(TOUCH) $@

$(MOD_FCGID_SKEL): $(MOD_FCGID_INSTALL)
	$(MKDIR) $(SKEL)/tmp/apache/fcgid_sock
	$(TOUCH) $@

$(MOD_FCGID)-clean:
	$(RM) -r $(MOD_FCGID_DIR) $(BUILD_HELPER_DIR)/$(MOD_FCGID)*
