LIBGSF := libgsf
LIBGSF_VERS := 1.14.44
LIBGSF_DIR := $(LIBGSF)-$(LIBGSF_VERS)

LIBGSF_BUILD := $(BUILD_HELPER_DIR)/$(LIBGSF_DIR)-build
LIBGSF_INSTALL := $(BUILD_HELPER_DIR)/$(LIBGSF_DIR)-install
LIBGSF_UNPACK := $(BUILD_HELPER_DIR)/$(LIBGSF_DIR)-unpack

.PHONY: $(LIBGSF)-build $(LIBGSF)-install $(LIBGSF)-skel $(LIBGSF)-clean

$(LIBGSF): $(LIBGSF_BUILD)

$(LIBGSF)-install: $(LIBGSF_INSTALL)


ifneq ($(filter $(DISTRO_CODE),sles15 sles15sp1 sles15sp2 sles15sp3),)
$(LIBGSF_BUILD): $(LIBGSF_UNPACK)
	cd $(LIBGSF_DIR) && ./configure --prefix=$(OMD_ROOT)
	$(MAKE) -C $(LIBGSF_DIR)
# Package msitools needs some stuff during the build.
	$(MAKE) -C $(LIBGSF_DIR) prefix=$(PACKAGE_LIBGSF_DESTDIR) install
	$(TOUCH) $@
else
$(LIBGSF_BUILD):
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@
endif

$(LIBGSF_INSTALL): $(LIBGSF_BUILD)
ifneq ($(filter $(DISTRO_CODE),sles15 sles15sp1 sles15sp2 sles15sp3),)
	$(MAKE) DESTDIR=$(DESTDIR) -C $(LIBGSF_DIR) install
endif
	$(TOUCH) $@

$(LIBGSF)-skel:

$(LIBGSF)-clean:
	rm -rf $(LIBGSF_DIR) $(BUILD_HELPER_DIR)/$(LIBGSF_DIR)*
