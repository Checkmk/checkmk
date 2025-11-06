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
ifneq ($(filter sles% el%,$(DISTRO_CODE)),)
$(XINETD_BUILD):
	$(BAZEL_BUILD) @xinetd//:xinetd
endif

#$(XINETD_INTERMEDIATE_INSTALL): $(XINETD_BUILD)
#ifneq ($(filter sles% el9,$(DISTRO_CODE)),)
#	$(MKDIR) $(XINETD_INSTALL_DIR)/bin
#	install -m 755 $(XINETD_BUILD_DIR)/xinetd $(XINETD_INSTALL_DIR)/bin
#
#	$(MKDIR) $(XINETD_INSTALL_DIR)/share/man/man5
#	install -m 644 $(XINETD_BUILD_DIR)/man/xinetd.log.5 $(XINETD_INSTALL_DIR)/share/man/man5
#	install -m 644 $(XINETD_BUILD_DIR)/man/xinetd.conf.5 $(XINETD_INSTALL_DIR)/share/man/man5
#	$(MKDIR) $(XINETD_INSTALL_DIR)/share/man/man8/
#	install -m 644 $(XINETD_BUILD_DIR)/man/xinetd.8 $(XINETD_INSTALL_DIR)/share/man/man8
#
#	$(MKDIR) $(XINETD_INSTALL_DIR)/share/doc/xinetd
#	install -m 644 $(XINETD_BUILD_DIR)/CHANGELOG $(XINETD_INSTALL_DIR)/share/doc/xinetd
#	install -m 644 $(XINETD_BUILD_DIR)/COPYRIGHT $(XINETD_INSTALL_DIR)/share/doc/xinetd
#	install -m 644 $(XINETD_BUILD_DIR)/README.md $(XINETD_INSTALL_DIR)/share/doc/xinetd
#	$(TOUCH) $@
#else
#$(XINETD_INTERMEDIATE_INSTALL):
#	$(TOUCH) $@
#endif

.PHONY: $(XINETD_INSTALL)
ifneq ($(filter sles% el%,$(DISTRO_CODE)),)
$(XINETD_INSTALL): $(XINETD_BUILD)
	$(RSYNC) --chmod=u+w $(BAZEL_BIN_EXT)/$(XINETD)/$(XINETD)/ $(DESTDIR)$(OMD_ROOT)/
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/doc/xinetd/*
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/man/man5/xinetd.*
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/man/man8/xinetd.8
else
$(XINETD_INSTALL):
endif
