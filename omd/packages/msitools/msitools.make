MSITOOLS := msitools

MSITOOLS_BUILD := $(BUILD_HELPER_DIR)/$(MSITOOLS)-build
MSITOOLS_INSTALL := $(BUILD_HELPER_DIR)/$(MSITOOLS)-install

MSITOOLS_BUILD_DIR := $(BAZEL_BIN_EXT)/$(MSITOOLS)/$(MSITOOLS)

.PHONY: $(MSITOOLS_BUILD)
$(MSITOOLS_BUILD):
	# NOTE: this might result in unexpected build behavior, when dependencies of @$(MSITOOLS)//:$(MSITOOLS)
	#       are built somewhere else without --define git-ssl-no-verify=true being specified, likely
	#       resulting in different builds
	$(BAZEL_CMD) build \
	    $(if $(filter $(DISTRO_CODE),sles15 sles15sp1 sles15sp2 sles15sp3 sles15sp4 sles15sp5 sles15sp6),--define omd-libgsf=true) \
	    @$(MSITOOLS)//:$(MSITOOLS)

.PHONY: $(MSITOOLS_INSTALL)
$(MSITOOLS_INSTALL): $(MSITOOLS_BUILD)
	$(RSYNC) --chmod=u+w $(MSITOOLS_BUILD_DIR)/ $(DESTDIR)$(OMD_ROOT)/
