# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

include omd.make
include $(BUILD_BASE_DIR)/build-helper-files.make

# You can build single packages by calling make <PACKAGENAME>
# e.g.: make nagios rrdtool
#
# You can select a subset of the packages by overriding this
# variable, e.g. make PACKAGES='nagios rrdtool' pack
#
# If you just want to test package building, you can reduce the
# number of packages to just "omd" - to speed up your tests.
# PACKAGES="omd"
#
# Alternatively,
# ```
# cd omd
# PACKAGE=check-cert; make $PWD/build/stamps/$PACKAGE-build
# ```
#
# You can also create a file named .config and override the
# PACKAGES variable there to customzie the list of packages.

PACKAGES := \
    apache-omd \
    check_mk \
    omd

ifeq ($(EDITION),enterprise)
PACKAGES += enterprise
endif
ifeq ($(EDITION),managed)
PACKAGES += enterprise
PACKAGES += cloud
PACKAGES += managed
PACKAGES += otel-collector
endif
ifeq ($(EDITION),cloud)
PACKAGES += enterprise
PACKAGES += cloud
PACKAGES += otel-collector
endif
ifeq ($(EDITION),saas)
PACKAGES += enterprise
PACKAGES += cloud
PACKAGES += saas
endif

BUILD_TARGET_VARS := $(call package_target_prefix,$(PACKAGES))
INSTALL_TARGETS := $(foreach package,$(addsuffix _INSTALL,$(BUILD_TARGET_VARS)),$($(package)))
INSTALL_LOG_TARGETS := $(foreach package,$(INSTALL_TARGETS),$(addsuffix -log,$(package)))
CACHE_PKG_PROCESS_TARGETS := $(foreach package,$(addsuffix _CACHE_PKG_PROCESS,$(BUILD_TARGET_VARS)),$($(package)))

PRE_INSTALL := $(BUILD_HELPER_DIR)/pre-install
INSTALL := $(BUILD_HELPER_DIR)/install
INSTALL_GLOBAL := $(BUILD_HELPER_DIR)/install-global

include packages/packages.make

# Workaround: Makefiles evaluate Variables the first time they are read. If a variable is not set the
# moment it is read, it is replaced with an empty string. Therefor our dependencies get lost, if the
# inlcuded Makefiles are not ordered correctly. For that reason, we parse the Makefiles for certain
# variable definitions and write them to an extra Makefile, which we include before the package Makefile.
$(BUILD_BASE_DIR)/build-helper-files.make:
	$(MKDIR) $(BUILD_BASE_DIR)
	$(RM) $@
	for P in $(PACKAGES); do \
	  inc_path=$$(test -f "$(NON_FREE_PACKAGE_DIR)/$$P/$$P.make" && echo "$(NON_FREE_PACKAGE_DIR)/$$P/$$P.make" || echo "$(PACKAGE_DIR)/$$P/$$P.make"); \
	  P_VAR=$$(echo $${P^^} | tr '-' '_' ); \
	  egrep -h "^$$P_VAR\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "^$${P_VAR}_VERS\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "^$${P_VAR}_DIR\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "^$${P_VAR}_BUILD(_[A-Z]+)?\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "^$${P_VAR}_INSTALL(_[A-Z]+)?\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "^$${P_VAR}_INTERMEDIATE_INSTALL(_[A-Z]+)?\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "^$${P_VAR}_CACHE_PKG_PROCESS(_[A-Z]+)?\s+:=\s+" $$inc_path >> $@ ; \
	done || true


-include .config

# debian/rules and RPM specfile (omd.spec) set DESTDIR to install files to
# the package build directories
DESTDIR ?= $(BUILD_BASE_DIR)/dest

RPM_TOPDIR := $(BUILD_BASE_DIR)/rpm/topdir
RPM_BUILDROOT := $(BUILD_BASE_DIR)/rpm/buildroot

SKEL := $(DESTDIR)$(OMD_ROOT)/skel
SKEL_PERMISSIONS := $(DESTDIR)$(OMD_ROOT)/share/omd/skel.permissions
CMA_PKG_VERSION_TXT := $(shell if [ "$(DISTRO_CODE)" = "bookworm" ]; then echo "-4" ; elif [ "$(DISTRO_CODE)" = "buster" ]; then echo "-3"; fi )
ARCH := $(shell uname -m)
CMA_PACKAGE:= $(REPO_PATH)/check-mk-$(EDITION)-$(PKG_VERSION)$(CMA_PKG_VERSION_TXT)-$(ARCH).cma
BOM := bill-of-materials.json

.PHONY: install cma rpm deb clean install-clean venv

# Called while building the .rpm/.deb packages
install: $(INSTALL_GLOBAL) $(DEPS_INSTALL_BAZEL)
	python3 ./strip_binaries --exclude cmk-agent-ctl --exclude mk-sql --exclude cmc --exclude waitmax --exclude agent_modbus $(DESTDIR)$(OMD_ROOT)/

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
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/skel
	$(call log_time,$@,done)
	touch $@

$(INSTALL_TARGETS) $(CACHE_PKG_PROCESS_TARGETS): $(PRE_INSTALL)

$(INSTALL_LOG_TARGETS): %-log: %
	$(call log_time,$@,done)

$(INSTALL): $(INSTALL_LOG_TARGETS)
# Repair packages that install with silly modes (such as Nagios)
	chmod -R o+Xr $(DESTDIR)$(OMD_ROOT)
	$(TOUCH) $@

$(SKEL_PERMISSIONS): $(INSTALL)
# Create permissions file for skel
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/omd
	set -e ; \
	OUTPUT=""; \
	cd packages ; for p in $(PACKAGES) rrdtool; do \
	    if [ -d $$p ] && [ -e $$p/skel.permissions ] ; then \
	        OUTPUT="$${OUTPUT}# $$p\n$$(cat $$p/skel.permissions)\n"; \
	    fi ; \
	done ; \
	cd ../../non-free/packages ; for p in $(PACKAGES) ; do \
	    if [ -d $$p ] && [ -e $$p/skel.permissions ] ; then \
	        OUTPUT="$${OUTPUT}# $$p\n$$(cat $$p/skel.permissions)\n"; \
	    fi ; \
	done ; \
	bazel build //omd:skel_permissions_$(EDITION_SHORT) ; \
	OUTPUT="$${OUTPUT}# Bazel\n$$(cat $(REPO_PATH)/bazel-bin/omd/skel.permissions_$(EDITION_SHORT))\n" ; \
	echo -e "$$OUTPUT" > $(SKEL_PERMISSIONS)

$(INSTALL_GLOBAL): $(SKEL_PERMISSIONS) $(BOM)
	# Create link to default version
	ln -sf $(OMD_VERSION) $(DESTDIR)$(OMD_BASE)/versions/default

	# Create global symbolic links. Those links are share between
	# all installed versions and refer to the default version.
	mkdir -p $(DESTDIR)/usr/bin
	ln -sfn /omd/versions/default/bin/omd $(DESTDIR)/usr/bin/omd
	mkdir -p $(DESTDIR)/usr/share/man/man8
	ln -sfn /omd/versions/default/share/man/man8/omd.8.gz $(DESTDIR)/usr/share/man/man8/omd.8.gz
	mkdir -p $(DESTDIR)/etc/init.d
	ln -sfn /omd/versions/default/share/omd/omd.init $(DESTDIR)/etc/init.d/omd
	mkdir -p $(DESTDIR)$(APACHE_CONF_DIR)
	ln -sfn /omd/versions/default/share/omd/apache.conf $(DESTDIR)$(APACHE_CONF_DIR)/zzz_omd.conf

	# Base directories below /omd
	mkdir -p $(DESTDIR)$(OMD_BASE)/sites
	mkdir -p $(DESTDIR)$(OMD_BASE)/apache

	# Information about distribution and OMD
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/omd
	install -m 644 distros/$(DISTRO_NAME)_$(DISTRO_VERSION).mk $(DESTDIR)$(OMD_ROOT)/share/omd/distro.info
	echo -e "OMD_VERSION = $(OMD_VERSION)\nOMD_PHYSICAL_BASE = $(OMD_PHYSICAL_BASE)" > $(DESTDIR)$(OMD_ROOT)/share/omd/omd.info

	# Install ChangeLog created from all werks
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/doc
	ln -sfn check_mk/ChangeLog $(DESTDIR)$(OMD_ROOT)/share/doc/ChangeLog

	chmod 755 $(DESTDIR)$(OMD_ROOT)/share
	chmod 755 $(DESTDIR)$(OMD_ROOT)/share/man
	chmod 755 $(DESTDIR)$(OMD_ROOT)/share/man/man1

	git rev-parse HEAD > $(DESTDIR)$(OMD_ROOT)/share/doc/COMMIT
	chmod 644 $(DESTDIR)$(OMD_ROOT)/share/doc/COMMIT

# This file is normally generated by our CI chain. In case it is not there, just
# create an empty one instead of failing the build.
$(BOM):
	$(TOUCH) $@

# Perform some validations
	for SKEL_DIR in tmp var etc; do \
	    if [ -d "$(DESTDIR)$(OMD_ROOT)/$$SKEL_DIR" ]; then \
	        echo "ERROR: The directory $$SKEL_DIR is only allowed to exist in skel/" ; \
	        find "$(DESTDIR)$(OMD_ROOT)/$$SKEL_DIR" ; \
	        exit 1 ; \
	    fi ; \
	done
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
	if [ "$(EDITION)" =  "raw" ]; then \
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

debian/changelog:
	sed -e 's/###DISTRO_CODE###/$(DISTRO_CODE)/g' \
	    -e "s/###PKG_VERSION###/$(PKG_VERSION)/g" \
	    -e "s/###NOW###/$(shell date -R)/g" \
	    -e 's/###EDITION###/$(EDITION)/g' \
	    debian/changelog.in > debian/changelog

debian/control: debian/control.in
	sed -e 's/###OMD_VERSION###/$(OMD_VERSION)/g' \
	    -e "s/###PKG_VERSION###/$(PKG_VERSION)/g" \
	    -e 's/###EDITION###/$(EDITION)/g' \
	    -e 's/###OS_PACKAGES###/$(OS_PACKAGES)/g' \
	    -e '/Depends:/s/\> /, /g' \
	    -e '/Depends:/s/@/ /g' \
	   debian/control.in > debian/control

# Called by our release system to build DEB packages
#
# Check out "man debuild" and "man dpkg-buildpackage" to get a description of
# the build mechanism.
# Please keep in mind that we are building for multiple Ubuntu/Debian version
# and need to be compatible to all of the tool chains shipped with them.
#
# In case we want to have fast package creation without need to rebuild
# everything, we'd have to
# a) drop the "clean" argument for newer distros
# b) remove the dh_prep from debian/rules
deb: debian/changelog debian/control
	debuild \
	--preserve-envvar="NEXUS_*" \
	--preserve-envvar="BAZEL_*" \
	--preserve-envvar="MAKE" \
	--preserve-envvar="CI" \
	--preserve-envvar="RUSTUP_HOME" \
	--prepend-path $$HOME/.cargo/bin \
	--prepend-path=/usr/local/bin \
	--prepend-path=`dirname $$(which python3)` \
	--set-envvar EDITION=$(EDITION) \
	--no-lintian \
	-i\.git -I\.git \
	-i.gitignore -I.gitignore \
	-rfakeroot \
	--no-sign -- clean build-arch binary-arch

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
