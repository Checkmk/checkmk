NET_SNMP := net-snmp
NET_SNMP_VERS := 5.9.1
NET_SNMP_DIR := $(NET_SNMP)-$(NET_SNMP_VERS)
# Increase this to enforce a recreation of the build cache
NET_SNMP_BUILD_ID := 2

NET_SNMP_PATCHING := $(BUILD_HELPER_DIR)/$(NET_SNMP_DIR)-patching
NET_SNMP_BUILD := $(BUILD_HELPER_DIR)/$(NET_SNMP_DIR)-build
NET_SNMP_INTERMEDIATE_INSTALL := $(BUILD_HELPER_DIR)/$(NET_SNMP_DIR)-install-intermediate
NET_SNMP_INTERMEDIATE_INSTALL_BASE := $(BUILD_HELPER_DIR)/$(NET_SNMP_DIR)-install-base
NET_SNMP_INTERMEDIATE_INSTALL_PYTHON := $(BUILD_HELPER_DIR)/$(NET_SNMP_DIR)-install-python
NET_SNMP_INTERMEDIATE_INSTALL_PERL := $(BUILD_HELPER_DIR)/$(NET_SNMP_DIR)-install-perl
NET_SNMP_CACHE_PKG_PROCESS := $(BUILD_HELPER_DIR)/$(NET_SNMP_DIR)-cache-pkg-process
NET_SNMP_INSTALL := $(BUILD_HELPER_DIR)/$(NET_SNMP_DIR)-install

NET_SNMP_INSTALL_DIR := $(INTERMEDIATE_INSTALL_BASE)/$(NET_SNMP_DIR)
NET_SNMP_BUILD_DIR := $(PACKAGE_BUILD_DIR)/$(NET_SNMP_DIR)
#NET_SNMP_WORK_DIR := $(PACKAGE_WORK_DIR)/$(NET_SNMP_DIR)

$(NET_SNMP_BUILD): $(NET_SNMP_PATCHING) $(PYTHON_CACHE_PKG_PROCESS) $(PERL_MODULES_CACHE_PKG_PROCESS)
# Skip Perl-Modules because of build errors when MIB loading is disabled.
# Skip Python binding because we need to use our own python, see install target.
	cd $(NET_SNMP_BUILD_DIR) \
        && if [ "$(DISTRO_CODE)" == "el8" ]; then export CFLAGS='-Wformat -I../../include -D_REENTRANT -D_GNU_SOURCE -O2 -g -pipe -Wp,-D_FORTIFY_SOURCE=2 -Wp,-D_GLIBCXX_ASSERTIONS -fexceptions -fstack-protector-strong -grecord-gcc-switches -specs=/usr/lib/rpm/redhat/redhat-hardened-cc1 -specs=/usr/lib/rpm/redhat/redhat-annobin-cc1 -m64 -mtune=generic -fasynchronous-unwind-tables -fstack-clash-protection -fcf-protection -fwrapv -fno-strict-aliasing -I/usr/local/include -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64'; fi \
        && ./configure \
	    --enable-ipv6 \
	    --disable-agent \
	    --disable-snmptrapd-subagent \
	    --with-mibdirs="\$$HOME/local/share/snmp/mibs:\$$HOME/share/snmp/mibs:/usr/share/snmp/mibs" \
	    --with-defaults \
	    --disable-scripts \
	    --prefix="/" && $(MAKE)
	$(TOUCH) $@

NET_SNMP_CACHE_PKG_PATH := $(call cache_pkg_path,$(NET_SNMP_DIR),$(NET_SNMP_BUILD_ID))

$(NET_SNMP_CACHE_PKG_PATH):
	$(call pack_pkg_archive,$@,$(NET_SNMP_DIR),$(NET_SNMP_BUILD_ID),$(NET_SNMP_INTERMEDIATE_INSTALL))

$(NET_SNMP_CACHE_PKG_PROCESS): $(NET_SNMP_CACHE_PKG_PATH)
	$(call unpack_pkg_archive,$(NET_SNMP_CACHE_PKG_PATH),$(NET_SNMP_DIR))
	$(call upload_pkg_archive,$(NET_SNMP_CACHE_PKG_PATH),$(NET_SNMP_DIR),$(NET_SNMP_BUILD_ID))
	$(TOUCH) $@

$(NET_SNMP_INTERMEDIATE_INSTALL): $(NET_SNMP_INTERMEDIATE_INSTALL_BASE) $(NET_SNMP_INTERMEDIATE_INSTALL_PYTHON) $(NET_SNMP_INTERMEDIATE_INSTALL_PERL)
	$(TOUCH) $@

$(NET_SNMP_INTERMEDIATE_INSTALL_BASE): $(NET_SNMP_BUILD)
	cd $(NET_SNMP_BUILD_DIR)/snmplib && $(MAKE) DESTDIR=$(NET_SNMP_INSTALL_DIR) installlibs
	cd $(NET_SNMP_BUILD_DIR)/apps && $(MAKE) DESTDIR=$(NET_SNMP_INSTALL_DIR) installbin
	cd $(NET_SNMP_BUILD_DIR)/man && $(MAKE) DESTDIR=$(NET_SNMP_INSTALL_DIR) install
	$(MKDIR) $(NET_SNMP_INSTALL_DIR)/share/snmp/mibs
	cd $(NET_SNMP_BUILD_DIR)/mibs && $(MAKE) DESTDIR=$(NET_SNMP_INSTALL_DIR) mibsinstall
	$(TOUCH) $@

$(NET_SNMP_INTERMEDIATE_INSTALL_PYTHON): $(NET_SNMP_BUILD) $(PACKAGE_PYTHON3_MODULES_PYTHON_DEPS)
	$(MKDIR) $(NET_SNMP_INSTALL_DIR)/lib/python
	cd $(NET_SNMP_BUILD_DIR)/python && \
	    $(PACKAGE_PYTHON3_MODULES_PYTHON) setup.py install \
		--basedir=.. \
		--root=$(NET_SNMP_INSTALL_DIR) \
		--prefix='' \
		--single-version-externally-managed
	$(TOUCH) $@
# For some obscure reason beyond the mental capacities of mere humans, the
# easy_install mechanism triggered by the setup call above results in the
# creation of a lib/python/site.py, a copy of site-patch.py from setuptools.
# Having this in the PYTHONPATH makes it impossible to run python3-based SW as a
# site user, including gdb! So let's simply nuke it here...
# TODO(sp): Disabled for now, otherwise the netsnmp module is not found. Figure
# out what's really going on here!
#	$(RM) $(DESTDIR)$(OMD_ROOT)/lib/python/site.py*

# TODO: Use perl standard path variables
$(NET_SNMP_INTERMEDIATE_INSTALL_PERL): $(NET_SNMP_BUILD)
	cd $(NET_SNMP_BUILD_DIR)/perl && \
	    $(MAKE) \
		DESTDIR=$(NET_SNMP_INSTALL_DIR) \
		INSTALLSITEARCH=/lib/perl5/lib/perl5 \
		INSTALLSITEMAN3DIR=/share/man/man3 \
		INSTALLARCHLIB=/lib/perl5/lib/perl5/x86_64-linux-gnu-thread-multi \
		install
# Fixup some library permissions. They need to be owner writable to make
# dh_strip command of deb packaging procedure work
	find $(NET_SNMP_INSTALL_DIR)/lib/perl5/lib/perl5/auto/*SNMP -type f -name \*.so -exec chmod u+w {} \;
	$(TOUCH) $@

$(NET_SNMP_INSTALL): $(NET_SNMP_CACHE_PKG_PROCESS)
	$(RSYNC) $(NET_SNMP_INSTALL_DIR)/ $(DESTDIR)$(OMD_ROOT)/
	$(TOUCH) $@
