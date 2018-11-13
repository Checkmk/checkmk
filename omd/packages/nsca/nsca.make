NSCA := nsca
NSCA_VERS := 2.9.1
NSCA_DIR := $(NSCA)-$(NSCA_VERS)

NSCA_BUILD := $(BUILD_HELPER_DIR)/$(NSCA_DIR)-build
NSCA_INSTALL := $(BUILD_HELPER_DIR)/$(NSCA_DIR)-install
NSCA_PATCHING := $(BUILD_HELPER_DIR)/$(NSCA_DIR)-patching

.PHONY: $(NSCA) $(NSCA)-install $(NSCA)-skel $(NSCA)-build

$(NSCA): $(NSCA_BUILD)

$(NSCA)-install: $(NSCA_INSTALL)

# Configure options for Nagios. Since we want to compile
# as non-root, we use our own user and group for compiling.
# All files will be packaged as user 'root' later anyway.
NSCA_CONFIGUREOPTS = ""

$(NSCA_BUILD): $(NSCA_PATCHING)
	cd $(NSCA_DIR) ; ./configure $(NSCA_CONFIGUREOPTS)
	$(MAKE) -C $(NSCA_DIR) all
	$(TOUCH) $@

$(NSCA_INSTALL): $(NSCA_BUILD)
	install -m 755 $(NSCA_DIR)/src/nsca $(DESTDIR)$(OMD_ROOT)/bin
	install -m 755 $(NSCA_DIR)/src/send_nsca $(DESTDIR)$(OMD_ROOT)/bin

	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/doc/nsca
	install -m 644 $(NSCA_DIR)/README $(DESTDIR)$(OMD_ROOT)/share/doc/nsca
	install -m 644 $(NSCA_DIR)/LEGAL $(DESTDIR)$(OMD_ROOT)/share/doc/nsca
	install -m 644 $(NSCA_DIR)/SECURITY $(DESTDIR)$(OMD_ROOT)/share/doc/nsca
	$(TOUCH) $@

$(NSCA)-skel:

$(NSCA)-clean:
	$(RM) -r $(NSCA_DIR) $(BUILD_HELPER_DIR)/$(NSCA)*
