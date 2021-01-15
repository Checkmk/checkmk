LASSO := lasso
LASSO_VERS := 2.6.1.2
LASSO_DIR := $(LASSO)-$(LASSO_VERS)

LASSO_BUILD := $(BUILD_HELPER_DIR)/$(LASSO_DIR)-build
LASSO_UNPACK := $(BUILD_HELPER_DIR)/$(LASSO_DIR)-unpack
LASSO_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(LASSO_DIR)-install-intermediate
LASSO_INSTALL := $(BUILD_HELPER_DIR)/$(LASSO_DIR)-install

#LASSO_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(LASSO_DIR)
LASSO_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(LASSO_DIR)
#LASSO_WORK_DIR := $(PACKAGE_WORK_DIR)/$(LASSO_DIR)

$(LASSO): $(LASSO_BUILD) $(LASSO_INTERMEDIATE_INSTALL)

$(LASSO)-unpack: $(LASSO_UNPACK)

$(LASSO)-int: $(LASSO_INTERMEDIATE_INSTALL)

ifeq ($(filter $(DISTRO_CODE),sles15 sles12sp3 sles12sp4),)
$(LASSO_BUILD): $(LASSO_UNPACK)
	cd $(LASSO_BUILD_DIR) \
	&& echo $(LASSO_VERS) > .tarball-version \
	&& ./autogen.sh noconfig \
        && ./configure --prefix=$(OMD_ROOT) --disable-gtk-doc --enable-static-linking \
	&& $(MAKE)
	$(TOUCH) $@
else
$(LASSO_BUILD):
	$(MKDIR) $(BUILD_HELPER_DIR)
	$(TOUCH) $@
endif

$(LASSO_INTERMEDIATE_INSTALL): $(LASSO_BUILD)
ifeq ($(filter $(DISTRO_CODE),sles15 sles12sp3 sles12sp4),)
	$(MKDIR) $(INTERMEDIATE_INSTALL_BASE)/$(LASSO_DIR)
	$(MAKE) DESTDIR=$(INTERMEDIATE_INSTALL_BASE)/$(LASSO_DIR) -C $(LASSO_BUILD_DIR) install
endif
	$(TOUCH) $@

$(LASSO_INSTALL): $(LASSO_BUILD)
ifeq ($(filter $(DISTRO_CODE),sles15 sles12sp3 sles12sp4),)
	$(MAKE) DESTDIR=$(DESTDIR) \
		-C $(LASSO_BUILD_DIR) install
	if [ -d "$(DESTDIR)/$(OMD_ROOT)/lib64/perl5" ]; then mv $(DESTDIR)/$(OMD_ROOT)/lib64/perl5 $(DESTDIR)/$(OMD_ROOT)/lib/; rm -r $(DESTDIR)/$(OMD_ROOT)/lib64; fi
endif
	$(TOUCH) $@

$(LASSO)_download:
	cd packages/lasso/ \
	&& wget https://repos.entrouvert.org/lasso.git/snapshot/lasso-$(LASSO_VERS).tar.gz
