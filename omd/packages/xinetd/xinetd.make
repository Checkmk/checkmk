# This package has been introduced to fix the installation of Checkmk on SLES
# where it was not possible to get xinetd from official SLES sources. Users either
# had to install an "unsupported" package from third party sources or could not
# use the "livestatus via TCP" option which needs an xinetd instance within the
# site.
#
# To solve this usability issue, we now ship xinetd with Checkmk only for SLES.
# We use the xinetd from https://github.com/openSUSE/xinetd which is also the
# base for the Ubuntu 20.04 packages.

XINETD := xinetd
XINETD_DIR := xinetd
# Increase this to enforce a recreation of the build cache
XINETD_BUILD_ID := 0

XINETD_BUILD := $(BUILD_HELPER_DIR)/$(XINETD_DIR)-build
XINETD_INSTALL := $(BUILD_HELPER_DIR)/$(XINETD_DIR)-install

XINETD_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(XINETD_DIR)

.PHONY: $(XINETD_BUILD)
ifneq ($(filter sles% el9,$(DISTRO_CODE)),)
$(XINETD_BUILD):
	bazel build @$(XINETD)//:$(XINETD)
endif

.PHONY: $(XINETD_INSTALL)
ifneq ($(filter sles% el9,$(DISTRO_CODE)),)
$(XINETD_INSTALL): $(XINETD_BUILD)
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(XINETD)/$(XINETD)/ $(DESTDIR)$(OMD_ROOT)/
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/doc/xinetd/*
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/man/man5/xinetd.*
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/man/man8/xinetd.8
else
$(XINETD_INSTALL):
endif
