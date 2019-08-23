SHELL = /bin/bash

include Makefile.omd

# You can select a subset of the packages by overriding this
# variale, e.g. make PACKAGES='nagios rrdtool' pack
#
# If you just want to test package building, you can reduce the
# number of packages to just "omd" - to speed up your tests.
# PACKAGES="omd"
#
# You can also create a file named .config and override the
# PACKAGES variable there to customzie the list of packages.
PACKAGES=\
    libgsf \
    perl-modules \
    python \
    freetds \
    re2 \
    python-modules \
    boost \
    rrdtool \
    msitools \
    net-snmp \
    apache-omd \
    mod_python \
    mod_fcgid \
    check_mk \
    check_multi \
    check_mysql_health \
    check_oracle_health \
    check_webinject \
    dokuwiki \
    jmx4perl \
    mk-livestatus \
    icinga \
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
    nail \
    snap7 \
    heirloom-pkgtools

ifeq ($(EDITION),enterprise)
    PACKAGES+=check_mk_enterprise
endif
ifeq ($(EDITION),managed)
    PACKAGES+=check_mk_enterprise
    PACKAGES+=check_mk_managed
endif

default: build

-include .config

DESTDIR ?=$(shell pwd)/destdir
RPM_TOPDIR=$$(pwd)/rpm.topdir
BIN_TGZ=check-mk-$(EDITION)-bin-$(OMD_VERSION).tar.gz
NEW_SERIAL=$$(($(OMD_SERIAL) + 1))

.PHONY: install-global

check-edition:
	@if [ -z "$(EDITION)" ]; then \
	    echo "FEHLER: Du musst eine Edition angeben! (EDITION=raw|enterprise|managed)" ; \
	    exit 1 ; \
	fi

build: check-edition
	@set -e ; cd packages ; for p in $(PACKAGES) ; do \
	    if [ -d $$p ]; then \
	        echo "[$$(date '+%F %T')] ============================== build for package $$p started..." ; \
	        $(MAKE) -C $$p build ; \
	        echo "[$$(date '+%F %T')] ============================== build for package $$p finished" ; \
	    fi ; \
        done

pack: check-edition
	rm -rf $(DESTDIR)
	mkdir -p $(DESTDIR)$(OMD_PHYSICAL_BASE)
	A="$(OMD_PHYSICAL_BASE)" ; ln -s $${A:1} $(DESTDIR)/omd
	@set -e ; cd packages ; for p in $(PACKAGES) ; do \
	    if [ -d $$p ]; then \
	        $(MAKE) -C $$p DESTDIR=$(DESTDIR) install ; \
                for hook in $$(cd $$p ; ls *.hook 2>/dev/null) ; do \
                    mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks ; \
                    install -m 755 $$p/$$hook $(DESTDIR)$(OMD_ROOT)/lib/omd/hooks/$${hook%.hook} ; \
                done ; \
	    fi ; \
        done

	# Repair packages that install with silly modes (such as Nagios)
	chmod -R o+Xr $(DESTDIR)$(OMD_ROOT)
	$(MAKE) install-global

	# Install skeleton files (subdirs skel/ in packages' directories)
	mkdir -p $(DESTDIR)$(OMD_ROOT)/skel
	@set -e ; cd packages ; for p in $(PACKAGES) ; do \
            if [ -d "$$p" ] && [ -d "$$p/skel" ] ; then  \
              tar cf - -C $$p/skel --exclude="*~" --exclude=".gitignore" . | tar xvf - -C $(DESTDIR)$(OMD_ROOT)/skel ; \
            fi ;\
            $(MAKE) DESTDIR=$(DESTDIR) SKEL=$(DESTDIR)$(OMD_ROOT)/skel -C $$p skel ;\
        done

        # Create permissions file for skel
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/omd
	@set -e ; cd packages ; for p in $(PACKAGES) ; do \
	    if [ -d $$p ] && [ -e $$p/skel.permissions ] ; then \
	        echo "# $$p" ; \
	        cat $$p/skel.permissions ; \
	    fi ; \
	done > $(DESTDIR)$(OMD_ROOT)/share/omd/skel.permissions

        # Make sure, all permissions in skel are set to 0755, 0644
	@failed=$$(find $(DESTDIR)$(OMD_ROOT)/skel -type d -not -perm 0755) ; \
	if [ -n "$$failed" ] ; then \
	    echo "Invalid permissions for skeleton dirs. Must be 0755:" ; \
            echo "I'll fix this for you this time..." ; \
            chmod -c 755 $$failed ; \
            echo "$$failed" ; \
        fi
	@failed=$$(find $(DESTDIR)$(OMD_ROOT)/skel -type f -not -perm 0644) ; \
	if [ -n "$$failed" ] ; then \
	    echo "Invalid permissions for skeleton files. Must be 0644:" ; \
            echo "$$failed" ; \
            echo "I'll fix this for you this time..." ; \
            chmod -c 644 $$failed ; \
        fi

	# Fix packages which did not add ###ROOT###
	find $(DESTDIR)$(OMD_ROOT)/skel -type f | xargs -n1 sed -i -e 's+$(OMD_ROOT)+###ROOT###+g'

	# Remove site-specific directories that went under /omd/version
	rm -rf $(DESTDIR)/{var,tmp}

	# Pack the whole stuff into a tarball
	tar czf $(BIN_TGZ) --owner=root --group=root -C $(DESTDIR) .

clean:
	@if [ -d $(DESTDIR) ]; then \
	    rm -rf $(DESTDIR) ; \
	fi
	env
	@for p in packages/* ; do \
	    if [ -d $$p ] && [ -f $$p/Makefile ]; then \
		$(MAKE) -C $$p clean ; \
	    fi ; \
	done

# Create installations files that do not lie beyond /omd/versions/$(OMD_VERSION)
# and files not owned by a specific package.
install-global:
	# Create link to default version
	ln -s $(OMD_VERSION) $(DESTDIR)$(OMD_BASE)/versions/default

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
	ln -s check_mk/ChangeLog $(DESTDIR)$(OMD_ROOT)/share/doc/ChangeLog
	install -m 644 Licenses.csv $(DESTDIR)$(OMD_ROOT)/share/doc/Licenses.csv
	install -m 644 Licenses.README.txt $(DESTDIR)$(OMD_ROOT)/share/doc/Licenses.README.txt
	install -m 644 License_texts.pdf $(DESTDIR)$(OMD_ROOT)/share/doc/License_texts.pdf

	if [ -f COMMIT ]; then \
	    install -m 644 COMMIT $(DESTDIR)$(OMD_ROOT)/share/doc ; \
	fi


rpm: check-edition
	PKG_VERSION=$(OMD_VERSION) ; \
	PKG_VERSION=$${PKG_VERSION/.cee/} ; \
	PKG_VERSION=$${PKG_VERSION/.cre/} ; \
	PKG_VERSION=$${PKG_VERSION/.cme/} ; \
	sed -e 's/^Requires:.*/Requires:        $(OS_PACKAGES)/' \
	    -e 's/%{version}/$(OMD_VERSION)/g' \
	    -e "s/%{pkg_version}/$$PKG_VERSION/g" \
	    -e 's/%{edition}/$(EDITION)/g' \
	    -e 's/^Version:.*/Version: $(DISTRO_CODE)/' \
	    -e 's/^Release:.*/Release: $(OMD_SERIAL)/' \
	    -e 's#@APACHE_CONFDIR@#$(APACHE_CONF_DIR)#g' \
	    -e 's#@APACHE_NAME@#$(APACHE_INIT_NAME)#g' \
	    omd.spec.in > omd.spec
	if [ "$(EDITION)" =  "raw" ]; then \
	    sed -i '/icmpsender/d;/icmpreceiver/d' omd.spec ; \
	fi
	make -C $(REPO_PATH) dist
	mkdir -p $(RPM_TOPDIR)/{SOURCES,BUILD,RPMS,SRPMS,SPECS}
	cp ../check-mk-$(EDITION)-$(OMD_VERSION).tar.gz $(RPM_TOPDIR)/SOURCES
	# NO_BRP_STALE_LINK_ERROR ignores errors when symlinking from skel to
	# share,lib,bin because the link has a invalid target until the site is created
	# NO_BRP_CHECK_RPATH ignores errors with the compiled python2.7 binary which
	# has a rpath hard coded to the OMD shipped libpython2.7.
	NO_BRP_CHECK_RPATH="yes" \
	NO_BRP_STALE_LINK_ERROR="yes" \
	rpmbuild -ba --define "_topdir $(RPM_TOPDIR)" \
	     --buildroot=$$(pwd)/rpm.buildroot omd.spec
	mv -v $(RPM_TOPDIR)/RPMS/*/*.rpm $(REPO_PATH)
	mv -v $(RPM_TOPDIR)/SRPMS/*.src.rpm $(REPO_PATH)
	rm -rf $(RPM_TOPDIR) rpm.buildroot

# Build DEB from prebuild binary. This currently needs 'make dist' and thus only
# works within a GIT repository.
deb-environment:
	@if test -z "$(DEBFULLNAME)" || test -z "$(DEBEMAIL)"; then \
	  echo "please read 'man dch' and set DEBFULLNAME and DEBEMAIL" ;\
	  exit 1; \
	fi

# create a debian/changelog to build the package 
deb-changelog: deb-environment
	# this is a hack!
	rm -f debian/changelog
	PKG_VERSION=$(OMD_VERSION) ; \
	PKG_VERSION=$${PKG_VERSION/.cee/} ; \
	PKG_VERSION=$${PKG_VERSION/.cre/} ; \
	PKG_VERSION=$${PKG_VERSION/.cme/} ; \
	dch --create --package check-mk-$(EDITION)-$$PKG_VERSION \
	    --newversion 0.$(DISTRO_CODE) "`cat debian/changelog.tmpl`"
	dch --release "releasing ...."

deb: check-edition deb-changelog
	PKG_VERSION=$(OMD_VERSION) ; \
	PKG_VERSION=$${PKG_VERSION/.cee/} ; \
	PKG_VERSION=$${PKG_VERSION/.cre/} ; \
	PKG_VERSION=$${PKG_VERSION/.cme/} ; \
	sed -e 's/###OMD_VERSION###/$(OMD_VERSION)/' \
	    -e "s/###PKG_VERSION###/$$PKG_VERSION/" \
	    -e 's/###EDITION###/$(EDITION)/' \
	    -e 's/###BUILD_PACKAGES###/$(BUILD_PACKAGES)/' \
	    -e 's/###OS_PACKAGES###/$(OS_PACKAGES)/' \
	    -e '/Depends:/s/\> /, /g' \
	    -e '/Depends:/s/@/ /g' \
	   `pwd`/debian/control.in > `pwd`/debian/control
	fakeroot bash -c "export EDITION=$(EDITION) ; debian/rules clean"
	debuild --set-envvar EDITION=$(EDITION) \
		--prepend-path=/usr/local/bin --no-lintian -i\.git -I\.git \
			-icheck-mk-$(EDITION)-bin-$(OMD_VERSION).tar.gz \
			-Icheck-mk-$(EDITION)-bin-$(OMD_VERSION).tar.gz \
			-i.gitignore -I.gitignore \
			-uc -us -rfakeroot
	# -- renaming deb package to DISTRO_CODE dependend name
	# arch=`dpkg-architecture -qDEB_HOST_ARCH` ; \
	# build=`sed -e '1s/.*(\(.*\)).*/\1/;q' debian/changelog` ; \
	# distro=`echo $$build | sed -e 's/build/$(DISTRO_CODE)/' ` ; \
	# echo "$$arch $$build $$distro"; \
	# mv "../omd-$(OMD_VERSION)_$${build}_$${arch}.deb" \
	#  "../omd-$(OMD_VERSION)_$${distro}_$${arch}.deb" ;

# Only for development: install tarball below /
xzf:
	tar xzf $(BIN_TGZ) -C / # HACK: Add missing suid bits if compiled as non-root
	chmod 4755 $(OMD_ROOT)/lib/nagios/plugins/check_{icmp,dhcp}
	chmod 4775 $(OMD_ROOT)/bin/mkeventd_open514
	$(APACHE_CTL) -k graceful

# On debian based systems register the alternative switches
alt:
	@if which update-alternatives >/dev/null 2>&1; then \
	    update-alternatives --install /omd/versions/default \
		omd /omd/versions/$(OMD_VERSION) $(OMD_SERIAL) \
		--slave /usr/bin/omd omd.bin /omd/versions/$(OMD_VERSION)/bin/omd \
		--slave /usr/share/man/man8/omd.8.gz omd.man8 \
               /omd/versions/$(OMD_VERSION)/share/man/man8/omd.8.gz ; \
	fi ;

setversion:
	NEW_OMD_VERSION=$(NEW_VERSION).$(EDITION_SHORT)$(DEMO_SUFFIX) ; \
	if [ -n "$$NEW_OMD_VERSION" ] && [ "$$NEW_OMD_VERSION" != "$(OMD_VERSION)" ]; then \
	    sed -ri 's/^(OMD_SERIAL[[:space:]]*= *).*/\1'"$(NEW_SERIAL)/" Makefile.omd ; \
	fi ; \
	sed -ri 's/^(OMD_VERSION[[:space:]]*= *).*/\1"'"$$NEW_OMD_VERSION"'"/' packages/omd/omd

test:
	t/test_all.sh

cma: check-edition
	# make the cmc the default core
	sed -i 's/default)/default) echo "cmc"; exit;/g' packages/omd/CORE.hook
	# enable the event console by default
	sed -i 's/default)/default) echo "on"; exit;/g' packages/check_mk/MKEVENTD.hook
	
	make PACKAGES="$(PACKAGES) cma" build pack
	
	# Create info file to mark minimal cma firmware version requirement
	@if [ "$(DISTRO_CODE)" = "stretch" ]; then \
	    MIN_VERSION=1.4.0 ; \
	else \
	    MIN_VERSION=1.1.2 ; \
	fi ; \
	echo -e "MIN_VERSION=$${MIN_VERSION}\n" > $(DESTDIR)/opt/omd/versions/$(OMD_VERSION)/cma.info
	
	# Mark demo builds in cma.info file
	@if [ -f packages/nagios/patches/9999-demo-version.dif ]; then \
	    echo -e "DEMO=1\n" >> $(DESTDIR)/opt/omd/versions/$(OMD_VERSION)/cma.info ; \
	fi
	
	rm check-mk-$(EDITION)-bin-$(OMD_VERSION).tar.gz
	
	if [ "$(DISTRO_CODE)" = "stretch" ]; then \
	    CMA_PKG_VERSION_TXT="-2" ; \
	else \
	    CMA_PKG_VERSION_TXT="" ; \
	fi ; \
	PKG_VERSION=$(OMD_VERSION) ; \
	PKG_VERSION=$${PKG_VERSION/.cee/} ; \
	PKG_VERSION=$${PKG_VERSION/.cre/} ; \
	PKG_VERSION=$${PKG_VERSION/.cme/} ; \
	tar czf $(REPO_PATH)/check-mk-$(EDITION)-$${PKG_VERSION}$${CMA_PKG_VERSION_TXT}-$$(uname -m).cma \
	    --owner=root \
	    --group=root \
	    -C $(DESTDIR)/opt/omd/versions/ \
	    $(OMD_VERSION)

setup:
	@echo "Packages needed for compilation:"
	@echo "$(BUILD_PACKAGES)"
	@CMD="$(PACKAGE_INSTALL) $(BUILD_PACKAGES)" ; \
	if [ $$(id -u) != 0 ]; then \
	    CMD="$(BECOME_ROOT) '$$CMD'" ; \
	fi ; \
	echo "Going to run >>> $$CMD <<<..." ; \
	\
	if eval "$$CMD"; then \
	    echo "OK - You are now ready for 'make rpm' or 'make deb'" ; \
	else \
	    echo "ERROR: Some packages could not be installed. You will get " ; \
	    echo "problems while compiling if something is missing." ; \
	    exit 1 ; \
	fi
