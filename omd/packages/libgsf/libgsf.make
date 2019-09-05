LIBGSF := libgsf
LIBGSF_VERS := 1.14.46
LIBGSF_DIR := $(LIBGSF)-$(LIBGSF_VERS)

LIBGSF_BUILD := $(BUILD_HELPER_DIR)/$(LIBGSF_DIR)-build
LIBGSF_INSTALL := $(BUILD_HELPER_DIR)/$(LIBGSF_DIR)-install
LIBGSF_UNPACK := $(BUILD_HELPER_DIR)/$(LIBGSF_DIR)-unpack

.PHONY: $(LIBGSF)-build $(LIBGSF)-install $(LIBGSF)-skel $(LIBGSF)-clean

$(LIBGSF): $(LIBGSF_BUILD)

$(LIBGSF)-install: $(LIBGSF_INSTALL)


$(LIBGSF_BUILD): $(LIBGSF_UNPACK)
	cd $(LIBGSF_DIR) && ./configure --prefix=$(OMD_ROOT)
	$(MAKE) -C $(LIBGSF_DIR)
# Package msitools needs some stuff during the build.
	$(MAKE) -C $(LIBGSF_DIR) prefix=$(PACKAGE_LIBGSF_DESTDIR) install
	$(TOUCH) $@

$(LIBGSF_INSTALL): $(LIBGSF_BUILD)
	$(MAKE) DESTDIR=$(DESTDIR) -C $(LIBGSF_DIR) install
	$(TOUCH) $@

$(LIBGSF)-skel:

$(LIBGSF)-clean:
	rm -rf $(LIBGSF_DIR) $(BUILD_HELPER_DIR)/$(LIBGSF_DIR)*
