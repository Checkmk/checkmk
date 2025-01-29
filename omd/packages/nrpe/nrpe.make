# This package contains the NRPE library (https://github.com/NagiosEnterprises/nrpe)
NRPE := nrpe

NRPE_BUILD := $(BUILD_HELPER_DIR)/$(NRPE)-build
NRPE_INSTALL := $(BUILD_HELPER_DIR)/$(NRPE)-install

NRPE_BUILD_DIR := $(BAZEL_BIN_EXT)/$(NRPE)/$(NRPE)

.PHONY: $(NRPE_BUILD)
$(NRPE_BUILD):
	# run the Bazel build process which does all the dependency stuff
	$(BAZEL_CMD) build @$(NRPE)//:$(NRPE)

.PHONY: $(NRPE_INSTALL)
$(NRPE_INSTALL): $(NRPE_BUILD)
	$(RSYNC) --chmod=u+w $(NRPE_BUILD_DIR)/ $(DESTDIR)$(OMD_ROOT)/
