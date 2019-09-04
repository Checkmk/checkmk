MSITOOLS := msitools
MSITOOLS_VERS := 0.94
MSITOOLS_DIR := msitools-$(MSITOOLS_VERS)

LCAB_VERSION := 1.0b12
LCAB_DIR     := lcab-$(LCAB_VERSION)

MSITOOLS_BUILD := $(BUILD_HELPER_DIR)/$(MSITOOLS_DIR)-build
MSITOOLS_INSTALL := $(BUILD_HELPER_DIR)/$(MSITOOLS_DIR)-install
MSITOOLS_PATCHING := $(BUILD_HELPER_DIR)/$(MSITOOLS_DIR)-patching
.PHONY: skel

$(MSITOOLS): $(MSITOOLS_BUILD)

$(MSITOOLS)-install: $(MSITOOLS_INSTALL)

$(MSITOOLS_BUILD): $(LIBGSF_BUILD) $(MSITOOLS_PATCHING) $(BUILD_HELPER_DIR)/$(LCAB_DIR)-unpack
	cd $(MSITOOLS_DIR) && GSF_LIBS="$(PACKAGE_LIBGSF_LDFLAGS)" GSF_CFLAGS="$(PACKAGE_LIBGSF_CFLAGS)" ./configure --prefix=$(OMD_ROOT)
	$(MAKE) -C $(MSITOOLS_DIR)/libmsi
	$(MAKE) -C $(MSITOOLS_DIR) msibuild msiinfo
	cd $(LCAB_DIR) && ./configure && $(MAKE)
	$(TOUCH) $@

$(MSITOOLS_INSTALL): $(MSITOOLS_BUILD)
	echo $(DESTDIR)
	install -m 755 $(MSITOOLS_DIR)/.libs/msiinfo $(DESTDIR)$(OMD_ROOT)/bin ; \
	install -m 755 $(MSITOOLS_DIR)/.libs/msibuild $(DESTDIR)$(OMD_ROOT)/bin ; \
	install -m 755 $(LCAB_DIR)/lcab $(DESTDIR)$(OMD_ROOT)/bin ; \
	install -m 755 $(MSITOOLS_DIR)/libmsi/.libs/libmsi.so* $(DESTDIR)$(OMD_ROOT)/lib ; \
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows ; \
	install -m 644 $(PACKAGE_DIR)/$(MSITOOLS)/*.msi $(DESTDIR)$(OMD_ROOT)/share/check_mk/agents/windows ; \
	$(TOUCH) $@

$(MSITOOLS)-skel:

$(MSITOOLS)-clean:
	$(RM) -r $(MSITOOLS_DIR) $(LCAB_DIR) $(BUILD_HELPER_DIR)/$(MSITOOLS)* $(BUILD_HELPER_DIR)/$(LCAB_DIR)*
