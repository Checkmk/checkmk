MSITOOLS := msitools

MSITOOLS_BUILD := $(BUILD_HELPER_DIR)/$(MSITOOLS)-build
MSITOOLS_INSTALL := $(BUILD_HELPER_DIR)/$(MSITOOLS)-install

MSITOOLS_BUILD_DIR := $(BAZEL_BIN_EXT)/$(MSITOOLS)/$(MSITOOLS)

$(MSITOOLS_BUILD):
ifneq ($(filter $(DISTRO_CODE),sles15 sles15sp3 sles15sp4 sles15sp5),)
	BAZEL_EXTRA_ARGS="--define omd-libgsf=true" $(BAZEL_BUILD) @msitools//:msitools
else
	$(BAZEL_BUILD) @msitools//:msitools
endif

$(MSITOOLS_INSTALL): $(MSITOOLS_BUILD)
	$(RSYNC) --chmod=u+w $(MSITOOLS_BUILD_DIR)/ $(DESTDIR)$(OMD_ROOT)/
