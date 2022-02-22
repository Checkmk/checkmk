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
XINETD_VERS := 2.3.15.4
XINETD_DIR := xinetd-$(XINETD_VERS)
# Increase this to enforce a recreation of the build cache
XINETD_BUILD_ID := 0

XINETD_UNPACK := $(BUILD_HELPER_DIR)/$(XINETD_DIR)-unpack
XINETD_BUILD := $(BUILD_HELPER_DIR)/$(XINETD_DIR)-build
XINETD_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(XINETD_DIR)-install-intermediate
XINETD_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(XINETD_DIR)-cache-pkg-process
XINETD_INSTALL := $(BUILD_HELPER_DIR)/$(XINETD_DIR)-install

XINETD_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(XINETD_DIR)
XINETD_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(XINETD_DIR)
#XINETD_WORK_DIR := $(PACKAGE_WORK_DIR)/$(XINETD_DIR)

ifneq ($(filter sles%,$(DISTRO_CODE)),)
$(XINETD_BUILD): $(XINETD_UNPACK)
	cd $(XINETD_BUILD_DIR) && \
	    ./configure \
		--prefix="" \
		--with-loadavg \
		--with-libwrap && \
	    $(MAKE)
	$(TOUCH) $@
else
$(XINETD_BUILD):
	$(TOUCH) $@
endif

XINETD_CACHE_PKG_PATH := $(call cache_pkg_path,$(XINETD_DIR),$(XINETD_BUILD_ID))

$(XINETD_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(XINETD_DIR),$(XINETD_BUILD_ID),$(XINETD_INTERMEDIATE_INSTALL))

ifneq ($(filter sles%,$(DISTRO_CODE)),)
$(XINETD_CACHE_PKG_PROCESS): $(XINETD_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(XINETD_CACHE_PKG_PATH),$(XINETD_DIR))
	$(call upload_pkg_archive,$(XINETD_CACHE_PKG_PATH),$(XINETD_DIR),$(XINETD_BUILD_ID))
	$(TOUCH) $@
else
$(XINETD_CACHE_PKG_PROCESS):
	$(TOUCH) $@
endif

$(XINETD_INTERMEDIATE_INSTALL): $(XINETD_BUILD)
ifneq ($(filter sles%,$(DISTRO_CODE)),)
	$(MKDIR) $(XINETD_INSTALL_DIR)/bin
	install -m 755 $(XINETD_BUILD_DIR)/xinetd $(XINETD_INSTALL_DIR)/bin
	
	$(MKDIR) $(XINETD_INSTALL_DIR)/share/man/man5
	install -m 644 $(XINETD_BUILD_DIR)/man/xinetd.log.5 $(XINETD_INSTALL_DIR)/share/man/man5
	install -m 644 $(XINETD_BUILD_DIR)/man/xinetd.conf.5 $(XINETD_INSTALL_DIR)/share/man/man5
	$(MKDIR) $(XINETD_INSTALL_DIR)/share/man/man8/
	install -m 644 $(XINETD_BUILD_DIR)/man/xinetd.8 $(XINETD_INSTALL_DIR)/share/man/man8

	$(MKDIR) $(XINETD_INSTALL_DIR)/share/doc/xinetd
	install -m 644 $(XINETD_BUILD_DIR)/CHANGELOG $(XINETD_INSTALL_DIR)/share/doc/xinetd
	install -m 644 $(XINETD_BUILD_DIR)/COPYRIGHT $(XINETD_INSTALL_DIR)/share/doc/xinetd
	install -m 644 $(XINETD_BUILD_DIR)/README.md $(XINETD_INSTALL_DIR)/share/doc/xinetd
	$(TOUCH) $@
else
$(XINETD_INTERMEDIATE_INSTALL):
	$(TOUCH) $@
endif

ifneq ($(filter sles%,$(DISTRO_CODE)),)
$(XINETD_INSTALL): $(XINETD_CACHE_PKG_PROCESS)
	$(RSYNC) $(XINETD_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
else
$(XINETD_INSTALL):
	$(TOUCH) $@
endif
