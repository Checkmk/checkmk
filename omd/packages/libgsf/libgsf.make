LIBGSF := libgsf

LIBGSF_BUILD := $(BUILD_HELPER_DIR)/$(LIBGSF)-build
LIBGSF_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(LIBGSF)-install-intermediate
LIBGSF_INSTALL := $(BUILD_HELPER_DIR)/$(LIBGSF)-install

LIBGSF_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(LIBGSF)
LIBGSF_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(LIBGSF)

$(LIBGSF_BUILD):
ifneq ($(filter $(DISTRO_CODE),sles15 sles15sp1 sles15sp2 sles15sp3 sles15sp4),)
	$(BAZEL_BUILD) @$(LIBGSF)//:$(LIBGSF)
endif

$(LIBGSF_INTERMEDIATE_INSTALL): $(LIBGSF_BUILD)
ifneq ($(filter $(DISTRO_CODE),sles15 sles15sp1 sles15sp2 sles15sp3 sles15sp4),)
	$(MKDIR) $(LIBGSF_INSTALL_DIR)
	$(RSYNC) --chmod=u+w $(BAZEL_BIN)/$(LIBGSF)/$(LIBGSF)/ $(LIBGSF_INSTALL_DIR)/
	# TODO: Linking with force is needed as this target might be executed more than once
	cd $(LIBGSF_INSTALL_DIR)/lib ; \
	    ln -sf libgsf-1.so.114.0.44 libgsf-1.so ;\
	    ln -sf libgsf-1.so.114.0.44 libgsf-1.so.114
endif

$(LIBGSF_INSTALL): $(LIBGSF_INTERMEDIATE_INSTALL)
ifneq ($(filter $(DISTRO_CODE),sles15 sles15sp1 sles15sp2 sles15sp3 sles15sp4),)
	$(RSYNC) $(LIBGSF_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
endif
