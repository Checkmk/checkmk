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

# $(SKEL) used in `omd/packages/appliance/appliance.make`.
SKEL := $(DESTDIR)$(OMD_ROOT)/skel
CMA_PKG_VERSION_TXT := $(shell if [ "$(DISTRO_CODE)" = "bookworm" ]; then echo "-4" ; elif [ "$(DISTRO_CODE)" = "buster" ]; then echo "-3"; fi )
ARCH := $(shell uname -m)
CMA_PACKAGE:= $(REPO_PATH)/check-mk-$(EDITION)-$(PKG_VERSION)$(CMA_PKG_VERSION_TXT)-$(ARCH).cma
BOM := bill-of-materials.json

.PHONY: install cma clean install-clean venv

# Called while building the cma / dist packages
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
