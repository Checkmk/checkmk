MOD_AUTH_MELLON := mod_auth_mellon
MOD_AUTH_MELLON_VERS := 0.17.0
MOD_AUTH_MELLON_DIR := $(MOD_AUTH_MELLON)-$(MOD_AUTH_MELLON_VERS)

MOD_AUTH_MELLON_BUILD := $(BUILD_HELPER_DIR)/$(MOD_AUTH_MELLON_DIR)-build
MOD_AUTH_MELLON_UNPACK := $(BUILD_HELPER_DIR)/$(MOD_AUTH_MELLON_DIR)-unpack
MOD_AUTH_MELLON_INSTALL := $(BUILD_HELPER_DIR)/$(MOD_AUTH_MELLON_DIR)-install

#MOD_AUTH_MELLON_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(MOD_AUTH_MELLON_DIR)
MOD_AUTH_MELLON_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(MOD_AUTH_MELLON_DIR)
#MOD_AUTH_MELLON_WORK_DIR := $(PACKAGE_WORK_DIR)/$(MOD_AUTH_MELLON_DIR)

$(MOD_AUTH_MELLON): $(MOD_AUTH_MELLON_BUILD)

$(MOD_AUTH_MELLON)-unpack: $(MOD_AUTH_MELLON_UNPACK)

ifeq ($(filter $(DISTRO_CODE),sles15 sles12sp3 sles12sp4),)
$(MOD_AUTH_MELLON_BUILD): $(MOD_AUTH_MELLON_UNPACK) $(LASSO_INTERMEDIATE_INSTALL)
	export LASSO_DIR="$(LASSO_DIR)" \
	&& sed -i "s|^prefix=$(OMD_ROOT)$$|prefix=$(INTERMEDIATE_INSTALL_BASE)/$(LASSO_DIR)/$(OMD_ROOT)|" $(INTERMEDIATE_INSTALL_BASE)/$(LASSO_DIR)/$(OMD_ROOT)/lib/pkgconfig/lasso.pc
	cd $(MOD_AUTH_MELLON_BUILD_DIR) \
	&& echo $(MOD_AUTH_MELLON_VERS) > .tarball-version \
      	&& export PKG_CONFIG_PATH="$(INTERMEDIATE_INSTALL_BASE)/$(LASSO_DIR)/$(OMD_ROOT)/lib/pkgconfig" \
        && ./autogen.sh noconfig \
        && ./configure \
	&& $(MAKE)
	$(TOUCH) $@
else
$(MOD_AUTH_MELLON_BUILD):
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@
endif

$(MOD_AUTH_MELLON_INSTALL): $(MOD_AUTH_MELLON_BUILD)
ifeq ($(filter $(DISTRO_CODE),sles15 sles12sp3 sles12sp4),)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	cp $(MOD_AUTH_MELLON_BUILD_DIR)/.libs/mod_auth_mellon.so $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	chmod 644 $(DESTDIR)$(OMD_ROOT)/lib/apache/modules/mod_auth_mellon.so
	cp $(MOD_AUTH_MELLON_BUILD_DIR)/mellon_create_metadata.sh $(DESTDIR)$(OMD_ROOT)/bin/mellon_create_metadata
	chmod 644 $(DESTDIR)$(OMD_ROOT)/bin/mellon_create_metadata
endif
	$(TOUCH) $@

$(MOD_AUTH_MELLON)_download:
	wget https://github.com/latchset/mod_auth_mellon/releases/download/v$(MOD_AUTH_MELLON_VERS)/mod_auth_mellon-$(MOD_AUTH_MELLON_VERS).tar.gz

