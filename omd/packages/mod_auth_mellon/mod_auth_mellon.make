MOD_AUTH_MELLON := mod_auth_mellon
MOD_AUTH_MELLON_VERS := 0.18.0
MOD_AUTH_MELLON_DIR := $(MOD_AUTH_MELLON)-$(MOD_AUTH_MELLON_VERS)

MOD_AUTH_MELLON_BUILD := $(BUILD_HELPER_DIR)/$(MOD_AUTH_MELLON_DIR)-build
MOD_AUTH_MELLON_UNPACK := $(BUILD_HELPER_DIR)/$(MOD_AUTH_MELLON_DIR)-unpack
MOD_AUTH_MELLON_INSTALL := $(BUILD_HELPER_DIR)/$(MOD_AUTH_MELLON_DIR)-install

#MOD_AUTH_MELLON_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(MOD_AUTH_MELLON_DIR)
MOD_AUTH_MELLON_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(MOD_AUTH_MELLON_DIR)
#MOD_AUTH_MELLON_WORK_DIR := $(PACKAGE_WORK_DIR)/$(MOD_AUTH_MELLON_DIR)

$(MOD_AUTH_MELLON): $(MOD_AUTH_MELLON_BUILD)

$(MOD_AUTH_MELLON)-unpack: $(MOD_AUTH_MELLON_UNPACK)

ifeq ($(filter sles%,$(DISTRO_CODE)),)
$(MOD_AUTH_MELLON_BUILD): $(MOD_AUTH_MELLON_UNPACK) $(LASSO_CACHE_PKG_PROCESS)
	export LASSO_DIR="$(LASSO_DIR)" \
	&& sed -i "s|^prefix=$$|prefix=$(LASSO_INSTALL_DIR)|" $(LASSO_INSTALL_DIR)/lib/pkgconfig/lasso.pc
	cd $(MOD_AUTH_MELLON_BUILD_DIR) \
	&& echo $(MOD_AUTH_MELLON_VERS) > .tarball-version \
      	&& export PKG_CONFIG_PATH="$(LASSO_INSTALL_DIR)/lib/pkgconfig" \
        && ./autogen.sh noconfig \
        && ./configure \
	&& $(MAKE) \
	&& sed -i "s|^prefix=$(LASSO_INSTALL_DIR)$$|prefix=|" $(LASSO_INSTALL_DIR)/lib/pkgconfig/lasso.pc
	$(TOUCH) $@
else
$(MOD_AUTH_MELLON_BUILD):
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@
endif

$(MOD_AUTH_MELLON_INSTALL): $(MOD_AUTH_MELLON_BUILD)
ifeq ($(filter sles%,$(DISTRO_CODE)),)
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	cp $(MOD_AUTH_MELLON_BUILD_DIR)/.libs/mod_auth_mellon.so $(DESTDIR)$(OMD_ROOT)/lib/apache/modules
	chmod 644 $(DESTDIR)$(OMD_ROOT)/lib/apache/modules/mod_auth_mellon.so
	cp $(MOD_AUTH_MELLON_BUILD_DIR)/mellon_create_metadata.sh $(DESTDIR)$(OMD_ROOT)/bin/mellon_create_metadata
	chmod 644 $(DESTDIR)$(OMD_ROOT)/bin/mellon_create_metadata
endif
	$(TOUCH) $@

$(MOD_AUTH_MELLON)_download:
	wget https://github.com/latchset/mod_auth_mellon/releases/download/v$(MOD_AUTH_MELLON_VERS)/mod_auth_mellon-$(MOD_AUTH_MELLON_VERS).tar.gz

