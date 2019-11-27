include Makefile.omd
include $(BUILD_BASE_DIR)/build-helper-files.make
include packages/packages.make

# You can build singele packages by calling macke <PACKAGENAME>
# e.g.: make nagios rrdtool
#
# You can select a subset of the packages by overriding this
# variale, e.g. make PACKAGES='nagios rrdtool' pack
#
# If you just want to test package building, you can reduce the
# number of packages to just "omd" - to speed up your tests.
# PACKAGES="omd"
#
# You can also create a file named .config and override the
# PACKAGES variable there to customzie the list of packages.

PACKAGES := \
    libgsf \
    perl-modules \
    Python \
    Python3 \
    freetds \
    re2 \
    python-modules \
    python3-modules \
    rrdtool \
    msitools \
    net-snmp \
    apache-omd \
    mod_fcgid \
    mod_wsgi \
    check_mk \
    check_multi \
    check_mysql_health \
    check_oracle_health \
    Webinject \
    dokuwiki \
    jmx4perl \
    mk-livestatus \
    stunnel \
    nagios \
    monitoring-plugins \
    nagvis \
    nrpe \
    nsca \
    omd \
    openhardwaremonitor \
    navicli \
    pnp4nagios \
    maintenance \
    patch \
    heirloom-mailx \
    snap7 \
    heirloom-pkgtools

ifeq ($(EDITION),enterprise)
PACKAGES += enterprise
endif
ifeq ($(EDITION),managed)
PACKAGES += enterprise
PACKAGES += managed
endif

# Workaround: Makefiles evaluate Variables the first time they are read. If a variable is not set the
# moment it is read, it is replaced with an empty string. Therefor our dependencies get lost, if the
# inlcuded Makefiles are not ordered correctly. For that reason, we parse the Makefiles for certain
# variable definitions and write them to an extra Makefile, which we include before the package Makefile.
$(BUILD_BASE_DIR)/build-helper-files.make:
	$(MKDIR) $(BUILD_BASE_DIR)
	$(RM) $@
	for P in $(PACKAGES); do \
	  inc_path=$(PACKAGE_DIR)/$$P/$$P.make; \
	  if [[ $$P == 'enterprise' || $$P == 'managed' ]] ; then \
	    inc_path=$(REPO_PATH)/$$P/$$P.make; \
	  fi ; \
	  P_VAR=$$(echo $${P^^} | tr '-' '_' ); \
	  egrep -h "$$P_VAR\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "$${P_VAR}_VERS\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "$${P_VAR}_DIR\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "$${P_VAR}_BUILD\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "$${P_VAR}_INSTALL\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "$${P_VAR}_INTERMEDIATE_INSTALL\s+:=\s+" $$inc_path >> $@ ; \
	  egrep -h "$${P_VAR}_CACHE_PKG_PROCESS\s+:=\s+" $$inc_path >> $@ ; \
	  if [ "$$P" == "rrdtool" ]; then \
	    egrep -h "$${P_VAR}_BUILD_LIBRARY\s+:=\s+" $$inc_path >> $@ ; \
	    egrep -h "$${P_VAR}_INSTALL_LIBRARY\s+:=\s+" $$inc_path >> $@ ; \
	    egrep -h "$${P_VAR}_BUILD_BINDINGS\s+:=\s+" $$inc_path >> $@ ; \
	    egrep -h "$${P_VAR}_INSTALL_BINDINGS\s+:=\s+" $$inc_path >> $@ ; \
	  fi \
	done


-include .config

# debian/rules and RPM specfile (omd.spec) set DESTDIR to install files to
# the package build directories
DESTDIR ?= $(BUILD_BASE_DIR)/dest

RPM_TOPDIR := $(BUILD_BASE_DIR)/rpm/topdir
RPM_BUILDROOT := $(BUILD_BASE_DIR)/rpm/buildroot

NEW_SERIAL=$$(($(OMD_SERIAL) + 1))
SKEL := $(DESTDIR)$(OMD_ROOT)/skel
CMA_PKG_VERSION_TXT := $(shell if [ "$(DISTRO_CODE)" = "stretch" ]; then echo "-2" ; fi )
ARCH := $(shell uname -m)
CMA_PACKAGE:= $(REPO_PATH)/check-mk-$(EDITION)-$(PKG_VERSION)$(CMA_PKG_VERSION_TXT)-$(ARCH).cma

PRE_INSTALL := $(BUILD_HELPER_DIR)/pre-install
PRE_SKEL := $(BUILD_HELPER_DIR)/pre-skel
INSTALL := $(BUILD_HELPER_DIR)/install
INSTALL_GLOBAL := $(BUILD_HELPER_DIR)/install-global

BUILD_TARGET_VARS := $(shell echo $(PACKAGES)  | tr 'a-z' 'A-Z' | tr '-' '_' )
BUILD_TARGETS := $(foreach package,$(addsuffix _BUILD,$(BUILD_TARGET_VARS)),$($(package)))
INSTALL_TARGETS := $(foreach package,$(addsuffix _INSTALL,$(BUILD_TARGET_VARS)),$($(package)))
SKEL_TARGETS :=  $(foreach package,$(addsuffix _SKEL,$(BUILD_TARGET_VARS)),$($(package)))

.PHONY: install cma rpm deb clean setversion install-clean

# Called while building the .rpm/.deb packages
install: $(DESTDIR)$(OMD_ROOT)/share/omd/skel.permissions $(FIX_SKEL)

# Called by our release system to build appliance packages
cma: $(CMA_PACKAGE)

install-clean:
	rm -rf $(DESTDIR)
	rm -rf $(BUILD_HELPER_DIR)/*-install
	rm -rf $(BUILD_HELPER_DIR)/*-skel

# Prepare clean install environment
$(PRE_INSTALL):
	$(MKDIR) $(DESTDIR)$(OMD_PHYSICAL_BASE)
	A="$(OMD_PHYSICAL_BASE)" ; ln -s $${A:1} $(DESTDIR)/omd
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/bin
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/lib/nagios/plugins
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/omd
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/diskspace
	$(MKDIR) $(DESTDIR)$(OMD_ROOT)/share/man/man1
	touch $@


$(INSTALL_TARGETS): $(PRE_INSTALL)

$(SKEL_TARGETS): $(PRE_SKEL)

$(INSTALL): $(INSTALL_TARGETS)
	# Repair packages that install with silly modes (such as Nagios)
	chmod -R o+Xr $(DESTDIR)$(OMD_ROOT)
	$(TOUCH) $@

$(PRE_SKEL) : $(INSTALL_GLOBAL)
	# Install skeleton files (subdirs skel/ in packages' directories)
	mkdir -p $(DESTDIR)$(OMD_ROOT)/skel
	@set -e ; cd packages ; for p in $(PACKAGES) ; do \
            if [ -d "$$p/skel" ] ; then  \
              tar cf - -C $$p/skel --exclude="*~" --exclude=".gitignore" . | tar xvf - -C $(DESTDIR)$(OMD_ROOT)/skel ; \
            fi ;\
        done
	$(TOUCH) $@

$(DESTDIR)$(OMD_ROOT)/share/omd/skel.permissions: $(PRE_SKEL) $(SKEL_TARGETS)
	# Create permissions file for skel
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/omd
	set -e ; cd packages ; for p in $(PACKAGES) ; do \
	    if [ -d $$p ] && [ -e $$p/skel.permissions ] ; then \
	        echo "# $$p" ; \
	        cat $$p/skel.permissions ; \
	    fi ; \
	done > $(DESTDIR)$(OMD_ROOT)/share/omd/skel.permissions

# TODO: There is no FIX_SKEL definition. This is never executed. WTF?
$(FIX_SKEL): $(SKEL_TARGETS)
	# Make sure, all permissions in skel are set to 0755, 0644
	@failed=$$(find $(DESTDIR)$(OMD_ROOT)/skel -type d -not -perm 0755) ; \
	if [ -n "$$failed" ] ; then \
	    echo "Fixing invalid permissions for skeleton dirs. Must be 0755:" ; \
            chmod -c 755 $$failed ; \
            echo "$$failed" ; \
        fi
	@failed=$$(find $(DESTDIR)$(OMD_ROOT)/skel -type f -not -perm 0644) ; \
	if [ -n "$$failed" ] ; then \
	    echo "Fixing invalid permissions for skeleton files. Must be 0644:" ; \
            echo "$$failed" ; \
            chmod -c 644 $$failed ; \
        fi

	# Fix packages which did not add ###ROOT###
	find $(DESTDIR)$(OMD_ROOT)/skel -type f | xargs -n1 sed -i -e 's+$(OMD_ROOT)+###ROOT###+g'

	# Remove site-specific directories that went under /omd/version
	rm -rf $(DESTDIR)/{var,tmp}
	$(TOUCH) $@

# Create installations files that do not lie beyond /omd/versions/$(OMD_VERSION)
# and files not owned by a specific package.
$(INSTALL_GLOBAL): $(INSTALL)
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
	install -m 644 Licenses.csv $(DESTDIR)$(OMD_ROOT)/share/doc/Licenses.csv
	install -m 644 Licenses.README.txt $(DESTDIR)$(OMD_ROOT)/share/doc/Licenses.README.txt
	install -m 644 License_texts.pdf $(DESTDIR)$(OMD_ROOT)/share/doc/License_texts.pdf

	if [ -f COMMIT ]; then \
	    install -m 644 COMMIT $(DESTDIR)$(OMD_ROOT)/share/doc ; \
	fi

# Perform some validations
	for SKEL_DIR in tmp var etc; do \
	    if [ -d "$(DESTDIR)$(OMD_ROOT)/$$SKEL_DIR" ]; then \
	        echo "ERROR: The directory $$SKEL_DIR is only allowed to exist in skel/" ; \
	        find "$(DESTDIR)$(OMD_ROOT)/$$SKEL_DIR" ; \
	        exit 1 ;
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
# In case we want to have fast package creation without need to rebuild
# everything, we'd have to
# a) add -nc fo jessie/trusty/xenial
# b) drop the "clean" argument for newer distros
deb: debian/changelog debian/control
	echo $(DISTRO_CODE)
	if [ "$(DISTRO_CODE)" = "jessie" ] || [ "$(DISTRO_CODE)" = "trusty" ] || [ "$(DISTRO_CODE)" = "xenial" ]; then \
	    TARGET="-us -uc -B" ; \
	else \
	    TARGET="--no-sign -- clean binary-arch" ; \
	fi && \
	    debuild \
	    --preserve-envvar="NEXUS_*" \
	    --preserve-envvar="PYTHON_ENABLE_OPTIMIZATIONS" \
	    --prepend-path=/usr/local/bin \
	    --set-envvar EDITION=$(EDITION) \
	    --no-lintian \
	    -i\.git -I\.git \
	    -i.gitignore -I.gitignore \
	    -rfakeroot \
	    $$TARGET

setversion:
# NEW_VERSION should be set on the command line.  Replace all '/' since sed
# tries to interpret them '/' might occur in custom branches filenames and sed
# arguments should not contain '/'
	NEW_OMD_VERSION=$(subst /,-,$(NEW_VERSION)).$(EDITION_SHORT)$(DEMO_SUFFIX) ; \
	if [ -n "$$NEW_OMD_VERSION" ] && [ "$$NEW_OMD_VERSION" != "$(OMD_VERSION)" ]; then \
	    sed -ri 's/^(OMD_SERIAL[[:space:]]*= *).*/\1'"$(NEW_SERIAL)/" Makefile.omd ; \
	fi ; \
	sed -ri 's/^(OMD_VERSION[[:space:]]*= *).*/\1"'"$$NEW_OMD_VERSION"'"/' packages/omd/omdlib/__init__.py

# TODO: Can not find CMA_INSTALL definition. Is this dead?
$(CMA_INSTALL): $(INSTALL_TARGETS)

# Please note: APPLIANCE_*_CMA are defined in omd/packages/appliance/appliance.make
$(APPLIANCE_INSTALL_CMA): $(PRE_INSTALL)

# Please note: APPLIANCE_*_CMA are defined in omd/packages/appliance/appliance.make
$(CMA_PACKAGE): $(CMA_INSTALL) $(APPLIANCE_INSTALL_CMA) $(APPLIANCE_SKEL_CMA) install
	# Create info file to mark minimal cma firmware version requirement
	@if [ "$(DISTRO_CODE)" = "stretch" ]; then \
	    MIN_VERSION=1.4.0 ; \
	else \
	    MIN_VERSION=1.1.2 ; \
	fi ; \
	echo -e "MIN_VERSION=$${MIN_VERSION}\n" > $(DESTDIR)/opt/omd/versions/$(OMD_VERSION)/cma.info

	# Mark demo builds in cma.info file
	@if [ -n "$(DEMO_SUFFIX)" ]; then \
	    echo -e "DEMO=1\n" >> $(DESTDIR)/opt/omd/versions/$(OMD_VERSION)/cma.info ; \
	fi

	tar czf $@ \
	    --owner=root \
	    --group=root \
	    -C $(DESTDIR)/opt/omd/versions/ \
	    $(OMD_VERSION)

clean: $(addsuffix -clean,$(PACKAGES)) install-clean
	rm -rf $(DESTDIR)
	@for p in packages/* ; do \
	    if [ -d $$p ] && [ -f $$p/Makefile ]; then \
		$(MAKE) -C $$p clean ; \
	    fi ; \
	done
	$(RM) -r $(BUILD_HELPER_DIR)
	$(RM) -r $(BUILD_BASE_DIR)

setup:
	@echo "Please run the build in a docker container."
	@echo "Dockerfiles for all Distros can be found under 'buildscripts/infrastructure/build-nodes/'."
