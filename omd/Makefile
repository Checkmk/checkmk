# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

include omd.make
include packages/packages.make

-include .config

# debian/rules and RPM specfile (omd.spec) set DESTDIR to install files to
# the package build directories
DESTDIR ?= $(BUILD_BASE_DIR)/dest

PRE_INSTALL := $(BUILD_HELPER_DIR)/pre-install
INSTALL := $(BUILD_HELPER_DIR)/install
RPM_TOPDIR := $(BUILD_BASE_DIR)/rpm/topdir
RPM_BUILDROOT := $(BUILD_BASE_DIR)/rpm/buildroot

# $(SKEL) used in `omd/packages/appliance/appliance.make`.
SKEL := $(DESTDIR)$(OMD_ROOT)/skel
CMA_PKG_VERSION_TXT := $(shell if [ "$(DISTRO_CODE)" = "bookworm" ]; then echo "-4" ; elif [ "$(DISTRO_CODE)" = "buster" ]; then echo "-3"; fi )
ARCH := $(shell uname -m)
CMA_PACKAGE:= $(REPO_PATH)/check-mk-$(EDITION)-$(PKG_VERSION)$(CMA_PKG_VERSION_TXT)-$(ARCH).cma
BOM := bill-of-materials.json

.PHONY: install cma rpm deb clean install-clean venv

# Called while building the .rpm/.deb packages
install: $(INSTALL_GLOBAL) $(DEPS_INSTALL_BAZEL)

# Called by our release system to build appliance packages
cma: $(CMA_PACKAGE)

install-clean:
	rm -rf $(DESTDIR)
	rm -rf $(BUILD_HELPER_DIR)/*-install

$(BUILD_HELPER_DIR):
	$(MKDIR) $(BUILD_HELPER_DIR)

# Prepare clean install environment
$(PRE_INSTALL): $(BUILD_HELPER_DIR)
	$(MKDIR) $(DESTDIR)$(OMD_PHYSICAL_BASE)
# The default physical base for OMD is /opt/omd. This may be changed by
# the user locally, but the logical path for OMD is always /omd. We use
# /omd during installation to make all programs that persist the path
# somehow use the logical path.
	A="$(OMD_PHYSICAL_BASE)" ; ln -sfn $${A:1} $(DESTDIR)/omd
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/omd
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/diskspace
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/man/man1
	$(call log_time,$@,done)
	touch $@

$(INSTALL_LOG_TARGETS): %-log: %
	$(call log_time,$@,done)

$(INSTALL): $(PRE_INSTALL) $(INSTALL_LOG_TARGETS)
	$(TOUCH) $@

omd.spec: omd.spec.in
	sed -e 's/^Requires:.*/Requires:        $(OS_PACKAGES)/' \
	    -e 's/%{version}/$(OMD_VERSION)/g' \
	    -e "s/%{pkg_version}/$(PKG_VERSION)/g" \
	    -e 's/%{edition}/$(EDITION)/g' \
	    -e 's/^Version:.*/Version: $(DISTRO_CODE)/' \
	    -e 's/^Release:.*/Release: $(OMD_SERIAL)/' \
	    -e 's#@APACHE_CONFDIR@#$(APACHE_CONF_DIR)#g' \
	    -e 's#@APACHE_NAME@#$(APACHE_INIT_NAME)#g' \
	    omd.spec.in > omd.spec
	if [ "$(EDITION)" =  "community" ]; then \
	    sed -i '/icmpsender/d;/icmpreceiver/d' omd.spec ; \
	fi

# Called by our release system to build RPM packages
# To make incremental builds possible, e.g. for testing, remove the install-clean target
rpm: install-clean omd.spec
	$(MKDIR) $(RPM_TOPDIR)/{SOURCES,BUILD,RPMS,SRPMS,SPECS}
	# NO_BRP_STALE_LINK_ERROR ignores errors when symlinking from skel to
	# share,lib,bin because the link has a invalid target until the site is created
	# NO_BRP_CHECK_RPATH ignores errors with the compiled python2.7 binary which
	# has a rpath hard coded to the OMD shipped libpython2.7.
	NO_BRP_CHECK_RPATH="yes" \
	NO_BRP_STALE_LINK_ERROR="yes" \
	REPO_PATH=$(REPO_PATH) \
	rpmbuild -bb --define "_topdir $(RPM_TOPDIR)" \
	     --buildroot=$(RPM_BUILDROOT) omd.spec
	mv -v $(RPM_TOPDIR)/RPMS/*/*.rpm $(REPO_PATH)
	rm -rf $(RPM_TOPDIR) $(RPM_BUILDROOT)

# Please note: APPLIANCE_*_CMA are defined in omd/packages/appliance/appliance.make
$(APPLIANCE_INSTALL_CMA): $(PRE_INSTALL)

# Please note: APPLIANCE_*_CMA are defined in omd/packages/appliance/appliance.make
$(CMA_PACKAGE): $(APPLIANCE_INSTALL_CMA) install
	# Create info file to mark minimal cma firmware version requirement
	@if [ "$(DISTRO_CODE)" = "bookworm" ]; then \
	    MIN_VERSION=1.7.0 ; \
	elif [ "$(DISTRO_CODE)" = "buster" ]; then \
	    MIN_VERSION=1.5.0 ; \
	else \
	    echo "ERROR: Unsupported CMA platform ($(DISTRO_CODE))" ; \
	    exit 1 ; \
	fi ; \
	echo -e "MIN_VERSION=$$MIN_VERSION\n" > $(DESTDIR)/opt/omd/versions/$(OMD_VERSION)/cma.info

	tar czf $@ \
	    --owner=root \
	    --group=root \
	    -C $(DESTDIR)/opt/omd/versions/ \
	    $(OMD_VERSION)

clean: install-clean
	$(RM) -r $(BUILD_HELPER_DIR)
	$(RM) -r $(BUILD_BASE_DIR)
	$(RM) -r $(PACKAGE_BUILD_DIR)
